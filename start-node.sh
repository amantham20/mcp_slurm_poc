#!/bin/bash
# start-node.sh

# Start munge
mkdir -p /run/munge
chown munge:munge /run/munge
chmod 755 /run/munge
sudo -u munge /usr/sbin/munged

# Wait for controller to be ready
echo "Waiting for slurmctld to be ready..."
while ! nc -z slurmctld 6817; do
    echo "Controller not ready, waiting..."
    sleep 2
done

# Create directories
mkdir -p /var/run/slurm
chown slurm:slurm /var/run/slurm

# Configure cgroups
mkdir -p /sys/fs/cgroup/cpuset
mkdir -p /sys/fs/cgroup/memory
mkdir -p /sys/fs/cgroup/devices

# Start slurmd
echo "Starting slurmd on $HOSTNAME..."
/usr/local/sbin/slurmd -D