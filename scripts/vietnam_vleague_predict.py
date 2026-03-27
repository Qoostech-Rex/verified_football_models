#!/usr/bin/env python3
"""
越南職業聯賽 (Vietnam V-League) Over/Under 預測腳本
用法: python vietnam_vleague_predict.py <event_id>
"""

import sys
import pickle
import pandas as pd
import numpy as np

MODEL_PATH = '/root/.openclaw/workspace/projects/football-analysis/models/vietnam_vleague_combined.pkl'
DATA_PATH = '/root/.openclaw/workspace/projects/football-analysis/models/vietnam_vleague_data.pkl'

def load_model():
    with open(MODEL_PATH, 'rb') as f:
        data = pickle.load(f)
    return data

def predict(event_id: str) -> dict:
    """
    預測指定比賽的 Over/Under 結果
    
    Args:
        event_id: 比賽 ID
        
    Returns:
        dict: {
            'event_id': str,
            'prediction': 'OVER' or 'UNDER',
            'probability': float,  # OVER 的概率
            'threshold': float,    # 使用的 threshold
            'features': dict,      # 使用的特征值
            'model_info': str,     # 模型描述
            'season_window': str   # 所屬窗口
        }
    """
    model_data = load_model()
    models_info = model_data['models_info']
    
    # Load historical data for feature computation
    df_hist = pd.read_pickle(DATA_PATH)
    
    # For this event, we need to fetch fresh data from DB
    import pymysql
    conn = pymysql.connect(
        host='10.18.0.30', port=3306, user='root',
        password='QazWsxEdc$@3649', database='mslot', charset='utf8mb4'
    )
    
    query = f"""
    SELECT 
        e.event_id, e.start_time, ht.name AS home_team, at.name AS away_team,
        e.home_ft_score, e.away_ft_score,
        ou.over_odd, ou.over_under_cap, ou.under_odd,
        wo.home_odd, wo.draw_odd, wo.away_odd,
        ho.home_cap, ho.home_odd AS home_handicap_odd, ho.away_odd AS away_handicap_odd
    FROM fb_event e
    JOIN fb_team ht ON e.home_id = ht.team_id
    JOIN fb_team at ON e.away_id = at.team_id
    LEFT JOIN (SELECT o1.* FROM fb_over_under_odd o1 INNER JOIN (SELECT event_id, MAX(created_at) AS max_created FROM fb_over_under_odd GROUP BY event_id) o2 ON o1.event_id = o2.event_id AND o1.created_at = o2.max_created) ou ON e.event_id = ou.event_id
    LEFT JOIN (SELECT w1.* FROM fb_win_odd w1 INNER JOIN (SELECT event_id, MAX(created_at) AS max_created FROM fb_win_odd GROUP BY event_id) w2 ON w1.event_id = w2.event_id AND w1.created_at = w2.max_created) wo ON e.event_id = wo.event_id
    LEFT JOIN (SELECT h1.* FROM fb_handicap_odd h1 INNER JOIN (SELECT event_id, MAX(created_at) AS max_created FROM fb_handicap_odd GROUP BY event_id) h2 ON h1.event_id = h2.event_id AND h1.created_at = h2.max_created) ho ON e.event_id = ho.event_id
    WHERE e.event_id = '{event_id}'
    """
    
    event_df = pd.read_sql(query, conn)
    conn.close()
    
    if len(event_df) == 0:
        return {'error': f'No event found with id: {event_id}'}
    
    event = event_df.iloc[0]
    
    # Determine season_window
    start_time = pd.to_datetime(event['start_time'])
    year = start_time.year
    month = start_time.month
    
    if month >= 9:
        season = f"{year}-{year+1}"
    else:
        season = f"{year-1}-{year}"
    
    if month in [9, 10, 11]:
        window = 'W1 (Sep-Nov)'
    elif month in [12, 1, 2]:
        window = 'W2 (Dec-Feb)'
    elif month in [3, 4, 5]:
        window = 'W3 (Mar-May)'
    else:
        window = 'W4 (Jun-Aug)'
    
    season_window = f"{season} / {window}"
    
    # Get historical data for feature computation (only matches before this one)
    past_matches = df_hist[df_hist['start_time'] < start_time].copy()
    
    # Compute features
    home_team = event['home_team']
    away_team = event['away_team']
    
    # Historical averages
    home_past = past_matches[(past_matches['home_team'] == home_team) | (past_matches['away_team'] == home_team)]
    away_past = past_matches[(past_matches['home_team'] == away_team) | (past_matches['away_team'] == away_team)]
    
    home_scored = list(home_past[home_past['home_team'] == home_team]['home_ft_score']) + \
                  list(home_past[home_past['away_team'] == home_team]['away_ft_score'])
    home_conceded = list(home_past[home_past['home_team'] == home_team]['away_ft_score']) + \
                    list(home_past[home_past['away_team'] == home_team]['home_ft_score'])
    away_scored = list(away_past[away_past['home_team'] == away_team]['home_ft_score']) + \
                  list(away_past[away_past['away_team'] == away_team]['away_ft_score'])
    away_conceded = list(away_past[away_past['home_team'] == away_team]['away_ft_score']) + \
                    list(away_past[away_past['away_team'] == away_team]['home_ft_score'])
    
    home_avg_scored = np.mean(home_scored) if home_scored else 1.25
    home_avg_conceded = np.mean(home_conceded) if home_conceded else 1.25
    away_avg_scored = np.mean(away_scored) if away_scored else 1.25
    away_avg_conceded = np.mean(away_conceded) if away_conceded else 1.25
    
    expected_goals = (home_avg_scored + away_avg_conceded + away_avg_scored + home_avg_conceded) / 2
    attack_vs_defense = (home_avg_scored - away_avg_conceded) - (away_avg_scored - home_avg_conceded)
    
    implied_prob_over = 1 / event['over_odd']
    implied_prob_under = 1 / event['under_odd']
    implied_prob_home = 1 / event['home_odd']
    implied_prob_draw = 1 / event['draw_odd']
    implied_prob_away = 1 / event['away_odd']
    overround = implied_prob_over + implied_prob_under
    norm_prob_over = implied_prob_over / overround
    market_bias = implied_prob_over - implied_prob_under
    handicap_spread = abs(event['home_cap']) if pd.notna(event['home_cap']) else 0
    book_margin = 1 - (1/event['home_odd'] + 1/event['draw_odd'] + 1/event['away_odd'])
    cap_minus_expected = event['over_under_cap'] - expected_goals
    
    feature_values = {
        'implied_prob_over': implied_prob_over,
        'norm_prob_over': norm_prob_over,
        'market_bias': market_bias,
        'over_under_cap': event['over_under_cap'],
        'handicap_spread': handicap_spread,
        'implied_prob_home': implied_prob_home,
        'implied_prob_draw': implied_prob_draw,
        'implied_prob_away': implied_prob_away,
        'home_avg_scored': home_avg_scored,
        'home_avg_conceded': home_avg_conceded,
        'away_avg_scored': away_avg_scored,
        'away_avg_conceded': away_avg_conceded,
        'expected_goals': expected_goals,
        'attack_vs_defense': attack_vs_defense,
        'book_margin': book_margin,
        'cap_minus_expected': cap_minus_expected
    }
    
    feature_cols = model_data['feature_cols']
    
    # Get model for this season_window
    if season_window in models_info:
        mi = models_info[season_window]
        model = mi['model']
        scaler = mi['scaler']
        threshold = mi['threshold']
    else:
        # Fallback to first available model
        season_window = list(models_info.keys())[0]
        mi = models_info[season_window]
        model = mi['model']
        scaler = mi['scaler']
        threshold = mi['threshold']
    
    X = np.array([[feature_values[c] for c in feature_cols]])
    X_scaled = scaler.transform(X)
    
    proba_over = model.predict_proba(X_scaled)[0][1]
    prediction = 'OVER' if proba_over >= threshold else 'UNDER'
    
    return {
        'event_id': event_id,
        'prediction': prediction,
        'probability': round(proba_over, 3),
        'threshold': threshold,
        'features': {k: round(v, 3) if isinstance(v, float) else v for k, v in feature_values.items()},
        'model_info': f"{mi['best_model'] if 'best_model' in mi else 'LR'}/GB",
        'season_window': season_window,
        'over_odd': event['over_odd'],
        'under_odd': event['under_odd'],
        'over_under_cap': event['over_under_cap'],
        'home_team': home_team,
        'away_team': away_team,
        'start_time': str(start_time)
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python vietnam_vleague_predict.py <event_id>")
        sys.exit(1)
    result = predict(sys.argv[1])
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
