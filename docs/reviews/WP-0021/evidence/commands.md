# Independent execution record

The reviewer used Windows, CPython 3.12.10 and Git 2.55.0.windows.1 from the `scope21-review` worktree. The existing WP-0005 Python supplied Pillow 13.0.0 and NumPy 2.2.6. All generated files under `$d` belong to the reviewer. The exports each contained only the listed paths. Commands below share these values.

```powershell
$d = '../wp0021-data/reviewer'
$py = 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe'
$pub = "$d/public/docs/coordination/WP-0021"
$pri = "$d/primary/docs/coordination/WP-0021"
$open = "$d/unsealed/docs/coordination/WP-0021"
$code = 'docs/reviews/WP-0021'
```

| Check | Result |
| --- | --- |
| Extracted all ten pages of the supplied PDF with `pypdf.PdfReader`, compared its file SHA-256 using `Get-FileHash`, inspected original Git objects for `visual.py` and `formats.py`. | Supplied digest matched. Verified blob IDs and byte SHA-256s are in [detector.json](detector.json). |
| Exported the reserved observable streams, PNGs and freeze metadata, then the primary predictions, with the listed `git archive` and `Expand-Archive` commands below. | Five streams, ten rasters and ten prediction files exported. |
| Independently ran the frozen detector and the frozen reader on fresh scratch before opening the key. | Both exited 0. Six reviewer-created PNG controls passed. The harness checked unchanged input objects, all page-two row receipts, twelve causal prefixes and forty-five altered literal words in each mode. A runtime audit hook checked the in-memory binding function for filesystem/process/network access. |
| Ran checker against released answers, matched against every source line, and compared each case and aggregate to the originally frozen scorer. | An initial reviewer assertion demanded entire threshold masks match. It failed at line 129 on 72 pixels in the page-two twin pair. Corrected reviewer checker at `c8fcbc301c88c144f4e9eda48b097b15def42cb5` uses equality of the actual binder input and records pixel differences separately. Final reconciliation exited 0. Source and released predictions stayed pinned. |
| Verified all ten entire prediction files against corresponding Git blobs at author freeze `263f7263d654faedb17be096699c47d6050315ab` and coordinator freeze `91b8f778cc4bea4c804a0809cdff423e4b107fa1`. | Every file matched byte-for-byte. Files and digests appear in [reconciliation.json](reconciliation.json). |
| Compared rebuilt five JSON, ten PNGs, and answer key against the committed bytes and pre-freeze SHA-256 receipts. Compared generator SHA-256 against pre-freeze commitment. | All matched. [Regeneration](regeneration.json) |
| Compared stock scorer complete output file to `git show 66e9cb7da495f8d65bf6eecb4db7b2b8be3e7579:docs/coordination/WP-0021/primary-scores.json`. | Byte-identical, SHA-256 `247b933d8f31fea6a2c70d23809e6b41c5b12eb6bb7bb0d6bc78cbee5c254cc4`. |
| Inspected author candidate, tests and README. Executed author's unit suite in separate scratch. | Nine of nine passed. Git diff of pre-freeze author and coordinator changes contains research and coordination files. |

```powershell
git archive --format=zip -o "$d/pinned-observables.zip" 7a430d242d0c1eab168281f3865e9976f9ae6f02 docs/coordination/WP-0021/evidence docs/coordination/WP-0021/input-receipt.json
Expand-Archive -LiteralPath "$d/pinned-observables.zip" -DestinationPath "$d/public"
git archive --format=zip -o "$d/frozen-predictions.zip" 91b8f778cc4bea4c804a0809cdff423e4b107fa1 docs/coordination/WP-0021/evidence/predictions docs/coordination/WP-0021/prediction-freeze.json
Expand-Archive -LiteralPath "$d/frozen-predictions.zip" -DestinationPath "$d/primary"
& $py -I -B "$code/replay_reader.py" 613a5ff92e9dd6783b8950529fbda76f6c21e9d3 "$pub/evidence/inputs" "$d/reader-decisive"
& $py -I -B "$code/replay_detector.py" "$d/detector-decisive" --input "$pub/evidence/rasters"
git archive --format=zip -o "$d/unsealed.zip" f858ecf538a371161b5fda5c1e2de235f38de212 docs/coordination/WP-0021/fixtures.py docs/coordination/WP-0021/answers.json docs/coordination/WP-0021/rebuild.json docs/coordination/WP-0021/score.py
Expand-Archive -LiteralPath "$d/unsealed.zip" -DestinationPath "$d/unsealed"
& $py -I -B "$open/fixtures.py" . "$d/regenerated"
python -I -B "$open/score.py" --inputs "$pub/evidence/inputs" --key "$open/answers.json" --predictions "$pri/evidence/predictions" --out "$d/stock-score.json"
git archive --format=zip -o "$d/author-src.zip" 613a5ff92e9dd6783b8950529fbda76f6c21e9d3 docs/research/WP-0021
Expand-Archive -LiteralPath "$d/author-src.zip" -DestinationPath "$d/author-src"
python -B "$d/author-src/docs/research/WP-0021/test_read_scope.py" -v
& $py -I -B "$code/reconcile.py" "$pub/evidence" "$open/answers.json" "$d/reader-decisive" "$d/detector-decisive/detector.json" "$pri/evidence/predictions" "$d/stock-score.json" "$d/independent-score.json"
```

Two earlier development detector invocations used separate `control-smoke` and `detector-observations` directories. Both passed. The decisive prediction and detector source freeze was `1181da64488651d91b33b61096c947aee5911118`. Only score reconciliation changed at the later checker freeze. The reviewer invoked no OCR, GPU, product application, customer-data, Packet B or model workload.
