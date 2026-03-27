#!/usr/bin/env python3
"""
Serbia Super Liga Over/Under 預測腳本
用法: python serbia_super_liga_predict.py <event_id>
"""

import sys
import pickle
import pandas as pd
import numpy as np
import pymysql
from datetime import datetime

def get_season(dt):
    if dt.month >= 8:
        return f"{dt.year}-{dt.year+1}"
    else:
        return f"{dt.year-1}-{dt.year}"

def get_window(dt):
    month = dt.month
    if month in [8, 9, 10]:
        return 1
    elif month in [11, 12, 1]:
        return 2
    elif month in [2, 3, 4]:
        return 3
    else:
        return 4

def get_event_data(event_id):
    """Fetch event data from database"""
    connection = pymysql.connect(
        host='10.18.0.30',
        port=3306,
        user='root',
        password='QazWsxEdc$@3649',
        database='mslot',
        charset='utf8mb4'
    )
    
    query = """
    SELECT 
        e.event_id,
        e.start_time,
        ht.name AS home_team,
        at.name AS away_team,
        e.home_ft_score,
        e.away_ft_score,
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
    
    df = pd.read_sql(query, connection, params=(event_id,))
    connection.close()
    
    if len(df) == 0:
        return None
    
    return df.iloc[0]

def engineer_features(row, historical_df):
    """Engineer features for a single event"""
    
    # Implied probabilities
    implied_over_prob = 1 / row['over_odd']
    implied_under_prob = 1 / row['under_odd']
    implied_home_prob = 1 / row['home_odd']
    implied_draw_prob = 1 / row['draw_odd']
    implied_away_prob = 1 / row['away_odd']
    
    # Odds ratios
    over_under_ratio = row['over_odd'] / row['under_odd']
    home_away_ratio = row['home_odd'] / row['away_odd']
    
    # Odds gaps
    ou_odds_gap = row['over_odd'] - row['under_odd']
    ha_odds_gap = row['home_odd'] - row['away_odd']
    
    # Cap features
    cap_level = row['over_under_cap'] - 2.5
    cap_floor = 1 if row['over_under_cap'] <= 2.5 else 0
    
    # Market indicators
    market_bias_over = 1 if implied_over_prob > 0.5 else 0
    market_favorite_home = 1 if implied_home_prob > implied_away_prob else 0
    
    # Overround
    overround_ou = implied_over_prob + implied_under_prob
    overround_ha = implied_home_prob + implied_draw_prob + implied_away_prob
    
    # Logit features
    eps = 1e-6
    logit_over = np.log((implied_over_prob + eps) / (1 - implied_over_prob + eps))
    logit_home = np.log((implied_home_prob + eps) / (1 - implied_home_prob + eps))
    
    # Historical features (from past matches only)
    home = row['home_team']
    away = row['away_team']
    
    # Filter historical data for this team (before this event)
    home_history = historical_df[historical_df['home_team'] == home]
    home_history = home_history[home_history['start_time'] < row['start_time']].tail(10)
    away_history = historical_df[historical_df['away_team'] == away]
    away_history = away_history[away_history['start_time'] < row['start_time']].tail(10)
    
    # Also check when team was away
    home_as_away = historical_df[historical_df['away_team'] == home]
    home_as_away = home_as_away[home_as_away['start_time'] < row['start_time']].tail(10)
    
    away_as_home = historical_df[historical_df['home_team'] == away]
    away_as_home = away_as_home[away_as_home['start_time'] < row['start_time']].tail(10)
    
    # Home team historical stats
    all_home_history = pd.concat([home_history, home_as_away])
    if len(all_home_history) >= 3:
        home_avg_scored = all_home_history['home_ft_score'].mean() if len(home_history) > 0 else all_home_history[all_home_history['home_team']==home]['home_ft_score'].mean() if len(all_home_history[all_home_history['home_team']==home]) > 0 else all_home_history['home_ft_score'].mean()
        home_avg_conceded = all_home_history['away_ft_score'].mean()
        home_over_rate = (all_home_history['total_goals'] > all_home_history['over_under_cap']).mean()
    else:
        home_avg_scored = 1.5
        home_avg_conceded = 1.3
        home_over_rate = 0.45
    
    # Away team historical stats
    all_away_history = pd.concat([away_history, away_as_home])
    if len(all_away_history) >= 3:
        away_avg_scored = all_away_history['away_ft_score'].mean() if len(away_history) > 0 else all_away_history['away_ft_score'].mean()
        away_avg_conceded = all_away_history['home_ft_score'].mean()
        away_over_rate = (all_away_history['total_goals'] > all_away_history['over_under_cap']).mean()
    else:
        away_avg_scored = 1.2
        away_avg_conceded = 1.4
        away_over_rate = 0.40
    
    combined_avg_total = (home_avg_scored + away_avg_conceded + away_avg_scored + home_avg_conceded) / 4
    avg_over_rate = (home_over_rate + away_over_rate) / 2
    
    features = {
        'over_odd': row['over_odd'],
        'under_odd': row['under_odd'],
        'over_under_cap': row['over_under_cap'],
        'home_odd': row['home_odd'],
        'draw_odd': row['draw_odd'],
        'away_odd': row['away_odd'],
        'implied_over_prob': implied_over_prob,
        'implied_under_prob': implied_under_prob,
        'implied_home_prob': implied_home_prob,
        'implied_draw_prob': implied_draw_prob,
        'implied_away_prob': implied_away_prob,
        'over_under_ratio': over_under_ratio,
        'home_away_ratio': home_away_ratio,
        'ou_odds_gap': ou_odds_gap,
        'ha_odds_gap': ha_odds_gap,
        'cap_level': cap_level,
        'cap_floor': cap_floor,
        'home_cap': row['home_cap'],
        'home_handicap_odd': row['home_handicap_odd'],
        'away_handicap_odd': row['away_handicap_odd'],
        'market_bias_over': market_bias_over,
        'market_favorite_home': market_favorite_home,
        'overround_ou': overround_ou,
        'overround_ha': overround_ha,
        'logit_over': logit_over,
        'logit_home': logit_home,
        'home_avg_scored': home_avg_scored,
        'home_avg_conceded': home_avg_conceded,
        'away_avg_scored': away_avg_scored,
        'away_avg_conceded': away_avg_conceded,
        'home_over_rate': home_over_rate,
        'away_over_rate': away_over_rate,
        'combined_avg_total': combined_avg_total,
        'avg_over_rate': avg_over_rate
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
            'probability': float,
            'threshold': float,
            'features': dict,
            'model_info': str
        }
    """
    
    # Load models
    models_path = '/root/.openclaw/workspace/projects/verified_models/models/serbia_super_liga_combined_ou_models.pkl'
    with open(models_path, 'rb') as f:
        window_models = pickle.load(f)
    
    # Get event data
    event = get_event_data(event_id)
    if event is None:
        return {'error': f'Event {event_id} not found'}
    
    # Determine season/window
    start_time = event['start_time']
    season = get_season(start_time)
    window = get_window(start_time)
    window_key = f"{season}_W{window}"
    
    # Also check previous window if current not available
    if window_key not in window_models:
        # Try previous window in same season
        prev_window = window - 1
        if prev_window >= 1:
            window_key = f"{season}_W{prev_window}"
        if window_key not in window_models:
            # Try latest available model
            window_key = sorted(window_models.keys())[-1]
    
    model_data = window_models[window_key]
    
    # Load historical data for feature engineering
    historical_df = pd.read_pickle('/root/.openclaw/workspace/projects/verified_models/reports/serbia_super_liga_enhanced_data.pkl')
    
    # Engineer features
    features = engineer_features(event, historical_df)
    feature_values = [features[k] for k in model_data['features']]
    
    # Transform features
    X = np.array([feature_values])
    X_scaled = model_data['scaler'].transform(X)
    X_selected = model_data['selector'].transform(X_scaled)
    
    # Predict
    prob = model_data['model'].predict_proba(X_selected)[0, 1]
    prediction = 'OVER' if prob >= model_data['threshold'] else 'UNDER'
    
    return {
        'event_id': event_id,
        'home_team': event['home_team'],
        'away_team': event['away_team'],
        'start_time': str(start_time),
        'prediction': prediction,
        'probability': float(prob),
        'threshold': float(model_data['threshold']),
        'window_used': window_key,
        'features': {k: float(features[k]) for k in list(features.keys())[:10]},  # Top 10 features
        'model_info': f"Serbia Super Liga Combined O/U Model (window: {window_key})"
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python serbia_super_liga_predict.py <event_id>")
        sys.exit(1)
    result = predict(sys.argv[1])
    print(result)
