#!/usr/bin/env python3
"""
卡塔爾超級聯賽 (Qatar Stars League) Over/Under 預測腳本
用法: python qatar_predict.py <event_id>
"""

import sys
import pickle
import pandas as pd
import numpy as np
import pymysql
from datetime import datetime

def get_feature_columns():
    return [
        'over_odd', 'under_odd', 'over_under_cap',
        'win_home_odd', 'win_draw_odd', 'win_away_odd',
        'handicap_cap', 'handicap_home_odd', 'handicap_away_odd',
        'implied_over_prob', 'implied_under_prob', 'over_juice',
        'is_home_favorite', 'handicap_home_favorite',
        'home_avg_goals', 'away_avg_goals', 'home_avg_concede', 'away_avg_concede',
        'home_over_rate', 'away_over_rate',
        'expected_total_goals', 'goals_diff_from_cap'
    ]

def get_db_connection():
    return pymysql.connect(
        host='10.18.0.30',
        port=3306,
        user='root',
        password='QazWsxEdc$@3649',
        database='mslot',
        charset='utf8mb4'
    )

def fetch_event_features(event_id: str, historical_df: pd.DataFrame) -> dict:
    """Build features for a single event using historical data + latest odds"""
    connection = get_db_connection()
    
    query = """
    SELECT 
        e.event_id, e.start_time, e.home_id, e.away_id,
        ht.name AS home_team, at.name AS away_team,
        ou.over_odd, ou.over_under_cap, ou.under_odd,
        wo.home_odd AS win_home_odd, wo.draw_odd AS win_draw_odd, wo.away_odd AS win_away_odd,
        ho.home_cap AS handicap_cap, ho.home_odd AS handicap_home_odd, ho.away_odd AS handicap_away_odd
    FROM fb_event e
    JOIN fb_team ht ON e.home_id = ht.team_id
    JOIN fb_team at ON e.away_id = at.team_id
    LEFT JOIN (
        SELECT o1.* FROM fb_over_under_odd o1
        INNER JOIN (
            SELECT event_id, MAX(created_at) AS max_created
            FROM fb_over_under_odd GROUP BY event_id
        ) o2 ON o1.event_id = o2.event_id AND o1.created_at = o2.max_created
    ) ou ON e.event_id = ou.event_id
    LEFT JOIN (
        SELECT w1.* FROM fb_win_odd w1
        INNER JOIN (
            SELECT event_id, MAX(created_at) AS max_created
            FROM fb_win_odd GROUP BY event_id
        ) w2 ON w1.event_id = w2.event_id AND w1.created_at = w2.max_created
    ) wo ON e.event_id = wo.event_id
    LEFT JOIN (
        SELECT h1.* FROM fb_handicap_odd h1
        INNER JOIN (
            SELECT event_id, MAX(created_at) AS max_created
            FROM fb_handicap_odd GROUP BY event_id
        ) h2 ON h1.event_id = h2.event_id AND h1.created_at = h2.max_created
    ) ho ON e.event_id = ho.event_id
    WHERE e.event_id = %s
    """
    
    event_df = pd.read_sql(query, connection, params=(event_id,))
    connection.close()
    
    if len(event_df) == 0:
        return None
    
    row = event_df.iloc[0]
    
    # Compute historical features
    home_team = row['home_team']
    away_team = row['away_team']
    
    # Filter historical completed matches (before this event)
    past = historical_df[historical_df['start_time'] < row['start_time']]
    
    # Home team history
    home_matches = past[(past['home_team'] == home_team) | (past['away_team'] == home_team)]
    if len(home_matches) > 0:
        home_avg_goals = home_matches.apply(
            lambda r: r['home_ft_score'] if r['home_team'] == home_team else r['away_ft_score'], axis=1
        ).mean()
        home_avg_concede = home_matches.apply(
            lambda r: r['away_ft_score'] if r['home_team'] == home_team else r['home_ft_score'], axis=1
        ).mean()
        home_over_rate = home_matches.apply(
            lambda r: (r['total_goals'] > r['over_under_cap']), axis=1
        ).mean()
    else:
        home_avg_goals = 2.0
        home_avg_concede = 2.0
        home_over_rate = 0.5
    
    # Away team history
    away_matches = past[(past['home_team'] == away_team) | (past['away_team'] == away_team)]
    if len(away_matches) > 0:
        away_avg_goals = away_matches.apply(
            lambda r: r['away_ft_score'] if r['away_team'] == away_team else r['home_ft_score'], axis=1
        ).mean()
        away_avg_concede = away_matches.apply(
            lambda r: r['home_ft_score'] if r['away_team'] == away_team else r['away_ft_score'], axis=1
        ).mean()
        away_over_rate = away_matches.apply(
            lambda r: (r['total_goals'] > r['over_under_cap']), axis=1
        ).mean()
    else:
        away_avg_goals = 2.0
        away_avg_concede = 2.0
        away_over_rate = 0.5
    
    # Derived features
    implied_over_prob = 1 / row['over_odd'] if row['over_odd'] > 0 else 0.5
    implied_under_prob = 1 / row['under_odd'] if row['under_odd'] > 0 else 0.5
    over_juice = implied_over_prob + implied_under_prob - 1
    is_home_favorite = 1 if row['win_home_odd'] < row['win_away_odd'] else 0
    handicap_home_favorite = 1 if row['handicap_home_odd'] < row['handicap_away_odd'] else 0
    expected_total_goals = (home_avg_goals + away_avg_goals + home_avg_concede + away_avg_concede) / 2
    goals_diff_from_cap = expected_total_goals - row['over_under_cap']
    
    features = {
        'over_odd': row['over_odd'],
        'under_odd': row['under_odd'],
        'over_under_cap': row['over_under_cap'],
        'win_home_odd': row['win_home_odd'],
        'win_draw_odd': row['win_draw_odd'],
        'win_away_odd': row['win_away_odd'],
        'handicap_cap': row['handicap_cap'],
        'handicap_home_odd': row['handicap_home_odd'],
        'handicap_away_odd': row['handicap_away_odd'],
        'implied_over_prob': implied_over_prob,
        'implied_under_prob': implied_under_prob,
        'over_juice': over_juice,
        'is_home_favorite': is_home_favorite,
        'handicap_home_favorite': handicap_home_favorite,
        'home_avg_goals': home_avg_goals,
        'away_avg_goals': away_avg_goals,
        'home_avg_concede': home_avg_concede,
        'away_avg_concede': away_avg_concede,
        'home_over_rate': home_over_rate,
        'away_over_rate': away_over_rate,
        'expected_total_goals': expected_total_goals,
        'goals_diff_from_cap': goals_diff_from_cap
    }
    
    return features

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
            'model_info': str      # 模型描述
        }
    """
    # Load model
    with open('/root/.openclaw/workspace/projects/verified_models/models/qatar_combined_overunder.pkl', 'rb') as f:
        model_pkg = pickle.load(f)
    
    model = model_pkg['model']
    scaler = model_pkg['scaler']
    threshold = model_pkg['threshold']
    features_list = model_pkg['features']
    
    # Load historical data for feature computation
    historical_df = pd.read_csv('/root/.openclaw/workspace/projects/verified_models/data_qatar_enhanced.csv')
    historical_df['start_time'] = pd.to_datetime(historical_df['start_time'])
    
    # Get features for this event
    features = fetch_event_features(event_id, historical_df)
    if features is None:
        return {'error': f'Event {event_id} not found'}
    
    # Build feature vector in correct order
    X = pd.DataFrame([features])[features_list]
    
    # Scale (GB model)
    X_scaled = scaler.transform(X)
    
    # Predict probability
    prob_over = model.predict_proba(X_scaled)[0][1]
    
    # Make prediction
    if prob_over >= threshold:
        prediction = 'OVER'
    else:
        prediction = 'UNDER'
    
    return {
        'event_id': event_id,
        'prediction': prediction,
        'probability': round(float(prob_over), 4),
        'threshold': threshold,
        'features': {k: round(v, 4) if isinstance(v, float) else v for k, v in features.items()},
        'model_info': f"GradientBoostingClassifier (n_estimators=100, max_depth=3, threshold={threshold})"
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python qatar_predict.py <event_id>")
        sys.exit(1)
    result = predict(sys.argv[1])
    print(result)
