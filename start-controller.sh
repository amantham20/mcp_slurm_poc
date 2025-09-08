#!/bin/bash
# start-controller.sh

# Start munge
mkdir -p /run/munge
chown munge:munge /run/munge
chmod 755 /run/munge
sudo -u munge /usr/sbin/munged

# Wait for MySQL to be ready
echo "Waiting for MySQL to be ready..."
while ! mysqladmin ping -h mysql -u slurm -ppassword --silent; do
    echo "MySQL not ready, waiting..."
    sleep 2
done

echo "MySQL is ready, initializing Slurm accounting database..."

# Initialize accounting database
sacctmgr -i add cluster slurm-cluster || true
sacctmgr -i add account compute-account || true
sacctmgr -i add user root account=compute-account || true

# Create directories
mkdir -p /var/run/slurm
chown slurm:slurm /var/run/slurm

# Start slurmctld
echo "Starting slurmctld..."
/usr/local/sbin/slurmctld -D