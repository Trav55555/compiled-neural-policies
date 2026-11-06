---
id: compiled-neural-policies-project
tags: [technical-report, neural-policies, evidence-handling]
type: project
status: publication-approved
created: 2026-11-05
---

# Compiled neural policies for evidence handling

A technical report separating bounded numerical policy execution, trustworthy
receipts and successful task completion. It preserves negative results and does
not claim new general reasoning, a novel compiler, or a coding advantage over
ordinary Python.

## Public artifact scope

- `report.md`: report source, approximately 2,700 prose words.
- `data/results.json`: explicitly selected aggregate measurements and source-receipt
  hash commitments, not full raw evidence or independent execution attestation.
- `docs/`: deterministic static report output, ready for a GitHub Pages project
  site with the publication branch's `/docs` folder as its source.
- `tools/` and `tests/`: site build, consistency and publication-boundary checks.

Private evaluators, test patches, raw model responses, machine paths, transcripts,
model weights and local experiments are excluded. This repository alone does not
permit full reproduction of the underlying experiments. It does reproduce the
static report site from the published source and aggregate JSON.

## Build and check locally

Python 3.11 or later and [uv](https://docs.astral.sh/uv/) are required. The only
site dependency is the locked Markdown renderer.

```sh
uv sync --locked
uv run python3 tools/build_site.py
uv run python3 tools/check_site.py
uv run python3 -m unittest discover -s tests -v
uv run python3 tools/check_publication.py
```

Serve the already-built site locally:

```sh
uv run python3 -m http.server 8080 --directory docs --bind 127.0.0.1
```

Open `http://127.0.0.1:8080/`. The site has no JavaScript, external font dependency
or analytics. Browser printing uses its print stylesheet.

## Publication status

Report site: <https://trav55555.github.io/compiled-neural-policies/>.

The selected Kaggle destination is the **Developer Agent Competition**, not the
Paper Track. The report is a separate technical artifact, not a competition
score or a claim that the custom action head runs in the official harness.
Competition packaging and validation are tracked separately. No new account,
rule or model-license acceptance is performed by this report build.

A private architecture-only smoke used a tiny randomly initialized Gemma 4 model.
It is not a pretrained Gemma result, a coding improvement, or evidence that a
custom action head is compatible with Kaggle's documented host runtime. It is
not part of the report's empirical results or public release.

Before publication, run the staged-file privacy allowlist check and independent
claim review. Do not publish the parent experimental directory or force-add
ignored files. No third-party model weights or benchmark patches are licensed or
redistributed by this project.
