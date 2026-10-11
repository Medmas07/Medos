#!/bin/sh
# Installation helper of Hospital Node @NODE_REF@ (HC-221).
#
#   ./install.sh --data-dir DIR       verify the package and the data, load the image, start
#   ./install.sh --data-dir DIR --verify-only    the same checks, without Docker
#
# It never installs software and never asks for administrator rights. It needs Docker
# Engine with the Compose plugin, already installed by the hospital's administrator.
set -eu

NODE_REF="@NODE_REF@"
PORT="@PORT@"
IMAGE_REF="@IMAGE_REF@"
IMAGE_IDS="@IMAGE_IDS@"
IMAGE_ARCHIVE="@IMAGE_ARCHIVE@"
DATA_FILES="@DATA_FILES@"
# How long the Node must stay up after starting. Not a health check (HC-223).
STARTUP_SECONDS=8

fail() {
    echo "install.sh: $1" >&2
    exit "${2:-1}"
}

usage() {
    sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
}

DATA_DIR=""
VERIFY_ONLY=0
while [ $# -gt 0 ]; do
    case "$1" in
        --data-dir)
            [ $# -ge 2 ] || fail "--data-dir needs a directory." 2
            DATA_DIR="$2"
            shift 2
            ;;
        --verify-only)
            VERIFY_ONLY=1
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            usage >&2
            fail "unknown argument: $1" 2
            ;;
    esac
done

cd "$(dirname "$0")"

# 1. Every file of the package is the one the platform built.
echo "Checking the package's checksums..."
if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c --quiet SHA256SUMS || fail "a file of the package is corrupted or was changed."
elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -c SHA256SUMS >/dev/null || fail "a file of the package is corrupted or was changed."
else
    fail "neither sha256sum nor shasum is available to check the package."
fi

# 2. The hospital's own data, which the package never carries.
[ -n "$DATA_DIR" ] || fail "--data-dir is required: the directory holding this hospital's data files." 2
[ -d "$DATA_DIR" ] || fail "$DATA_DIR is not a directory." 2
missing=""
for file in $DATA_FILES; do
    [ -f "$DATA_DIR/$file" ] && [ -r "$DATA_DIR/$file" ] || missing="$missing $file"
done
[ -z "$missing" ] || fail "missing from $DATA_DIR:$missing" 2
DATA_DIR="$(cd "$DATA_DIR" && (pwd -W 2>/dev/null || pwd))"
echo "Package and data checked."

if [ "$VERIFY_ONLY" -eq 1 ]; then
    exit 0
fi

# 3. Docker must already be there; this helper never installs it.
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    fail "Docker Engine with the Compose plugin is required and was not found.
This helper does not install it. Ask the host's administrator to install it:
https://docs.docker.com/engine/install/ — then run install.sh again." 3
fi
docker info >/dev/null 2>&1 || fail "Docker is installed but its daemon does not answer. Start it, then run install.sh again." 3

# 4. The image comes from this package, and must be the one the manifest names.
echo "Loading $IMAGE_REF..."
docker load -q -i "$IMAGE_ARCHIVE" >/dev/null || fail "docker load failed for $IMAGE_ARCHIVE."
image_id="$(docker image inspect --format '{{.Id}}' "$IMAGE_REF")" || fail "$IMAGE_REF is not available after loading."
case " $IMAGE_IDS " in
    *" $image_id "*) ;;
    *) fail "$IMAGE_REF is $image_id, not the image this package was built with ($IMAGE_IDS)." ;;
esac

# 5. Local configuration, then start.
printf 'HOSPITAL_NODE_DATA_DIR=%s\n' "$DATA_DIR" > .env
docker compose up -d || fail "docker compose up failed."

# 6. The Node stops at startup on an invalid configuration or on another
# organization's records; do not report a crash loop as an installation.
container="$(docker compose ps -q hospital-node)"
seconds=0
while [ "$seconds" -lt "$STARTUP_SECONDS" ]; do
    sleep 1
    seconds=$((seconds + 1))
    state="$(docker inspect --format '{{.RestartCount}} {{.State.Running}}' "$container" 2>/dev/null)" || state="gone"
    if [ "$state" != "0 true" ]; then
        docker compose logs --tail 5 hospital-node >&2
        docker compose down >/dev/null 2>&1
        fail "the Node stopped at startup (log above), so it was removed. Check --data-dir." 4
    fi
done

echo "Hospital Node $NODE_REF started and stayed up for ${STARTUP_SECONDS}s, on 127.0.0.1:$PORT only."
echo "Check it by hand: curl -s http://127.0.0.1:$PORT/health (deployment health checks are HC-223)."
echo "Stop it with: docker compose down, from this directory."
