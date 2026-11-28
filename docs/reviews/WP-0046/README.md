# WP-0046 eld-rd-reviewer Stage 0 review area

Author: eld-rd-reviewer (local Claude Code, claude-opus-5-5, high effort). Everything here is constructed by this author or derived from the pinned bundle's public repository extracts. It contains no private handoff pages, host paths, provider transcripts or copied PDFs.

| Path | Role |
| --- | --- |
| `challenges/cases.json` | 49 label-free constructed inputs. They contain no answers and can be fed to any candidate implementation. |
| `expectations/expected.json` | Hand-derived full return objects, frozen and committed before any execution. Reading notes name the open interpretations. |
| `expectations/tool-predictions.json` | Predicted outputs of the supplied checker and the two audit tools, frozen before execution. |
| `expectations/reference-model-predictions.json` | Inspection-only predictions for the bundle's `amendments.py` functions on selected challenges. Not executed. |
| `tools/evaluate.py`, `tools/compare.py` | Independent evaluator (standard library only, no bundle imports) and a field-by-field comparator. |
| `tools/audit_register.py`, `tools/archive_checks.py` | Register/source audit using `ast` only, and an independent recomputation of the checker's quantities and the archived page masks. Each takes the extracted bundle directory as its argument. |
| `results/` | Outputs and command records, committed after the freeze. |
| `first.md` | First independent position with two separate verdicts. |

Reproduce: run `python -I tools/evaluate.py challenges/cases.json OUT.json`, then `python -I tools/compare.py expectations/expected.json OUT.json`. Run the audit tools as `python -I tools/<tool>.py BUNDLE_DIR`. Separately, from outside the bundle directory, run `python -I BUNDLE_DIR/check.py`.

The evaluator and its expectations share an author, so their agreement only shows internal consistency. It is not independent acceptance of the fixtures.
