# Parallel R&D lane: initial hypotheses and evaluation corpus

This is a release template for the local coordinator to bind. It is one product's research lane, not a second product. No GPU experiments, model modifications, training, or production edits are released by this brief.

## Purpose and independence

Develop a small, falsifiable experiment backlog and checked test material while the product team builds durable intake. Start now from source material and pinned upstream artifacts; an accepted eLedgerCare OCR baseline does not exist yet.

Use separate Astra and Carbon sessions with distinct IDs/worktrees. Each produces a short independent first assessment before seeing the other's conclusions. Then exchange findings once and reconcile evidence once. Publish at most three prioritized experiments, with disagreements preserved. No long-running debate tournament or new multi-day provider ranking campaign is required.

Astra: propose mechanisms, baseline definitions, measurable outcomes, and the simplest tests capable of falsifying a benefit.
Carbon: challenge feasibility, identify confounding variables and platform/data constraints, and propose lower-complexity alternatives; own corpus preparation if assigned.
An uninvolved Opus reviewer checks joint outputs and independently verifies admitted fixture ground truth before those outputs are promoted as accepted shared evaluation material. Review involvement in upstream work must be disclosed; a fresh session alone does not undo authorship.

A product reviewer who participated in fixture design cannot independently establish those fixtures' correctness. Use already reviewed fixtures or a non-author check. Product implementation and R&D do not write a shared staging area.

## Initial work

1. Read the first product feature and environment receipt.
2. Pin the actual Baidu Unlimited-OCR-2 model/code sources and runtime documentation used. Keep requested model labels distinct from verified checkpoint/build IDs.
3. Separate product-enabling qualification from optional improvements. Whether vanilla OCR can run locally is a product dependency for the extraction feature; novel R&D success is not required.
4. Prepare the initial corpus and a minimal provenance manifest.
5. Produce and reconcile hypotheses. Return a short experiment backlog plus unresolved runtime/storage needs. Stop before GPU execution.

Do not postpone source-based work while waiting for a GPU lease or enterprise documents. Do not interpret an unmeasured baseline as a zero score.

## Small initial corpus

Target eight synthetic document families and up to two admitted public developer examples. This is a bounded starter set, not a statistically representative benchmark.

Suggested synthetic families:
- three single-page maintenance work orders with fictional properties/units and distinct layouts;
- three maintenance invoices with deterministic line items, subtotals, tax/discount choices, and expected totals;
- two multi-page documents with deliberate page order and cross-page identifiers.

Generate authoritative structured source data first, then render PDFs. Independently check arithmetic and the visible output. A printed handwriting-style font is not representative real handwriting. Scan/photo degradations can be later derived variants; retain their family link and transformation parameters.

Keep fixture generation deterministic with a recorded seed/tool version where applicable. Store small lawful fixtures and their source/ground truth in evaluation; keep large corpora outside Git. The product implementer may make a minimal independent synthetic fixture to avoid waiting for the entire research corpus.

Public candidates identified for inspection:
- Azure-Samples/cognitive-services-REST-api-samples at commit 4a3c5ca76318feb3f7cfb109e1f79c542eb14d01:
  curl/form-recognizer/sample-invoice.pdf
  Git blob 1e7c93c6f70ccd74697b7a74cbb6a19fa6d5d6d8, 104430 bytes.
- Same repository/revision:
  curl/form-recognizer/Invoice-6.pdf
  Git blob 1c24566e64aa6cdab8bb229c3b1ac64e750fa235, 167063 bytes.
- Root LICENSE.md at that revision has Git blob b5f17c02bce61a15a953244b8587cb468b273644 and contains Microsoft's MIT license and third-party-program note.

The cloud adviser verified directory metadata and license text, not the PDF bytes, internal notices, ground truth, or document contents. These are CANDIDATES, not admitted dataset entries. Inspect exact files/notices, retain applicable attribution, compute SHA-256, and document the permitted use before admission. Public availability alone is not a blanket training or redistribution license. If admission is uncertain, use synthetic material and record the unresolved candidate without delaying the product.

Existing model-output JSON alongside public PDFs is an example output, not unquestioned ground truth. Inspect source pages to establish the expected fields. No Azure service call, cloud OCR account, or customer-data upload is needed to use a permitted local sample.

## Manifest fields

For each admitted item: fixture ID, family ID, synthetic/public classification, origin URL and revision where applicable, file path, Git blob where available, SHA-256, size, page count, source/license/notice references, generation/transformation parameters, expected fields/tables, ground-truth checker, and intended development/evaluation split.

Keep variants of one original in the same split; they are not independent documents. Freeze a small held-out set before tuning. Label sample size and distribution limitations. A result on maintenance invoices does not establish performance on medical records, contracts, handwriting, or all business paperwork.

The durability feature needs known original bytes and expected status transitions; it does not need a trained model or a large OCR dataset.

## Hypothesis card

For each of at most three candidates:
- observed or literature-supported limitation, with source and applicability;
- proposed single change and mechanism;
- vanilla baseline checkpoint/runtime/configuration;
- controlled variables and the factors that may still confound;
- predicted quality/completeness, latency, memory, or cost effect;
- metric and denominator, failure signal, and rejection criterion;
- smallest execution needed and hardware/storage requirements;
- product relevance, risks, and promotion cost.

Useful initial areas are page-window scheduling, conditional image preprocessing, and deterministic text-layer versus OCR routing. These are options to assess, not declared improvements. Switching renderers/backends or multiple settings at once creates a different treatment and must be identified.

Measure omissions/truncation, source-page ordering, and field/table correctness rather than relying on confident prose. Use paired document comparisons and report per-document failures; do not assume scores follow a bell curve or claim significance from this small set. A local-model architecture change or fine-tune remains future work after a credible baseline.

## Resource and promotion rules

GPU execution is a later assignment: choose model/data storage, verify runtime compatibility, reserve the shared GPU, and observe actual process state. Do not kill another agent's process or treat an expired lease/timeout as proof of release.

Experiments pin product code once a suitable accepted baseline exists; before that, label them upstream-only. Keep production and experiment environments, databases, output paths, and dependencies separate. No shared mutable “latest model” directory.

Any accepted improvement is promoted through a bounded product change with independent review and regression checks. Neither member of the joint Astra/Carbon team may independently approve the joint result. An uninvolved reviewer must be able to reproduce what is claimed.

Return source tables, corpus admission/ground-truth records, hypothesis cards, and a canonical research report at the coordinator-assigned path. Distinguish inspected, executed, reproduced, and still proposed work.

