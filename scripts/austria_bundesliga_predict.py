#!/usr/bin/env python3
"""
Austria Bundesliga Over/Under 預測腳本
用法: python austria_bundesliga_predict.py <event_id>
"""

import sys
import os
import pickle
import pymysql
import pandas as pd
import numpy as np

WORK_DIR = '/root/.openclaw/workspace/projects/football-analysis/'
MODEL_DIR = os.path.join(WORK_DIR, 'models/')

EVENT_TYPE_ID = '0ffdf60cd8d84b75a91b45db09c32370'
LEAGUE_NAME = 'Austria Bundesliga'

def load_model_for_event(window_label):
    """Load the model pickle file for the given window."""
    safe = window_label.replace('-', '_').replace(' ', '_')
    filepath = os.path.join(MODEL_DIR, f'austria_bundesliga_ou_{safe}.pkl')
    if not os.path.exists(filepath):
        return None, f"Model file not found: {filepath}"
    with open(filepath, 'rb') as f:
        return pickle.load(f), None

def get_event_features(event_id, conn):
    """Fetch event data and compute features for prediction."""
    query = """
    SELECT 
        e.event_id,
        e.start_time,
        ht.name AS home_team,
        at.name AS away_team,
        e.home_ft_score,
        e.away_ft_score,
        ou.over_odd,
        ou.over_under_cap,
        ou.under_odd,
        wo.home_odd,
        wo.draw_odd,
        wo.away_odd,
        ho.home_cap,
        ho.away_cap,
        ho.home_odd AS home_handicap_odd,
        ho.away_odd AS away_handicap_odd
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
    df = pd.read_sql(query, conn, params=(event_id,))
    if len(df) == 0:
        return None
    return df.iloc[0]

def compute_features(row):
    """Compute features from raw event data (same as training)."""
    feats = {}
    
    # Implied probabilities
    feats['implied_over_prob'] = 1.0 / row['over_odd']
    feats['implied_under_prob'] = 1.0 / row['under_odd']
    prob_sum_ou = feats['implied_over_prob'] + feats['implied_under_prob']
    feats['implied_over_prob_norm'] = feats['implied_over_prob'] / prob_sum_ou
    feats['implied_under_prob_norm'] = feats['implied_under_prob'] / prob_sum_ou
    
    feats['implied_home_prob'] = 1.0 / row['home_odd']
    feats['implied_draw_prob'] = 1.0 / row['draw_odd']
    feats['implied_away_prob'] = 1.0 / row['away_odd']
    prob_sum_3way = feats['implied_home_prob'] + feats['implied_draw_prob'] + feats['implied_away_prob']
    feats['implied_home_prob_norm'] = feats['implied_home_prob'] / prob_sum_3way
    feats['implied_away_prob_norm'] = feats['implied_away_prob'] / prob_sum_3way
    
    feats['odds_ratio'] = row['over_odd'] / row['under_odd']
    feats['over_under_diff'] = row['under_odd'] - row['over_odd']
    feats['market_ou_vig'] = prob_sum_ou - 1.0
    feats['market_3way_vig'] = prob_sum_3way - 1.0
    feats['handicap_spread'] = row['home_cap'] - row['away_cap']
    feats['cap_centered'] = row['over_under_cap'] - 2.5
    feats['market_over_lean'] = feats['implied_over_prob_norm'] - 0.5
    
    # Cap dummies
    for cap_val in [2.0, 2.25, 2.5, 2.75, 3.0, 3.25]:
        feats[f'cap_{str(cap_val).replace(".", "_")}'] = 1.0 if row['over_under_cap'] == cap_val else 0.0
    
    # Historical (use only the raw over_under_cap)
    feats['over_under_cap'] = row['over_under_cap']
    feats['over_odd'] = row['over_odd']
    feats['under_odd'] = row['under_odd']
    feats['home_odd'] = row['home_odd']
    feats['draw_odd'] = row['draw_odd']
    feats['away_odd'] = row['away_odd']
    feats['home_handicap_odd'] = row['home_handicap_odd']
    feats['away_handicap_odd'] = row['away_handicap_odd']
    feats['home_cap'] = row['home_cap']
    feats['away_cap'] = row['away_cap']
    
    return feats

def get_window_for_event(start_time):
    """Determine the window label for an event's start_time."""
    from datetime import datetime
    dt = start_time if isinstance(start_time, datetime) else pd.to_datetime(start_time)
    if dt.month >= 8:
        season = f"{dt.year}-{dt.year+1}"
    else:
        season = f"{dt.year-1}-{dt.year}"
    season_start_year = int(season.split('-')[0])
    if dt.month >= 8:
        months_from_start = dt.month - 8
        year_offset = dt.year - season_start_year
    else:
        months_from_start = dt.month + 12 - 8
        year_offset = dt.year - season_start_year - 1
    window = (months_from_start + year_offset * 12) // 3 + 1
    return f"S{season}-W{window}"

def predict(event_id):
    """
    預測指定比賽的 Over/Under 結果
    
    Args:
        event_id: 比賽 ID
        
    Returns:
        dict: {
            'event_id': str,
            'prediction': 'OVER' or 'UNDER',
            'probability': float,  # OVER probability
            'threshold': float,
            'features': dict,
            'model_info': str,
            'window_label': str
        }
    """
    conn = pymysql.connect(
        host='10.18.0.30', port=3306, user='root',
        password='QazWsxEdc$@3649', database='mslot', charset='utf8mb4'
    )
    
    row = get_event_features(event_id, conn)
    conn.close()
    
    if row is None:
        return {'error': f'Event {event_id} not found'}
    
    # Determine window
    window_label = get_window_for_event(row['start_time'])
    
    # Load model
    model_data, err = load_model_for_event(window_label)
    if err:
        return {'error': err, 'window_label': window_label}
    
    model = model_data['model']
    scaler = model_data['scaler']
    threshold = model_data['threshold']
    feature_cols = model_data['feature_cols']
    model_name = model_data['model_name']
    
    # Compute features
    feats = compute_features(row)
    
    # Build feature vector
    X = np.array([[feats.get(c, 0.0) for c in feature_cols]])
    X_scaled = scaler.transform(X)
    
    # Predict
    prob = model.predict_proba(X_scaled)[0, 1]
    prediction = 'OVER' if prob >= threshold else 'UNDER'
    
    return {
        'event_id': event_id,
        'home_team': row['home_team'],
        'away_team': row['away_team'],
        'start_time': str(row['start_time']),
        'prediction': prediction,
        'probability': float(prob),
        'threshold': float(threshold),
        'over_odd': float(row['over_odd']),
        'under_odd': float(row['under_odd']),
        'over_under_cap': float(row['over_under_cap']),
        'model_name': model_name,
        'model_window': window_label,
        'feature_cols': feature_cols,
        'features': {k: float(v) for k, v in feats.items() if k in feature_cols},
        'model_info': f'{LEAGUE_NAME} Over/Under Model ({model_name}) for {window_label}'
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python austria_bundesliga_predict.py <event_id>")
        sys.exit(1)
    
    result = predict(sys.argv[1])
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
