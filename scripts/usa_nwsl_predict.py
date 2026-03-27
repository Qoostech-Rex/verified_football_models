#!/usr/bin/env python3
"""
USA NWSL Over/Under Combined 預測腳本
用法: python usa_nwsl_predict.py <event_id>
"""

import sys
import pickle
import numpy as np

MODEL_PATH = '/root/.openclaw/workspace/projects/football-analysis/models/usa_nwsl_combined.pkl'

# === USA NWSL TEAM ID MAPPING ===
TEAM_NAMES = {
    'portland_thorns': '波特蘭荊棘女足',
    'chicago_redstars': '芝加哥紅星女足',
    'nc_courage': '北卡羅勇氣女足',
    'bay_fc': '海灣FC女足',
    'utah_royals': '猶他皇家女足',
    'san_diego_wavec': '聖地牙哥海浪女足',
    'seattle_reign': '西雅圖王朝女足',
    'kansas_city_current': '肯薩斯城流動女足',
    'washingtonSpirit': '華盛頓精神女足',
    'angel_city': '天使城女足',
    'houston_dash': '侯斯頓達斯女足',
    'nj_ny Gotham': 'NJ/NY天蔔女足',
    'orlando_pride': '奧蘭多榮耀女足',
    'miami_flag': '邁阿密FLAG女足',
    'bay_fc_womens': '灣區FC女足',
    'racing_louisville': '路易斯維爾競技女足',
    'gotham': '天蔔女足',
    'longevity': '長命百歲女足',
}

def load_model():
    with open(MODEL_PATH, 'rb') as f:
        return pickle.load(f)

def get_season_window(start_time):
    """Determine which season/window this event belongs to"""
    from datetime import datetime
    if isinstance(start_time, str):
        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    elif hasattr(start_time, 'year'):
        dt = start_time
    else:
        dt = start_time
    
    year, month = dt.year, dt.month
    if month >= 3 and month <= 10:
        season = year
    else:
        season = year - 1
    if 3 <= month <= 5:
        window = 1
    elif 6 <= month <= 8:
        window = 2
    else:
        window = 3
    return f"{season}-{season+1} W{window}"

def predict(event_id: str, db_params: dict = None) -> dict:
    """
    預測指定比賽的 Over/Under 結果
    
    Args:
        event_id: 比賽 ID
        db_params: 可選，數據庫連接參數
        
    Returns:
        dict: {
            'event_id': str,
            'prediction': 'OVER' or 'UNDER',
            'probability': float,  # OVER 的概率
            'threshold': float,     # 使用的 threshold
            'features': dict,       # 使用的特征值
            'model_info': str       # 模型描述
        }
    """
    import pymysql
    
    if db_params is None:
        db_params = {
            'host': '10.18.0.30', 'port': 3306, 'user': 'root',
            'password': 'QazWsxEdc$@3649', 'database': 'mslot', 'charset': 'utf8mb4'
        }
    
    # Load model
    model_data = load_model()
    all_model_info = model_data['all_model_info']
    
    # Fetch event data
    conn = pymysql.connect(**db_params)
    query = """
    SELECT 
        e.event_id, e.start_time,
        ht.name AS home_team, at.name AS away_team,
        e.home_id, e.away_id,
        ou.over_odd, ou.over_under_cap, ou.under_odd,
        wo.home_odd AS win_home_odd, wo.draw_odd AS win_draw_odd, wo.away_odd AS win_away_odd,
        ho.home_cap AS handicap_cap,
        ho.home_odd AS handicap_home_odd, ho.away_odd AS handicap_away_odd
    FROM fb_event e
    JOIN fb_team ht ON e.home_id = ht.team_id
    JOIN fb_team at ON e.away_id = at.team_id
    LEFT JOIN (
        SELECT o1.* FROM fb_over_under_odd o1
        INNER JOIN (SELECT event_id, MAX(created_at) AS max_created FROM fb_over_under_odd GROUP BY event_id) o2
        ON o1.event_id = o2.event_id AND o1.created_at = o2.max_created
    ) ou ON e.event_id = ou.event_id
    LEFT JOIN (
        SELECT w1.* FROM fb_win_odd w1
        INNER JOIN (SELECT event_id, MAX(created_at) AS max_created FROM fb_win_odd GROUP BY event_id) w2
        ON w1.event_id = w2.event_id AND w1.created_at = w2.max_created
    ) wo ON e.event_id = wo.event_id
    LEFT JOIN (
        SELECT h1.* FROM fb_handicap_odd h1
        INNER JOIN (SELECT event_id, MAX(created_at) AS max_created FROM fb_handicap_odd GROUP BY event_id) h2
        ON h1.event_id = h2.event_id AND h1.created_at = h2.max_created
    ) ho ON e.event_id = ho.event_id
    WHERE e.event_id = %s
    """
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute(query, (event_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return {'error': f'Event {event_id} not found'}
    
    # Determine season/window
    wl = get_season_window(row['start_time'])
    
    # Find best available model (try exact match, then closest)
    if wl in all_model_info:
        model_info = all_model_info[wl]
    else:
        # Fallback: use any available model
        available_wls = list(all_model_info.keys())
        model_info = all_model_info[available_wls[-1]]
        wl = available_wls[-1]
    
    # Build features
    implied_over = 1 / row['over_odd']
    implied_under = 1 / row['under_odd']
    over_juice = implied_over + implied_under
    norm_over = implied_over / over_juice
    norm_under = implied_under / over_juice
    
    implied_home = 1 / row['win_home_odd']
    implied_draw = 1 / row['win_draw_odd']
    implied_away = 1 / row['win_away_odd']
    twj = implied_home + implied_draw + implied_away
    norm_home = implied_home / twj
    
    home_fav = 1 if row['win_home_odd'] < row['win_away_odd'] else 0
    fav_prob = max(norm_home, 1 - norm_home)
    
    hhi = 1 / row['handicap_home_odd']
    hai = 1 / row['handicap_away_odd']
    thj = hhi + hai
    norm_hh = hhi / thj
    
    cap_bin = {2.0: 0, 2.25: 1, 2.5: 2, 2.75: 3, 3.0: 4}.get(row['over_under_cap'], 2)
    
    features = {}
    fc = model_info['feature_cols']
    
    if 'norm_over_prob' in fc:
        features['norm_over_prob'] = norm_over
    if 'norm_under_prob' in fc:
        features['norm_under_prob'] = norm_under
    if 'over_under_cap' in fc:
        features['over_under_cap'] = row['over_under_cap']
    if 'odds_ratio' in fc:
        features['odds_ratio'] = row['over_odd'] / row['under_odd']
    if 'over_odd_log' in fc:
        features['over_odd_log'] = np.log(row['over_odd'])
    if 'under_odd_log' in fc:
        features['under_odd_log'] = np.log(row['under_odd'])
    if 'home_favorite' in fc:
        features['home_favorite'] = home_fav
    if 'favorite_prob' in fc:
        features['favorite_prob'] = fav_prob
    if 'norm_home_prob' in fc:
        features['norm_home_prob'] = norm_home
    if 'norm_handicap_home_prob' in fc:
        features['norm_handicap_home_prob'] = norm_hh
    if 'market_over_lean' in fc:
        features['market_over_lean'] = (norm_over - 0.5) * 2
    if 'cap_bin' in fc:
        features['cap_bin'] = cap_bin
    if 'cap_per_over_odd' in fc:
        features['cap_per_over_odd'] = row['over_under_cap'] / row['over_odd']
    if 'cap_per_under_odd' in fc:
        features['cap_per_under_odd'] = row['over_under_cap'] / row['under_odd']
    if 'h_avg_scored' in fc:
        features['h_avg_scored'] = 2.5  # placeholder - needs historical data
    if 'h_avg_conceded' in fc:
        features['h_avg_conceded'] = 2.5
    if 'a_avg_scored' in fc:
        features['a_avg_scored'] = 2.5
    if 'a_avg_conceded' in fc:
        features['a_avg_conceded'] = 2.5
    if 'h_over_rate' in fc:
        features['h_over_rate'] = 0.5
    if 'a_over_rate' in fc:
        features['a_over_rate'] = 0.5
    if 'expected_total' in fc:
        features['expected_total'] = 2.5
    if 'expected_vs_cap' in fc:
        features['expected_vs_cap'] = 2.5 - row['over_under_cap']
    if 'h_games' in fc:
        features['h_games'] = 5
    if 'a_games' in fc:
        features['a_games'] = 5
    
    # Build feature vector
    X = np.array([[features.get(c, 0.5) for c in fc]])
    X_scaled = model_info['scaler'].transform(X)
    
    # Predict
    prob_over = model_info['model'].predict_proba(X_scaled)[0, 1]
    threshold = model_info['threshold']
    prediction = 'OVER' if prob_over >= threshold else 'UNDER'
    
    return {
        'event_id': event_id,
        'home_team': row['home_team'],
        'away_team': row['away_team'],
        'start_time': str(row['start_time']),
        'prediction': prediction,
        'probability': float(prob_over),
        'threshold': float(threshold),
        'features': features,
        'model_info': f"Model: Logistic Regression, Window: {wl}, Feature set: {model_info['feature_cols'][:3]}...",
        'cap': row['over_under_cap'],
        'over_odd': row['over_odd'],
        'under_odd': row['under_odd'],
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python usa_nwsl_predict.py <event_id>")
        sys.exit(1)
    result = predict(sys.argv[1])
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
