#!/usr/bin/env python3
"""
Turkey Super Lig Over/Under 預測腳本 (Combined Model)
用法: python turkey_combined_predict.py <event_id>
"""

import sys
import pickle
import pandas as pd
import numpy as np
import pymysql

MODEL_PATH = '/root/.openclaw/workspace/projects/football-analysis/models/turkey_combined_overunder.pkl'

def get_latest_odds(event_id, conn):
    """Fetch latest odds for an event"""
    cur = conn.cursor()
    
    # Over/Under odds
    cur.execute("""
        SELECT o1.* FROM fb_over_under_odd o1
        INNER JOIN (
            SELECT event_id, MAX(created_at) AS max_created
            FROM fb_over_under_odd WHERE event_id = %s GROUP BY event_id
        ) o2 ON o1.event_id = o2.event_id AND o1.created_at = o2.max_created
        WHERE o1.event_id = %s
    """, (event_id, event_id))
    ou_row = cur.fetchone()
    
    # Win odds
    cur.execute("""
        SELECT w1.* FROM fb_win_odd w1
        INNER JOIN (
            SELECT event_id, MAX(created_at) AS max_created
            FROM fb_win_odd WHERE event_id = %s GROUP BY event_id
        ) w2 ON w1.event_id = w2.event_id AND w1.created_at = w2.max_created
        WHERE w1.event_id = %s
    """, (event_id, event_id))
    wo_row = cur.fetchone()
    
    # Handicap odds
    cur.execute("""
        SELECT h1.* FROM fb_handicap_odd h1
        INNER JOIN (
            SELECT event_id, MAX(created_at) AS max_created
            FROM fb_handicap_odd WHERE event_id = %s GROUP BY event_id
        ) h2 ON h1.event_id = h2.event_id AND h1.created_at = h2.max_created
        WHERE h1.event_id = %s
    """, (event_id, event_id))
    ho_row = cur.fetchone()
    
    # Event info
    cur.execute("""
        SELECT e.event_id, e.start_time, e.home_id, e.away_id,
               ht.name AS home_team, at.name AS away_team
        FROM fb_event e
        LEFT JOIN fb_team ht ON e.home_id = ht.team_id
        LEFT JOIN fb_team at ON e.away_id = at.team_id
        WHERE e.event_id = %s
    """, (event_id,))
    event_row = cur.fetchone()
    
    return {
        'ou': ou_row,
        'wo': wo_row,
        'ho': ho_row,
        'event': event_row,
    }

def build_features(odds_data, df_history):
    """Build features from odds data and historical stats"""
    ou = odds_data['ou']
    wo = odds_data['wo']
    ho = odds_data['ho']
    ev = odds_data['event']
    
    if ou is None or ev is None:
        return None
    
    # Basic odds features
    over_odd = ou[3]  # over_odd
    cap = ou[4]       # over_under_cap
    under_odd = ou[5] # under_odd
    home_odd = wo[2] if wo else None
    draw_odd = wo[3] if wo else None
    away_odd = wo[4] if wo else None
    home_cap = ho[3] if ho else None
    
    implied_over_prob = 1 / over_odd
    implied_under_prob = 1 / under_odd
    implied_over_prob_norm = implied_over_prob / (implied_over_prob + implied_under_prob)
    over_odd_under_odd_ratio = over_odd / under_odd
    
    if home_odd and draw_odd and away_odd:
        total_win = (1/home_odd) + (1/draw_odd) + (1/away_odd)
        implied_home_prob_norm = (1/home_odd) / total_win
        implied_draw_prob_norm = (1/draw_odd) / total_win
        implied_away_prob_norm = (1/away_odd) / total_win
    else:
        implied_home_prob_norm = implied_draw_prob_norm = implied_away_prob_norm = 0.5
    
    # Cap features
    cap_is_2_5 = 1 if cap == 2.5 else 0
    cap_is_2_75 = 1 if cap == 2.75 else 0
    cap_is_3_0 = 1 if cap == 3.0 else 0
    cap_above_2_75 = 1 if cap > 2.75 else 0
    cap_normalized = (cap - 2.5) / 0.5
    
    # Vig features
    over_odds_vig = over_odd * implied_over_prob
    under_odds_vig = under_odd * implied_under_prob
    total_implied = implied_over_prob + implied_under_prob
    over_edge = implied_over_prob - (1 - implied_over_prob_norm)
    
    fav_home = 1 if home_odd and away_odd and home_odd < away_odd else 0
    odds_spread = (away_odd - home_odd) if home_odd and away_odd else 0
    home_advantage = implied_home_prob_norm - implied_away_prob_norm
    expected_over_prob = 1 - implied_under_prob_norm
    market_vs_expected = expected_over_prob - implied_over_prob_norm
    
    # Historical stats (from recent games of the teams)
    home_id = ev[2]
    away_id = ev[3]
    
    # Get last N games stats
    home_games = df_history[df_history['home_id'] == home_id].tail(10)
    away_games = df_history[df_history['away_id'] == away_id].tail(10)
    
    home_avg_goals = home_games['home_ft_score'].mean() if len(home_games) > 0 else 2.0
    home_avg_conceded = home_games['away_ft_score'].mean() if len(home_games) > 0 else 2.0
    away_avg_goals = away_games['away_ft_score'].mean() if len(away_games) > 0 else 2.0
    away_avg_conceded = away_games['home_ft_score'].mean() if len(away_games) > 0 else 2.0
    
    home_avg_total = home_avg_goals + away_avg_conceded
    away_avg_total = away_avg_goals + home_avg_conceded
    
    expected_total_vs_cap = (home_avg_total + away_avg_total) / 2
    expected_vs_cap_diff = expected_total_vs_cap - cap
    
    # Form
    home_recent = df_history[df_history['home_id'] == home_id].tail(5)
    away_recent = df_history[df_history['away_id'] == away_id].tail(5)
    
    home_form = home_recent.apply(lambda r: r['home_ft_score'] + r['away_ft_score'], axis=1).mean() if len(home_recent) > 0 else 2.5
    away_form = away_recent.apply(lambda r: r['home_ft_score'] + r['away_ft_score'], axis=1).mean() if len(away_recent) > 0 else 2.5
    combined_form = home_form + away_form
    
    feature_dict = {
        'over_odd': over_odd,
        'over_under_cap': cap,
        'under_odd': under_odd,
        'implied_over_prob_norm': implied_over_prob_norm,
        'over_odd_under_odd_ratio': over_odd_under_odd_ratio,
        'implied_home_prob_norm': implied_home_prob_norm,
        'implied_draw_prob_norm': implied_draw_prob_norm,
        'implied_away_prob_norm': implied_away_prob_norm,
        'handicap_spread': home_cap if home_cap else 0,
        'home_avg_goals': home_avg_goals,
        'home_avg_conceded': home_avg_conceded,
        'away_avg_goals': away_avg_goals,
        'away_avg_conceded': away_avg_conceded,
        'home_avg_total': home_avg_total,
        'away_avg_total': away_avg_total,
        'expected_total_vs_cap': expected_total_vs_cap,
        'expected_vs_cap_diff': expected_vs_cap_diff,
        'cap_normalized': cap_normalized,
        'home_form': home_form,
        'away_form': away_form,
        'combined_form': combined_form,
        'cap_is_2.5': cap_is_2_5,
        'cap_is_2.75': cap_is_2_75,
        'cap_is_3.0': cap_is_3_0,
        'cap_above_2.75': cap_above_2_75,
        'over_odds_vig': over_odds_vig,
        'under_odds_vig': under_odds_vig,
        'total_implied': total_implied,
        'over_edge': over_edge,
        'fav_home': fav_home,
        'odds_spread': odds_spread,
        'home_advantage': home_advantage,
        'expected_over_prob': expected_over_prob,
        'market_vs_expected': market_vs_expected,
    }
    
    return feature_dict

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
    with open(MODEL_PATH, 'rb') as f:
        pkg = pickle.load(f)
    
    model = pkg['model']
    scaler = pkg['scaler']
    feature_cols = pkg['feature_cols']
    
    # Connect to DB
    conn = pymysql.connect(
        host='10.18.0.30',
        port=3306,
        user='root',
        password='QazWsxEdc$@3649',
        database='mslot',
        charset='utf8mb4'
    )
    
    try:
        # Get odds data
        odds_data = get_latest_odds(event_id, conn)
        
        if odds_data['event'] is None:
            return {'error': f'Event {event_id} not found'}
        if odds_data['ou'] is None:
            return {'error': f'No over/under odds for event {event_id}'}
        
        ev = odds_data['event']
        home_team = ev[4]
        away_team = ev[5]
        
        # Build features
        # Get historical data for feature building
        cur = conn.cursor()
        cur.execute("""
            SELECT e.home_id, e.away_id, e.home_ft_score, e.away_ft_score, e.start_time
            FROM fb_event e
            WHERE e.event_type_id = 'e9fbca5f40f44ac8a772b0dfeb8064e8'
              AND e.home_ft_score IS NOT NULL
              AND e.away_ft_score IS NOT NULL
              AND e.start_time < (SELECT start_time FROM fb_event WHERE event_id = %s)
            ORDER BY e.start_time DESC
            LIMIT 500
        """, (event_id,))
        hist_rows = cur.fetchall()
        df_hist = pd.DataFrame(hist_rows, columns=['home_id', 'away_id', 'home_ft_score', 'away_ft_score', 'start_time'])
        
        features = build_features(odds_data, df_hist)
        if features is None:
            return {'error': 'Could not build features'}
        
        # Create feature vector
        X = pd.DataFrame([features])[feature_cols].fillna(0)
        X_sc = scaler.transform(X)
        
        # Predict
        prob_over = model.predict_proba(X_sc)[0, 1]
        threshold = 0.5  # Default threshold; model-specific threshold should be used
        prediction = 'OVER' if prob_over > threshold else 'UNDER'
        
        return {
            'event_id': event_id,
            'home_team': home_team,
            'away_team': away_team,
            'prediction': prediction,
            'probability': round(float(prob_over), 4),
            'threshold': threshold,
            'features': {k: round(float(v), 4) for k, v in features.items()},
            'model_info': 'Turkey Super Lig Combined Over/Under XGBoost Model (max_depth=5, n_estimators=300)',
            'odds': {
                'over_odd': float(odds_data['ou'][3]),
                'cap': float(odds_data['ou'][4]),
                'under_odd': float(odds_data['ou'][5]),
            }
        }
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python turkey_combined_predict.py <event_id>")
        sys.exit(1)
    result = predict(sys.argv[1])
    print(result)
