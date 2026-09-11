# The step-3 sandbox image (D-4 step 3; F00-R12, T7; F01-R10) — and, since F10-T3, the
# devcontainer image too (F10-R5, R6, Q1): what a contributor builds in is what the gate builds
# in. One image serves the authoritative gate, precheck, reproduce.sh and .devcontainer/
# (conventions §1). It holds elan, ONE pinned Lean toolchain, the gate's Lean metaprograms, and
# the network repository's gate with its Python environment synced, so pregate.sh runs inside it
# with no network and no build. The Python pipeline of the gate itself still runs on the host and
# wraps every toolchain call in an isolated container (gate/opn_gate/sandbox.py); nothing here
# is executed by the sandbox except elan and lean.
#
#   docker build -f gate/Dockerfile --build-arg LEAN_TOOLCHAIN=leanprover/lean4:v4.33.1 \
#                -t opn-gate:leanprover-lean4-v4.33.1 .          # the context is the repo root
#
# Pins: base image by digest; elan and uv by release; the toolchain by build arg (a graph's
# gate-spec.json names it); Python by .python-version and uv.lock. Change a pin here and every
# graph pinning this commit reproduces differently — which is the point (D-5, D-35). Published
# to GHCR on every tag by .github/workflows/image-publish.yml and referenced by digest in
# gate-spec.json devcontainer_ref (F10-R5).
ARG LEAN_TOOLCHAIN=leanprover/lean4:v4.33.1
ARG ELAN_VERSION=v4.2.4
ARG UV_VERSION=0.12.10

FROM debian:bookworm-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171
ARG LEAN_TOOLCHAIN
ARG ELAN_VERSION
ARG UV_VERSION

ENV ELAN_HOME=/opt/elan \
    PATH=/opt/elan/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LC_ALL=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git bash \
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
COPY gate/lean/ /opt/opn/lean/
RUN set -eux; \
    printf '%s\n' "${LEAN_TOOLCHAIN}" > /opt/opn/lean/lean-toolchain; \
    cd /opt/opn/lean; \
    elan run "${LEAN_TOOLCHAIN}" lake build; \
    test -x .lake/build/bin/opn-witness-type; \
    test -x .lake/build/bin/opn-used-constants; \
    test -x .lake/build/bin/opn-hazards; \
    chmod -R a+rX /opt/opn

# F10-R6: the network's gate, runnable offline. uv (pinned) installs the Python .python-version
# names and syncs the locked environment; pregate.sh then needs nothing the image lacks.
ENV UV_PYTHON_INSTALL_DIR=/opt/uv/python \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_NO_DEV=1 \
    UV_NO_PROGRESS=1
RUN set -eux; \
    curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | env UV_INSTALL_DIR=/usr/local/bin sh; \
    uv --version
COPY .python-version lean-toolchain pyproject.toml uv.lock /opt/opn/network/
COPY gate/ /opt/opn/network/gate/
RUN set -eux; \
    cd /opt/opn/network; \
    uv python install; \
    uv sync --frozen; \
    rm -rf /tmp/uv-cache; \
    chmod -R a+rX /opt/uv /opt/opn/network
# The gate finds elan and the built metaprograms here rather than under a home directory
# (opn_gate.config OPN_ELAN_HOME, OPN_LEAN_PKG_BIN; the sandbox sets the same two).
ENV OPN_ELAN_HOME=/opt/elan \
    OPN_LEAN_PKG_BIN=/opt/opn/lean/.lake/build/bin \
    NETWORK=/opt/opn/network

# Non-root. The sandbox runs as 1000 with HOME=/tmp and copies its inputs in; the devcontainer
# runs as the same uid with a home of its own, so an editor has somewhere to write.
RUN useradd --uid 1000 --create-home --shell /bin/bash opn
USER 1000:1000
ENV HOME=/home/opn
WORKDIR /home/opn
