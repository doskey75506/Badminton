# 积分规则 / Rating rules

本页描述 app 使用的积分算法（`ratings.py`）。团队总和 Elo，K = 32。

This document describes the rating algorithm used by the app (`ratings.py`). Team-sum Elo with K = 32.

---

## 中文

### 公式

```
delta = 32 × (实际结果 − 期望胜率) × 分差倍率
```

- **双方实力** = 队内所有队员积分之和（如 2v2：1000 + 1100 = 2100 对 1900 + 2000 = 3900）
- **期望胜率**（标准 Elo）：`1 / (1 + 10^((积分B − 积分A) / 400))`
- **实际结果**：胜 = 1，负 = 0（不允许平局）
- **分差倍率**：`ln(分差 + 1) × 2.2 / (积分差 × 0.001 + 2.2)`，结果限制在 **[1.0, 2.0]**

### 分差倍率的行为

- 分差越大倍率越高：21:20 ≈ 1.0，21:15 ≈ 1.95，21:10 达到 2.0 封顶
- 双方越接近倍率越高；积分差 400 时约 0.85，强者赢弱者涨得少（随后被下限 1.0 托起）
- 下限 1.0：倍率**只会放大、永远不会把涨幅压到基础值以下**——21:20 的险胜拿满基础涨幅

### 应用方式

- 全队每人加（或减）**相同的 delta**，不按个人贡献分摊
- 保留 1 位小数，下限 0 分（不会减成负数）
- **开赛时**快照双方积分（`ratings_before`），**提交比分时**才结算——中途在其他场地打完的比赛不影响本场

### 校验

- 平局、比分超出 0–30、空队伍均拒绝提交

### 示例

双方各 1000 分（2v2 各 2000），比分 21:15：

| 步骤 | 值 |
| --- | --- |
| 期望胜率 | 0.5 |
| 分差倍率 | ln(7) × 1.0 ≈ 1.95 |
| delta | 32 × 0.5 × 1.95 ≈ **+31.1** |

胜方每人 1000 → 1031.1，负方每人 → 968.9。

---

## English

### Formula

```
delta = 32 × (actual result − expected score) × margin multiplier
```

- **Team strength** = sum of all teammates' ratings (e.g. in 2v2: 1000 + 1100 = 2100 vs 1900 + 2000 = 3900)
- **Expected score** (standard Elo): `1 / (1 + 10^((ratingB − ratingA) / 400))`
- **Actual result**: win = 1, loss = 0 (ties are rejected)
- **Margin multiplier**: `ln(point_diff + 1) × 2.2 / (rating_diff × 0.001 + 2.2)`, clamped to **[1.0, 2.0]**

### Margin multiplier behavior

- Bigger score lines give bigger multipliers: 21:20 ≈ 1.0, 21:15 ≈ 1.95, 21:10 hits the 2.0 cap
- Closer teams give bigger multipliers; at a 400-point gap it is about 0.85, so a strong team beating a weak one gains less (then the 1.0 floor kicks in)
- The 1.0 floor means the multiplier **only amplifies — it never reduces a change below the base value**; a tight 21:20 win still gets the full base delta

### How it is applied

- Every teammate gains (or loses) the **same delta**; it is not split by individual contribution
- Ratings are rounded to 1 decimal and floored at 0 (never go negative)
- Both teams' ratings are **snapshotted at match start** (`ratings_before`) and the change is **applied only when the score is submitted** — finishing another match in between does not affect this one

### Validation

- Ties, scores outside 0–30, and empty teams are all rejected

### Example

Both teams at 2000 (each player 1000), score 21:15:

| Step | Value |
| --- | --- |
| Expected score | 0.5 |
| Margin multiplier | ln(7) × 1.0 ≈ 1.95 |
| delta | 32 × 0.5 × 1.95 ≈ **+31.1** |

Each winner goes 1000 → 1031.1; each loser → 968.9.
