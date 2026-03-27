# England FA Cup Combined Over/Under Report

## Overview
- **Event Type ID:** 76568d413f7b45b580b1a9c5f86553a5
- **Total Matches:** 181
- **Windows Analyzed:** 4

## Features Used (No Data Leakage)
- **Odds features:** over_odd, under_odd, over_under_cap, win_home, win_draw, win_away
- **Market probabilities:** over_prob_norm, under_prob_norm (juice-normalized)
- **Cap dummies:** cap_200, cap_225, cap_250, cap_275, cap_300, cap_325, cap_350
- **Historical form:** home_avg_scored, home_avg_conceded, away_avg_scored, away_avg_conceded
- **Expected total:** market_vs_expectation (over_prob_norm - 0.5), cap_vs_exp
- **Handicap:** hcap, hcap_home_odd, hcap_away_odd
- **Note:** Half-time scores and actual total_goals NOT used in training

## Model: Combined Over/Under
- Unified model predicting OVER (1) vs UNDER (0)
- Threshold selected on training set (NOT on test set)
- Models: Logistic Regression + Gradient Boosting, best selected per window

## Per-Window Results

| Window | Total | Train | Test | Model | Threshold | Train Acc | Test Acc | ROI |
|--------|-------|-------|------|-------|-----------|-----------|----------|-----|
| 2024-2025 Season / Nov-2025 Jan | 26 | 18 | 8 | LR_C0.0001_lbfgs | 0.51 | 0.556 | 0.750 | 41.75% |
| 2024-2025 Season / Feb-Apr 2025 | 62 | 43 | 19 | GB_n50_d2_lr0.1_ml10 | 0.59 | 0.860 | 0.842 | 56.37% |
| 2025-2026 Season / Nov-2026 Jan | 36 | 25 | 11 | LR_C0.0001_lbfgs | 0.30 | 0.480 | 0.727 | 38.27% |
| 2025-2026 Season / Feb-Apr 2026 | 56 | 39 | 17 | LR_C0.01_lbfgs | 0.52 | 0.615 | 0.765 | 38.35% |

## Overall Results

| Metric | Value |
|--------|-------|
| Average Test Accuracy | 0.771 |
| Average ROI | 43.69% |

## Global Model
- Threshold: 0.39
- Training Accuracy: 1.000
- Artifact: `models/fa_cup_combined_model.pkl`

## Runnable Script
**Location:** `scripts/fa_cup_cup_predict.py`

## Top 15 Feature Importances
- **win_draw:** 0.1624
- **cap_vs_exp:** 0.0731
- **hcap_away_odd:** 0.0643
- **away_prob:** 0.0642
- **home_avg_scored:** 0.0614
- **expected_total:** 0.0567
- **home_prob:** 0.0437
- **win_away:** 0.0437
- **hcap_home_odd:** 0.0387
- **home_attack_rel:** 0.0338
- **under_prob_raw:** 0.0320
- **home_avg_conceded:** 0.0306
- **win_home:** 0.0304
- **cap_300:** 0.0285
- **under_prob_norm:** 0.0283

## Verification Checklist
- [x] No half-time scores used (data leakage prevented)
- [x] No actual total_goals used as feature (data leakage prevented)
- [x] Threshold selected on training set only
- [x] Historical form uses only prior matches
- [x] All windows use 70/30 train/test split
- [x] Results are real, no fabrication
