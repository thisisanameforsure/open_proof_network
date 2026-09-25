# F16-T7: the harness image, where the connectors' real-client tier runs (make verify-harness).
#
#   docker build -f gate/clients/harness/Dockerfile -t opn-harness .
#   docker run --rm -v "$PWD":/work -w /work opn-harness make verify-harness
#
# Third-party binaries live here and nowhere else (C5): they are never a Python dependency and
# never on the gate's path. Pins: the base by digest (the gate image's own, gate/Dockerfile);
# Node by release and sha256; uv by release, as the gate image; each harness by exact version in
# package.json with its tarball's integrity hash in package-lock.json, installed with `npm ci`.
# Move a harness pin only in a commit that carries a passing run of the new version (F16-R11).
# The image holds no secret. A level-3 run passes a model key in with `docker run -e` by hand
# (F16-Q5); level 2 needs none.

ARG NODE_VERSION=v22.22.2
ARG NODE_SHA256_X64=88fd1ce767091fd8d4a99fdb2356e98c819f93f3b1f8663853a2dee9b438068a
ARG NODE_SHA256_ARM64=e9e1930fd321a470e29bb68f30318bf58e3ecb4acb4f1533fb19c58328a091fe
ARG UV_VERSION=0.12.10

FROM debian:bookworm-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171
ARG NODE_VERSION
ARG NODE_SHA256_X64
ARG NODE_SHA256_ARM64
ARG UV_VERSION

ENV LC_ALL=C.UTF-8 \
    PATH=/opt/harness/node_modules/.bin:/opt/node/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    UV_PYTHON_INSTALL_DIR=/opt/uv/python \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_NO_PROGRESS=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git make xz-utils openssh-client \
 && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "$(uname -m)" in \
      x86_64) arch=x64; sum="${NODE_SHA256_X64}" ;; \
      aarch64) arch=arm64; sum="${NODE_SHA256_ARM64}" ;; \
      *) echo "unsupported architecture $(uname -m)"; exit 1 ;; \
    esac; \
    curl -sSfL "https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-linux-${arch}.tar.xz" \
      -o /tmp/node.tar.xz; \
    echo "${sum}  /tmp/node.tar.xz" | sha256sum -c -; \
    mkdir -p /opt/node; \
    tar -xJf /tmp/node.tar.xz -C /opt/node --strip-components=1; \
    rm -f /tmp/node.tar.xz; \
    node --version

RUN set -eux; \
    curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | env UV_INSTALL_DIR=/usr/local/bin sh; \
    uv --version

COPY gate/clients/harness/package.json gate/clients/harness/package-lock.json /opt/harness/
RUN set -eux; \
    cd /opt/harness; \
    npm ci --no-audit --no-fund; \
    claude --version; codex --version; gemini --version; copilot --version; \
    chmod -R a+rX /opt/harness /opt/node

# The check runs each harness with a throwaway HOME; the repository is mounted at run time.
RUN useradd --uid 1000 --create-home --shell /bin/bash opn
USER 1000:1000
ENV HOME=/home/opn OPN_HARNESS_BIN=/opt/harness/node_modules/.bin
WORKDIR /work
