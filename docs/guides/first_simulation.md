# How to Run Your First Simulation
> **Synthetic Persona Sandbox** — Getting Started Guide

---

## What you'll build

By the end of this guide you will have:
1. Defined a customer segment (e.g. "Gen Z, Madrid, 18–24")
2. Created a campaign with an ad copy stimulus
3. Launched a simulation and reviewed the persona's synthetic response
4. Compared conversion scores across multiple variants

**Time to complete:** ~10 minutes

---

## Prerequisites

| Requirement | Check |
|-------------|-------|
| Account with `marketer` or `admin` role | Ask your org admin to invite you via **Org Settings → Members** |
| The Sandbox dashboard is open | `https://app.syntheticpersonasandbox.com` (or `http://localhost:5173` in dev) |

---

## Step 1 — Define a Customer Segment

A **Segment** is a definition of your target audience. The platform uses it to build a synthetic persona that responds to your stimuli.

1. In the top navigation, click **Segments**.
2. Click **New Segment**.
3. Fill in the form:

   | Field | Example |
   |-------|---------|
   | **Name** | Gen Z — Madrid |
   | **Description** | Urban young adults, high digital engagement |
   | **Age range** | 18 – 24 |
   | **City** | Madrid |
   | **Country** | Spain |
   | **Category affinities** | Electronics, Fashion, Social Media |
   | **Purchase history window** | 90 days |

4. Click **Save Segment**. The segment will appear with a `stale` badge — this is expected. The embedding is computed asynchronously by the Airflow pipeline.

> **Tip:** You can run simulations against a stale segment. The platform uses the definition directly if no embedding is available yet.

---

## Step 2 — Create a Campaign

A **Campaign** groups multiple ad variants that will compete against the same segment.

1. Click **Campaigns** in the navigation.
2. Click **New Campaign**.
3. Enter a name (e.g. "Summer Sale — Gen Z") and select the segment you created.
4. Click **Continue**.

---

## Step 3 — Add Variants

Each **Variant** is a specific stimulus — an ad, a price change, or a promo — that will be shown to the persona.

1. On the campaign page, click **Add Variant**.
2. Choose stimulus type: **Ad Copy**.
3. Fill in:

   | Field | Example |
   |-------|---------|
   | **Variant name** | Headline A — Emotional |
   | **Headline** | "The sneakers that move with you." |
   | **Body copy** | "Crafted for the city. Born for the moment. New drop available now." |
   | **Call to action** | Shop Now |

4. Click **Add Variant** again to create a second variant to compare:

   | Field | Example |
   |-------|---------|
   | **Variant name** | Headline B — Rational |
   | **Headline** | "30% off this weekend only." |
   | **Body copy** | "Premium sneakers at a price that makes sense. Limited stock." |
   | **CTA** | Get the Deal |

---

## Step 4 — Launch the Simulation

1. Click **Launch Simulation**.
2. You will see the **Thinking…** animation for each variant. The platform sends each stimulus to the synthetic persona (powered by Claude) and waits for a response.
3. Results appear as they complete — no need to refresh.

**What the platform computes for each variant:**

| Metric | What it means |
|--------|--------------|
| **Conversion Score** | Probability (0–1) that this segment converts given this stimulus |
| **Sentiment** | Persona's emotional reaction: `positive`, `neutral`, `negative` |
| **Likelihood to convert** | The persona's self-reported intent: `high`, `medium`, `low` |
| **Verbatim response** | What the synthetic persona "said" about the ad |

---

## Step 5 — Review Results

The **Simulation Results** page shows:
- A ranked leaderboard of variants by conversion score
- Score bars with semantic color coding (green = high, red = low)
- Sentiment pills per variant
- The full verbatim persona response (expandable)

**Reading the results:**
- A score above `0.70` is strong — this variant resonates with the segment.
- A score below `0.40` suggests the message is misaligned with this audience.
- Compare sentiment: a `negative` sentiment with a high score can indicate the persona is motivated by urgency or fear, not enthusiasm — check the verbatim to confirm.

---

## Step 6 — Explore Historical Data

Click **Analytics** in the navigation to access:

- **Conversion Trend** — how scores have evolved over your simulation history
- **Stimulus Breakdown** — which stimulus types perform best for your org
- **Variant Comparison** — compare any subset of past runs side-by-side
- **History Table** — filter by date, segment, or score range; export to CSV

---

## Frequently Asked Questions

**How long does a simulation take?**
Typically 3–8 seconds per variant. If the API worker queue is busy, it may take up to 30 seconds. The progress bar updates in real-time via WebSocket.

**How accurate are the synthetic personas?**
The personas are calibrated against behavioral segment embeddings. Conversion scores on holdout validation achieve AUC ≥ 0.72. Use them to rank and eliminate weak variants — not as absolute CTR predictions.

**Can I test price changes?**
Yes. Choose **Price Change** as the stimulus type and enter the new price and original price. The persona will respond based on its price sensitivity profile.

**Can I test promotional offers?**
Yes. Choose **Promo** and enter the discount percentage, duration, and conditions (e.g., "free shipping on orders over €50").

**How do I invite teammates?**
Go to **Org Settings → Members → Invite Member**. You must have `admin` role to invite.

**How do I create an API key for programmatic access?**
Go to **Org Settings → API Keys → Create Key**. Copy the key immediately — it is shown only once.

---

## Next Steps

- **API access** — see [`docs/api/README.md`](../api/README.md) to integrate simulations into your own tooling
- **Airflow DAGs** — see the [Airflow UI](http://localhost:8080) to trigger bulk simulation pipelines
- **Security** — see [`docs/security/owasp_checklist.md`](../security/owasp_checklist.md) for the platform's security posture
