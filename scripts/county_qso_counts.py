#!/usr/bin/env python3
"""
County QSO Count Generator
Generates QSO count per county for choropleth map visualization
Supports different filtering criteria (mobile stations, all stations, etc.)
"""

import sqlite3
import json
from typing import Dict, List, Optional
from pathlib import Path


class CountyQSOCounter:
    """Generates QSO counts per county for map visualization"""
    
    def __init__(self):
        pass
    
    def get_qso_counts_by_filter(self, db_path: str, 
                                filter_type: str = "all",
                                station_list: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Get QSO counts per county with different filtering options
        
        Args:
            db_path: Path to SQLite database
            filter_type: "all", "mobile_only", "fixed_only", "station_list"
            station_list: List of specific stations (used with "station_list" filter)
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if filter_type == "all":
            query = """
            SELECT tx_county, COUNT(*) as qso_count
            FROM qsos 
            GROUP BY tx_county
            ORDER BY qso_count DESC
            """
            cursor.execute(query)
            
        elif filter_type == "mobile_only" and station_list:
            placeholders = ','.join('?' * len(station_list))
            query = f"""
            SELECT tx_county, COUNT(*) as qso_count
            FROM qsos 
            WHERE tx_call IN ({placeholders})
            GROUP BY tx_county
            ORDER BY qso_count DESC
            """
            cursor.execute(query, station_list)
            
        elif filter_type == "fixed_only" and station_list:
            # Exclude mobile stations
            placeholders = ','.join('?' * len(station_list))
            query = f"""
            SELECT tx_county, COUNT(*) as qso_count
            FROM qsos 
            WHERE tx_call NOT IN ({placeholders})
            GROUP BY tx_county
            ORDER BY qso_count DESC
            """
            cursor.execute(query, station_list)
            
        elif filter_type == "station_list" and station_list:
            placeholders = ','.join('?' * len(station_list))
            query = f"""
            SELECT tx_county, COUNT(*) as qso_count
            FROM qsos 
            WHERE tx_call IN ({placeholders})
            GROUP BY tx_county
            ORDER BY qso_count DESC
            """
            cursor.execute(query, station_list)
            
        else:
            raise ValueError(f"Invalid filter_type: {filter_type}")
        
        rows = cursor.fetchall()
        conn.close()
        
        return {county: count for county, count in rows}
    
    def generate_qc_report(self, county_counts: Dict[str, int], output_path: str, 
                          title: str = "County QSO Counts"):
        """Generate QC report for county QSO counts"""
        lines = []
        lines.append(f"{title.upper()} QC REPORT")
        lines.append("=" * 50)
        lines.append(f"Counties with QSOs: {len(county_counts)}")
        lines.append(f"Total QSOs: {sum(county_counts.values())}")
        lines.append("")
        
        # Top counties
        sorted_counties = sorted(county_counts.items(), key=lambda x: x[1], reverse=True)
        
        lines.append("TOP 20 COUNTIES BY QSO COUNT:")
        lines.append("-" * 30)
        lines.append(f"{'County':<8} {'QSOs':<8}")
        lines.append("-" * 30)
        
        for county, count in sorted_counties[:20]:
            lines.append(f"{county:<8} {count:<8}")
        
        if len(sorted_counties) > 20:
            lines.append(f"... and {len(sorted_counties) - 20} more counties")
        
        lines.append("")
        
        # Statistics
        counts = list(county_counts.values())
        lines.append("STATISTICS:")
        lines.append(f"  Max QSOs: {max(counts)}")
        lines.append(f"  Min QSOs: {min(counts)}")
        lines.append(f"  Average: {sum(counts) / len(counts):.1f}")
        lines.append(f"  Median: {sorted(counts)[len(counts)//2]}")
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
    
    def save_table(self, county_counts: Dict[str, int], output_path: str):
        """Save county QSO counts as JSON"""
        with open(output_path, 'w') as f:
            json.dump(county_counts, f, indent=2)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate county QSO count table')
    parser.add_argument('--db', default='../data/contest_qsos.db', help='Database path')
    parser.add_argument('--filter', choices=['all', 'mobile_only', 'fixed_only'], 
                       default='all', help='QSO filtering type')
    parser.add_argument('--mobiles', help='Mobile stations JSON file (for mobile_only/fixed_only filters)')
    parser.add_argument('--output', help='Output JSON file (auto-generated if not specified)')
    parser.add_argument('--verbose', action='store_true', help='Generate QC reports')
    
    args = parser.parse_args()
    
    # Auto-generate output filename if not specified
    if not args.output:
        if args.filter == 'all':
            args.output = 'outputs/county_qso_counts_all.json'
        elif args.filter == 'mobile_only':
            args.output = 'outputs/county_qso_counts_mobile.json'
        elif args.filter == 'fixed_only':
            args.output = 'outputs/county_qso_counts_fixed.json'
    
    # Create output directory
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    
    # Load mobile stations if needed
    mobile_stations = None
    if args.mobiles and args.filter in ['mobile_only', 'fixed_only']:
        with open(args.mobiles, 'r') as f:
            mobile_data = json.load(f)
        mobile_stations = list(mobile_data.keys())
    
    # Generate county QSO counts
    counter = CountyQSOCounter()
    
    if args.filter == 'all':
        print("Counting all QSOs by county...")
        county_counts = counter.get_qso_counts_by_filter(args.db, "all")
        title = "All County QSO Counts"
        
    elif args.filter == 'mobile_only':
        print(f"Counting QSOs from {len(mobile_stations)} mobile stations...")
        county_counts = counter.get_qso_counts_by_filter(args.db, "mobile_only", mobile_stations)
        title = "Mobile Station County QSO Counts"
        
    elif args.filter == 'fixed_only':
        print(f"Counting QSOs from fixed stations (excluding {len(mobile_stations)} mobiles)...")
        county_counts = counter.get_qso_counts_by_filter(args.db, "fixed_only", mobile_stations)
        title = "Fixed Station County QSO Counts"
    
    total_qsos = sum(county_counts.values())
    print(f"Found QSOs in {len(county_counts)} counties ({total_qsos} total QSOs)")
    
    # Save table
    counter.save_table(county_counts, args.output)
    print(f"County QSO counts saved to {args.output}")
    
    # Generate QC report if verbose
    if args.verbose:
        qc_path = args.output.replace('.json', '_qc.txt')
        counter.generate_qc_report(county_counts, qc_path, title)
        print(f"QC report saved to {qc_path}")
    
    # Show top counties
    sorted_counties = sorted(county_counts.items(), key=lambda x: x[1], reverse=True)
    print(f"\nTop 10 counties:")
    for county, count in sorted_counties[:10]:
        print(f"  {county}: {count} QSOs")


if __name__ == "__main__":
    main()
