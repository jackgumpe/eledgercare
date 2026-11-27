# Reproduce the independent opening

Use the original role worktree for the pinned live runtime path bindings. All following commands operate offline on static artifacts. The private raw runs and retained HMAC keys are needed to recheck each actual custody instance. They remain under the corresponding role, in the current user's eLedgerCare-Speed/WP-0045 directory. The public row comparisons and paper-specific amendments can be reviewed separately. Original third-party source inputs and full private editions require the local access recorded by the coordinator.

Use a new reviewer scratch and preserve the archive directory hierarchy. Let W be eld-rd-reviewer/opened, INPUT be coordination/inputs and ROOT be the repository root. Git-archive the listed folders into W/<name> with paths relative to ROOT.

| Name | Git revision | Folders |
| --- | --- | --- |
| fixture | 261f36893db27ee5ad8627366c3842fa140c8383 | docs/fixtures/WP-0045, docs/coordination/WP-0045 |
| author | 2514ca6c7d31f417b0617ec230037c688c610e52 | docs/research/WP-0045, docs/research/WP-0044, docs/coordination/WP-0045, docs/coordination/WP-0044 |
| edition | 2c9637e465ed0ca6e9ce4d023aba3e5c2be548bf | docs/editions/WP-0045 |
| repack | a1d0d128301199a6b7a10b1bdcef80341fdbcaeb | docs/editions/WP-0045 and docs/coordination/WP-0045 |
| repack-final | 5e22e53f802b96e46a9e8154fb9c0621e531ae05 | docs/editions/WP-0045 and docs/coordination/WP-0045 |
| corrected-fixture | fc46492bd115a8547b155b0e71c919ff375c7edc | docs/fixtures/WP-0045 and docs/coordination/WP-0045 |

Let F be W/fixture/docs/fixtures/WP-0045, E be W/edition/docs/editions/WP-0045, P be W/repack-final/docs/editions/WP-0045, O be eld-fixture-claude/oracle, and R be W/corrected-fixture/docs/fixtures/WP-0045/reconciliation. The full frozen map for each implementation, including the independent reviewer, is under the respective blind commit. Run the following with CPython 3.12.10, pypdf 6.16.2, fixed PYTHONHASHSEED=0 for assembly. Commands shown use the symbols above as path arguments. Historic and correction inputs include all authentic archive members.

    python -I -B F/build_fixtures.py --check
    python -I -B O/oracle.py --fixtures F --repo ROOT --out W/oracle-rerun
    python -I -B O/selftest.py --fixtures F --reference INPUT/edition02
    python -I -B E/historical.py INPUT/Edition02-source.zip W/historical
    python -B E/trial.py public W/public-trial
    python -B opening/check.py
    python -B opening/a2.py
    python -I -B R/oracle_r1.py --repo ROOT --out W/reconciliation-repeat
    python -I -B R/regression.py --out W/reconciliation-repeat/regression-results.json
    python -B P/build.py W/assembled-original --inputs INPUT
    python -B P/navigation/package.py INPUT W/assembled-original/Edition02.1-source.zip P/papers W/assembled-final
    python -B P/navigation/audit.py INPUT P/papers W/assembled-final W/final-supplied-audit.json
    powershell -NoProfile -File opening/render.ps1 -Directory E/papers -Output W/public-render
    powershell -NoProfile -File opening/render.ps1 -Directory INPUT -Output W/original-render
    powershell -NoProfile -File opening/render.ps1 -Directory W/assembled-final -Output W/complete-render
    python -B opening/papers.py
    powershell -NoProfile -File opening/pixels.ps1 -Work W -Result opening/pixels.json

For the repeat observation use the same source PDF files and renderer with distinct destinations repeat-public, repeat-original and repeat-complete. Compare each page's PNG file to its matching initial image and compare the complete pages with their amendment or precursor counterparts. render-repeat.json lists each changed image by item. Exact encoded equality in the second comparison directly implies equal decoded pixels for that observation. The first comparison's decoded differences are recorded separately.

The reviewer sourced worker, supervisor and observer tokens at the medium entry. The static review shell was high integrity. Digest checks, PDF rendering, source inspection and HMAC recomputation performed after opening do not measure a live token, a caller or prior handle liveness. No new native attempt is part of these commands.
