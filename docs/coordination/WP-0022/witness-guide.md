# WP-0022 paired witness guide

Each locator names a logical body row in the ground-truth key. Every physical line touching the row appears below in reader order. Rectangles are top-left PDF points. The last candidate, its distance from the intended printed Amount header, and frame states immediately before and after the line come from a replay that reproduced every frozen prediction. State numbers resolve to complete frame records, including captured heading and header references, column anchors and grid rules in the linked document. The recorded W line text is the native Windows OCR line.

The machine-readable files also contain every target, the parent and child opening events, all saved states, and pairwise word correspondences with four-coordinate deltas. [All target locators](witnesses/index.json) · [Source-only literal and timing readback](diagnostic-readback.json)

## N01-T04 · A split parent header prevents return to the parent ledger.

On page one, the rendered parent header is one line. Windows emits “Date Description” on line 4 and “Ref Amount” on line 7, with other lines between. The parent frame exists by name, but its header and anchors were never captured. The correct amount is present on page two. [Full line, frame and comparison records](witnesses/N01.json)

Page 2, parent scope, value target, printed value `71.50`. Amount rectangle [152, 284, 219, 314]. Logical row rectangle [40, 284, 594, 314].

**R**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/2 `May Inspection R52 71.50` | p2:L2:W1 May [42.96, 295.2, 62.16, 305.04] · p2:L2:W2 Inspection [71.04, 295.2, 117.12, 305.04] · p2:L2:W3 R52 [132, 295.2, 150.24, 302.88] · p2:L2:W4 71.50 [155.04, 295.2, 180.24, 302.88] | p2:L2:W4, +0.00 pt | 6 → 4, grid-match |

State 4 contains parent (heading p1:L3:W1, typed header p1:L4:W1,p1:L4:W2,p1:L4:W3,p1:L4:W4, x₀ anchors [42.96, 71.04, 132.0, 155.04]) in outer-to-inner order.

State 6 contains parent (heading p1:L3:W1, typed header p1:L4:W1,p1:L4:W2,p1:L4:W3,p1:L4:W4, x₀ anchors [42.96, 71.04, 132.0, 155.04]) → child (heading p1:L7:W1,p1:L7:W2, typed header p1:L8:W1,p1:L8:W2,p1:L8:W3,p1:L8:W4, x₀ anchors [86.88, 114.96, 175.92, 198.96]) in outer-to-inner order.

**W**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/3 `May Inspection` | p2:L3:W1 May [42.96, 295.2, 62.16, 305.04] · p2:L3:W2 Inspection [71.04, 295.2, 117.12, 305.04] | p2:L3:W2, -84.24 pt | 5 → 5, missing-header-anchors |
| 2/4 `R52 71.50` | p2:L4:W1 R52 [132, 295.2, 150, 302.88] · p2:L4:W2 71.50 [155.04, 295.2, 180.24, 302.88] | p2:L4:W2, -0.24 pt | 5 → 5, missing-header-anchors |

State 5 contains parent (heading p1:L3:W1, typed header unobserved, x₀ anchors []) → child (heading p1:L9:W1,p1:L9:W2, typed header p1:L10:W1,p1:L10:W2,p1:L10:W3,p1:L10:W4, x₀ anchors [86.88, 114.96, 175.92, 199.2]) in outer-to-inner order.

## N01-T02 · A captured child is vetoed by its incomplete parent.

The rendered child and the Windows child both have a recognized four-word header. The Windows price aligns to the child within 0.24 pt. The grid identifies the child, but the word matcher requires anchors in every open frame, including the incomplete parent. [Full line, frame and comparison records](witnesses/N01.json)

Page 1, child scope, value target, printed value `65.20`. Amount rectangle [196, 394, 263, 424]. Logical row rectangle [84, 394, 594, 424].

**R**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 1/9 `May Restoration G12 65.20` | p1:L9:W1 May [86.88, 405.36, 106.08, 415.2] · p1:L9:W2 Restoration [114.96, 405.36, 167.28, 413.04] · p1:L9:W3 G12 [175.92, 405.36, 194.88, 413.04] · p1:L9:W4 65.20 [198.96, 405.36, 224.4, 413.04] | p1:L9:W4, +0.00 pt | 6 → 6, same-headed-grid |

State 6 contains parent (heading p1:L3:W1, typed header p1:L4:W1,p1:L4:W2,p1:L4:W3,p1:L4:W4, x₀ anchors [42.96, 71.04, 132.0, 155.04]) → child (heading p1:L7:W1,p1:L7:W2, typed header p1:L8:W1,p1:L8:W2,p1:L8:W3,p1:L8:W4, x₀ anchors [86.88, 114.96, 175.92, 198.96]) in outer-to-inner order.

**W**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 1/11 `May Restoration G12 65.20` | p1:L11:W1 May [86.88, 405.36, 106.08, 415.2] · p1:L11:W2 Restoration [114.96, 405.36, 167.28, 413.04] · p1:L11:W3 G12 [175.92, 405.36, 194.64, 413.04] · p1:L11:W4 65.20 [198.96, 405.36, 224.4, 413.04] | p1:L11:W4, -0.24 pt | 5 → 5, grid-word-disagreement |

State 5 contains parent (heading p1:L3:W1, typed header unobserved, x₀ anchors []) → child (heading p1:L9:W1,p1:L9:W2, typed header p1:L10:W1,p1:L10:W2,p1:L10:W3,p1:L10:W4, x₀ anchors [86.88, 114.96, 175.92, 199.2]) in outer-to-inner order.

## N01-T03 · The available child header also fails on a fragmented continuation.

The combined reader needs complete saved signatures for a grid match off the header page, and complete frame anchors for word alignment. Windows splits this row into two groups and the parent frame is still incomplete. [Full line, frame and comparison records](witnesses/N01.json)

Page 2, child scope, value target, printed value `43.20`. Amount rectangle [196, 95, 263, 125]. Logical row rectangle [84, 95, 594, 125].

**R**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/1 `May Rekeying T38 43.20` | p2:L1:W1 May [86.88, 106.32, 106.08, 116.16] · p2:L1:W2 Rekeying [114.96, 106.32, 157.44, 116.16] · p2:L1:W3 T38 [175.92, 106.32, 193.44, 114] · p2:L1:W4 43.20 [198.96, 106.32, 224.64, 114] | p2:L1:W4, +0.00 pt | 6 → 6, grid-match |

State 6 contains parent (heading p1:L3:W1, typed header p1:L4:W1,p1:L4:W2,p1:L4:W3,p1:L4:W4, x₀ anchors [42.96, 71.04, 132.0, 155.04]) → child (heading p1:L7:W1,p1:L7:W2, typed header p1:L8:W1,p1:L8:W2,p1:L8:W3,p1:L8:W4, x₀ anchors [86.88, 114.96, 175.92, 198.96]) in outer-to-inner order.

**W**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/1 `May Rekeying` | p2:L1:W1 May [86.88, 106.32, 106.08, 116.16] · p2:L1:W2 Rekeying [114.96, 106.32, 157.44, 116.16] | p2:L1:W2, -84.24 pt | 5 → 5, missing-header-anchors |
| 2/2 `T38 43.20` | p2:L2:W1 T38 [175.92, 106.32, 193.44, 114] · p2:L2:W2 43.20 [198.96, 106.32, 224.64, 114] | p2:L2:W2, -0.24 pt | 5 → 5, missing-header-anchors |

State 5 contains parent (heading p1:L3:W1, typed header unobserved, x₀ anchors []) → child (heading p1:L9:W1,p1:L9:W2, typed header p1:L10:W1,p1:L10:W2,p1:L10:W3,p1:L10:W4, x₀ anchors [86.88, 114.96, 175.92, 199.2]) in outer-to-inner order.

## N03-T03 · Right alignment exceeds the frozen tolerance on a wrapped child row.

On the rendered first physical line, the price is the final word but its left edge is 8.64 pt left of its header. The continuation line ends in a description token. Windows separately emits the price with an 8.88 pt leftward shift from its own observed header, while the active schemas lack anchors. [Full line, frame and comparison records](witnesses/N03.json)

Page 2, child scope, value target, printed value `12,450.00`. Amount rectangle [381, 114, 498, 160]. Logical row rectangle [68, 114, 594, 160].

**R**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/2 `Mar Replace K6 12,450.00` | p2:L2:W1 Mar [71.04, 125.28, 88.8, 132.96] · p2:L2:W2 Replace [150.96, 125.28, 188.4, 135.12] · p2:L2:W3 K6 [322.08, 125.28, 333.84, 132.96] · p2:L2:W4 12,450.00 [448.08, 125.28, 492.96, 134.4] | p2:L2:W4, -8.64 pt | 6 → 6, grid-word-disagreement |
| 2/3 `valve packing` | p2:L3:W1 valve [150.96, 141.36, 175.2, 149.04] · p2:L3:W2 packing [178.32, 141.36, 213.36, 151.2] | p2:L3:W2, -278.40 pt | 6 → 6, grid-word-disagreement |

State 6 contains parent (heading p1:L3:W1, typed header p1:L4:W1,p1:L4:W2,p1:L4:W3,p1:L4:W4, x₀ anchors [42.96, 117.12, 295.92, 432.72]) → child (heading p1:L7:W1,p1:L7:W2, typed header p1:L8:W1,p1:L8:W2,p1:L8:W3,p1:L8:W4, x₀ anchors [71.04, 150.96, 322.08, 456.72]) in outer-to-inner order.

**W**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/2 `Mar` | p2:L2:W1 Mar [71.04, 125.28, 88.56, 132.96] | p2:L2:W1, -385.92 pt | 4 → 4, missing-header-anchors |
| 2/9 `Replace` | p2:L9:W1 Replace [150.96, 125.28, 188.4, 135.12] | p2:L9:W1, -306.00 pt | 4 → 4, missing-header-anchors |
| 2/10 `valve packing` | p2:L10:W1 valve [150.96, 141.36, 175.2, 149.04] · p2:L10:W2 packing [178.56, 141.36, 213.36, 151.2] | p2:L10:W2, -278.40 pt | 4 → 4, missing-header-anchors |
| 2/22 `12,450.00` | p2:L22:W1 12,450.00 [448.08, 125.28, 492.96, 134.4] | p2:L22:W1, -8.88 pt | 4 → 4, missing-header-anchors |

State 4 contains parent (heading p1:L3:W1, typed header unobserved, x₀ anchors []) → child (heading p1:L9:W1,p1:L9:W2, typed header unobserved, x₀ anchors []) in outer-to-inner order.

## N03-T04 · A same-height note becomes the last candidate on a populated row.

The rendered physical line ends with a margin number. The reader considers that final word for Amount and flags it. The printed amount has its own source identity even when the note carries the same digits. Windows places the price and note on separate lines, then flags both. [Full line, frame and comparison records](witnesses/N03.json)

Page 2, child scope, value target, printed value `9.00`. Amount rectangle [381, 162, 498, 192]. Logical row rectangle [68, 162, 594, 192].

**R**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/4 `Mar Delivery D9 9.00 9.00` | p2:L4:W1 Mar [71.04, 173.28, 88.8, 180.96] · p2:L4:W2 Delivery [150.96, 173.28, 188.4, 183.12] · p2:L4:W3 D9 [322.08, 173.28, 334.56, 180.96] · p2:L4:W4 9.00 [473.28, 173.28, 492.96, 180.96] · p2:L4:W5 9.00 [533.04, 173.28, 552.72, 180.96] | p2:L4:W5, +76.32 pt | 6 → 6, grid-word-disagreement |

State 6 contains parent (heading p1:L3:W1, typed header p1:L4:W1,p1:L4:W2,p1:L4:W3,p1:L4:W4, x₀ anchors [42.96, 117.12, 295.92, 432.72]) → child (heading p1:L7:W1,p1:L7:W2, typed header p1:L8:W1,p1:L8:W2,p1:L8:W3,p1:L8:W4, x₀ anchors [71.04, 150.96, 322.08, 456.72]) in outer-to-inner order.

**W**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/3 `Mar` | p2:L3:W1 Mar [71.04, 173.28, 88.56, 180.96] | p2:L3:W1, -385.92 pt | 4 → 4, missing-header-anchors |
| 2/11 `Delivery` | p2:L11:W1 Delivery [150.96, 173.28, 188.4, 183.12] | p2:L11:W1, -306.00 pt | 4 → 4, missing-header-anchors |
| 2/23 `9.00` | p2:L23:W1 9.00 [473.52, 173.28, 492.96, 180.96] | p2:L23:W1, +16.56 pt | 4 → 4, missing-header-anchors |
| 2/26 `9.00` | p2:L26:W1 9.00 [533.28, 173.28, 552.72, 180.96] | p2:L26:W1, +76.32 pt | 4 → 4, missing-header-anchors |

State 4 contains parent (heading p1:L3:W1, typed header unobserved, x₀ anchors []) → child (heading p1:L9:W1,p1:L9:W2, typed header unobserved, x₀ anchors []) in outer-to-inner order.

## N03-T06 · A wrapped parent amount fails despite a captured parent.

On renderer input the parent frame and column anchors survive. The first physical line carries the printed parenthetical value. Its left edge is 10.56 pt away from the saved amount header. Each following wrapped line also supplies a description token as its own terminal candidate. On Windows input, the first parent header was incomplete before this return. [Full line, frame and comparison records](witnesses/N03.json)

Page 2, parent scope, value target, printed value `(7,814.60)`. Amount rectangle [353, 379, 474, 441]. Logical row rectangle [40, 379, 594, 441].

**R**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/6 `Mar Inspect K6 (7,814.60)` | p2:L6:W1 Mar [42.96, 390.24, 60.72, 397.92] · p2:L6:W2 Inspect [117.12, 390.24, 149.76, 400.08] · p2:L6:W3 K6 [295.92, 390.24, 307.68, 397.92] · p2:L6:W4 (7,814.60) [422.16, 390.24, 468.96, 400.08] | p2:L6:W4, -10.56 pt | 6 → 6, grid-word-disagreement |
| 2/7 `upper flue` | p2:L7:W1 upper [117.12, 408.48, 143.52, 416.16] · p2:L7:W2 flue [146.64, 406.32, 163.2, 414] | p2:L7:W2, -286.08 pt | 6 → 6, grid-word-disagreement |
| 2/8 `and renew seal` | p2:L8:W1 and [117.12, 422.4, 133.68, 430.08] · p2:L8:W2 renew [137.28, 424.56, 165.36, 430.08] · p2:L8:W3 seal [168.48, 422.4, 186.72, 430.08] | p2:L8:W3, -264.24 pt | 6 → 6, grid-word-disagreement |

State 6 contains parent (heading p1:L3:W1, typed header p1:L4:W1,p1:L4:W2,p1:L4:W3,p1:L4:W4, x₀ anchors [42.96, 117.12, 295.92, 432.72]) → child (heading p1:L7:W1,p1:L7:W2, typed header p1:L8:W1,p1:L8:W2,p1:L8:W3,p1:L8:W4, x₀ anchors [71.04, 150.96, 322.08, 456.72]) in outer-to-inner order.

**W**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/5 `Mar` | p2:L5:W1 Mar [42.96, 390.24, 60.48, 397.92] | p2:L5:W1, -390.00 pt | 4 → 4, missing-header-anchors |
| 2/13 `Inspect` | p2:L13:W1 Inspect [117.12, 390.24, 149.76, 400.08] | p2:L13:W1, -315.84 pt | 4 → 4, missing-header-anchors |
| 2/14 `upper flue` | p2:L14:W1 upper [117.12, 408.48, 143.28, 416.16] · p2:L14:W2 flue [146.64, 406.32, 163.2, 414] | p2:L14:W2, -286.32 pt | 4 → 4, missing-header-anchors |
| 2/15 `and renew seal` | p2:L15:W1 and [117.12, 422.4, 133.68, 430.08] · p2:L15:W2 renew [137.52, 424.56, 165.36, 430.08] · p2:L15:W3 seal [168.48, 422.4, 186.72, 430.08] | p2:L15:W3, -264.48 pt | 4 → 4, missing-header-anchors |
| 2/24 `(7,814.60)` | p2:L24:W1 (7,814.60) [422.16, 390.24, 468.72, 400.08] | p2:L24:W1, -10.80 pt | 4 → 4, missing-header-anchors |

State 4 contains parent (heading p1:L3:W1, typed header unobserved, x₀ anchors []) → child (heading p1:L9:W1,p1:L9:W2, typed header unobserved, x₀ anchors []) in outer-to-inner order.

## N05-T03 · Windows emits a child A amount after a later child B heading.

The section-heading order and native column reading order separate the earlier amount from its row. Inspect the individual frame-state references before each candidate. A correct parent schema had never been captured in this arm. [Full line, frame and comparison records](witnesses/N05.json)

Page 2, child scope, value target, printed value `63.80`. Amount rectangle [196, 56, 263, 86]. Logical row rectangle [84, 56, 594, 86].

**R**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/1 `Jun Lamps H2 63.80` | p2:L1:W1 Jun [86.88, 67.2, 102.96, 74.88] · p2:L1:W2 Lamps [114.96, 67.2, 145.44, 77.04] · p2:L1:W3 H2 [175.92, 67.2, 188.4, 74.88] · p2:L1:W4 63.80 [198.96, 67.2, 224.4, 74.88] | p2:L1:W4, +0.00 pt | 6 → 6, grid-match |

State 6 contains parent (heading p1:L3:W1, typed header p1:L4:W1,p1:L4:W2,p1:L4:W3,p1:L4:W4, x₀ anchors [42.96, 71.04, 132.0, 155.04]) → child (heading p1:L7:W1,p1:L7:W2, typed header p1:L8:W1,p1:L8:W2,p1:L8:W3,p1:L8:W4, x₀ anchors [86.88, 114.96, 175.92, 198.96]) in outer-to-inner order.

**W**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/1 `Lamps` | p2:L1:W1 Lamps [114.96, 67.2, 145.44, 77.04] | p2:L1:W1, -84.24 pt | 4 → 4, missing-header-anchors |
| 2/3 `Jun` | p2:L3:W1 Jun [86.88, 67.2, 102.96, 74.88] | p2:L3:W1, -112.32 pt | 4 → 4, missing-header-anchors |
| 2/12 `63.80` | p2:L12:W1 63.80 [198.96, 67.2, 224.4, 74.88] | p2:L12:W1, -0.24 pt | 5 → 5, missing-header-anchors |

State 4 contains parent (heading p1:L3:W1, typed header unobserved, x₀ anchors []) → child (heading p1:L9:W1,p1:L9:W2, typed header unobserved, x₀ anchors []) in outer-to-inner order.

State 5 contains parent (heading p1:L3:W1, typed header unobserved, x₀ anchors []) → child (heading p2:L7:W1,p2:L7:W2, typed header unobserved, x₀ anchors []) in outer-to-inner order.

## N03-T05 · Blank and right-margin control.

The amount cell is truly empty. Both arms flag the margin note and leave the cell unposted. Neither output represents an explicit blank. [Full line, frame and comparison records](witnesses/N03.json)

Page 2, child scope, blank target, printed value `(empty)`. Amount rectangle [381, 194, 498, 224]. Logical row rectangle [68, 194, 594, 224].

**R**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/5 `Mar Allowance M1 9.00` | p2:L5:W1 Mar [71.04, 205.44, 88.8, 213.12] · p2:L5:W2 Allowance [150.96, 205.44, 198.72, 213.12] · p2:L5:W3 M1 [322.08, 205.44, 334.32, 213.12] · p2:L5:W4 9.00 [533.04, 205.44, 552.72, 213.12] | p2:L5:W4, +76.32 pt | 6 → 6, grid-word-disagreement |

State 6 contains parent (heading p1:L3:W1, typed header p1:L4:W1,p1:L4:W2,p1:L4:W3,p1:L4:W4, x₀ anchors [42.96, 117.12, 295.92, 432.72]) → child (heading p1:L7:W1,p1:L7:W2, typed header p1:L8:W1,p1:L8:W2,p1:L8:W3,p1:L8:W4, x₀ anchors [71.04, 150.96, 322.08, 456.72]) in outer-to-inner order.

**W**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/4 `Mar` | p2:L4:W1 Mar [71.04, 205.44, 88.56, 213.12] | p2:L4:W1, -385.92 pt | 4 → 4, missing-header-anchors |
| 2/12 `Allowance` | p2:L12:W1 Allowance [151.2, 205.44, 198.72, 213.12] | p2:L12:W1, -305.76 pt | 4 → 4, missing-header-anchors |
| 2/19 `MI` | p2:L19:W1 MI [322.08, 205.44, 334.32, 213.12] | p2:L19:W1, -134.88 pt | 4 → 4, missing-header-anchors |
| 2/27 `9.00` | p2:L27:W1 9.00 [533.28, 205.44, 552.72, 213.12] | p2:L27:W1, +76.32 pt | 4 → 4, missing-header-anchors |

State 4 contains parent (heading p1:L3:W1, typed header unobserved, x₀ anchors []) → child (heading p1:L9:W1,p1:L9:W2, typed header unobserved, x₀ anchors []) in outer-to-inner order.

## N07-T03 · Indistinguishable continuation control.

The visible twin N08 has the opposite intended scope. The renderer reports a geometric tie, while Windows flags the amount with incomplete frame anchors. Both outcomes satisfy the ambiguous-row safety criterion. [Full line, frame and comparison records](witnesses/N07.json)

Page 2, parent scope, ambiguous target, printed value `41.60`. Amount rectangle [152, 103, 219, 133]. Logical row rectangle [40, 103, 594, 133].

**R**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/1 `Jul Locks V2 41.60` | p2:L1:W1 Jul [42.96, 114.24, 55.44, 121.92] · p2:L1:W2 Locks [71.04, 114.24, 97.44, 121.92] · p2:L1:W3 V2 [132, 114.24, 144.48, 121.92] · p2:L1:W4 41.60 [155.04, 114.24, 180.72, 121.92] | p2:L1:W4, +0.00 pt | 6 → 6, tied-scopes |

State 6 contains parent (heading p1:L3:W1, typed header p1:L4:W1,p1:L4:W2,p1:L4:W3,p1:L4:W4, x₀ anchors [42.96, 71.04, 132.0, 155.04]) → child (heading p1:L7:W1,p1:L7:W2, typed header p1:L8:W1,p1:L8:W2,p1:L8:W3,p1:L8:W4, x₀ anchors [42.96, 71.04, 132.0, 155.04]) in outer-to-inner order.

**W**

| Page/line and native or renderer text | Ordered source words and point boxes | Candidate, Δx₀ to printed header | State before → after and decision |
| --- | --- | --- | --- |
| 2/1 `Jul` | p2:L1:W1 Jul [42.96, 114.24, 55.44, 121.92] | p2:L1:W1, -112.32 pt | 4 → 4, missing-header-anchors |
| 2/2 `Locks` | p2:L2:W1 Locks [71.04, 114.24, 97.44, 121.92] | p2:L2:W1, -84.24 pt | 4 → 4, missing-header-anchors |
| 2/3 `V2 41.60` | p2:L3:W1 V2 [132, 114.24, 144.24, 121.92] · p2:L3:W2 41.60 [155.04, 114.24, 180.72, 121.92] | p2:L3:W2, -0.24 pt | 4 → 4, missing-header-anchors |

State 4 contains parent (heading p1:L3:W1, typed header unobserved, x₀ anchors []) → child (heading p1:L10:W1,p1:L10:W2, typed header unobserved, x₀ anchors []) in outer-to-inner order.
