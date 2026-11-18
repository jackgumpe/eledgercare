# WP-0015 corpus and common scoring protocol

The three development PDFs and their scoring keys are public to the assigned authors. Each PDF contains one lossless raster per source page. H is a new four-page held-out family. A and B are separate sealed 60-page families. The custodian prepared all six before trial execution. Their inputs and answer keys are separate. All records are synthetic.

## Development inputs

| Folder | Pages | Coverage |
| --- | ---: | --- |
| [dev/short](dev/short/) | 1 | Maintenance note, confusable work ID, decimal pressure reading |
| [dev/dense](dev/dense/) | 1 | Six-column stock grid with printed headers, repeated item rows, empty batch cells, signed and unsigned amounts |
| [dev/boundary](dev/boundary/) | 4 | Dispatch, meter readings, intentionally blank third page, fourth-page release with new critical values |

Within each family, `source.pdf` is the only inference input. `truth.json` is for scoring. `rasters.json` pins the PDF, key and actual PDFium 300-DPI RGB bytes for each page. Every original page is 612 × 792 PDF points. The frozen renderer produces 2550 × 3301 RGB pixels on this pinned build. Check the actual image dimensions when mapping geometry. The [CPU counts](cpu-counts.json) include truth-only diagnostic controls. They measure the evaluator and carry no model accuracy or speed evidence.

## Prediction contract

Write one UTF-8 JSON document per PDF. The following invented single-page output illustrates the required fields. The integer `page` is the original one-based PDF ordinal across all windows. The receiver binds `source_sha256` to the original PDF bytes actually used. A prediction may represent a failure or truncation with its actual `state` and surviving text. An empty successful page has `state: "complete"`, empty text and empty arrays.

```json
{
  "source_sha256": "<64 lowercase hex digits>",
  "pages": [{
    "page": 1, "source_sha256": "<same original PDF hash>", "state": "complete",
    "text": "Shift receipt\nPump P-810\nPart Qty\nSeal 3",
    "spans": [
      {"text": "Shift receipt", "bbox": [36, 40, 131, 61]},
      {"text": "Pump P-810", "bbox": [36, 90, 128, 107], "flagged": false}
    ],
    "tables": [{
      "bbox": [35, 155, 302, 225],
      "rows": [["Part", "Qty"], ["Seal", {"text": "3", "flagged": true}]]
    }]
  }]
}
```

All four coordinates are original PDF points in top-left origin, increasing right/down. For a full-page raster in pixel coordinates, multiply x by PDF width/raster width and y by PDF height/raster height. Undo model resizing, padding, tiles and crops first. `spans` accept individual text lines, words or indivisible cells with real source geometry. `tables` accept the detected table block and printed row order, including header rows, repeated rows and explicit empty strings. A cell string implies `flagged=false`. Use a cell object with a local flag for a genuinely surfaced review state. A nested `page` or `source_sha256` override is inspected for wrong-source associations. Never supply estimator geometry from scoring truth. If geometry is unavailable, leave the affected array empty and retain the full recognized text.

Join the model's visible text in its emitted reading order in `text`, including table headers and cell strings in row-major order. Strip only structural markup, preserve numbers, punctuation, repeats, and case. One adapter definition per output contract must freeze before decisive runs. Keep raw generation, its page delimiters, token IDs, stops, window/source map, transformation, per-page state and the actual durable result independently. An inference process may receive fresh source pixels and its frozen software only. Keys and scoring belong to a separate post-run step.

## Metrics

Run `python -B score.py <truth.json> <prediction.json> --baseline <control-prediction.json> --out <score.json>` from this directory. Omit `--baseline` to score one output. Run `python -B check_score.py` for CPU scorer controls. Python's standard library suffices for both commands.

* CER is the sum of page-local Unicode Levenshtein distances divided by total normalized reference characters. Normalize each page using NFC and collapse whitespace to one space. Preserve case, order, punctuation and decimal placement. Missing pages cost deletions. Foreign, duplicate and extra outputs cost insertions. A hallucination on a blank page costs insertions even when that page contributes zero reference characters. A family with zero reference characters has null CER. Report numerators and denominators by family.
* The scorer consumes source/page pairs in output order. The first attributable instance per ordinal supplies its score. A reordered packet may preserve text accuracy while failing completion. Missing, duplicate, wrong-source, out-of-range, noncomplete and unexpectedly empty pages cannot support a full-document speed claim. A written hallucination on a known blank is separately reported. A speed claim additionally requires matching raw input/output identities and the measured final durable write. JSON cannot attest those runtime events.
* In original-PDF coordinates, direct text spans localize to a cell when the center is inside and all edges are within two points of the printed cell. Words in one region are read left to right. A source table is eligible at intersection-over-union of at least 0.50 with a printed table. Greedy descending IoU, then original order, selects one match per table. Its row and column ordinal determine cell identity. The matched table takes precedence over overlapping span evidence. Ink and cell borders are in the truth. The report retains direct reported span boxes or the reported table box with its row/column address. Block-plus-ordinal evidence locates a value within a table. It does not establish a model-predicted cell rectangle.
* Cell accuracy is exact, position-correct values divided by reference cells plus surplus predicted grid entries. Count every printed header and empty cell. An explicit empty entry can be correct. A missing entry is wrong. Spans without table objects receive cell credit only for localized regions. Unassigned spans remain subject to the full-page CER. With zero reference cells, report null cell accuracy and the extra-cell count. The [scorer](score.py) emits every expected/observed position and whether a critical mismatch was flagged.
* Critical table values require the exact source position and normalized value. Critical prose needs a local text span on the source line and an unambiguous printed identifier or amount. Its digit-bearing tokens must agree in order with the reference line. The line-center tolerance is three points vertically, with at least half of the narrower horizontal interval overlapping and a height cap of 2.5 times the source line height. Report all critical errors, flagged values, extra/missing/wrong links and candidate-new or changed critical errors. Absence of source evidence cannot earn critical credit.
* For changed output on each decisive packet, CER may increase by at most 0.01 and cell accuracy may decrease by at most 0.02 against matched baseline. Null metrics remain N/A. Compare absolute critical and source-link errors for unattended eligibility even if a control made the same error. A comparative budget pass alone cannot qualify an unattended result. Check other limits, complete paired timings, control noise and independent replay separately.
* Exact mode also requires independent token-by-token, EOS/stop, page/window and state parity on the complete matched input. This scorer consumes normalized output. It cannot establish token parity, inference validity, flags actually presented to the operator, CPU/GPU timings, durable-write integrity or product searchability. Audit those against retained raw per-page artifacts.

## Reproduction and custody

The CPU fixture builder and raster audit use the read-only Q0 Python 3.12.10 environment, Pillow 13.0.0, pypdfium2 5.15.2 and PDFium 159.0.8149.0. The builder uses Windows Arial regular `edfbd22a3d088fc2f5d7c79b8c9c732df6dc878a60f0a80be0f92a3c7a634404` and bold `4d59199834e7439c67ea4949407639961060b21b173833f566eb60ac6fd8f5af`. From this directory:

```powershell
$q0 = 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe'
& $q0 -B development.py <empty-output-directory>
& $q0 -B audit.py dev/dense --out <new-audit-file>
```

[Commitments](commitments.json) bind all three sealed originals, truths, rendered-pixel manifests and six authenticated encrypted bundles. Sealed payloads live in the external WP-0015 custody area. Separate DPAPI-protected keys stay with the custodian. This is procedural independence on a shared Windows account. The custodian performed the only pre-freeze integrity round trips, verified each extracted byte commitment, then removed the generated plaintext copies. The private layout generator and seed are also wrapped. No held-out document, plaintext values, layout recipe or key is published in Git.

After both sources, adapters, clock and commands freeze, the coordinator names the reviewer, exact source, representative packet, isolated runtime, lease and time limit. The custodian releases only that reviewer's **input**. Retain both raw paired outputs and completion evidence, then authorize **scoring** separately. Hash the reconstructed PDFs, predictions and score results in the reviewer receipt. Families A and B have distinct keys and remain reserved pending their own releases. The reviewer receives its key-file location from the custodian. PowerShell 7 with .NET AES-GCM and CurrentUser DPAPI can run:

```powershell
./release.ps1 -Family H -Stage input -SealedDirectory <sealed-folder> -KeyFile <custodian-provided-key> -Destination <new-reviewer-input-directory>
./release.ps1 -Family H -Stage scoring -SealedDirectory <sealed-folder> -KeyFile <separate-key> -Destination <new-reviewer-scoring-directory>
```

H has three shorter pages and one table page crossing a window boundary. Prior warm WP-0014 measurements of 6.851 seconds for short and 118.670 seconds for dense imply about 139 seconds per arm, 4.6 minutes per pair or 9.3 minutes for two pairs. A and B contain 12 and 15 dense pages respectively. Applying the same proxy to the remaining shorter pages gives about 58.4 and 69.6 minutes per full matched pair. Two warm pairs double those times. These are feasibility estimates. They exclude setup, cold load, serialization, persistence, restarts, scoring and overruns. Actual page length and decode cost can differ. Use fresh dev timings before binding reviewer work and preserve a complete representative replay within the protected hour. [Prior measurement](../../agent-reports/eld-coordinator/WP-0014/003_2026-11-18_verification_eld-coordinator.md)
