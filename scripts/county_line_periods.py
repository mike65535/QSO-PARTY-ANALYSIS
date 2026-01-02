#!/usr/bin/env python3
"""
County Line Period Generator
Generates county-line operation periods table from mobile stations
"""

import sqlite3
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class CountyLinePeriod:
    """County line operation period"""
    start_time: str  # ISO timestamp
    end_time: str    # ISO timestamp
    counties: List[str]  # Sorted alphabetically
    qso_count: int
    alternations: int
    start_idx: int
    end_idx: int


@dataclass
class QSORecord:
    """QSO record for analysis"""
    timestamp: datetime
    tx_county: str
    qso_id: int


class CountyLinePeriodGenerator:
    """Generates county-line periods table"""
    
    def __init__(self, 
                 min_alternations: int = 3,
                 max_consecutive_same: int = 2):
        self.min_alternations = min_alternations
        self.max_consecutive_same = max_consecutive_same
    
    def load_mobile_qsos(self, db_path: str, callsign: str) -> List[QSORecord]:
        """Load QSOs for a mobile station"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT id, datetime, tx_county
        FROM qsos 
        WHERE tx_call = ? 
        ORDER BY datetime
        """
        
        cursor.execute(query, (callsign,))
        rows = cursor.fetchall()
        conn.close()
        
        qsos = []
        for qso_id, datetime_str, tx_county in rows:
            timestamp = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            qsos.append(QSORecord(timestamp, tx_county, qso_id))
        
        return qsos
    
    def find_county_line_periods(self, qsos: List[QSORecord]) -> List[CountyLinePeriod]:
        """Find county-line periods in QSO sequence"""
        if len(qsos) < self.min_alternations + 1:
            return []
        
        periods = []
        i = 0
        
        while i < len(qsos) - self.min_alternations:
            period = self._detect_period_from(qsos, i)
            
            if period:
                periods.append(period)
                i = period.end_idx + 1
            else:
                i += 1
        
        return periods
    
    def _detect_period_from(self, qsos: List[QSORecord], start_idx: int) -> Optional[CountyLinePeriod]:
        """Detect county-line period starting at index"""
        if start_idx + self.min_alternations >= len(qsos):
            return None
        
        # Look for alternating pair in next 10 QSOs
        scan_window = min(start_idx + 10, len(qsos))
        county_pair = self._find_alternating_pair(qsos[start_idx:scan_window])
        
        if not county_pair:
            return None
        
        county_a, county_b = county_pair
        end_idx, alternations = self._trace_pattern(qsos, start_idx, county_a, county_b)
        
        if alternations >= self.min_alternations:
            return CountyLinePeriod(
                start_time=qsos[start_idx].timestamp.isoformat(),
                end_time=qsos[end_idx].timestamp.isoformat(),
                counties=sorted([county_a, county_b]),
                qso_count=end_idx - start_idx + 1,
                alternations=alternations,
                start_idx=start_idx,
                end_idx=end_idx
            )
        
        return None
    
    def _find_alternating_pair(self, qsos: List[QSORecord]) -> Optional[tuple]:
        """Find alternating county pair"""
        for i in range(len(qsos) - 2):
            a = qsos[i].tx_county
            b = qsos[i + 1].tx_county
            
            if a == b:
                continue
            
            if i + 2 < len(qsos) and qsos[i + 2].tx_county == a:
                return (a, b)
        
        return None
    
    def _trace_pattern(self, qsos: List[QSORecord], start_idx: int, 
                      county_a: str, county_b: str) -> tuple:
        """Trace extent of alternating pattern"""
        expected = qsos[start_idx].tx_county
        if expected not in (county_a, county_b):
            return (start_idx, 0)
        
        alternations = 0
        consecutive_same = 0
        last_valid_idx = start_idx
        
        for i in range(start_idx, len(qsos)):
            current = qsos[i].tx_county
            
            if current not in (county_a, county_b):
                break
            
            if current == expected:
                consecutive_same = 0
                last_valid_idx = i
                expected = county_b if expected == county_a else county_a
                alternations += 1
            else:
                consecutive_same += 1
                last_valid_idx = i
                
                if consecutive_same > self.max_consecutive_same:
                    last_valid_idx = i - consecutive_same
                    break
        
        return (last_valid_idx, alternations)
    
    def generate_periods_table(self, db_path: str, mobile_stations: List[str]) -> Dict[str, List[CountyLinePeriod]]:
        """Generate county-line periods table for all mobile stations"""
        periods_table = {}
        
        for callsign in mobile_stations:
            qsos = self.load_mobile_qsos(db_path, callsign)
            periods = self.find_county_line_periods(qsos)
            
            if periods:
                periods_table[callsign] = periods
        
        return periods_table
    
    def generate_qc_report(self, periods_table: Dict[str, List[CountyLinePeriod]], 
                          output_path: str):
        """Generate QC report for county-line periods"""
        lines = []
        lines.append("COUNTY LINE PERIODS QC REPORT")
        lines.append("=" * 50)
        lines.append(f"Detection parameters:")
        lines.append(f"  Minimum alternations: {self.min_alternations}")
        lines.append(f"  Max consecutive same: {self.max_consecutive_same}")
        lines.append("")
        
        total_periods = sum(len(periods) for periods in periods_table.values())
        lines.append(f"Stations with county-line periods: {len(periods_table)}")
        lines.append(f"Total periods detected: {total_periods}")
        lines.append("")
        
        lines.append("-" * 100)
        lines.append(f"{'Station':<8} {'Period':<3} {'Start Time':<16} {'End Time':<16} {'Counties':<8} {'QSOs':<5} {'Alt':<4} {'Duration':<8}")
        lines.append("-" * 100)
        
        for callsign, periods in sorted(periods_table.items()):
            for i, period in enumerate(periods, 1):
                start_dt = datetime.fromisoformat(period.start_time)
                end_dt = datetime.fromisoformat(period.end_time)
                duration = (end_dt - start_dt).total_seconds() / 60
                
                counties_str = '/'.join(period.counties)
                
                lines.append(f"{callsign:<8} {i:<3} {start_dt.strftime('%m-%d %H:%M'):<16} "
                           f"{end_dt.strftime('%m-%d %H:%M'):<16} {counties_str:<8} "
                           f"{period.qso_count:<5} {period.alternations:<4} {duration:>6.0f}m")
        
        lines.append("-" * 100)
        lines.append("")
        
        # Summary by station
        lines.append("SUMMARY BY STATION:")
        lines.append("")
        for callsign, periods in sorted(periods_table.items()):
            total_qsos = sum(p.qso_count for p in periods)
            total_duration = sum(
                (datetime.fromisoformat(p.end_time) - datetime.fromisoformat(p.start_time)).total_seconds() / 60
                for p in periods
            )
            lines.append(f"{callsign}: {len(periods)} periods, {total_qsos} QSOs, {total_duration:.0f} minutes")
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
    
    def save_table(self, periods_table: Dict[str, List[CountyLinePeriod]], output_path: str):
        """Save periods table as JSON"""
        # Convert to serializable format
        serializable = {}
        for callsign, periods in periods_table.items():
            serializable[callsign] = [asdict(period) for period in periods]
        
        with open(output_path, 'w') as f:
            json.dump(serializable, f, indent=2)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate county-line periods table')
    parser.add_argument('--db', default='../data/contest_qsos.db', help='Database path')
    parser.add_argument('--mobiles', default='../data/ny_mobiles.db', help='Mobile stations database')
    parser.add_argument('--output', default='outputs/county_line_periods.json', help='Output JSON file')
    parser.add_argument('--verbose', action='store_true', help='Generate QC reports')
    parser.add_argument('--min-alternations', type=int, default=3, help='Minimum alternations')
    parser.add_argument('--max-consecutive', type=int, default=2, help='Max consecutive same county')
    
    args = parser.parse_args()
    
    # Create output directory
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    
    # Load mobile stations from database
    import sqlite3
    conn = sqlite3.connect(args.mobiles)
    cursor = conn.execute("SELECT callsign FROM mobile_stations")
    mobile_stations = [row[0] for row in cursor.fetchall()]
    conn.close()
    print(f"Processing {len(mobile_stations)} mobile stations...")
    
    # Generate periods table
    generator = CountyLinePeriodGenerator(
        min_alternations=args.min_alternations,
        max_consecutive_same=args.max_consecutive
    )
    
    periods_table = generator.generate_periods_table(args.db, mobile_stations)
    
    stations_with_periods = len(periods_table)
    total_periods = sum(len(periods) for periods in periods_table.values())
    print(f"Found county-line periods for {stations_with_periods} stations ({total_periods} total periods)")
    
    # Save table
    generator.save_table(periods_table, args.output)
    print(f"County-line periods table saved to {args.output}")
    
    # Generate QC report if verbose
    if args.verbose:
        qc_path = args.output.replace('.json', '_qc.txt')
        generator.generate_qc_report(periods_table, qc_path)
        print(f"QC report saved to {qc_path}")


if __name__ == "__main__":
    main()
