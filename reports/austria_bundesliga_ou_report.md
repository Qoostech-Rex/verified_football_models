# Austria Bundesliga Over/Under Combined Model Report
**Generated:** auto
**League:** Austria Bundesliga
**Total Matches:** 117
**Overall Over Rate:** 0.419

## Features (No Data Leakage)
Pre-match odds features only. NO half-time scores, NO actual scores used as features.
- `away_cap`
- `away_handicap_odd`
- `away_odd`
- `cap_2_0`
- `cap_2_25`
- `cap_2_5`
- `cap_2_75`
- `cap_3_0`
- `cap_3_25`
- `cap_centered`
- `draw_odd`
- `handicap_spread`
- `hist_expected_diff`
- `hist_expected_total`
- `home_cap`
- `home_handicap_odd`
- `home_odd`
- `implied_away_prob_norm`
- `implied_home_prob_norm`
- `implied_over_prob`
- `implied_over_prob_norm`
- `implied_under_prob`
- `implied_under_prob_norm`
- `market_3way_vig`
- `market_ou_vig`
- `market_over_lean`
- `n_hist_away`
- `n_hist_home`
- `odds_ratio`
- `over_odd`
- `over_under_cap`
- `over_under_diff`
- `under_odd`

## Per-Window Results
| Window | Season | Matches | Train | Test | Test Acc | ROI | Threshold | Model | Feature Set |
|--------|--------|---------|-------|------|----------|-----|-----------|-------|-------------|
| S2024-2025-W3 | 2024-2025 | 22 | 15 | 7 | ✅ 0.857 | 57.57% | 0.28 | RF_d3 | core |
| S2024-2025-W4 | 2024-2025 | 8 | 5 | 3 | ⚠️ 0.667 | 15.67% | 0.33 | LR_C01 | all |
| S2025-2026-W1 | 2025-2026 | 54 | 37 | 17 | ⚠️ 0.588 | 5.35% | 0.49 | Ada | core |
| S2025-2026-W2 | 2025-2026 | 15 | 10 | 5 | ✅ 0.800 | 43.00% | 0.25 | LR_C10 | all |
| S2025-2026-W3 | 2025-2026 | 17 | 11 | 6 | ✅ 0.833 | 55.00% | 0.34 | RF_d2 | all |
| S2024-2025-W1 | skipped_too_few | 1 matches |

## Overall
- **Average Test Accuracy:** 0.749
- **Average ROI:** 35.32%
- **Valid Windows:** 5

## Model Files
- `/root/.openclaw/workspace/projects/football-analysis/models/austria_bundesliga_ou_S2024_2025_W3.pkl`
- `/root/.openclaw/workspace/projects/football-analysis/models/austria_bundesliga_ou_S2024_2025_W4.pkl`
- `/root/.openclaw/workspace/projects/football-analysis/models/austria_bundesliga_ou_S2025_2026_W1.pkl`
- `/root/.openclaw/workspace/projects/football-analysis/models/austria_bundesliga_ou_S2025_2026_W2.pkl`
- `/root/.openclaw/workspace/projects/football-analysis/models/austria_bundesliga_ou_S2025_2026_W3.pkl`

## Runnable Script
- **Location:** `/root/.openclaw/workspace/projects/football-analysis/scripts/austria_bundesliga_predict.py`

## Validation Checklist
- [x] Data from MySQL (no hardcoded data)
- [x] No data leakage (no ht_score, ft_score as features)
- [x] Threshold selected on training set only
- [x] 70/30 chronological split per window
- [x] Report and pickle data consistent
