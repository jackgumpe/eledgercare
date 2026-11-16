# WP-0006: accepted local extraction and saved results

F2, “Extract a submitted maintenance document and reopen its saved result,” is accepted for the authorized local synthetic-document profile. The independently reviewed product source is `8a73b7a5dab51e3ccf803aceedded4929529dd35`. Intake now connects to real local inference, durable attempt/result storage, honest failure and interruption states, explicit retry, and an unreviewed result screen that remains readable with OCR disabled.

## Exact evidence and acceptance

| Record | Revision |
| --- | --- |
| Accepted design /002 | `e2452e1ab3d8937868c07ffb30ce430715b5be78` |
| Product source | `8a73b7a5dab51e3ccf803aceedded4929529dd35` |
| Independent source reconciliation | `82e8f732afbf038bfb5b6c560f1b1219aaa4e40f` |
| Author final /003 | `3ece293f4ea9b78f19dbfb7f95472b95d091d79e` |
| Author saved-result completion | `88f24fb2f08eeaa773d330ab0d8b1e7c74037d8f` |
| Independent runtime authority | `513da1a18c9b80ed99d56dd1ff7bf3bc1cb77905` |
| Independent clean executing HEAD | `b343f6ff78aa41332ecbe957577b6776f8edc22f` |
| Independent frozen runtime helper | `694f4b61294aa1b489fb0a486cd328bdc61643aa` |
| Independent final runtime evidence | `7f0ec3a9338606ce54c4c6d2eeabab8a2c245e2a` |
| Independent final /004 | `c854a1d4c306c3b10d78df42a1a2552a06bb4a98` |

[Author /003](../../../agent-reports/eld-f2-implementer/WP-0006/003_2026-11-16_implementation_eld-f2-implementer.md), [independent /004](../../../agent-reports/eld-next-reviewer/WP-0006/004_2026-11-16_review_eld-next-reviewer.md), and the [source reconciliation](../../../reviews/WP-0006/eld-next-reviewer/source-reconciliation/README.md) retain exact commands, findings, source inventories and raw observations. The coordinator [final runtime publication audit](../reviewer-runtime-publication-audit.json) verifies original captures, three saved outputs, provenance, protected source and the report-only publication. The combined final preservation inventory records every integration change.

| Criterion | Accepted evidence |
| --- | --- |
| F2-01: real raster extraction and browser result | Separate author and reviewer genuine F01 inference through the production path, persisted completion and actual Edge result checks. |
| F2-02: original/raw/provenance/page integrity | Original download digests, native raw bytes, PostgreSQL bytea digest, API and browser text match; F07 preserves three ordered pages. |
| F2-03: durable duplicate/retry fencing | Independent PostgreSQL/source boundary tests plus actual interrupted attempt, explicit retry, retained history and one accepted result. |
| F2-04: recovery and child lifetime | Queued/orphan recovery tests; actual API-supervisor-only termination during inference, observed launcher/worker Job Object cleanup, no automatic retry, successful explicit retry. |
| F2-05: restart and worker-independent reading | Actual API and PostgreSQL fast restart, three saved results reopened in Edge with OCR disabled, exact original/raw/provenance and unchanged four run directories. |
| F2-06: honest bounded failures and safe display | Independent error/envelope/storage/diagnostic tests and inert unreviewed browser rendering. Real inference supplies happy-path evidence. |
| F2-07: migration, least privilege and separation | Independent real-PostgreSQL migration/permission/regression tests, build/browser checks, exact accepted source identity and no product imports of qualification/research/evaluation. |

The corrected source passed 74 .NET tests, including 20 real-PostgreSQL acceptance tests, and nine Python tests in the independent reviewer worktree. Additional actual child, NTFS churn/ACL/reparse and PostgreSQL diagnostic probes passed. Ten previously passed Edge regression cases were reused only where the UI tree remained identical; new actual-model Edge checks separately verified this runtime. The coordinator audited evidence and integration rather than claiming to have authored or rerun those suites.

## Actual independent runtime

The reviewer used its own database `eledgercare_f2_runtime_reviewer`, runtime directory `C:/Users/jackg/eLedgerCare-F2/WP-0006/reviewer`, and loopback ports API5290/UI4310/PG55435. The four planned model attempts yielded three completed results and one deliberately interrupted attempt:

| Document | Attempt | Result / outcome |
| --- | --- | --- |
| `01a1e571-2838-714b-861b-bf0835d7c90a` | `01a1e571-297a-7f0e-a293-e9e1c0851cd4` | `01a1e573-a855-7735-96e1-f5d14cada602`, one page |
| `01a1e573-ca14-72ba-a46a-c84690288e22` | `01a1e573-ca25-733e-b048-44c8ea2ac61d` | `01a1e578-8bfa-7bba-b104-ea8309dbfd9e`, three pages |
| `01a1e578-8f3a-7e0c-826b-a2c9dc066a8f` | `01a1e578-8f49-75ab-89c7-4d184378bf28` | Deliberately interrupted; no accepted result |
| Same document, explicit retry | `01a1e579-4599-7bed-acdc-2863c448c6fa` | `01a1e57b-bfbd-7447-916c-92b386e5931d`, one page |

F01 outputs were 3,236 bytes, SHA256 `7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95`. F07 was 7,511 bytes, SHA256 `c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639`. These observed matches across the two sessions do not establish general determinism or content accuracy.

The reviewer terminated supervisor18496 after actual inference progress11; launcher11796/worker32708 exited through Job Object containment in547.2ms. Recovery exposed the interrupted attempt, empty replay returned409 `retry_explicit_required`, and explicit retry returned202 and completed. PostgreSQL postmaster22360 restarted as27172; API29208 restarted as8172 with OCR disabled. Actual Edge checks verified all three results, all four history rows, inert text and original downloads.

The sole reviewer lease returned at2026-11-16T17:51:15.145246Z and was [independently acknowledged](../gpu-reviewer-release/lease-return.json) at17:52:28.6270843Z after model processes and ports were absent and18 model objects plus notice reverified. All author and reviewer leases are returned. Owned databases, runtime directories and raw evidence are retained; local trial services are stopped.

## Preserved failures and factual corrections

The initial author trial failed before model load because the isolated Python entrypoint could not import `local_ocr`. Independent review also found storage-churn/child-cleanup/recovery and PostgreSQL diagnostic-encoding defects. The assigned author corrected them; the independent reconciliation resolved all three findings on exact8a73. Original failure records remain unchanged.

The corrected author trial completed its four intended model outcomes but its final browser helper expected “Interrupted” where the UI correctly displayed “Extraction interrupted.” That original trial summary remains FAILED. A separately authorized CPU-only supplement, with OCR disabled and no new model calls, verified the existing three saved results/four attempts across API/PostgreSQL restart. Two supplement helper setup failures and reviewer helper preparation failures remain preserved. The independent final frozen runtime then passed its entire matrix without source changes.

Immutable author /003's CUDA12.8 / torchvision0.23.0+cu128 prose is incorrect. Actual pinned packages are **torch2.13.0+cu130 and torchvision0.28.0+cu130**. This is a report correction, not an environment change. “All four attempts succeeded” describes three completed extractions and one intentional interruption, not four completed extractions. A byte-identical retry is an observation only.

The reviewer runtime README labels its final free space as51.92GiB; the underlying observation is51,918,110,720 bytes, or48.3525GiB. Both exceed the20GiB floor; the byte observation governs. The criterion map above follows the original accepted design's F2-01..07 numbering; /004 groups the same evidence under a different ordering.

## Completion boundary

This acceptance covers the admitted synthetic one-to-three-page local profile and durable product behavior. It does not establish customer-document accuracy, production deployment readiness or power-loss durability: the PostgreSQL test was a clean fast restart. Raw outputs remain explicitly unreviewed. The unmodified model, frozen generation/rendering settings and local torchvision TOFU limit remain unchanged. Qualification and baseline code stay separate from product code. F3 corrections/approval, F4 search, E1-E3 optimization, training, customer data and deployment remain unreleased.
