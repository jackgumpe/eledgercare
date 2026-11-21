# WP-0022 fixture custody

The fixtures are eight new synthetic two-page ledgers. The eight logical documents contribute 42 body rows. Their PNGs have 14 distinct byte sequences across 16 page appearances. All inputs use the same 612 × 792 point, 300 DPI page frame. The public commitment at `e207ee56ce1716abf6568ecdb254c6f8e0a89f74` pins the exact generator, key, raster bytes, renderer observations and pre-counts. Arm input consists of the manifest, the ordered renderer observations and the PNGs under `public/`.

## Reproduction

Run these commands from the repository root using a fresh empty output directory. The generator checks both system font files against their SHA-256 commitments. The reference environment uses Python 3.12.10, Pillow 13.0.0, FreeType 2.14.3 and zlib-ng exposed as 1.3.1.zlib-ng by Pillow.

```powershell
$python = 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe'
$fixture = 'docs/fixtures/WP-0022'
$output = Join-Path $env:TEMP ("wp0022-custody-" + [Guid]::NewGuid().ToString())
& $python -B "$fixture/generate.py" $output
& $python -B "$fixture/verify_custody.py" $fixture "$fixture/generate.py" $output
```

The verifier compares 28 files byte for byte, checks each input SHA-256, verifies every renderer source ID and checks for visible ink along each edge of all 354 layout word boxes. It also checks every value, blank, heading, amount header, property and unit against the intended rectangle. Its additional assertions cover all four matched note pairs, both siblings in two forms, and identical public inputs with opposite hidden continuations.

## Layout and ground truth

The generator places each word from its actual antialiased glyph mask and measures its tight nonzero extent in integer raster pixels before compositing. Multiplication by 0.24 projects either pixel axis into PDF points. Coordinates use top-left and half-open extents. Declared logical row rectangles enclose all wrapped lines and notes at that height. The separate amount rectangle lies inside the printed fourth column. A numeric note uses its own right-margin rectangle. The named crews have separate caption and schema-heading lines. The same `Contractor detail` heading text on successive siblings resolves to distinct printed regions.

The `setup` tag covers the two page-one body rows in each form. A `return` covers every row in a resumed parent block, including the hidden parent half of the ambiguous twins. The twin contains no observable return cue. `amount_header` points to the most recent valid printed Amount word in the intended section. A damaged post-break header leaves this reference on its earlier valid header. `property_region` and `unit_region` enclose the value tokens. Reported headings and identity references always carry their own source page number.

- N01 and N02 use compact common-schema headers, source-order body words, and left-anchored amounts. Their first post-break body row continues the child and their second resumes the parent.
- N03 and N04 rotate damaged/missing headers and which scope receives two- and three-line descriptions. All four wide/narrow pairs share the right edge within their own amount column. The same note is printed opposite one value and one true blank in each block. In two of those pairs its literal equals the populated cell. The other two pairs preserve a different literal.
- N05 and N06 resume the parent for one row between two named contractors and return to it again after the second contractor. Both contractor instances use the same printed schema name and column geometry.
- N07 and N08 share identical raster bytes and ordered renderer observations, including both setup sheets. Their only substantive difference lies in the intended ownership of the continuation, which is absent from the page. Both targets require review.

A logical document appearance supplies its own context even when its page bytes are shared. The pre-count uses these appearances. Physical OCR scheduling uses the 14 distinct raster digests. Compact controls were specified from type and column positions before recognition. Their acceptance by a Windows OCR engine is an empirical outcome. Figures describe this deliberately balanced synthetic design.

The original offline drafts and visual contact sheet remain in owned custody scratch. The final reference inputs and their clean regeneration matched before either study arm. The custodian used no OCR, table detector or saved-frame reader in design, selection or verification. See the canonical custody report for release chronology.
