#!/bin/bash
# Fleet launcher (PREREGISTRATION_V2_NETWORKS_2026-11-08.md): runs analysis/v2_fleet/run_network.py for each network id given,
# networks one after another on this machine (chunks of a network in parallel). Logs: results/v2/runs/<NET>/fleet.log
#   bash analysis/v2_fleet/run_network.sh NET1 [NET2 ...]
# Refuses to start unless the pre-registration file and results/v2/networks.json are in origin/main (no data before the push).
set -u
cd "$(dirname "$0")/../.."
if [ -d .git ]; then
  git fetch -q origin main || { echo "git fetch failed"; exit 2; }
  git cat-file -e origin/main:PREREGISTRATION_V2_NETWORKS_2026-11-08.md 2>/dev/null && git cat-file -e origin/main:results/v2/networks.json 2>/dev/null     || { echo "pre-registration not on origin/main yet: refusing to request data"; exit 3; }
  git merge -q --ff-only origin/main || { echo "local repo not fast-forwardable to origin/main"; exit 4; }
else   # VM/Kaggle copy made by `git archive origin/main` after the pre-registration push; FLEET_COMMIT = that sha
  [ -s FLEET_COMMIT ] && [ -f PREREGISTRATION_V2_NETWORKS_2026-11-08.md ] && [ -f results/v2/networks.json ]     || { echo "no FLEET_COMMIT / pre-registration / networks.json in this copy: refusing to request data"; exit 3; }
fi
export P10_PY=${P10_PY:-/opt/p10/bin/python} P10_PLATFORM=${P10_PLATFORM:-$(hostname)}
mkdir -p results/v2/runs
for NET in "$@"; do
  $P10_PY analysis/v2_fleet/run_network.py "$NET" >> results/v2/runs/fleet_$(hostname).log 2>&1
done
touch results/v2/runs/FLEET_DONE_$(hostname)
