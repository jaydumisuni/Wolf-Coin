#!/usr/bin/env bash
# Owner-run KRATOS paper bootstrap. This does not relax Oracle or Patrol security.
set -Eeuo pipefail
ROOT=/home/kratos/projects/Wolf-Coin
REMOTE=https://github.com/jaydumisuni/Wolf-Coin.git
BRANCH=work/wx-tenfold-cookpit-20261123
DB="$HOME/.local/state/wolf-coin/paper.db"

if [[ "$(id -un)" != "kratos" ]]; then echo "Must run as kratos, not root" >&2; exit 2; fi
if grep -Eq '^NoNewPrivs:[[:space:]]*1$' /proc/self/status; then
  echo "Use a native KRATOS login terminal, not Oracle's restricted subprocess" >&2
  exit 2
fi
command -v patrol >/dev/null
command -v git >/dev/null

if [[ ! -d "$ROOT" ]]; then
  sudo -v
  patrol init-project Wolf-Coin --remote "$REMOTE"
fi
[[ "$(patrol route Wolf-Coin)" == "$ROOT" ]] || { echo "Patrol registry missing" >&2; exit 3; }
[[ "$(stat -c '%U' "$ROOT")" == "kratos" ]] || { echo "Unexpected project owner" >&2; exit 3; }
python3 - "$ROOT/.patrol-project.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))["id"]=="Wolf-Coin"
PY
if git -C "$ROOT" remote get-url origin >/dev/null 2>&1; then
  [[ "$(git -C "$ROOT" remote get-url origin)" == "$REMOTE" ]] || exit 3
else
  git -C "$ROOT" remote add origin "$REMOTE"
fi
git -C "$ROOT" fetch --no-tags origin \
  'refs/heads/main:refs/remotes/origin/main' \
  "refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=all)" ]] || {
  echo "Existing local modifications must be reviewed first" >&2; exit 3;
}
if [[ "$(git -C "$ROOT" branch --show-current)" != "$BRANCH" ]]; then
  if git -C "$ROOT" show-ref --verify --quiet "refs/heads/$BRANCH"; then
    echo "Existing branch requires manual currentness review" >&2; exit 3
  fi
  git -C "$ROOT" switch -c "$BRANCH" --track "origin/$BRANCH"
fi
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$(git -C "$ROOT" rev-parse "origin/$BRANCH")" ]] || exit 3
[[ "$(git -C "$ROOT" hash-object wolf_gateway/resident.py)" == 17bb01f909e9d49a95cd509cf54ec1cc1c06ae45 ]] || exit 3
[[ "$(git -C "$ROOT" hash-object tests/test_resident.py)" == 2c525f6eb21e51377775a86629fb3b6205a648a1 ]] || exit 3
[[ "$(git -C "$ROOT" hash-object pyproject.toml)" == ecbf5faf02dbf3ae2eca431df47ca534ffa65665 ]] || exit 3
cd "$ROOT"
python3 -m pytest -q
mkdir -p "$(dirname "$DB")"
chmod 700 "$(dirname "$DB")"
for domain in sports trading; do
  python3 -m wolf_core.paper_operator --db "$DB" --domain "$domain" --account pilot-1 init
  python3 -m wolf_core.paper_operator --db "$DB" --domain "$domain" --account pilot-1 deposit --amount 100 --event-id "virtual-start-$domain"
done
python3 -m wolf_gateway.resident --db "$DB" --check
echo "PAPER READY: run python3 -m wolf_gateway.resident --db $DB"
echo "Read-only sports: http://127.0.0.1:8765/sports"
echo "Read-only trading: http://127.0.0.1:8765/trading"
echo "No real-money execution enabled."
