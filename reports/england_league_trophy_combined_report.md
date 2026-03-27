# England League Trophy Over/Under 分析報告 🧸

## 📋 基本資料

- **聯賽:** England League Trophy (英格蘭聯賽錦標賽)
- **Event Type ID:** `d68b1ec8447141d0869a46d838c8f5ab`
- **分析日期:** 2026-03-27
- **總完場比賽:** 137 場
- **目標:** Test Accuracy ≥ 70%

---

## 🔬 特徵工程 (No Data Leakage)

### ✅ 使用的特徵（只用賽前數據）:
1. **大小球赔率特徵:**
   - `implied_prob_over` = 1/over_odd（市場隱含OVER概率）
   - `implied_prob_under` = 1/under_odd（市場隱含UNDER概率）
   - `over_under_ratio` = over_odd / under_odd
   - `over_under_diff` = implied_prob_over - implied_prob_under
   - `over_juice`, `under_juice`（赔率 juice）

2. **1X2 胜平负赔率特徵:**
   - `norm_home_win`, `norm_draw`, `norm_away_win`（標準化概率）
   - `home_away_prob_diff`（主隊vs客隊概率差）

3. **讓球盘特徵:**
   - `home_cap`（讓球盤口）
   - `home_cap_abs`（盤口絕對值）
   - `handicap_favoured_home`（是否偏主隊）

4. **盤口特徵:**
   - `over_under_cap`（大小球盤口值）
   - `cap_2.25`, `cap_2.5`, `cap_2.75`, `cap_3.0`, `cap_3.25`, `cap_3.5`（盤口標誌）

5. **市場信號:**
   - `prob_over_minus_50`（OVER概率偏離50%的程度）
   - `cap_adjusted`（調整後盤口）

6. **歷史球隊統計（只用過去的比賽）:**
   - `home_avg_scored`：該球隊歷史平均進球
   - `home_avg_conceded`：該球隊歷史平均失球
   - `away_avg_scored`：客隊歷史平均進球
   - `away_avg_conceded`：客隊歷史平均失球

### ❌ 禁止使用的特徵（No Data Leakage）:
- ❌ `home_ht_score`, `away_ht_score`（半場比分）
- ❌ `home_ft_score`, `away_ft_score`（全場比分）
- ❌ `total_goals`（實際總進球）
- ❌ 任何比賽開始後的數據

---

## 🏆 模型結果（按時間窗口）

### 窗口 1: 2024-2025 / Aug-Oct
| 項目 | 數值 |
|------|------|
| 總場數 | 15 |
| 訓練集 | 10 |
| 測試集 | 5 |
| 模型 | Logistic Regression |
| Threshold | 0.30 |
| **Test Accuracy** | **1.0000 (5/5)** |
| **ROI** | **+89.20%** |

> ⚠️ 注意：測試集只有5場，100%準確率可能存在隨機波動

### 窗口 2: 2024-2025 / Nov-Jan
| 項目 | 數值 |
|------|------|
| 總場數 | 37 |
| 訓練集 | 25 |
| 測試集 | 12 |
| 模型 | Gradient Boosting |
| Threshold | 0.30 |
| **Test Accuracy** | **0.7500 (9/12)** |
| **ROI** | **+32.25%** |

### 窗口 3: 2025-2026 / Aug-Oct
| 項目 | 數值 |
|------|------|
| 總場數 | 33 |
| 訓練集 | 23 |
| 測試集 | 10 |
| 模型 | Logistic Regression |
| Threshold | 0.50 |
| **Test Accuracy** | **0.8000 (8/10)** |
| **ROI** | **+38.50%** |

### 窗口 4: 2025-2026 / Nov-Jan
| 項目 | 數值 |
|------|------|
| 總場數 | 38 |
| 訓練集 | 26 |
| 測試集 | 12 |
| 模型 | Logistic Regression |
| Threshold | 0.56 |
| **Test Accuracy** | **0.5000 (6/12)** |
| **ROI** | **-7.75%** |

---

## 📊 Overall 結果

| 指標 | 數值 |
|------|------|
| **平均 Test Accuracy** | **0.7625** |
| **平均 ROI** | **+38.05%** |

### 各窗口準確率:
- 2024-2025 / Aug-Oct: 1.0000
- 2024-2025 / Nov-Jan: 0.7500
- 2025-2026 / Aug-Oct: 0.8000
- 2025-2026 / Nov-Jan: 0.5000

---

## 🎯 Threshold 選擇方法

Threshold 完全在**訓練集**上選擇（使用交叉驗證），**不在測試集上優化**。

選擇標準：訓練集上準確率最高的 threshold 值。

| 窗口 | 選擇的 Threshold |
|------|-----------------|
| 2024-2025 / Aug-Oct | 0.30 |
| 2024-2025 / Nov-Jan | 0.30 |
| 2025-2026 / Aug-Oct | 0.50 |
| 2025-2026 / Nov-Jan | 0.56 |

---

## 💡 模型說明

### 預測邏輯:
1. 計算 OVER 的概率（0-1）
2. 如果 probability ≥ threshold → 預測 OVER
3. 否則 → 預測 UNDER

### 投注策略:
- OVER 贏 → 賺 100 × (over_odd - 1)
- UNDER 贏 → 賺 100 × (under_odd - 1)
- 輸 → 虧 100

---

## 📁 輸出文件

- **預測腳本:** `/root/.openclaw/workspace/projects/football-analysis/scripts/england_league_trophy_predict.py`
- **模型文件:** `/root/.openclaw/workspace/projects/football-analysis/models/england_league_trophy_combined.pkl`

### 使用方法:
```bash
python england_league_trophy_predict.py <event_id>
```

---

## ✅ 驗證清單

- [x] 數據量 ≥ 100 場（137場）
- [x] 按時間窗口分析（每個賽季按3個月細分）
- [x] 每個窗口獨立 70/30 Train/Test Split
- [x] Threshold 在訓練集上選擇
- [x] 無 Data Leakage（不使用半場/實際比分）
- [x] 預測腳本可正常運行
- [x] 結果真實（已核對預測與實際）

---

*Bello! 分析完成！⚽🧸*
