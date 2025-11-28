# slurm-docker-cluster (ready-to-run pack)

This folder mirrors the layout and behavior of the example at
giovtorres/slurm-docker-cluster. Use it to replace a non-working setup.

## Quick start
```bash
cd slurm-docker-cluster-example
docker compose up -d
./register_cluster.sh
docker compose exec slurmctld bash -lc 'sinfo && squeue'
docker compose exec slurmctld bash -lc 'cd /data && sbatch --wrap="hostname" && sleep 2 && ls -l'
```

## Files
- `docker-compose.yml` — spins up: mysql, slurmdbd, slurmctld, c1, c2
- `slurm.conf` — cluster+partition config (ControlMachine=slurmctld, nodes c1,c2)
- `slurmdbd.conf` — accounting to MySQL at `mysql` with user `slurm`/`password`
- `register_cluster.sh` — seeds the accounting DB with a cluster, account, and user

## Notes
- The compose uses the published image `giovtorres/slurm-docker-cluster:latest`.
- Named volumes persist configs and logs between restarts.
- If your host uses cgroups v2, we run nodes as `privileged: true` so slurmd cgroups work.
- You can customize CPU/memory in `slurm.conf` and scale compute nodes by adding `c3`, `c4`, etc.
