# Token grammar for the pinned Baidu decoder

This is a CPU specification for the proposed G1 treatment. The tokenizer has 128,831 addressable IDs, the language-model head has 129,280 columns, and a four-digit counter changes the legal successor within each coordinate. Eleven conceptual phases do not define eleven table rows. A complete byte recognizer and its exhaustive token composition are available in [token_proof.py](token_proof.py).

## Alphabet and language

The pin is Baidu revision `0480966938291445591f69f08a13b041c073a96a`, tokenizer.json SHA-256 `c55c165e32c5a67830362a53e1f548c8930dcc8469efa30ff3252a982799c589`. Q0 uses a ByteLevel BPE decoder. Invert its 256-glyph byte alphabet for byte-mapped pieces and retain literal UTF-8 for added spellings containing characters outside the alphabet, as its decoder does. CPU preflight checked all 128,831 isolated spellings against the installed decoder. Compose bytes across tokens before interpreting Unicode. For example, three separately encoded bytes for 表 decode together to one character, whereas separate one-ID decodes produce replacement characters.

For IDs 1 and 128827 the existing EOS and page guard still apply. The control excludes EOS from returned text. In the grammar EOS can stop in any prose-prefix state. Other printable special IDs have their real spelling, including 128828 `<BLOCK>`, 128829 `<FORK>`, and table tags in prose. The 449 IDs 128831…129279 have no tokenizer spelling. Reject all of them in G1 and count any such baseline/top-1 proposal. This explicit difference also applies in prose. Never index a compressed tokenizer vector directly with an unchecked LM index.

Read this grammar over the entire emitted stream from the first generated token. Prose includes arbitrary text, numbers, tables, punctuation, Unicode and partial UTF-8 at token boundaries. In prose, the complete ASCII byte string `<BLOCK>` begins a reserved structural header. Track the longest suffix that is a proper prefix of that string, including across ordinary tokens. An incomplete prefix alone at end of prose is text. Literal unescaped `<BLOCK>` printed on a source document is inherently ambiguous in this serialization. Count altered or non-representable literal cases as limitations of the format.

| Part of header after the marker | Accepted bytes |
| --- | --- |
| Label | One or more Unicode 15 word characters or ASCII hyphen, as in the original Python projection. Optionally, the exact case-sensitive label `title` may take `<LEVEL`, one or more ASCII digits, and `>`. |
| Opening | Zero or more ASCII whitespace bytes and `[`. |
| Coordinates 1–3, in order | Zero or more ASCII whitespace bytes, one to four ASCII digits, then `,`. |
| Coordinate 4 | Zero or more ASCII whitespace bytes, one to four ASCII digits, then `]`. With one to three digits, optional ASCII whitespace may precede the closing bracket. The four-digit rule forces `]` immediately. |
| Closing | The exact bytes `<FORK>` follow `]` immediately. Resume scanning prose on the next byte, including remaining bytes in the same token. |

ASCII whitespace here means space, tab, CR, LF, form feed and vertical tab. The original regex accepts additional Unicode whitespace and digits. These alternatives are deliberately outside the numeric language. Its positive syntax check allows 0000 and 9999. The independent geometry check must retain the projection’s range at most 999 and its increasing x and y pairs. Syntactic validity says nothing about the existence, size or content of a table. The original official projection does not admit the documented title annotation, while the frozen sensitivity rule does. Count both parser outcomes for every marker and retain raw coordinates. [Official projection](../../WP-0015/astra/formats.py) · [Frozen public title rule](https://github.com/jackgumpe/eledgercare/blob/0186467670074761a777602d77b53deff3451300/docs/research/WP-0015/astra/sensitivity-title-level/rescore.py)

## Construction and proof

Let `D(q,b)` be the partial byte transition, with an absorbing rejection row zero. The scanner, label lexer, four coordinates, structural literals and rejection state are generated in `Grammar`. For coordinate j the machine stores k in 0…4. For k=0 it accepts leading whitespace and requires a digit before leaving. For k=1…3 it permits another digit or its legal terminator. After k=4 the outgoing byte alphabet is exactly the required comma (j<4) or right bracket (j=4). A comma leads to the next slot's k=0. The right bracket leads to the mandatory fork literal. No prose byte can repair a malformed prefix inside a completed `<BLOCK>`.

The table for token v is the left-to-right fold of D over its complete byte spelling. Reaching zero at any interior byte rejects the **whole** token. For any two token strings u and v, applying their composed transitions equals applying D to the concatenated bytes, by induction on byte count. The exception EOS has its explicit stop rule above. This covers noncanonical alternate tokenizations, merged coordinate digits, delimiters bundled with other characters, and special tokens. It neither assumes one token per digit nor splits a chosen token at inference. Every byte has a single-byte token witness. Therefore every admissible byte path has a real-token realization, including continuations of a multibyte label. All 367 states (including rejection) were reachable from initial prose using the real token alphabet.

Four distinct remaining capacities plus k=0 are necessary for a direct counter in each slot. For fixed j, states k and l, k<l, can be distinguished by a suffix of 4−k additional digits and the remaining legal separators and coordinates. At k this completes the coordinate, at l it overflows. Different coordinate slots require different remaining numbers of commas before the fork. In addition, allowable whitespace, label recognition, split structural markers, UTF-8 label continuations and a rejection state affect the full count. This construction has 317 shared Unicode word-continuation states and 50 other states. It does not assert global DFA minimality.

| Actual token | State-dependent result |
| --- | --- |
| 764, space plus left bracket | After a label, opens the first coordinate. In a coordinate it fails. |
| 6895, `123` | At k=1 it reaches k=4. At k=2 it is rejected as a whole. |
| 6105, space plus right bracket | Closes the last coordinate after one to three digits. A fourth digit requires an immediate bracket. |
| 70962, `]<` | At the end of the fourth coordinate it closes the box and consumes the first byte of the fork literal. Its next required byte is `F`. Forcing atomic ID 128829 here would duplicate the less-than sign. |
| 18005, `,,` | Its second comma would produce an empty next coordinate, so it fails. |
| 3014, `][` | The second byte violates the mandatory fork after closing the last coordinate. |

The CPU oracle tests all 1,110 digit-only token IDs in all 20 coordinate/count states, checks the forced next byte after four digits by enumerating every candidate ID, and verifies full strings using both canonical tokenization and one-token-per-byte paths. The reference also checks EOS boundaries, malformed, truncated, Unicode, title, out-of-range and composite cases.

## Finite generation and guard conflicts

A fourth digit forces a delimiter at the next **byte**. The same selected token may contain that delimiter. This is a local termination property. Unbounded valid class names, title levels and whitespace allow cycles, and a decoder may reach its ordinary length or page boundary mid-header. A static token grammar alone cannot prove whole-header closure or a successful model stop.

Compute d(q), the minimum whole tokens from q to any complete prose state, by reverse shortest paths in the token graph. The longest such minimum among live states is 13 for this tokenizer. At a decision with R remaining freely generatable token slots up to the next forced page/EOS or output-limit boundary, require a legal candidate with d(next) ≤ R−1. Intersect this structural rule with the original 35-gram and per-page guards. Include first-token selection and split-marker states. The operator must prebind the precise remaining budget from the original per-row emitted count, effective context and current page length, accounting for whether the next position is already reserved for a forced control. For a forced control, check the actual ID separately and require a complete header before accepting it. Keep the original EOS/length/page acceptance conditions.

Concretely, after the original guard accounts for the previous token, let n be the number of emitted tokens, N the effective generation cap, p the page length since its last atomic marker, and P the configured page cap. Before an ordinary decision use R=min(N−n, P−p), with P−p omitted when the page cap is disabled. If the original guard already forces a control because of the page cap or marker overrun, test just that control at a complete-header boundary. A voluntarily emitted atomic page marker can reset the page budget only after its legal selection. The total cap keeps decreasing. A token limit reached without the original EOS/stop condition remains an incomplete window.

With R decreasing by one along any unfinished header, this invariant forces a complete prose state by R=0 whenever eligible finite scores exist throughout. It prevents starting a header that cannot finish in the available budget. It does not force the model to emit EOS, exempt a token from n-gram policy or certify that a finite candidate always exists after the intersection. At page/sequence limits, incomplete UTF-8 label prefixes or all-ineligible logits must produce a recorded failure, with the raw prefix preserved. An all-masked `argmax` can otherwise silently select index zero. Treat NaN/+infinity as invalid input with a counted failure. For live selection preserve the control's FP32 comparison and tie breaking (lowest token ID); record pre- and post-grammar choices separately. At a raw EOS in prose, stop exactly once.

## Representation and storage

For every LM token v form its full transition vector over all states. Group v and w only if the vectors are identical in every state. This is an exact factorization, including zero for rejection. Build the class lookup once on CPU and upload immutable buffers before timing. `class_id[v]` indexes an unsigned-16 table `next[class_id[v], q]`. Positive next state means eligible subject to the boundary and original guards. Maintain the actual token ID independently so equal structural classes never coalesce logits, output IDs, page counters or EOS. The proof expanded the classification back to all 47,445,760 entries and checked exact equality in chunks.

| Representation | Bytes (1 MiB = 1,048,576 B) |
| --- | ---: |
| Proposed eleven-row M BF16 plus T int32, aligned to all 129,280 head logits | 8,532,480 (8.137 MiB) |
| Dense M/T for all 367 rows of this oracle | 284,674,560 (271.487 MiB) |
| Token-ID-to-class map, uint16[129280] | 258,560 |
| Exact transition classes, uint16[341,367] | 250,294 |
| Completion distance, uint16[367] | 734 |
| Four lane states, int32[4] | 16 |
| Total of these four compressed buffers | 509,604 (0.486 MiB) |
| B4 BF16 selected-mask rows alone if materialized | 1,034,240 |
| B4 FP32 score rows alone | 2,068,480 |

`M.index_select` and advanced indexing create output tensors in ordinary eager execution. The proposed pseudocode establishes neither zero allocations nor 3.3 MiB VRAM. A device implementation can fuse lookup, legality and greedy reduction using fixed-address scratch and a separate deterministic lower-ID tie break. Store raw top-2/margins in preallocated bounded telemetry. Count valid candidates, forced delimiters and invalid-ID proposals. An alternate implementation may materialize rows into preallocated scratch if it passes the same memory and timing limits. Independently verify actual immutable table bytes, dtype, aligned allocated/reserved bytes, extra buffers, high-water device use, and any graph-pool bytes. All numbers above are CPU layout sizes. The design provides no observation of CUDA residency.

The canonical token-major uint16 transition hash is `a958eb39797ed1de73eb3fcefadfa325c65a1dc6a0a4e02f4c6dfddcafdbf118`. CPU reproduction pins the class table ordering, byte endianness and Unicode version. Future source acceptance requires the implementation to match all permitted/denied selections and next states, then pass budget and guard controls. A smaller language or more restrictive tokenizer decomposition needs its own disclosure and frozen comparison.
