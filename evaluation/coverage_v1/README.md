# WP-0011 sealed matched diagnostic corpus

Owner: eld-eval-custodian, continuing native session originally requested xhigh. Authority: public jackgumpe/eledgercare commit 8d23d755a35be26ff29c319c527bd770abdcae4b, accepted starting base 956c056be2ec970340074871ecdd7e1a9855d944. New owned local repository C:/Users/jackg/eLedgerCare-Coverage/WP-0011/sealed, branch sealed/wp-0011, no remote. Original WP9 materials are preserved.

Procedural sealing applies until exact accepted diagnostic protocol/scoring freeze, independent admission and coordinator unseal. Only custodian and independent reviewer may inspect identifying facts, labels/header selections, arrangements, sources, images, expected records, annotations or ideal-native witnesses. This is not OS-enforced isolation. Public schema/condition/path/hash coordination is permitted without identifying examples. Sources contain clearly fictional new content.

Exactly three independently authored content families produce four matched one-page documents each: control, layout, vocabulary and degraded, with fixed IDs WP11-F01/F02/F03-<condition>-v0. Three independent families must not be counted as twelve independent generalization samples. Facts, canonical slots/row keys, values, types, units and absence meanings are identical within each family.

Control label/header signatures and geometry are supported by frozen B0 and mapping_v1 source, verified using private ideal-native witnesses with both unchanged mappers. Witnesses describe ideal reading of printed content and reserved form regions; they are not model output or OCR success evidence. They are retained for all four conditions under annotations schema eld-coverage-annotations/1. Annotation label/value boxes are fixed physical regions containing actual printed ink; full ink extents and operators remain separately retained. Both full-score control recovery and region fidelity are checked.

Layout changes only arrangement; exact text multiplicities and typography are preserved. Vocabulary changes only field/absence labels and table headers; reserved regions, anchor coordinates, fonts, one-line/no-wrap layout and all facts are fixed. Ink widths naturally vary with wording within those fixed regions and are retained, not presented as identical glyph extents. Degraded is one fixed composite scan-quality recipe selected before generation: control's exact canonical 300-DPI raster, grayscale, BOX downsample to 850x1100, BILINEAR return to 2550x3301, Gaussian radius 0.5 and fixed tone lookup round(40+0.80*x). No random noise or model-dependent selection. Components are not separately attributable.

Every variant uses the same 612x792.24 point box. Canonical 300-DPI raster size is 2550x3301. The losslessly embedded degraded target must render to exactly identical final model-input pixels, so clipping/resampling/container differences are not silently folded into severity. Canonical degraded text/reference and witness come from its exact same-family control. PDFium CPU rasterization is not inference. The final observed quality is admitted by independent visual inspection, not an OCR promise.

Expected records retain B0 schema_version 1.0.0 with variant_kind equal to the condition and split diagnostic_eval. Explicit printed empty slots use absent_blank. Unprinted optional slots have no absence denominator. Quantity units remain printed and separately retained; inherited numeric normalized scores alone are not unit accuracy. The diagnostic author controls separately versioned metric definitions; this custodian changes no scorer.

Generic PDF serialization is an unchanged copy of evaluation/generation/pdf_writer.py at authority, SHA256 e75929f4d9567921d4e64093f6c655021dd82c28b161280066191fb7808087c6, with explicit packet metadata constants. Control-support module/file pins are in provenance/source-pins.json. Only existing read-only CPU Python 3.12.10, pypdfium2 5.15.2, Pillow 13.0.0 and pypdf 7.1.0 are used. No new packages, downloads, models, services, GPU or subagents.

Freeze helpers before generation/decisive checks, and commit candidate before validation. Output/attempt directories are exclusive. Preserve all failures, partial generations, original candidates and correction commits. Independent reviewer proposes corrections; custodian authors them. Corpus admission is not self-acceptance. After exact root unseal, reserved /008 publishes the admitted tracked bytes unchanged under the separately approved namespace. No private source content enters the public reservation before that gate.

Commands:

```text
python generation/create.py --out corpus/r1
python generation/validate.py --candidate corpus/r1 --candidate-commit <full-sealed-sha> --public-repo <custodian-public-worktree> --run-id verify-r1
```
