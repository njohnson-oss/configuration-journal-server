# Not a stage of Dockerfile: the docker driver builds every stage of that,
# once per platform, and only prepare.yml needs this image.

# ── keygen ────────────────────────────────────────────────────────────
# The tools README.md suggests for the keys a user supplies: tor and
# i2pd generate them for a service whose key file is missing.
# prepare.yml runs keygen.sh in this image.
FROM docker.io/library/debian:13 AS keygen

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      tor i2pd \
 && rm -rf /var/lib/apt/lists/*

COPY keygen.sh /usr/local/bin/keygen
