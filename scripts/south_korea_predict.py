#!/usr/bin/env python3
"""
South Korea WK-League Combined Over/Under 預測腳本
用法: python south_korea_wk_league_predict.py <event_id>
"""

import sys
import pickle
import os

WORK_DIR = '/root/.openclaw/workspace/projects/verified_models'
MODEL_PATH = f'{WORK_DIR}/models/south_korea_wk_league_combined_model.pkl'

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
            'model_info': str
        }
    """
    if not os.path.exists(MODEL_PATH):
        return {'error': f'Model not found at {MODEL_PATH}'}
    
    with open(MODEL_PATH, 'rb') as f:
        model_data = pickle.load(f)
    
    # Fetch event data from database
    import pymysql
    conn = pymysql.connect(
        host='10.18.0.30', port=3306, user='root',
        password='QazWsxEdc$@3649', database='mslot', charset='utf8mb4')
    
    query = '''
        SELECT 
            e.start_time,
            ht.name AS home_team,
            at.name AS away_team,
            wo.home_odd, wo.draw_odd, wo.away_odd,
            ou.over_odd, ou.over_under_cap, ou.under_odd,
            ho.home_cap, ho.home_odd AS home_handicap_odd, ho.away_odd AS away_handicap_odd
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
    '''
    
    df = __import__('pandas').read_sql(query, conn, params=(event_id,))
    conn.close()
    
    if len(df) == 0:
        return {'error': f'Event {event_id} not found'}
    
    row = df.iloc[0]
    
    # Get historical features (need all historical events for same league)
    all_query = '''
        SELECT 
            e.event_id, e.start_time,
            ht.name AS home_team, at.name AS away_team,
            e.home_ft_score, e.away_ft_score,
            ou.over_odd, ou.over_under_cap
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
        WHERE e.event_type_id = '9a68bdbe5a70460fb0704a3d22a6a602'
        AND e.start_time <= %s
        ORDER BY e.start_time ASC
    '''
    
    hist_df = __import__('pandas').read_sql(all_query, conn if False else None, params=(row['start_time'],))
    if conn:
        conn.close()
    
    # Build features incrementally (same as training)
    import numpy as np
    
    team_games = {}
    rows = []
    
    for _, hrow in hist_df.iterrows():
        ht = hrow['home_team']
        at = hrow['away_team']
        htg = team_games.get(ht, [])
        atg = team_games.get(at, [])
        
        def av(g, ih, ix):
            v = [g[i][ix] for i in range(len(g)) if g[i][2] == ih]
            return float(np.mean(v)) if v else 1.8
        
        def ovr(g, n=5):
            r = g[-n:]
            return float(sum(1 for g in r if g[0] > g[3]) / max(len(r), 1)) if r else 0.5
        
        cap = float(hrow['over_under_cap'])
        oo = float(hrow['over_odd'])
        uo = float(1.0)  # placeholder
        ho_odds = float(1.9)
        ao_odds = float(1.9)
        
        # Get win odds if available from history
        win_query = f'''
            SELECT home_odd, draw_odd, away_odd FROM fb_win_odd
            WHERE event_id = %s ORDER BY created_at DESC LIMIT 1
        '''
        
        rows.append({
            'f_cap': cap,
            'f_over_odd': oo,
            'f_under_odd': uo,
            'f_home_odd': ho_odds,
            'f_draw_odd': 3.0,
            'f_away_odd': ao_odds,
            'f_ou_ratio': oo / uo if uo > 0 else 1.0,
            'f_ha_ratio': 1.0,
            'f_imp_over': 1.0 / oo if oo > 0 else 0.5,
            'f_imp_home': 0.5,
            'f_ht_h_sc': av(htg, 1, 0),
            'f_ht_a_sc': av(htg, 0, 0),
            'f_at_h_sc': av(atg, 1, 0),
            'f_at_a_sc': av(atg, 0, 0),
            'f_ht_h_co': av(htg, 1, 1),
            'f_at_a_co': av(atg, 0, 1),
            'f_ht_ovr': ovr(htg),
            'f_at_ovr': ovr(atg),
            'f_cap_rel': cap - (av(htg, 1, 0) + av(atg, 0, 0)),
            'f_ht_total': av(htg, 1, 0) + av(htg, 1, 1),
            'f_at_total': av(atg, 0, 0) + av(atg, 0, 1),
        })
        
        if ht not in team_games:
            team_games[ht] = []
        if at not in team_games:
            team_games[at] = []
        team_games[ht].append((int(hrow['home_ft_score']), int(hrow['away_ft_score']), 1, cap, at))
        team_games[at].append((int(hrow['away_ft_score']), int(hrow['home_ft_score']), 0, cap, ht))
    
    # Build features for current event
    ht = row['home_team']
    at = row['away_team']
    htg = team_games.get(ht, [])
    atg = team_games.get(at, [])
    
    def av(g, ih, ix):
        v = [g[i][ix] for i in range(len(g)) if g[i][2] == ih]
        return float(np.mean(v)) if v else 1.8
    
    def ovr(g, n=5):
        r = g[-n:]
        return float(sum(1 for g in r if g[0] > g[3]) / max(len(r), 1)) if r else 0.5
    
    cap = float(row['over_under_cap'])
    oo = float(row['over_odd'])
    uo = float(row['under_odd'])
    ho_odds = float(row['home_odd'])
    ao_odds = float(row['away_odd'])
    draw_odds = float(row['draw_odd'])
    
    features = {
        'f_cap': cap,
        'f_over_odd': oo,
        'f_under_odd': uo,
        'f_home_odd': ho_odds,
        'f_draw_odd': draw_odds,
        'f_away_odd': ao_odds,
        'f_ou_ratio': oo / uo,
        'f_ha_ratio': ho_odds / ao_odds,
        'f_imp_over': 1.0 / oo,
        'f_imp_home': 1.0 / ho_odds,
        'f_ht_h_sc': av(htg, 1, 0),
        'f_ht_a_sc': av(htg, 0, 0),
        'f_at_h_sc': av(atg, 1, 0),
        'f_at_a_sc': av(atg, 0, 0),
        'f_ht_h_co': av(htg, 1, 1),
        'f_at_a_co': av(atg, 0, 1),
        'f_ht_ovr': ovr(htg),
        'f_at_ovr': ovr(atg),
        'f_cap_rel': cap - (av(htg, 1, 0) + av(atg, 0, 0)),
        'f_ht_total': av(htg, 1, 0) + av(htg, 1, 1),
        'f_at_total': av(atg, 0, 0) + av(atg, 0, 1),
    }
    
    # Get feature vector in correct order
    feature_cols = model_data['feature_cols']
    X = np.array([[features.get(c, 0.0) for c in feature_cols]], dtype=float)
    
    scaler = model_data['scaler']
    X_s = scaler.transform(X)
    
    prob = float(model_data['model'].predict_proba(X_s)[0, 1])
    thresh = float(model_data['threshold'])
    
    prediction = 'OVER' if prob >= thresh else 'UNDER'
    
    return {
        'event_id': event_id,
        'prediction': prediction,
        'probability': prob,
        'threshold': thresh,
        'features': {k: float(v) for k, v in features.items()},
        'model_info': f"South Korea WK-League Combined O/U Model (GB, threshold={thresh:.2f})"
    }


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('用法: python south_korea_wk_league_predict.py <event_id>')
        sys.exit(1)
    result = predict(sys.argv[1])
    print(result)
