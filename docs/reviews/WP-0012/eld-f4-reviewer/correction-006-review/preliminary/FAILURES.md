# Preserved preliminary native probe failures

`native-attempt-01` ran frozen helper source `055486fe09f3ca0d848a1c00f7e08258508ca278` and exited 1 before unit tests. The inherited old-/001 baseline compared the actual `(key, SHA)` extractor result with a SHA string. This was a test representation defect, not a product regression. It had already reproduced the old startup process/handle leaks; its owned benign children were reaped, reviewer ports were idle, PostgreSQL status was stopped, and runtime runs remained empty.

Native [old baseline adaptation](../helpers/probe_old_001_baseline_native.py) fixes tuple unpacking while preserving the original Carbon probe file and this failed execution. No mutable correction /006 was executed or evaluated. Subsequent preparation execution uses a new evidence directory after another source freeze.
