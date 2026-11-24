# Wolf-Coin Desktop v0.8.0 — native Chromium and signed application backend

Electron 37.2.6 hosts the nine-screen Wolf-Coin interface, native Wolf
Browser, owner-held D-XQT runtime and persistent isolated website profiles.
Each website session has an independent Chromium storage partition. Wolf
Browser offers normal website controls and does not apply product-category
restrictions to financial website controls.

The desktop host starts the existing Wolf-Coin 0.1.0a10 backend as a private
Python child process using authenticated wolf.app.request.v1 /
wolf.app.bridge.v2 stdin/stdout messages. SQLite records persist in the
application's private host data directory. Python 3.11+ must be available
on the host (or specified by WOLF_BACKEND_PYTHON).

Before development, locally stage the owner-held backend source without
checking it into this public frontend branch:

  python3 apps/wolfcoin-desktop/stage-backend.py --source /path/to/backend-worktree

Then assemble the owner-held D-XQT payload into the generated UI using
apps/wolfcoin-ui/assemble.py; the generated HTML and staged Python runtime
are ignored by Git. npm start runs the host from its assembled app directory.

Verified on KRATOS: actual package launch, nine tabs, fixture account signup,
login, isolated sessions, browser action tools, native signed financial state,
history, logout and restart, two-platform Sync All, candidate comparison and
UI screenshot capture. The Windows portable archive has passed structure
and source checks, but Windows runtime acceptance remains to be performed.
Real platform/OAuth/provider-specific acceptance is separate.
