# Business Value

What the Synthetic Persona Sandbox is for, what it costs, what the evidence shows so far,
and how to find out whether it pays off.

## The problem

Campaign ideas are usually validated only after money is spent.

| Method | Strength | Weakness |
|--------|----------|----------|
| Live A/B test | Measures real behavior | Needs traffic, budget and weeks; the losing variant spends money |
| Focus group | Rich explanations | Slow, small, and people say what they think they should |
| Survey | Cheap at scale | Measures stated intent, not behavior |
| Intuition | Fast and free | Depends on who is deciding |

Many choices between variants, especially below a certain budget, are made on intuition.

## What the platform offers

A cheap, fast first filter before any money is spent. A marketer describes an audience,
writes several variants (ad copy, a price change or a promotion), states what success means
(a purchase, a click or a sign-up) and gets, for each variant:

- a **score** from 0 to 1, for comparing variants,
- a **sentiment**: positive, neutral or negative,
- a short **first-person reaction** explaining it.

## Where it fits

```
Brief → Draft variants → [ Sandbox: drop the weak ones ] → Live A/B test → Scale the winner
```

It narrows what goes into a live test. It does not replace the test.

## Who uses it and how

| Role | Use |
|------|-----|
| Campaign manager | Compare variants before committing budget; send fewer, stronger ones to a live test |
| Copywriter | Read why a message might not land, and rewrite before review |
| Analyst | Review history, compare stimulus types, export results |
| Administrator | Keep each organization's data, members and API keys separate |

## What the evidence shows so far

Measured on real headline A/B tests where the winner is known (details in
[EVALUATION.md](EVALUATION.md)):

- **Stating the right goal matters.** When the platform was asked about purchases but the
  real outcome was clicks, it picked the winner no more often than chance. Asking about
  clicks instead added 4 to 8 points, depending on the model. Variants now carry a goal for this reason.
  The generic click wording the app ships recovered only about 2.5 of those points.
- **The persona has not beaten a plain prompt.** On two local models, a small one and a larger one, a short
  prompt without a persona picked the winner more often.
- **The model the platform uses (Claude) has only been smoke-tested** on 10 tests. A
  meaningful run of 200 tests would cost about $8.

**This is not yet evidence that the platform predicts campaign results.** It is evidence
that the evaluation works and that the goal setting is needed.

## What it is not

- **Not a forecast.** Accuracy on real campaigns has not been measured.
- **Not an ad platform.** It doesn't buy media or connect to ad networks.
- **Not a substitute for research** with real customers.
- **Not yet using observed behavior** when simulations start from the dashboard; it uses
  the audience *definition* only. See [APPLIED_AI.md](APPLIED_AI.md).

## Costs

| Item | Measured or estimated |
|------|-----------------------|
| One Claude call | About $0.003 at list price (10-test smoke run: $0.43 for 129 calls) |
| Comparing 4 variants once | About $0.01–0.02 |
| Full 200-test evaluation | About $8 |
| Local models (Ollama) | No API cost; slower, and results differ from Claude |
| Hosting | Database, queue, vector store, streaming and monitoring; not yet costed |

Replies are cached, so repeating an identical simulation costs nothing, but it also
returns the same answer.

## How to prove value

Before relying on the scores, run a pilot:

1. **Pick past campaigns with known results**, ideally with at least two variants and a
   clear winner.
2. **Set the goal to match** what each campaign measured.
3. **Simulate the same variants** without looking at the results.
4. **Compare** how often the sandbox's top variant was the real winner, against chance and
   against the team's own guess made beforehand.
5. **Track the money:** cost per simulation against the media spend that dropping weak
   variants earlier would have saved.

| Pilot outcome | Decision |
|---------------|----------|
| Beats the team's guess clearly | Use it as a filter before live tests |
| Matches the team's guess | Use it only where no expert is available |
| No better than chance | Don't use it for decisions; revisit the prompt and data |

Until a pilot like this is done, no savings or accuracy figure should be quoted.

## Risks

| Risk | Mitigation |
|------|------------|
| Teams trust scores that are wrong | Show the evaluation status in the product; require a live test before scaling |
| Stereotyped persona reactions | Review reactions, not just scores; test diverse segments |
| Personal data in segment or stimulus text | Policy and training; identifiers in ingested events are already anonymized |
| Model costs grow with use | Per-organization rate limit on the async endpoint, caching, monitoring |
| Model or API changes alter results | Version prompts and re-run the evaluation after changes |
