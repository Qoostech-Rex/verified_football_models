#!/usr/bin/env python3
"""
Main Prediction Dispatcher
=========================
Takes an event_id and automatically routes to the correct prediction script.

Usage:
    python main.py <event_id>
    python main.py <event_id> --dry-run  # Just show which script would be used

If no matching script is found, returns None.
"""

import sys
import subprocess
import argparse
import pymysql
import pandas as pd

# Mapping of event_type_id -> (league_name, script_name)
EVENT_TYPE_MAP = {
    'df1451df9b5b450aab4659bebe8c58fa': ('德國甲組聯賽', 'bundesliga_predict.py'),
    'e5bd2126796b4cc296caf3199ebd39f8': ('世界盃非洲區外圍賽', 'wc_africa_qualifiers_predict.py'),
    '76568d413f7b45b580b1a9c5f86553a5': ('英格蘭足總盃', 'fa_cup_cup_predict.py'),
    'd68b1ec8447141d0869a46d838c8f5ab': ('英格蘭聯賽錦標賽', 'england_league_trophy_predict.py'),
    '71971bdaa7f84213830d98a1a5fdac0e': ('墨西哥甲組聯賽', 'mexico_liga_mx_predict.py'),
    '0ffdf60cd8d84b75a91b45db09c32370': ('奧地利甲組聯賽', 'austria_bundesliga_predict.py'),
    'bb9368b159a3436a9f7ce8b137aee943': ('美國國家女子聯賽', 'usa_nwsl_predict.py'),
    '1b3aab24b09e4178aa341fc595194729': ('南韓職業聯賽', 'south_korea_predict.py'),
    'aa68938630354e84a2ca48d5ea252091': ('日本職業聯賽', 'japan_professional_league_predict.py'),
    'e125b5cab22a4440a1e8ec51234e331e': ('卡塔爾超級聯賽', 'qatar_predict.py'),
    'd80510661207420e86d9064e51a8bc7d': ('越南職業聯賽', 'vietnam_vleague_predict.py'),
    '5812b158e546477ab04c0d85b56772b3': ('U21歐洲國家盃外圍賽', 'u21_euro_qualifiers_predict.py'),
    'e9fbca5f40f44ac8a772b0dfeb8064e8': ('土耳其超級聯賽', 'turkey_combined_predict.py'),
    '30281baf2d1444fd91d421576d3cc16d': ('塞爾維亞超級聯賽', 'serbia_super_liga_predict.py'),
}

SCRIPT_DIR = '/root/.openclaw/workspace/projects/verified_models/scripts'

DB_CONFIG = {
    'host': '10.18.0.30',
    'port': 3306,
    'user': 'root',
    'password': 'QazWsxEdc$@3649',
    'database': 'mslot',
    'charset': 'utf8mb4'
}


def get_event_info(event_id: str) -> dict:
    """Query database to get event_type_id and event details for a given event_id."""
    conn = pymysql.connect(**DB_CONFIG)
    
    query = """
    SELECT 
        e.event_id,
        e.event_type_id,
        e.start_time,
        ht.name AS home_team,
        at.name AS away_team,
        et.name AS league_name
    FROM fb_event e
    JOIN fb_event_type et ON e.event_type_id = et.event_type_id
    LEFT JOIN fb_team ht ON e.home_id = ht.team_id
    LEFT JOIN fb_team at ON e.away_id = at.team_id
    WHERE e.event_id = %s
    """
    
    df = pd.read_sql(query, conn, params=(event_id,))
    conn.close()
    
    if df.empty:
        return None
    
    return df.iloc[0].to_dict()


def find_script(event_type_id: str) -> tuple:
    """
    Find the corresponding script for a given event_type_id.
    Returns (league_name, script_path) or None if not found.
    """
    if event_type_id in EVENT_TYPE_MAP:
        league_name, script_name = EVENT_TYPE_MAP[event_type_id]
        script_path = f"{SCRIPT_DIR}/{script_name}"
        return league_name, script_path
    return None


def main():
    parser = argparse.ArgumentParser(description='Football O/U Prediction Dispatcher')
    parser.add_argument('event_id', help='Event ID to predict')
    parser.add_argument('--dry-run', action='store_true', help='Show which script would be used')
    args = parser.parse_args()
    
    event_id = args.event_id
    
    # Get event info from database
    try:
        event_info = get_event_info(event_id)
    except Exception as e:
        print(f"Error querying database: {e}")
        return None
    
    if event_info is None:
        print(f"Event {event_id} not found in database")
        return None
    
    event_type_id = event_info['event_type_id']
    
    print(f"Event: {event_info['home_team']} vs {event_info['away_team']}")
    print(f"League: {event_info['league_name']}")
    
    # Find matching script
    result = find_script(event_type_id)
    
    if result is None:
        print(f"No prediction script found for this league ({event_info['league_name']})")
        return None
    
    league_name, script_path = result
    
    if args.dry_run:
        print(f"Matched League: {league_name}")
        print(f"Script: {script_path}")
        print(f"Command: python {script_path} {event_id}")
        return
    
    # Run the prediction script
    print(f"\nRunning {league_name} prediction...")
    result = subprocess.run(
        ['python', script_path, event_id],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        # Filter out UserWarnings which are just pandas compatibility warnings
        stderr_lines = [line for line in result.stderr.split('\n') if 'UserWarning' not in line]
        if stderr_lines:
            print('\n'.join(stderr_lines), file=sys.stderr)


if __name__ == '__main__':
    main()
