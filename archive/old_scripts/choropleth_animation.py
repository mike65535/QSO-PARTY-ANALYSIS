#!/usr/bin/env python3
"""
Choropleth Animation Engine
Generates animated county coloring based on QSO accumulation over time
"""

import sqlite3
import json
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path

# Animation timing constants
ANIMATION_TIME_STEP_MINUTES = 5  # Time step for animation frames


class ChoroplethAnimationEngine:
    """Generates animated choropleth data for county coloring"""
    
    def __init__(self, contest_start: str = "2025-10-18T14:00:00", 
                 contest_end: str = "2025-10-19T02:00:00",
                 time_step_minutes: int = ANIMATION_TIME_STEP_MINUTES):
        self.contest_start = datetime.fromisoformat(contest_start)
        self.contest_end = datetime.fromisoformat(contest_end)
        self.time_step = timedelta(minutes=time_step_minutes)
    
    def generate_animation_data(self, db_path: str, 
                               filter_type: str = "all",
                               station_list: List[str] = None) -> Dict:
        """
        Generate time-series data for animated choropleth
        
        Returns:
        {
            "time_points": ["2025-10-18T14:00:00", "2025-10-18T14:01:00", ...],
            "county_data": {
                "ERI": [0, 5, 12, 25, ...],  # Cumulative counts at each time point
                "ONO": [0, 2, 8, 15, ...],
                ...
            },
            "max_count": 1234  # Maximum count reached (for color scaling)
        }
        """
        # Generate time points
        time_points = []
        current_time = self.contest_start
        while current_time <= self.contest_end:
            time_points.append(current_time.isoformat())
            current_time += self.time_step
        
        # Get QSO data from database
        qso_data = self._load_qso_data(db_path, filter_type, station_list)
        
        # Build cumulative counts for each time point
        county_data = {}
        max_count = 0
        
        for time_point in time_points:
            time_dt = datetime.fromisoformat(time_point)
            
            # Count QSOs up to this time point
            county_counts = {}
            for qso_time, county in qso_data:
                if qso_time <= time_dt:
                    county_counts[county] = county_counts.get(county, 0) + 1
            
            # Update county_data with cumulative counts
            for county, count in county_counts.items():
                if county not in county_data:
                    county_data[county] = []
                county_data[county].append(count)
                max_count = max(max_count, count)
            
            # Fill in zeros for counties with no QSOs at this time
            for county in county_data:
                if len(county_data[county]) < len([t for t in time_points if t <= time_point]):
                    county_data[county].append(county_data[county][-1] if county_data[county] else 0)
        
        return {
            "time_points": time_points,
            "county_data": county_data,
            "max_count": max_count,
            "filter_type": filter_type,
            "total_qsos": len(qso_data)
        }
    
    def _load_qso_data(self, db_path: str, filter_type: str, 
                      station_list: List[str] = None) -> List[Tuple[datetime, str]]:
        """Load QSO data based on filter type"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if filter_type == "all":
            query = """
            SELECT datetime, tx_county
            FROM qsos 
            ORDER BY datetime
            """
            cursor.execute(query)
            
        elif filter_type == "mobile_only" and station_list:
            placeholders = ','.join('?' * len(station_list))
            query = f"""
            SELECT datetime, tx_county
            FROM qsos 
            WHERE tx_call IN ({placeholders})
            ORDER BY datetime
            """
            cursor.execute(query, station_list)
            
        elif filter_type == "fixed_only" and station_list:
            placeholders = ','.join('?' * len(station_list))
            query = f"""
            SELECT datetime, tx_county
            FROM qsos 
            WHERE tx_call NOT IN ({placeholders})
            ORDER BY datetime
            """
            cursor.execute(query, station_list)
            
        else:
            raise ValueError(f"Invalid filter_type: {filter_type}")
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to datetime objects
        qso_data = []
        for datetime_str, county in rows:
            qso_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            qso_data.append((qso_time, county))
        
        return qso_data
    
    def generate_javascript_module(self, animation_data: Dict) -> str:
        """Generate JavaScript module for choropleth animation"""
        js_code = f'''
// Choropleth Animation Module
class ChoroplethAnimator {{
    constructor(animationData, map, boundaries) {{
        this.data = animationData;
        this.map = map;
        this.boundaries = boundaries;
        this.currentTimeIndex = 0;
        this.countyLayers = {{}};
        this.maxCount = animationData.max_count;
        
        this.initializeCountyLayers();
    }}
    
    initializeCountyLayers() {{
        // Create county layers for coloring
        this.countyLayers = L.geoJSON(this.boundaries, {{
            style: (feature) => {{
                return {{
                    fillColor: '#e8e8e8',
                    weight: 1,
                    opacity: 0.8,
                    color: '#666',
                    fillOpacity: 0.3
                }};
            }}
        }}).addTo(this.map);
    }}
    
    updateColors(timeIndex) {{
        this.currentTimeIndex = timeIndex;
        
        this.countyLayers.eachLayer((layer) => {{
            const countyName = layer.feature.properties.NAME;
            const count = this.getCountForCounty(countyName, timeIndex);
            const color = this.getColorForCount(count);
            
            layer.setStyle({{
                fillColor: color,
                fillOpacity: count > 0 ? 0.7 : 0.3
            }});
        }});
    }}
    
    getCountForCounty(countyName, timeIndex) {{
        // Find county by full name in data (data uses abbreviations)
        for (const [abbrev, counts] of Object.entries(this.data.county_data)) {{
            // Would need county name mapping here
            if (counts && timeIndex < counts.length) {{
                return counts[timeIndex];
            }}
        }}
        return 0;
    }}
    
    getColorForCount(count) {{
        if (count === 0) return '#e8e8e8';
        
        // Color scale from light blue to dark red
        const intensity = Math.min(count / this.maxCount, 1.0);
        const red = Math.floor(255 * intensity);
        const blue = Math.floor(255 * (1 - intensity));
        const green = Math.floor(128 * (1 - intensity));
        
        return `rgb(${{red}}, ${{green}}, ${{blue}})`;
    }}
    
    reset() {{
        this.updateColors(0);
    }}
}}

// Export animation data
const choroplethData = {json.dumps(animation_data, indent=2)};
'''
        return js_code
    
    def save_animation_data(self, animation_data: Dict, output_path: str):
        """Save animation data as JSON"""
        with open(output_path, 'w') as f:
            json.dump(animation_data, f, indent=2)
    
    def generate_qc_report(self, animation_data: Dict, output_path: str):
        """Generate QC report for animation data"""
        lines = []
        lines.append("CHOROPLETH ANIMATION QC REPORT")
        lines.append("=" * 50)
        lines.append(f"Filter type: {animation_data['filter_type']}")
        lines.append(f"Total QSOs: {animation_data['total_qsos']}")
        lines.append(f"Time points: {len(animation_data['time_points'])}")
        lines.append(f"Counties with data: {len(animation_data['county_data'])}")
        lines.append(f"Maximum count: {animation_data['max_count']}")
        lines.append("")
        
        # Time range
        start_time = animation_data['time_points'][0]
        end_time = animation_data['time_points'][-1]
        lines.append(f"Time range: {start_time} to {end_time}")
        lines.append("")
        
        # Top counties by final count
        final_counts = {}
        for county, counts in animation_data['county_data'].items():
            if counts:
                final_counts[county] = counts[-1]
        
        sorted_counties = sorted(final_counts.items(), key=lambda x: x[1], reverse=True)
        
        lines.append("TOP 10 COUNTIES BY FINAL COUNT:")
        lines.append("-" * 30)
        for county, count in sorted_counties[:10]:
            lines.append(f"  {county}: {count}")
        
        with open(output_path, 'w') as f:
            f.write('\\n'.join(lines))


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate choropleth animation data')
    parser.add_argument('--db', default='data/contest_qsos.db', help='Database path')
    parser.add_argument('--filter', choices=['all', 'mobile_only', 'fixed_only'], 
                       default='mobile_only', help='QSO filtering type')
    parser.add_argument('--mobiles', help='Mobile stations JSON file (for mobile_only/fixed_only)')
    parser.add_argument('--output', help='Output JSON file (auto-generated if not specified)')
    parser.add_argument('--time-step', type=int, default=ANIMATION_TIME_STEP_MINUTES, 
                       help=f'Time step in minutes (default: {ANIMATION_TIME_STEP_MINUTES})')
    parser.add_argument('--verbose', action='store_true', help='Generate QC reports')
    
    args = parser.parse_args()
    
    # Auto-generate output filename
    if not args.output:
        args.output = f'outputs/choropleth_animation_{args.filter}.json'
    
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    
    # Load mobile stations if needed
    mobile_stations = None
    if args.mobiles and args.filter in ['mobile_only', 'fixed_only']:
        with open(args.mobiles, 'r') as f:
            mobile_data = json.load(f)
        mobile_stations = list(mobile_data.keys())
    
    # Generate animation data
    engine = ChoroplethAnimationEngine(time_step_minutes=args.time_step)
    
    print(f"Generating choropleth animation data ({args.filter})...")
    animation_data = engine.generate_animation_data(args.db, args.filter, mobile_stations)
    
    print(f"Generated {len(animation_data['time_points'])} time points")
    print(f"Counties with data: {len(animation_data['county_data'])}")
    print(f"Maximum count: {animation_data['max_count']}")
    
    # Save data
    engine.save_animation_data(animation_data, args.output)
    print(f"Animation data saved to {args.output}")
    
    # Generate QC report if verbose
    if args.verbose:
        qc_path = args.output.replace('.json', '_qc.txt')
        engine.generate_qc_report(animation_data, qc_path)
        print(f"QC report saved to {qc_path}")


if __name__ == "__main__":
    main()
