"""Evaluation harness.

Answers "how do you know it works?" with measurements against baselines, rather than
assertions. See EVALUATION.md at the repo root for the design rationale behind each
option; this package is its implementation.

    python -m eval.run --all          # everything, writes eval/results/REPORT.md
    python -m eval.run --option b     # one option
    python -m eval.generate --n 300   # rebuild the dataset (needs OPENAI_API_KEY)

Read `eval/results/REPORT.md` for what the numbers mean, including the limits of a
synthetic dataset — which are substantial and stated up front.
"""
