"""Independent, deterministic, standard-library CPU witnesses and original transport check."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import sys

SCRATCH = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0042/review")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def guard(history, width):
    """Index by actual complete 35-token words retained in the window."""
    window = history[-width:]
    index = {}
    for end in range(35, len(window) + 1):
        word = tuple(window[end - 35:end])
        index.setdefault(word[:-1], set()).add(word[-1])
    return index.get(tuple(history[-34:]), set())


def fibers(pairs):
    return all(len(set(values)) == 1 for _, rows in itertools.groupby(
        sorted(pairs), lambda item: item[0]) for values in [[out for _, out in rows]])


def layout():
    # Two strided private views intersect at source address 3, not at their logical offset zero.
    src = bytearray(8)
    cp = src[:]
    u, v = memoryview(cp)[1::2], memoryview(cp)[3:6]
    u[1] = 71
    assert (v[0], src[3]) == (71, 0)
    a = {"kv": src}
    b = a.copy()
    b["kv"] = cp
    assert a["kv"] is src and b["kv"] is cp
    alias = a
    alias["kv"] = cp
    assert a["kv"] is cp and src == bytearray(8)
    # Rebinding then restoring leaves the endpoint digest and topology unchanged.
    alias["kv"] = src
    assert a["kv"] is src
    return {"strided_read_source": [v[0], src[3]], "rebind_without_changed_old_storage": True,
            "offsets_bytes": [1445 * 128 * 2, 1445 * 10 * 128 * 2, 1445 * 128 * 4]}


def transition(state):
    return (*state, len(state) // 32)


def step_trace(local, bridge):
    n = 30
    rows = []
    for k in range(5):
        post = n + 1 + (local if k == 0 else 0)
        next_pre = post + (bridge if k == 0 else 0)
        rows.append((n, post, next_pre))
        n = next_pre
    return rows


def scores(raw, processed, allowed):
    if len(raw) != len(processed) or not allowed or not allowed <= set(range(len(raw))):
        return False
    return all(map(math.isfinite, raw)) and all(
        math.isfinite(value) if i in allowed else value == -math.inf
        for i, value in enumerate(processed))


def solve(required, observed):
    missing = set(required) - set(observed)
    bad = {i for i, ok in observed.items() if i in required and not ok}
    assert required and set(observed) <= set(required)
    return ("M" if bad else "U" if missing else "P", tuple(sorted(missing)), tuple(sorted(bad)))


def main():
    assert sys.flags.optimize == 0
    script = SCRATCH / "six_controls.py"
    expected = (SCRATCH / "six-results.txt").read_bytes()
    proc = subprocess.run([sys.executable, "-IB", str(script)], cwd=SCRATCH, capture_output=True)
    (SCRATCH / "six.stdout.bin").write_bytes(proc.stdout)
    (SCRATCH / "six.stderr.bin").write_bytes(proc.stderr)
    normalized = proc.stdout.replace(b"\r\n", b"\n")
    assert proc.returncode == 0 and proc.stderr == b"" and normalized == expected
    forced = subprocess.run([sys.executable, "-IB", "-c",
        r"import runpy,sys;sys.stdout.reconfigure(newline='\n');runpy.run_path(sys.argv[1],run_name='__main__')",
        str(script)], cwd=SCRATCH, capture_output=True)
    assert forced.returncode == 0 and forced.stderr == b"" and forced.stdout == expected
    (SCRATCH / "six.explicit-lf.bin").write_bytes(forced.stdout)
    p = list(range(200, 234))
    assert guard(p + [1328] + p, 128) == {1328}
    assert guard(p + [6] + p, 128) == {6}
    assert not guard([6,1449,16,1328] * 2, 128)
    long_history = p + [1328] + list(range(300,500)) + p
    assert guard(long_history, 128) == set() and guard(long_history, 1024) == {1328}
    assert fibers([((t, flag), (t+1, flag)) for t, flag in itertools.product(range(2), repeat=2)])
    assert not fibers([((t, t+1), (t+1, flag)) for t, flag in itertools.product(range(2), repeat=2)])
    assert all(len((t+1,)*11+(t,)) == 12 and t//32 == 45 for t in range(1445,1450))
    memory = layout()
    assert memory["offsets_bytes"] == [369920,3699200,739840]
    entry = (0,) * 31
    clean, second = transition(entry), transition(transition(entry))
    assert len(clean) == 32 and clean[-1] == 0 and len(second) == 33 and second[-1] == 1
    assert transition(entry) == clean and (32,32,second[-1]) != (32,31,clean[-1])
    ref = step_trace(0,0)
    observed = {str((a,b)): step_trace(a,b) for a,b in ((1,0),(0,1),(1,-1))}
    assert observed["(0, 1)"][0] == (30,31,32)
    assert observed["(1, 0)"][0] == (30,32,32)
    assert observed["(1, -1)"][0] == (30,32,31)
    assert [x[0] for x in ref] == [x[0] for x in observed["(1, -1)"]]
    # A within-transition change and repair at the same cut is invisible to both projections.
    assert [(b, (s+1)-1, n) for b,s,n in ref] == ref
    inf = math.inf
    assert scores([4,3], [4,-inf], {0}) and not scores([4,3], [4,-inf], {0,1})
    assert not scores([4,3], [-inf,-inf], set()) and not scores([4,3], [4,-inf], {0,2})
    assert not scores([4,3], [4], {0}) and not scores([math.nan,3], [4,-inf], {0})
    assert not scores([4,3], [inf,-inf], {0})
    assert [(4,n) for n in (3,2)] == [(4,3),(4,2)] and {(4,-inf) for _ in (3,2)} == {(4,-inf)}
    assert struct.pack("<f",0.0) != struct.pack("<f",-0.0)
    assert struct.pack("<f", -inf) == bytes.fromhex("000080ff")
    # A finite but altered permitted value satisfies the validity predicate; parity must fail independently.
    assert scores([4,3],[9,-inf],{0}) and struct.pack("<f",9) != struct.pack("<f",4)
    assert (2,2) != (4,) and (1,0) != (0,1)
    assert max(range(3),key=[1,4,4].__getitem__) == 1
    required = set(range(5))
    tally = {"M":0, "U":0, "P":0}
    for row in itertools.product("MUP", repeat=5):
        observations = {i:c == "P" for i,c in enumerate(row) if c != "U"}
        actual, missing, bad = solve(required, observations)
        assert actual == sorted(row, key="MUP".index)[0]
        tally[actual] += 1
        assert set(missing) == {i for i,c in enumerate(row) if c=="U"}
        assert set(bad) == {i for i,c in enumerate(row) if c=="M"}
    assert tally == {"M":211, "U":31, "P":1}
    assert solve({"P2b","P1","resume"},{"P1":False}) == ("M",("P2b","resume"),("P1",))
    assert solve({"P1","resume"},{"P1":True}) == ("U",("resume",),())
    for name in ["P1","P2a","P2b"]:
        atoms = {f"{k}/{name}" for k in range(5)}
        assert solve(atoms, {})[0] == "U"
    output = {"python":sys.version,"executable":sys.executable,"python_sha256":sha(Path(sys.executable).read_bytes()),
        "control_argv":proc.args,"control_exit":proc.returncode,"stdout_native":[len(proc.stdout),sha(proc.stdout)],
        "stdout_crlf":proc.stdout.count(b"\r\n"),"stdout_lf":[len(normalized),sha(normalized)],
        "stderr":[len(proc.stderr),sha(proc.stderr)], "expected":[len(expected),sha(expected)],
        "explicit_lf_argv":forced.args, "explicit_lf_direct":[len(forced.stdout),sha(forced.stdout)], "raw_equal":proc.stdout==expected,"normalized_equal":True,"oracle":{"window_128_vs_1024":[[],[1328]],
        "memory":memory,"block_indices":[clean[-1],second[-1]],"traces":observed,
        "validity_independent_of_equality":True,"first_max_tie_index":1,"verdicts":tally}}
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

