# Retrospective scoring and window accounting

WP-0020 /002 uses Python's standard library. The author of this analysis has no routing or mapping authorship. The evaluator is frozen on synthetic and WP-0015 development controls before any H/A scoring join. Both routed predictions must have an immutable Git commit and the coordinator must release scoring before replay.

## Scoring

For H use h-r1-ab once. For A use a-recovery-ab once. Check every consumed archive file against the WP-0015 blind inventory for that run or its pre-inference truth/raster commitment. Recheck every consumed archive digest after processing. Verify the route's manifest hash, the exact Windows prediction used to select, the primary timing identities and per-page source and RGB links. Reparse each original ordinary native raw page with the pinned WP-0015 parser and check equality to the original prediction. Apply only the frozen title-level header correction from 0186467670074761a777602d77b53deff3451300. Score all three arms with the byte-pinned WP-0015 score.py.

Each truth-addressed line and each table cell occurs once in the region view. The critical view uses the scorer's own critical token decision on prose lines and its full-cell comparison on critical cells. The two views overlap and their counts must be kept separate. A marker pass on a private copy of original Windows table entries and existing word spans changes text alone and runs the same scorer layout. The marker output shows every reference to which a candidate actually contributed, including unmatched and multiple hits. This avoids assuming that observed table and WinRT line ordinals are printed reference ordinals. No marker reaches a scored prediction.

All transitions use raw correctness. Existing flags and newly added flags are reported independently. A substitution may emit the original value. Report selector-level and critical-location-level coverage separately. A label-positive printed reference uses the same predicate on the printed prose line or the header above a printed body cell. A noncritical printed title can match this predicate. Report unmatched candidates, candidates on already-correct regions, candidates with no critical target, candidates without a critical error, and candidates without a native-right critical opportunity as distinct definitions. Each opportunity is attributed after scoring to an actual recovery, uncovered location, unresolved binding or substituted reading that remained wrong. Where several candidates touch a reference, any substitution takes precedence in the aggregate and every contributing ID stays in the evidence. A scorer-derived perfect region choice is a retrospective ceiling.

Count all printed empty cells and all correct-to-wrong changes at such cells. JSON null is a missing read. Count all expected normalized values with an internal space in separate cell, line and critical-value views. Inspect each previously correct spaced region that became wrong for actual spacing damage. This conservative witness list also catches lexical damage on a spaced line. The scorer preserves token separation and normalizes runs of whitespace. Typography or exact inter-word gap widths are outside its resolution.

## Time

The observed Windows clock runs from primary request acceptance to committed complete prediction after warm-up. For native, use the same run's recorded first/last page and engine begin/end for every available three-page window, including a possible short final window. Request each selected window once. Report triggered pages and all purchased pages separately. For a conservative serial floor add the complete Windows time to engine.read durations of the purchased windows. For a fuller serial estimate, assign each native window its actual interval from the preceding window's last page commit to its own last page commit. The first starts at request acceptance and the terminal window ends at document commit. These disjoint intervals sum exactly to the native whole-document clock. They include the rendering and publication in each interval. An edge window can carry document setup or final serialization costs that a sparse run would place elsewhere.

Compare the serial floor and segment model with two seconds per page, including Windows. An engine floor above the target is sufficient to call the serial design over budget. Neither sum measures a combined selective run. Both exclude selection, cross-engine dispatch, binding and routed-result persistence. They assume resident engines, the archived native window composition and serial execution. They do not include service startup, new hardware measurements, warm-up, queuing or model load.

## Run

Execute the following from the analysis worktree with two unused output directories. The scratch directory retains all six complete frozen-scorer outputs and the two actual corrected-native prediction inputs. The two Windows inputs pin to the historical archive and the two routed inputs pin to their Git blobs. Only H/A are read.

```powershell
python -B docs/research/WP-0020/analysis/check.py
python -B docs/research/WP-0020/analysis/replay.py --archive "$env:USERPROFILE/eLedgerCare-Speed/WP-0015/review" --route-commit ROUTED_PREDICTIONS_SHA --scratch ../wp0020-data/analysis/run1 --out docs/research/WP-0020/analysis/evidence
```

Each family's published inputs.json records hashes of all private scorer outputs, common code and inputs. Its summary.json gives transitions, denominators, score counts and matched clocks. Its fields.json retains each location's flags, missing states, critical and full-region outcomes, printed label status, candidate joins, separate selection diagnostics, and literal scored witnesses on reading changes and native opportunities or risks. Full truth files remain in their approved archive.
