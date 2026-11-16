# Saved-output diagnosis protocol

Owner: eld-mapping-author. Initial base `5e1241d6d365d664f12619d415f48ec3d3b7ddca`; supplied authority `22b88bc32d053231678aef88e6b7f76d3e61910a` was fast-forwarded once before diagnosis. Native Codex session, xhigh explicitly requested; actual backend checkpoint and effort are not separately exposed. No other author identity is claimed.

The helper is frozen in Git before the decisive command:

```powershell
python -I -B docs/research/WP-0009/eld-mapping-author/diagnosis/diagnose.py --out docs/research/WP-0009/eld-mapping-author/diagnosis/results
```

Only standard-library host Python and the accepted pure `corpus`, `native`, `score`, and `typed_values` modules are imported. No runtime/model imports, services, downloads, GPU execution, transformed PDF rendering, or fresh reserved corpus access occur. Reads are finite paths in the original admitted corpus and retained B0 packets. The old heldout partition is now exposed regression data. No proposed mapping is implemented or scored.

The unchanged score objects for dev13 and heldout13 must equal the original packets, including raw hashes, before diagnosis succeeds. The helper reproduces the original split/family summaries and keeps all document, field, cell, row, absence, page, sentinel, adjacency and cross-page-link denominators. The original failure uses the same unavailable-output empty prediction for accounting only; it is not an observed empty model output. Recovery is rescored separately and never pooled into primary counts.

`input-inventory.json` lists every consumed helper input with bytes, SHA256 and Git blob. The missing original raw path is explicit. Clean-parent PDFs and hybrid source declarations are the frozen reference construction inputs. Transformed PDF bytes and token IDs are not needed for this CPU text/scoring diagnosis and are not newly adjudicated. The accepted baseline source tree and relevant pure files must retain the exact accepted identity.

Every expected field/cell receives an item ID, original printed/typed credit, local causal categories and residual unknown status. Categories are **nonexclusive affected slots**, not a partition, causal percentage, or independent sample count. Printed-correct items with failed typed conversion remain included. Rows, absences and links retain original denominators; field/cell cause counts do not claim complete attribution for those other metrics.

Evidence standards:

- A correct string appearing somewhere in raw output is a search aid only. It does not prove the right field, row, page, or complete recognition. Raw native locations use one-based pages and zero-based block/row/cell indices; offsets are Unicode character offsets, not byte offsets.
- Same-row field cases require an exact known label and an exact expected adjacent value at a specific native location. This diagnostic comparison uses expected answers and must never enter a production predictor. It establishes the local mapping failure, not future implementation accuracy.
- Table cases use manually inspected finite table/header bindings and a unique row key on the expected page. They retain exact native values, header quotes and expected item IDs. Character mismatches in those bound rows are recognition differences as well as unmapped items. Missing row keys alone do not prove text omission; F08 continuation omission requires the inspected table to contain only its header and E07/E08 keys to be absent from the entire raw output.
- Native colspan structure and parse-invalid recovery are separate from recognition. The helper never expands spans, repairs text, changes document eligibility or awards proposed credit.
- All remaining failed field/cell slots are explicitly unadjudicated. These unknowns are not assumed to be either perfect reading or recognition failures.
- Expected absence slots retain actual candidates, violations and label locations. Unmapped/unverified slots are not inventions; zero detected violations cannot establish comprehensive absence of invented text. Supported wrong-unit counterfactuals illustrate numeric-only typed semantics and are excluded from all observed denominators.

Exploratory inspection preceded this freeze. It established packet schemas, source behavior and finite raw/table bindings. The helper was syntax-checked without executing diagnosis. If decisive execution fails, retain its log and diagnose the failure; any helper correction needs a new committed freeze before rerunning. No source adjustment may rescue a score mismatch.
