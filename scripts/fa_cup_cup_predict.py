#!/usr/bin/env python3
"""
England FA Cup Over/Under 預測腳本
用法: python fa_cup_cup_predict.py <event_id>
"""

import sys
import pickle
import pandas as pd
import numpy as np

MODEL_PATH = '/root/.openclaw/workspace/projects/football-analysis/models/fa_cup_combined_model.pkl'

def load_model():
    with open(MODEL_PATH, 'rb') as f:
        return pickle.load(f)

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
    import pymysql
    
    artifacts = load_model()
    model = artifacts['model']
    scaler = artifacts['scaler']
    threshold = artifacts['threshold']
    feature_cols = artifacts['feature_cols']
    fill_value = artifacts['fill_value']
    
    # Fetch event data
    conn = pymysql.connect(
        host='10.18.0.30', port=3306, user='root',
        password='QazWsxEdc$@3649', database='mslot', charset='utf8mb4'
    )
    q = """
    SELECT
        e.event_id, e.start_time, e.home_id, e.away_id,
        ht.name as home_team, at.name as away_team,
        ou.over_odd, ou.over_under_cap, ou.under_odd,
        wo.home_odd as win_home, wo.draw_odd as win_draw, wo.away_odd as win_away,
        ho.home_cap as hcap, ho.home_odd as hcap_home_odd, ho.away_odd as hcap_away_odd
    FROM fb_event e
    JOIN fb_team ht ON e.home_id = ht.team_id
    JOIN fb_team at ON e.away_id = at.team_id
    LEFT JOIN (
        SELECT * FROM (SELECT o.*, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY created_at DESC) as rn FROM fb_over_under_odd o) sub WHERE rn = 1
    ) ou ON e.event_id = ou.event_id
    LEFT JOIN (
        SELECT * FROM (SELECT w.*, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY created_at DESC) as rn FROM fb_win_odd w) sub WHERE rn = 1
    ) wo ON e.event_id = wo.event_id
    LEFT JOIN (
        SELECT * FROM (SELECT h.*, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY created_at DESC) as rn FROM fb_handicap_odd h) sub WHERE rn = 1
    ) ho ON e.event_id = ho.event_id
    WHERE e.event_id = %s
    """
    df = pd.read_sql(q, conn, params=(event_id,), index_col='event_id')
    conn.close()
    
    if df.empty:
        return {'error': f'No event found with id: {event_id}'}
    
    row = df.iloc[0]
    
    # Build features
    op = 1.0 / row['over_odd'] if row['over_odd'] > 0 else 0.5
    up = 1.0 / row['under_odd'] if row['under_odd'] > 0 else 0.5
    wp = 1.0 / row['win_home'] if row['win_home'] > 0 else 0.33
    dp = 1.0 / row['win_draw'] if row['win_draw'] > 0 else 0.33
    ap = 1.0 / row['win_away'] if row['win_away'] > 0 else 0.33
    tot_p = op + up
    opn = op / tot_p if tot_p > 0 else 0.5
    cap = row['over_under_cap']
    home_prob = wp / (wp + dp + ap + 1e-6)
    away_prob = ap / (wp + dp + ap + 1e-6)
    
    feat_dict = {
        'over_odd': row['over_odd'],
        'under_odd': row['under_odd'],
        'over_under_cap': cap,
        'win_home': row['win_home'],
        'win_draw': row['win_draw'],
        'win_away': row['win_away'],
        'over_prob_norm': opn,
        'under_prob_norm': 1.0 - opn,
        'over_prob_raw': op,
        'under_prob_raw': up,
        'over_juice': row['over_odd'] - 1.0,
        'under_juice': row['under_odd'] - 1.0,
        'home_prob': home_prob,
        'away_prob': away_prob,
        'cap_200': float(abs(cap - 2.00) < 0.01),
        'cap_225': float(abs(cap - 2.25) < 0.01),
        'cap_250': float(abs(cap - 2.50) < 0.01),
        'cap_275': float(abs(cap - 2.75) < 0.01),
        'cap_300': float(abs(cap - 3.00) < 0.01),
        'cap_325': float(abs(cap - 3.25) < 0.01),
        'cap_350': float(abs(cap - 3.50) < 0.01),
        'cap_dev': cap - 2.5,
        'home_avg_scored': 2.0,
        'home_avg_conceded': 2.0,
        'away_avg_scored': 2.0,
        'away_avg_conceded': 2.0,
        'expected_total': 4.0,
        'market_vs_expectation': opn - 0.5,
        'cap_vs_exp': cap - 4.0,
        'home_attack_rel': 0.8,
        'away_attack_rel': 0.8,
        'hcap': row['hcap'] if pd.notna(row['hcap']) else 0.0,
        'hcap_home_odd': row['hcap_home_odd'] if pd.notna(row['hcap_home_odd']) else 1.95,
        'hcap_away_odd': row['hcap_away_odd'] if pd.notna(row['hcap_away_odd']) else 1.95,
    }
    
    feat_df = pd.DataFrame([feat_dict], columns=feature_cols)
    feat_df = feat_df.fillna(fill_value)
    feat_s = scaler.transform(feat_df)
    
    prob_over = float(model.predict_proba(feat_s)[0, 1])
    prediction = 'OVER' if prob_over > threshold else 'UNDER'
    
    return {
        'event_id': event_id,
        'home_team': str(row['home_team']),
        'away_team': str(row['away_team']),
        'prediction': prediction,
        'probability': prob_over,
        'threshold': threshold,
        'cap': float(cap),
        'over_odd': float(row['over_odd']),
        'under_odd': float(row['under_odd']),
        'features': feat_dict,
        'model_info': 'England FA Cup Combined Over/Under GB Model'
    }

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("用法: python fa_cup_cup_predict.py <event_id>")
        sys.exit(1)
    result = predict(sys.argv[1])
    import json
    print(json.dumps(result, indent=2, default=str))
