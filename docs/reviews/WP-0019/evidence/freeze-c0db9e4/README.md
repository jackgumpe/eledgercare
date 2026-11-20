# WP-0019 reviewer freeze evidence (eld-rd-reviewer)

- **Frozen preregistration and source:** `c0db9e4363eedfd01913207fa1a972424cc60caa` on `review/wp-0019-fixed-crop`, pushed and verified on `origin`. It is based on `fc15d1bd3af1b4c7dfbfbf1eac2680b9ae9ac1af`.
- **`selftest.json`** (SHA-256 `a6252f64d3ea537b02c7d06ae19244daef3f6dd818428797e85692b0f2292a33`):
  - **What ran:** `review_selftest.py` at the frozen tree, `python -I -B` from the WP-0005 venv, output to `wp0019-data/review/frozen-c0db9e4-selftest`.
  - **Result:** 19/19 PASS. Every recorded source SHA-256 equals its blob at `c0db9e43`.
  - **What it is:** script validation on the WP-0015 archive copies and on constructed controls. It is **not** a WP-0019 result, and it ran no WinRT or OCR.
- **`env.json`** (SHA-256 `b02181cf2264a052588ffa33fa8ab1a53eaf05ae70ab8afaf245da267a50fae2`):
  - **What it is:** the freeze-time `review_checks.py env` snapshot, taken from files and the registry only.
  - **Comparison:** the replay compares against it with `--expect`.
  - **Pre-commit provenance:** it was taken during pre-freeze development with a functionally identical `env` subcommand. The later pre-freeze edits to that file changed `inputs`, `geometry`, `identity`, `timing`, `audit` and `expect-bgra`, not `env`.
- **`env-frozen-code.json`** (SHA-256 `d53b5c8c489a899deabed6b0d5e5d3cb98378e589c29ae3820dd1f800ae0d603`):
  - **What ran:** the frozen-code `env --expect env.json`, after the freeze.
  - **Result:** E5 PASS. The OCR assets and the OS build/UBR equal the reference snapshot.
- **Pre-freeze runs kept in scratch only:** `prefreeze-selftest-1` through `-5` (described in PREREGISTRATION §0).
