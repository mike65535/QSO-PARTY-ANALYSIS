#!/usr/bin/env python3
"""
Generate mobile animation using pre-computed county-line periods.
No real-time detection - uses county_line_periods.json
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

class MobileAnimationGenerator:
    def __init__(self, output_dir="../outputs"):
        self.output_dir = Path(output_dir)
        
    def generate_animation(self):
        """Generate mobile animation HTML using pre-computed periods"""
        
        # Load county-line periods
        periods_path = self.output_dir / 'county_line_periods.json'
        with open(periods_path, 'r') as f:
            county_line_periods = json.load(f)
            
        # Load mobile QSO data from database
        db_path = Path("../data/ny_mobiles.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT callsign FROM mobile_stations")
        mobile_callsigns = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # Load QSO data
        qso_db_path = Path("../data/contest_qsos.db")
        conn = sqlite3.connect(qso_db_path)
        
        mobile_data = {}
        for callsign in mobile_callsigns:
            cursor = conn.execute("""
                SELECT datetime, tx_county, freq, mode 
                FROM qsos 
                WHERE station_call = ? 
                ORDER BY datetime
            """, (callsign,))
            
            qsos = []
            for row in cursor.fetchall():
                qsos.append({
                    'timestamp': row[0].replace(' ', 'T'),
                    'county': row[1],
                    'freq': row[2],
                    'mode': row[3]
                })
            mobile_data[callsign] = qsos
            
        conn.close()
        
        # Generate HTML
        html_content = self._generate_html_template(mobile_data, county_line_periods)
        
        output_file = self.output_dir / 'mobile_animation_complete.html'
        with open(output_file, 'w') as f:
            f.write(html_content)
            
        print(f"Mobile animation generated: {output_file}")
        
    def _generate_html_template(self, mobile_data, county_line_periods):
        """Generate HTML template with embedded data"""
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NYQP Mobile Animation</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #map {{ height: 100vh; width: 100%; }}
        .mobile-marker {{ background: none; border: none; }}
        .mobile-icon {{ font-size: 20px; text-align: center; line-height: 20px; }}
        .mobile-label {{ font-size: 10px; text-align: center; color: #333; text-shadow: 1px 1px 1px white; }}
        
        .control-btn {{ padding: 8px 12px; border: none; border-radius: 6px; background: #3498db; color: white; cursor: pointer; font-size: 14px; }}
        .control-btn:hover {{ background: #2980b9; }}
        .control-btn:disabled {{ background: #7f8c8d; cursor: not-allowed; }}
        .time-display {{ font-size: 16px; font-weight: bold; }}
        .speed-control select {{ padding: 6px; border-radius: 4px; }}
        
        .progress-container {{ width: 300px; height: 8px; background: #34495e; border-radius: 4px; cursor: pointer; }}
        .progress-bar {{ height: 100%; background: #e74c3c; border-radius: 4px; width: 0%; transition: width 0.1s; }}
        
        .control-panel {{ position: fixed; bottom: 0; left: 0; right: 0; background: #2c3e50; padding: 10px; z-index: 1000; }}
        .top-controls {{ display: flex; justify-content: center; gap: 10px; margin-bottom: 8px; }}
        .middle-row {{ display: flex; align-items: center; margin-bottom: 8px; }}
        .time-info {{ width: 10%; color: white; font-weight: bold; display: flex; gap: 5px; }}
        .progress-section {{ width: 85%; margin-left: 2%; }}
        .progress-container {{ width: 100%; height: 8px; background: #34495e; border-radius: 4px; cursor: pointer; }}
        .bottom-info {{ text-align: center; color: white; font-size: 12px; }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div class="control-panel">
        <div class="top-controls">
            <button class="control-btn" id="playBtn" onclick="togglePlay()" style="padding: 8px 18px !important;">▶ Play</button>
            <button class="control-btn" id="resetBtn" onclick="resetAnimation()">⏮ Reset</button>
            <button class="control-btn" id="speedBtn" onclick="cycleSpeed()">Speed 10x</button>
        </div>
        <div class="middle-row">
            <div class="time-info">
                <span id="dateDisplay">2025-10-18</span> <span id="timeDisplay">14:00Z</span>
            </div>
            <div class="progress-section">
                <div class="progress-container" onclick="seekToPosition(event)">
                    <div class="progress-bar" id="progressBar"></div>
                </div>
            </div>
        </div>
        <div class="bottom-info">
            <span id="statusDisplay">Ready - Click Play to start animation</span>
        </div>
    </div>

    <script>
        // Embedded data
        const mobileData = {json.dumps(mobile_data, indent=8)};
        const countyLinePeriods = {json.dumps(county_line_periods, indent=8)};
        
        // County coordinates and names
        const countyCoords = {{
            "Albany County": [42.6006, -73.9712], "Allegany County": [42.2578, -78.0311],
            "Bronx County": [40.8448, -73.8648], "Broome County": [42.1654, -75.8088],
            "Cattaraugus County": [42.2348, -78.6597], "Cayuga County": [42.9317, -76.5661],
            "Chautauqua County": [42.2348, -79.2353], "Chemung County": [42.1654, -76.8997],
            "Chenango County": [42.4981, -75.5168], "Clinton County": [44.7317, -73.6370],
            "Columbia County": [42.2481, -73.6370], "Cortland County": [42.5981, -76.1661],
            "Delaware County": [42.2781, -74.9168], "Dutchess County": [41.7654, -73.7481],
            "Erie County": [42.7654, -78.7311], "Essex County": [44.1317, -73.7481],
            "Franklin County": [44.5981, -74.2981], "Fulton County": [43.1317, -74.4481],
            "Genesee County": [43.0000, -78.1997], "Greene County": [42.3654, -74.0481],
            "Hamilton County": [43.4654, -74.4481], "Herkimer County": [43.4317, -74.9881],
            "Jefferson County": [44.0317, -75.9168], "Lewis County": [43.7654, -75.4481],
            "Livingston County": [42.7317, -77.7997], "Madison County": [42.9000, -75.6661],
            "Monroe County": [43.1654, -77.6161], "Montgomery County": [42.9317, -74.4481],
            "Nassau County": [40.7317, -73.5898], "Niagara County": [43.1317, -78.9481],
            "Oneida County": [43.2317, -75.4481], "Onondaga County": [43.0654, -76.1997],
            "Ontario County": [42.8654, -77.2661], "Orange County": [41.4000, -74.3000],
            "Orleans County": [43.2654, -78.2311], "Oswego County": [43.4654, -76.2997],
            "Otsego County": [42.6317, -74.9881], "Putnam County": [41.4317, -73.7481],
            "Rensselaer County": [42.7317, -73.4481], "Richmond County": [40.5795, -74.1502],
            "Rockland County": [41.1317, -74.0481], "Saratoga County": [43.0654, -73.7481],
            "Schenectady County": [42.8317, -73.9481], "Schoharie County": [42.5654, -74.4481],
            "Schuyler County": [42.3981, -76.8997], "Seneca County": [42.7981, -76.8161],
            "St. Lawrence County": [44.4317, -75.1661], "Steuben County": [42.2654, -77.4000],
            "Suffolk County": [40.8654, -72.6161], "Sullivan County": [41.6654, -74.7661],
            "Tioga County": [42.1317, -76.3661], "Tompkins County": [42.4654, -76.4661],
            "Ulster County": [41.9317, -74.2000], "Warren County": [43.4981, -73.7481],
            "Washington County": [43.3317, -73.4481], "Wayne County": [43.0654, -77.0661],
            "Westchester County": [41.1654, -73.7661], "Wyoming County": [42.6981, -78.0661],
            "Yates County": [42.6317, -77.0661]
        }};
        
        const countyNames = {{
            ny_counties: {{
                "ALB": "Albany County", "ALL": "Allegany County", "BRX": "Bronx County", "BRM": "Broome County",
                "CAT": "Cattaraugus County", "CAY": "Cayuga County", "CHA": "Chautauqua County", "CHE": "Chemung County",
                "CGO": "Chenango County", "CLI": "Clinton County", "COL": "Columbia County", "COR": "Cortland County",
                "DEL": "Delaware County", "DUT": "Dutchess County", "ERI": "Erie County", "ESS": "Essex County",
                "FRA": "Franklin County", "FUL": "Fulton County", "GEN": "Genesee County", "GRE": "Greene County",
                "HAM": "Hamilton County", "HER": "Herkimer County", "JEF": "Jefferson County", "LEW": "Lewis County",
                "LIV": "Livingston County", "MAD": "Madison County", "MON": "Monroe County", "MTG": "Montgomery County",
                "NAS": "Nassau County", "NIA": "Niagara County", "ONE": "Oneida County", "ONO": "Onondaga County",
                "ONT": "Ontario County", "ORA": "Orange County", "ORL": "Orleans County", "OSW": "Oswego County",
                "OTS": "Otsego County", "PUT": "Putnam County", "REN": "Rensselaer County", "RIC": "Richmond County",
                "ROC": "Rockland County", "SAR": "Saratoga County", "SCH": "Schenectady County", "SCO": "Schoharie County",
                "SCU": "Schuyler County", "SEN": "Seneca County", "STL": "St. Lawrence County", "STE": "Steuben County",
                "SUF": "Suffolk County", "SUL": "Sullivan County", "TIO": "Tioga County", "TOM": "Tompkins County",
                "ULS": "Ulster County", "WAR": "Warren County", "WAS": "Washington County", "WAY": "Wayne County",
                "WES": "Westchester County", "WYO": "Wyoming County", "YAT": "Yates County"
            }}
        }};
        
        // Mobile icons
        const mobileIcons = {{
            'AB1BL': '🚗', 'K2A': '🚙', 'K2Q': '🚐', 'K2V': '🚛', 'KQ2R': '🏎️',
            'KV2X': '🚓', 'N1GBE': '🚑', 'N2B': '🚒', 'N2CU': '🚌', 'N2T': '🚚',
            'W1WV': '🛻', 'WI2M': '🚜', 'WT2X': '🏍️'
        }};
        
        // Animation variables
        let map, mobileMarkers = {{}}, isPlaying = false, animationSpeed = 0.1;
        let currentTime = new Date('2025-10-18T14:00:00Z');
        let animationInterval;
        const startTime = new Date('2025-10-18T14:00:00Z');
        const endTime = new Date('2025-10-19T02:00:00Z');
        
        // Initialize map
        function initMap() {{
            map = L.map('map').setView([43.0, -76.0], 7);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
            
            // Create mobile markers
            for (const [call, qsos] of Object.entries(mobileData)) {{
                if (qsos.length === 0) continue;
                
                const iconSymbol = mobileIcons[call] || '📍';
                const icon = L.divIcon({{
                    html: `<div class="mobile-icon">${{iconSymbol}}</div><div class="mobile-label">${{call}}</div>`,
                    className: 'mobile-marker',
                    iconSize: [40, 40],
                    iconAnchor: [20, 20]
                }});
                
                const coords = getStationCoords(call, currentTime);
                const marker = L.marker(coords, {{ icon, riseOnHover: true }});
                marker.bindPopup(`<b>${{call}}</b><br>Initializing...`);
                mobileMarkers[call] = marker;
                marker.addTo(map);
            }}
            
            updateDisplay();
        }}
        
        // Get station coordinates using pre-computed periods
        function getStationCoords(callsign, time) {{
            const periods = countyLinePeriods[callsign] || [];
            
            // Check if time falls within any county-line period
            for (const period of periods) {{
                const startTime = new Date(period.start_time + 'Z');
                const endTime = new Date(period.end_time + 'Z');
                
                if (time >= startTime && time <= endTime) {{
                    // On county line - position between counties
                    const county1Name = countyNames.ny_counties[period.counties[0]];
                    const county2Name = countyNames.ny_counties[period.counties[1]];
                    const coords1 = countyCoords[county1Name] || [42.9, -75.5];
                    const coords2 = countyCoords[county2Name] || [42.9, -75.5];
                    return [(coords1[0] + coords2[0]) / 2, (coords1[1] + coords2[1]) / 2];
                }}
            }}
            
            // Not on county line - find current county from QSOs
            const qsos = mobileData[callsign] || [];
            let currentCounty = null;
            
            for (const qso of qsos) {{
                const qsoTime = new Date(qso.timestamp + 'Z');
                if (qsoTime <= time) {{
                    currentCounty = qso.county;
                }} else {{
                    break;
                }}
            }}
            
            if (currentCounty) {{
                const fullCountyName = countyNames.ny_counties[currentCounty];
                return countyCoords[fullCountyName] || [42.9, -75.5];
            }}
            
            return [42.9, -75.5]; // Default position
        }}
        
        // Update display
        function updateDisplay() {{
            // Update time display
            document.getElementById('dateDisplay').textContent = currentTime.toISOString().split('T')[0];
            document.getElementById('timeDisplay').textContent = currentTime.toISOString().split('T')[1].substring(0, 5) + 'Z';
            
            // Update progress bar
            const totalDuration = endTime - startTime;
            const elapsed = currentTime - startTime;
            const progress = Math.max(0, Math.min(100, (elapsed / totalDuration) * 100));
            document.getElementById('progressBar').style.width = progress + '%';
            
            // Update mobile markers
            for (const [call, qsos] of Object.entries(mobileData)) {{
                const marker = mobileMarkers[call];
                if (!marker) continue;
                
                // Find most recent QSO
                let currentQSO = null;
                for (const qso of qsos) {{
                    const qsoTime = new Date(qso.timestamp + 'Z');
                    if (qsoTime <= currentTime) {{
                        currentQSO = qso;
                    }} else {{
                        break;
                    }}
                }}
                
                if (currentQSO) {{
                    const coords = getStationCoords(call, currentTime);
                    marker.setLatLng(coords);
                    marker.setOpacity(1);
                    
                    // Determine county display
                    const periods = countyLinePeriods[call] || [];
                    let countyDisplay = currentQSO.county;
                    let isOnCountyLine = false;
                    
                    for (const period of periods) {{
                        const startTime = new Date(period.start_time + 'Z');
                        const endTime = new Date(period.end_time + 'Z');
                        
                        if (currentTime >= startTime && currentTime <= endTime) {{
                            countyDisplay = period.counties.join('/');
                            isOnCountyLine = true;
                            break;
                        }}
                    }}
                    
                    const qsoCount = qsos.filter(q => new Date(q.timestamp + 'Z') <= currentTime).length;
                    marker.getPopup().setContent(
                        `<b>${{call}}</b><br>County: ${{countyDisplay}}<br>QSOs: ${{qsoCount}}<br>Status: ${{isOnCountyLine ? 'County Line' : 'Single County'}}`
                    );
                }} else {{
                    marker.setOpacity(0.3);
                }}
            }}
            
            // Update status
            const activeStations = Object.keys(mobileData).filter(call => {{
                const qsos = mobileData[call];
                return qsos.some(qso => new Date(qso.timestamp + 'Z') <= currentTime);
            }}).length;
            
            document.getElementById('statusDisplay').textContent = 
                `Active: ${{activeStations}}/13 stations | Time: ${{currentTime.toISOString().split('T')[1].substring(0, 5)}}Z`;
        }}
        
        // Animation controls
        function togglePlay() {{
            if (isPlaying) {{
                clearInterval(animationInterval);
                document.getElementById('playBtn').innerHTML = '▶ Play';
                isPlaying = false;
            }} else {{
                animationInterval = setInterval(() => {{
                    currentTime = new Date(currentTime.getTime() + (5 * 60 * 1000)); // 5 minute steps
                    if (currentTime > endTime) {{
                        currentTime = endTime;
                        togglePlay();
                    }}
                    updateDisplay();
                }}, animationSpeed * 1000);
                document.getElementById('playBtn').innerHTML = '⏸ Pause';
                isPlaying = true;
            }}
        }}
        
        function resetAnimation() {{
            if (isPlaying) togglePlay();
            currentTime = new Date('2025-10-18T14:00:00Z');
            updateDisplay();
        }}
        
        function cycleSpeed() {{
            const speeds = [0.01, 0.05, 0.1, 0.3, 0.6];
            const labels = ['1x', '5x', '10x', '30x', '60x'];
            let currentIndex = speeds.indexOf(animationSpeed);
            currentIndex = (currentIndex + 1) % speeds.length;
            animationSpeed = speeds[currentIndex];
            document.getElementById('speedBtn').textContent = `Speed ${{labels[currentIndex]}}`;
        }}
        
        function seekToPosition(event) {{
            const rect = event.target.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const percentage = x / rect.width;
            const totalDuration = endTime - startTime;
            currentTime = new Date(startTime.getTime() + (percentage * totalDuration));
            updateDisplay();
        }}
        
        // Initialize
        document.addEventListener('DOMContentLoaded', initMap);
    </script>
</body>
</html>'''

def main():
    generator = MobileAnimationGenerator()
    generator.generate_animation()

if __name__ == "__main__":
    main()
