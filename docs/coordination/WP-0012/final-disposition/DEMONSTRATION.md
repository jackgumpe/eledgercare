# Local demonstration: upload, review, find and reopen

This walkthrough uses the accepted local product and fictional one- and three-page maintenance documents. It describes the workflow exercised in WP-0012. The retained rehearsal databases and original evidence must remain intact. A historical runtime lease cannot be reused for another model run; the demonstrated operator sequence is repeatable with a new owned session and current resource allocation.

1. Open the local application. Submit `tests/fixtures/SYN-WO-01-v1-raster300.pdf`, open its document page, and choose **Extract document**. Show the queued/running state, then **Completed (unreviewed)**. Extraction completion does not mean the contents have been checked.
2. Compare the saved extraction with the original PDF. Open **Review as maintenance work order**, correct the source-backed values, and save a reviewed revision. Save a later draft to demonstrate that a pending edit stays distinct from the last reviewed version.
3. Find the document through the archive. Search machine text and reviewed fields separately; show the provenance label and open the source and review history from the matching result.
4. Submit `tests/fixtures/SYN-MP-01-v0-clean.pdf` and extract it. Compare its pages with the result. Mark fields absent from the source explicitly unknown. Save the reviewed revision, then reopen the matching source page and its review history.
5. Stop and restart the owned API and PostgreSQL, with extraction disabled on restart. Reopen both saved documents, repeat the archive searches, and verify the original, raw extraction, reviewed revision, newer draft, explicit unknowns and history remain available. Confirm that no new extraction attempt appeared.

Use the accepted [detailed operator runbook](../../../implementation/WP-0012/eld-f4-implementer/correction-006/RUNBOOK.md) for the exact prepared resources, commands and source-grounded values. Its preparation-era status is historical; the final disposition and immutable runtime reports record what actually ran. The author resources used API5590/UI4610/PostgreSQL55438, and the independent reviewer used5690/4710/55439. All are loopback-only; services are stopped after the evidence run. Credentials remain outside Git.

Allow several minutes for OCR on this machine. The author observed about194 seconds for the one-page document and347 seconds for the three-page document, including its browser wait; these are two measured runs, not a performance guarantee. Original OCR mistakes remain visible. The demonstration proves this local synthetic workflow within its tested scope, not general document accuracy, production reliability or OS-enforced outbound isolation.

For a presentation, explain the distinction between original paperwork, untouched machine output and a saved reviewed revision. Scripted test corrections demonstrate the software's review state; they are not customer approval or authenticated human sign-off. Research mapping results remain separate from the product.

Evidence limit: the independent reviewer's immediate archive screenshot was still loading and its post-restart native PDF panes were unpainted. Functional query, navigation, page-fragment and original-range checks passed. Those captures are not visual proof of painted target pages; retain this distinction when showing the evidence.
