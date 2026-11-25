#!/usr/bin/env bash
# Real .deb registration, headless browser/backend testing and removal in a
# disposable unprivileged dpkg database. Never edits host /var/lib/dpkg.
set -euo pipefail
test $# -ge 1 || { echo "Usage: $0 /absolute/path/wolf-coin.deb" >&2; exit 2; }
PKG=$(realpath "$1")
APPDIR=$(cd "$(dirname "$0")/.." && pwd)
TESTROOT=$(mktemp -d /tmp/wolf-dpkg-acceptance-XXXXXX)
ROOT="$TESTROOT/root"
PORT=${WOLF_QA_CDP_PORT:-13972}
FIXTURE_PORT=${WOLF_QA_FIXTURE_PORT:-44671}
if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/json" >/dev/null 2>&1; then
 echo "DevTools port $PORT is occupied; supply WOLF_QA_CDP_PORT" >&2;exit 3
fi
mkdir -p "$ROOT/var/lib/dpkg"/{updates,info,alternatives,triggers,parts}
touch "$ROOT/var/lib/dpkg/status"
APP_PID=
FIXTURE_PID=
cleanup() {
  if test -n "$APP_PID"; then kill -- "-$APP_PID" 2>/dev/null || kill "$APP_PID" 2>/dev/null || :; fi
  if test -n "$FIXTURE_PID"; then kill "$FIXTURE_PID" 2>/dev/null || :; fi
}
trap cleanup EXIT
fakeroot dpkg --force-depends --instdir="$ROOT" --admindir="$ROOT/var/lib/dpkg" \
 --log="$TESTROOT/dpkg.log" --install "$PKG" >"$TESTROOT/dpkg-install.log" 2>&1
dpkg-query --admindir="$ROOT/var/lib/dpkg" -W wolf-coin | tee "$TESTROOT/status.txt"
# An isolated fakeroot install executes as the package owner, which can hide
# a root-installed 0600 JS/HTML defect. Normal users must be able to read
# the application source/resources after a real system installation.
unreadable=$(find "$ROOT/opt/wolf-coin/resources/app" "$ROOT/usr/share/applications" \
 -type f ! -perm -004 -print -quit)
if test -n "$unreadable";then
 echo "Package contains root-only unreadable resource: $unreadable" >&2;exit 4
fi
echo "WOLF_DEB_WORLD_READABLE_RESOURCE_GATE_PASS"
env WOLF_FIXTURE_PORT="$FIXTURE_PORT" node "$APPDIR/test_fixture.cjs" >"$TESTROOT/fixture.log" 2>&1 &
FIXTURE_PID=$!
setsid env WOLF_TEST_MODE=1 WOLF_TEST_USER_DATA="$TESTROOT/app-profile" \
 xvfb-run -a "$ROOT/opt/wolf-coin/wolf-coin" \
 --no-sandbox --disable-gpu "--remote-debugging-port=$PORT" \
 "$ROOT/opt/wolf-coin" >"$TESTROOT/electron.log" 2>&1 &
APP_PID=$!
for i in $(seq 1 40); do
 if curl --max-time 2 -fsS "http://127.0.0.1:$PORT/json" >/dev/null 2>&1; then break; fi
 sleep 0.2
done
curl --max-time 5 -fsS "http://127.0.0.1:$PORT/json" >/dev/null
WOLF_TEST_CDP_PORT="$PORT" WOLF_FIXTURE_URL="http://127.0.0.1:$FIXTURE_PORT/login" \
  node "$APPDIR/tests/native_ui_e2e.mjs" | tee "$TESTROOT/native-ui.log"
WOLF_TEST_CDP_PORT="$PORT" \
  node "$APPDIR/tests/native-backend-ui.e2e.mjs" | tee "$TESTROOT/native-backend-ui.log"
kill "$APP_PID" 2>/dev/null || :
APP_PID=
fakeroot dpkg --force-depends --instdir="$ROOT" --admindir="$ROOT/var/lib/dpkg" \
 --log="$TESTROOT/dpkg-remove.log" --remove wolf-coin >"$TESTROOT/dpkg-remove.stdout" 2>&1
test ! -e "$ROOT/opt/wolf-coin/wolf-coin"
test -d "$TESTROOT/app-profile"
echo "WOLF_LINUX_DPKG_INSTALL_LAUNCH_REMOVE_PASS $TESTROOT"
