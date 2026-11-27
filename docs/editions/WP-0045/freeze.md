# Edition 02.1 candidate freeze

eld-depth-author prepared these sources on owned branch research/wp-0045-edition from 1439d0c944a38d0993283b0485f59daa15b73be4. Actual native Codex child /root/edition45, session 01a21e1f-067b-7a82-b21f-7eb3978744a3. Coordinator reports dispatch request gpt-6.2-astra / xhigh; child exposes its session identifier and no independent provider/model-effort attestation. Only docs/editions/WP-0045 and the reserved /003 report are owned. Next reviewer is eld-rd-reviewer. The exact frozen SHA is supplied outside this commit.

The three documents, shared source and profile overlays, normal entry, owned finite fixtures with separately hand-derived expected rows, original source/PDF binds, and this command specification precede blind access. The source pins, frozen wire and schedule are from base commit above. All blind input bytes are supplied by the independent fixture owner via local coordinator after independent source/oracle commitments. The expected hash inventory for blind bytes is the coordinator/fixture owner's separate seal, inaccessible to this author at author freeze. The wrapper hashes incoming bytes before JSON decoding and binds every return by exact ID in two maps. A missing ID, exception, timeout, changed input digest or differing typed return fails that row. No repair after observation.

## Predictions independent of challenge bytes

The original unmodified reference should emit 24 PASS lines plus its 448-check summary, canonical-LF SHA-256 d7e26e8d4e2f4932d4a54667c9461f912d8109cd5779b5e76da93f678e13fa66. Original vectors hash 51792f1d7af0bafe26dc450f4c37afd85dcc9a1b5aa9bc4e055f0a84e3dcf67f. Report raw byte count and SHA even if raw transport differs. In each scheduled finite case the exact unknown numeric inputs determine its values. Typing, ordering and symbolic predictions follow; the 23 owned public fixtures bind concrete full expected records, derived by arithmetic and explicit traces independently of the evaluator.

| Scheduled case | Prediction given the stated case construct |
| --- | --- |
| A1.stock | One stock(a,a+1) call, one decoded stock, stock tuple, history determined by commit. |
| A1.duplicate_first | Both branches receive a and produce a+1; both decoded stock then duplicate. Tuple is stock's. |
| A1.duplicate_second_private | Same two calls and readouts; duplicate tuple, zero commits, empty history. |
| A1.duplicate_second_commit | Same pair, duplicate tuple is sole history entry and commits=1. |
| A1.literal | Stock and K linked extra calls increase by one per call; only kK decoded, token a+K+1. |
| A1.invalid | M/invalid_selection, 0 commits, empty history, no added keys. |
| A2.clean | P, all phase arrays returned unchanged, support from both declared masks, winner earliest numerical maximum. |
| A2.masked_nan | M, first raw affected index, no winner; a later legal mask cannot clear the raw conflict. |
| A2.raw_inf | M, first raw affected index, no winner even if infinity is later masked. |
| A2.illegal_repeat | M, first changed index in offending phase under its immediate predecessor. Preserve independent page faults as well. |
| A2.signed_zero | Equal signed maxima on permitted IDs tie by smallest ID if preserved; any illicit sign-bit flip is M at its first cut and gives no winner. |
| A2.empty | M, support empty, null winner, append support/-1 after phase conflicts. |
| C1.exact | Choose lowest varying index minimizing sum of squared counts on distinct tuples; empty/singleton exits CONFLICT/IDENTIFIED. |
| C1.uninformative | Positive-probability outcomes leave posterior unchanged. Below threshold return UNRESOLVED with null action and gain. |
| C1.informative | Choose largest strictly positive conditional gain, reduced rational. |
| C1.duplicate | Already-used source leaves posterior and budget fixed; only another informative unused source can earn QUERY below threshold. |
| C1.impossible | New observed zero marginal gives MODEL_CONFLICT and null posterior, action and gain. |
| C1.budget | Below threshold with exhausted budget => UNRESOLVED, unchanged current posterior. |
| C1.threshold | Equality is sufficient for ACCEPT before budget test; null action and gain. |
| C1.tie | Tied maximal positive gains choose smallest action ID, regardless of input order. |

A1 success emits the selected branch labels in update and guard and y in the middle. For A2 always return the exact three input arrays, sorted allowed IDs, all phase/index conflicts in native cut order, first conflict or null. For valid noisy rows return exact reduced posterior strings, normalized after acquisition. All non-query actions/gains are null. The paper's normative missing-evidence exits extend beyond the complete constructed wire.

## Normal commands and constraints

From the owned worktree root, use the following PowerShell bindings. The Python executable is CPython 3.12.10 AMD64, SHA-256 4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a. PDF generation uses pypdf 6.16.2, zlib runtime 1.3.1. Clause, historical and challenge evaluation use the standard library. All rows execute serially on one thread. No OS provenance trial, GPU, model, external service or privilege is required.

    $d = 'docs/editions/WP-0045'
    $private = 'C:/Users/jackg/eLedgerCare-Speed/WP-0045/eld-depth-author'
    $inputs = 'C:/Users/jackg/eLedgerCare-Speed/WP-0045/coordination/inputs'
    $env:PYTHONHASHSEED = '0'
    $py = 'C:/Users/jackg/AppData/Local/Programs/Python/Python312/python.exe'

The decisive commands below use new, owned local directories, exact inputs and unmodified scripts in the committed candidate. The decisive blind measurement begins with reads of the coordinator-staged input bytes and ends after saving three output maps, before any expected-row opening. Use at most 30 seconds per case, 300 seconds total run and 64 MiB trial outputs. No subprocess in the blind evaluator. The historical reference is a single bounded child. Build/checks and PDF custody files are outside computed trial raw-output accounting.

    & $py -B "$d/trial.py" blind "$private/blind-results" --inputs "$private/blind"
    & $py -B "$d/trial.py" public "$private/public-results"
    & $py -B "$d/historical.py" "$inputs/Edition02-source.zip" "$private/historical"
    & $py -B "$d/build.py" "$private/assembly" --inputs "$inputs"

A second full assembly, using exactly the source ZIP extracted from the first build, targets "$private/rebuilt". Compare assembly.json and every public/complete PDF byte-for-byte. Public and historical runs compare full expected outputs (plus reference transcript and transport hashes). Blind runs emit received bytes' digests and returns with no access to expected rows. Publish them immutably before coordinator opens separate oracle. Exact public predictions precede execution; no model-accuracy conclusions or native score claims follow.
