"""Selection and metric logic of the Upworthy evaluation (no API calls)."""

from __future__ import annotations

from scripts.evaluate_upworthy import select_tests, top1_credit


def _row(test: str, headline: str, clicks: int, **overrides: str) -> dict[str, str]:
    return {
        "created_at": "2014-06-01 00:00:00",
        "clickability_test_id": test,
        "eyecatcher_id": "img",
        "excerpt": "excerpt",
        "headline": headline,
        "impressions": "3000",
        "clicks": str(clicks),
        **overrides,
    }


def test_keeps_clear_winner() -> None:
    [selected] = select_tests([_row("t", "a", 30), _row("t", "b", 150)])
    assert selected.variants[selected.winner_index].headline == "b"


def test_drops_unclear_bad_window_and_image_only_tests() -> None:
    rows = [
        _row("close", "a", 100),
        _row("close", "b", 103),
        _row("window", "a", 30, created_at="2013-08-01 00:00:00"),
        _row("window", "b", 150, created_at="2013-08-01 00:00:00"),
        _row("images", "a", 30, eyecatcher_id="one"),
        _row("images", "a", 150, eyecatcher_id="two"),
    ]
    assert select_tests(rows) == []


def test_ties_share_credit() -> None:
    assert top1_credit([0.5, 0.5, 0.1], winner=0) == 0.5
    assert top1_credit([0.2, 0.9], winner=1) == 1.0
    assert top1_credit([0.2, 0.9], winner=0) == 0.0
