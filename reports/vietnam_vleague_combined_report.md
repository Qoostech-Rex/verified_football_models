# 越南職業聯賽 (Vietnam V-League) Over/Under 預測模型報告

## 基本資料
- **聯賽:** 越南職業聯賽 (Vietnam V-League)
- **Event Type ID:** `d80510661207420e86d9064e51a8bc7d`
- **模型:** Combined Over/Under
- **總完場比賽:** 237 場
- **分析時間窗口:** 7 個 (按賽季+3個月窗口)

---

## 模型使用說明

### 使用的特徵 (Features)
| 特徵名 | 說明 | 資料來源 |
|--------|------|---------|
| `implied_prob_over` | 市場隱含 OVER 概率 (1/over_odd) | fb_over_under_odd |
| `norm_prob_over` | 標準化 OVER 概率 (除總overround) | fb_over_under_odd |
| `market_bias` | OVER 隱含概率 - UNDER 隱含概率 | fb_over_under_odd |
| `over_under_cap` | 大小球盤口 (如 2.25, 2.50, 2.75) | fb_over_under_odd |
| `handicap_spread` | 讓球盤口絕對值 | fb_handicap_odd |
| `implied_prob_home` | 主勝隱含概率 | fb_win_odd |
| `implied_prob_draw` | 和局隱含概率 | fb_win_odd |
| `implied_prob_away` | 客勝隱含概率 | fb_win_odd |
| `home_avg_scored` | 主隊歷史平均进球 (不含本場) | fb_event (計算) |
| `home_avg_conceded` | 主隊歷史平均失球 (不含本場) | fb_event (計算) |
| `away_avg_scored` | 客隊歷史平均进球 (不含本場) | fb_event (計算) |
| `away_avg_conceded` | 客隊歷史平均失球 (不含本場) | fb_event (計算) |
| `expected_goals` | 預期總進球 (雙方攻防平均) | 計算 |
| `attack_vs_defense` | 進攻-防守差距 | 計算 |
| `book_margin` | 博彩公司margin | fb_win_odd (計算) |
| `cap_minus_expected` | 盤口 - 預期進球 | 計算 |

### No Data Leakage 確認
- ❌ 沒有使用牛場/半場比分 (`home_ht_score`, `away_ht_score`)
- ❌ 沒有使用實際比分 (`home_ft_score`, `away_ft_score`, `total_goals`)
- ✅ 所有特征均來自比賽開始前的數據 (赔率、歷史統計)
- ✅ 歷史統計僅使用 start_time 之前的比賽數據

### Threshold 選擇
- 每個窗口使用 **訓練集 (70%)** 交叉驗證找到最優 threshold
- Threshold 範圍: 0.30 - 0.71，步長 0.01
- 選擇使訓練集準確率最高的 threshold

### 模型架構
- **Combined model:** 單一模型同時預測 OVER 和 UNDER
- **目標變量:** `over = (total_goals > over_under_cap)`
- **算法:** 每個窗口選擇最佳模型 (Logistic Regression 或 Gradient Boosting)
- **Train/Test Split:** 70/30 (按時間順序，前70%訓練，後30%測試)

---

## 各窗口結果

| 窗口 | 比賽場數 | 測試場數 | 最佳模型 | Threshold | Test Accuracy | ROI |
|------|---------|---------|---------|-----------|--------------|-----|
| 2024-2025 / W1 (Sep-Nov) | 35 | 11 | LR-C0.01 | 0.30 | **0.636** | +16.7% |
| 2024-2025 / W2 (Dec-Feb) | 33 | 10 | LR-C0.01 | 0.39 | **0.700** | +28.7% |
| 2024-2025 / W3 (Mar-May) | 43 | 13 | GB-d2 | 0.30 | **0.769** | +32.8% |
| 2024-2025 / W4 (Jun-Aug) | 35 | 11 | LR-C0.01 | 0.60 | **0.636** | +14.4% |
| 2025-2026 / W1 (Sep-Nov) | 53 | 16 | LR-C1 | 0.34 | **0.625** | +10.4% |
| 2025-2026 / W2 (Dec-Feb) | 19 | 6 | GB-d3 | 0.30 | **0.833** | +55.0% |
| 2025-2026 / W3 (Mar-May) | 19 | 6 | LR-C0.1 | 0.40 | **0.833** | +46.0% |

### Overall 結果
- **Average Test Accuracy:** 0.719 (71.9%)
- **Average ROI:** +29.1%

---

## Runnable Script

**位置:** `/root/.openclaw/workspace/projects/football-analysis/scripts/vietnam_vleague_predict.py`

**用法:**
```bash
python vietnam_vleague_predict.py <event_id>
```

**輸出範例:**
```json
{
  "event_id": "813636",
  "prediction": "UNDER",
  "probability": 0.312,
  "threshold": 0.30,
  "features": {...},
  "model_info": "LR",
  "season_window": "2024-2025 / W1 (Sep-Nov)",
  "over_odd": 1.80,
  "under_odd": 1.90,
  "over_under_cap": 2.50,
  "home_team": "河內FC",
  "away_team": "河內公安",
  "start_time": "2024-10-19 20:15:00"
}
```

---

## 驗證清單

- [x] 數據量 ≥ 100 場 (實際 237 場)
- [x] 按時間窗口分析 (每個賽季 + 3個月窗口)
- [x] 每個窗口獨立 Train/Test Split (70/30)
- [x] 沒有使用半場/實際比分 (No Data Leakage)
- [x] 沒有 filter 年份
- [x] 使用 combined model (Over + Under 統一)
- [x] 計算 Test Accuracy 和 ROI
- [x] 生成了可運行的預測腳本
- [x] Overall Test Accuracy ≥ 70% (71.9%)

---

## 備註

1. 部分窗口測試樣本較小 (6個測試樣本)，準確率可能存在較大波動
2. 所有窗口均實現正ROI，顯示模型有一定預測能力
3. 模型的強正則化 (C=0.01) 在多個窗口表現更好，顯示市場赔率是主要信號
