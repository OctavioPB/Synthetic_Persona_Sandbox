"""Does the sandbox pick the headline that real readers clicked most?

Evaluates persona inference against the Upworthy Research Archive (CC BY 4.0,
Matias et al., Scientific Data 2021, https://osf.io/jd64p), using real headline
A/B tests. Two arms are compared with random choice:

  persona   the app's own prompt, with a generic US reader segment
  baseline  the same model and stimulus without the persona

Usage (from the repository root):

    curl -L -o data/upworthy/exploratory.csv https://osf.io/download/3vqmp/
    uv run python -m scripts.evaluate_upworthy                 # dry run, no API calls
    uv run python -m scripts.evaluate_upworthy --run --tests 10 --max-usd 1

    uv run python -m scripts.evaluate_upworthy --run --tests 10 \
        --ollama qwen3:4b-instruct-2507-q4_K_M

``--run`` calls the Claude API and costs money. It needs ANTHROPIC_API_KEY in the
environment. With ``--ollama MODEL`` it uses a local Ollama model instead, at no
cost. Responses are cached on disk, so repeating a run is free.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
import time
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from ml.synthetic_data.claude_client import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, CachedClaudeClient
from ml.synthetic_data.conversion_scorer import ConversionScorer
from ml.synthetic_data.persona_context_builder import PersonaContextBuilder
from ml.synthetic_data.persona_inference import PersonaInferenceService, SyntheticResponse
from ml.synthetic_data.stimulus_schema import AdCopyStimulus, format_stimulus_prompt

DEFAULT_DATA = Path("data/upworthy/exploratory.csv")
DEFAULT_OUTPUT = Path("data/upworthy/results.json")

# Tests in this window were not reliably randomized (2024 Author Correction).
BAD_RANDOMIZATION = ("2013-06-25", "2014-01-10")

SEGMENT_NAME = "US news readers"
SEGMENT_DEFINITION = {"geo": {"country": "United States"}}
TEMPERATURE = 0.7  # the API's default for simulations

BASELINE_SYSTEM = """\
You judge how likely a general reader is to click a piece of content.
Respond with a single JSON object with exactly this structure:
{
  "verbatim_response": "A 2-3 sentence reaction",
  "sentiment": "positive" | "neutral" | "negative",
  "likelihood_to_convert": <float 0.0-1.0>,
  "key_factors": ["<factor 1>", "<factor 2>"]
}
Return ONLY the JSON object."""

# USD per million tokens for DEFAULT_MODEL (claude-sonnet-4-6).
INPUT_USD_PER_MTOK = 3.00
OUTPUT_USD_PER_MTOK = 15.00
TYPICAL_OUTPUT_TOKENS = 150  # assumption, replaced by measured usage in a real run

ARMS = ("persona", "persona_click", "goal_click", "baseline")

# persona_click = the application's persona prompt with only the outcome reworded
# from purchasing to clicking, so persona vs persona_click isolates the wording.
_CLICK_REWORDING = (
    (
        "When presented with a marketing stimulus, react authentically as this persona.",
        "When presented with a marketing stimulus, react authentically as this persona.\n"
        'The stimulus is a news headline; "likelihood_to_convert" is the probability that '
        "you click it to read the story.",
    ),
    ("= extremely likely to purchase immediately", "= extremely likely to click and read"),
    ("= interested, may convert with follow-up", "= interested, likely to click"),
    ("= unlikely to convert, may disengage", "= unlikely to click, would scroll past"),
    (
        "a high-purchase-frequency,\n  high-basket-size persona responds better to "
        "premium/quality messaging.",
        "react as a typical reader\n  of this segment would.",
    ),
    (
        "A low-conversion-rate persona is naturally skeptical; require compelling value.",
        "Readers skip headlines that feel generic; require a compelling reason to click.",
    ),
)


@dataclass(frozen=True)
class Variant:
    headline: str
    impressions: int
    clicks: int

    @property
    def ctr(self) -> float:
        return self.clicks / self.impressions


@dataclass(frozen=True)
class HeadlineTest:
    test_id: str
    excerpt: str
    variants: tuple[Variant, ...]

    @property
    def winner_index(self) -> int:
        return max(range(len(self.variants)), key=lambda i: self.variants[i].ctr)


# ── Data selection ───────────────────────────────────────────────────────────


def two_proportion_p_value(a: Variant, b: Variant) -> float:
    """Two-sided z-test for a difference between two click-through rates."""
    pooled = (a.clicks + b.clicks) / (a.impressions + b.impressions)
    se = math.sqrt(pooled * (1 - pooled) * (1 / a.impressions + 1 / b.impressions))
    if se == 0:
        return 1.0
    return math.erfc(abs(a.ctr - b.ctr) / se / math.sqrt(2))


def select_tests(
    rows: Iterable[dict[str, str]], min_impressions: int = 1000, alpha: float = 0.05
) -> list[HeadlineTest]:
    """Keep headline-only comparisons with a clear winner.

    Packages are grouped by test, image and excerpt so that the headline is the
    only difference. The top headline must beat the runner-up at ``alpha``
    (no multiple-comparison correction).
    """
    groups: dict[tuple[str, str, str], dict[str, list[int]]] = defaultdict(dict)
    for row in rows:
        day = row["created_at"][:10]
        if BAD_RANDOMIZATION[0] <= day <= BAD_RANDOMIZATION[1]:
            continue
        headline = row["headline"].strip()
        if not headline or len(headline) > 200:
            continue
        key = (row["clickability_test_id"], row["eyecatcher_id"], row["excerpt"].strip())
        totals = groups[key].setdefault(headline, [0, 0])
        totals[0] += int(row["impressions"])
        totals[1] += int(row["clicks"])

    best_per_test: dict[str, HeadlineTest] = {}
    for (test_id, _, excerpt), headlines in groups.items():
        variants = tuple(
            Variant(text, impressions, clicks)
            for text, (impressions, clicks) in sorted(headlines.items())
            if impressions >= min_impressions
        )
        if len(variants) < 2:
            continue
        top, second = sorted(variants, key=lambda v: v.ctr, reverse=True)[:2]
        if two_proportion_p_value(top, second) >= alpha:
            continue
        current = best_per_test.get(test_id)
        if current is None or len(variants) > len(current.variants):
            best_per_test[test_id] = HeadlineTest(test_id, excerpt[:1000], variants)
    return [best_per_test[k] for k in sorted(best_per_test)]


# ── Metrics ──────────────────────────────────────────────────────────────────


def top1_credit(scores: Sequence[float], winner: int) -> float:
    """1 if the winner has the top score; ties share the credit equally."""
    best = max(scores)
    tied = [i for i, s in enumerate(scores) if math.isclose(s, best)]
    return 1 / len(tied) if winner in tied else 0.0


def bootstrap_interval(
    values: Sequence[float], samples: int = 2000, seed: int = 0
) -> tuple[float, float]:
    """95% bootstrap interval for the mean."""
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(samples))
    return means[int(0.025 * samples)], means[int(0.975 * samples) - 1]


# ── Prompts and cost ─────────────────────────────────────────────────────────


def stimulus_for(test: HeadlineTest, variant: Variant) -> AdCopyStimulus:
    return AdCopyStimulus(
        headline=variant.headline, body_copy=test.excerpt or "(none)", cta="Read more"
    )


def persona_system_prompt() -> str:
    return PersonaContextBuilder().build_system_prompt(SEGMENT_NAME, SEGMENT_DEFINITION)


def persona_click_system_prompt() -> str:
    prompt = persona_system_prompt()
    for old, new in _CLICK_REWORDING:
        if old not in prompt:  # the app prompt changed; the rewording must be updated
            raise RuntimeError(f"Persona prompt no longer contains: {old!r}")
        prompt = prompt.replace(old, new)
    return prompt


def arm_prompts() -> dict[str, str]:
    return {
        "persona": persona_system_prompt(),
        "persona_click": persona_click_system_prompt(),
        # The wording the application ships for stimuli with goal="click".
        "goal_click": PersonaContextBuilder().build_system_prompt(
            SEGMENT_NAME, SEGMENT_DEFINITION, goal="click"
        ),
        "baseline": BASELINE_SYSTEM,
    }


def cost_usd(input_tokens: float, output_tokens: float) -> float:
    return (input_tokens * INPUT_USD_PER_MTOK + output_tokens * OUTPUT_USD_PER_MTOK) / 1e6


def estimate(tests: Sequence[HeadlineTest]) -> dict[str, float]:
    """Rough size and cost of a run (about 4 characters per token)."""
    systems = list(arm_prompts().values())
    calls = input_tokens = 0
    for test in tests:
        for variant in test.variants:
            user = format_stimulus_prompt(stimulus_for(test, variant))
            for system in systems:
                calls += 1
                input_tokens += (len(system) + len(user)) // 4
    return {
        "calls": calls,
        "input_tokens": input_tokens,
        "typical_usd": cost_usd(input_tokens, calls * TYPICAL_OUTPUT_TOKENS),
        "ceiling_usd": cost_usd(input_tokens, calls * DEFAULT_MAX_TOKENS),
    }


# ── Local models ─────────────────────────────────────────────────────────────

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")

_REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "verbatim_response": {"type": "string"},
        "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
        "likelihood_to_convert": {"type": "number"},
        "key_factors": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verbatim_response", "sentiment", "likelihood_to_convert"],
}


class OllamaClient:
    """Local counterpart of CachedClaudeClient.complete, with its own disk cache.

    Replies are constrained to the expected JSON schema and thinking is off, so
    results are not a like-for-like comparison with the Claude path.
    """

    def __init__(self, model: str, cache_dir: Path = Path("data/cache/ollama")) -> None:
        self.model = model
        self._cache_dir = cache_dir
        self.retries: list[str] = []  # every crash that was retried, kept for the record
        cache_dir.mkdir(parents=True, exist_ok=True)

    def complete(self, system: str, user_message: str, temperature: float) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            "format": _REPLY_SCHEMA,
            "think": False,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": 4096, "num_predict": 512},
        }
        key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        path = self._cache_dir / f"{key}.json"
        if path.exists():
            return {**json.loads(path.read_text(encoding="utf-8")), "cached": True}
        for attempt in range(3):
            response = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=600)
            if not response.is_error:
                break
            # Ollama restarts a crashed model process (seen with CUDA errors when the
            # GPU is nearly full), so a crash is retried; other errors are not.
            error = f"Ollama {response.status_code}: {response.text[:300]}"
            if "process has terminated" not in response.text or attempt == 2:
                raise RuntimeError(error)
            self.retries.append(error)
            time.sleep(5)
        result = {"text": response.json()["message"]["content"]}
        path.write_text(json.dumps(result), encoding="utf-8")
        return {**result, "cached": False}


# ── Real run ─────────────────────────────────────────────────────────────────


def run(
    tests: Sequence[HeadlineTest],
    max_usd: float,
    output: Path,
    ollama_model: str | None = None,
    seed: int | None = None,
) -> None:
    """Score every variant with every arm, stopping before ``max_usd`` is exceeded.

    The output file holds the settings, prompt hashes, timings, call counts and
    failures next to the scores, so every reported number can be checked later.
    """
    client = OllamaClient(ollama_model) if ollama_model else CachedClaudeClient()
    started = time.monotonic()
    scorer = ConversionScorer()
    prompts = arm_prompts()
    spent = 0.0
    calls = {"live": 0, "cached": 0}
    live_seconds = 0.0
    consecutive_failures = 0
    failures: list[dict[str, str]] = []
    results: list[dict[str, Any]] = []
    meta: dict[str, Any] = {
        "model": ollama_model or DEFAULT_MODEL,
        "backend": "ollama" if ollama_model else "anthropic",
        "dataset": "Upworthy Research Archive, exploratory packages 03.12.2020 (CC BY 4.0)",
        "seed": seed,
        "tests_requested": len(tests),
        "temperature": TEMPERATURE,
        "segment": {"name": SEGMENT_NAME, "definition": SEGMENT_DEFINITION},
        "excluded_window": BAD_RANDOMIZATION,
        "arms": {
            arm: hashlib.sha256(text.encode()).hexdigest()[:16] for arm, text in prompts.items()
        },
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }

    def save(finished: bool) -> None:
        meta.update(
            tests_completed=len(results),
            failures=failures,
            retried_crashes=list(getattr(client, "retries", [])),
            calls=calls,
            live_seconds_per_call=round(live_seconds / calls["live"], 2) if calls["live"] else None,
            elapsed_seconds=round(time.monotonic() - started, 1),
            spent_usd=round(spent, 4),
            finished=finished,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"meta": meta, "results": results}, indent=2), "utf-8")

    def score(system: str, test: HeadlineTest, variant: Variant) -> float:
        nonlocal spent, live_seconds
        stimulus = stimulus_for(test, variant)
        t0 = time.monotonic()
        reply = client.complete(
            system=system,
            user_message=format_stimulus_prompt(stimulus),
            temperature=TEMPERATURE,
        )
        if reply["cached"]:
            calls["cached"] += 1
        else:
            calls["live"] += 1
            live_seconds += time.monotonic() - t0
            if not ollama_model:
                spent += cost_usd(reply["input_tokens"], reply["output_tokens"])
        # Same parsing and scoring as the application.
        parsed = PersonaInferenceService._parse_response(reply["text"], stimulus.stimulus_id)
        return scorer.score(
            SyntheticResponse(
                segment_id="upworthy",
                stimulus_id=stimulus.stimulus_id,
                verbatim_response=parsed["verbatim_response"],
                sentiment=parsed["sentiment"],
                likelihood_to_convert=parsed["likelihood_to_convert"],
            )
        )

    for number, test in enumerate(tests, start=1):
        # Worst case for this test, so the cap cannot be overshot by a whole test.
        if not ollama_model and spent + estimate([test])["ceiling_usd"] > max_usd:
            print(f"Stopping at test {number}: the next one could exceed ${max_usd:.2f}.")
            break
        try:
            scores = {arm: [score(prompts[arm], test, v) for v in test.variants] for arm in ARMS}
        except Exception as exc:  # one bad reply should not lose the whole run
            print(f"Test {test.test_id} skipped: {type(exc).__name__}: {exc}", file=sys.stderr)
            failures.append({"test_id": test.test_id, "error": f"{type(exc).__name__}: {exc}"})
            consecutive_failures += 1
            if consecutive_failures >= 3:
                print("Three failures in a row; aborting.", file=sys.stderr)
                break
            continue
        consecutive_failures = 0
        results.append(
            {
                "test_id": test.test_id,
                "variants": [asdict(v) for v in test.variants],
                "winner": test.winner_index,
                "scores": scores,
            }
        )
        save(finished=False)
        elapsed = time.monotonic() - started
        print(f"[{number}/{len(tests)}] done, {elapsed:.0f}s, spent ${spent:.3f}", flush=True)

    save(finished=True)
    print(
        f"\nSaved {output}  (live calls {calls['live']}, cached {calls['cached']}, "
        f"failed tests {len(failures)})"
    )
    report(results, spent)


def report(results: Sequence[dict[str, Any]], spent: float) -> None:
    if not results:
        print("No completed tests, nothing to report.")
        return
    n = len(results)
    arms = [arm for arm in ARMS if arm in results[0]["scores"]]
    credit = {arm: [top1_credit(r["scores"][arm], r["winner"]) for r in results] for arm in arms}
    chance = sum(1 / len(r["variants"]) for r in results) / n
    print(f"\nCompleted tests: {n}   spent this run: ${spent:.3f}")
    print(f"  random choice  {chance:.1%}")
    for arm in arms:
        low, high = bootstrap_interval(credit[arm])
        ties = sum(r["scores"][arm].count(max(r["scores"][arm])) > 1 for r in results)
        print(
            f"  {arm:<13}  {sum(credit[arm]) / n:.1%}  (95% CI {low:.1%} to {high:.1%}, "
            f"top-score ties in {ties}/{n})"
        )
    pairs = [
        (a, b)
        for a, b in [
            ("persona", "baseline"),
            ("persona_click", "baseline"),
            ("persona_click", "persona"),
            ("goal_click", "persona"),
            ("goal_click", "baseline"),
        ]
        if a in credit and b in credit
    ]
    for a, b in pairs:
        diff = [x - y for x, y in zip(credit[a], credit[b], strict=True)]
        low, high = bootstrap_interval(diff)
        print(f"  {a} minus {b}: {sum(diff) / n:+.1%} (95% CI {low:+.1%} to {high:+.1%})")
    if n < 100:
        print("  Fewer than 100 tests: treat this as a smoke test, not a result.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, help="results file (default depends on model)")
    parser.add_argument("--ollama", metavar="MODEL", help="use a local Ollama model, at no cost")
    parser.add_argument("--tests", type=int, default=200, help="number of A/B tests to sample")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--run", action="store_true", help="call the Claude API (costs money)")
    parser.add_argument("--max-usd", type=float, default=2.0, help="spending cap for --run")
    args = parser.parse_args()

    if not args.data.exists():
        print(f"{args.data} not found. See the usage notes at the top of this script.")
        return 1
    with args.data.open(encoding="utf-8", newline="") as handle:
        eligible = select_tests(csv.DictReader(handle))
    tests = random.Random(args.seed).sample(eligible, min(args.tests, len(eligible)))
    if not tests:
        print("No eligible tests.")
        return 1

    size = estimate(tests)
    variants = sum(len(t.variants) for t in tests)
    print(f"Eligible tests: {len(eligible)}   sampled: {len(tests)}   headlines: {variants}")
    if args.ollama:
        print(
            f"Local model {args.ollama}: {size['calls']} calls ({len(ARMS)} prompt versions), no cost"
        )
    else:
        print(
            f"Model {DEFAULT_MODEL}: {size['calls']} calls ({len(ARMS)} prompt versions), "
            f"about {size['input_tokens']:,} input tokens"
        )
        print(
            f"Estimated cost ${size['typical_usd']:.2f} (ceiling ${size['ceiling_usd']:.2f} "
            f"if every reply hits {DEFAULT_MAX_TOKENS} tokens)"
        )

    if not args.run:
        example = tests[0]
        print("\nDRY RUN - no API calls made. Example test:")
        for i, variant in enumerate(example.variants):
            mark = "*" if i == example.winner_index else " "
            print(f"  {mark} {variant.ctr:6.2%}  {variant.headline}")
        print("\nExample stimulus message:\n")
        print(format_stimulus_prompt(stimulus_for(example, example.variants[0])))
        return 0

    if not args.ollama and not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set.")
        return 1
    slug = (args.ollama or DEFAULT_MODEL).replace(":", "_").replace("/", "_")
    output = args.output or DEFAULT_OUTPUT.with_name(f"results-{slug}.json")
    run(tests, args.max_usd, output, args.ollama, args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
