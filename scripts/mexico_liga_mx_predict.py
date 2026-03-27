#!/usr/bin/env python3
"""
Mexico Liga MX Over/Under 預測腳本 (Combined Model)
用法: python mexico_liga_mx_predict.py <event_id>
"""

import sys
import pickle
import pandas as pd
import numpy as np

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
            'model_info': str,      # 模型描述
            'window': str,         # 比賽所屬窗口
            'recommended_bet': str
        }
    """
    import pymysql
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    
    # Load window models
    with open('/root/.openclaw/workspace/projects/verified_models/models/mexico_liga_mx_window_models.pkl', 'rb') as f:
        window_models = pickle.load(f)
    
    # Database connection
    conn = pymysql.connect(
        host='10.18.0.30', port=3306, user='root',
        password='QazWsxEdc$@3649', database='mslot', charset='utf8mb4'
    )
    
    # Fetch event data
    query = """
    SELECT 
        e.event_id, e.start_time,
        ht.name AS home_team, at.name AS away_team,
        e.home_id, e.away_id,
        wo.home_odd, wo.draw_odd, wo.away_odd,
        ou.over_odd, ou.over_under_cap, ou.under_odd,
        ho.home_cap AS handicap_cap,
        ho.home_odd AS home_handicap_odd,
        ho.away_odd AS away_handicap_odd
    FROM fb_event e
    LEFT JOIN fb_team ht ON e.home_id = ht.team_id
    LEFT JOIN fb_team at ON e.away_id = at.team_id
    INNER JOIN (
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
    
    df_event = pd.read_sql(query, conn, params=(event_id,))
    conn.close()
    
    if len(df_event) == 0:
        return {'error': 'Event not found'}
    
    row = df_event.iloc[0]
    
    # Determine window label
    dt = row['start_time']
    year = dt.year
    month = dt.month
    
    if month >= 7:
        season = f"{year}-{year+1}"
        if month in [7, 8, 9]:
            window = "Jul-Sep"
        elif month in [10, 11, 12]:
            window = "Oct-Dec"
    else:
        season = f"{year-1}-{year}"
        if month in [1, 2, 3]:
            window = "Jan-Mar"
        elif month in [4, 5, 6]:
            window = "Apr-Jun"
    
    window_label = f"{season} / {window}"
    
    # Check if we have a model for this window
    if window_label not in window_models:
        return {'error': f'No model for window {window_label}'}
    
    model_info = window_models[window_label]
    model = model_info['model']
    scaler = model_info['scaler']
    threshold = model_info['threshold']
    feature_cols = model_info['feature_cols']
    model_name = model_info['model_name']
    
    # Build features
    df = pd.DataFrame([row])
    df['implied_over_prob'] = 1 / df['over_odd']
    df['implied_under_prob'] = 1 / df['under_odd']
    df['total_implied'] = df['implied_over_prob'] + df['implied_under_prob']
    df['fair_over_prob'] = df['implied_over_prob'] / df['total_implied']
    df['imp_home_prob'] = 1 / df['home_odd']
    df['imp_away_prob'] = 1 / df['away_odd']
    df['imp_draw_prob'] = 1 / df['draw_odd']
    df['total_win'] = df['imp_home_prob'] + df['imp_draw_prob'] + df['imp_away_prob']
    df['fair_home_prob'] = df['imp_home_prob'] / df['total_win']
    df['fair_away_prob'] = df['imp_away_prob'] / df['total_win']
    df['fair_draw_prob'] = df['imp_draw_prob'] / df['total_win']
    df['odds_ratio'] = df['over_odd'] / df['under_odd']
    df['log_odds_ratio'] = np.log(df['odds_ratio'] + 0.001)
    df['home_away_ratio'] = df['home_odd'] / df['away_odd']
    for cap in [2.0, 2.5, 2.75, 3.0, 3.5]:
        df[f'cap_{cap}'] = (df['over_under_cap'] == cap).astype(int)
    df['cap_distance'] = abs(df['over_under_cap'] - 2.5)
    df['cap_above_2_5'] = (df['over_under_cap'] > 2.5).astype(int)
    df['home_handicap_odd_adj'] = df['home_handicap_odd'] * df['handicap_cap']
    df['handicap_home_fav'] = (df['handicap_cap'] < 0).astype(int)
    
    # For historical features, use defaults (no historical data available at prediction time)
    df['home_avg_goals'] = 1.8
    df['home_avg_conceded'] = 1.3
    df['away_avg_goals'] = 1.3
    df['away_avg_conceded'] = 1.8
    df['home_over_rate'] = 0.5
    df['away_over_rate'] = 0.5
    df['expected_total'] = df['home_avg_goals'] + df['away_avg_goals']
    df['expected_diff'] = df['home_avg_goals'] - df['away_avg_goals']
    df['over_expectation'] = df['expected_total'] - df['over_under_cap']
    df['goals_sum_avg'] = df['home_avg_goals'] + df['away_avg_goals']
    df['goals_diff_avg'] = df['home_avg_goals'] - df['away_avg_goals']
    df['total_defense_avg'] = df['home_avg_conceded'] + df['away_avg_conceded']
    df['avg_over_rate'] = (df['home_over_rate'] + df['away_over_rate']) / 2
    df['over_rate_diff'] = df['home_over_rate'] - df['away_over_rate']
    df['cap_x_fair_over'] = df['over_under_cap'] * df['fair_over_prob']
    df['cap_x_home'] = df['over_under_cap'] * df['fair_home_prob']
    df['over_juice'] = df['over_odd'] * df['fair_over_prob']
    df['under_juice'] = df['under_odd'] * (1 - df['fair_over_prob'])
    df = df.fillna(0).replace([np.inf, -np.inf], 0)
    
    X = df[feature_cols].values
    X_scaled = scaler.transform(X)
    
    prob = model.predict_proba(X_scaled)[0][1]
    prediction = 'OVER' if prob >= threshold else 'UNDER'
    
    # Recommended bet
    confidence = abs(prob - 0.5) * 2  # 0 to 1 scale
    if confidence > 0.3:
        recommended = prediction
    else:
        recommended = 'SKIP'
    
    return {
        'event_id': event_id,
        'home_team': row['home_team'],
        'away_team': row['away_team'],
        'start_time': str(row['start_time']),
        'window': window_label,
        'prediction': prediction,
        'probability': float(prob),
        'threshold': float(threshold),
        'model': model_name,
        'recommended_bet': recommended,
        'confidence': float(confidence),
        'features': {
            'over_odd': float(row['over_odd']),
            'under_odd': float(row['under_odd']),
            'over_under_cap': float(row['over_under_cap']),
            'home_odd': float(row['home_odd']),
            'away_odd': float(row['away_odd']),
            'fair_over_prob': float(df['fair_over_prob'].values[0])
        }
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python mexico_liga_mx_predict.py <event_id>")
        sys.exit(1)
    result = predict(sys.argv[1])
    import json
    print(json.dumps(result, indent=2, default=str))
