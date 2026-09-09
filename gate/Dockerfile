# The step-3 sandbox image (D-4 step 3; F00-R12, T7; F01-R10). One image serves the authoritative
# gate, precheck and reproduce.sh (conventions §1). It holds elan, ONE pinned Lean toolchain and
# the gate's Lean metaprograms, nothing else: the Python pipeline stays on the host and wraps
# every toolchain call in an isolated container (gate/opn_gate/sandbox.py).
#
#   docker build -f gate/Dockerfile --build-arg LEAN_TOOLCHAIN=leanprover/lean4:v4.33.1 \
#                -t opn-gate:leanprover-lean4-v4.33.1 gate
#
# Pins: base image by digest; elan by release; the toolchain by build arg (a graph's gate-spec.json
# names it). Change a pin here and every graph pinning this commit reproduces differently — which
# is the point (D-5, D-35).
ARG LEAN_TOOLCHAIN=leanprover/lean4:v4.33.1
ARG ELAN_VERSION=v4.2.4

FROM debian:bookworm-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171
ARG LEAN_TOOLCHAIN
ARG ELAN_VERSION

ENV ELAN_HOME=/opt/elan \
    PATH=/opt/elan/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LC_ALL=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git \
 && rm -rf /var/lib/apt/lists/*

# elan from its release tarball (pinned), then the one toolchain; no default toolchain is set so
# every invocation names the toolchain it runs (`elan run <toolchain> lean ...`).
RUN set -eux; \
    arch="$(uname -m)"; \
    curl -sSfL "https://github.com/leanprover/elan/releases/download/${ELAN_VERSION}/elan-${arch}-unknown-linux-gnu.tar.gz" \
      -o /tmp/elan.tar.gz; \
    tar -xzf /tmp/elan.tar.gz -C /tmp; \
    /tmp/elan-init -y --no-modify-path --default-toolchain none; \
    rm -f /tmp/elan.tar.gz /tmp/elan-init; \
    elan toolchain install "${LEAN_TOOLCHAIN}"; \
    elan run "${LEAN_TOOLCHAIN}" lean --version; \
    chmod -R a+rX /opt/elan

# The gate's Lean metaprograms (F01-R1, R10; F02-R1: the hazard checkers): built here so the
# authoritative gate, precheck and reproduce.sh run identical binaries. The package pins the same
# toolchain via lean-toolchain.
COPY lean/ /opt/opn/lean/
RUN set -eux; \
    printf '%s\n' "${LEAN_TOOLCHAIN}" > /opt/opn/lean/lean-toolchain; \
    cd /opt/opn/lean; \
    elan run "${LEAN_TOOLCHAIN}" lake build; \
    test -x .lake/build/bin/opn-witness-type; \
    test -x .lake/build/bin/opn-used-constants; \
    test -x .lake/build/bin/opn-hazards; \
    chmod -R a+rX /opt/opn

# Non-root, no home to write to beyond /tmp.
RUN useradd --uid 1000 --no-create-home --shell /usr/sbin/nologin opn
USER 1000:1000
ENV HOME=/tmp
WORKDIR /tmp
