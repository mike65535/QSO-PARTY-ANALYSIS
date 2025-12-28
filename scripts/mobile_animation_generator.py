import json
import sys
import os

# Add the lib directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from lib.map_generator import NYMapGenerator
from lib.animation_ui import TimelineControls, ProgressBar, StatusBar, Legend

class MobileAnimationGenerator:
    def __init__(self, boundaries_file, county_names_file):
        self.map_generator = NYMapGenerator(boundaries_file, county_names_file)
    
    def generate_html(self, output_file, mobile_data, title="NYQP Mobile Animation"):
        """Generate complete mobile animation HTML"""
        
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/@turf/turf@6/turf.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }}
        #map {{
            height: 100vh;
            width: 100%;
        }}
        .mobile-marker {{
            background: none;
            border: none;
        }}
        .mobile-icon {{
            font-size: 20px;
            text-align: center;
            line-height: 20px;
        }}
        .mobile-label {{
            font-size: 10px;
            font-weight: bold;
            text-align: center;
            color: #333;
            text-shadow: 1px 1px 1px white;
        }}
        {TimelineControls.get_css()}
        {ProgressBar.get_css()}
        .control-panel {{ position: fixed; bottom: 0; left: 0; right: 0; background: #2c3e50; padding: 15px; z-index: 1000; }}
        .top-controls {{ display: flex; justify-content: center; gap: 15px; margin-bottom: 10px; }}
        .middle-row {{ display: flex; align-items: center; margin-bottom: 10px; }}
        .time-info {{ width: 10%; color: white; font-weight: bold; display: flex; gap: 5px; }}
        .progress-section {{ width: 85%; margin-left: 2%; }}
        .progress-container {{ width: 100%; height: 8px; background: #34495e; border-radius: 4px; cursor: pointer; }}
        .bottom-info {{ text-align: center; color: white; font-size: 14px; }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div class="control-panel">
        <div class="top-controls">
            <button class="control-btn" id="playBtn" onclick="togglePlay()" style="padding: 12px 25px !important;">▶ Play</button>
            <button class="control-btn" id="resetBtn" onclick="resetAnimation()">⏮ Reset</button>
            <button class="control-btn" id="speedBtn" onclick="cycleSpeed()">Speed 10x</button>
        </div>
        <div class="middle-row">
            <div class="time-info">
                <span id="dateDisplay">2025-10-18</span> <span id="timeDisplay">14:00Z</span>
            </div>
            <div class="progress-section">
                <div class="progress-container">
                    <div class="progress-bar" id="progressBar"></div>
                </div>
            </div>
        </div>
        <div class="bottom-info">
            NYQP 2025 Mobile Activity | QSOs: <span id="qsoCount">0</span> | Counties Covered: <span id="countyCount">0</span>
        </div>
    </div>
    
    <script>
        const mobileData = {json.dumps(mobile_data)};
        const countyNames = {json.dumps(self.map_generator.county_names)};
        
        // Mobile station icons
        const mobileIcons = {{
            'N2CU': '🚗', 'K2A': '🚙', 'N2T': '🚐', 'K2V': '🚕', 'K2Q': '🚓',
            'N1GBE': '🚑', 'WI2M': '🚒', 'W1WV/M': '🚚', 'N2B': '🚛', 'KQ2R': '🏎️',
            'KV2X/M': '🚜', 'WT2X': '🛻', 'AB1BL': '🚌'
        }};
        
        {self.map_generator._get_base_map_js()}
        
        // Mobile animation logic
        let mobileMarkers = {{}};
        let currentTime = new Date('2025-10-18T14:00:00Z');
        const startTime = new Date('2025-10-18T14:00:00Z');
        const endTime = new Date('2025-10-19T02:00:00Z'); // 12 hours: 14Z to 02Z next day
        
        // Calculate county centroids from GeoJSON
        const countyCoords = {{}};
        boundaries.features.forEach(feature => {{
            const countyName = feature.properties.NAME;
            // Use bounding box center - bbox returns [minLon, minLat, maxLon, maxLat]
            const bbox = turf.bbox(feature);
            const centerLon = (bbox[0] + bbox[2]) / 2;
            const centerLat = (bbox[1] + bbox[3]) / 2;
            countyCoords[countyName] = [centerLat, centerLon]; // Leaflet expects [lat, lon]
        }});
        
        // Create mobile station markers
        function createMobileMarkers() {{
            const firstHourEnd = new Date('2025-10-18T15:00:00Z');
            const countyStations = {{}}; // Track stations per county
            
            // First pass: count stations per county
            for (const [call, qsos] of Object.entries(mobileData)) {{
                const hasFirstHourQSO = qsos.some(qso => {{
                    const qsoTime = new Date(qso.timestamp + 'Z');
                    return qsoTime <= firstHourEnd;
                }});
                
                if (hasFirstHourQSO) {{
                    const county = qsos[0].county;
                    if (!countyStations[county]) countyStations[county] = [];
                    countyStations[county].push(call);
                }}
            }}
            
            for (const [call, qsos] of Object.entries(mobileData)) {{
                const hasFirstHourQSO = qsos.some(qso => {{
                    const qsoTime = new Date(qso.timestamp + 'Z');
                    return qsoTime <= firstHourEnd;
                }});
                
                if (hasFirstHourQSO) {{
                    const coords = getStationCoords(call, qsos);
                    const detection = detectCountyLine(qsos);
                    
                    if (detection.isCountyLine) {{
                        console.log(`Creating county-line marker for ${{call}}: ${{detection.counties.join('/')}} -> midpoint`);
                    }} else {{
                        const firstQSO = qsos[0];
                        console.log(`Creating marker for ${{call}}: ${{firstQSO.county}} -> single county`);
                    }}
                    
                    const iconSymbol = mobileIcons[call] || '📍';
                    const icon = L.divIcon({{
                        html: `<div class="mobile-icon">${{iconSymbol}}</div><div class="mobile-label">${{call}}</div>`,
                        className: 'mobile-marker',
                        iconSize: [40, 40],
                        iconAnchor: [20, 20] // Center the icon on the coordinates
                    }});
                    
                    const marker = L.marker(coords, {{
                        icon,
                        riseOnHover: true
                    }}).bindPopup(`<b>${{call}}</b><br>QSOs: ${{qsos.length}}`);
                    
                    mobileMarkers[call] = marker;
                    marker.addTo(map);
                    console.log(`Added marker for ${{call}} at`, coords);
                }}
            }}
        }}
        
        {TimelineControls.get_javascript()}
        {ProgressBar.get_javascript()}
        
        // Override togglePlay to adjust padding
        function togglePlay() {{
            isPlaying = !isPlaying;
            const btn = document.getElementById('playBtn');
            if (isPlaying) {{
                btn.textContent = '⏸ Pause';
                btn.style.padding = '12px 16px !important';
            }} else {{
                btn.textContent = '▶ Play';
                btn.style.padding = '12px 25px !important';
            }}
        }}
        animationSpeed = 0.1;
        const speedOptions = [0.01, 0.05, 0.1, 0.3, 0.6];
        const speedLabels = ['1x', '5x', '10x', '30x', '60x'];
        let currentSpeedIndex = 2; // Start at 10x
        
        function cycleSpeed() {{
            currentSpeedIndex = (currentSpeedIndex + 1) % speedOptions.length;
            animationSpeed = speedOptions[currentSpeedIndex];
            document.getElementById('speedBtn').textContent = `Speed ${{speedLabels[currentSpeedIndex]}}`;
        }}
        
        function changeSpeed() {{
            animationSpeed = parseFloat(document.getElementById('speedSelect').value);
        }}
        
        // County-line detection utility
        function detectCountyLine(qsos, currentTime = null) {{
            const counties = qsos.map(q => q.county);
            let relevantQSOs;
            
            if (currentTime) {{
                // Filter by current time and get recent QSOs
                const currentQSOs = qsos.filter(qso => new Date(qso.timestamp + 'Z') <= currentTime);
                const currentCounties = currentQSOs.map(q => q.county);
                relevantQSOs = currentCounties.slice(-6);
            }} else {{
                // Use early QSOs for initial detection
                relevantQSOs = counties.slice(0, 6);
            }}
            
            const uniqueCounties = [...new Set(relevantQSOs)];
            
            if (uniqueCounties.length === 2 && relevantQSOs.length >= 2) {{
                let alternations = 0;
                for (let i = 1; i < relevantQSOs.length; i++) {{
                    if (relevantQSOs[i] !== relevantQSOs[i-1]) alternations++;
                }}
                if (alternations >= 1) {{
                    return {{ isCountyLine: true, counties: uniqueCounties }};
                }}
            }}
            
            return {{ isCountyLine: false, counties: [] }};
        }}
        
        // Get coordinates for county-line or single county
        function getStationCoords(call, qsos, currentTime = null) {{
            const detection = detectCountyLine(qsos, currentTime);
            
            if (detection.isCountyLine) {{
                const county1Name = countyNames.ny_counties[detection.counties[0]];
                const county2Name = countyNames.ny_counties[detection.counties[1]];
                const coords1 = countyCoords[county1Name] || [42.9, -75.5];
                const coords2 = countyCoords[county2Name] || [42.9, -75.5];
                return [(coords1[0] + coords2[0]) / 2, (coords1[1] + coords2[1]) / 2];
            }} else {{
                const firstQSO = qsos[0];
                const fullCountyName = countyNames.ny_counties[firstQSO.county];
                return countyCoords[fullCountyName] || [42.9, -75.5];
            }}
        }}
        
        // Animation system
        function onTick() {{
            manageIcons();
        }}
        
        function manageIcons() {{
            for (const [call, qsos] of Object.entries(mobileData)) {{
                const marker = mobileMarkers[call];
                if (!marker) continue;
                
                // Find most recent QSO before current time
                let currentQSO = null;
                let latestTime = new Date(0);
                
                for (const qso of qsos) {{
                    const qsoTime = new Date(qso.timestamp + 'Z');
                    if (qsoTime <= currentTime && qsoTime > latestTime) {{
                        currentQSO = qso;
                        latestTime = qsoTime;
                    }}
                }}
                
                if (currentQSO) {{
                    const coords = getStationCoords(call, qsos, currentTime);
                    marker.setLatLng(coords);
                    marker.setOpacity(1);
                }}
            }}
        }}
        
        function initializeIcons() {{
            const firstHourEnd = new Date('2025-10-18T15:00:00Z');
            
            for (const [call, qsos] of Object.entries(mobileData)) {{
                // Only create marker if station has QSOs in first hour
                const hasFirstHourQSO = qsos.some(qso => {{
                    const qsoTime = new Date(qso.timestamp + 'Z');
                    return qsoTime <= firstHourEnd;
                }});
                
                if (hasFirstHourQSO) {{
                    const iconSymbol = mobileIcons[call] || '📍';
                    const icon = L.divIcon({{
                        html: `<div class="mobile-icon">${{iconSymbol}}</div><div class="mobile-label">${{call}}</div>`,
                        className: 'mobile-marker',
                        iconSize: [40, 40],
                        iconAnchor: [20, 20]
                    }});
                    
                    // Determine initial position (county-line or single county)
                    const coords = getStationPosition(call, qsos);
                    
                    const marker = L.marker(coords, {{
                        icon,
                        riseOnHover: true
                    }}).bindPopup(`<b>${{call}}</b><br>Initializing...`);
                    
                    mobileMarkers[call] = marker;
                    marker.addTo(map);
                }}
            }}
        }}
        
        function getStationPosition(call, qsos) {{
            // Check for county-line operation (alternating between 2 counties)
            const counties = qsos.map(q => q.county);
            const uniqueCounties = [...new Set(counties)];
            
            if (uniqueCounties.length === 2) {{
                // County-line operation - check if alternating
                let isAlternating = false;
                for (let i = 1; i < counties.length; i++) {{
                    if (counties[i] !== counties[i-1]) {{
                        isAlternating = true;
                        break;
                    }}
                }}
                
                if (isAlternating) {{
                    // Place on county line (midpoint between two counties)
                    const county1Name = countyNames.ny_counties[uniqueCounties[0]];
                    const county2Name = countyNames.ny_counties[uniqueCounties[1]];
                    const coords1 = countyCoords[county1Name] || [42.9, -75.5];
                    const coords2 = countyCoords[county2Name] || [42.9, -75.5];
                    return [(coords1[0] + coords2[0]) / 2, (coords1[1] + coords2[1]) / 2];
                }}
            }}
            
            // Single county or non-alternating - use first county
            const firstCounty = qsos[0].county;
            const fullCountyName = countyNames.ny_counties[firstCounty];
            return countyCoords[fullCountyName] || [42.9, -75.5];
        }}
        
        function updateIconPositions() {{
            // This function is deprecated - all positioning handled by manageIcons()
            return;
        }}
        
        function updateCountyLineStatus(call, qsos, marker) {{
            const currentQSO = qsos.find(qso => new Date(qso.timestamp + 'Z') <= currentTime);
            if (!currentQSO) return;
            
            // Check if this is a county-line operation (alternating between exactly 2 counties)
            const counties = qsos.map(q => q.county);
            const uniqueCounties = [...new Set(counties)];
            
            console.log(`Station ${{call}}: ${{uniqueCounties.length}} unique counties: ${{uniqueCounties.join(', ')}}`);
            
            let isCountyLine = false;
            if (uniqueCounties.length === 2) {{
                // Check if alternating pattern exists
                for (let i = 1; i < counties.length; i++) {{
                    if (counties[i] !== counties[i-1]) {{
                        isCountyLine = true;
                        console.log(`${{call}} has alternating pattern - county-line station`);
                        break;
                    }}
                }}
            }}
            
            if (isCountyLine) {{
                // County-line: stay at midpoint during animation
                const county1Name = countyNames.ny_counties[uniqueCounties[0]];
                const county2Name = countyNames.ny_counties[uniqueCounties[1]];
                const coords1 = countyCoords[county1Name] || [42.9, -75.5];
                const coords2 = countyCoords[county2Name] || [42.9, -75.5];
                const midpoint = [(coords1[0] + coords2[0]) / 2, (coords1[1] + coords2[1]) / 2];
                console.log(`County-line station ${{call}} positioned at midpoint between ${{uniqueCounties[0]}} and ${{uniqueCounties[1]}}`);
                marker.setLatLng(midpoint);
            }} else {{
                // Single county: normal positioning
                const fullCountyName = countyNames.ny_counties[currentQSO.county];
                const coords = countyCoords[fullCountyName] || [42.9, -75.5];
                marker.setLatLng(coords);
            }}
        }}
        
        function manageStatusBar() {{
            // Update timestamp
            const timeStr = currentTime.toISOString().substr(11, 5) + 'Z';
            const dateStr = currentTime.toISOString().substr(0, 10);
            document.getElementById('timeDisplay').textContent = timeStr;
            document.getElementById('dateDisplay').textContent = dateStr;
            
            // Update progress bar
            const totalDuration = endTime - startTime;
            const elapsed = currentTime - startTime;
            const percent = (elapsed / totalDuration) * 100;
            updateProgress(percent);
            
            // Update counts
            let totalQSOs = 0;
            const activeCounties = new Set();
            for (const [call, qsos] of Object.entries(mobileData)) {{
                const currentQSOs = qsos.filter(q => new Date(q.timestamp + 'Z') <= currentTime);
                totalQSOs += currentQSOs.length;
                currentQSOs.forEach(q => activeCounties.add(q.county));
            }}
            document.getElementById('qsoCount').textContent = totalQSOs;
            document.getElementById('countyCount').textContent = activeCounties.size;
        }}
        
        function manageLegend() {{
            // Legend management (placeholder)
        }}
        
        function manageMapColorization() {{
            // Map colorization management (placeholder)
        }}
        
        // Animation loop
        function animate() {{
            if (isPlaying) {{
                // Advance time by animationSpeed minutes
                currentTime = new Date(currentTime.getTime() + animationSpeed * 60000);
                
                // Check if we've reached the end
                if (currentTime > endTime) {{
                    currentTime = endTime;
                    isPlaying = false;
                    document.getElementById('playBtn').textContent = '▶ Play';
                }}
                
                // Update display
                const timeStr = currentTime.toISOString().substr(11, 5) + 'Z';
                const dateStr = currentTime.toISOString().substr(0, 10);
                document.getElementById('timeDisplay').textContent = timeStr;
                document.getElementById('dateDisplay').textContent = dateStr;
                
                // Update progress bar
                const totalDuration = endTime - startTime;
                const elapsed = currentTime - startTime;
                const percent = (elapsed / totalDuration) * 100;
                updateProgress(percent);
                
                // Update mobile markers
                onTick();
            }}
            
            requestAnimationFrame(animate);
        }}
        
        function resetAnimation() {{
            isPlaying = false;
            currentTime = new Date(startTime);
            document.getElementById('playBtn').textContent = '▶ Play';
            document.getElementById('timeDisplay').textContent = '14:00Z';
            document.getElementById('dateDisplay').textContent = '2025-10-18';
            updateProgress(0);
            
            // Reset all stations to their initial positions
            for (const [call, qsos] of Object.entries(mobileData)) {{
                const marker = mobileMarkers[call];
                if (marker) {{
                    const coords = getStationCoords(call, qsos);
                    marker.setLatLng(coords);
                    marker.setOpacity(1);
                }}
            }}
            
            onTick();
        }}
        
        function updateMap() {{
            // Disabled - positioning handled by manageIcons()
            return;
        }}
        
        // Initialize
        createMobileMarkers();
        
        // Start animation loop
        animate();
        
        // Start animation loop
        animate();
    </script>
</body>
</html>'''
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"Mobile animation generated: {output_file}")

if __name__ == "__main__":
    import sqlite3
    
    # Load mobile data from database
    conn = sqlite3.connect('../data/contest_qsos.db')
    cursor = conn.cursor()
    
    # Attach metadata database
    cursor.execute("ATTACH DATABASE '../data/contest_meta.db' AS meta")
    
    # Get mobile stations based on category
    cursor.execute('''
        SELECT q.station_call, q.datetime, q.tx_county 
        FROM qsos q
        JOIN meta.stations m ON q.station_call = m.callsign
        WHERE m.station_type = 'MOBILE'
        ORDER BY q.station_call, q.datetime
    ''')
    
    mobile_data = {}
    for station_call, datetime_str, tx_county in cursor.fetchall():
        if station_call not in mobile_data:
            mobile_data[station_call] = []
        mobile_data[station_call].append({
            "timestamp": datetime_str,
            "county": tx_county
        })
    
    conn.close()
    
    generator = MobileAnimationGenerator('../data/ny-counties-boundaries.json', '../data/ny_county_names.json')
    generator.generate_html('../outputs/mobile_animation_complete.html', mobile_data)
