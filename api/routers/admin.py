"""Admin endpoints — seed and clear the database with synthetic data.

Only available when ENV != production. Requires admin role.

Endpoints:
    GET    /admin/stats   — row counts per table for the current org
    POST   /admin/seed    — insert randomised segments, campaigns, variants, runs
    DELETE /admin/clear   — delete all org data (segments, campaigns, runs)
"""

from __future__ import annotations

import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import require
from api.auth.jwt_handler import TokenClaims
from api.auth.rbac import Permission
from api.models.campaign import CampaignORM, CampaignVariantORM
from api.models.segment import SegmentORM
from api.models.simulation import SimulationRunORM
from api.services.db import get_db

router = APIRouter(prefix="/admin", tags=["admin"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
_ENV  = os.getenv("ENV", "development").lower()


def _guard_non_production() -> None:
    if _ENV == "production":
        raise HTTPException(
            status_code=403,
            detail="Admin seed/clear endpoints are disabled in production.",
        )


# ── Response models ───────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    segments:         int
    campaigns:        int
    campaign_variants: int
    simulation_runs:  int


class SeedResponse(BaseModel):
    segments:         int
    campaigns:        int
    campaign_variants: int
    simulation_runs:  int
    message:          str


class ClearResponse(BaseModel):
    deleted_segments:  int
    deleted_campaigns: int
    deleted_runs:      int
    message:           str


# ── Seed corpus ───────────────────────────────────────────────────────────────

_SEGMENT_TEMPLATES = [
    {
        "name": "Gen Z — Madrid",
        "description": "Urban young adults with high digital engagement and mobile-first behaviour.",
        "definition": {
            "age_range": {"min_age": 18, "max_age": 24},
            "geo": {"city": "Madrid", "country": "Spain"},
            "category_affinities": ["Electronics", "Fashion"],
            "purchase_history_days": 60,
        },
    },
    {
        "name": "Millennials — Barcelona",
        "description": "Tech-savvy professionals aged 25–34, dual income, frequent online shoppers.",
        "definition": {
            "age_range": {"min_age": 25, "max_age": 34},
            "geo": {"city": "Barcelona", "country": "Spain"},
            "category_affinities": ["Electronics", "Food & Beverage"],
            "purchase_history_days": 90,
            "min_purchase_count": 3,
        },
    },
    {
        "name": "Parents — Valencia",
        "description": "Households with children, strong home & garden and food affinity.",
        "definition": {
            "age_range": {"min_age": 30, "max_age": 45},
            "geo": {"city": "Valencia", "country": "Spain"},
            "category_affinities": ["Home & Garden", "Food & Beverage"],
            "purchase_history_days": 120,
            "min_purchase_count": 2,
        },
    },
    {
        "name": "Sports Enthusiasts — Bilbao",
        "description": "Active adults with strong sports & outdoors purchase history.",
        "definition": {
            "age_range": {"min_age": 22, "max_age": 40},
            "geo": {"city": "Bilbao", "country": "Spain"},
            "category_affinities": ["Sports"],
            "purchase_history_days": 90,
        },
    },
    {
        "name": "Fashion Forward — Seville",
        "description": "Style-conscious shoppers, high basket size, Fashion category leaders.",
        "definition": {
            "age_range": {"min_age": 20, "max_age": 35},
            "geo": {"city": "Seville", "country": "Spain"},
            "category_affinities": ["Fashion"],
            "purchase_history_days": 45,
            "min_page_views": 10,
        },
    },
    {
        "name": "Book Lovers — All Spain",
        "description": "High page-view users with strong Books affinity, nationwide.",
        "definition": {
            "geo": {"country": "Spain"},
            "category_affinities": ["Books"],
            "purchase_history_days": 180,
            "min_purchase_count": 1,
        },
    },
]

_CAMPAIGN_SUFFIXES = [
    "Summer 2026 Launch",
    "Back to School",
    "Flash Sale",
    "New Collection Drop",
    "Member Exclusive",
    "Holiday Special",
    "Weekend Offer",
    "Early Access",
]

_AD_COPY_VARIANTS: list[dict] = [
    {
        "type": "ad_copy",
        "headline": "Discover Your Next Favourite — Exclusive for You",
        "body_copy": "Curated picks based on your style. Limited time offer.",
        "cta": "Shop Now",
    },
    {
        "type": "ad_copy",
        "headline": "Summer Deals Are Here. Don't Miss Out.",
        "body_copy": "Up to 40% off on top categories. Free delivery on orders over €30.",
        "cta": "Explore Deals",
    },
    {
        "type": "ad_copy",
        "headline": "New Arrivals Just Dropped — Grab Yours",
        "body_copy": "Fresh styles, fresh prices. Shop the latest collection before it sells out.",
        "cta": "See New Arrivals",
    },
]

_PRICE_VARIANTS: list[dict] = [
    {"type": "price_change", "product_name": "Wireless Headphones Pro", "original_price": 129.99, "new_price": 89.99},
    {"type": "price_change", "product_name": "Running Shoes X500",     "original_price": 99.90,  "new_price": 69.90},
    {"type": "price_change", "product_name": "Smart Home Starter Kit", "original_price": 199.00, "new_price": 149.00},
]

_PROMO_VARIANTS: list[dict] = [
    {"type": "promo", "promo_code": "SUMMER20", "discount_value": 20, "discount_type": "percent", "expiry_days": 7},
    {"type": "promo", "promo_code": "WELCOME10", "discount_value": 10, "discount_type": "fixed",   "expiry_days": 14},
    {"type": "promo", "promo_code": "FLASH15",  "discount_value": 15, "discount_type": "percent", "expiry_days": 3},
]

_ALL_STIMULI = _AD_COPY_VARIANTS + _PRICE_VARIANTS + _PROMO_VARIANTS

_SENTIMENTS = ["positive", "neutral", "negative"]
_SENTIMENT_WEIGHTS = [0.55, 0.30, 0.15]

_VERBATIM_TEMPLATES = {
    "positive": [
        "This offer genuinely appeals to me — good value for what I need right now.",
        "The discount makes this an easy decision. I'd likely convert.",
        "Exactly the kind of promotion I respond to. Timing is great.",
        "Strong headline, clear benefit. I would click through to learn more.",
    ],
    "neutral": [
        "Somewhat interesting, but I'd need to see more details before deciding.",
        "The offer is okay, but nothing that would make me act immediately.",
        "I might consider it, but it's not urgent enough to convert today.",
        "Reasonable, though the discount could be stronger for my price point.",
    ],
    "negative": [
        "Not relevant to what I'm looking for right now.",
        "The messaging doesn't resonate with my current needs.",
        "I rarely respond to this type of promotion — feels generic.",
        "The timing is off for me personally, though the offer is fair.",
    ],
}


def _rand_score(sentiment: str) -> float:
    if sentiment == "positive":
        return round(random.uniform(0.55, 0.95), 4)
    if sentiment == "neutral":
        return round(random.uniform(0.30, 0.60), 4)
    return round(random.uniform(0.05, 0.35), 4)


def _rand_ts(days_ago_max: int = 30) -> datetime:
    delta = timedelta(
        days=random.randint(0, days_ago_max),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    return datetime.now(timezone.utc) - delta


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    claims: Annotated[object, Depends(require(Permission.SEGMENTS_READ))],
    db:     DbDep,
) -> StatsResponse:
    """Return row counts for all tenant tables."""
    from api.auth.jwt_handler import TokenClaims
    ct: TokenClaims = claims  # type: ignore[assignment]

    seg_count = (await db.execute(
        select(func.count()).select_from(SegmentORM).where(SegmentORM.org_id == ct.org_id)
    )).scalar_one()

    cam_count = (await db.execute(
        select(func.count()).select_from(CampaignORM).where(CampaignORM.org_id == ct.org_id)
    )).scalar_one()

    var_count = (await db.execute(
        select(func.count()).select_from(CampaignVariantORM).where(
            CampaignVariantORM.campaign_id.in_(
                select(CampaignORM.id).where(CampaignORM.org_id == ct.org_id)
            )
        )
    )).scalar_one()

    run_count = (await db.execute(
        select(func.count()).select_from(SimulationRunORM).where(
            SimulationRunORM.org_id == ct.org_id
        )
    )).scalar_one()

    return StatsResponse(
        segments=seg_count,
        campaigns=cam_count,
        campaign_variants=var_count,
        simulation_runs=run_count,
    )


@router.post("/seed", response_model=SeedResponse)
async def seed_database(
    claims: Annotated[object, Depends(require(Permission.SEGMENTS_WRITE))],
    db:     DbDep,
    n_segments:   int = 6,
    n_campaigns:  int = 2,
    n_runs:       int = 8,
) -> SeedResponse:
    """Insert randomised demo data for the current org.

    Query params:
        n_segments  — number of segments to create (1–6, default 6)
        n_campaigns — campaigns per segment (1–4, default 2)
        n_runs      — simulation runs per segment (1–20, default 8)
    """
    _guard_non_production()

    from api.auth.jwt_handler import TokenClaims
    ct: TokenClaims = claims  # type: ignore[assignment]

    n_segments  = max(1, min(n_segments,  6))
    n_campaigns = max(1, min(n_campaigns, 4))
    n_runs      = max(1, min(n_runs,     20))

    templates   = random.sample(_SEGMENT_TEMPLATES, k=n_segments)
    seg_count   = cam_count = var_count = run_count = 0
    campaign_suffixes = _CAMPAIGN_SUFFIXES.copy()
    random.shuffle(campaign_suffixes)

    for i, tmpl in enumerate(templates):
        seg = SegmentORM(
            id=uuid.uuid4(),
            org_id=ct.org_id,
            name=tmpl["name"],
            description=tmpl["description"],
            definition=tmpl["definition"],
            is_stale=random.random() < 0.15,
            last_trained_at=_rand_ts(10) if random.random() > 0.2 else None,
            created_by=uuid.UUID(ct.sub) if _is_uuid(ct.sub) else None,
        )
        db.add(seg)
        await db.flush()   # materialise segment.id before FK references below
        seg_count += 1

        for j in range(n_campaigns):
            suffix_idx = (i * n_campaigns + j) % len(campaign_suffixes)
            cam = CampaignORM(
                id=uuid.uuid4(),
                org_id=ct.org_id,
                segment_id=seg.id,
                name=f"{seg.name.split('—')[0].strip()} — {campaign_suffixes[suffix_idx]}",
                description=f"Targeting {seg.name} with a focused stimulus test.",
                status=random.choice(["draft", "running", "completed"]),
                created_by=uuid.UUID(ct.sub) if _is_uuid(ct.sub) else None,
            )
            db.add(cam)
            cam_count += 1

            n_variants = random.randint(1, 3)
            for stim in random.sample(_ALL_STIMULI, k=min(n_variants, len(_ALL_STIMULI))):
                var = CampaignVariantORM(
                    id=uuid.uuid4(),
                    campaign_id=cam.id,
                    name=_variant_name(stim),
                    stimulus=stim,
                )
                db.add(var)
                var_count += 1

        for _ in range(n_runs):
            stim      = random.choice(_ALL_STIMULI)
            sentiment = random.choices(_SENTIMENTS, weights=_SENTIMENT_WEIGHTS)[0]
            score     = _rand_score(sentiment)
            latency   = random.randint(800, 4500)
            created   = _rand_ts(30)
            run = SimulationRunORM(
                id=uuid.uuid4(),
                org_id=ct.org_id,
                segment_id=seg.id,
                stimulus=stim,
                verbatim_response=random.choice(_VERBATIM_TEMPLATES[sentiment]),
                sentiment=sentiment,
                likelihood_to_convert=round(score + random.uniform(-0.05, 0.05), 4),
                conversion_score=score,
                llm_metadata={
                    "key_factors": ["price sensitivity", "category match", "timing"],
                    "input_tokens": random.randint(400, 900),
                    "output_tokens": random.randint(80, 220),
                    "latency_ms": latency,
                },
                status="completed",
                model_id="claude-sonnet-4-6",
                created_at=created,
                completed_at=created + timedelta(milliseconds=latency),
            )
            db.add(run)
            run_count += 1

    await db.flush()

    return SeedResponse(
        segments=seg_count,
        campaigns=cam_count,
        campaign_variants=var_count,
        simulation_runs=run_count,
        message=f"Seeded {seg_count} segments, {cam_count} campaigns, {var_count} variants, {run_count} simulation runs.",
    )


@router.delete("/clear", response_model=ClearResponse)
async def clear_database(
    claims: Annotated[object, Depends(require(Permission.ORG_DATA_DELETE))],
    db:     DbDep,
) -> ClearResponse:
    """Delete all segments, campaigns, variants and simulation runs for the current org."""
    _guard_non_production()

    from api.auth.jwt_handler import TokenClaims
    ct: TokenClaims = claims  # type: ignore[assignment]

    # Runs
    run_result = await db.execute(
        delete(SimulationRunORM).where(SimulationRunORM.org_id == ct.org_id)
    )

    # Variants (via campaign FK)
    campaign_ids = (await db.execute(
        select(CampaignORM.id).where(CampaignORM.org_id == ct.org_id)
    )).scalars().all()
    if campaign_ids:
        await db.execute(
            delete(CampaignVariantORM).where(CampaignVariantORM.campaign_id.in_(campaign_ids))
        )

    # Campaigns
    cam_result = await db.execute(
        delete(CampaignORM).where(CampaignORM.org_id == ct.org_id)
    )

    # Segments
    seg_result = await db.execute(
        delete(SegmentORM).where(SegmentORM.org_id == ct.org_id)
    )

    await db.flush()

    deleted_runs = run_result.rowcount or 0
    deleted_cams = cam_result.rowcount or 0
    deleted_segs = seg_result.rowcount or 0

    return ClearResponse(
        deleted_segments=deleted_segs,
        deleted_campaigns=deleted_cams,
        deleted_runs=deleted_runs,
        message=f"Cleared {deleted_segs} segments, {deleted_cams} campaigns, {deleted_runs} simulation runs.",
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_uuid(s: str) -> bool:
    try:
        uuid.UUID(s)
        return True
    except ValueError:
        return False


def _variant_name(stim: dict) -> str:
    t = stim.get("type", "")
    if t == "ad_copy":
        return f"Ad Copy — {stim.get('cta', 'CTA')}"
    if t == "price_change":
        return f"Price Drop — {stim.get('product_name', 'Product')}"
    return f"Promo — {stim.get('promo_code', 'CODE')}"
