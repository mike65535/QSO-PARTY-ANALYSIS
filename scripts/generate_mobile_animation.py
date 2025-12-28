#!/usr/bin/env python3
import sys
import os
import sqlite3
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.map_generator import NYMapGenerator

def load_mobile_data():
    """Load mobile QSO data from database"""
    # Connect to the local database
    conn = sqlite3.connect('../data/contest_qsos.db')
    
    # Get mobile stations and their QSOs
    mobile_data = {}
    
    # Query for mobile QSOs (stations with /M suffix or known mobiles)
    cursor = conn.execute('''
        SELECT station_call, rx_county, datetime
        FROM qsos 
        WHERE (station_call LIKE '%/M' OR station_call IN ('AB1BL', 'K2A', 'K2Q', 'K2V', 'KQ2R', 'KV2X', 'N1GBE', 'N2B', 'N2CU', 'N2T', 'W1WV', 'WI2M', 'WT2X'))
        AND rx_county IS NOT NULL
        ORDER BY datetime
    ''')
    
    for row in cursor:
        call, county, timestamp = row
        if call not in mobile_data:
            mobile_data[call] = []
        
        mobile_data[call].append({
            'timestamp': timestamp,
            'county': county
        })
    
    conn.close()
    return mobile_data

if __name__ == "__main__":
    print("Loading mobile data...")
    mobile_data = load_mobile_data()
    
    print("Generating mobile animation map...")
    generator = NYMapGenerator('../data/ny-counties-boundaries.json', '../data/ny_county_names.json')
    generator.generate_mobile_animation_html('../outputs/mobile_animation.html', mobile_data, "NYQP 2025 Mobile Animation")
    
    print(f"Generated mobile animation with {len(mobile_data)} mobile stations")
    for call, qsos in mobile_data.items():
        print(f"  {call}: {len(qsos)} QSOs")
