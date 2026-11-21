# Explicit saved frames for a two-level ledger

Run the same reader in either observation mode. The CLI reads one UTF-8 JSON document at a time, in increasing page order. The caller supplies the input and output paths. Python 3.12.10, standard library only.

```powershell
python -B docs/research/WP-0021/test_read_scope.py -v
python -B docs/research/WP-0021/read_scope.py --mode grid input.json grid.json
python -B docs/research/WP-0021/read_scope.py --mode grid-words input.json grid-words.json
```

## Events and state

The observation contract supplies ordered lines of literal source words, one-based source references, top-left bounding boxes in document points and page-local detected rule coordinates. A body line contains one token per occupied cell, in reading order, with an observed final amount. The first three cells may be blank. The pilot assumes left-aligned header and body words and a constant physical layout for each scope throughout a document. It consumes idealized word observations and precomputed detected rules.

The reader copies the banner value words following `Property:` and `Unit:` in the preamble. A visible `Ledger` opens a parent frame. `Contractor detail` saves the parent and opens a child which shadows it. The next recognized four-word header in that frame supplies its own schema, word references, four left edges and any associated full rule signature. The declared typed headers are `Date Charge Unit Amount`, `Vendor WorkOrder Hrs Amount` and the shared `Date Description Ref Amount`. In the shared case the preceding heading supplies the identity. Scope and geometry are learned from those opening events. The schema vocabulary and the existence of the two nesting levels are given.

Both frames survive a page break. A unique ancestor match pops the child and restores the ancestor, including its original header references. A unique child match leaves both frames available. When several scopes are compatible or evidence is missing, emit a flagged, unbound row and keep the stack intact. A frame with an unobserved header blocks geometric fallthrough to the other frame. A new input file starts with empty state.

## Geometry and tie handling

- A row belongs to a candidate detected band only when all its words' vertical centers fall between the same two successive horizontal rules (top inclusive, bottom exclusive). Grid association uses the vertical positions only. More than one covering grid makes association ambiguous. A complete four-column grid has exactly five strictly increasing vertical rules.
- The current explicit heading applies directly inside the same observed, page-local complete grid when its schema appeared in that grid's first band. Outside that block, compare all five observed vertical rules against each open frame's header signature. Every corresponding coordinate must agree within **2 points**. The tolerance accommodates small rule-localization differences. It does not bridge a missing rule. Both live frames need a complete learned signature for this comparison.
- In `grid-words` mode, compare the body word starts against the ordered, observed header word starts. The last token must align to the last header. For preceding tokens, enumerate the ordered subsets of preceding columns, allowing blanks. Every present token must match within **3 points**. Every live frame needs observed anchors. No data vocabulary, number format, absolute page template or fixture identifier participates.
- A unique grid match binds the row in either mode. In combined mode its scope must also be compatible with the words. A contradictory unique grid and word reading abstains. A partial, overlapping, missing, unmatched or scope-ambiguous grid allows a unique complete word alignment to decide. If the evidence still cannot distinguish two frames, abstain. The reader also abstains when either banner value is missing.
- Both outputs preserve the last token's exact literal and source pointer plus every observed body word. A bound `column_role` is `Amount`; a flagged row has null scope and role. Banner value pointers exclude the separately recorded label pointer. The output also records heading/header pointers, the stack before and after each row and candidate scopes for each observation channel.

The reader has no basis to infer a silent geometry change, reinterpret a cropped amount, repair OCR spelling or reconstruct missing cells. A detector that supplies a convincing but false complete grid can therefore mislead grid-only. The author's constructed disagreement test demonstrates this failure mode and the combined-mode abstention. Independent replay and checks against the released observations follow candidate freeze.
