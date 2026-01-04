#!/usr/bin/env python3

import sqlite3
import json
from datetime import datetime, timedelta

def generate_state_qso_animation():
    """Generate state-level QSO animation data"""
    
    # Connect to database
    conn = sqlite3.connect('data/contest_qsos.db')
    cursor = conn.cursor()
    
    # Get all QSOs with state information - filter to contest timeframe
    query = """
    SELECT 
        datetime,
        station_call,
        tx_county,
        CASE 
            WHEN tx_county IN (
                'ALB', 'ALL', 'BRO', 'CAT', 'CAY', 'CHA', 'CHE', 'CLI', 'COL', 'COR', 'DEL', 'DUT', 'ERI', 'ESS', 'FRA', 'FUL', 'GEN', 'GRE', 'HAM', 'HER', 'JEF', 'KIN', 'LEW', 'LIV', 'MAD', 'MON', 'NAS', 'NIA', 'ONE', 'ONO', 'ONT', 'ORA', 'ORL', 'OSW', 'OTS', 'PUT', 'QUE', 'REN', 'RIC', 'ROC', 'SCH', 'SCO', 'SEN', 'STL', 'STU', 'SUF', 'SUL', 'TIO', 'TOM', 'ULS', 'WAR', 'WAS', 'WAY', 'WES', 'WYO', 'YAT'
            ) THEN 'NY'
            ELSE SUBSTR(tx_county, -2)
        END as state
    FROM qsos 
    WHERE tx_county IS NOT NULL AND tx_county != ''
        AND datetime >= '2025-10-18 14:00:00' AND datetime <= '2025-10-19 02:00:00'
    ORDER BY datetime
    """
    
    cursor.execute(query)
    qsos = cursor.fetchall()
    
    print(f"Processing {len(qsos)} QSOs for state animation...")
    
    # Contest start time
    start_time = datetime(2025, 10, 18, 14, 0, 0)
    
    # Group QSOs by 5-minute intervals and state
    state_data = {}
    
    for qso_time_str, station, county, state in qsos:
        qso_time = datetime.strptime(qso_time_str, '%Y-%m-%d %H:%M:%S')
        
        # Calculate 1-minute interval
        minutes_elapsed = int((qso_time - start_time).total_seconds() / 60) * 1
        interval_time = start_time + timedelta(minutes=minutes_elapsed)
        time_key = interval_time.strftime('%H:%M')
        
        if time_key not in state_data:
            state_data[time_key] = {}
        
        if state not in state_data[time_key]:
            state_data[time_key][state] = 0
        
        state_data[time_key][state] += 1
    
    # Convert to cumulative counts and create animation frames
    animation_data = []
    cumulative_counts = {}
    
    # Create ALL 1-minute intervals from 14:00 to 02:00 (next day)
    all_intervals = []
    current_time = start_time
    end_time = datetime(2025, 10, 19, 2, 0, 0)  # Contest ends at 02:00Z next day
    
    while current_time < end_time:
        # Store both time and date info
        time_key = current_time.strftime('%H:%M')
        date_key = current_time.strftime('%Y-%m-%d')
        all_intervals.append({
            'time': time_key,
            'date': date_key,
            'datetime': current_time
        })
        current_time += timedelta(minutes=1)
    
    # Process each interval
    for interval in all_intervals:
        time_key = interval['time']
        
        # For the very first frame (14:00), start with empty states
        if interval['datetime'] == start_time:
            frame = {
                'time': time_key,
                'date': interval['date'],
                'states': {}
            }
            animation_data.append(frame)
            continue
            
        # Update cumulative counts if there's data for this interval
        if time_key in state_data:
            for state, count in state_data[time_key].items():
                if state not in cumulative_counts:
                    cumulative_counts[state] = 0
                cumulative_counts[state] += count
        
        # Create frame data (even if no new QSOs in this interval)
        frame = {
            'time': time_key,
            'date': interval['date'],
            'states': dict(cumulative_counts)
        }
        animation_data.append(frame)
    
    # Save animation data
    output_data = {
        'frames': animation_data,
        'total_qsos': len(qsos),
        'contest_start': '14:00',
        'contest_end': '02:00'
    }
    
    with open('outputs/state_qso_animation_data.json', 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"State animation data saved: {len(animation_data)} frames")
    print(f"States with activity: {len(cumulative_counts)}")
    
    conn.close()
    return output_data

if __name__ == "__main__":
    generate_state_qso_animation()
