# The operator attempt and SGLang preflight

The operator's local worker envelope and PostgreSQL result match on all four reported durations. The coordinator matched the attempt identifier privately, verified the original PDF digest against its request, and selected only timing and status columns using the application's database role in read-only mode. The receipt and PDF stayed on the workstation. The initial query used the default schema and failed. Qualifying the live application's `eledgercare` schema returned one completed attempt. [Selected database intervals](operator-database-timing.json)

| Original interval | Seconds |
| --- | ---: |
| Queue timestamp to claim timestamp | 0.020 |
| Claim timestamp to Python worker entry | 0.385 |
| Worker entry to finalizing raw output | 53.374 |
| Worker completion timestamp to attempt end timestamp | 2.011 |
| Queue timestamp to attempt end timestamp, directly from stored timestamps | 55.790 |

The worker clock contains rendering (0.182 s), loading the tokenizer and model (12.261 s), synchronized inference (26.808 s), and 14.123 s outside those timers. Its 61 output tokens include markup and the page marker. There is no first-token clock in the saved original. PostgreSQL's recorded attempt end is assigned by the application before its transaction commits. The original browser click and first painted result have no retained timestamps.

The shipping verifier rereads both weight shards, the other model files, and the notice. The coordinator timed the actual verifier in an isolated Python process using the approved environment. It checked 6,699,209,288 bytes in 7.293 s, with a further 0.250 s for the AST checks. Filesystem cache state was uncontrolled. This measurement establishes a recurring verification cost but cannot retrospectively allocate the 14.123 s in Jack's original attempt. The receipt includes per-file timing. [Verification measurement](file-verification.json)

## Serving backend C

Baidu's version-2 model card recommends SGLang for serving. The pinned model release includes the custom engine wheel `sglang-0.5.20.dev13+g75b9b06b02`. Its downloaded SHA-256 matched the published LFS digest `576c71dab3cacad843f6870739494e13b2e8169a69cc038f84395d6503e801ea`. We inspected its package metadata locally. It requires `sglang-kernel==0.4.7`. PyPI supplies Linux x86_64 and aarch64 wheels for that release. An actual CPython 3.10/Windows AMD64 binary resolution against the public index returned no matching distribution. [Pinned release](https://huggingface.co/baidu/Unlimited-OCR-2/tree/0480966938291445591f69f08a13b041c073a96a/wheel) · [Kernel distributions](https://pypi.org/project/sglang-kernel/0.4.7/#files)

On this Windows 11 Home machine, WSL 2.7.10 is installed and the default is version 2. Both listing distributions and attempting `wsl --system --exec /bin/true` reported no installed distributions. Windows reports `Virtualization Enabled In Firmware: No`, available CPU virtualization extensions, and no active hypervisor. The Docker client exists, but its desktop-linux engine pipe is unavailable. Docker's Windows GPU passthrough requires WSL 2. These observations block the documented local binary route before engine startup. C has zero model requests and no speed or memory result. [Host and resolver receipt](sglang-preflight.json) · [Docker GPU prerequisites](https://docs.docker.com/desktop/features/gpu/) · [Microsoft WSL troubleshooting](https://learn.microsoft.com/en-us/windows/wsl/troubleshooting)

To reopen C on this workstation, enable AMD SVM/virtualization in firmware at a planned reboot, provision a GPU-capable WSL2 Linux environment, and verify GPU enumeration inside it. Use a separate environment and the verified custom wheel. Stage dependencies before offline startup, bind to loopback, mount the pinned model read-only, and start with one GPU request at a time. Reuse the exact diagnostic rasters in Base mode, the existing prompt and stopping/guard settings, and compare both raw and normalized output. Measure native on that Linux substrate as a bridge control, or report the combined platform-and-engine effect. A virtual environment on this Windows installation alone cannot supply the required published kernel wheel.

The upstream 7.0× and 5.6× figures compare decoding steps on hundred-page workloads. They do not establish a three-sentence cold or warm latency on an RTX 5070 Ti. [Baidu technical paper, §5.3.3](https://arxiv.org/html/2610.39308v2)
