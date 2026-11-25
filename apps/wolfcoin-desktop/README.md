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


The local page classifier can identify a betting/trading category from
visible headings as well as price/odds controls; categories and market
opportunities are separate observations. Public landing-page tests do not
establish site-specific authenticated market support.

## Windows 0.9.1 self-contained host and installer

Windows portable/NSIS developer distributions include the official
CPython 3.14.7 embeddable interpreter under resources/python. The host
selects it automatically unless WOLF_BACKEND_PYTHON is explicitly supplied;
the owner-controlled Python backend modules are found in the loose
resources/app/backend-runtime or ASAR-unpacked resources directory.

Stage the official CPython redistributable (SHA-256
d297e5ff019966817ad8502465176139f2d3d840fa4ed84b13bed399a6ab1f15)
using apps/wolfcoin-desktop/stage-windows-python.py.
The original Python LICENSE.txt is included in the Windows payload.
The staged interpreter and backend code are not tracked in public Git.

The reproducible per-user NSIS setup is defined by
apps/wolfcoin-desktop/installer/wolfcoin-windows.nsi.in and
installer/build-nsis.py. The script requires the staged, owner-approved
Windows portable directory and an NSIS compiler. The installer does not
erase the separate per-user app state during uninstall.
The installer is unsigned development output until owner-issued signing
keys and end-to-end installation acceptance are supplied.

ATHENA's opt-in WOLF_BACKGROUND_QA test passed fresh and restore flows
while its game retained foreground ownership. The bundled Python interpreter
was exercised without a host installation dependency. See
docs/frontend/PROOF_AND_LIMITATIONS_2026-11-23.md.
