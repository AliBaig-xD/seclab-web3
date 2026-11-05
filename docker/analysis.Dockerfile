# seclab-web3 analysis toolchain (pinned via versions.env; resolve-then-freeze).
FROM python:3.11-slim-bookworm
ENV DEBIAN_FRONTEND=noninteractive \
    PATH="/root/.foundry/bin:/root/.solc-select/bin:/usr/local/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
      git curl ca-certificates jq build-essential xz-utils unzip \
      libgmp-dev libssl-dev pkg-config \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

COPY docker/requirements.in /tmp/requirements.in
RUN pip install --no-cache-dir -r /tmp/requirements.in \
 && pip freeze > /opt/resolved-requirements.txt

RUN solc-select install 0.8.28 && solc-select use 0.8.28

RUN curl -L https://foundry.paradigm.xyz | bash && /root/.foundry/bin/foundryup

# Echidna / Medusa / Aderyn — latest linux RELEASE BINARY (exclude installers/updaters)
RUN bash -c '\
  install_bin(){ repo="$1"; pat="$2"; bin="$3"; \
    u=$(curl -fsSL "https://api.github.com/repos/$repo/releases/latest" \
        | jq -r ".assets[].browser_download_url" \
        | grep -iE "$pat" \
        | grep -ivE "arm|aarch|darwin|sha256|\.asc|\.sig|installer|npm|\.rb|update|source|checksum" \
        | head -1); \
    echo "[$bin] $u"; [ -n "$u" ] || { echo "no asset for $bin"; exit 1; }; \
    f=/tmp/$bin.pkg; curl -fsSL "$u" -o "$f"; \
    case "$u" in \
      *.tar.gz|*.tgz) tar -xzf "$f" -C /tmp;; \
      *.tar.xz)       tar -xJf "$f" -C /tmp;; \
      *.zip)          unzip -o "$f" -d /tmp;; \
      *)              cp "$f" /tmp/$bin;; \
    esac; \
    p=$(find /tmp -maxdepth 3 -type f -name "$bin" | head -1); \
    [ -n "$p" ] || { echo "binary $bin not found after extract"; exit 1; }; \
    install -m755 "$p" /usr/local/bin/$bin; $bin --version 2>&1 | head -1 || true; }; \
  install_bin crytic/echidna "x86_64-linux|linux"      echidna; \
  install_bin crytic/medusa  "linux"                    medusa; \
  install_bin Cyfrin/aderyn  "x86_64.*linux.*(tar|gz|xz)" aderyn'

WORKDIR /work
