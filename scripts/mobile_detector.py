#!/usr/bin/env python3
"""
Mobile Station Detector
Identifies mobile stations from QSO database and generates mobile stations table
"""

import sqlite3
import json
from typing import Dict, List, Set
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class MobileStation:
    """Mobile station metadata"""
    callsign: str
    total_qsos: int
    counties: List[str]
    first_qso: str  # ISO timestamp
    last_qso: str   # ISO timestamp
    icon: str
    is_active: bool


class MobileDetector:
    """Detects mobile stations from QSO database"""
    
    def __init__(self, 
                 min_counties: int = 2,
                 min_qsos: int = 10,
                 ny_counties: Set[str] = None):
        self.min_counties = min_counties
        self.min_qsos = min_qsos
        self.ny_counties = ny_counties or self._get_ny_counties()
        
        # Default icons for mobile stations
        self.default_icons = {
            'N2CU': '🚗', 'K2A': '🚙', 'N2T': '🚐', 'K2V': '🚕', 'K2Q': '🚓',
            'N1GBE': '🚑', 'WI2M': '🚒', 'W1WV': '🚚', 'N2B': '🚛', 'KQ2R': '🏎️',
            'KV2X': '🚜', 'WT2X': '🛻', 'AB1BL': '🚌'
        }
    
    def _get_ny_counties(self) -> Set[str]:
        """Get set of NY county abbreviations"""
        return {
            'ALD', 'ALL', 'BRO', 'CAT', 'CAY', 'CHA', 'CHE', 'CLI', 'COL', 'COR',
            'DEL', 'DUT', 'ERI', 'ESS', 'FRA', 'FUL', 'GEN', 'GRE', 'HAM', 'HER',
            'JEF', 'KIN', 'LEW', 'LIV', 'MAD', 'MON', 'NAS', 'NIA', 'ONE', 'ONO',
            'ORA', 'ORL', 'OSW', 'OTS', 'PUT', 'QUE', 'REN', 'RIC', 'ROC', 'SCH',
            'SCO', 'SEN', 'STL', 'STU', 'SUF', 'SUL', 'TIO', 'TOM', 'ULS', 'WAR',
            'WAS', 'WAY', 'WES', 'WYO', 'YAT'
        }
    
    def detect_mobiles(self, db_path: str) -> Dict[str, MobileStation]:
        """Detect NY mobile stations from database using metadata + pattern analysis"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First, get stations declared as MOBILE in metadata
        mobile_callsigns = set()
        try:
            # Try to access contest_meta.db
            meta_db_path = db_path.replace('contest_qsos.db', 'contest_meta.db')
            meta_conn = sqlite3.connect(meta_db_path)
            meta_cursor = meta_conn.cursor()
            
            # Get mobile stations using proper category fields
            meta_cursor.execute("""
                SELECT callsign, operator_category, power 
                FROM stations 
                WHERE station_type = 'MOBILE'
            """)
            
            mobile_metadata = {}
            for callsign, op_category, power in meta_cursor.fetchall():
                # Handle callsign variations (remove /M, /P suffixes for matching)
                base_call = callsign.split('/')[0]
                mobile_callsigns.add(base_call)
                mobile_metadata[base_call] = {
                    'full_call': callsign,
                    'operator_category': op_category,
                    'power': power
                }
            
            meta_conn.close()
            print(f"Found {len(mobile_callsigns)} stations declared as MOBILE in metadata")
            
            # Show valid categories found
            categories = set(m['operator_category'] for m in mobile_metadata.values() if m['operator_category'])
            powers = set(m['power'] for m in mobile_metadata.values() if m['power'])
            print(f"Mobile categories: {sorted(categories)}")
            print(f"Power levels: {sorted(powers)}")
            
        except Exception as e:
            print(f"Could not access metadata ({e}), falling back to pattern analysis only")
            mobile_callsigns = set()
            mobile_metadata = {}
        
        if not mobile_callsigns:
            print("No metadata available, falling back to pattern analysis only")
            mobile_callsigns = None
        
        # Now filter for NY operations using pattern analysis
        if mobile_callsigns:
            # Only analyze stations declared as mobile
            placeholders = ','.join('?' * len(mobile_callsigns))
            query = f"""
            SELECT 
                tx_call,
                COUNT(*) as total_qsos,
                COUNT(DISTINCT tx_county) as county_count,
                GROUP_CONCAT(DISTINCT tx_county) as counties,
                MIN(datetime) as first_qso,
                MAX(datetime) as last_qso
            FROM qsos 
            WHERE tx_call IN ({placeholders})
              AND tx_county IN ({','.join('?' * len(self.ny_counties))})
            GROUP BY tx_call
            HAVING county_count >= ? AND total_qsos >= ?
            ORDER BY tx_call
            """
            params = list(mobile_callsigns) + list(self.ny_counties) + [self.min_counties, self.min_qsos]
        else:
            # Fallback to original pattern analysis
            query = """
            SELECT 
                tx_call,
                COUNT(*) as total_qsos,
                COUNT(DISTINCT tx_county) as county_count,
                GROUP_CONCAT(DISTINCT tx_county) as counties,
                MIN(datetime) as first_qso,
                MAX(datetime) as last_qso
            FROM qsos 
            WHERE tx_county IN ({})
            GROUP BY tx_call
            HAVING county_count >= ? AND total_qsos >= ?
            ORDER BY tx_call
            """.format(','.join('?' * len(self.ny_counties)))
            params = list(self.ny_counties) + [self.min_counties, self.min_qsos]
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        mobiles = {}
        for row in rows:
            callsign, total_qsos, county_count, counties_str, first_qso, last_qso = row
            
            counties = sorted(counties_str.split(','))
            icon = self.default_icons.get(callsign, '📍')
            
            mobiles[callsign] = MobileStation(
                callsign=callsign,
                total_qsos=total_qsos,
                counties=counties,
                first_qso=first_qso,
                last_qso=last_qso,
                icon=icon,
                is_active=True
            )
        
        return mobiles
    
    def generate_qc_report(self, mobiles: Dict[str, MobileStation], output_path: str):
        """Generate QC report for NY mobile station detection"""
        lines = []
        lines.append("NY MOBILE STATION DETECTION QC REPORT")
        lines.append("=" * 50)
        lines.append(f"Detection criteria:")
        lines.append(f"  1. Declared as MOBILE in contest metadata")
        lines.append(f"  2. Operated from NY counties (minimum {self.min_counties} counties)")
        lines.append(f"  3. Minimum QSOs: {self.min_qsos}")
        lines.append(f"  NY counties considered: {len(self.ny_counties)}")
        lines.append("")
        lines.append(f"NY mobile stations detected: {len(mobiles)}")
        lines.append("")
        
        lines.append("-" * 80)
        lines.append(f"{'Callsign':<10} {'QSOs':<6} {'Counties':<4} {'County List':<30} {'Icon':<4}")
        lines.append("-" * 80)
        
        for callsign, mobile in sorted(mobiles.items()):
            county_list = ','.join(mobile.counties[:5])  # Show first 5
            if len(mobile.counties) > 5:
                county_list += f"... (+{len(mobile.counties)-5})"
            
            lines.append(f"{callsign:<10} {mobile.total_qsos:<6} {len(mobile.counties):<4} "
                        f"{county_list:<30} {mobile.icon:<4}")
        
        lines.append("-" * 80)
        lines.append("")
        
        # Activity timeline
        lines.append("ACTIVITY TIMELINE:")
        lines.append("")
        for callsign, mobile in sorted(mobiles.items()):
            lines.append(f"{callsign}: {mobile.first_qso} to {mobile.last_qso}")
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
    
    def save_table(self, mobiles: Dict[str, MobileStation], output_path: str):
        """Save mobile stations table as JSON"""
        # Convert to serializable format
        table = {callsign: asdict(mobile) for callsign, mobile in mobiles.items()}
        
        with open(output_path, 'w') as f:
            json.dump(table, f, indent=2)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Detect mobile stations from QSO database')
    parser.add_argument('--db', default='data/contest_qsos.db', help='Database path')
    parser.add_argument('--output', default='outputs/mobile_stations.json', help='Output JSON file')
    parser.add_argument('--verbose', action='store_true', help='Generate QC reports')
    parser.add_argument('--min-counties', type=int, default=2, help='Minimum counties for mobile detection')
    parser.add_argument('--min-qsos', type=int, default=10, help='Minimum QSOs for mobile detection')
    
    args = parser.parse_args()
    
    # Create output directory
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    
    # Detect mobile stations
    detector = MobileDetector(
        min_counties=args.min_counties,
        min_qsos=args.min_qsos
    )
    
    print(f"Detecting mobile stations from {args.db}...")
    mobiles = detector.detect_mobiles(args.db)
    print(f"Found {len(mobiles)} mobile stations")
    
    # Save table
    detector.save_table(mobiles, args.output)
    print(f"Mobile stations table saved to {args.output}")
    
    # Generate QC report if verbose
    if args.verbose:
        qc_path = args.output.replace('.json', '_qc.txt')
        detector.generate_qc_report(mobiles, qc_path)
        print(f"QC report saved to {qc_path}")
    
    # Summary
    print("\nSummary:")
    for callsign, mobile in sorted(mobiles.items()):
        print(f"  {callsign}: {mobile.total_qsos} QSOs across {len(mobile.counties)} counties")


if __name__ == "__main__":
    main()
