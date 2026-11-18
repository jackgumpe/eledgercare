# WP-0014 frozen native OCR probe

Use the accepted production worker at tree `dc9b69e480f93db1e73ebdd65719efaa9aeab298` (product commit `c1fed68020ae67e8b4763bc6ea5473adaa86de2b`). The Q0 model revision is `0480966938291445591f69f08a13b041c073a96a`. The accepted synthetic WP-0012 rehearsal request supplies the model, 32-package lock, source and configuration digests, GPU UUID, guards and provenance exception. Each run gets new document, job and attempt IDs.

## Inputs and pass criteria

A and B are new synthetic scan-only US Letter PDFs. `fixtures.py` contains the verbatim expected sentences, font checksum and reproducible PDF bytes. S is the accepted raster work order in `tests/fixtures/SYN-WO-01-v1-raster300.pdf`. `cases.py` pins all three digests and checks printed fields and position-specific cells against existing truth. A/B accuracy means exact ordered text with case and punctuation after stripping native layout markup and collapsing whitespace. Retain raw hashes, output token counts, finish state, page count and raster identity.

The predeclared target is warm short service at most 10 seconds and at least 2× improvement over the equivalent cold result wait with exact short text and zero lost required content. Compare by document and retain each measurement and the short-run median/range. Report existing structured OCR mistakes separately from additional lost content.

## Measurement

Three serial, fresh unmodified production worker processes receive A, B and S. A fourth, fresh instrumented process runs A → B → A → B → A → S with one model load. This yields two warm services for each short page and one structured service after the model is resident. Every call runs the real worker request entry, fresh PDFium rendering, prompt/token/page guards, native monitor and fresh per-request result. The resident harness reuses the verified platform, model, tokenizer, model-file checks and source AST check for the fixed process lifetime. It still reads and validates the pinned manifests, worker and configuration, request input, storage, environment, loaded modules and output. It serializes requests in one owned process, retains a run-local module cache and moves completed outputs between requests. No HTTP or database contributes to these measurements.

Fresh result-ready wait starts immediately before Popen and ends when a parent poll first observes the atomic envelope (40 ms polling interval plus scheduling). Process exit is observed separately. Resident request wait starts before synthetic input preparation and ends when execute_request_file returns after its envelope/heartbeat. Parent and child monotonic timestamps share Windows QPC. Native TTFT spans the model's internal clock through the first selected token (integer conversion synchronizes GPU output). Additional PEP 669 events measure the first TextStreamer.put boundary after explicit CUDA synchronization. The span from SAM entry through projector return has synchronized endpoints and includes feature combination between the calls. Native post-first time includes later decoding, final EOS selection, cleanup and text decoding. Emission cadence uses the N−1 subsequent visible emissions and their first-to-last interval. Total inference rate includes page preparation, prefill and completion. These intervals overlap. Instrumentation can perturb timing. OS file caches and device state are uncontrolled, so “fresh” means process-cold.

## Commands

Use a new owned run label. The CPU stage verifies fixture regeneration, truth checks, static pins and PDF content/rendering. Model execution requires a sole GPU release for the exact candidate.

~~~powershell
$probe = 'docs/research/WP-0014/eld-latency-author/probe.py'
$gpu = 'GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d'
python -I -B $probe cpu trial1
foreach ($stage in 'fresh-A','fresh-B','fresh-S','resident') {
    python -I -B $probe $stage trial1 --gpu $gpu
    if ($LASTEXITCODE -ne 0) { break }
}
python -I -B docs/research/WP-0014/eld-latency-author/summarize.py C:\Users\jackg\eLedgerCare-Latency\WP-0014\author\trial1\runs
~~~

The probe creates a new cache/profile/temp tree for each fresh worker and one for the resident process. The fixed Q0 interpreter runs with `-I -B` and the product environment allowlist. The supervisor has a 1,200-second stage ceiling and terminates only its owned child tree if needed. Full subprocess logs, caches and materializations stay under the external run directory.

Windows read-sharing handles deny writes and deletion of each manifest file and notice while the model is resident. A fresh namespace snapshot (file IDs, sizes, modification times, attributes, and directory entries) must match before use and before publishing each raw result. Initial verification hashes under held handles. The CPU scratch controls cover write, unlink, extra, prior corruption and missing file. Load-time local events capture the tokenizer, model construction and weights, CUDA transfer dispatch and final synchronization; these nested clocks sit inside the named model-load span. The research process samples Windows logical I/O and working-set counters before/after each request. Logical reads can hit the filesystem cache.

The independent short-only repeat uses stages `fresh-A` and `resident-short` (A → B → A), each with `--owner reviewer` and a separate lease.
