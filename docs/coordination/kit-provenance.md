# Supplied kit provenance

The eight files under docs/inputs/bootstrap-kit/ were copied byte-for-byte from the exact directory Jack supplied. The original manifest was preserved, not regenerated.

The seven manifest-listed input files were checked against the supplied files and their SHA-256 values. All seven copies match their supplied originals. Six inputs match their manifest hashes and sizes. The supplied 00-START-COORDINATOR.txt differs from the supplied manifest:

| Field | Supplied manifest | Actual supplied file / retained copy |
| --- | --- | --- |
| Bytes | 9288 | 9384 |
| SHA-256 | 42fb48f02b5e4b50b2faf79f594c3e401a3ddfbbc791b3bd96770c87ee2f68bd | 162cc5c3653b6d277e68087c4d0e3f8d7b4d38089bacced12040c2054989baa1 |

No prior version was recovered or guessed. Jack directly supplied the current start file as the instruction source; its text governs this handoff, with the discrepancy preserved as a provenance limitation. No substantive conflicting authority was identified between the current instructions and the remaining kit.

The first staged whitespace check reported trailing blank lines in six imported source files. Their exact bytes are intentional evidence, so .gitattributes preserves those inputs and disables whitespace-error checks only for that imported directory. Authored repository files remain checked. An initial remote-create command with --push refused to proceed because the whitespace gate had prevented the seed commit; no remote publication was claimed from that attempt.
