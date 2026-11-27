# Research Roadmap

What published research says about predicting A/B test winners with language models, which
techniques fit this project, and in what order to try them. Measured results so far are in
[EVALUATION.md](EVALUATION.md).

## Where we stand

On 200 real Upworthy headline tests, a plain prompt with no persona picked the winner more
often than every persona prompt, on both local models tested:

| Prompt | Qwen 3 4B | Gemma 4 26B |
|--------|-----------|-------------|
| Random choice | 28.6% | 28.6% |
| Persona, purchase wording | 27.8% | 24.3% |
| Persona, best click wording | 36.0% | 28.7% |
| Plain prompt, no persona | **39.9%** | **35.7%** |

## What the literature says

| Finding | Source |
|---------|--------|
| A generic-reader prompt beats a ten-persona panel on Upworthy (Kendall τ 0.36 vs 0.08; top-1 49% vs 35%) on three Gemini models | Maiorano, 2026 [1] |
| Prompted LLMs are only slightly better than random on 17,681 Upworthy tests; a fine-tuned Llama-3-8B gains a little more | Ye, Yoganarasimhan & Zheng, 2025 [2] |
| A model retrained on outcomes from earlier tests picks 52.8% of decisive winners, against 25.6% for random | Clark [3] |
| The gap is set by the training signal, not by model size or prompting | Jung & An, 2026 [4] |

Our result matches published work. Persona prompting alone does not predict winners. What
does help is a better way to elicit scores, a training signal from real outcomes, or using
the model's prediction as a starting point for a live test.

**What this means for the claim.** Change the claim from "the persona predicts the winner"
to "the platform finds the winner sooner and with less wasted spend". The second claim can
be tested, and it holds up even when the predictor is weak (technique 6).

## Techniques

Impact and cost are relative estimates for this codebase, not measurements.

### AI: how scores are produced

| # | Technique | What it fixes | Impact | Cost |
|---|-----------|---------------|--------|------|
| 1 | Semantic similarity rating (SSR) | Coarse scores, ties, the 0.22 spike | High | Low |
| 2 | Pairwise comparison | Ties; pointwise scoring is weak at ranking | High | Medium |
| 3 | Repeated sampling and model ensembles | One reply stands for a segment; no uncertainty | Medium | Low |
| 4 | Token-probability scores | Discrete scores | Medium | Low (local models only) |
| 5 | Training on real outcomes | No training signal | Highest | High |

**1. Semantic similarity rating.** Maier et al. [5] found that asking for a numeric rating gives narrow,
skewed answers. Instead, the persona writes a free-text reaction. The reaction is embedded,
and its cosine similarity to five anchor statements (from "would definitely not click" to
"would definitely click") gives a distribution over a 1–5 scale. On 57 purchase-intent
surveys this reached 90% of human test-retest reliability.
- *Here:* `all-MiniLM-L6-v2` is already a dependency. Score = expected value of the
  distribution. It works with Claude, which returns no token probabilities.
- *Risk:* results depend on the anchor wording. Fix the anchors on tuning data, never on
  test data.

**2. Pairwise comparison.** Qin et al. [6] show that judging two items at a time ranks far
better than scoring each one alone.
- *Here:* each Upworthy test has 2–4 headlines, which is 1–6 pairs. Ask about both orders,
  because headline benchmarks report a position bias [7]. Combine the results with
  Bradley-Terry (technique 9).
- *In the app:* `variant_competition` would compare variants against each other instead of
  ranking independent scores.

**3. Repeated sampling and ensembles.** Schoenegger et al. [8] found that an ensemble of 12 LLMs
forecasts as well as a crowd of 925 people.
- *Here:* sample k = 5 replies per variant at temperature 0.7 and average them; optionally
  average across models. The disk cache key needs a sample index, because today an identical
  prompt always returns the same stored reply.
- *Bonus:* each variant gets an uncertainty band, which the app does not have yet.

**4. Token-probability scores.** Weighting the score digits by their token probabilities
turns a few discrete values into a continuous score [9]. Ollama can expose these; the Claude
API cannot, so this is for local models only.

**5. Training on real outcomes.** The strongest results in the literature come from this
[3][4].
- *Here:* train a small ranker on headline embeddings, or fine-tune a small model, on the
  Upworthy exploratory set; evaluate on the confirmatory set.
- *For the product:* this is the right role for the behavioral events the platform already
  ingests. Use real clicks and purchases as training labels, not as numbers in a prompt.

### Engineering: how the platform uses scores

| # | Technique | What it changes | Impact | Cost |
|---|-----------|-----------------|--------|------|
| 6 | LLM prior for a bandit test (LOLA) | Turns a weak predictor into money saved | High | Medium |
| 7 | Prediction-powered inference | Valid error bars from a small human sample | High | Medium |
| 8 | Tuning and test split, pre-registered comparisons | Stops overfitting the prompt to the test data | High | Low |

**6. LLM prior for a bandit test.** LOLA [2] uses the LLM's prediction as the starting point
for an upper-confidence-bound bandit, which then moves live traffic toward the better
variant. It beat both pure LLM ranking and standard A/B testing, by 4–9% in clicks depending
on the time horizon.
- *Here:* this fits the existing campaign ranking and the `variant_competition` DAG. It
  needs a feed of live click counts per variant.
- *To measure:* simulate on Upworthy by replaying its impressions and clicks, and compare
  clicks lost against an even split.

**7. Prediction-powered inference.** Treat the LLM as a biased predictor and correct it with
a small set of real responses. Around 100 human responses brought estimates within 5% bias,
with valid confidence intervals [10]. Simply pooling synthetic and real data is biased [11].
- *Here:* this becomes the pilot method in [BUSINESS_VALUE.md](BUSINESS_VALUE.md): a small
  real test plus many simulated ones, with honest error bars.

**8. Split the data and pre-register.** `persona_click` was written knowing the test set was
news headlines, so its lead may be partly tailoring. The Gemma run also showed an interim
lead that disappeared.
- *Here:*
  - tune prompts, anchors and methods on part of the exploratory set;
  - report once on the held-out confirmatory set;
  - name the primary comparison before the run.
- *Tooling:* the harness already records prompt fingerprints. It needs a `--split` option
  and a frozen list of test IDs per split.

### Math: how results are judged

| # | Technique | Purpose |
|---|-----------|---------|
| 9 | Bradley-Terry model | Turn pairwise judgments into one score per variant, with intervals |
| 10 | Kendall τ and captured lift | Metrics that use the whole ranking and map to money |
| 11 | Power analysis | Choose the sample size before running |
| 12 | Multiple-comparison correction | Keep false positives in check across many differences |
| 13 | Calibration | Make the 0–1 score a real probability |

**9. Bradley-Terry.** Fits a strength per headline so that P(i beats j) = s_i / (s_i + s_j).
Fitted on the model's pairwise judgments, it yields a full ranking with no ties.

**10. Better metrics.** Top-1 credit is coarse and distorted by ties. Add:
- **Kendall τ**, or the share of pairs ordered correctly, over all headlines in a test;
- **captured lift**: the click-through rate of the chosen headline as a share of the best
  one. It converts directly to money and is the headline metric in [1].

**11. Power analysis.** At 200 tests, the standard deviation of the paired per-test
differences was about 0.29. Detecting a 3-point difference at 80% power then needs about
n = (2.8 × 0.29 / 0.03)² ≈ 730 tests. That is more than the 282 eligible tests in the
exploratory set. Every medium and goal comparison so far was therefore underpowered. Use
the confirmatory set for final results.

**12. Multiple comparisons.** The harness reports 11 differences per run. Apply Holm
correction, or name one primary comparison in advance and label the rest exploratory.

**13. Calibration.** The current score adds a fixed +0.05 or −0.08 for sentiment, which is a
heuristic. Fit an isotonic or logistic map from predicted scores to observed click-through
rates on tuning data. The score then becomes a probability that the business docs can quote.

## Plan

| Phase | Work | Techniques | Cost | Done when |
|-------|------|------------|------|-----------|
| 1. Harness | Kendall τ, captured lift, Holm correction, tuning and test split, frozen test IDs | 8, 10, 11, 12 | Free, about a day | Every run reports the new metrics on a fixed split |
| 2. Scoring experiments | SSR, pairwise with both orders plus Bradley-Terry, then sampling if ties remain | 1, 2, 3, 9 | Free on Qwen | A method beats the plain prompt on the confirmatory set, after correction |
| 3. Confirm on Claude | Best method from phase 2, 200+ tests | — | About $8–25, with approval and a `--max-usd` cap | Result holds on the model the app uses |
| 4. Product | Bandit prior in `variant_competition`; prediction-powered inference in the pilot plan; calibrated scores | 6, 7, 13 | Medium | Upworthy replay shows fewer clicks lost than an even split |
| 5. Training signal | Ranker or fine-tune on exploratory outcomes; later, the platform's own behavioral events | 4, 5 | High | Beats phase 2 on the confirmatory set |

## Decision rules

| Outcome | Decision |
|---------|----------|
| A phase 2 method beats the plain prompt on held-out data | Ship it as the default scorer; re-run on Claude |
| No method beats the plain prompt | Make the plain prompt the default; keep personas for qualitative reactions only |
| Bandit replay saves clicks even with a weak predictor | Lead the product claim with this |
| Nothing beats random on held-out data | Stop quoting prediction accuracy; position the product as a drafting and review tool |

## Sources

1. Maiorano, A. C. (2026). *Do Synthetic Personas Predict Real Audience Response? A Sim-to-Real
   Study Where a No-Persona Baseline Beats Persona-Based Copy Simulation.*
   [arXiv:2609.25010](https://arxiv.org/abs/2609.25010).
   [Replication package](https://github.com/alemaiorano/sim-to-real-validity).
2. Ye, Z., Yoganarasimhan, H. & Zheng, Y. (2025). *LOLA: LLM-Assisted Online Learning Algorithm
   for Content Experiments.* Marketing Science. [arXiv:2406.02611](https://arxiv.org/abs/2406.02611).
3. Clark, N. *Predict, Observe, Retrain: Can a Language Model Learn to Pick A/B Test Winners
   from Its Own Feedback Loop?* [SSRN 7323738](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7323738).
4. Jung, J. & An, D. (2026). *Grounding Language Models in Revealed Audience Behavior.*
   [arXiv:2611.31999](https://arxiv.org/abs/2611.31999).
5. Maier et al. (2025). *LLMs Reproduce Human Purchase Intent via Semantic Similarity
   Elicitation of Likert Ratings.* [arXiv:2510.08338](https://arxiv.org/abs/2510.08338).
6. Qin, Z. et al. (2024). *Large Language Models are Effective Text Rankers with Pairwise
   Ranking Prompting.* NAACL Findings. [arXiv:2306.17563](https://arxiv.org/abs/2306.17563).
7. *jev-headline-bench* (unreviewed project; reports position bias).
   [GitHub](https://github.com/Gaurav-Gosain/jev-headline-bench).
8. Schoenegger, P. et al. (2024). *Wisdom of the Silicon Crowd: LLM Ensemble Prediction
   Capabilities Rival Human Crowd Accuracy.* Science Advances.
   [arXiv:2402.19379](https://arxiv.org/abs/2402.19379).
9. Verbalized confidence weighted by token probabilities. ACL Findings 2026.
   [PDF](https://aclanthology.org/2026.findings-acl.1671.pdf).
10. *Valid Survey Simulations with Limited Human Data.* [arXiv:2510.11408](https://arxiv.org/abs/2510.11408).
11. Byun et al. *Valid Inference with Imperfect Synthetic Data.*
    [arXiv:2508.06635](https://arxiv.org/abs/2508.06635).
12. Matias, J. N. et al. (2021). *The Upworthy Research Archive.* Scientific Data.
    [OSF](https://osf.io/jd64p).

Several sources are 2026 preprints that have not been peer reviewed. Treat their numbers as
indicative until replicated.
