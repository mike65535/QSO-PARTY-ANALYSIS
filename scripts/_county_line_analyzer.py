#!/usr/bin/env python3
"""
County Line Detector for NY QSO Party Database
Analyzes QSO database to detect periods of county line operation based on alternating TX county
"""

import sqlite3
from typing import List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class QSORecord:
    """Represents a single QSO from the database"""
    timestamp: datetime
    freq: str
    mode: str
    tx_call: str
    tx_county: str  # The county being transmitted (3-letter abbrev, uppercase)
    rx_call: str
    rx_county: str  # The county received from other station
    qso_id: int  # Database ID


@dataclass
class CountyLinePeriod:
    """Represents a period of county line operation"""
    start_time: datetime
    end_time: datetime
    county_a: str
    county_b: str
    start_idx: int
    end_idx: int
    qso_count: int
    alternations: int


class DatabaseLoader:
    """Load QSO data from SQLite database"""
    
    @staticmethod
    def load_station_qsos(db_path: str, station_call: str) -> List[QSORecord]:
        """Load all QSOs for a specific station, ordered by datetime"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT id, freq, mode, datetime, tx_call, tx_county, rx_call, rx_county
        FROM qsos 
        WHERE tx_call = ? 
        ORDER BY datetime
        """
        
        cursor.execute(query, (station_call,))
        rows = cursor.fetchall()
        conn.close()
        
        qsos = []
        for row in rows:
            qso_id, freq, mode, datetime_str, tx_call, tx_county, rx_call, rx_county = row
            
            # Parse datetime (format: "2025-10-18 14:02:00")
            timestamp = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            
            qsos.append(QSORecord(
                timestamp=timestamp,
                freq=freq,
                mode=mode,
                tx_call=tx_call,
                tx_county=tx_county,
                rx_call=rx_call,
                rx_county=rx_county,
                qso_id=qso_id
            ))
        
        return qsos
    
    @staticmethod
    def get_ny_mobile_stations(db_path: str) -> List[str]:
        """Get list of all NY mobile station callsigns"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find stations with multiple NY counties (potential mobiles)
        query = """
        SELECT tx_call, COUNT(DISTINCT tx_county) as county_count
        FROM qsos 
        WHERE tx_county IN (
            'ALD', 'ALL', 'BRO', 'CAT', 'CAY', 'CHA', 'CHE', 'CLI', 'COL', 'COR',
            'DEL', 'DUT', 'ERI', 'ESS', 'FRA', 'FUL', 'GEN', 'GRE', 'HAM', 'HER',
            'JEF', 'KIN', 'LEW', 'LIV', 'MAD', 'MON', 'NAS', 'NIA', 'ONE', 'ONO',
            'ORA', 'ORL', 'OSW', 'OTS', 'PUT', 'QUE', 'REN', 'RIC', 'ROC', 'SCH',
            'SCO', 'SEN', 'STL', 'STU', 'SUF', 'SUL', 'TIO', 'TOM', 'ULS', 'WAR',
            'WAS', 'WAY', 'WES', 'WYO', 'YAT'
        )
        GROUP BY tx_call
        HAVING county_count >= 2
        ORDER BY tx_call
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]


class CountyLineDetector:
    """
    Detects county line operation periods from QSO records based on 
    alternating TX county pattern (A-B-A-B...)
    """
    
    def __init__(self, 
                 min_alternations: int = 3,
                 max_consecutive_same: int = 2):
        """
        Args:
            min_alternations: Minimum A-B transitions to confirm county line
            max_consecutive_same: Max allowed consecutive same-county QSOs 
                                 before pattern is considered broken
        """
        self.min_alternations = min_alternations
        self.max_consecutive_same = max_consecutive_same
    
    def find_county_line_periods(self, qsos: List[QSORecord]) -> List[CountyLinePeriod]:
        """
        Finds all county line operation periods in the log
        """
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
    
    def _detect_period_from(self, qsos: List[QSORecord], 
                           start_idx: int) -> Optional[CountyLinePeriod]:
        """
        Attempts to detect a county line period starting at start_idx
        """
        if start_idx + self.min_alternations >= len(qsos):
            return None
        
        scan_window = min(start_idx + 10, len(qsos))
        county_pair = self._find_alternating_pair(qsos[start_idx:scan_window])
        
        if not county_pair:
            return None
        
        county_a, county_b = county_pair
        
        end_idx, alternations = self._trace_pattern(
            qsos, start_idx, county_a, county_b
        )
        
        if alternations >= self.min_alternations:
            return CountyLinePeriod(
                start_time=qsos[start_idx].timestamp,
                end_time=qsos[end_idx].timestamp,
                county_a=county_a,
                county_b=county_b,
                start_idx=start_idx,
                end_idx=end_idx,
                qso_count=end_idx - start_idx + 1,
                alternations=alternations
            )
        
        return None
    
    def _find_alternating_pair(self, qsos: List[QSORecord]) -> Optional[Tuple[str, str]]:
        """Scans for two counties that alternate"""
        for i in range(len(qsos) - 2):
            a = qsos[i].tx_county
            b = qsos[i + 1].tx_county
            
            if a == b:
                continue
            
            if i + 2 < len(qsos) and qsos[i + 2].tx_county == a:
                return (a, b)
        
        return None
    
    def _trace_pattern(self, qsos: List[QSORecord], 
                      start_idx: int,
                      county_a: str, 
                      county_b: str) -> Tuple[int, int]:
        """Traces the extent of alternating pattern"""
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


def format_text_report(qsos: List[QSORecord], 
                      periods: List[CountyLinePeriod],
                      callsign: str = "") -> str:
    """
    Formats a text report of county line periods
    """
    lines = []
    lines.append("=" * 80)
    lines.append(f"COUNTY LINE OPERATION ANALYSIS - {callsign}")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Total QSOs in log: {len(qsos)}")
    lines.append(f"County line periods detected: {len(periods)}")
    lines.append("")
    
    if not periods:
        lines.append("No county line operation detected in this log.")
        return "\n".join(lines)
    
    lines.append("-" * 80)
    lines.append(f"{'Period':<8} {'Start Time':<18} {'End Time':<18} {'Counties':<10} {'QSOs':<6} {'Alt':<5}")
    lines.append("-" * 80)
    
    for idx, period in enumerate(periods, 1):
        start_str = period.start_time.strftime("%Y-%m-%d %H:%M")
        end_str = period.end_time.strftime("%Y-%m-%d %H:%M")
        counties = f"{period.county_a}/{period.county_b}"
        
        lines.append(f"{idx:<8} {start_str:<18} {end_str:<18} {counties:<10} "
                    f"{period.qso_count:<6} {period.alternations:<5}")
    
    lines.append("-" * 80)
    lines.append("")
    
    # Detailed breakdown
    lines.append("DETAILED BREAKDOWN:")
    lines.append("")
    
    for idx, period in enumerate(periods, 1):
        lines.append(f"Period {idx}: {period.county_a}/{period.county_b}")
        lines.append(f"  Start: {period.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  End:   {period.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  Duration: {(period.end_time - period.start_time).total_seconds() / 60:.1f} minutes")
        lines.append(f"  QSOs: {period.qso_count}")
        lines.append(f"  Alternations: {period.alternations}")
        lines.append(f"  Log indices: {period.start_idx} to {period.end_idx}")
        
        # Show TX county sequence for this period
        tx_sequence = [qsos[i].tx_county for i in range(period.start_idx, 
                                                        min(period.end_idx + 1, len(qsos)))]
        lines.append(f"  TX Sequence: {'-'.join(tx_sequence)}")
        lines.append("")
    
    lines.append("=" * 80)
    
    return "\n".join(lines)


def analyze_all_mobiles(db_path: str, output_dir: str = "outputs"):
    """Analyze all NY mobile stations and generate reports"""
    import os
    
    # Get all mobile stations
    mobile_stations = DatabaseLoader.get_ny_mobile_stations(db_path)
    print(f"Found {len(mobile_stations)} potential mobile stations")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    detector = CountyLineDetector(min_alternations=3, max_consecutive_same=2)
    
    all_results = {}
    
    for station in mobile_stations:
        print(f"\nAnalyzing {station}...")
        
        # Load QSOs for this station
        qsos = DatabaseLoader.load_station_qsos(db_path, station)
        print(f"  {len(qsos)} QSOs found")
        
        if len(qsos) < 4:
            print(f"  Skipping {station} - insufficient QSOs")
            continue
        
        # Detect county line periods
        periods = detector.find_county_line_periods(qsos)
        print(f"  {len(periods)} county line periods detected")
        
        all_results[station] = {
            'qsos': qsos,
            'periods': periods
        }
        
        # Generate individual report
        if periods:
            report = format_text_report(qsos, periods, station)
            report_file = os.path.join(output_dir, f"{station}_county_line_analysis.txt")
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"  Report written to: {report_file}")
    
    return all_results


def main():
    """Main analysis function"""
    db_path = "data/contest_qsos.db"
    output_dir = "outputs"
    
    print("NY QSO Party County Line Analysis")
    print("=" * 50)
    
    # Analyze all mobile stations
    results = analyze_all_mobiles(db_path, output_dir)
    
    # Summary report
    print(f"\nSUMMARY:")
    print(f"Analyzed {len(results)} mobile stations")
    
    total_periods = sum(len(data['periods']) for data in results.values())
    print(f"Total county line periods detected: {total_periods}")
    
    # Show stations with county line operation
    county_line_stations = {call: data for call, data in results.items() if data['periods']}
    
    if county_line_stations:
        print(f"\nStations with county line operation:")
        for call, data in county_line_stations.items():
            periods = data['periods']
            print(f"  {call}: {len(periods)} period(s)")
            for i, period in enumerate(periods, 1):
                duration = (period.end_time - period.start_time).total_seconds() / 60
                print(f"    Period {i}: {period.county_a}/{period.county_b} "
                      f"({period.qso_count} QSOs, {duration:.1f} min)")


if __name__ == "__main__":
    main()
