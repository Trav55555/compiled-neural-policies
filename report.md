---
id: compiled-neural-policies-evidence-handling
tags: [neural-circuits, evidence-handling, verification, negative-results]
type: technical-report
status: completed-local-evidence
created: 2026-11-05
title: Compiled neural policies for evidence handling
reportdate: 2026-11-05
---

# Compiled neural policies for evidence handling

Report date: 2026-11-05

## Abstract

Fixed neural weights can execute a bounded evidence-handling policy without making the evidence trustworthy or the checked program correct. This report separates those claims through numerical tests, constrained action comparisons, and a failed live coding pilot. A hand-authored compiler lowered Boolean threshold computations into residual SwiGLU stages. The original receipt policy matched its specification on 9,575 cases in CPU FP32 and GPU BF16. A later hypothesis-falsification and test-selection circuit matched on 45,779 cases per evaluation. In small structured action comparisons, neural and ordinary Python replacements agreed and exceeded instructions-only Qwen scores.

Neither changed the pretrained model's weights or demonstrated better coding. The frozen live pilot never reached a policy decision because both unique initial responses were invalid. A separate post-hoc diagnostic reached seven decisions and four public test calls, but failed its artifact budget. Both distinct final source states later passed 59 tests and failed one requested-bug check; the gold control passed 60. A parent-authored trust probe also caused the frozen recorder to accept a deliberately failing process as passing. The supported result is exact observed execution within a bounded contract, plus concrete failures at the evidence and task-completion boundaries.

## Question and scope

What does a compiled neural policy guarantee when a coding agent supplies its evidence?

Three propositions require separate measurements. The numerical implementation must compute the declared policy. Its input receipts must accurately describe executed checks and applicable source revisions. The declared checks must cover the requested behavior. Passing the first proposition establishes neither of the others.

Here, a receipt is a structured record of a check's execution, result, dependencies, and checked revisions. The experiment asks whether fixed neural weights can calculate freshness and next actions from such records. It also tests bounded hypothesis falsification and constrained test selection. These are specified computations, not measurements of general cognition, causal discovery, or prose understanding.

This is a technical report of completed local work, not a peer-reviewed paper or a claim of a new compiler method. The public artifact contains aggregate results and method descriptions, with a [sanitized results summary](data/results.json). Full raw traces and private evaluators are not public. The published repository is therefore not sufficient for full reproduction or independent inspection of every underlying observation.

## Bounded contracts

The original receipt policy has three check slots, three component slots, and four-bit revision identifiers. Identifiers range from 0 through 15 and must not wrap or refer to different contents within a scenario. The caller supplies a complete check-to-component dependency matrix. The encoder validates these facts and serializes bits; it does not decide freshness or verification.

A required check is missing if it has not executed. An executed required check is stale if any dependent component's current revision differs from the recorded revision. Freshness uses equality, not chronological order. A fresh required check fails when its recorded result is nonpassing. An old failure becomes stale after a relevant edit, rather than proving that the revised code still fails.

Verification requires at least one required check, with no missing, stale, or failed required check. The action priority is DEFINE_CHECKS when none are required, FIX_FAILURE for a fresh required failure, RUN_CHECKS for missing or stale evidence, and otherwise REPORT_VERIFIED. A verification claim contradicts the supplied evidence if these conditions do not support it. Nonrequired checks do not block verification.

REPORT_VERIFIED means that the declared current checks passed. It does not mean full correctness or successful issue resolution. The policy cannot identify an omitted regression test from receipt bits alone.

The later circuit eliminates supplied deterministic hypotheses that conflict with observations, detects conflicting observations, and flags unsupported exclusive claims. For each proposed test, it partitions surviving hypotheses by supplied predicted outcome. If S is the survivor set and B(t,o) is the outcome bucket, its guaranteed elimination score is:

```text
gain(t) = |S| - max_o |B(t,o)|
```

It selects an informative feasible test under supplied budget and downside constraints. Ties prefer lower downside, then lower cost, then stable test index. Contradictions require model revision; inadequate discrimination or resources produce NO_INFORMATION or DEFER. This is worst-case hypothesis elimination, not Bayesian information gain. A unique survivor is consistent with the supplied model family, not established truth.

## Mathematical construction

A threshold gate reads Boolean registers x_i and integer coefficients a_i and c. Its target output is one exactly when the integer sum reaches one:

```text
z = c + sum_i a_i x_i
b = 1 if z >= 1, otherwise 0
```

AND, OR, negation, revision comparisons, and bounded rankings compose into a directed acyclic graph of these gates. A constant-one register carries offsets. The lowering uses two scaled sigmoid linear units, SiLU, per gate:

```text
SiLU(u) = u / (1 + exp(-u))
G(z) = [SiLU(512 * (z - 1/4))
        - SiLU(512 * (z - 3/4))] / 256
```

The corresponding difference of ReLU ramps is zero at integer z <= 0 and one at integer z >= 1. At z = 1, the scaled inputs are 384 and 128, whose difference is 256. SiLU approaches those ramps at the chosen scale. In real arithmetic, its exponential tails are not identically zero. Exact Boolean output here is an observed finite-precision property on the tested domains, not a universal identity for arbitrary inputs or numerical backends.

SwiGLU denotes a Swish-gated linear unit. A residual stage has the form:

```text
r_next = r + W_down [SiLU(W_gate r) * (W_up r)]
```

The up projection supplies ones for these gate units. The down projection uses coefficients +1/256 and -1/256 to write the difference into a previously unused register. Stages follow graph depth. The later implementation gathers static dependency registers and scatters residual updates, avoiding full-width dense matrices at every depth. Its maximum absolute input-weight sum per threshold is four. Runtime policy execution uses fixed tensor operations, not a Python semantic checker.

The original circuit has 201 registers and 12 residual stages, with 161,403 parameter values, 1,447 nonzero. The later circuit has 1,098 registers, 1,038 threshold gates, and 30 stages, with 826,730 parameters, 10,301 nonzero. None were trained.

These circuits run in a custom parallel structured-input branch beside Qwen3.5-0.8B. When enabled, the branch overwrites scores for a finite set of action labels. It does not graft the policy into existing pretrained weights or supply free-text reasoning. When disabled, ownership returns to the original scores rather than forcing abstention. All 473 named Qwen parameter tensors had identical before-and-after combined digests in the attachment measurements. This says nothing about unchanged transient buffers.

## Setup and measurements

Numerical evaluations used CPU FP32 and GPU BF16 with PyTorch 2.10.0+rocm7.1 and HIP 7.1.25424. FP32 denotes 32-bit floating point; BF16 denotes bfloat16. They compared saved circuit outputs against separately expressed ordinary Python specifications. Reload tests used fresh processes. Integer threshold interpretation checked generated gate registers separately from the semantic oracle. That interpreter tests lowering and execution, not independently derived meanings for every internal register.

The action comparison used the same original Qwen forward logits across instructions-only, neural, and Python arms. Each arm received the same raw facts and an explicit policy. Neural and Python arms replaced owned action scores. This design isolates bounded action enforcement, but a correct replacement need not use the model's logits at all.

The live pilot used one public Flask bug task in a qualified focused environment, not the official benchmark image or a full benchmark evaluation. Its native public tests passed 59/59 on the unchanged base. Separate evaluator qualification yielded 59 passed and one failed on the buggy base, then 60/60 with the gold fix. This established a usable focused oracle while exposing the public check set's inadequacy for that bug.

Actor workspaces excluded evaluator material. Evaluators graded sealed source exports after actor work ended, without feeding outcomes back to the actor. The execution sandbox used a read-only root, no network, a non-root process, dropped capabilities, and bounded CPU, memory, process count, and runtime. These controls limited execution; they did not authenticate candidate-generated test summaries. The environment was minimal and nonofficial, so its results are not an official SWE-bench score.

## Numerical and action results

The original suite matched on 9,575 cases per device and dtype, including fresh-process reload. Cases covered handwritten scenarios, four-bit equality, dependency and revision-change patterns, multi-check states, seeded joint inputs, and permutations. They overlap and are not 9,575 independent observations. Nine malformed inputs were rejected. Zeroing the readout caused the expected mismatch. Nonfinite routing probes passed after arithmetic masking was replaced with tensor selection.

The later suite matched on 45,779 cases per evaluation in CPU FP32, GPU BF16, and a fresh-process reload of each. The resulting 183,116 presentations are repetitions, not independent tasks. Every evaluation had zero output mismatches and zero intermediate-register mismatches under exact equality, without tolerances. Each checked 47,518,602 generated gate-register values immediately after their writing stage, plus the final residual state. All 28 malformed inputs were rejected, and all four targeted weight mutations were detected. Disabled and nonfinite controls checked score preservation and enabled takeover.

The paired action results were:

| Structured comparison | Instructions-only correct | Neural correct | Python correct |
| --- | ---: | ---: | ---: |
| Actual-event replay, 18 presentations | 5/18 | 18/18 | 18/18 |
| Hypothesis/test-selection attachment, 40 presentations | 4/40 | 40/40 | 40/40 |

The event comparison used nine controlled fixture states rendered twice. The later comparison used 20 handwritten states rendered twice. These were known inputs, not untouched held-out tasks. The baseline selected DEFER throughout the later comparison; its four correct responses came from two DEFER states rendered twice.

On 12 event presentations that did not justify REPORT_VERIFIED, instructions-only selected it four times. Both deterministic replacements selected it zero times. These are finite action choices, not free-text completion statements. Python parity is central to interpreting the results. No practical advantage of neural execution over an ordinary checker was demonstrated, and no comparative latency or throughput benefit was measured.

## Live results and retained failures

The frozen live run produced two unique invalid initial responses. One had malformed JSON; the other omitted a required field. Each response was shared across all three arms, yielding six correlated episodes, not six independent coding failures. The protocol did not repair either response. All episodes terminated with unchanged base sources.

There were zero action forwards, zero native test calls, and zero final-text calls. Consequently, zero unsupported reporting actions had zero opportunities. It is not evidence of compliance, live neural/Python parity, or improved task completion. The intended comparison was not reached.

A separate post-hoc diagnostic normalized only an absent optional field in one original response. It preserved that response's unrelated source edit without repairing the requested bug. Selection followed inspection of the interface failure, so this was not held-out efficacy evidence and did not replace the frozen result.

| Diagnostic arm | Decisions | Public test calls | Observed sequence |
| --- | ---: | ---: | --- |
| Python | 2 | 1 | RUN_CHECKS, REPORT_VERIFIED |
| Instructions-only | 3 | 2 | RUN_CHECKS repeated three times |
| Neural | 2 | 1 | RUN_CHECKS, REPORT_VERIFIED |

Across seven decisions, all four public test calls returned 59 passed. Instructions-only exhausted its two-test budget after redundant requests. Neural decisions matched the ordinary Boolean oracle on every recorded evidence state. All three final source maps were identical. There were no new code-generation calls, repair proposals, added tests, or final-text calls.

The diagnostic's overall status remains FAILED. Runtime caches caused retained artifacts to exceed its 256 MiB ceiling during sealing. The worker recorded 270,305,137 bytes against a 268,435,456-byte limit. Later cache disposal and authenticated post-stop exports did not retroactively restore budget compliance. The interrupted original Python seal remained incomplete; separate exports preserved its final source for grading.

Final grading deduplicated complete source maps rather than treating archive bundles as independent programs:

| Distinct source state or control | Export members | Passed | Failed |
| --- | ---: | ---: | ---: |
| Frozen unchanged base | 6 | 59 | 1 |
| Post-hoc candidate | 3 | 59 | 1 |
| Gold-fixed control | Separate control | 60 | 0 |

There were two distinct candidate source states, not nine. Neither resolved the requested bug. Genuine fresh public passes supported REPORT_VERIFIED under the narrow policy while failing to establish task completion. No final free-text claim was observed, so no free-text false-completion rate can be calculated.

## Falsifiers and trust assumptions

A supported-input mismatch, non-Boolean generated register, reload discrepancy, or failed mutation detection would falsify the tested numerical construction. The retained tests found none within their domains. That evidence does not prove all possible joint inputs or portability across kernels, devices, dtypes, and quantization schemes.

The live results reject a stronger inference. Correct policy execution did not establish successful coding. The frozen study failed at its interface, and the diagnostic's public checks passed without covering the requested bug. Neither failure should disappear behind synthetic perfect scores.

A separate parent-authored trust probe tested receipt authenticity. Its negative process ran a deliberate failing assertion, exited one, and the frozen helper classified it as failing. A second process ran the same failure, then appended a fake passing summary through an exit callback and exited zero. The frozen helper accepted that output as supported and passing, despite the captured failure marker.

This is a confirmed recorder-reliability counterexample. It was not an observed model attack, a security privilege escalation, or part of the coding efficacy counts. Candidate code and tests execute in the same interpreter that can control stdout and exit status. Hashes and fresh revision identifiers establish correspondence to bytes, not truthful test interpretation. Candidate-writable XML alone would not solve that trust problem.

The policy therefore assumes authentic receipts, complete dependencies, unique revision identifiers, and an adequate required-check set. It also assumes valid encoded inputs and correct compiler/runtime execution. These tensor computations grant no tool permissions and are not a mandatory adversarial completion gate.

## Threats to validity

The strongest numerical evidence concerns bounded domains. Exhaustive subdomains and metamorphic tests do not exhaust the entire joint state space. A separately written oracle can share a specification mistake with the compiler. Register checks and mutations reduce some implementation risks without proving the specification adequate.

The action comparisons used a small model and known structured states with correlated renderings. Their denominators cannot support task-level confidence intervals or broad reasoning claims. The live evidence covers one task, two initial responses, and a post-hoc interface intervention. It offers no causal estimate of coding benefit. Public benchmark contamination remains possible.

The diagnostic's artifact failure limits process-success claims even though its decision records and public test receipts survived validation. Focused grading used a nonofficial environment. Sandboxing restricted execution but did not isolate a trusted test oracle from candidate-controlled reporting.

Finally, this public artifact permits aggregate inspection, not full independent reproduction. Private evaluator identities, detailed logs, raw model content, and full traces remain unpublished. Reported aggregate checks should not be mistaken for publicly rerunnable evidence.

## Related work

[Reifier's pinned SwiGLU implementation][reifier] already constructs threshold steps from paired offset ReLU approximations, scaled SiLU, and subtraction. It includes an exact FP16/BF16 path and addresses bias precision and duplicated constant channels. That substantially overlaps this construction. Quarter offsets, residual registers, compact lowering, and receipt workloads do not establish a novel compiler or numerical theorem.

[Tracr][tracr] compiles RASP programs into transformer weights. [ALTA][alta] extends compiler-based transformer analysis to looping programs and Universal Transformers. The present bounded policy graph is not an expressivity advance over that program-compilation lineage.

[PiShield][pishield] constructs inference-time PyTorch layers from logical or numerical requirements. Its output-correction setting differs, but requirement-enforcing neural computation is established prior work. [Sparks of Weight-Space Programming][sparks] studies model-directed weight reading, construction, and pretrained-weight repair. Here, a hand-authored compiler builds a separate branch while Qwen's original tensors remain unchanged. This experiment does not reproduce learned weight editing or backbone repair. No first claim follows from these results.

## Conclusion

The fixed neural circuits executed their declared bounded policies on the tested numerical domains. They matched ordinary Python action replacements on small structured comparisons. That is the positive result.

The live evidence sets the limit. Invalid proposals prevented the frozen comparison; the post-hoc diagnostic failed its artifact budget; both distinct source states left the bug unresolved; and a controlled fake summary defeated receipt interpretation. A useful next study needs an independent test oracle, reliable interfaces, broader frozen tasks, and direct symbolic/runtime controls. Until then, exact observed policy execution should remain separate from trustworthy evidence and successful completion.

## References

- [Sanitized aggregate results](data/results.json). Local study summary, 2026-11-05. Method and aggregate evidence only.
- [Reifier, pinned SwiGLU implementation][reifier]. Source revision used for the overlap comparison.
- [Tracr: Compiled Transformers as a Laboratory for Interpretability][tracr]. arXiv:2301.05062.
- [ALTA: Compiler-Based Analysis of Transformers][alta]. arXiv:2410.18077.
- [PiShield: A PyTorch Package for Learning with Requirements][pishield]. arXiv:2402.18285.
- [Sparks of Weight-Space Programming: LLMs can natively read & write neural network weights][sparks]. Project article.

[reifier]: https://github.com/contramont/reifier/blob/1b77b9b15766a4af60957f4df56754880a2fc97f/src/reifier/tensors/swiglu.py
[tracr]: https://arxiv.org/abs/2301.05062
[alta]: https://arxiv.org/abs/2410.18077
[pishield]: https://arxiv.org/abs/2402.18285
[sparks]: https://rikiyat.github.io/blog/weight-space-programming/
