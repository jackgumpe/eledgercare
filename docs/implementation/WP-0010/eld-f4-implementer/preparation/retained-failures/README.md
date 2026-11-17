# Retained Pre-Freeze Interactive Setup Failures (`WP-0010` `eld-f4-implementer` Preparation)

Both failures below occurred during pre-freeze interactive setup of gitignored `.local/` caches before any seed helper existed or was frozen. No product, test, deploy, routing, or database state was mutated by either failure.

1. [`prefreeze-setup-failure-01.txt`](prefreeze-setup-failure-01.txt) (`exit 1`, `2026-11-17T03:28:57-05:00`):
   - **Cause**: The default tool shell on Windows is Windows PowerShell 5.1 (`powershell.exe`), whose `Set-Content -Encoding` enum does not define PowerShell 7's `utf8NoBOM` value when writing `.local/nuget/offline.nuget.config`.
   - **Resolution**: Executed PowerShell 7 (`pwsh.exe -NoProfile -File`), matching `#Requires -Version 7.0` in `deploy/dev/postgres/*.ps1`.

2. [`prefreeze-setup-failure-02.txt`](prefreeze-setup-failure-02.txt) (`exit 1`, `2026-11-17T03:29:30-05:00`):
   - **Cause**: Passing a PowerShell `@"..."@` here-string inside `powershell.exe` -> `pwsh -NoProfile -Command '...'` stripped inner double quotes across Win32 command-line argument quoting (`ParserError` at `@`).
   - **Resolution**: Invoked `.scratch/bootstrap_local.ps1` directly via `pwsh -NoProfile -File` (`exit 0`), and removed `.scratch/bootstrap_local.ps1` during final `.scratch/` cleanup after decisive frozen seed verification.
