# Lab operations and recovery

Use these helpers on the lab host with the same explicit owner-only lane
selector used by the benchmark runner. They inspect the whole Docker host but
only apply cleanup to resources whose lane label matches the selected lane.
Resources without a clear owner remain review items. No helper runs Docker
prune, removes volumes, changes Minikube profiles, or resumes a benchmark.

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
directory-size breakdown. It reports whether that breakdown needs root access.
For complete filesystem attribution, run a read-only scan separately:

```bash
sudo du -x -B1 --max-depth=2 / 2>/dev/null | sort -n | tail -80
```

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
the owner-verified PostgreSQL custom dump, a consistent SQLite backup, and
ignored operational/evidence files over SSH, encrypts the stream to the
configured OpenSSH Ed25519 key, and uploads ciphertext to a private GitHub
Release. The helper refuses to start when an operator job or selected-lane
runner is active. It downloads the uploaded asset, decrypts it in a temporary
owner-only directory, and checks archive CRCs and every manifest checksum
before reporting success.
Before creating the temporary restore database, it confirms the selected
database filesystem has at least twice the source database size plus 2 GiB of
free space. A failed capacity check leaves the uploaded encrypted release in
place and stops without changing the database.

```bash
python3 scripts/lab_ops_backup.py
```

The asset is encrypted to `~/.ssh/codex_kubellm_operator_ui`; retain that
private identity offline with access to the recovery machine. GitHub receives
only ciphertext. The plaintext archive exists briefly in a mode-0700 local
temporary directory during verification and is removed when the command exits.
Each release asset must remain below GitHub's 2 GiB limit. If an archive exceeds
that size, the helper stops without uploading; split the evidence set only
after reviewing its contents.

To recover an asset, download it from the private
[`kubellm-lab-backups` repository](https://github.com/minh-mhl-le/kubellm-lab-backups),
decrypt with `age -d -i ~/.ssh/codex_kubellm_operator_ui`, then inspect
`manifest.json` and verify checksums before restoring into an isolated path.
Restore PostgreSQL into a fresh database first; load the SQLite SQL snapshot
into a fresh SQLite file, then restore evidence to a separate state directory.
Do not overlay a live database or operator state until the isolated restore
has been checked.

The release repository is a recovery copy, not the sole long-term archive.
Keep at least one additional encrypted copy outside this lab host and GitHub.
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

For services to start before login, user lingering must already be enabled.
If the installer reports it is disabled, an administrator must run:

```bash
sudo loginctl enable-linger "$USER"
```

During the handoff, stop the existing loopback UI and RAG processes only after
checking that no operator job or selected-lane runner is active. Then start the
units with `systemctl --user start kubellm-ui kubellm-rag` and verify each with
`systemctl --user status` plus the readiness check below. Logs are collected by
the system journal and use the host's configured journal rotation.

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
