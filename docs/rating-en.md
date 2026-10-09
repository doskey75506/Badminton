# Rating rules

This document describes the rating algorithm used by the app (`ratings.py`). Team-sum Elo with K = 32.

## Formula

```
delta = 32 × (actual result − expected score) × margin multiplier
```

- **Team strength** = sum of all teammates' ratings (e.g. in 2v2: 1000 + 1100 = 2100 vs 1900 + 2000 = 3900)
- **Expected score** (standard Elo): `1 / (1 + 10^((ratingB − ratingA) / 400))`
- **Actual result**: win = 1, loss = 0 (ties are rejected)
- **Margin multiplier**: `ln(point_diff + 1) × 2.2 / (rating_diff × 0.001 + 2.2)`, clamped to **[1.0, 2.0]**

## Margin multiplier behavior

- Bigger score lines give bigger multipliers: 21:20 ≈ 1.0, 21:15 ≈ 1.95, 21:10 hits the 2.0 cap
- Closer teams give bigger multipliers; at a 400-point gap it is about 0.85, so a strong team beating a weak one gains less (then the 1.0 floor kicks in)
- The 1.0 floor means the multiplier **only amplifies — it never reduces a change below the base value**; a tight 21:20 win still gets the full base delta

## How it is applied

- Every teammate gains (or loses) the **same delta**; it is not split by individual contribution
- Ratings are rounded to 1 decimal and floored at 0 (never go negative)
- Both teams' ratings are **snapshotted at match start** (`ratings_before`) and the change is **applied only when the score is submitted** — finishing another match in between does not affect this one

## Validation

- Ties, scores outside 0–30, and empty teams are all rejected

## Example

Both teams at 2000 (each player 1000), score 21:15:

| Step | Value |
| --- | --- |
| Expected score | 0.5 |
| Margin multiplier | ln(7) × 1.0 ≈ 1.95 |
| delta | 32 × 0.5 × 1.95 ≈ **+31.1** |

Each winner goes 1000 → 1031.1; each loser → 968.9.
