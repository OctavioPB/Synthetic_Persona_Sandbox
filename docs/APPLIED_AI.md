# Applied AI

How the platform uses language models, what has been measured, and how far to trust the
output.

## The idea

A segment is described to the model as a person ("you are a customer in this segment").
The model reads a marketing stimulus and answers as that person would: a short reaction,
a sentiment, and a 0–1 likelihood of doing what the stimulus asks. Comparing those scores
across variants is meant to show which variant is likely to do best.

## Pipeline

```
segment definition (+ behavioral aggregates, batch path only) ─┐
stimulus goal (purchase, click, signup) ───────────────────────┼─> system prompt
stimulus (ad copy, price change, promo) ───────────────────────────> user message
                                                Claude ─> JSON reply
                         validation ─> sentiment adjustment ─> conversion score
```

### 1. Persona prompt

`ml/synthetic_data/persona_context_builder.py` builds the system prompt from:

- **Demographics:** age range, location and the behavioral data window.
- **Behavioral aggregates**, when available: purchase frequency, basket size, session
  depth, conversion rate, category diversity and recency. Without them the prompt says
  behavioral data is not yet available.
- **Category interests.**
- **Response instructions:** the JSON format and a calibration scale for the score.

The prompt is the same for every stimulus with the same segment and goal, which is what
lets prompt caching apply on repeated calls.

### 2. Stimulus and goal

Stimuli are ad copy (headline, body, call to action), a price change, or a promotion, each
a validated Pydantic model.

Each stimulus has a **goal**: `purchase` (the default), `click` or `signup`. The goal sets
how the calibration scale and its guidance are worded, for example "extremely likely to
purchase immediately" or "extremely likely to click right away". The default prompt is
byte-for-byte what it was before goals existed, so earlier results stay comparable.

Choose the goal the campaign is really after. On Upworthy headlines, where clicks are the
real outcome, purchase wording picked the winning headline in 27.8% of 200 tests, against
36.0% for click wording (Qwen 3 4B; random choice 28.6%). See [EVALUATION.md](EVALUATION.md).

### 3. Model call

`ml/synthetic_data/claude_client.py`:

- Default model `claude-sonnet-4-6`, temperature 0.7 unless the request sets another.
- Retries connection, rate-limit and server errors up to three times with exponential
  backoff.
- Marks long system prompts for Anthropic prompt caching.
- **Caches replies on disk**, keyed by model, prompts, temperature and token limit. The
  same input returns the same stored reply, so a repeated simulation is not a new sample.

### 4. Output validation

Markdown fences are stripped, the three required keys are checked, the likelihood is
clamped to [0, 1], and an unknown sentiment becomes `neutral`. Invalid JSON fails the run.

### 5. Conversion score

The score is the model's own likelihood plus a fixed adjustment: **+0.05** for positive
sentiment, **−0.08** for negative, clamped to [0, 1]. It is a heuristic, not a trained or
calibrated model. One side effect: a 0.30 with negative sentiment becomes 0.22, and in the
Qwen runs about 45% of persona scores were exactly 0.22.

## Embeddings and staleness

The extraction DAG describes a segment's aggregates in text, encodes it with
`all-MiniLM-L6-v2` (384 dimensions) and stores it in Qdrant. Inference does not read these
vectors today.

`ml/evaluation/drift_detector.py` flags segments not retrained in 7 days. This is an age
check, not statistical drift detection.

## What has been measured

Full method and numbers: [EVALUATION.md](EVALUATION.md). In short:

| Model | Tests | Unchanged persona | Persona, click wording | Simple prompt | Random |
|-------|-------|-------------------|------------------------|---------------|--------|
| Qwen 3 4B (local) | 200 | 27.8% | 36.0% | 39.9% | 28.6% |
| Gemma 4 26B (local) | 200 | 24.3% | 28.7% | 35.7% | 28.6% |
| Claude Sonnet 4.6 | 10 (smoke test) | 30.0% | 35.0% | 38.3% | 24.2% |

Each figure is how often the top score went to the headline real readers clicked most.

What this supports:

- **Matching the goal to the real outcome matters.** Click wording added 8.3 points for Qwen,
  with a 95% interval of +3.2 to +13.5. For Gemma it added 4.5 points, with an interval of −1.4 to +10.3.
- **The persona does worse than a plain prompt without one.** Both models were tested with the
  persona in click wording against the plain prompt. The persona trailed by 3.8 points for Qwen
  (interval −8.5 to +0.5) and by 7.0 points for Gemma (interval −13.5 to −0.1).
- **The app's own click wording helps less.** The generic `goal="click"` prompt scored 30.3%
  for Qwen, 5.7 points below the hand-written news-specific wording (interval −10.4 to −1.3).
- **A larger local model didn't help.** Gemma 26B scored below Qwen 4B with every prompt.
- **Claude is unmeasured at a useful scale.** Ten tests only showed that the pipeline works.

What it does not cover: purchases, real customer segments, behavioral data, and close
races between variants.

## Limitations

1. **Dashboard and API simulations ignore behavioral data.** Only the
   `run_simulation_pipeline` DAG includes it.
2. **One reply stands for a whole segment.** There is no sampling and no confidence
   interval per variant.
3. **Scores are coarse.** Ties for the top score were common, about 40% of tests for Qwen,
   so many comparisons can't separate variants.
4. **Stereotypes.** Language models can bring demographic stereotypes into persona reactions.
5. **User text reaches the model as written.** Segment names and stimulus text are not
   anonymized. Don't put personal data in them.
6. **Seed data is random.** The admin seed creates fake runs that never involved a model.

## Recommended next steps

1. Let a campaign describe its medium (for example "news headline" or "email subject
   line") in the prompt, and measure whether that closes the gap between `goal_click` and
   `persona_click`.
2. Run the full 200-test evaluation on Claude, the model the app uses.
3. Pass behavioral aggregates on the interactive path.
4. Reduce ties by sampling several replies per variant, or by comparing variants in pairs.
5. Validate on real campaign outcomes before quoting any accuracy.
