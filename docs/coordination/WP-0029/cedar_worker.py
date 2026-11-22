"""Enter the exclusive Windows job before loading the exact previous capture implementation."""
from pathlib import Path
import os
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main(path, digest, job_name):
    sys.path.insert(0, str(ROOT / "qualification/baseline"))
    import winjob
    winjob.join(job_name)
    sys.path.insert(0, str(HERE))
    import cedar_plan as c
    c.require(c.guard.sha(path) == digest, "Changed plan")
    plan = c.read(path)
    folder = c.OUTPUT / "sensor"
    c.require(folder.resolve(strict=True) == folder and Path.cwd() == ROOT and
              {p.name for p in folder.iterdir()} == {"cache"} and
              all(p.is_dir() and p.resolve() == p for p in (folder/"cache").rglob("*")), "Fresh worker cache")
    sys.path.insert(0, str(ROOT / "docs/research/WP-0026"))
    import worker
    original_warmup = worker.run_warmup

    def validate(bound):
        fields = c.execution_fields()
        c.require(set(bound) == set(fields) | {"candidate","environment"} and
                  all(bound[k] == v for k,v in fields.items()), "Unbound model/fixture/schedule")
        c.require(c.git("rev-parse","HEAD:docs/research/WP-0024/sensor") == bound["sensor_tree"]
                  and c.guard.sha(Path(worker.__file__)) == bound["runner_sha256"], "Acquisition revision")

    def verify_w0(*args):
        warm = original_warmup(*args)
        c.require(warm["success"] and warm["emitted"] == 62 and warm["through_eos_sha256"] == c.WARM_TOKENS,
                  "W0 differs from accepted native tokens; Cedar withheld")
        return warm

    worker.validate_plan = validate
    worker.run_warmup = verify_w0
    os.chdir(folder)
    sys.stdout.reconfigure(encoding="utf8")
    sys.stderr.reconfigure(encoding="utf8")
    worker.conduct(plan, digest, folder)


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(strict=True), sys.argv[2], sys.argv[3])
