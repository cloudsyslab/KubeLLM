# Lab storage hygiene

The lab root filesystem backs the selected minh-lane Docker data root. Keep
campaign evidence and active worktrees intact; reclaim only reviewed, rebuildable
artifacts owned by Minh.

## Read-only report

A weekly user cron job writes one owner-only snapshot to
~/.local/state/kubellm-storage/latest.json. It reports the campaign filesystem
gate, Docker data-root profile-start gate, a 25 GiB early-warning threshold,
selected user-owned directory sizes, and counts of removable private-lane
candidates. It never deletes files. The campaign startup gate is
**20,000,000,000 bytes (20 GB decimal)** and its before-attempt floor is
10,000,000,000 bytes. Separately, the readiness helper requires **20 GiB free
in Docker's data root** before starting the Minikube profile. The report
measures both paths.

Run from the feature worktree on the lab, or inspect the latest snapshot:

~~~bash
cd /home/minh/KubeLLM/.local/operator_ui/worktrees/model-router-v0
./.venv/bin/python orchestrator/lab_storage_hygiene.py --report
cat ~/.local/state/kubellm-storage/latest.json
~~~

## Reviewed cleanup

Create a fresh owner-only plan and inspect its exact targets before applying:

~~~bash
cd /home/minh/KubeLLM/.local/operator_ui/worktrees/model-router-v0
./.venv/bin/python orchestrator/lab_storage_hygiene.py --plan
cat ~/.local/lab-ops/storage-hygiene-plan.json
./.venv/bin/python orchestrator/lab_storage_hygiene.py \
  --apply ~/.local/lab-ops/storage-hygiene-plan.json
~~~

Plans are tied to this host and user, expire after one hour, and are refused if
any target changes. Directory targets come from a fixed allowlist, are
user-owned, and have no open file handles or other users' files. Internal
symlinks are fingerprinted; dangling, foreign-owned, or escaping links block
the plan. The prediction-pilot venv has explicit exceptions for its three
known Python symlinks to the system interpreter, and those links must resolve
to regular files. Temporary build contexts are eligible only when they match
`/tmp/build.<digits>.tar`, are owned by Minh, are at least 30 days old, have a
single link, are valid tar archives, and have no open handles. Recent files,
foreign-owned files, and other `/tmp` items are ignored. Every candidate is
listed in the fresh plan and must be reviewed before apply.
Private image removal is confined to the verified minh-lane Minikube node.
Case images must be backed by checked-in case configs and Dockerfiles. The
four selected Python base tags must have no container or pod references and
are recorded by registry digest before removal. Shared-host Docker images are
never listed or changed.

The active operator UI worktree keeps data/README.md and data/exploratory.
Other tracked datasets remain in GitHub and can be restored with
git sparse-checkout add data/<dataset>. Private raw runs, campaign artifacts,
and retired-workspace archives remain intact and are reported by size. The
helper never deletes them automatically.

The reviewed 2026-11-18 cleanup removed ten allowlisted user directories,
four unused Python base tags from the private lane, and 347 eligible
`/tmp/build.<digits>.tar` files (about 5.5 MB allocated). Those archives were
user-owned, valid tar files at least 30 days old, single-link, and free of open
handles; two were older than four months. The private image registry digests
were recorded for recovery. Current root free space is 23.24 GB (21.64 GiB).
Both the 20 GB campaign startup floor and 20 GiB Docker-root profile-start gate
pass. The 25 GiB early-warning remains active. The report now finds zero
eligible temporary build archives and zero private cleanup candidates. No
campaign has been run.

The cron job runs Mondays at 09:00 UTC. It executes from the persistent
model-router-v0 feature worktree, so update the crontab path if that worktree is
moved or removed. Inspect the schedule with:

~~~bash
crontab -l
~~~
