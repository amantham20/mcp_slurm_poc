#!/usr/bin/env bash
set -euo pipefail
echo "Registering cluster and default account/user in Slurm accounting..."
docker compose exec -T slurmctld bash -lc "sacctmgr -i add cluster slurm-cluster || true;     sacctmgr -i add account compute-account || true;     sacctmgr -i add user root account=compute-account || true"
echo "Done."
