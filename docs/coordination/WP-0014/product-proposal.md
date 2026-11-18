# Proposed product change for short-page OCR

**As an intake operator, I can open Intake and continue selecting or uploading paperwork while the local OCR worker prepares. When I extract a document, the service uses the available worker and saves the result against my attempt.**

Qualify one resident native worker per GPU. Start it asynchronously from Intake, coalesce simultaneous preparation requests, and serve already-queued documents in order. Report ready only after a representative first inference succeeds. If an actual request arrives before a warm-up has begun, let its document be the first inference. Show the existing processing or queued status throughout. The current fresh-worker path provides a rollback on subsequent explicitly started attempts.

The service owns the model process and its lifetime. Run the full installation and model verification before loading a generation. Keep its artifact identities stable, check the namespace per document, and retire the generation on mismatch. Verify each document's digest, render it anew, create fresh inference state, and validate its output before the existing database transaction. Retain the original bytes, raw extraction, provenance, page count, and attempt-specific fencing.

Before product acceptance, exercise two simultaneous Intake openings, immediate Extract, an already-ready request, two queued documents, interruption during actual decoding, worker or API loss during publication, restart, and idle retirement while new work arrives. A late reply from an old worker must never complete a retried attempt. A retired model must release GPU memory and a failed warm-up must leave upload usable. Keep native raw layout output in each attempt so coordinate changes are observable.

Measure Intake-to-first-result, Extract-click-to-visible, both users' completion times, and idle VRAM. Carry forward the 10-second ready short-page target and the twofold improvement threshold at matching boundaries. The measured diagnostic comparisons and the independent repeat determine whether this proposal merits its own implementation assignment.
