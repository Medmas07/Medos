#!/bin/sh
# Container runtime check of Hospital Node @NODE_REF@ (HC-222).
#
#   ./check-runtime.sh        report whether this host can run the Node, and what to do if not
#
# Exit code 0 when the host is ready, 3 when it is not. install.sh runs it before
# starting the Node. It only reads: it never installs software, never starts or
# configures a service, and never asks for administrator rights.

# The image in this package, as the platform built it.
IMAGE_OS="@IMAGE_OS@"
IMAGE_ARCH="@IMAGE_ARCH@"
# Compose v2 is the `docker compose` plugin; the standalone v1 `docker-compose` is not used.
COMPOSE_MAJOR=2

case "${1:-}" in
    "") ;;
    -h | --help)
        sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
        exit 0
        ;;
    *)
        echo "check-runtime.sh: unknown argument: $1" >&2
        exit 2
        ;;
esac

BLOCKING=0
ok() { echo "[ok]      $1"; }
warn() { echo "[warning] $1"; }
blocked() {
    echo "[missing] $1"
    shift
    for line in "$@"; do
        echo "          $line"
    done
    BLOCKING=1
}

# Where the administrator installs Docker depends on the host; only a pointer is given.
host="$(uname -s 2>/dev/null)" || host=""
case "$host" in
    Linux) install_hint="Docker Engine with the Compose plugin: https://docs.docker.com/engine/install/" ;;
    Darwin) install_hint="Docker Desktop for Mac: https://docs.docker.com/desktop/setup/install/mac-install/" ;;
    MINGW* | MSYS* | CYGWIN*) install_hint="Docker Desktop for Windows (WSL 2 backend): https://docs.docker.com/desktop/setup/install/windows-install/" ;;
    *) install_hint="Docker Engine with the Compose plugin: https://docs.docker.com/get-started/get-docker/" ;;
esac

finish() {
    echo
    if [ "$BLOCKING" -eq 0 ]; then
        echo "This host can run Hospital Node @NODE_REF@ ($IMAGE_OS/$IMAGE_ARCH)."
        exit 0
    fi
    echo "This host cannot run Hospital Node @NODE_REF@ yet. Nothing was installed or changed;"
    echo "ask the host's administrator to act on the lines above, then run this check again."
    exit 3
}

echo "Checking the container runtime for Hospital Node @NODE_REF@ ($IMAGE_OS/$IMAGE_ARCH)..."

# 1. The Docker command-line client.
if ! command -v docker >/dev/null 2>&1; then
    others=""
    for tool in podman nerdctl; do
        command -v "$tool" >/dev/null 2>&1 && others="$others $tool"
    done
    if [ -n "$others" ]; then
        blocked "Docker was not found. Found instead:$others, which this package was not tested with." \
            "Install $install_hint"
    else
        blocked "Docker was not found." "Install $install_hint"
    fi
    finish
fi
client="$(docker --version 2>/dev/null)" || client=""
case "$client" in
    *[Pp]odman*) warn "the docker command is Podman ($client). Only Docker was tested (ADR-0016)." ;;
    "") warn "the docker command did not report its version." ;;
    *) ok "client: $client" ;;
esac

# 2. The Compose v2 plugin, which install.sh calls as `docker compose`.
compose="$(docker compose version --short 2>/dev/null)" || compose=""
compose="${compose#v}"
if [ -z "$compose" ]; then
    if command -v docker-compose >/dev/null 2>&1; then
        blocked "the Compose plugin (docker compose) was not found; only the standalone docker-compose is installed." \
            "Install the Compose plugin: https://docs.docker.com/compose/install/linux/"
    else
        blocked "the Compose plugin (docker compose) was not found." \
            "Install the Compose plugin: https://docs.docker.com/compose/install/linux/"
    fi
elif [ "${compose%%.*}" -ge "$COMPOSE_MAJOR" ] 2>/dev/null; then
    ok "compose: $compose"
else
    blocked "Compose $compose is too old; version $COMPOSE_MAJOR or later is required." \
        "Upgrade the Compose plugin: https://docs.docker.com/compose/install/linux/"
fi

# 3. The daemon answers, and runs containers of the image's platform.
if ! info="$(docker info --format '{{.OSType}}|{{.Architecture}}|{{.ServerVersion}}|{{range .SecurityOptions}}{{.}} {{end}}' 2>/dev/null)"; then
    # The formatted output is empty fields when the daemon does not answer; the
    # reason is on stderr.
    reason="$(docker info --format '{{.ServerVersion}}' 2>&1 >/dev/null)"
    case "$reason" in
        *[Pp]ermission\ denied*)
            blocked "Docker is installed, but this user may not use its daemon (permission denied)." \
                "The administrator can grant access (membership of the docker group is equivalent to root)" \
                "or set up rootless Docker: https://docs.docker.com/engine/security/rootless/" \
                "This check never uses sudo."
            ;;
        *)
            newline='
'
            first="${reason%%"$newline"*}"
            blocked "Docker is installed, but its daemon does not answer: $first" \
                "Start Docker Desktop, or ask the administrator to start the Docker service."
            ;;
    esac
    finish
fi

IFS='|' read -r os arch server security <<EOF
$info
EOF
case "$arch" in
    x86_64 | amd64) arch=amd64 ;;
    aarch64 | arm64) arch=arm64 ;;
esac
case " $security " in
    *name=rootless*) mode="rootless" ;;
    *) mode="rootful" ;;
esac
ok "daemon: Docker Engine $server, $os/$arch, $mode"

if [ "$os" != "$IMAGE_OS" ]; then
    blocked "the daemon runs $os containers; the Node's image is a $IMAGE_OS image." \
        "On Docker Desktop for Windows, switch to Linux containers."
elif [ "$arch" != "$IMAGE_ARCH" ]; then
    blocked "the daemon runs $arch containers; this package's image was built for $IMAGE_ARCH." \
        "Ask the platform operator for a package built for $os/$arch. Emulation was not tested."
else
    ok "platform: the image's $IMAGE_OS/$IMAGE_ARCH matches"
fi

finish
