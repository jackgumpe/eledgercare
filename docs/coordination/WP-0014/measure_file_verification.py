"""Time the shipping model-file verifier without importing Torch or opening a document."""

import argparse
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("q0", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root / "workers/local_ocr"))
    from local_ocr import protocol, verify_runtime

    manifest, manifest_sha = verify_runtime.load_json_checked(protocol.MODEL_MANIFEST_PATH, None, "model")
    model = args.q0 / "models" / manifest["model_dir_basename"]
    notices = args.q0 / "notices" / ("Unlimited-OCR-2_" + manifest["revision"])
    measurements = []
    original = verify_runtime.file_digests

    def timed_digests(path, **kwargs):
        started = time.perf_counter_ns()
        result = original(path, **kwargs)
        measurements.append({"file": path.name, "bytes": result["size"],
                             "elapsed_ms": (time.perf_counter_ns() - started) / 1e6})
        return result

    with args.output.open("x", encoding="utf-8") as stream:
        started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        verify_runtime.file_digests = timed_digests
        start = time.perf_counter_ns()
        try:
            verify_runtime.normalize_and_verify_model_dir(str(model), str(notices), manifest)
        finally:
            verify_runtime.file_digests = original
        hash_ms = (time.perf_counter_ns() - start) / 1e6
        start = time.perf_counter_ns()
        verify_runtime.verify_model_sources_ast_safety(model)
        ast_ms = (time.perf_counter_ns() - start) / 1e6
        receipt = {"started_utc": started_utc, "source": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "worker_source_digest": protocol.compute_worker_source_sha256(),
            "model_revision": manifest["revision"], "manifest_sha256": manifest_sha,
            "verified_files_and_notices_ms": hash_ms, "source_ast_checks_ms": ast_ms,
            "verified_bytes": sum(item["bytes"] for item in measurements), "files": measurements,
            "scope": "Separate CPU file-verification run. Filesystem cache state uncontrolled."}
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
        print(f"Verified {receipt['verified_bytes']:,} bytes in {hash_ms / 1000:.3f}s; AST {ast_ms / 1000:.3f}s.")


if __name__ == "__main__":
    main()
