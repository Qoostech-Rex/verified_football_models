#!/usr/bin/env python3
"""
German Bundesliga Over/Under Prediction Script
==============================================
League: German Bundesliga (德甲)
Event Type ID: df1451df9b5b450aab4659bebe8c58fa
Model: Combined Over/Under (using both Over and Under odds)

Usage:
    python bundesliga_predict.py <event_id>

Example:
    python bundesliga_predict.py 810160
"""

import sys
import pickle
import pandas as pd
import numpy as np
import pymysql
from datetime import datetime

# Paths
MODEL_PATH = '/root/.openclaw/workspace/projects/football-analysis/models/bundesliga_results.pkl'
DATA_PATH = '/root/.openclaw/workspace/projects/football-analysis/models/bundesliga_enhanced.pkl'

def get_event_features(event_id: str) -> dict:
    """
    Fetch the latest features for a given event_id from the database.
    """
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
        ho.home_odd AS home_handicap_odd,
        ho.away_odd AS away_handicap_odd
    FROM fb_event e
    JOIN fb_event_type et ON e.event_type_id = et.event_type_id
    JOIN fb_team ht ON e.home_id = ht.team_id
    JOIN fb_team at ON e.away_id = at.team_id
    JOIN (
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
    WHERE et.event_type_id = 'df1451df9b5b450aab4659bebe8c58fa'
    AND e.event_id = %s
    """
    
    df = pd.read_sql(query, conn, params=(event_id,))
    conn.close()
    
    if df.empty:
        return None
    
    row = df.iloc[0]
    return row.to_dict()


def get_model_for_event(event_time: datetime) -> tuple:
    """
    Select the appropriate model based on event time.
    
    Bundesliga Season Windows:
    - W1: Aug to Oct
    - W2: Nov to Jan (next year)
    - W3: Feb to May
    """
    with open(MODEL_PATH, 'rb') as f:
        data = pickle.load(f)
    
    # Determine season/window from event time
    year = event_time.year
    month = event_time.month
    
    # Season determination
    if year == 2024 and month >= 8:
        season = "2024-2025"
    elif year == 2025 and month <= 5:
        season = "2024-2025"
    elif year == 2025 and month >= 8:
        season = "2025-2026"
    elif year == 2026 and month <= 5:
        season = "2025-2026"
    else:
        season = None
    
    # Window determination
    if month in [8, 9, 10]:
        window_num = 1
    elif month in [11, 12]:
        window_num = 2
    elif month == 1:
        window_num = 2
    elif month in [2, 3, 4, 5]:
        window_num = 3
    else:
        window_num = None
    
    # Try exact match first
    if season and window_num:
        model_key = f"{season}_W{window_num}"
        if model_key in data['models']:
            return data['models'][model_key], data['feature_cols']
    
    # Fallback: use the best available model (2025-2026 W1)
    # For events in 2024-2025 W1 (Aug-Oct 2024), no model exists
    # Use the best performing model as fallback
    fallback_keys = ['2025-2026_W1', '2025-2026_W2', '2025-2026_W3',
                     '2024-2025_W3', '2024-2025_W2']
    for key in fallback_keys:
        if key in data['models']:
            return data['models'][key], data['feature_cols']
    
    return None, None


def compute_features_from_row(row: dict) -> np.ndarray:
    """
    Compute derived features from raw event data.
    """
    features = {}
    
    # Basic odds features
    features['over_odd'] = row['over_odd']
    features['under_odd'] = row['under_odd']
    features['over_under_cap'] = row['over_under_cap']
    features['home_odd'] = row['home_odd']
    features['draw_odd'] = row['draw_odd']
    features['away_odd'] = row['away_odd']
    features['home_handicap_odd'] = row.get('home_handicap_odd', 2.0)
    features['away_handicap_odd'] = row.get('away_handicap_odd', 2.0)
    
    # Historical averages (using league averages as fallback)
    features['home_avg_goals_for'] = 1.5
    features['home_avg_goals_against'] = 1.5
    features['away_avg_goals_for'] = 1.5
    features['away_avg_goals_against'] = 1.5
    features['home_recent_win_rate'] = 0.45
    features['away_recent_win_rate'] = 0.45
    features['combined_avg_goals'] = 3.0
    features['combined_avg_defense'] = 3.0
    features['goal_diff_avg'] = 0
    features['form_diff'] = 0
    
    # Implied probabilities
    features['implied_prob_over'] = 1 / row['over_odd']
    features['implied_prob_under'] = 1 / row['under_odd']
    features['juice'] = row['over_odd'] + row['under_odd'] - 2
    features['cap_normalized'] = row['over_under_cap'] - 3.0
    
    # O/U rates
    features['home_team_ou_rate'] = 0.5
    features['away_team_ou_rate'] = 0.5
    features['home_team_gd'] = 0
    features['away_team_gd'] = 0
    features['combined_ou_rate'] = 0.5
    features['vig_free_over'] = features['implied_prob_over'] / (features['implied_prob_over'] + features['implied_prob_under'])
    features['vig_free_under'] = features['implied_prob_under'] / (features['implied_prob_over'] + features['implied_prob_under'])
    features['cap_deviation'] = row['over_under_cap'] - 3.0
    features['odds_ratio'] = row['over_odd'] / row['under_odd']
    
    return features


def predict(event_id: str) -> dict:
    """
    Predict Over/Under for a given event_id.
    
    Args:
        event_id: Event ID string
        
    Returns:
        dict: {
            'event_id': str,
            'prediction': 'OVER' or 'UNDER',
            'probability': float,  # Probability of OVER
            'threshold': float,    # Threshold used
            'features': dict,      # Feature values used
            'model_info': str,     # Model description
            'window': str,         # Season/Window
            'odds': dict           # Available odds
        }
    """
    # Get event data
    row = get_event_features(event_id)
    if row is None:
        return {'error': f'Event {event_id} not found or not a Bundesliga match'}
    
    # Get model
    model_data, feature_cols = get_model_for_event(row['start_time'])
    if model_data is None:
        return {'error': 'No suitable model found for this event time'}
    
    # Compute features
    features = compute_features_from_row(row)
    
    # Build feature vector
    X = np.array([[features.get(f, 0.0) for f in feature_cols]])
    
    # Scale
    X_scaled = model_data['scaler'].transform(X)
    
    # Predict
    prob_over = model_data['model'].predict_proba(X_scaled)[0, 1]
    prediction = 'OVER' if prob_over > model_data['threshold'] else 'UNDER'
    
    return {
        'event_id': event_id,
        'home_team': row['home_team'],
        'away_team': row['away_team'],
        'start_time': str(row['start_time']),
        'prediction': prediction,
        'probability': round(float(prob_over), 4),
        'threshold': round(float(model_data['threshold']), 4),
        'model_name': model_data['model_name'],
        'window': model_data['window_label'],
        'odds': {
            'over_odd': row['over_odd'],
            'under_odd': row['under_odd'],
            'over_under_cap': row['over_under_cap']
        },
        'features_used': {f: round(features.get(f, 0.0), 4) for f in feature_cols}
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python bundesliga_predict.py <event_id>")
        print("\nExample:")
        print("  python bundesliga_predict.py 810160")
        sys.exit(1)
    
    event_id = sys.argv[1]
    result = predict(event_id)
    
    if 'error' in result:
        print(f"Error: {result['error']}")
        sys.exit(1)
    
    print("=" * 60)
    print("BUNDESLIGA OVER/UNDER PREDICTION")
    print("=" * 60)
    print(f"Event ID:    {result['event_id']}")
    print(f"Match:       {result['home_team']} vs {result['away_team']}")
    print(f"Start Time:  {result['start_time']}")
    print(f"Window:      {result['window']}")
    print("-" * 60)
    print(f"Prediction:  {result['prediction']}")
    print(f"Probability: {result['probability']:.2%}")
    print(f"Threshold:   {result['threshold']:.2f}")
    print(f"Model:       {result['model_name']}")
    print("-" * 60)
    print(f"O/U Cap:     {result['odds']['over_under_cap']}")
    print(f"Over Odd:    {result['odds']['over_odd']}")
    print(f"Under Odd:   {result['odds']['under_odd']}")
    print("=" * 60)
