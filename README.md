# Synthetic Customer Lab

Synthetic Customer Lab is a CPU-only Python harness that runs deterministic fictional personas through local scripted app or agent fixtures. It records each interaction, detects failures, clusters them with hand-written rules, and produces reports with links back to the session evidence.

## Quickstart

Use Python 3.10 or newer. There are no runtime dependencies.

```powershell
python -m pip install -e .
synlab personas --seed 42 --count 100
synlab simulate --seed 42 --target defects --count 100
synlab cluster
synlab report --format md
```

The equivalent module commands work without installing the console script, for example `python -m synlab simulate --seed 42 --target defects`. The available fixture targets are `happy`, `slow`, and `defects`. The aliases `happy-path`, `slow-confusing`, and `planted-defects` are also accepted.

The simulator writes deterministic JSON artifacts to `.synlab/`: `latest-personas.json`, `latest-sessions.json`, `latest-clusters.json`, and `latest-run.json`. Reports are written to `.synlab/latest-report.md` or `.synlab/latest-report.html`. Set `SYNLAB_HOME` to use a different local artifact directory. Each CLI command appends an event to `synlab-audit.jsonl` in that state directory. Audit timestamps use the current UTC time, while session, cluster, and report data contain no wall-clock timestamps.

## Architecture

```text
seed + count
    |
    v
persona generator ---> scripted journey builder
                              |
                              v
                    local fixture target
                              |
                              v
                 transcript + failure detector
                    |                   |
                    v                   v
             session JSON       rule-based clustering
                                        |
                                        v
                           ranked evidence report

All CLI activity ----------------> append-only audit JSONL
```

The fixture target interface is local and synchronous. `happy` returns clear guidance, `slow` returns delayed opaque guidance, and `defects` drops a notification settings request, changes its account recovery answer across repeated identical questions, and exceeds the wait budget for diagnostic marker 504. Response times are simulated integer milliseconds, not measured network or wall-clock latency. Each persona gets a fresh target instance so fixture state does not leak between sessions.

The simulator varies the first request using each persona's goal, skill, communication tendencies, and seeded edge-case scores. Typos and vague wording affect that request. Retry tendency repeats the dropped-request prompt. Frustration escalation is recorded after multiple failures when the persona's seeded escalation score reaches the documented threshold. The rest of the journey includes fixed probes so the fixture defects can be compared across personas.

## Determinism and seeds

Each persona generation call creates a private `random.Random(seed)` instance and consumes it in a fixed order. It does not read system entropy or share global random state. Persona IDs are assigned in generation order. A simulation uses only those generated personas, deterministic fixture behavior, and logical integer timings. It does not put the current time in transcripts or reports. Running the same command with the same seed, count, target, and Python runtime rewrites byte-identical persona, transcript, cluster, and report artifacts. Audit JSONL is intentionally append-only and has real UTC timestamps, so separate audit events differ.

Seed is required for `personas` and `simulate`. Count must be a positive integer and defaults to 100. The seed is recorded in every session and the run manifest. To compare targets, run each with the same seed and count.

## Persona model

Each fictional persona has an ID, generated name, role, skill level, goal, patience from 1 to 5, communication style, and four seeded tendency scores from 0 to 100: typos, vague requests, repeated retries, and frustration escalation. Scores of 55 or higher activate typo, retry, or escalation behavior; vague requests activate at 65 or higher. A persona's response wait budget is `900 + 450 * patience` milliseconds.

## Failure taxonomy

| Code | Detection rule |
| --- | --- |
| `TIMEOUT` | Fixture latency is above the persona wait budget. |
| `CONTRADICTION` | The same normalized question receives different non-empty answers in one session. |
| `UNANSWERED` | The fixture is called and returns no answer without timing out. |
| `FRUSTRATION_TRIGGER` | After at least two other failures, an escalation-prone persona emits an explicit synthetic frustration message. |
| `CONFUSING_RESPONSE` | The fixture returns its opaque wording behavior code. |
| `SLOW_RESPONSE` | A non-timeout response exceeds the deterministic slow-response threshold. |

Clustering groups shared failure signatures and fixture behavior codes. For each group it extracts normalized transcript bigrams and trigrams, ranks them by the number of member sessions containing each phrase, and stores them as evidence. Unknown failure codes use a deterministic behavior-code and n-gram fallback. Clusters carry every contributing session ID and interaction pointer. Report severity and affected-session rates are computed from the recorded sessions and persona count.

## HONESTY BOUNDARY

Every user is simulated. Every complaint is synthetic. Findings are test-harness output. This is not user research, customer feedback analysis, or evidence about a real product's real users. Fixture response timings and defects are scripted measurements, not observations of a deployed service. Reports and CLI output repeat this boundary so synthetic results cannot be mistaken for real customer evidence.

## Development

Run the local test suite with:

```powershell
python -m pytest
```

The implementation uses only the Python standard library at runtime. Clustering is a deterministic rule-based pass implemented in this project. There is no model download, external service, GPU, CUDA, TensorFlow, or PyTorch dependency.
