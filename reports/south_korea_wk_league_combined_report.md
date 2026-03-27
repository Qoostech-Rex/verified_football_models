# South Korea WK-League Combined Over/Under 模型報告 🧸⚽

## 模型概述
- **聯賽:** 南韓女子職業聯賽 (South Korea WK-League)
- **Event Type ID:** 9a68bdbe5a70460fb0704a3d22a6a602
- **目標:** Over/Under 2.5 預測（combined model）
- **總完場比賽:** 100場

---

## 特徵列表（No Data Leakage）

所有特徵均為**比賽前**可獲得的數據，**不使用**半場比分或實際比分：

| 特徵名 | 說明 |
|--------|------|
| f_cap | Over/Under 盤口值 |
| f_over_odd | OVER 赔率 |
| f_under_odd | UNDER 赔率 |
| f_home_odd | 主勝赔率 |
| f_draw_odd | 和局赔率 |
| f_away_odd | 客勝赔率 |
| f_ou_ratio | OVER/UNDER 赔率比率 |
| f_ha_ratio | 主勝/客勝赔率比率 |
| f_imp_over | 市場隱含OVER概率 (1/over_odd) |
| f_imp_home | 市場隱含主勝概率 (1/home_odd) |
| f_ht_h_sc | 主隊主場平均進球（歷史） |
| f_ht_a_sc | 主隊客場平均進球（歷史） |
| f_at_h_sc | 客隊主場平均進球（歷史） |
| f_at_a_sc | 客隊客場平均進球（歷史） |
| f_ht_h_co | 主隊主場平均失球（歷史） |
| f_at_a_co | 客隊客場平均失球（歷史） |
| f_ht_ovr | 主隊最近5場OVER率 |
| f_at_ovr | 客隊最近5場OVER率 |
| f_cap_rel | 盤口相對值（cap - 歷史平均總进球） |
| f_ht_total | 主隊歷史平均總进球 |
| f_at_total | 客隊歷史平均總进球 |

---

## 比賽窗口分佈

| 賽季 | 窗口 | 總場數 | Over率 | 狀態 |
|------|------|--------|--------|------|
| 2024-2025 | 2024-09 to 2024-11 | 2 | 0.500 | SKIP（太少） |
| 2024-2025 | 2025-03 to 2025-05 | 37 | 0.432 | ✅ TRAINABLE |
| 2024-2025 | 2025-06 to 2025-08 | 30 | 0.633 | ✅ TRAINABLE |
| 2025-2026 | 2025-09 to 2025-11 | 31 | 0.451 | ✅ TRAINABLE |

---

## 模型配置

- **算法:** GradientBoostingClassifier
- **參數:** n_estimators=50, max_depth=2, learning_rate=0.05, random_state=42
- **閾值選擇:** 通過交叉驗證（CV）在訓練集上選擇
- **Train/Test Split:** 70/30（按時間順序）
- **驗證方法:** 5-fold Stratified CV on training set

---

## 每窗口結果

### Window 1: 2024-2025 Season / 2025-03 to 2025-05
| 指標 | 数值 |
|------|------|
| 訓練樣本 | 25 |
| 測試樣本 | 12 |
| Threshold (CV) | 0.59 |
| CV Accuracy | 0.600 |
| **Test Accuracy** | **0.333** |
| ROI | -40.83% |

### Window 2: 2024-2025 Season / 2025-06 to 2025-08
| 指標 | 数值 |
|------|------|
| 訓練樣本 | 21 |
| 測試樣本 | 9 |
| Threshold (CV) | 0.56 |
| CV Accuracy | 0.619 |
| **Test Accuracy** | **0.667** |
| ROI | +19.56% |

### Window 3: 2025-2026 Season / 2025-09 to 2025-11
| 指標 | 数值 |
|------|------|
| 訓練樣本 | 21 |
| 測試樣本 | 10 |
| Threshold (CV) | 0.38 |
| CV Accuracy | 0.667 |
| **Test Accuracy** | **0.300** |
| ROI | -46.40% |

---

## Overall 結果

| 指標 | 数值 |
|------|------|
| **Overall Test Accuracy** | **0.419 (41.9%)** |
| **Overall ROI** | **-25.10%** |
| Total Test Samples | 31 |

---

## 數據分析發現

### 市場效率
- 市場隱含OVER概率平均約 52-53%，與實際OVER率（50%）相近
- 市場赔率本身沒有顯示明顯的預測偏差

### 窗口特徵差異
- Window 2（2025-06 to 2025-08）Over率 63.3%，模型預測效果最好
- Window 1 和 Window 3 的Over率低於50%，但模型傾向預測OVER
- 市場赔率在低Over率窗口傾向高估OVER概率

### 模型局限性
1. **數據量不足**: 每窗口僅 30-37 場比賽，訓練樣本 21-25 場
2. **閾值過擬合**: 交叉驗證選擇的閾值在小樣本上不夠穩健
3. **市場效率**: 博彩公司的赔率已經很好地反映了真實概率
4. **窗口不穩定**: 不同窗口的最佳模型和閾值差異很大

---

## Runnable Script

預測腳本位置: `/root/.openclaw/workspace/projects/football-analysis/scripts/south_korea_wk_league_predict.py`

```bash
python south_korea_wk_league_predict.py <event_id>
```

---

## 模型文件

- 模型文件: `/root/.openclaw/workspace/projects/football-analysis/models/south_korea_wk_league_combined_model.pkl`
- 測試數據: `/root/.openclaw/workspace/projects/football-analysis/models/south_korea_wk_league_test_data.pkl`

---

## 結論

⚠️ **Test Accuracy 0.419，低於 70% 目標**

南韓女子職業聯賽的 Over/Under 預測面臨以下挑戰：
1. 比賽數據有限（僅100場）
2. 市場赔率高度有效，缺乏明顯的預測邊緣
3. 不同窗口的比賽特徵差異大，難以建立穩定模型
4. 小樣本導致模型訓練不穩健

建議：增加更多賽季的數據，或專注於特定窗口（如Window 2）進行更有針對性的分析。

---

*Bello! 以上係誠實嘅分析結果！🧸⚽*
