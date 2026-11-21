# Paired witness rows

Each case includes every native or renderer line touching the truth row, in that arm's original processing order. Word rectangles use the 612 × 792 point frame. A renderer line string is the ordered words joined by one space when no separate text was supplied. W strings are the exact native OcrLine text. The reference after each word locates it in its arm and document.

A transition names the exact frame and banner snapshots in the appendix. The saved deltas are signed candidate x0 minus each saved Amount x0, in points. An absent anchor produces an undefined delta. Physical deltas use the observed word in the printed header region, regardless of whether the reader captured it.

This author-selected extract uses the coordinator's frozen post-key diagnostic. I reproduced all nine diagnostic JSON files and the scores byte for byte. The [full index](https://github.com/jackgumpe/eledgercare/blob/d7d3a5f717662e8e0980e86dd726911e7d04fa3e/docs/coordination/WP-0022/witnesses/index.json) contains the paired outcome for every target.

## N01-T01

Page 1 expects parent Amount "58.40". The row is [40, 184, 594, 214], the cell is [152, 184, 219, 214], and the note rectangles are []. Pair outcome is pass/fail.

The two printed header fragments reach W as separate lines, with body text between them. The parent heading is present. Its anchors stay empty. The amount and physical header have the same x0 in W.

First changed renderer word in the body band and its native match are recorded as `{"r":"p1:L5:W1","w":["p1:L5:W1"],"changes":["line-grouping"],"WminusR_Pt":[0.0,0.0,0.0,0.0]}`. The matched physical amount is `[{"r":"p1:L5:W4","w":["p1:L8:W2"],"changes":["rectangle"],"WminusR_Pt":[0.24,0.0,0.0,0.0]}]`. [Full document witness](https://github.com/jackgumpe/eledgercare/blob/d7d3a5f717662e8e0980e86dd726911e7d04fa3e/docs/coordination/WP-0022/witnesses/N01.json)

### Arm R

Observed physical Amount header word(s) are `[{"page":1,"line":4,"ref":"p1:L4:W4","x0":155.04}]`. The scorer returned `value_owned`.

**Line 1/5** `"May Inspection J24 58.40"`. State N01/R/4 → N01/R/4.

"May" p1:L5:W1 [42.96, 195.36, 62.16, 205.2] · "Inspection" p1:L5:W2 [71.04, 195.36, 117.12, 205.2] · "J24" p1:L5:W3 [132.0, 195.36, 148.32, 203.04] · "58.40" p1:L5:W4 [155.04, 195.36, 180.48, 203.04]

Terminal candidate `p1:L5:W4`. Saved header deltas parent 0.0. Physical header deltas [0.0]. Decision `same-headed-grid`, scope `parent`, flagged `False`. Grid evidence `{"reason":"same-headed-grid","candidates":["parent"]}`. Word evidence `{"reason":"aligned-words","candidates":["parent"]}`.

### Arm W

Observed physical Amount header word(s) are `[{"page":1,"line":7,"ref":"p1:L7:W2","x0":155.28}]`. The scorer returned `value_flagged`.

**Line 1/5** `"May Inspection"`. State N01/W/3 → N01/W/3.

"May" p1:L5:W1 [42.96, 195.36, 62.16, 205.2] · "Inspection" p1:L5:W2 [71.04, 195.36, 117.12, 205.2]

Terminal candidate `p1:L5:W2`. Saved header deltas parent undefined. Physical header deltas [-84.24]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 1/8** `"J24 58.40"`. State N01/W/3 → N01/W/3.

"J24" p1:L8:W1 [132.0, 195.36, 148.32, 203.04] · "58.40" p1:L8:W2 [155.28, 195.36, 180.48, 203.04]

Terminal candidate `p1:L8:W2`. Saved header deltas parent undefined. Physical header deltas [0.0]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

## N01-T02

Page 1 expects child Amount "65.20". The row is [84, 394, 594, 424], the cell is [196, 394, 263, 424], and the note rectangles are []. Pair outcome is pass/fail.

W captures this child header in one line. Every child column aligns, the grid identifies the child, and the amount is only 0.24 pt left of its saved child header. The parent's empty anchor vector makes the all-open-frames alignment check return missing-header-anchors.

First changed renderer word in the body band and its native match are recorded as `{"r":"p1:L9:W3","w":["p1:L11:W3"],"changes":["rectangle"],"WminusR_Pt":[0.0,0.0,-0.24,0.0]}`. The matched physical amount is `[{"r":"p1:L9:W4","w":["p1:L11:W4"],"changes":[],"WminusR_Pt":[0.0,0.0,0.0,0.0]}]`. [Full document witness](https://github.com/jackgumpe/eledgercare/blob/d7d3a5f717662e8e0980e86dd726911e7d04fa3e/docs/coordination/WP-0022/witnesses/N01.json)

### Arm R

Observed physical Amount header word(s) are `[{"page":1,"line":8,"ref":"p1:L8:W4","x0":198.96}]`. The scorer returned `value_owned`.

**Line 1/9** `"May Restoration G12 65.20"`. State N01/R/6 → N01/R/6.

"May" p1:L9:W1 [86.88, 405.36, 106.08, 415.2] · "Restoration" p1:L9:W2 [114.96, 405.36, 167.28, 413.04] · "G12" p1:L9:W3 [175.92, 405.36, 194.88, 413.04] · "65.20" p1:L9:W4 [198.96, 405.36, 224.4, 413.04]

Terminal candidate `p1:L9:W4`. Saved header deltas parent 43.92, child 0.0. Physical header deltas [0.0]. Decision `same-headed-grid`, scope `child`, flagged `False`. Grid evidence `{"reason":"same-headed-grid","candidates":["child"]}`. Word evidence `{"reason":"aligned-words","candidates":["child"]}`.

### Arm W

Observed physical Amount header word(s) are `[{"page":1,"line":10,"ref":"p1:L10:W4","x0":199.2}]`. The scorer returned `value_flagged`.

**Line 1/11** `"May Restoration G12 65.20"`. State N01/W/5 → N01/W/5.

"May" p1:L11:W1 [86.88, 405.36, 106.08, 415.2] · "Restoration" p1:L11:W2 [114.96, 405.36, 167.28, 413.04] · "G12" p1:L11:W3 [175.92, 405.36, 194.64, 413.04] · "65.20" p1:L11:W4 [198.96, 405.36, 224.4, 413.04]

Terminal candidate `p1:L11:W4`. Saved header deltas parent undefined, child -0.24. Physical header deltas [-0.24]. Decision `grid-word-disagreement`, scope `None`, flagged `True`. Grid evidence `{"reason":"same-headed-grid","candidates":["child"]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

## N01-T03

Page 2 expects child Amount "43.20". The row is [84, 95, 594, 125], the cell is [196, 95, 263, 125], and the note rectangles are []. Pair outcome is pass/fail.

Across the page break W retains the correctly anchored child. The parent is still unanchored. The grid check now also requires saved grid rules from all open frames and reports missing-header-grid. The amount box is identical across arms.

First changed renderer word in the body band and its native match are recorded as `{"r":"p2:L1:W1","w":["p2:L1:W1"],"changes":["line-grouping"],"WminusR_Pt":[0.0,0.0,0.0,0.0]}`. The matched physical amount is `[{"r":"p2:L1:W4","w":["p2:L2:W2"],"changes":[],"WminusR_Pt":[0.0,0.0,0.0,0.0]}]`. [Full document witness](https://github.com/jackgumpe/eledgercare/blob/d7d3a5f717662e8e0980e86dd726911e7d04fa3e/docs/coordination/WP-0022/witnesses/N01.json)

### Arm R

Observed physical Amount header word(s) are `[{"page":1,"line":8,"ref":"p1:L8:W4","x0":198.96}]`. The scorer returned `value_owned`.

**Line 2/1** `"May Rekeying T38 43.20"`. State N01/R/6 → N01/R/6.

"May" p2:L1:W1 [86.88, 106.32, 106.08, 116.16] · "Rekeying" p2:L1:W2 [114.96, 106.32, 157.44, 116.16] · "T38" p2:L1:W3 [175.92, 106.32, 193.44, 114.0] · "43.20" p2:L1:W4 [198.96, 106.32, 224.64, 114.0]

Terminal candidate `p2:L1:W4`. Saved header deltas parent 43.92, child 0.0. Physical header deltas [0.0]. Decision `grid-match`, scope `child`, flagged `False`. Grid evidence `{"reason":"grid-match","candidates":["child"]}`. Word evidence `{"reason":"aligned-words","candidates":["child"]}`.

### Arm W

Observed physical Amount header word(s) are `[{"page":1,"line":10,"ref":"p1:L10:W4","x0":199.2}]`. The scorer returned `value_flagged`.

**Line 2/1** `"May Rekeying"`. State N01/W/5 → N01/W/5.

"May" p2:L1:W1 [86.88, 106.32, 106.08, 116.16] · "Rekeying" p2:L1:W2 [114.96, 106.32, 157.44, 116.16]

Terminal candidate `p2:L1:W2`. Saved header deltas parent undefined, child -84.24. Physical header deltas [-84.24]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/2** `"T38 43.20"`. State N01/W/5 → N01/W/5.

"T38" p2:L2:W1 [175.92, 106.32, 193.44, 114.0] · "43.20" p2:L2:W2 [198.96, 106.32, 224.64, 114.0]

Terminal candidate `p2:L2:W2`. Saved header deltas parent undefined, child -0.24. Physical header deltas [-0.24]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

## N03-T03

Page 2 expects child Amount "12,450.00". The row is [68, 114, 594, 160], the cell is [381, 114, 498, 160], and the note rectangles are []. Pair outcome is fail/fail.

The wide value lands 8.64 pt left of the saved child Amount header in R. The grid selects the child. The frozen tolerance rejects the row, retains both frames, and applies its terminal-word rule again to the wrapped description. W separates the amount and never assembles either saved header. The amount box itself matches across arms.

First changed renderer word in the body band and its native match are recorded as `{"r":"p2:L2:W1","w":["p2:L2:W1"],"changes":["line-grouping","rectangle"],"WminusR_Pt":[0.0,0.0,-0.24,0.0]}`. The matched physical amount is `[{"r":"p2:L2:W4","w":["p2:L22:W1"],"changes":[],"WminusR_Pt":[0.0,0.0,0.0,0.0]}]`. [Full document witness](https://github.com/jackgumpe/eledgercare/blob/d7d3a5f717662e8e0980e86dd726911e7d04fa3e/docs/coordination/WP-0022/witnesses/N03.json)

### Arm R

Observed physical Amount header word(s) are `[{"page":1,"line":8,"ref":"p1:L8:W4","x0":456.72}]`. The scorer returned `value_flagged`.

**Line 2/2** `"Mar Replace K6 12,450.00"`. State N03/R/6 → N03/R/6.

"Mar" p2:L2:W1 [71.04, 125.28, 88.8, 132.96] · "Replace" p2:L2:W2 [150.96, 125.28, 188.4, 135.12] · "K6" p2:L2:W3 [322.08, 125.28, 333.84, 132.96] · "12,450.00" p2:L2:W4 [448.08, 125.28, 492.96, 134.4]

Terminal candidate `p2:L2:W4`. Saved header deltas parent 15.36, child -8.64. Physical header deltas [-8.64]. Decision `grid-word-disagreement`, scope `None`, flagged `True`. Grid evidence `{"reason":"grid-match","candidates":["child"]}`. Word evidence `{"reason":"unaligned-words","candidates":[]}`.

**Line 2/3** `"valve packing"`. State N03/R/6 → N03/R/6.

"valve" p2:L3:W1 [150.96, 141.36, 175.2, 149.04] · "packing" p2:L3:W2 [178.32, 141.36, 213.36, 151.2]

Terminal candidate `p2:L3:W2`. Saved header deltas parent -254.4, child -278.4. Physical header deltas [-278.4]. Decision `grid-word-disagreement`, scope `None`, flagged `True`. Grid evidence `{"reason":"grid-match","candidates":["child"]}`. Word evidence `{"reason":"unaligned-words","candidates":[]}`.

### Arm W

Observed physical Amount header word(s) are `[{"page":1,"line":20,"ref":"p1:L20:W1","x0":456.96}]`. The scorer returned `value_flagged`.

**Line 2/2** `"Mar"`. State N03/W/4 → N03/W/4.

"Mar" p2:L2:W1 [71.04, 125.28, 88.56, 132.96]

Terminal candidate `p2:L2:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-385.92]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/9** `"Replace"`. State N03/W/4 → N03/W/4.

"Replace" p2:L9:W1 [150.96, 125.28, 188.4, 135.12]

Terminal candidate `p2:L9:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-306.0]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/10** `"valve packing"`. State N03/W/4 → N03/W/4.

"valve" p2:L10:W1 [150.96, 141.36, 175.2, 149.04] · "packing" p2:L10:W2 [178.56, 141.36, 213.36, 151.2]

Terminal candidate `p2:L10:W2`. Saved header deltas parent undefined, child undefined. Physical header deltas [-278.4]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/22** `"12,450.00"`. State N03/W/4 → N03/W/4.

"12,450.00" p2:L22:W1 [448.08, 125.28, 492.96, 134.4]

Terminal candidate `p2:L22:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-8.88]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

## N03-T04

Page 2 expects child Amount "9.00". The row is [68, 162, 594, 192], the cell is [381, 162, 498, 192], and the note rectangles are [[516,162,594,192]]. Pair outcome is fail/fail.

The correctly printed amount and its right-margin note both say 9.00. R proposes its fifth, terminal word from the margin. The four-anchor alignment rejects it. W isolates the two sources as different native lines. The correct cell word also remains unposted.

First changed renderer word in the body band and its native match are recorded as `{"r":"p2:L4:W1","w":["p2:L3:W1"],"changes":["line-grouping","rectangle"],"WminusR_Pt":[0.0,0.0,-0.24,0.0]}`. The matched physical amount is `[{"r":"p2:L4:W4","w":["p2:L23:W1"],"changes":["rectangle"],"WminusR_Pt":[0.24,0.0,0.0,0.0]}]`. [Full document witness](https://github.com/jackgumpe/eledgercare/blob/d7d3a5f717662e8e0980e86dd726911e7d04fa3e/docs/coordination/WP-0022/witnesses/N03.json)

### Arm R

Observed physical Amount header word(s) are `[{"page":1,"line":8,"ref":"p1:L8:W4","x0":456.72}]`. The scorer returned `other_word_flagged`.

**Line 2/4** `"Mar Delivery D9 9.00 9.00"`. State N03/R/6 → N03/R/6.

"Mar" p2:L4:W1 [71.04, 173.28, 88.8, 180.96] · "Delivery" p2:L4:W2 [150.96, 173.28, 188.4, 183.12] · "D9" p2:L4:W3 [322.08, 173.28, 334.56, 180.96] · "9.00" p2:L4:W4 [473.28, 173.28, 492.96, 180.96] · "9.00" p2:L4:W5 [533.04, 173.28, 552.72, 180.96]

Terminal candidate `p2:L4:W5`. Saved header deltas parent 100.32, child 76.32. Physical header deltas [76.32]. Decision `grid-word-disagreement`, scope `None`, flagged `True`. Grid evidence `{"reason":"grid-match","candidates":["child"]}`. Word evidence `{"reason":"unaligned-words","candidates":[]}`.

### Arm W

Observed physical Amount header word(s) are `[{"page":1,"line":20,"ref":"p1:L20:W1","x0":456.96}]`. The scorer returned `value_flagged`.

**Line 2/3** `"Mar"`. State N03/W/4 → N03/W/4.

"Mar" p2:L3:W1 [71.04, 173.28, 88.56, 180.96]

Terminal candidate `p2:L3:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-385.92]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/11** `"Delivery"`. State N03/W/4 → N03/W/4.

"Delivery" p2:L11:W1 [150.96, 173.28, 188.4, 183.12]

Terminal candidate `p2:L11:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-306.0]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/23** `"9.00"`. State N03/W/4 → N03/W/4.

"9.00" p2:L23:W1 [473.52, 173.28, 492.96, 180.96]

Terminal candidate `p2:L23:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [16.56]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/26** `"9.00"`. State N03/W/4 → N03/W/4.

"9.00" p2:L26:W1 [533.28, 173.28, 552.72, 180.96]

Terminal candidate `p2:L26:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [76.32]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

## N03-T06

Page 2 expects parent Amount "(7,814.60)". The row is [40, 379, 594, 441], the cell is [353, 379, 474, 441], and the note rectangles are []. Pair outcome is fail/fail.

The returning parent is still the first saved frame in R and the grid uniquely selects it. The parenthesized amount starts 10.56 pt left of the saved parent header. The first line and both continuation lines are rejected and retain both frames. W preserves the printed amount but has no saved parent headers.

First changed renderer word in the body band and its native match are recorded as `{"r":"p2:L6:W1","w":["p2:L5:W1"],"changes":["line-grouping","rectangle"],"WminusR_Pt":[0.0,0.0,-0.24,0.0]}`. The matched physical amount is `[{"r":"p2:L6:W4","w":["p2:L24:W1"],"changes":["rectangle"],"WminusR_Pt":[0.0,0.0,-0.24,0.0]}]`. [Full document witness](https://github.com/jackgumpe/eledgercare/blob/d7d3a5f717662e8e0980e86dd726911e7d04fa3e/docs/coordination/WP-0022/witnesses/N03.json)

### Arm R

Observed physical Amount header word(s) are `[{"page":1,"line":4,"ref":"p1:L4:W4","x0":432.72}]`. The scorer returned `value_flagged`.

**Line 2/6** `"Mar Inspect K6 (7,814.60)"`. State N03/R/6 → N03/R/6.

"Mar" p2:L6:W1 [42.96, 390.24, 60.72, 397.92] · "Inspect" p2:L6:W2 [117.12, 390.24, 149.76, 400.08] · "K6" p2:L6:W3 [295.92, 390.24, 307.68, 397.92] · "(7,814.60)" p2:L6:W4 [422.16, 390.24, 468.96, 400.08]

Terminal candidate `p2:L6:W4`. Saved header deltas parent -10.56, child -34.56. Physical header deltas [-10.56]. Decision `grid-word-disagreement`, scope `None`, flagged `True`. Grid evidence `{"reason":"grid-match","candidates":["parent"]}`. Word evidence `{"reason":"unaligned-words","candidates":[]}`.

**Line 2/7** `"upper flue"`. State N03/R/6 → N03/R/6.

"upper" p2:L7:W1 [117.12, 408.48, 143.52, 416.16] · "flue" p2:L7:W2 [146.64, 406.32, 163.2, 414.0]

Terminal candidate `p2:L7:W2`. Saved header deltas parent -286.08, child -310.08. Physical header deltas [-286.08]. Decision `grid-word-disagreement`, scope `None`, flagged `True`. Grid evidence `{"reason":"grid-match","candidates":["parent"]}`. Word evidence `{"reason":"unaligned-words","candidates":[]}`.

**Line 2/8** `"and renew seal"`. State N03/R/6 → N03/R/6.

"and" p2:L8:W1 [117.12, 422.4, 133.68, 430.08] · "renew" p2:L8:W2 [137.28, 424.56, 165.36, 430.08] · "seal" p2:L8:W3 [168.48, 422.4, 186.72, 430.08]

Terminal candidate `p2:L8:W3`. Saved header deltas parent -264.24, child -288.24. Physical header deltas [-264.24]. Decision `grid-word-disagreement`, scope `None`, flagged `True`. Grid evidence `{"reason":"grid-match","candidates":["parent"]}`. Word evidence `{"reason":"unaligned-words","candidates":[]}`.

### Arm W

Observed physical Amount header word(s) are `[{"page":1,"line":18,"ref":"p1:L18:W1","x0":432.96}]`. The scorer returned `value_flagged`.

**Line 2/5** `"Mar"`. State N03/W/4 → N03/W/4.

"Mar" p2:L5:W1 [42.96, 390.24, 60.48, 397.92]

Terminal candidate `p2:L5:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-390.0]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/13** `"Inspect"`. State N03/W/4 → N03/W/4.

"Inspect" p2:L13:W1 [117.12, 390.24, 149.76, 400.08]

Terminal candidate `p2:L13:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-315.84]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/14** `"upper flue"`. State N03/W/4 → N03/W/4.

"upper" p2:L14:W1 [117.12, 408.48, 143.28, 416.16] · "flue" p2:L14:W2 [146.64, 406.32, 163.2, 414.0]

Terminal candidate `p2:L14:W2`. Saved header deltas parent undefined, child undefined. Physical header deltas [-286.32]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/15** `"and renew seal"`. State N03/W/4 → N03/W/4.

"and" p2:L15:W1 [117.12, 422.4, 133.68, 430.08] · "renew" p2:L15:W2 [137.52, 424.56, 165.36, 430.08] · "seal" p2:L15:W3 [168.48, 422.4, 186.72, 430.08]

Terminal candidate `p2:L15:W3`. Saved header deltas parent undefined, child undefined. Physical header deltas [-264.48]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/24** `"(7,814.60)"`. State N03/W/4 → N03/W/4.

"(7,814.60)" p2:L24:W1 [422.16, 390.24, 468.72, 400.08]

Terminal candidate `p2:L24:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-10.8]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

## N03-T07

Page 2 expects parent Amount "-8.75". The row is [40, 443, 594, 473], the cell is [353, 443, 474, 473], and the note rectangles are [[516,443,594,473]]. Pair outcome is fail/fail.

The negative amount and differently worded note occupy a single five-word R line. The terminal note 214.75 is 100.32 pt right of the saved parent header. W gives -8.75 and the note separate source lines. Neither arm posts the note.

First changed renderer word in the body band and its native match are recorded as `{"r":"p2:L9:W1","w":["p2:L6:W1"],"changes":["line-grouping","rectangle"],"WminusR_Pt":[0.0,0.0,-0.24,0.0]}`. The matched physical amount is `[{"r":"p2:L9:W4","w":["p2:L25:W1"],"changes":[],"WminusR_Pt":[0.0,0.0,0.0,0.0]}]`. [Full document witness](https://github.com/jackgumpe/eledgercare/blob/d7d3a5f717662e8e0980e86dd726911e7d04fa3e/docs/coordination/WP-0022/witnesses/N03.json)

### Arm R

Observed physical Amount header word(s) are `[{"page":1,"line":4,"ref":"p1:L4:W4","x0":432.72}]`. The scorer returned `other_word_flagged`.

**Line 2/9** `"Mar Delivery D9 -8.75 214.75"`. State N03/R/6 → N03/R/6.

"Mar" p2:L9:W1 [42.96, 454.32, 60.72, 462.0] · "Delivery" p2:L9:W2 [117.12, 454.32, 154.56, 464.16] · "D9" p2:L9:W3 [295.92, 454.32, 308.4, 462.0] · "-8.75" p2:L9:W4 [445.68, 454.32, 468.96, 462.0] · "214.75" p2:L9:W5 [533.04, 454.32, 564.24, 462.0]

Terminal candidate `p2:L9:W5`. Saved header deltas parent 100.32, child 76.32. Physical header deltas [100.32]. Decision `grid-word-disagreement`, scope `None`, flagged `True`. Grid evidence `{"reason":"grid-match","candidates":["parent"]}`. Word evidence `{"reason":"unaligned-words","candidates":[]}`.

### Arm W

Observed physical Amount header word(s) are `[{"page":1,"line":18,"ref":"p1:L18:W1","x0":432.96}]`. The scorer returned `value_flagged`.

**Line 2/6** `"Mar"`. State N03/W/4 → N03/W/4.

"Mar" p2:L6:W1 [42.96, 454.32, 60.48, 462.0]

Terminal candidate `p2:L6:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-390.0]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/16** `"Delivery"`. State N03/W/4 → N03/W/4.

"Delivery" p2:L16:W1 [117.12, 454.32, 154.56, 464.16]

Terminal candidate `p2:L16:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-315.84]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/25** `"-8.75"`. State N03/W/4 → N03/W/4.

"-8.75" p2:L25:W1 [445.68, 454.32, 468.96, 462.0]

Terminal candidate `p2:L25:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [12.72]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/28** `"214.75"`. State N03/W/4 → N03/W/4.

"214.75" p2:L28:W1 [533.04, 454.32, 564.24, 462.0]

Terminal candidate `p2:L28:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [100.08]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

## N05-T03

Page 2 expects child Amount "63.80". The row is [84, 56, 594, 86], the cell is [196, 56, 263, 86], and the note rectangles are []. Pair outcome is pass/fail.

Arm R still holds child A and posts its continuation. W delivers the child A description on page 2 lines 1 and 3, then processes the child B heading on line 7, then delivers child A's 63.80 on line 12. Both child frames lack anchor vectors at those decisions. The return problem is already present before the sibling update.

First changed renderer word in the body band and its native match are recorded as `{"r":"p2:L1:W1","w":["p2:L3:W1"],"changes":["line-grouping"],"WminusR_Pt":[0.0,0.0,0.0,0.0]}`. The matched physical amount is `[{"r":"p2:L1:W4","w":["p2:L12:W1"],"changes":[],"WminusR_Pt":[0.0,0.0,0.0,0.0]}]`. [Full document witness](https://github.com/jackgumpe/eledgercare/blob/d7d3a5f717662e8e0980e86dd726911e7d04fa3e/docs/coordination/WP-0022/witnesses/N05.json)

### Arm R

Observed physical Amount header word(s) are `[{"page":1,"line":8,"ref":"p1:L8:W4","x0":198.96}]`. The scorer returned `value_owned`.

**Line 2/1** `"Jun Lamps H2 63.80"`. State N05/R/6 → N05/R/6.

"Jun" p2:L1:W1 [86.88, 67.2, 102.96, 74.88] · "Lamps" p2:L1:W2 [114.96, 67.2, 145.44, 77.04] · "H2" p2:L1:W3 [175.92, 67.2, 188.4, 74.88] · "63.80" p2:L1:W4 [198.96, 67.2, 224.4, 74.88]

Terminal candidate `p2:L1:W4`. Saved header deltas parent 43.92, child 0.0. Physical header deltas [0.0]. Decision `grid-match`, scope `child`, flagged `False`. Grid evidence `{"reason":"grid-match","candidates":["child"]}`. Word evidence `{"reason":"aligned-words","candidates":["child"]}`.

### Arm W

Observed physical Amount header word(s) are `[{"page":1,"line":14,"ref":"p1:L14:W2","x0":199.2}]`. The scorer returned `value_flagged`.

**Line 2/1** `"Lamps"`. State N05/W/4 → N05/W/4.

"Lamps" p2:L1:W1 [114.96, 67.2, 145.44, 77.04]

Terminal candidate `p2:L1:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-84.24]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/3** `"Jun"`. State N05/W/4 → N05/W/4.

"Jun" p2:L3:W1 [86.88, 67.2, 102.96, 74.88]

Terminal candidate `p2:L3:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-112.32]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/12** `"63.80"`. State N05/W/5 → N05/W/5.

"63.80" p2:L12:W1 [198.96, 67.2, 224.4, 74.88]

Terminal candidate `p2:L12:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-0.24]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

## N05-T04

Page 2 expects parent Amount "82.10". The row is [40, 207, 594, 237], the cell is [152, 207, 219, 237], and the note rectangles are []. Pair outcome is pass/fail.

The single-row parent return selects and retains only the parent in R. W splits that row, keeps the two headings open on all three events, and has never captured a parent header. The W candidate and physical parent header share their left edge.

First changed renderer word in the body band and its native match are recorded as `{"r":"p2:L2:W1","w":["p2:L2:W1"],"changes":["line-grouping"],"WminusR_Pt":[0.0,0.0,0.0,0.0]}`. The matched physical amount is `[{"r":"p2:L2:W4","w":["p2:L5:W1"],"changes":["rectangle"],"WminusR_Pt":[0.24,0.0,0.0,0.0]}]`. [Full document witness](https://github.com/jackgumpe/eledgercare/blob/d7d3a5f717662e8e0980e86dd726911e7d04fa3e/docs/coordination/WP-0022/witnesses/N05.json)

### Arm R

Observed physical Amount header word(s) are `[{"page":1,"line":4,"ref":"p1:L4:W4","x0":155.04}]`. The scorer returned `value_owned`.

**Line 2/2** `"Jun Fees E3 82.10"`. State N05/R/6 → N05/R/4.

"Jun" p2:L2:W1 [42.96, 218.4, 59.04, 226.08] · "Fees" p2:L2:W2 [71.04, 218.4, 93.36, 226.08] · "E3" p2:L2:W3 [132.0, 218.4, 143.76, 226.08] · "82.10" p2:L2:W4 [155.04, 218.4, 180.48, 226.08]

Terminal candidate `p2:L2:W4`. Saved header deltas parent 0.0, child -43.92. Physical header deltas [0.0]. Decision `grid-match`, scope `parent`, flagged `False`. Grid evidence `{"reason":"grid-match","candidates":["parent"]}`. Word evidence `{"reason":"aligned-words","candidates":["parent"]}`.

### Arm W

Observed physical Amount header word(s) are `[{"page":1,"line":7,"ref":"p1:L7:W2","x0":155.28}]`. The scorer returned `value_flagged`.

**Line 2/2** `"Jun"`. State N05/W/4 → N05/W/4.

"Jun" p2:L2:W1 [42.96, 218.4, 59.04, 226.08]

Terminal candidate `p2:L2:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-112.32]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/4** `"Fees"`. State N05/W/4 → N05/W/4.

"Fees" p2:L4:W1 [71.04, 218.4, 93.36, 226.08]

Terminal candidate `p2:L4:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [-84.24]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

**Line 2/5** `"82.10"`. State N05/W/4 → N05/W/4.

"82.10" p2:L5:W1 [155.28, 218.4, 180.48, 226.08]

Terminal candidate `p2:L5:W1`. Saved header deltas parent undefined, child undefined. Physical header deltas [0.0]. Decision `missing-header-anchors`, scope `None`, flagged `True`. Grid evidence `{"reason":"missing-header-grid","candidates":[]}`. Word evidence `{"reason":"missing-header-anchors","candidates":[]}`.

## Exact before and after states

Each snapshot preserves frame order, heading and header references, left-edge anchors, saved rules, headed page and grid, and complete banner sources. Shared state numbers within one document and arm designate identical snapshots.

**N01/R/4**

```json
{"frames":[{"scope":"parent","headingRefs":["p1:L3:W1"],"headerRefs":["p1:L4:W1","p1:L4:W2","p1:L4:W3","p1:L4:W4"],"x0Anchors":[42.96,71.04,132.0,155.04],"rules":[38.5,66.5,127.5,150.5,220.0],"headerPage":1,"headedGrid":{"xs":[38.5,66.5,127.5,150.5,220.0],"ys":[157.0,183.0,215.0]}}],"banners":{"property":[["Rowan","Quay"],["p1:L1:W2","p1:L1:W3"],"p1:L1:W1"],"unit":[["Elm"],["p1:L2:W2"],"p1:L2:W1"]}}
```

**N01/R/6**

```json
{"frames":[{"scope":"parent","headingRefs":["p1:L3:W1"],"headerRefs":["p1:L4:W1","p1:L4:W2","p1:L4:W3","p1:L4:W4"],"x0Anchors":[42.96,71.04,132.0,155.04],"rules":[38.5,66.5,127.5,150.5,220.0],"headerPage":1,"headedGrid":{"xs":[38.5,66.5,127.5,150.5,220.0],"ys":[157.0,183.0,215.0]}},{"scope":"child","headingRefs":["p1:L7:W1","p1:L7:W2"],"headerRefs":["p1:L8:W1","p1:L8:W2","p1:L8:W3","p1:L8:W4"],"x0Anchors":[86.88,114.96,175.92,198.96],"rules":[83.0,111.0,172.0,195.0,264.0],"headerPage":1,"headedGrid":{"xs":[83.0,111.0,172.0,195.0,264.0],"ys":[367.0,393.5,425.0]}}],"banners":{"property":[["Rowan","Quay"],["p1:L1:W2","p1:L1:W3"],"p1:L1:W1"],"unit":[["Elm"],["p1:L2:W2"],"p1:L2:W1"]}}
```

**N01/W/3**

```json
{"frames":[{"scope":"parent","headingRefs":["p1:L3:W1"],"headerRefs":[],"x0Anchors":[],"rules":[],"headerPage":0,"headedGrid":null}],"banners":{"property":[["Rowan","Quay"],["p1:L1:W2","p1:L1:W3"],"p1:L1:W1"],"unit":[["Elm"],["p1:L2:W2"],"p1:L2:W1"]}}
```

**N01/W/5**

```json
{"frames":[{"scope":"parent","headingRefs":["p1:L3:W1"],"headerRefs":[],"x0Anchors":[],"rules":[],"headerPage":0,"headedGrid":null},{"scope":"child","headingRefs":["p1:L9:W1","p1:L9:W2"],"headerRefs":["p1:L10:W1","p1:L10:W2","p1:L10:W3","p1:L10:W4"],"x0Anchors":[86.88,114.96,175.92,199.2],"rules":[83.0,111.0,172.0,195.0,264.0],"headerPage":1,"headedGrid":{"xs":[83.0,111.0,172.0,195.0,264.0],"ys":[367.0,393.5,425.0]}}],"banners":{"property":[["Rowan","Quay"],["p1:L1:W2","p1:L1:W3"],"p1:L1:W1"],"unit":[["Elm"],["p1:L2:W2"],"p1:L2:W1"]}}
```

**N03/R/6**

```json
{"frames":[{"scope":"parent","headingRefs":["p1:L3:W1"],"headerRefs":["p1:L4:W1","p1:L4:W2","p1:L4:W3","p1:L4:W4"],"x0Anchors":[42.96,117.12,295.92,432.72],"rules":[38.5,113.0,292.0,352.0,474.5],"headerPage":1,"headedGrid":{"xs":[38.5,113.0,292.0,352.0,474.5],"ys":[157.0,183.0,215.0]}},{"scope":"child","headingRefs":["p1:L7:W1","p1:L7:W2"],"headerRefs":["p1:L8:W1","p1:L8:W2","p1:L8:W3","p1:L8:W4"],"x0Anchors":[71.04,150.96,322.08,456.72],"rules":[66.5,146.5,318.0,379.5,498.5],"headerPage":1,"headedGrid":{"xs":[66.5,146.5,318.0,379.5,498.5],"ys":[367.0,393.5,425.0]}}],"banners":{"property":[["Juniper","Gate"],["p1:L1:W2","p1:L1:W3"],"p1:L1:W1"],"unit":[["Bay"],["p1:L2:W2"],"p1:L2:W1"]}}
```

**N03/W/4**

```json
{"frames":[{"scope":"parent","headingRefs":["p1:L3:W1"],"headerRefs":[],"x0Anchors":[],"rules":[],"headerPage":0,"headedGrid":null},{"scope":"child","headingRefs":["p1:L9:W1","p1:L9:W2"],"headerRefs":[],"x0Anchors":[],"rules":[],"headerPage":0,"headedGrid":null}],"banners":{"property":[["Juniper","Gate"],["p1:L1:W2","p1:L1:W3"],"p1:L1:W1"],"unit":[["Bay"],["p1:L2:W2"],"p1:L2:W1"]}}
```

**N05/R/4**

```json
{"frames":[{"scope":"parent","headingRefs":["p1:L3:W1"],"headerRefs":["p1:L4:W1","p1:L4:W2","p1:L4:W3","p1:L4:W4"],"x0Anchors":[42.96,71.04,132.0,155.04],"rules":[38.5,66.5,127.5,150.5,220.0],"headerPage":1,"headedGrid":{"xs":[38.5,66.5,127.5,150.5,220.0],"ys":[157.0,183.0,215.0]}}],"banners":{"property":[["Copper","Walk"],["p1:L1:W2","p1:L1:W3"],"p1:L1:W1"],"unit":[["Yew"],["p1:L2:W2"],"p1:L2:W1"]}}
```

**N05/R/6**

```json
{"frames":[{"scope":"parent","headingRefs":["p1:L3:W1"],"headerRefs":["p1:L4:W1","p1:L4:W2","p1:L4:W3","p1:L4:W4"],"x0Anchors":[42.96,71.04,132.0,155.04],"rules":[38.5,66.5,127.5,150.5,220.0],"headerPage":1,"headedGrid":{"xs":[38.5,66.5,127.5,150.5,220.0],"ys":[157.0,183.0,215.0]}},{"scope":"child","headingRefs":["p1:L7:W1","p1:L7:W2"],"headerRefs":["p1:L8:W1","p1:L8:W2","p1:L8:W3","p1:L8:W4"],"x0Anchors":[86.88,114.96,175.92,198.96],"rules":[83.0,111.0,172.0,195.0,264.0],"headerPage":1,"headedGrid":{"xs":[83.0,111.0,172.0,195.0,264.0],"ys":[367.0,393.5,425.0]}}],"banners":{"property":[["Copper","Walk"],["p1:L1:W2","p1:L1:W3"],"p1:L1:W1"],"unit":[["Yew"],["p1:L2:W2"],"p1:L2:W1"]}}
```

**N05/W/4**

```json
{"frames":[{"scope":"parent","headingRefs":["p1:L3:W1"],"headerRefs":[],"x0Anchors":[],"rules":[],"headerPage":0,"headedGrid":null},{"scope":"child","headingRefs":["p1:L9:W1","p1:L9:W2"],"headerRefs":[],"x0Anchors":[],"rules":[],"headerPage":0,"headedGrid":null}],"banners":{"property":[["Copper","Walk"],["p1:L1:W2","p1:L1:W3"],"p1:L1:W1"],"unit":[["Yew"],["p1:L2:W2"],"p1:L2:W1"]}}
```

**N05/W/5**

```json
{"frames":[{"scope":"parent","headingRefs":["p1:L3:W1"],"headerRefs":[],"x0Anchors":[],"rules":[],"headerPage":0,"headedGrid":null},{"scope":"child","headingRefs":["p2:L7:W1","p2:L7:W2"],"headerRefs":[],"x0Anchors":[],"rules":[],"headerPage":0,"headedGrid":null}],"banners":{"property":[["Copper","Walk"],["p1:L1:W2","p1:L1:W3"],"p1:L1:W1"],"unit":[["Yew"],["p1:L2:W2"],"p1:L2:W1"]}}
```
