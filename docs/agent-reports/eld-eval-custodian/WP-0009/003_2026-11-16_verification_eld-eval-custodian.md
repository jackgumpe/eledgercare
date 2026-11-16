# WP-0009 /003: Sealed fresh-family reservation

- Report path: `docs/agent-reports/eld-eval-custodian/WP-0009/003_2026-11-16_verification_eld-eval-custodian.md`
- Sequence reservation: [INDEX.md](../../../../INDEX.md), WP-0009 /003 at exact coordinator authority `22b88bc32d053231678aef88e6b7f76d3e61910a`
- Category: verification
- Author / agent ID: `eld-eval-custodian`
- Actual model / effort: native Codex session; backend model identity is not exposed in this worker context; fresh session requested `xhigh` by coordinator under explicit user preference
- Execution environment: Windows PowerShell; Python 3.12.10; existing read-only CPU environment with pypdfium2 5.15.2, Pillow 13.0.0 and pypdf 7.1.0
- Published by: author
- Timestamp: 2026-11-16 UTC
- Repository / branch: private `jackgumpe/eledgercare`; `evaluation/wp-0009-fresh-families`
- Owned worktree: `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-eval-custodian`
- Initial base revision: `5e1241d6d365d664f12619d415f48ec3d3b7ddca`
- Authority merged before work: `22b88bc32d053231678aef88e6b7f76d3e61910a`, fast-forward, exact origin observed
- Public deliverable revision: `7513a9a86e6af55a6d8ca7f5a8dc0f80f054ba0b`
- Previous report: none for this stable role in this packet
- Related authority: [bounded lane](../../../coordination/WP-0008-0009-authority.md), [exact custodian kickoff](../../../kickoffs/WP-0009-eld-eval-custodian.md)
- Status: ready-for-review — sealed reservation and custodian verification; independent admission pending
- Next owner: independent `eld-mapping-reviewer`, reserved WP-0009 /004, coordinated by root

## Summary

Exactly four new synthetic families are frozen: four PDFs and six pages, comprising three single-page documents and one three-page packet. Coarse task coverage is maintenance work orders, inspection/service checklists, supplier invoices and multi-page service records. Source operators, semantic source records, PDFs, expected values, complete reading-order references and author validation evidence are retained in a sealed local Git repository. Public deliverables expose hashes, counts, coarse coverage, custody and validation status only.

The custodian's generation, arithmetic, PDF/text/reference/expected checks, rendered inspection and two deterministic regenerations passed. This report is author verification. It does not accept its own ground truth. Root explicitly released canonical /003 publication as ready for independent review after the sealed candidate was reported; the independent admission and mapper/protocol freeze gates remain in force.

## Objective and acceptance criteria

Prepare the bounded fresh family set before mapper tuning, preserve important string identifiers and leading zeros, dates, descriptions, money, table rows, correctly printed quantity/unit cases, explicit absence semantics and multi-page links. Use canonical B0 semantic field/table-slot names and typed conventions where meanings agree; do not import mapper aliases or templates. Keep document-specific content blinded to the mapping author until accepted mapper/scoring/protocol freeze and exact coordinator unseal release.

The author preparation criteria are met. Independent ground-truth admission is outstanding. No inference or GPU execution was authorized or performed.

## Change inventory

| Action | Exact path or external resource | Result |
| --- | --- | --- |
| Added | `docs/evaluation/WP-0009/reservation/README.md` | Custody, disclosure boundary, checks, coverage limits and next reviewer |
| Added | `docs/evaluation/WP-0009/reservation/reservation.json` | Four opaque identities, page counts, 20 core artifact hashes, exact sealed receipts and author verification status |
| Added | `docs/evaluation/WP-0009/reservation/sealed-inventory.json` | Exact complete 39-file tracked-source/evidence inventory with paths, byte counts and SHA256 hashes |
| Added, after deliverable | This canonical report | Immutable reservation-stage verification and handoff; its publication SHA is supplied separately |
| Created outside public Git | `C:/Users/jackg/eLedgerCare-Mapping/WP-0009/sealed` | Verified absent before creation; local branch `sealed/wp-0009`, no remote; four committed receipts below |

The authority fast-forward imported only the coordinator's already published files. The author delta from that authority to the public deliverable contains exactly the three reservation paths above. No shared routing, product source, old corpus, B0, Q0 or historical report was edited.

## Sealed revision and inventory bindings

| Purpose | Exact local revision or identity |
| --- | --- |
| Generation/verification helper freeze | `dd3aaa2f9d80db434c62fcbed287e94b95610ae4` |
| Four-family corpus candidate | `1040e4132532670a100fa431266c69c2ea56aefc` |
| Author evidence and frozen inventory helper | `7e24593131a02d1bc768c39c6e3cc86735c2600c` |
| Inventory-only receipt; final clean sealed HEAD | `559c5d09490b7729be26fb9bf9d872305cae3303` |
| Complete sealed inventory | `inventory/sha256-r1.json` |
| Inventory SHA256 | `c2971612374178aaf1194f4b3a48e0c8435d14305b813b290f0e1e2b856ac322` |

The inventory includes every one of the 39 files tracked at the evidence commit. Its subsequent receipt binds the inventory itself as the fortieth file. Git internals, ignored byte-identical regeneration copies and Python cache are excluded. The public inventory copy is byte-identical. Exact per-artifact paths and hashes are in the [reservation](../../../evaluation/WP-0009/reservation/reservation.json) and [inventory](../../../evaluation/WP-0009/reservation/sealed-inventory.json).

## Decisions and rationale

Each family uses newly authored fictional semantic records and independently composed layout/header wording. Existing canonical task slots preserve interpretability without disclosing actual selections. The retained generic PDF serializer is pinned in sealed provenance; no B0 document template, original record, mapper alias list or future mapping implementation was used. The source contains explicit local fictional notices, addresses/contact details and identities. No customer/company document was copied.

All four inputs are clean digital PDFs. The reference includes every visible text operator, including titles, headers, labels, furniture and footers, with deterministic page/baseline/x/operator-order rules. Empty printed response boxes are explicit absences; optional fields without printed slots stay outside that denominator. Printed quantity and unit metadata are retained. The inherited numeric normalization metric alone does not measure unit correctness. No scorer or mapper was changed.

The external repository is procedurally restricted, with no claim of OS isolation. The mapping author must not read its files, images, expected values, detailed findings or history before exact release. Independent reviewers may inspect it, must keep correction specifics sealed and may not author fixes. Any correction requires a new version and preserved evidence; no overwrite is permitted.

## Verification

The following commands ran in sealed custody with the existing CPU Python environment unless specified otherwise. The full source and output records are covered by the sealed inventory.

| Check / exact command or operation | Revision / actual result | Evidence |
| --- | --- | --- |
| `python generation/create.py --out corpus/r1` | Frozen helper `dd3aaa2f...`; exit 0; four PDFs, six pages, 21 core files | `evidence/generation-r1/output.txt`, `exit-code.txt` |
| `python generation/validate.py --candidate corpus/r1 --run-id verify-r1 --public-repo "C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-eval-custodian" --candidate-commit 1040e4132532670a100fa431266c69c2ea56aefc` | Exact committed candidate; exit 0; ten check groups passed | `evidence/verify-r1/validation.json` |
| Candidate PDF parser, actual stream operator, complete reference and expected-location checks | All 20 manifest entries verified; 249 visible text operators; 39 fields, 90 cells, 15 rows, five tables, four explicit absences and three printed quantity/unit cells | Same validation JSON; core operators/reference/expected files |
| Separate Decimal invoice arithmetic and elapsed-time/labor checks | Passed against literal source values | Same validation JSON |
| Page geometry, text nonoverlap, response-box emptiness, page markers/adjacency/repeated identity | Passed across six pages | Same validation JSON |
| Six PDFium renders and local `view_image` of contact sheet | Rendered and visually inspected; no observed clipping, collision or unreadable value | Six PNGs, `contact-sheet.png`, `visual-inspection.json` |
| Two `generation/create.py` invocations into distinct ignored `scratch/verify-r1/generate-1` and `generate-2` | All 21 output files byte-identical to candidate on each run | Commands and equality results in validation JSON; copies retained locally |
| `python generation/inventory.py --out inventory/sha256-r1.json` | Frozen inventory helper at `7e245931...`; 39 tracked files hashed, inventory-only receipt committed afterward | Public exact inventory copy |
| Public projection check: rehash all 39 inventory entries and 20 fixture artifacts; compare exact inventory bytes; inspect disclosure payload | Passed; long fresh labels/values absent from public payload; manual payload review found only permitted metadata | Reservation files at `7513a9a8...`; tool transcript |
| `git diff --name-only 22b88bc32d053231678aef88e6b7f76d3e61910a HEAD` at deliverable | Exactly three owned reservation paths | Deliverable Git diff |
| Paired `git rev-parse` of authority and deliverable trees for `evaluation`, `qualification`, `research`, `src`, `tests`, `docs/agent-reports` | All six identities equal; `qualification` includes B0 and Q0 | Exact tree observations below |
| `git diff --check 22b88bc32d053231678aef88e6b7f76d3e61910a HEAD` | Passed at deliverable | Git operation |
| `git -C <sealed> status --porcelain` | Empty at sealed receipt `559c5d094...`; no remote configured | Git operation |

Protected tree identities at both authority and deliverable: `evaluation` = `60fcc7fa1741b6c44489bb9cf8484e03a4cbf019`; `qualification` = `0ab2f5dab3984e832375d2ab225f0f0f598f8359`; `research` = `5036d17e55f96af3bdeea82a20a32eb54a26ddca`; `src` = `73d0146b3624ab4928a4d2cda7806d7d6166906e`; `tests` = `5ad9bd15f41ab24bd5851ca02bfa0d8054dc1453`; historical `docs/agent-reports` = `ec10af156af6cb7989cfcdf48c401be74ddd3123`. This report is the later new report addition.

Failure retained: the first post-deliverable preservation probe requested nonexistent tree `qualification/harness`; `git rev-parse 22b88bc32d053231678aef88e6b7f76d3e61910a:qualification/harness` exited 128 and the Python audit stopped with `CalledProcessError`. Directory inspection established actual `qualification/baseline` and `qualification/q0`; the subsequent explicit paired check used their enclosing `qualification` tree and passed. The failed probe did not mutate files. Both initial corpus generation and frozen corpus verification passed; the reservation's zero-failure counts refer specifically to those corpus runs.

Not run: independent admission, mapper/scorer evaluation, OCR/model inference, GPU execution, service startup or package/download setup. These are outside this preparation release. No fresh document content is unsealed by publication.

## Review map and handoff

Review public deliverable `7513a9a86e6af55a6d8ca7f5a8dc0f80f054ba0b`, the [custody README](../../../evaluation/WP-0009/reservation/README.md), exact inventory and reservation. Independently inspect sealed local corpus candidate `1040e4132532670a100fa431266c69c2ea56aefc` and final receipt `559c5d09490b7729be26fb9bf9d872305cae3303`, including actual PDFs, expected records, reading order, arithmetic, provenance and disclosure boundaries. Custodian author checks are supporting evidence only.

Root schedules independent /004. The mapping author remains blinded. After accepted mapper/scoring/protocol freeze, only a separate exact coordinator release may authorize publishing sealed content in a new owned evaluation namespace. Later unsealing is documented separately; this reservation report remains immutable.

Publication receipt: this report cannot contain its own commit SHA. Author will push the owned branch normally, verify exact origin tip and deliverable ancestry, and send the report publication SHA and complete sealed inventory receipt to root. Remote confirmation is pending at report construction and is completed in the handoff message.
