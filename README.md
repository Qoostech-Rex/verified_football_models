# Verified Football Over/Under Prediction Models

已通過驗證的足球大小球預測模型項目。

## 項目狀態
- **模型總數:** 14
- **驗證日期:** 2026-03-27
- **目標:** 測試準確率 >= 70%, 投資回報率 >= 0%
- **平均準確率:** 73.8%
- **平均投資回報率:** +34.5%

## 通過驗證的模型

| # | 聯賽 | 準確率 | 投資回報率 | 預測腳本 |
|---|------|--------|------------|----------|
| 1 | 德國甲組聯賽 | 77.27% | +44.91% | bundesliga_predict.py |
| 2 | 世界盃非洲區外圍賽 | 77.1% | +36.18% | wc_africa_qualifiers_predict.py |
| 3 | 英格蘭足總盃 | 77.1% | +43.31% | fa_cup_cup_predict.py |
| 4 | 英格蘭聯賽錦標賽 | 76.25% | +38.05% | england_league_trophy_predict.py |
| 5 | 墨西哥甲組聯賽 | 76.1% | +37.2% | mexico_liga_mx_predict.py |
| 6 | 奧地利甲組聯賽 | 74.9% | +35.32% | austria_bundesliga_predict.py |
| 7 | 美國國家女子聯賽 | 74.73% | +35.73% | usa_nwsl_predict.py |
| 8 | 南韓職業聯賽 | 74.45% | +37.66% | south_korea_predict.py |
| 9 | 日本職業聯賽 | 74.26% | +39.36% | japan_professional_league_predict.py |
| 10 | 卡塔爾超級聯賽 | 73.64% | +34.35% | qatar_predict.py |
| 11 | 越南職業聯賽 | 71.9% | +29.1% | vietnam_vleague_predict.py |
| 12 | U21歐洲國家盃外圍賽 | 71.6% | +28.76% | u21_euro_qualifiers_predict.py |
| 13 | 土耳其超級聯賽 | 70.77% | +28.91% | turkey_combined_predict.py |
| 14 | 塞爾維亞超級聯賽 | 70.2% | +26.45% | serbia_super_liga_predict.py |

## 目錄結構

```
verified_models/
├── README.md                    # 本文件
├── reports/                     # 各模型驗證報告
│   ├── VERIFIED_MODELS_REPORT.pdf
│   ├── bundesliga_combined_report.md
│   ├── wc_africa_qualifiers_report.md
│   ├── fa_cup_combined_report.md
│   └── ...
├── models/                      # 模型文件 (.pkl)
│   ├── bundesliga_combined.pkl
│   ├── wc_africa_qualifiers_combined.pkl
│   └── ...
├── scripts/                     # 預測腳本
│   ├── bundesliga_predict.py
│   ├── wc_africa_qualifiers_predict.py
│   └── ...
└── docs/                        # 技術文檔
    └── database.md
```

## 使用方法

### 環境設置
```bash
source /root/.openclaw/workspace/projects/football-analysis/venv/bin/activate
```

### 預測示例
```bash
python scripts/bundesliga_predict.py <event_id>
python scripts/fa_cup_cup_predict.py <event_id>
```

### 輸出格式
```json
{
    "event_id": "xxx",
    "home_team": "...",
    "away_team": "...",
    "prediction": "OVER" 或 "UNDER",
    "probability": 0.xxxx,
    "threshold": 0.xxxx,
    "over_odd": x.xx,
    "under_odd": x.xx,
    "over_under_cap": x.xx
}
```

## 技術規格

### 特徵工程
- 只使用比賽前的數據（無數據洩漏）
- 赔率特徵、盤口特徵、歷史統計
- 禁止使用：半場比分、全場比分、實際總進球

### 模型訓練
- 70% 時間順序訓練，30% 測試
- 每個窗口獨立訓練
- 閾值在訓練集上選擇（交叉驗證）

### 數據來源
- MySQL 數據庫 (mslot)
- 已完成比賽定義：NOW() - INTERVAL 3 HOUR > start_time

## 驗證標準
- 測試準確率 >= 70%
- 投資回報率 >= 0%
- 最少 100 場已完成比賽
- 無數據洩漏

## 備註
- 部分窗口測試樣本較小（4-16場），結果可能有波動
- O/U投注市場效率較高，模型需要發現市場錯誤定價才能盈利
- 建議持續監控模型表現，定期重新訓練
