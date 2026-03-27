#!/usr/bin/env python3
"""
U21 Euro Qualifiers Over/Under 預測腳本
用法: python u21_euro_qualifiers_predict.py <event_id>
"""

import sys
import pickle
import pandas as pd
import numpy as np
import pymysql

def get_event_odds(event_id: str) -> dict:
    """Fetch latest odds for an event from database"""
    conn = pymysql.connect(
        host='10.18.0.30',
        port=3306,
        user='root',
        password='QazWsxEdc$@3649',
        database='mslot',
        charset='utf8mb4'
    )
    
    query = """
    SELECT 
        e.event_id, e.start_time, ht.name AS home_team, at.name AS away_team,
        ou.over_odd, ou.over_under_cap, ou.under_odd,
        wo.home_odd, wo.draw_odd, wo.away_odd,
        ho.home_cap, ho.home_odd AS home_handicap_odd, ho.away_odd AS away_handicap_odd
    FROM fb_event e
    LEFT JOIN fb_team ht ON e.home_id = ht.team_id
    LEFT JOIN fb_team at ON e.away_id = at.team_id
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
    conn.close()
    
    if len(df) == 0:
        return None
    
    return df.iloc[0].to_dict()

def build_features(data: pd.DataFrame) -> pd.DataFrame:
    """Build features for prediction"""
    f = pd.DataFrame()
    f['over_odd'] = data['over_odd'].fillna(1.8) if pd.notna(data['over_odd']) else 1.8
    f['under_odd'] = data['under_odd'].fillna(1.8) if pd.notna(data['under_odd']) else 1.8
    f['over_under_cap'] = data['over_under_cap'].fillna(2.75) if pd.notna(data['over_under_cap']) else 2.75
    f['implied_over'] = 1 / f['over_odd']
    f['implied_under'] = 1 / f['under_odd']
    f['odds_ratio'] = f['over_odd'] / f['under_odd']
    
    cap = data['over_under_cap'] if pd.notna(data['over_under_cap']) else 2.75
    f['cap_2_5_2_75'] = 1 if (cap > 2.5 and cap <= 2.75) else 0
    f['cap_2_75_3_0'] = 1 if (cap > 2.75 and cap <= 3.0) else 0
    f['cap_3_0_3_5'] = 1 if (cap > 3.0 and cap <= 3.5) else 0
    f['cap_high'] = 1 if cap > 3.5 else 0
    f['cap_low'] = 1 if cap <= 2.5 else 0
    f['cap_norm'] = (cap - 2.5) / 1.5
    
    f['home_odd'] = data['home_odd'].fillna(1.8) if pd.notna(data['home_odd']) else 1.8
    f['away_odd'] = data['away_odd'].fillna(3.5) if pd.notna(data['away_odd']) else 3.5
    f['draw_odd'] = data['draw_odd'].fillna(3.5) if pd.notna(data['draw_odd']) else 3.5
    sum_odds = f['home_odd'] + f['draw_odd'] + f['away_odd']
    f['home_prob'] = f['home_odd'] / sum_odds
    f['away_prob'] = f['away_odd'] / sum_odds
    f['favor_over'] = 1 if f['over_odd'].iloc[0] < f['under_odd'].iloc[0] else 0
    f['market_even'] = 1 if abs(f['over_odd'].iloc[0] - f['under_odd'].iloc[0]) < 0.05 else 0
    f['home_cap'] = data['home_cap'] if pd.notna(data['home_cap']) else 0
    f['home_cap_abs'] = abs(data['home_cap']) if pd.notna(data['home_cap']) else 0
    
    return f.fillna(0)

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
    with open('/root/.openclaw/workspace/projects/verified_models/models/u21_euro_qualifiers_combined.pkl', 'rb') as f:
        model_data = pickle.load(f)
    
    model = model_data['model']
    threshold = model_data['threshold']
    
    # Get event data
    event_data = get_event_odds(event_id)
    if event_data is None:
        return {'error': f'Event {event_id} not found'}
    
    # Build features
    features = build_features(pd.DataFrame([event_data]))
    
    # Predict
    prob = model.predict_proba(features)[0][1]
    prediction = 'OVER' if prob >= threshold else 'UNDER'
    
    return {
        'event_id': event_id,
        'home_team': event_data.get('home_team'),
        'away_team': event_data.get('away_team'),
        'prediction': prediction,
        'probability': float(prob),
        'threshold': threshold,
        'features': {
            'over_odd': float(event_data.get('over_odd', 0)),
            'under_odd': float(event_data.get('under_odd', 0)),
            'over_under_cap': float(event_data.get('over_under_cap', 0)),
            'implied_over_prob': float(1/event_data.get('over_odd', 1.8)) if event_data.get('over_odd') else 0
        },
        'model_info': f'U21 Euro Qualifiers Combined Over/Under Model (LogisticRegression)'
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python u21_euro_qualifiers_predict.py <event_id>")
        sys.exit(1)
    
    result = predict(sys.argv[1])
    print(result)