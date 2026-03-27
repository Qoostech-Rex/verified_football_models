#!/usr/bin/env python3
"""
日本職業聯賽 (Japan Professional League) Over/Under 預測腳本
用法: python japan_professional_league_predict.py <event_id>
"""

import sys
import pickle
import pandas as pd
import numpy as np
import pymysql
from datetime import datetime
from sklearn.preprocessing import LabelEncoder

MODEL_PATH = '/root/.openclaw/workspace/projects/football-analysis/models/japan_professional_league_combined.pkl'

def load_model():
    with open(MODEL_PATH, 'rb') as f:
        return pickle.load(f)

def get_event_data(event_id):
    """Fetch event data from database."""
    conn = pymysql.connect(
        host='10.18.0.30', port=3306, user='root',
        password='QazWsxEdc$@3649', database='mslot', charset='utf8mb4'
    )
    query = """
    SELECT 
        e.event_id, e.start_time, e.home_id, e.away_id,
        ht.name AS home_team, at.name AS away_team,
        wo.home_odd, wo.draw_odd, wo.away_odd,
        ou.over_odd, ou.over_under_cap, ou.under_odd,
        ho.home_cap, ho.home_odd AS home_handicap_odd, ho.away_odd AS away_handicap_odd
    FROM fb_event e
    JOIN fb_team ht ON e.home_id = ht.team_id
    JOIN fb_team at ON e.away_id = at.team_id
    LEFT JOIN (
        SELECT w1.* FROM fb_win_odd w1
        INNER JOIN (
            SELECT event_id, MAX(created_at) AS max_created
            FROM fb_win_odd GROUP BY event_id
        ) w2 ON w1.event_id = w2.event_id AND w1.created_at = w2.max_created
    ) wo ON e.event_id = wo.event_id
    LEFT JOIN (
        SELECT o1.* FROM fb_over_under_odd o1
        INNER JOIN (
            SELECT event_id, MAX(created_at) AS max_created
            FROM fb_over_under_odd GROUP BY event_id
        ) o2 ON o1.event_id = o2.event_id AND o1.created_at = o2.max_created
    ) ou ON e.event_id = ou.event_id
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
    return df

def get_historical_stats(home_id, away_id, cutoff_time):
    """Get historical stats for both teams before cutoff_time."""
    conn = pymysql.connect(
        host='10.18.0.30', port=3306, user='root',
        password='QazWsxEdc$@3649', database='mslot', charset='utf8mb4'
    )
    query = """
    SELECT e.home_id, e.away_id, e.home_ft_score, e.away_ft_score, e.start_time
    FROM fb_event e
    WHERE e.start_time < %s
    AND e.home_ft_score IS NOT NULL
    AND (e.home_id = %s OR e.away_id = %s)
    ORDER BY e.start_time DESC
    LIMIT 30
    """
    df = pd.read_sql(query, conn, params=(cutoff_time, home_id, away_id))
    conn.close()
    
    if len(df) == 0:
        return {}
    
    home_past = df[df['home_id'] == home_id]
    away_past = df[df['away_id'] == away_id]
    
    # All past for this home team
    home_games = df[(df['home_id'] == home_id) | (df['away_id'] == home_id)]
    away_games = df[(df['home_id'] == away_id) | (df['away_id'] == away_id)]
    
    stats = {}
    if len(home_games) > 0:
        stats['home_avg_scored'] = home_games.apply(
            lambda r: r['home_ft_score'] if r['home_id'] == home_id else r['away_ft_score'], axis=1).mean()
        stats['home_avg_conceded'] = home_games.apply(
            lambda r: r['away_ft_score'] if r['home_id'] == home_id else r['home_ft_score'], axis=1).mean()
    else:
        stats['home_avg_scored'] = 2.3
        stats['home_avg_conceded'] = 2.3
    
    if len(away_games) > 0:
        stats['away_avg_scored'] = away_games.apply(
            lambda r: r['away_ft_score'] if r['away_id'] == away_id else r['home_ft_score'], axis=1).mean()
        stats['away_avg_conceded'] = away_games.apply(
            lambda r: r['home_ft_score'] if r['away_id'] == away_id else r['away_ft_score'], axis=1).mean()
    else:
        stats['away_avg_scored'] = 2.3
        stats['away_avg_conceded'] = 2.3
    
    return stats

def build_features(event_row, hist_stats):
    """Build feature vector from event data."""
    over_under_cap = event_row['over_under_cap']
    over_odd = event_row['over_odd']
    under_odd = event_row['under_odd']
    implied_prob_over = 1 / over_odd
    implied_prob_under = 1 / under_odd
    total_prob = implied_prob_over + implied_prob_under
    market_over_prob = implied_prob_over / total_prob
    implied_prob_home = 1 / event_row['home_odd']
    implied_prob_draw = 1 / event_row['draw_odd']
    implied_prob_away = 1 / event_row['away_odd']
    home_cap = event_row['home_cap'] if pd.notna(event_row['home_cap']) else 0
    odds_imbalance = over_odd - under_odd
    odds_ratio = over_odd / under_odd
    prob_deviation = abs(market_over_prob - 0.5)
    
    home_avg_scored = hist_stats.get('home_avg_scored', 2.3)
    home_avg_conceded = hist_stats.get('home_avg_conceded', 2.3)
    away_avg_scored = hist_stats.get('away_avg_scored', 2.3)
    away_avg_conceded = hist_stats.get('away_avg_conceded', 2.3)
    
    home_strength = home_avg_scored - home_avg_conceded
    away_strength = away_avg_scored - away_avg_conceded
    strength_diff = home_strength - away_strength
    expected_total = (home_avg_scored + away_avg_scored + home_avg_conceded + away_avg_conceded) / 2
    cap_vs_expected = over_under_cap - expected_total
    
    feature_cols = [
        'over_under_cap', 'over_odd', 'under_odd', 'market_over_prob',
        'implied_prob_home', 'home_cap', 'odds_imbalance', 'odds_ratio',
        'prob_deviation', 'home_strength', 'away_strength', 'strength_diff',
        'expected_total', 'cap_vs_expected', 'home_id_enc', 'away_id_enc',
        'home_avg_scored', 'home_avg_conceded', 'away_avg_scored', 'away_avg_conceded',
    ]
    
    # Get team encoder
    model_pkg = load_model()
    le_teams = model_pkg['team_encoder']
    home_id_enc = le_teams.transform([event_row['home_id']])[0]
    away_id_enc = le_teams.transform([event_row['away_id']])[0]
    
    values = [
        over_under_cap, over_odd, under_odd, market_over_prob,
        implied_prob_home, home_cap, odds_imbalance, odds_ratio,
        prob_deviation, home_strength, away_strength, strength_diff,
        expected_total, cap_vs_expected, home_id_enc, away_id_enc,
        home_avg_scored, home_avg_conceded, away_avg_scored, away_avg_conceded,
    ]
    
    return dict(zip(feature_cols, values))

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
    model_pkg = load_model()
    model = model_pkg['model']
    scaler = model_pkg['scaler']
    feature_cols = model_pkg['feature_cols']
    
    # Get event data
    event_df = get_event_data(event_id)
    if len(event_df) == 0:
        return {'error': f'No event found with id: {event_id}'}
    
    event = event_df.iloc[0]
    
    # Get historical stats
    hist_stats = get_historical_stats(event['home_id'], event['away_id'], event['start_time'])
    
    # Build features
    features = build_features(event, hist_stats)
    X = np.array([[features[col] for col in feature_cols]])
    X_scaled = scaler.transform(X)
    
    # Predict
    proba = model.predict_proba(X_scaled)[0, 1]
    
    # Use threshold from per-window results (average threshold ~0.5)
    threshold = 0.50
    prediction = 'OVER' if proba >= threshold else 'UNDER'
    
    return {
        'event_id': event_id,
        'home_team': event['home_team'],
        'away_team': event['away_team'],
        'prediction': prediction,
        'probability': round(float(proba), 4),
        'threshold': threshold,
        'features': {k: round(float(v), 4) if isinstance(v, (float, np.floating)) else v for k, v in features.items()},
        'model_info': f"日本職業聯賽 Combined Over/Under - GradientBoosting",
        'over_odd': float(event['over_odd']),
        'under_odd': float(event['under_odd']),
        'over_under_cap': float(event['over_under_cap']),
        'start_time': str(event['start_time']),
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python japan_professional_league_predict.py <event_id>")
        sys.exit(1)
    result = predict(sys.argv[1])
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
