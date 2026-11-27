# Evaluation

Does the sandbox pick the variant that real people preferred? This page describes the
method, every run so far, and how to reproduce them.

## Method

**Data.** The [Upworthy Research Archive](https://osf.io/jd64p) (CC BY 4.0; Matias et al.,
*Scientific Data*, 2021): real headline A/B tests run on Upworthy between 2013 and 2015,
with impressions and clicks per headline. We use the exploratory set.

**Which tests count.** A test is used when:

1. it compares headlines only, with the same image and excerpt;
2. each headline has at least 1,000 impressions;
3. the best headline beats the runner-up in a two-sided test at p < 0.05;
4. it was not run between 25 June 2013 and 10 January 2014, when randomization was
   unreliable (the archive's 2024 correction).

282 tests qualify. A fixed sample is drawn with seed 42.

**Task.** Every headline in a test is scored, with the excerpt as body copy and "Read more"
as the call to action. A version is credited when its top score goes to the real winner;
ties share the credit. Each stimulus is scored once, at temperature 0.7.

**Versions compared.**

| Version | System prompt |
|---------|---------------|
| `persona` | The app's persona prompt, unchanged (purchase wording) |
| `persona_click` | The same prompt with the outcome hand-reworded to clicking |
| `goal_click` | The prompt the app now builds for `goal="click"` |
| `baseline` | A short prompt with no persona, asking how likely a reader is to click |
| Random | Expected score of picking a headline at random |

All persona versions use one segment: "US news readers", country United States.

**Statistics.** 95% intervals come from 2,000 bootstrap resamples of tests. Differences
between versions are paired by test.

## Results

### Qwen 3 4B (local, Ollama), 200 tests

Runs `20261126-3arm` and `20261126-qwen-4arm`. The second run added `goal_click`; the other
three versions came from the cache and were not re-sampled. 0 failures, about 1.2 seconds per call.

| Version | Picked the winner | 95% interval | Tied top scores |
|---------|-------------------|--------------|-----------------|
| Random | 28.6% | | |
| `persona` | 27.8% | 22.8–32.8% | 85 / 200 |
| `persona_click` | 36.0% | 30.4–41.7% | 83 / 200 |
| `goal_click` | 30.3% | 24.7–35.7% | 72 / 200 |
| `baseline` | 39.9% | 34.1–45.4% | 92 / 200 |

| Difference | Points | 95% interval |
|------------|--------|--------------|
| `persona_click` − `persona` | +8.3 | +3.2 to +13.5 |
| `persona_click` − `baseline` | −3.8 | −8.5 to +0.5 |
| `persona` − `baseline` | −12.1 | −17.6 to −6.8 |
| `goal_click` − `persona` | +2.5 | −1.0 to +6.2 |
| `goal_click` − `persona_click` | −5.7 | −10.4 to −1.3 |
| `goal_click` − `baseline` | −9.5 | −14.6 to −4.7 |

**Why the shipped click wording scores lower.** `goal_click` and `persona_click` differ in
only four lines. The hand rewording describes the stimulus as a news headline and the person
as a reader ("click it to read the story"). The app's wording has to fit any campaign, so it
is generic ("click the stimulus to see more", "a typical member"). The hand rewording was
also written knowing the data were news headlines, so part of its lead may come from
tailoring the wording to this data.

### Claude Sonnet 4.6, 10 tests (smoke test)

Run `20261126-claude-smoke`, 129 calls, 0 failures, about 3.3 seconds per call, $0.43
estimated from reported tokens at list price.

| Version | Picked the winner | 95% interval | Tied top scores |
|---------|-------------------|--------------|-----------------|
| Random | 24.2% | | |
| `persona` | 30.0% | 0–60% | 0 / 10 |
| `persona_click` | 35.0% | 10–65% | 1 / 10 |
| `baseline` | 38.3% | 12–67% | 5 / 10 |

Ten tests can't separate the versions. The order matches Qwen's, and Claude produces far
fewer ties.

### Gemma 4 26B (local, Ollama), 200 tests

Run `20261126-gemma-3arm`, 0 failures, 3 Ollama crashes (CUDA error on an 8 GB GPU) each
recovered by a retry, 6.4 seconds per call, about 4.1 hours.

| Version | Picked the winner | 95% interval | Tied top scores |
|---------|-------------------|--------------|-----------------|
| Random | 28.6% | | |
| `persona` | 24.3% | 19.7–29.4% | 55 / 200 |
| `persona_click` | 28.7% | 23.3–34.8% | 41 / 200 |
| `baseline` | 35.7% | 30.0–41.9% | 58 / 200 |

| Difference | Points | 95% interval |
|------------|--------|--------------|
| `persona_click` − `persona` | +4.5 | −1.4 to +10.3 |
| `persona_click` − `baseline` | −7.0 | −13.5 to −0.1 |
| `persona` − `baseline` | −11.4 | −18.0 to −4.3 |

After 57 tests, `persona_click` led `baseline` by 5 points. The lead was gone by 155
tests. Read interim numbers as noise.

### Not yet measured

- `goal_click` on Gemma and Claude.
- Claude at 200 tests (about $8 estimated).

## Conclusions so far

1. **Purchase wording hurts on click data.** With purchase wording, the persona did no better than random on both models.
   Switching to click wording added 8.3 points for Qwen, a significant gain, and 4.5 points for Gemma, which is not significant.
   This finding led to the stimulus `goal` field.
   The generic click wording the app ships recovers only part of that gain: +2.5 points
   for Qwen, not significant. Describing the medium ("a news headline", "a reader")
   seems to matter as much as naming the goal.
2. **The persona does worse than a plain prompt.** On both models, the plain prompt
   beat the persona with either wording. The gap is significant for 3 of the 4 comparisons.
   The persona may still help on purchase data, real segments or behavioral detail, but this data can't test that.
3. **A larger model didn't help the persona.** Gemma 26B scored below Qwen 4B with every prompt.
4. **Ties limit ranking.** Scores are coarse, so several headlines often get the same top
   score. Gemma tied less often than Qwen but wasn't more accurate.

## Limits of this evaluation

- Headline clicks on a news site are not purchases.
- One generic segment; Upworthy has no audience demographics.
- Only clear winners, so close races are untested.
- The data is public, so a model may have seen it during training.
- Local models run with JSON-constrained output and thinking turned off; the Claude path
  does not, so results across models are not like for like.

## Reproduce

```bash
mkdir -p data/upworthy
curl -L -o data/upworthy/exploratory.csv https://osf.io/download/3vqmp/

uv run python -m scripts.evaluate_upworthy                      # dry run: tests, calls, cost
uv run python -m scripts.evaluate_upworthy --run --tests 200 \
  --ollama qwen3:4b-instruct-2507-q4_K_M                         # local, free
uv run python -m scripts.evaluate_upworthy --run --tests 10 --max-usd 1   # Claude, paid
```

Claude runs need `ANTHROPIC_API_KEY` and stop before any test that could exceed
`--max-usd`. Replies are cached on disk, so rerunning or adding a version only calls the
model for new prompts.

Each results file records the model, seed, settings, a fingerprint of every prompt,
timings, live and cached call counts, failures, retried crashes and whether the run
finished. Runs are kept under `data/upworthy/runs/`, which git ignores.

| Prompt fingerprint | Version |
|--------------------|---------|
| `d22ace0e5f159640` | `persona` |
| `abb2710b85a72f4f` | `persona_click` |
| `227cf77dc2b956ce` | `goal_click` |
| `d7fdcdefb06dd6b8` | `baseline` |

A different fingerprint means the prompt changed and the result belongs to a different
version.
