# WP-0011 exact admitted corpus publication

Root explicitly unsealed the admitted corpus at `e47def37be1ceaf04722125a8aee7ddb49e4159e`, following independent final source acceptance. All **109 tracked files / 6,311,650 bytes** from sealed receipt `6583715067d3a027dd2502ed9623cf02c545391d` are copied unchanged under [evaluation/coverage_v1](../../../../evaluation/coverage_v1/). Their relative paths, Git blob identities, modes and disk bytes are preserved. The corpus commit is `970675115b948defc32125d20e6a31ab788d88f9`.

This includes three independent families with four matched conditions each: twelve one-page PDFs, with 48 originally reserved PDF/expected/reference/annotation artifacts. Copying the complete admitted repository also preserves original sources, operators, provenance, author checks, interface checkpoint, inventories and historical custody notes. Historical statements such as pending admission or private paths inside those original files remain verbatim. This receipt and the explicit root release supply the later publication status; the original artifacts were not rewritten.

## Exact release and custody bindings

| Binding | Identity |
| --- | --- |
| Explicit release | [unseal.json](../../../coordination/WP-0011/unseal.json) at `e47def37be1ceaf04722125a8aee7ddb49e4159e`; SHA256 `79a89d2486efb7ec533dc87afc043bc4dff169fd63c1ee15bd5968ed20ac2cb8` |
| Final diagnostic source | `253519e07e7d45cf1f5ecb3e03053582f7f7d4cc`; coverage source tree `6bdab544c9fe26cbf093cc765212db2a2e7a97a5` |
| Final protocol SHA256 | `03b13a41a0047c827af32e71209933700457a5dfd6d38ec106daed82ef5b9000` |
| Independent source acceptance /002 | `bfac3057ce0142dcd37372dee26398d682238202` |
| Accepted integration | `55b4ac15d7d989669e6515b66aa6f0c7f885b18a` |
| Independent corpus admission /004 | `021dc265790c90ae83f1afa24fc3f2a71eae41e1` |
| Original local custody | `C:/Users/jackg/eLedgerCare-Coverage/WP-0011/sealed`, branch `sealed/wp-0011`, clean at `6583715067d3a027dd2502ed9623cf02c545391d`, no remote |
| Original inventory | `inventory/sha256-r1.json`; SHA256 `bd37f4020a4b5b185379d9d7d2e529b39ebc0d3fa0aa37802d2bccc0546c4330`; 108 entries plus itself |
| Original reservation | `98a3a3f73df0e578ae98ebf3923db7ba4882d018`; [reservation.json](../reservation/reservation.json) SHA256 `ac58c97459b199232cb541ba2216159cada61db73b8e44abaa4128a22284cddc` |

The [custody timeline](custody-timeline.json) distinguishes the earlier public schema-only checkpoint from subsequent source freezes. Public reservation preceded the initial and final diagnostic source candidates. Independent admission and final source acceptance preceded the explicit root unseal, frozen publication helper and unchanged publication.

## Publication verification

[publish.py](publish.py) was frozen at `4678a2931b767d88a9f4f3723dc77a504ca3b19b` before copying. SHA256 is `a28fd39d1cbc5944378bb9603ffdda3937bf5f8031178a988f2f761eb5da8702`. Each operation retains a separate exclusive receipt; no attempt is overwritten.

| Operation | Retained receipt | Result |
| --- | --- | --- |
| Verify release, originals and absent destination; exclusive copy | [copy-001](attempts/copy-001/receipt.json) | Passed; 109 disk files exact |
| Verify exact staged scope and bytes | [index-001](attempts/index-001/receipt.json) | Passed; all 109 staged blobs exact |
| Verify committed blobs and modes, complete old-tree preservation | [commit-001](attempts/commit-001/receipt.json) | Passed; all 109 original/public blobs and modes equal; all 2,901 preexisting authority entries preserved |

The committed receipt provides the complete 109-file private-to-public mapping with sizes, SHA256 values, original blob IDs and modes. [authority-tree.txt](authority-tree.txt) lists every protected authority path, mode and Git object; the frozen verifier checks the complete tree against the publication candidate. The original 48 reserved descriptors and twelve actual PDF page counts were checked in every mode.

The original corpus `.gitattributes` is one of the 109 copied files and contains `* -text`. This preserves admitted bytes even where the root has an inherited `eol=lf`; no root attribute changes or new corpus attribute file were needed. A separate `* -text` rule in this documentation namespace preserves publication evidence bytes. Staged whitespace inspection used `cr-at-eol` to recognize preserved CRLF; no original bytes were normalized.

The subsequent [publication inventory](publication-inventory.json) covers all corpus and helper/evidence additions through its exact source commit. Its explicitly excluded inventory, inventory-attempt receipt and later canonical /008 are separately bound by the report and publication handoff. Canonical [custodian /008](../../../agent-reports/eld-eval-custodian/WP-0011/008_2026-11-17_verification_eld-eval-custodian.md) records the final inventory and publication sequence.

This is author verification of exact publication. The unchanged corpus admission remains the independent reviewer's /004; the diagnostic source acceptance remains independent /002. Reviewer admission evidence has a separate owner and publication. No regeneration, mapper/scorer execution, rendering, inference, model/GPU/service/process query, dependency installation or download occurs here. Root must audit and integrate the exact publication before any separate finite runtime release. These exposed fixtures are regression material for future use.
