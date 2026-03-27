# Football Analysis Database Documentation

## MySQL 連線方式

### 連線參數
| 參數 | 值 |
|------|-----|
| Host | `10.18.0.30` |
| Port | `3306` |
| Database | `mslot` |
| User | `root` |
| Password | `QazWsxEdc$@3649` |

### 連線範例

```bash
mysql -h 10.18.0.30 -u root -p'QazWsxEdc$@3649' --skip-ssl mslot
```

### Python 連線範例
```python
import pymysql

connection = pymysql.connect(
    host='10.18.0.30',
    port=3306,
    user='root',
    password='QazWsxEdc$@3649',
    database='mslot',
    charset='utf8mb4'
)
```

---

## 資料表架構

### 1. fb_event (賽事資料)
| 欄位 | 類型 | 說明 |
|------|------|------|
| `event_id` | varchar(255) | Primary Key，比賽唯一識別碼 |
| `event_type_id` | varchar(255) | 比賽類型 (FK → fb_event_type) |
| `start_time` | datetime | 比賽開始時間 |
| `home_id` | varchar(255) | 主隊 ID (FK → fb_team) |
| `away_id` | varchar(255) | 客隊 ID (FK → fb_team) |
| `has_bet_in_run` | tinyint(1) | 是否滾球投注 |
| `home_ht_score` | int | 主隊半場比分 |
| `away_ht_score` | int | 客隊半場比分 |
| `home_ft_score` | int | 主隊全場比分 |
| `away_ft_score` | int | 客隊全場比分 |
| `created_at` | datetime | 建立時間 |
| `updated_at` | datetime | 更新時間 |

---

### 2. fb_team (球隊資料)
| 欄位 | 類型 | 說明 |
|------|------|------|
| `team_id` | varchar(255) | Primary Key，球隊唯一識別碼 |
| `name` | varchar(255) | 球隊名稱 |
| `model_label` | int | 模型標籤 (用於AI分析) |
| `created_at` | datetime | 建立時間 |
| `updated_at` | datetime | 更新時間 |

---

### 3. fb_event_type (賽事類型)
| 欄位 | 類型 | 說明 |
|------|------|------|
| `event_type_id` | varchar(255) | Primary Key，賽事類型唯一識別碼 |
| `name` | varchar(255) | 賽事類型名稱 (如：英超、亞冠盃等) |
| `model_label` | int | 模型標籤 |
| `created_at` | datetime | 建立時間 |
| `updated_at` | datetime | 更新時間 |

---

### 4. fb_win_odd (勝平負投注)
| 欄位 | 類型 | 說明 |
|------|------|------|
| `win_odd_id` | varchar(255) | Primary Key |
| `event_id` | varchar(255) | 比賽 ID (FK → fb_event) |
| `home_odd` | float | 主勝賠率 |
| `draw_odd` | float | 和局賠率 |
| `away_odd` | float | 客勝賠率 |
| `created_at` | datetime | 建立時間 |
| `updated_at` | datetime | 更新時間 |

---

### 5. fb_over_under_odd (大小球投注)
| 欄位 | 類型 | 說明 |
|------|------|------|
| `over_under_odd_id` | varchar(255) | Primary Key |
| `event_id` | varchar(255) | 比賽 ID (FK → fb_event) |
| `over_odd` | float | 大球赔率 |
| `over_under_cap` | float | 大小球盤口 (如 2.5, 3.0) |
| `under_odd` | float | 小球赔率 |
| `created_at` | datetime | 建立時間 |
| `updated_at` | datetime | 更新時間 |

---

### 6. fb_handicap_odd (讓球投注)
| 欄位 | 類型 | 說明 |
|------|------|------|
| `handicap_odd_id` | varchar(255) | Primary Key |
| `event_id` | varchar(255) | 比賽 ID (FK → fb_event) |
| `home_odd` | float | 主隊讓球赔率 |
| `home_cap` | float | 主隊讓球盤口 |
| `away_odd` | float | 客隊受讓赔率 |
| `away_cap` | float | 客隊受讓盤口 |
| `created_at` | datetime | 建立時間 |
| `updated_at` | datetime | 更新時間 |

---

## 資料表關聯圖

```
fb_event
├── event_type_id → fb_event_type.event_type_id
├── home_id → fb_team.team_id
└── away_id → fb_team.team_id

fb_event ─┬─→ fb_win_odd (event_id)
          ├─→ fb_over_under_odd (event_id)
          └─→ fb_handicap_odd (event_id)
```

---

## 重要：取得最新賠率

**⚠️ 注意：** 所有賠率表 (`fb_win_odd`, `fb_over_under_odd`, `fb_handicap_odd`) 都會記錄變化歷史，每個 `event_id` 可能有多筆記錄。

**取最新赔率方法：** 根據 `created_at` 取每個 event_id 最近的一筆記錄。

---

## 重要：赔率記錄 vs 比賽場數

**⚠️ 關鍵澄清：**

一場比賽可能有多個赔率記錄（因為赔率隨時間變化）。

- `fb_over_under_odd` 入面既記錄數 ≠ 比賽場數！
- 錯誤：`SELECT COUNT(*) FROM fb_over_under_odd` - 呢個係赔率記錄數
- 正確：`SELECT COUNT(DISTINCT event_id) FROM fb_over_under_odd` - 呢個係真正有赔率既比賽場數

**訓練模型前，必須確認有 ≥100 場比賽有赔率！**

---

## 重要：完場比賽定義

**完場比賽條件：**
```sql
NOW() - INTERVAL 3 HOUR > e.start_time
```
即係 `now - start_time > 3 hours` 先可以視為完場比賽。

**用途：** 只用完場比賽嚟 training 模型，確保比賽結果已經確定。

---

## 重要：模型訓練數據要求

**最低數據量：** 每個聯賽至少需要 **100 場完場比賽** 先可以訓練模型。

- 如果完場比賽 **＜ 100 場** → 直接標記為 `failed`（數據不足）
- 如果完場比賽 **≥ 100 場** → 可以嘗試訓練模型，目標 ≥70% 準確率

---

## 常用查詢範例

### 取得所有賽事及其最新賠率
```sql
SELECT 
    e.event_id,
    e.start_time,
    ht.name AS home_team,
    at.name AS away_team,
    wo.home_odd,
    wo.draw_odd,
    wo.away_odd,
    ou.over_odd,
    ou.over_under_cap,
    ou.under_odd,
    ho.home_cap,
    ho.home_odd AS home_handicap_odd,
    ho.away_odd AS away_handicap_odd
FROM fb_event e
LEFT JOIN fb_team ht ON e.home_id = ht.team_id
LEFT JOIN fb_team at ON e.away_id = at.team_id
-- 最新 win_odd (根據 created_at 取最新)
LEFT JOIN (
    SELECT w1.* FROM fb_win_odd w1
    INNER JOIN (
        SELECT event_id, MAX(created_at) AS max_created
        FROM fb_win_odd GROUP BY event_id
    ) w2 ON w1.event_id = w2.event_id AND w1.created_at = w2.max_created
) wo ON e.event_id = wo.event_id
-- 最新 over_under_odd
LEFT JOIN (
    SELECT o1.* FROM fb_over_under_odd o1
    INNER JOIN (
        SELECT event_id, MAX(created_at) AS max_created
        FROM fb_over_under_odd GROUP BY event_id
    ) o2 ON o1.event_id = o2.event_id AND o1.created_at = o2.max_created
) ou ON e.event_id = ou.event_id
-- 最新 handicap_odd
LEFT JOIN (
    SELECT h1.* FROM fb_handicap_odd h1
    INNER JOIN (
        SELECT event_id, MAX(created_at) AS max_created
        FROM fb_handicap_odd GROUP BY event_id
    ) h2 ON h1.event_id = h2.event_id AND h1.created_at = h2.max_created
) ho ON e.event_id = ho.event_id
ORDER BY e.start_time DESC;
```

### 取得特定球隊的所有比賽
```sql
SELECT 
    e.event_id,
    e.start_time,
    ht.name AS home_team,
    at.name AS away_team,
    e.home_ft_score,
    e.away_ft_score
FROM fb_event e
JOIN fb_team ht ON e.home_id = ht.team_id
JOIN fb_team at ON e.away_id = at.team_id
WHERE ht.name = 'Manchester United' OR at.name = 'Manchester United'
ORDER BY e.start_time DESC;
```
