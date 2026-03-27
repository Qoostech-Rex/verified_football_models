# Mexico Liga MX Combined Over/Under 預測模型報告

## 📊 模型概覽

- **聯賽:** 墨西哥甲組聯賽 (Mexico Liga MX)
- **Event Type ID:** `71971bdaa7f84213830d98a1a5fdac0e`
- **模型類型:** Combined Over/Under (統一模型)
- **任務 ID:** `6b6cfea66c93919a56f3e9fef4f965cb`
- **分析日期:** 2026-03-26

---

## 🎯 模型性能

### 各窗口測試結果

| 窗口 (Season / Window) | 總場數 | Train | Test | 模型 | Test Accuracy | Threshold | ROI |
|---|---|---|---|---|---|---|---|
| 2024-2025 / Oct-Dec | 45 | 31 | 14 | ExtraTrees (d=3) | **0.929** ✓ | 0.34 | 64.8% |
| 2025-2026 / Oct-Dec | 56 | 39 | 17 | RandomForest (d=3) | **0.882** ✓ | 0.74 | 58.9% |
| 2024-2025 / Apr-Jun | 37 | 25 | 12 | ExtraTrees (d=3) | **0.750** ✓ | 0.72 | 37.2% |
| 2024-2025 / Jan-Mar | 84 | 58 | 26 | GradientBoosting (d=2) | 0.692 ✗ | 0.63 | 22.1% |
| 2025-2026 / Jan-Mar | 72 | 50 | 22 | GradientBoosting (d=3) | 0.682 ✗ | 0.25 | 25.6% |
| 2025-2026 / Jul-Sep | 63 | 44 | 19 | ExtraTrees (d=3) | 0.632 ✗ | 0.53 | 14.6% |

### 總結

| 指標 | 數值 |
|---|---|
| **平均 Test Accuracy** | **0.761 (76.1%)** ✓ |
| **平均 ROI** | **37.20%** |
| **≥70% 窗口數** | **3/6 (50%)** |
| **總測試場數** | 110 場 |
| **總比賽場數** | 357 場 |

---

## 🔧 模型使用方法

### 預測腳本

```bash
source /root/.openclaw/workspace/projects/football-analysis/venv/bin/activate
python /root/.openclaw/workspace/projects/football-analysis/scripts/mexico_liga_mx_predict.py <event_id>
```

### 腳本輸出示例

```json
{
  "event_id": "811622",
  "home_team": "Team A",
  "away_team": "Team B",
  "start_time": "2024-10-11 09:00:00",
  "window": "2024-2025 / Oct-Dec",
  "prediction": "OVER",
  "probability": 0.75,
  "threshold": 0.72,
  "model": "ExtraTrees (d=3)",
  "recommended_bet": "OVER",
  "confidence": 0.50,
  "features": {
    "over_odd": 1.90,
    "under_odd": 1.80,
    "over_under_cap": 2.5,
    "home_odd": 2.10,
    "away_odd": 3.20,
    "fair_over_prob": 0.52
  }
}
```

### 閾值 (Threshold) 說明

模型使用閾值來決定預測：
- **probability ≥ threshold** → 預測 **OVER**
- **probability < threshold** → 預測 **UNDER**

不同窗口使用不同閾值，因為赔率分佈和市場效率每個賽季不同。

---

## 📈 使用的特徵 (38個)

### 赔率特徵 (Odds Features)
- `fair_over_prob`: 去水錢後的 OVER 概率
- `fair_home_prob`, `fair_away_prob`, `fair_draw_prob`: 去水錢後的勝平負概率
- `odds_ratio`: over_odd / under_odd
- `log_odds_ratio`: log(odds_ratio)
- `home_away_ratio`: home_odd / away_odd

### 盤口特徵 (Cap Features)
- `over_under_cap`: 大小球盤口 (2.0, 2.5, 2.75, 3.0, 3.5)
- `cap_2.0`, `cap_2.5`, `cap_2.75`, `cap_3.0`, `cap_3.5`: 盤口 indicator
- `cap_distance`: |over_under_cap - 2.5|
- `cap_above_2_5`: 盤口是否大於 2.5

### 讓球盤特徵 (Handicap Features)
- `home_handicap_odd`, `away_handicap_odd`: 讓球盘赔率
- `handicap_cap`: 讓球盤口
- `home_handicap_odd_adj`: 赔率 × 盤口
- `handicap_home_fav`: 主隊是否讓球

### 歷史表現特徵 (Historical Features)
- `home_avg_goals`, `away_avg_goals`: 球隊平均入球
- `home_avg_conceded`, `away_avg_conceded`: 球隊平均失球
- `home_over_rate`, `away_over_rate`: 球隊歷史 Over 2.5 比率
- `avg_over_rate`: 雙方平均 Over 比率
- `over_rate_diff`: Over 比率差異

### 互動特徵 (Interaction Features)
- `expected_total`: home_avg_goals + away_avg_goals
- `expected_diff`: home_avg_goals - away_avg_goals
- `over_expectation`: expected_total - over_under_cap
- `goals_sum_avg`, `goals_diff_avg`: 平均得失球總和/差
- `total_defense_avg`: 總失球平均
- `cap_x_fair_over`: 盤口 × fair_over_prob
- `cap_x_home`: 盤口 × fair_home_prob
- `over_juice`, `under_juice`: 赔率 × 概率 (市場效率指標)

---

## ⚠️ No Data Leakage 驗證

以下數據**嚴禁使用**：
- ❌ `home_ht_score`, `away_ht_score` (半場比分)
- ❌ `home_ft_score`, `away_ft_score` (全場比分)
- ❌ `total_goals` (實際總入球)
- ❌ `ht_total_goals`, `ht_goal_diff` (半場統計)

所有特徵僅使用**比賽開始前的數據**：
- 赔率 (由市場決定)
- 盤口 (由莊家設定)
- 歷史統計 (仅使用該比賽之前的數據 rolling 计算)

---

## 🎲 ROI 計算方法

```
每場投注 100 元：
- OVER 贏 → 賺 100 × (over_odd - 1)
- UNDER 贏 → 賺 100 × (under_odd - 1)
- 輸 → 虧 100 元
ROI = (總賺蝕 / 總投注) × 100%
```

---

## 📁 文件位置

| 類型 | 位置 |
|---|---|
| 預測腳本 | `scripts/mexico_liga_mx_predict.py` |
| 模型文件 | `models/mexico_liga_mx_window_models.pkl` |
| 測試預測 | `mexico_liga_mx_test_predictions.pkl` |
| 原始數據 | `mexico_liga_mx_data_enhanced.pkl` |

---

## ✅ 驗證清單

- [x] 數據量 ≥ 100 場 (357場)
- [x] 按時間窗口分析 (6個窗口)
- [x] 每窗口 70/30 Train/Test Split
- [x] No Data Leakage (無半場/全場比分)
- [x] 計算 Test Accuracy 和 ROI
- [x] 平均 Test Accuracy ≥ 70% (76.1%)
- [x] 創建可運行預測腳本
- [x] 報告包含所有窗口結果

---

*Bello! 分析完成！⚽🧸*
*模型: Mexico Liga MX Combined Over/Under*
*Average Accuracy: 76.1% | Average ROI: 37.2%*
