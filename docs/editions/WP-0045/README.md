# Targeted recurrent depth, Research Edition 02.1

The three operative amendments address the selection and publication of native decoder state, score preservation across two guards, and the information gained from a new noisy read. Paper I gives the mathematical decision, Paper II connects it to the original four concepts, and Paper III gives the falsifying observations and review return. Each PDF includes the complete amended definitions, proof sketches, worked boundaries and predecessor bindings.

| Paper | Public artifact | Authoring source |
| --- | --- | --- |
| I, Mathematical specification and proofs | [Amendment I](papers/Amendment-I-02.1.pdf) | [Paper I](paper-I.md) |
| II, Integrated concepts and experiments | [Amendment II](papers/Amendment-II-02.1.pdf) | [Paper II](paper-II.md) |
| III, Coordinator handoff and review | [Amendment III](papers/Amendment-III-02.1.pdf) | [Paper III](paper-III.md) |

The supplied research team prepared the original editions for Jack Gumpel. Gemini authored the seven-page advisory return on Edition 02. Local author eld-depth-author prepared the 02.1 amendments. The exact earlier PDFs, all original attachments and advisory are retained in local complete editions. Three independent references identify the arguments and evidentiary basis. [Predecessor hashes](../../coordination/WP-0045/source-pins.json) · [Native score and guard contract](../../research/WP-0042/scoring.md) · [Native cutpoints](../../research/WP-0042/source-cuts.md)

The section of each PDF headed by its paper-specific research question is followed by the shared operative clauses and binding appendix. Prior prose and listings on A1, A2 and C1 yield to those sections. All other definitions and proofs carry forward at the exact bound revision. The common TeX overlay and profile are situated over their pinned predecessor bytes, yielding fully materialized local files in the amended source ZIP. [Operative shared text](shared.md) · [Amended equations](model-02.1.tex) · [Machine-readable overlay](profile-02.1.json)

## Reproduction

From this directory, use CPython 3.12.10 and pypdf 6.16.2 for assembly. Set PYTHONHASHSEED=0 on the building process. All destinations must be fresh directories. INPUTS contains the exact three original PDFs, the Gemini advisory, Edition02-source.zip and companions.json. If staged plaintext or unzipped source is present, the build also verifies it against the actual PDFs and ZIP. Generate public supplements with the same command omitting the inputs flag.

    python -B build.py OUT --inputs INPUTS
    python -B historical.py INPUTS/Edition02-source.zip HISTORY
    python -B trial.py public PUBLIC-RETURNS

OUT contains three public supplements, three complete private PDFs, the amended source ZIP, and assembly.json with page counts, artifact digests and individual attachment hashes. Paper III embeds the two new complete companions and a digest manifest, alongside the intact old editions and submitted advisory. Extract Edition02.1-source.zip and run the first command using edition021/build.py to rebuild from the retained material. [Public finite inputs and separately specified expected rows](fixtures.json)

HISTORY contains original reference code, fixture and expected-output bytes, actual raw standard output, the canonical-LF transcript and comparison metadata. The raw Windows stream may contain CRLF. Only that line-ending conversion is admitted and recorded. The amended oracle has one normal entry for label-free objects. For example on Windows, supply JSON over standard input as shown below.

    '{"clause":"C1","mode":"exact","F":[[2,5]]}' | python -B clauses.py

Blind mode wraps the same evaluate() function, loads the fixed ID list from the coordinator's schedule, and maps each returned ID to its exact input-byte digest. A fresh investigator can implement the wire independently before comparing results. [Frozen interchange](../../coordination/WP-0045/wire.md) · [Candidate predictions and commands](freeze.md)
