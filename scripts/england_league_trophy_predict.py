#!/usr/bin/env python3
"""
England League Trophy Over/Under 預測腳本
用法: python england_league_trophy_predict.py <event_id>
"""

import sys
import pickle
import pandas as pd
import numpy as np
import pymysql
from datetime import datetime

MODEL_PATH = '/root/.openclaw/workspace/projects/verified_models/models/england_league_trophy_combined.pkl'

def get_season(dt):
    if dt.month >= 8: return f"{dt.year}-{dt.year+1}"
    else: return f"{dt.year-1}-{dt.year}"

def get_window_label(dt):
    m, y = dt.month, dt.year
    if m in [8,9,10]: return f"{y}-08 to {y}-10"
    elif m in [11,12]: return f"{y}-11 to {y+1}-01"
    elif m == 1: return f"{y-1}-11 to {y}-01"
    elif m in [2,3,4]: return f"{y}-02 to {y}-04"
    elif m in [5,6,7]: return f"{y}-05 to {y}-07"
    return None

def get_window_season(row):
    sy = int(row['season'][:4]); wl = row['window_label']
    if wl is None: return None
    if wl.startswith(f"{sy}-08"): return f"{sy}-{sy+1} / Aug-Oct"
    elif wl.startswith(f"{sy}-11") or wl.startswith(f"{sy+1}-01"): return f"{sy}-{sy+1} / Nov-Jan"
    elif wl.startswith(f"{sy}-02"): return f"{sy}-{sy+1} / Feb-Apr"
    elif wl.startswith(f"{sy}-05"): return f"{sy}-{sy+1} / May-Jul"
    return None

def build_features(df_in):
    df = df_in.copy()
    df['implied_prob_over'] = 1 / df['over_odd']
    df['implied_prob_under'] = 1 / df['under_odd']
    df['over_under_ratio'] = df['over_odd'] / df['under_odd']
    df['over_under_diff'] = df['implied_prob_over'] - df['implied_prob_under']
    df['implied_prob_home_win'] = 1 / df['home_odd']
    df['implied_prob_draw'] = 1 / df['draw_odd']
    df['implied_prob_away_win'] = 1 / df['away_odd']
    total_1x2 = df['implied_prob_home_win'] + df['implied_prob_draw'] + df['implied_prob_away_win']
    df['norm_home_win'] = df['implied_prob_home_win'] / total_1x2
    df['norm_draw'] = df['implied_prob_draw'] / total_1x2
    df['norm_away_win'] = df['implied_prob_away_win'] / total_1x2
    df['home_cap_abs'] = df['home_cap'].abs()
    df['handicap_favoured_home'] = (df['home_cap'] < 0).astype(int)
    for cap in [2.25, 2.5, 2.75, 3.0, 3.25, 3.5]:
        df[f'cap_{cap}'] = (np.isclose(df['over_under_cap'], cap)).astype(int)
    df['over_juice'] = df['over_odd'] * df['implied_prob_over']
    df['under_juice'] = df['under_odd'] * df['implied_prob_under']
    df['prob_over_minus_50'] = df['implied_prob_over'] - 0.5
    df['home_away_prob_diff'] = df['norm_home_win'] - df['norm_away_win']
    df['cap_adjusted'] = df['over_under_cap'] + (df['over_under_diff'] * 5)
    return df

def add_historical_stats(df_in, cutoff_time=None):
    df = df_in.copy()
    df = df.sort_values('start_time').reset_index(drop=True)
    if cutoff_time is not None:
        df = df[df['start_time'] < cutoff_time]
    home_avg_scored, home_avg_conceded = [], []
    away_avg_scored, away_avg_conceded = [], []
    for i, row in df.iterrows():
        past = df.iloc[:i]
        if len(past) < 3:
            home_avg_scored.append(np.nan); home_avg_conceded.append(np.nan)
            away_avg_scored.append(np.nan); away_avg_conceded.append(np.nan)
            continue
        hg = past[(past['home_id'] == row['home_id']) | (past['away_id'] == row['home_id'])]
        if len(hg) > 0:
            h_scored = hg.apply(lambda r: r['home_ft_score'] if r['home_id'] == row['home_id'] else r['away_ft_score'], axis=1).mean()
            h_conceded = hg.apply(lambda r: r['away_ft_score'] if r['home_id'] == row['home_id'] else r['home_ft_score'], axis=1).mean()
        else:
            h_scored = h_conceded = np.nan
        ag = past[(past['home_id'] == row['away_id']) | (past['away_id'] == row['away_id'])]
        if len(ag) > 0:
            a_scored = ag.apply(lambda r: r['home_ft_score'] if r['home_id'] == row['away_id'] else r['away_ft_score'], axis=1).mean()
            a_conceded = ag.apply(lambda r: r['away_ft_score'] if r['home_id'] == row['away_id'] else r['home_ft_score'], axis=1).mean()
        else:
            a_scored = a_conceded = np.nan
        home_avg_scored.append(h_scored); home_avg_conceded.append(h_conceded)
        away_avg_scored.append(a_scored); away_avg_conceded.append(a_conceded)
    df['home_avg_scored'] = home_avg_scored
    df['home_avg_conceded'] = home_avg_conceded
    df['away_avg_scored'] = away_avg_scored
    df['away_avg_conceded'] = away_avg_conceded
    return df

def fetch_event_odds(event_id):
    conn = pymysql.connect(
        host='10.18.0.30', port=3306, user='root',
        password='QazWsxEdc$@3649', database='mslot', charset='utf8mb4'
    )
    query = """
    SELECT e.event_id, e.start_time, e.home_id, e.away_id,
           ht.name AS home_team, at.name AS away_team,
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
    return df

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
    # Load model data
    with open(MODEL_PATH, 'rb') as f:
        model_data = pickle.load(f)
    
    results = model_data['results']
    feature_cols = model_data['feature_cols']
    feature_cols_base = model_data['feature_cols_base']
    hist_cols = model_data['hist_cols']
    
    # Fetch event data
    event_df = fetch_event_odds(event_id)
    if len(event_df) == 0:
        return {'error': f'Event {event_id} not found'}
    
    row = event_df.iloc[0]
    event_time = pd.to_datetime(row['start_time'])
    
    # Determine season and window
    season = get_season(event_time)
    window_label = get_window_label(event_time)
    season_start_year = int(season[:4])
    if window_label is not None:
        if window_label.startswith(f"{season_start_year}-08"):
            window_season = f"{season_start_year}-{season_start_year+1} / Aug-Oct"
        elif window_label.startswith(f"{season_start_year}-11") or window_label.startswith(f"{season_start_year+1}-01"):
            window_season = f"{season_start_year}-{season_start_year+1} / Nov-Jan"
        elif window_label.startswith(f"{season_start_year}-02"):
            window_season = f"{season_start_year}-{season_start_year+1} / Feb-Apr"
        elif window_label.startswith(f"{season_start_year}-05"):
            window_season = f"{season_start_year}-{season_start_year+1} / May-Jul"
        else:
            window_season = None
    else:
        window_season = None
    
    # Find matching result
    result = None
    for r in results:
        if r['window'] == window_season:
            result = r
            break
    
    if result is None:
        return {
            'error': f'No model for window {window_season}',
            'event_id': event_id,
            'season': season,
            'window': window_season,
            'available_windows': [r['window'] for r in results]
        }
    
    # Build features for this event
    feat_df = build_features(event_df)
    feat_df['season'] = [season]
    feat_df['window_label'] = [window_label]
    feat_df['window_season'] = [window_season]
    feat_df['total_goals'] = [0]  # placeholder
    feat_df['over'] = [0]  # placeholder
    
    # Add historical stats using all completed games before this event
    conn = pymysql.connect(
        host='10.18.0.30', port=3306, user='root',
        password='QazWsxEdc$@3649', database='mslot', charset='utf8mb4'
    )
    all_query = """
    SELECT e.event_id, e.start_time, e.home_id, e.away_id,
           e.home_ft_score, e.away_ft_score
    FROM fb_event e
    WHERE e.event_type_id = 'd68b1ec8447141d0869a46d838c8f5ab'
    AND NOW() - INTERVAL 3 HOUR > e.start_time
    AND e.home_ft_score IS NOT NULL
    ORDER BY e.start_time
    """
    all_df = pd.read_sql(all_query, conn)
    conn.close()
    all_df['start_time'] = pd.to_datetime(all_df['start_time'])
    all_df['total_goals'] = all_df['home_ft_score'] + all_df['away_ft_score']
    
    # Add historical stats to event
    past = all_df[all_df['start_time'] < event_time]
    if len(past) >= 3:
        # Home team
        hg = past[(past['home_id'] == row['home_id']) | (past['away_id'] == row['home_id'])]
        if len(hg) > 0:
            feat_df['home_avg_scored'] = hg.apply(
                lambda r: r['home_ft_score'] if r['home_id'] == row['home_id'] else r['away_ft_score'], axis=1).mean()
            feat_df['home_avg_conceded'] = hg.apply(
                lambda r: r['away_ft_score'] if r['home_id'] == row['home_id'] else r['home_ft_score'], axis=1).mean()
        else:
            feat_df['home_avg_scored'] = 1.5; feat_df['home_avg_conceded'] = 1.5
        # Away team
        ag = past[(past['home_id'] == row['away_id']) | (past['away_id'] == row['away_id'])]
        if len(ag) > 0:
            feat_df['away_avg_scored'] = ag.apply(
                lambda r: r['home_ft_score'] if r['home_id'] == row['away_id'] else r['away_ft_score'], axis=1).mean()
            feat_df['away_avg_conceded'] = ag.apply(
                lambda r: r['away_ft_score'] if r['home_id'] == row['away_id'] else r['home_ft_score'], axis=1).mean()
        else:
            feat_df['away_avg_scored'] = 1.5; feat_df['away_avg_conceded'] = 1.5
    else:
        feat_df['home_avg_scored'] = 1.5; feat_df['home_avg_conceded'] = 1.5
        feat_df['away_avg_scored'] = 1.5; feat_df['away_avg_conceded'] = 1.5
    
    # Prepare features
    X = feat_df[feature_cols].fillna(1.5).values
    scaler = result['scaler']
    X_sc = scaler.transform(X)
    
    model = result['model_obj']
    threshold = result['threshold']
    
    proba = model.predict_proba(X_sc)[0, 1]
    prediction = 'OVER' if proba >= threshold else 'UNDER'
    
    return {
        'event_id': event_id,
        'home_team': row['home_team'],
        'away_team': row['away_team'],
        'start_time': str(event_time),
        'prediction': prediction,
        'probability': float(proba),
        'threshold': float(threshold),
        'model': result['model'],
        'window': window_season,
        'over_under_cap': float(row['over_under_cap']),
        'over_odd': float(row['over_odd']),
        'under_odd': float(row['under_odd']),
        'features': {
            'implied_prob_over': float(row['over_odd']) if False else float(feat_df['implied_prob_over'].values[0]),
            'implied_prob_under': float(feat_df['implied_prob_under'].values[0]),
            'over_under_cap': float(row['over_under_cap']),
            'home_cap': float(row['home_cap']),
            'home_avg_scored': float(feat_df['home_avg_scored'].values[0]),
            'away_avg_scored': float(feat_df['away_avg_scored'].values[0]),
        },
        'model_info': f"England League Trophy Combined Over/Under Model | Window: {window_season} | Model: {result['model']} | Threshold: {threshold:.2f} | Test Accuracy: {result['test_accuracy']:.4f} | Test ROI: {result['roi']:.2f}%"
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python england_league_trophy_predict.py <event_id>")
        sys.exit(1)
    result = predict(sys.argv[1])
    print(result)
