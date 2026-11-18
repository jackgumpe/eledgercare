"""Read only the original envelope and six published F01 synthetic observations."""

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SOURCES = {
    "Q0 author": "qualification/q0/harness/evidence/004-gpu-trial/9e73ef86/run-20261115T202627Z-eb5bf7da",
    "Q0 reviewer": "docs/reviews/WP-0005/eld-q0-reviewer/runtime-005/run-20261115T210422Z-565e2de9",
}


def original_metadata():
    run_root = Path(os.environ["LOCALAPPDATA"]) / "eLedgerCare" / "ocr-runs"
    envelopes = list(run_root.glob("*/runs/*/output/envelope.json"))
    if len(envelopes) != 1:
        raise ValueError("Expected the one original envelope")
    envelope = json.loads(envelopes[0].read_text(encoding="utf-8"))
    times = envelope["timings"]
    diag = envelope["diagnostics"]
    metadata = {
        key: times[key] for key in ("render_duration_ms", "load_duration_ms", "infer_duration_ms", "total_duration_ms")
    }
    metadata["other_worker_ms"] = times["total_duration_ms"] - sum(
        times[key] for key in ("render_duration_ms", "load_duration_ms", "infer_duration_ms")
    )
    for key in ("kernel_path", "prompt_token_count", "output_token_count", "page_marker_count"):
        metadata[key] = diag[key]
    return metadata


def historical_rows():
    rows = []
    for session, directory in SOURCES.items():
        for invocation in ("warmup", "warm1", "warm2"):
            path = Path(directory, "evidence", f"F01.{invocation}.observation.json")
            obs = json.loads((ROOT / path).read_text(encoding="utf-8"))
            native = obs["native"]
            wall = obs["timing"]["external_synchronized_wall_s"]["value"]
            decode = native["time_s"] - native["prefill_time_s"]
            steps = obs["cache"]["decode_steps_observed"]
            assert abs(obs["timing"]["decode_s"]["value"] - decode) < 1e-8
            rows.append({
                "session": session,
                "source": path.as_posix(),
                "label": invocation,
                "prompt_positions": native["prompt_len"],
                "output_tokens": native["output_tokens"],
                "decode_forward_steps": steps,
                "native_to_first_token_s": native["prefill_time_s"],
                "native_after_first_token_s": decode,
                "decode_steps_per_s": steps / decode,
                "synchronized_call_wall_s": wall,
                "native_outside_generation_s": wall - native["time_s"],
                "observer_callback_self_s": obs["observer_overhead"]["callback_ns"] / 1e9,
                "dense_prefill_calls": obs["kernel_path"]["dense_sdpa_calls"],
                "fp32_decode_attend_calls": obs["kernel_path"]["decode_attend_fp32_calls"],
            })
    return rows


if __name__ == "__main__":
    print(json.dumps({"original_worker": original_metadata(), "historical_synthetic": historical_rows()}, indent=2))
