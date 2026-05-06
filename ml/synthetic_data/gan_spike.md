# GAN vs LLM — Go/No-Go Decision for Synthetic Persona Generation

**Date:** 2026-05-05  
**Author:** Octavio Pérez Bravo  
**Status:** Decision taken — LLM-only for MVP

---

## Context

Sprint 4 requires a synthetic persona generation layer that can simulate how a customer segment reacts to a marketing stimulus (ad copy, price change, promo). Two architectural approaches were evaluated:

1. **GAN-based generation** — Train a conditional GAN on real behavioral event data to generate realistic user response distributions.
2. **LLM-based simulation** — Use a prompted Claude model (claude-sonnet-4-6) to role-play as a persona and return a structured JSON reaction.

---

## Evaluation Criteria

| Criterion | Weight | GAN | LLM |
|---|---|---|---|
| Time to first working prototype | High | Weeks (data collection, training, evaluation) | Hours (prompt engineering) |
| Data requirements | High | Requires labeled {stimulus → conversion} pairs at scale | Requires only segment behavioral stats (already available) |
| Output interpretability | Medium | Black-box latent vectors; requires decoding | Natural language + structured JSON; fully auditable |
| Stimulus generalization | High | Requires re-training for new stimulus types | Zero-shot generalization via prompt |
| Cost at scale | Medium | One-time training cost + cheap inference | Per-call API cost (mitigated by caching) |
| Accuracy / groundedness | High | Trained on real outcomes — high validity with enough data | Plausible but not empirically calibrated; risk of hallucination |
| Maintenance overhead | Medium | Requires retraining as behavior drifts | Prompt updates; no retraining |

---

## GAN Assessment

**Pros:**
- Statistically grounded if trained on sufficient labeled data.
- Inference is fully local, zero marginal cost per call.
- Could model multi-modal response distributions.

**Cons:**
- We have no paired `(stimulus, conversion_outcome)` dataset today. The MVP data pipeline captures behavioral events, not ad experiment outcomes.
- Training a stable conditional GAN requires ~50k+ labeled pairs minimum; we currently have synthetic events only.
- GAN training instability (mode collapse, gradient vanishing) adds weeks of debugging overhead that is not justified for an MVP.
- GANs output numerical vectors; the persona narrative (verbatim response, key factors) that makes this platform valuable to marketers would require an additional decoding step — adding complexity without clear benefit.

**Decision: NO-GO for S4 MVP.**

GAN-based generation is tracked as a future upgrade path (see Future Work below) but is not included in Sprint 4.

---

## LLM Assessment

**Pros:**
- Immediately operational: `persona_context_builder.py` + `claude_client.py` are already implemented.
- Returns structured JSON + natural language verbatim reaction — directly useful for marketing teams.
- Zero-shot generalization to any new stimulus type without retraining.
- Cost is negligible at simulation scale: ~$0.002 per run × 1000 simulations/day = $2/day, further reduced by disk cache during development and Anthropic prompt caching on repeated segment evaluations.
- Prompt caching: the system prompt (persona context) is stable across all stimuli for a given segment, so Anthropic's ephemeral cache applies — 90% cost reduction on input tokens after the first call per segment.

**Cons:**
- Responses are plausible but not calibrated against real conversion outcomes. The `likelihood_to_convert` is a model estimate, not an empirically derived probability.
- Temperature introduces stochasticity — the same persona will give slightly different responses to identical stimuli across runs.
- The LLM's behavioral knowledge is general, not domain-specific to our customers.

**Mitigation:**
- Calibration against real A/B test outcomes is planned for Sprint 6 (`ml/evaluation/holdout_evaluator.py`).
- Disk caching eliminates stochasticity in development; production can pin temperature to 0.3 for higher consistency.

**Decision: GO for S4 MVP.**

---

## Architecture Decision

```
Stimulus (AdCopy | PriceChange | Promo)
    │
    ▼
format_stimulus_prompt()        ← stimulus_schema.py
    │
    ▼
CachedClaudeClient.complete()   ← claude_client.py
    │  system = PersonaContextBuilder.build_system_prompt()
    │  user   = formatted stimulus
    │
    ▼
PersonaInferenceService._parse_response()
    │
    ▼
SyntheticResponse               ← persona_inference.py
    │
    ▼
ConversionScorer.score()        ← conversion_scorer.py
    │
    ▼
float 0–1 (final conversion probability)
```

---

## Future Work — GAN Upgrade Path

When real `(stimulus, conversion_outcome)` labels are available at scale (≥50k pairs), revisit a **conditional CVAE** (Conditional Variational Autoencoder) rather than a plain GAN:

- CVAEs are more training-stable than GANs.
- The encoder can compress the LLM verbatim response into a latent vector, creating a hybrid LLM-as-encoder + CVAE-as-calibrator architecture.
- The decoder maps segment embedding + stimulus embedding → conversion distribution.

This hybrid approach would preserve the interpretability of the LLM layer while grounding the numeric output in real outcomes.

**Estimated effort when data is available:** Sprint of 2 weeks.
