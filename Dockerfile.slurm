FROM ubuntu:22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    curl \
    python3 \
    python3-pip \
    mysql-client \
    libmysqlclient-dev \
    libssl-dev \
    libpam0g-dev \
    libnuma-dev \
    libhwloc-dev \
    libfreeipmi-dev \
    librrd-dev \
    libncurses5-dev \
    libglib2.0-dev \
    libgtk2.0-dev \
    xauth \
    munge \
    libmunge-dev \
    openssh-server \
    supervisor \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Create slurm user
RUN groupadd -r slurm && useradd -r -g slurm -d /var/lib/slurm -s /bin/bash slurm

# Download and compile Slurm
WORKDIR /tmp
RUN wget https://download.schedmd.com/slurm/slurm-23.11.1.tar.bz2 && \
    tar xjf slurm-23.11.1.tar.bz2 && \
    cd slurm-23.11.1 && \
    export PKG_CONFIG_PATH=/usr/lib/x86_64-linux-gnu/pkgconfig:$PKG_CONFIG_PATH && \
    ./configure \
        --prefix=/usr/local \
        --sysconfdir=/etc/slurm \
        --with-mysql_config=/usr/bin/mariadb_config \
        --enable-pam \
        --with-munge \
        --with-hwloc \
        --with-freeipmi && \
    make -j$(nproc) && \
    make install && \
    cd / && rm -rf /tmp/slurm-23.11.1*

# Create necessary directories
RUN mkdir -p /var/spool/slurm \
             /var/log/slurm \
             /etc/slurm \
             /var/lib/slurm \
    && chown -R slurm:slurm /var/spool/slurm \
                            /var/log/slurm \
                            /etc/slurm \
                            /var/lib/slurm

# Set up munge
RUN mkdir -p /etc/munge /var/lib/munge /var/log/munge /run/munge && \
    chown -R munge:munge /etc/munge /var/lib/munge /var/log/munge /run/munge && \
    chmod 700 /etc/munge /var/lib/munge /var/log/munge && \
    chmod 755 /run/munge

# Generate munge key
RUN /usr/sbin/create-munge-key

# Set up SSH
RUN mkdir -p /var/run/sshd && \
    echo 'root:slurm123' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# Add Slurm binaries to PATH
ENV PATH="/usr/local/bin:/usr/local/sbin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/lib"

# Copy configuration and startup scripts
COPY slurm.conf /etc/slurm/slurm.conf
COPY start-controller.sh /start-controller.sh
COPY start-node.sh /start-node.sh
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Make scripts executable
RUN chmod +x /start-controller.sh /start-node.sh

EXPOSE 6817 6818 22

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]