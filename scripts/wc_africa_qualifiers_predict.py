#!/usr/bin/env python3
"""
World Cup Africa Qualifiers Over/Under 預測腳本
用法: python wc_africa_qualifiers_predict.py <event_id>
"""

import sys
import pickle
import pandas as pd
import numpy as np

MODEL_PATH = '/root/.openclaw/workspace/projects/verified_models/models/wc_africa_qualifiers.pkl'

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
            'features': dict,     # 使用的特征值
            'model_info': str     # 模型描述
        }
    """
    # Load model
    with open(MODEL_PATH, 'rb') as f:
        data = pickle.load(f)
    
    artifacts = data['artifacts']
    features = data['features']
    
    # For simplicity, use the last window's model (most recent)
    # In production, you'd determine which window based on event time
    latest_window = sorted(artifacts.keys())[-1]
    artifact = artifacts[latest_window]
    
    model = artifact['model']
    scaler = artifact['scaler']
    threshold = artifact['threshold']
    
    # Fetch data for this event
    import pymysql
    conn = pymysql.connect(
        host='10.18.0.30', port=3306, user='root',
        password='QazWsxEdc$@3649', database='mslot', charset='utf8mb4'
    )
    
    query = """
    SELECT e.event_id, e.start_time, ht.name AS home_team, at.name AS away_team,
        wo.home_odd, wo.draw_odd, wo.away_odd,
        ou.over_odd, ou.over_under_cap, ou.under_odd,
        ho.home_cap, ho.home_odd AS home_handicap_odd, ho.away_odd AS away_handicap_odd
    FROM fb_event e
    JOIN fb_team ht ON e.home_id = ht.team_id
    JOIN fb_team at ON e.away_id = at.team_id
    LEFT JOIN (
        SELECT w1.* FROM fb_win_odd w1
        INNER JOIN (SELECT event_id, MAX(created_at) AS max_created FROM fb_win_odd GROUP BY event_id) w2
        ON w1.event_id = w2.event_id AND w1.created_at = w2.max_created
    ) wo ON e.event_id = wo.event_id
    LEFT JOIN (
        SELECT o1.* FROM fb_over_under_odd o1
        INNER JOIN (SELECT event_id, MAX(created_at) AS max_created FROM fb_over_under_odd GROUP BY event_id) o2
        ON o1.event_id = o2.event_id AND o1.created_at = o2.max_created
    ) ou ON e.event_id = ou.event_id
    LEFT JOIN (
        SELECT h1.* FROM fb_handicap_odd h1
        INNER JOIN (SELECT event_id, MAX(created_at) AS max_created FROM fb_handicap_odd GROUP BY event_id) h2
        ON h1.event_id = h2.event_id AND h1.created_at = h2.max_created
    ) ho ON e.event_id = ho.event_id
    WHERE e.event_id = %s
    """
    
    df = pd.read_sql(query, conn, params=(event_id,))
    conn.close()
    
    if df.empty:
        return {'error': f'No event found with id {event_id}'}
    
    row = df.iloc[0]
    
    # Build features
    row['implied_over_prob'] = 1 / row['over_odd']
    row['implied_under_prob'] = 1 / row['under_odd']
    row['odds_spread'] = row['over_odd'] - row['under_odd']
    row['over_under_ratio'] = row['over_odd'] / row['under_odd']
    row['cap_centered'] = row['over_under_cap'] - 2.5
    row['home_win_prob'] = 1 / row['home_odd']
    row['draw_prob'] = 1 / row['draw_odd']
    row['away_win_prob'] = 1 / row['away_odd']
    row['home_away_diff'] = row['home_win_prob'] - row['away_win_prob']
    row['home_cap_abs'] = abs(row['home_cap'])
    
    X = row[features].values.reshape(1, -1)
    X_s = scaler.transform(X)
    prob = model.predict_proba(X_s)[0, 1]
    
    prediction = 'OVER' if prob >= threshold else 'UNDER'
    
    return {
        'event_id': event_id,
        'prediction': prediction,
        'probability': float(prob),
        'threshold': float(threshold),
        'features': {f: float(row[f]) for f in features},
        'model_info': f'WC Africa Qualifiers model (window={latest_window})',
        'home_team': row['home_team'],
        'away_team': row['away_team'],
        'start_time': str(row['start_time']),
        'over_under_cap': float(row['over_under_cap']),
        'over_odd': float(row['over_odd']),
        'under_odd': float(row['under_odd'])
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python wc_africa_qualifiers_predict.py <event_id>")
        sys.exit(1)
    result = predict(sys.argv[1])
    print(result)
