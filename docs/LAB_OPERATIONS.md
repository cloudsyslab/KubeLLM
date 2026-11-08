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

## Encrypted recovery copies

Run the backup client from your Mac. It streams selected-lane configuration,
the owner-verified PostgreSQL custom dump and image, a consistent SQLite
backup, and the selected operator state's history and logs over SSH. Other
ignored files are excluded because they may belong to a different lane. With
the explicit default-profile option below, it also cold-snapshots only the exact reviewed
`minikube` container, its `/var` volume, the committed container image, network
configuration, profile certificates, and the `minikube`-only kubeconfig
context. The snapshot is encrypted to the configured OpenSSH Ed25519 key
before it leaves the Mac and uploaded in sub-2 GiB assets to a private GitHub
Release. A second encrypted copy stays on the Mac.

The helper refuses to start when an operator job or selected-lane runner is
active. It downloads the release into a separate directory, reassembles the
encrypted stream, decrypts it in a temporary owner-only directory, and checks
archive CRCs and every manifest checksum. It restores PostgreSQL in the
separate x86_64 Colima profile and restores the default Minikube node, volume,
and network there; success requires the clone's Kubernetes API readiness probe.
If any snapshot or restore check fails, it starts the original default Minikube
container again. A passing drill leaves that original container stopped for
the separately reviewed retirement step.

```bash
python3 scripts/lab_ops_backup.py \
  --include-approved-default-minikube \
  --expected-default-minikube-container-id <full-id-from-the-reviewed-audit>
```

The asset is encrypted to `~/.ssh/codex_kubellm_operator_ui`; retain that
private identity offline with access to the recovery machine. GitHub and the
Mac snapshot directory receive ciphertext only. Plaintext exists briefly in a
mode-0700 local temporary directory during verification and is removed when
the command exits. Large snapshots are split into numbered assets below the
2 GiB per-asset limit, then their concatenated hash is checked after download.

To manually recover an asset, download all numbered parts from the private
[`kubellm-lab-backups` repository](https://github.com/minh-mhl-le/kubellm-lab-backups),
concatenate the parts in numeric order, and decrypt with
`age -d -i ~/.ssh/codex_kubellm_operator_ui`. Inspect `manifest.json` and verify
all listed checksums before restoring into an isolated path. Restore
PostgreSQL into a fresh database first; load the SQLite SQL snapshot into a
fresh SQLite file; restore the volume archive into a new Docker volume; and
recreate the node from the saved image and container metadata. Never overlay a
live database or operator state before an isolated restore passes.

The release repository and local encrypted snapshot directory are independent
recovery copies. Keep the matching private age identity offline and backed up.
Delete older releases only after a newer asset has passed download, decrypt,
checksum, and isolated restore verification.

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
