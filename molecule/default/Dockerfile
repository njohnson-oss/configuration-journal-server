# A minimal Debian server: systemd and sshd, but neither sudo
# nor Python, so the play's raw bootstrap has something to install.
ARG BASE_IMAGE=docker.io/library/debian:13
FROM ${BASE_IMAGE}

ENV container=docker

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      systemd systemd-sysv openssh-server \
 && rm -rf /var/lib/apt/lists/*

# systemd-modules-load fails on Debian 13, whose systemd loads libkmod
# only if kmod is installed, which this image leaves out. It would leave
# the system "degraded", hiding failures that matter. The container is
# privileged, so /dev/tty1-6 are the host's consoles; getty.target would
# start logins on them and hang up whatever runs there.
RUN systemctl mask \
      systemd-modules-load.service \
      getty.target

STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
