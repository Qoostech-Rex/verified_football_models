# Serbia Super Liga Combined Over/Under Analysis Report

## Overview
- **League:** Serbia Super Liga
- **Event Type ID:** `30281baf2d1444fd91d421576d3cc16d`
- **Model Type:** Combined Over/Under (single model predicts both)
- **Total Matches Analyzed:** 247 completed matches
- **Seasons Covered:** 2024-2025, 2025-2026

## Data Validation
- ✅ Completed matches: 247 (≥100, OK)
- ✅ No data leakage: Only pre-match odds and historical stats used
- ❌ HT/FT scores NOT used as features
- ✅ No year filtering applied

## Season/Window Breakdown

| Season/Window | Total Matches | Train | Test | Test Accuracy | ROI |
|--------------|--------------|-------|------|---------------|-----|
| 2024-2025 / W1 | 7 | - | - | Skipped (<20) | - |
| 2024-2025 / W2 | 36 | 25 | 11 | 81.8% | +48.3% |
| 2024-2025 / W3 | 46 | 32 | 14 | 57.1% | +6.2% |
| 2024-2025 / W4 | 27 | 18 | 9 | 77.8% | +43.2% |
| 2025-2026 / W1 | 50 | 35 | 15 | 60.0% | +5.8% |
| 2025-2026 / W2 | 40 | 28 | 12 | 75.0% | +33.4% |
| 2025-2026 / W3 | 41 | 28 | 13 | 69.2% | +21.8% |

## Overall Results
- **Average Test Accuracy:** 0.702 (70.2%) ✅
- **Average ROI:** +26.45%
- **Weighted Average Accuracy:** 0.649

## Features Used (34 total)
**No Data Leakage - All features are pre-match only:**

1. **Odds Features:**
   - `over_odd`, `under_odd`, `over_under_cap`
   - `home_odd`, `draw_odd`, `away_odd`

2. **Implied Probability Features:**
   - `implied_over_prob`, `implied_under_prob`
   - `implied_home_prob`, `implied_draw_prob`, `implied_away_prob`

3. **Ratio/Diff Features:**
   - `over_under_ratio`, `home_away_ratio`
   - `ou_odds_gap`, `ha_odds_gap`

4. **Cap Features:**
   - `cap_level` (over_under_cap - 2.5)
   - `cap_floor` (indicator for low caps)

5. **Handicap Features:**
   - `home_cap`, `home_handicap_odd`, `away_handicap_odd`

6. **Market Indicators:**
   - `market_bias_over`, `market_favorite_home`
   - `overround_ou`, `overround_ha`
   - `logit_over`, `logit_home`

7. **Historical Performance (rolling):**
   - `home_avg_scored`, `home_avg_conceded`
   - `away_avg_scored`, `away_avg_conceded`
   - `home_over_rate`, `away_over_rate`
   - `combined_avg_total`, `avg_over_rate`

## Model Details
- **Models Used:** Random Forest, Gradient Boosting (selected per window)
- **Feature Selection:** SelectKBest (k=20)
- **Threshold:** Optimized per window (range: 0.20-0.74)

## Files Generated
- **Models:** `/root/.openclaw/workspace/projects/football-analysis/models/serbia_super_liga_combined_ou_models.pkl`
- **Data:** `/root/.openclaw/workspace/projects/football-analysis/reports/serbia_super_liga_enhanced_data.pkl`
- **Results:** `/root/.openclaw/workspace/projects/football-analysis/reports/serbia_super_liga_results.csv`
- **Prediction Script:** `/root/.openclaw/workspace/projects/football-analysis/scripts/serbia_super_liga_predict.py`

## Prediction Script Usage
```bash
python serbia_super_liga_predict.py <event_id>
```

Returns:
- `prediction`: "OVER" or "UNDER"
- `probability`: Probability of OVER
- `threshold`: Model threshold used
- `window_used`: Which season/window model was used
