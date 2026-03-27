# World Cup Africa Qualifiers - Over/Under 預測報告

## 任務資料
- **Task ID:** `72aede56718b075bbfcedbd9dd33388a`
- **Event Type ID:** `e5bd2126796b4cc296caf3199ebd39f8`
- **Model:** Combined (Over + Under)
- **分析日期:** 2025-03-27

---

## 📊 數據概覽

| 項目 | 數值 |
|------|------|
| 總完場比賽 | 152 場 |
| 訓練集 | 106 場 (70%) |
| 測試集 | 46 場 (30%) |
| 總窗口數 | 2 個 |

---

## 🔍 特徵工程 (No Data Leakage)

**使用的特徵（僅限賽前數據）：**
- `over_odd` - 大球赔率
- `under_odd` - 小球赔率
- `over_under_cap` - 大小球盤口
- `cap_centered` - 盤口偏離2.5的值
- `implied_over_prob` - 1/over_odd（市場隱含OVER概率）
- `implied_under_prob` - 1/under_odd（市場隱含UNDER概率）
- `odds_spread` - over_odd - under_odd
- `over_under_ratio` - over_odd / under_odd
- `home_odd`, `draw_odd`, `away_odd` - 1X2主客和赔率
- `home_win_prob`, `draw_prob`, `away_win_prob` - 1X2隱含概率
- `home_away_diff` - 主勝概率 - 客勝概率
- `home_cap` - 讓球盤口
- `home_cap_abs` - 讓球盤口絕對值
- `home_handicap_odd`, `away_handicap_odd` - 讓球盘赔率

**❌ 未使用的特徵（Data Leakage）：**
- `home_ht_score`, `away_ht_score`, `ht_total_goals` - 半場比分
- `home_ft_score`, `away_ft_score`, `total_goals` - 實際比分

---

## 📅 窗口分析結果

### Window 1: 2024-2025 Season / 2025-03 to 2025-05
| 指標 | 數值 |
|------|------|
| 比賽場數 | 49 場 |
| 訓練集 | 34 場 (70%) |
| 測試集 | 15 場 (30%) |
| 訓練集 OVER 比率 | 50.0% |
| 測試集 OVER 比率 | 46.7% |
| **Test Accuracy** | **0.800 (80.0%)** ✅ |
| **ROI** | **38.93%** ✅ |
| Threshold | 0.33 |
| Train CV Accuracy | 0.618 |
| Top Features | cap_centered, draw_odd, home_cap_abs |
| Confusion Matrix | TN=6, FP=2, FN=1, TP=6 |

### Window 2: 2025-2026 Season / 2025-09 to 2025-11
| 指標 | 數值 |
|------|------|
| 比賽場數 | 103 場 |
| 訓練集 | 72 場 (70%) |
| 測試集 | 31 場 (30%) |
| 訓練集 OVER 比率 | 43.1% |
| 測試集 OVER 比率 | 48.4% |
| **Test Accuracy** | **0.742 (74.2%)** ✅ |
| **ROI** | **33.42%** ✅ |
| Threshold | 0.25 |
| Train CV Accuracy | 0.542 |
| Top Features | home_cap_abs, draw_odd, away_handicap_odd |
| Confusion Matrix | TN=11, FP=5, FN=3, TP=12 |

---

## 📈 Overall 結果

| 指標 | 數值 |
|------|------|
| **平均 Test Accuracy** | **0.771 (77.1%)** ✅ |
| **平均 ROI** | **36.18%** ✅ |
| Window 1 Accuracy | 0.800 |
| Window 2 Accuracy | 0.742 |
| Window 1 ROI | 38.93% |
| Window 2 ROI | 33.42% |

---

## 🤖 模型說明

### 模型架構
- **算法:** Gradient Boosting Classifier
- **參數:** n_estimators=100, max_depth=3, random_state=42
- **標準化:** StandardScaler

### Threshold 選擇方法
- 使用 **5-Fold Stratified Cross-Validation** 在訓練集上搜索最佳 threshold
- 搜索範圍: 0.25 to 0.75，步長 0.02
- **Threshold 在訓練集上選擇，不在測試集上優化！**

### 預測邏輯
```
probability = model.predict_proba(X)[:, 1]  # OVER probability
prediction = 'OVER' if probability >= threshold else 'UNDER'
```

### ROI 計算
- 每場投注 100 元
- OVER 贏 → +100 × (over_odd - 1)
- UNDER 贏 → +100 × (under_odd - 1)
- 輸 → -100 元
- ROI = (總賺蝕 / 總投注) × 100%

---

## 📁 輸出文件

| 文件 | 位置 |
|------|------|
| 模型 Pickle | `/root/.openclaw/workspace/projects/football-analysis/models/wc_africa_qualifiers.pkl` |
| 預測腳本 | `/root/.openclaw/workspace/projects/football-analysis/scripts/wc_africa_qualifiers_predict.py` |
| 本報告 | `/root/.openclaw/workspace/projects/football-analysis/reports/wc_africa_qualifiers_report.md` |

---

## ✅ 驗證清單

- [x] 完場比賽 ≥ 100 場（152場）
- [x] 每個窗口獨立做 Train/Test Split (70/30)
- [x] Threshold 在訓練集上選擇
- [x] 沒有使用半場/實際比分（No Data Leakage）
- [x] 每個窗口 Test Accuracy ≥ 70%
- [x] ROI > 0 所有窗口
- [x] 報告數據與 pickle 文件一致
- [x] 使用 venv 環境

---

## 🧪 預測腳本用法

```bash
source /root/.openclaw/workspace/projects/football-analysis/venv/bin/activate
python /root/.openclaw/workspace/projects/football-analysis/scripts/wc_africa_qualifiers_predict.py <event_id>
```

**範例輸出:**
```python
{
    'event_id': '844221',
    'prediction': 'UNDER',
    'probability': 0.187,
    'threshold': 0.25,
    'home_team': '中非共和國',
    'away_team': '馬達加斯加',
    'over_under_cap': 2.25,
    'over_odd': 1.9,
    'under_odd': 1.7
}
```

---

*Bello! 分析完成！⚽🧸*
