# Lab operations and recovery

Use these helpers on the lab host with the same explicit owner-only lane
selector used by the benchmark runner. They inspect the whole Docker host but
only apply cleanup to resources whose lane label matches the selected lane.
Resources without a clear owner remain review items. Cleanup never runs Docker
prune, removes volumes, or resumes a benchmark.

## Audit and cleanup

From the checkout being operated:

```bash
export KUBELLM_LAB_CONFIG="$HOME/.config/kubellm/lanes/minh.json"
install -d -m 700 .local/lab-ops
.venv/bin/python scripts/lab_ops.py --lab-config "$KUBELLM_LAB_CONFIG" audit > .local/lab-ops/audit.json
.venv/bin/python scripts/lab_ops.py --lab-config "$KUBELLM_LAB_CONFIG" plan
```

The audit includes global Docker container, image, and volume metadata; selected
lane endpoints and health; root filesystem capacity; and a bounded-depth
directory-size breakdown. It reports when complete filesystem attribution is
unavailable to the current account. Do not use sudo or privileged host mounts
to work around that limit; keep root-only attribution as a separate lab-admin
investigation.

The selected Minikube preparation gate requires 20 GiB free in Docker's data
root. Keep at least 30 GiB free for routine operation. After reviewing an audit,
make a fresh one-hour cleanup plan. The plan lists exact Docker IDs, owner lane,
references, and size estimates. Only explicitly lane-labeled unused images are
eligible for `apply`; ownership and references are checked again at removal.
Stopped containers may hold benchmark logs, and unattached volumes may hold
database or cluster state, so this helper leaves those for manual review.

```bash
.venv/bin/python scripts/lab_ops.py --lab-config "$KUBELLM_LAB_CONFIG" plan
.venv/bin/python scripts/lab_ops.py --lab-config "$KUBELLM_LAB_CONFIG" apply \
  --plan .local/lab-ops/cleanup-plan.json --resource <full-image-id> --yes
```

Never use `docker system prune`, `docker volume prune`, broad Minikube deletion,
or an old plan. A plan that predates the one-hour window or no longer matches
current ownership/use will fail closed. Cross-lane candidates stay in the
report; review their exact IDs, current owner, use, and expected recovery with
that lane's owner before any removal.

## Lab-native encrypted recovery

The Mac is a command and status terminal only. The lab creates, compresses,
encrypts, uploads, downloads, and verifies the snapshot on the server. Snapshot
and restore disk data stay in RAM-backed /dev/shm; snapshot bytes do not transit
the Mac. Only small control scripts and, after the restore VM is sealed, the
dedicated age recovery identity cross SSH.

A fine-grained GitHub token is needed only when resuming to upload the backup.
Create one for only the private
[minh-mhl-le/kubellm-lab-backups](https://github.com/minh-mhl-le/kubellm-lab-backups)
repository with **Contents: read and write**. Do not reuse the Mac's broad
GitHub login token. Wait until VM preparation finishes before installing it.

Prepare the disposable x86_64 restore VM and verify the reviewed OpenClaw image
by immutable digest in a fresh Docker engine. This first boot has network
access only for Ubuntu package setup and the digest pull; no backup, age
identity, or GitHub token is mounted into the guest. QEMU shuts the VM down
before the helper asks for the recovery identity.

~~~bash
python3 scripts/lab_ops_native.py prepare \
  --release-tag lab-backup-<UTC-timestamp>
python3 scripts/lab_ops_native.py status --job-id <job-id>
~~~

Preparation creates a dedicated recovery identity at
~/.codex/lab-backups/recovery.agekey. Make a second offline copy before
resuming; the private key cannot be recovered from GitHub.

For a new backup, omit --release-tag to create a fresh tag. To resume an
interrupted transfer, pass its exact tag: the worker reuses a complete private
draft after checking every numbered part and digest. Incomplete, unexpected, or
mismatching assets fail closed; they are never deleted or replaced.
Wait for status awaiting-recovery-key. Then install the token from a prompt
that does not echo input:

~~~bash
python3 scripts/lab_ops_native.py configure-token
~~~

The helper writes it to /home/minh/.config/kubellm/lab-ops/github.token on the
lab with mode 0600. It refuses to overwrite an existing token, checks the
private repository identity, and never writes the token to status or logs.
Then resume:

~~~bash
python3 scripts/lab_ops_native.py resume --job-id <job-id>
python3 scripts/lab_ops_native.py status --job-id <job-id>
~~~

The resume command sends the dedicated recovery identity only after QEMU has
restarted with user networking restrict=on and an egress probe fails. QEMU
exposes SSH only on a loopback port for control. The guest has no external
network route while restore data is present. The worker then:

1. Reuses a complete private draft for the requested tag, or takes a consistent
   selected-lane snapshot and cold snapshot of only the
   exact reviewed default Minikube container, /var volume, image, network,
   profile files, and Minikube kubeconfig context.
2. Compresses the ZIP stream with zstd, encrypts with the dedicated age recipient, and
   uploads numbered 128 MiB ciphertext assets directly from lab RAM.
3. Downloads every release asset into lab RAM and checks GitHub's SHA-256
   digest against the exact uploaded chunk, then decrypts, decompresses zstd
   within the RAM staging limit, and checks ZIP CRCs and all manifest checksums.
4. Restores PostgreSQL, SQLite, and the old Minikube profile into the
   network-restricted QEMU VM, capped at 32 GiB memory, four vCPUs, and a
   48 GiB sparse disk. RAM-backed staging is capped at 28 GiB with an 8 GiB
   host-memory safety floor.
5. Publishes the private release only after isolated restore passes. It then
   rechecks and retires the previously reviewed Minikube profile and removes
   only the approved, digest-verified, unused OpenClaw image. It never runs
   Docker prune or touches other images, volumes, containers, or lanes.

The age identity is created once at
~/.codex/lab-backups/recovery.agekey with mode 0600. Keep a second offline
copy: GitHub assets cannot be recovered without this key. The key remains on
the Mac; its temporary lab copy is RAM-only and removed at job completion.
GitHub stores ciphertext only. Status records under
/home/minh/KubeLLM/.local/lab-ops/jobs/ contain phases, counts, and safe
resource summaries, not credentials or backup contents.

If the process reports a failure, inspect status before retrying. The worker
restarts the reviewed Minikube container after snapshot or restore errors; a
host power loss during the brief cold snapshot can still leave it stopped, so
check its exact ID before starting anything. A partial draft stays private and
is never overwritten. Use a fresh release tag for a new snapshot. If status
reports cleanup-complete-preflight-failing, the exact authorized cleanup
finished but Docker still needs more space; review new candidate IDs and get
approval before removing anything else.

To restore elsewhere, download and concatenate numbered encrypted assets in
order, then decrypt with the matching age identity and verify manifest.json
before restoring into isolated database, volume, and cluster resources. Never
overlay a live database or operator state before isolated restore checks pass.

## Reboot and service ownership

Install per-user systemd units after a verified recovery snapshot:

```bash
.venv/bin/python scripts/install_lab_user_services.py \
  --lab-config "$KUBELLM_LAB_CONFIG" \
  --repo "$PWD" \
  --state-dir "$HOME/KubeLLM/.local/operator_ui"
```

The installer enables `kubellm-ui.service` and `kubellm-rag.service` without
starting them during the install window, and sets automatic restart on the
selected database container only after validating its lane label. The service
units start that same selected database before the UI or RAG API. The RAG API
loads provider credentials from the selected lane's owner-only service
environment file at startup; credentials are not copied into the systemd unit
or a shell startup file. The units do not start Minikube or resume benchmark
jobs. Interrupted campaigns remain interrupted and require deliberate
relaunch.

The installer tries to enable lingering for the invoking account with
`loginctl enable-linger` and no username argument. If host policy denies that
self-service action, it disables these systemd units and installs one tagged
`@reboot` crontab entry that starts a lane-scoped supervisor. The supervisor
waits for the selected database, starts only the selected UI and RAG services,
checks that existing loopback listeners belong to the selected lane, restarts
failed owned processes, and keeps bounded owner-only logs under the operator
state directory. It preserves unrelated crontab entries; no administrator or
sudo access is required.

During the handoff, stop the existing loopback UI and RAG processes only after
checking that no operator job or selected-lane runner is active. Then start the
units with `systemctl --user start kubellm-ui kubellm-rag` and verify each with
`systemctl --user status` plus the readiness check below. The cron fallback
starts the supervisor at boot and does not start Minikube or resume benchmark
jobs. Systemd logs use host journal rotation; fallback logs rotate at 5 MiB
with three retained files per service.

## Readiness, updates, and recovery checks

After cleanup or a service handoff, rerun the selected-lane readiness check
and canonical runner preflight:

```bash
.venv/bin/python .agents/skills/kubellm-benchmarks/scripts/check_readiness.py \
  --repo "$PWD" --lab-config "$KUBELLM_LAB_CONFIG" --check-only --json
.venv/bin/python debug_assistant_latest/runner.py \
  --lab-config "$KUBELLM_LAB_CONFIG" --preflight
```

The UI's readiness summary preserves allowlisted, redacted nested runner
failures, including the Minikube storage reason. Do not consider the lane ready
until its profile, database, RAG API, provider, case dry-run, and runner
preflight gates pass. Record the starting and ending free space and each
resource ID acted on. Review code updates in a separate checkout, retain the
previous service revision, then update one selected lane at a time and rerun
the same checks before removing rollback material.
