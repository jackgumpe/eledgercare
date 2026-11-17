# Old-version control limitation in the first receipt probe

Published evidence `candidate-6d055395-return-01/return-probe.json` is unchanged. Its `old_first_failure` case failed while the test fake startup tried to write `synthetic-api.log` into a missing temporary log directory. Its `browser=0` correctly records that it never reached the intended old browser failure. The assertion named `old_first_failure_no_receipt_reproduced` only established receipt absence after that setup failure; it does **not** independently reproduce the old browser-failure path. The reviewer retracts that interpretation.

All eight new-candidate simulations reached `browser=1`. Seven independently reproduced the clean-return-false/non-null-returned-timestamp issue; those conclusions are unaffected. Root accepted the receipt semantics finding and assigned the author a forward correction. No live leaked resource or actual inference was observed.

[The separately frozen remaining guard probe](../helpers/probe_bound_006_guards_cpu.py) runs one targeted old-only control with its temporary log directory created before writing. It preserves the original receipt probe unchanged for the same eight-scenario new-candidate comparison. Prior independent /002 also retains its valid old browser-failure reproduction.
