import json
import sys
import os
from pathlib import Path
from ny_state_map_generator import NYStateMapGenerator

# Animation timing constants
ANIMATION_BASE_TIME_STEP_MINUTES = 5  # Base time step for animation synchronization

class MobileAnimationGenerator:
    def __init__(self):
        self.map_generator = NYStateMapGenerator()
        
    def _get_base_map_js(self):
        """Generate base map JavaScript code"""
        return '''
        // Initialize map centered on NY
        const map = L.map('map').setView([43.0, -76.0], 7);
        
        // Add base tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        
        // County coordinates for positioning
        const countyCoords = {};
        
        // Load and display NY county boundaries
        fetch('../data/ny-counties-boundaries.json')
            .then(response => {
                console.log('Fetch response:', response.status, response.statusText);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Boundaries data loaded:', data.features ? data.features.length + ' counties' : 'Invalid data');
                L.geoJSON(data, {
                    style: {
                        color: '#2c3e50',
                        weight: 1,
                        opacity: 0.8,
                        fillColor: '#ecf0f1',
                        fillOpacity: 0.2
                    }
                }).addTo(map);
                
                // Calculate county center coordinates
                data.features.forEach(feature => {
                    const countyName = feature.properties.NAME;
                    const bbox = turf.bbox(feature);
                    const centerLon = (bbox[0] + bbox[2]) / 2;
                    const centerLat = (bbox[1] + bbox[3]) / 2;
                    countyCoords[countyName] = [centerLat, centerLon];
                });
                
                console.log('NY county boundaries loaded successfully');
            })
            .catch(error => {
                console.error('Error loading boundaries:', error);
                alert('Could not load county boundaries: ' + error.message);
            });
        '''
    
    def generate_html(self, output_file, mobile_data, title="NYQP Mobile Animation"):
        """Generate complete mobile animation HTML"""
        
        # Load county-line periods
        periods_path = Path(output_file).parent / 'county_line_periods.json'
        county_line_periods = {}
        if periods_path.exists():
            with open(periods_path, 'r') as f:
                county_line_periods = json.load(f)
        
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
        .control-btn {{ padding: 8px 12px; border: none; border-radius: 6px; background: #3498db; color: white; cursor: pointer; font-size: 14px; }}
        .control-btn:hover {{ background: #2980b9; }}
        .control-btn:disabled {{ background: #7f8c8d; cursor: not-allowed; }}
        .time-display {{ font-size: 16px; font-weight: bold; }}
        .speed-control select {{ padding: 6px; border-radius: 4px; }}
        
        .progress-container {{ width: 300px; height: 8px; background: #34495e; border-radius: 4px; cursor: pointer; }}
        .progress-bar {{ height: 100%; background: #e74c3c; border-radius: 4px; width: 0%; transition: width 0.1s; }}
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
        const countyLinePeriods = {json.dumps(county_line_periods)};
        const countyNames = {json.dumps({"ny_counties": self.map_generator.county_names})};
        
        // Mobile station icons
        const mobileIcons = {{
            'N2CU': '🚗', 'K2A': '🚙', 'N2T': '🚐', 'K2V': '🚕', 'K2Q': '🚓',
            'N1GBE': '🚑', 'WI2M': '🚒', 'W1WV/M': '🚚', 'N2B': '🚛', 'KQ2R': '🏎️',
            'KV2X/M': '🚜', 'WT2X': '🛻', 'AB1BL': '🚌'
        }};
        
        {self._get_base_map_js()}
        
        // Mobile animation logic
        let mobileMarkers = {{}};
        let currentTime = new Date('2025-10-18T14:00:00Z');
        const startTime = new Date('2025-10-18T14:00:00Z');
        const endTime = new Date('2025-10-19T02:00:00Z'); // 12 hours: 14Z to 02Z next day
        
        // Calculate county centroids from GeoJSON
        // countyCoords already declared above
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
                    // Use full QSO pattern to determine if county-line station
                    const coords = getStationCoords(call, qsos);
                    const detection = detectCountyLine(qsos);
                    
                    if (detection.isCountyLine) {{
                        // County-line marker
                    }} else {{
                        // Single county marker
                    }}
                    
                    const iconSymbol = mobileIcons[call] || '📍';
                    const icon = L.divIcon({{
                        html: `<div class="mobile-icon">${{iconSymbol}}</div><div class="mobile-label">${{call}}</div>`,
                        className: 'mobile-marker',
                        iconSize: [40, 40],
                        iconAnchor: [20, 20] // Center the icon on the coordinates
                    }});
                    
                    const countyDisplay = detection.isCountyLine ? 
                        [...new Set(detection.counties)].sort().join('/') : 
                        qsos[0].county;
                    
                    const marker = L.marker(coords, {{
                        icon,
                        riseOnHover: true
                    }}).bindPopup(`<b>${{call}}</b><br>County: ${{countyDisplay}}<br>QSOs: ${{qsos.length}}`);
                    
                    mobileMarkers[call] = marker;
                    marker.addTo(map);
                    console.log(`Added marker for ${{call}} at`, coords);
                }}
            }}
        }}
        
        // Animation controls
        let isPlaying = false;
        let animationSpeed = 0.1;
        const speedOptions = [0.01, 0.05, 0.1, 0.3, 0.6];
        const speedLabels = ['1x', '5x', '10x', '30x', '60x'];
        let currentSpeedIndex = 2;
        
        function togglePlay() {{
            if (isPlaying) {{
                clearInterval(animationInterval);
                document.getElementById('playBtn').innerHTML = '▶ Play';
                isPlaying = false;
            }} else {{
                animationInterval = setInterval(() => {{
                    currentTime = new Date(currentTime.getTime() + (5 * 60 * 1000));
                    if (currentTime > endTime) {{
                        currentTime = endTime;
                        togglePlay();
                    }}
                    onTick();
                }}, animationSpeed * 1000);
                document.getElementById('playBtn').innerHTML = '⏸ Pause';
                isPlaying = true;
            }}
        }}
        
        function resetAnimation() {{
            if (isPlaying) togglePlay();
            currentTime = new Date('2025-10-18T14:00:00Z');
            onTick();
        }}
        
        function cycleSpeed() {{
            currentSpeedIndex = (currentSpeedIndex + 1) % speedOptions.length;
            animationSpeed = speedOptions[currentSpeedIndex];
            document.getElementById('speedBtn').textContent = `Speed ${{speedLabels[currentSpeedIndex]}}`;
        }}
        
        function setupProgressBar() {{
            const progressContainer = document.querySelector('.progress-container');
            progressContainer.addEventListener('click', function(e) {{
                const rect = this.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const percentage = x / rect.width;
                const totalDuration = endTime - startTime;
                currentTime = new Date(startTime.getTime() + (percentage * totalDuration));
                onTick();
            }});
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
        
        // Get coordinates using pre-computed county-line periods
        function getStationCoords(call, qsos, currentTime = null) {{
            const time = currentTime || new Date('2025-10-18T15:00:00Z');
            const periods = countyLinePeriods[call] || [];
            
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
        
        // Check if station is on county line using pre-computed periods
        function isOnCountyLine(call, currentTime) {{
            const periods = countyLinePeriods[call] || [];
            
            for (const period of periods) {{
                const startTime = new Date(period.start_time + 'Z');
                const endTime = new Date(period.end_time + 'Z');
                
                if (currentTime >= startTime && currentTime <= endTime) {{
                    return {{ isCountyLine: true, counties: period.counties }};
                }}
            }}
            
            return {{ isCountyLine: false, counties: [] }};
        }}
        
        // Animation system
        function onTick() {{
            manageIcons();
            manageStatusBar();
        }}
        
        function manageIcons() {{
            for (const [call, qsos] of Object.entries(mobileData)) {{
                const marker = mobileMarkers[call];
                if (!marker) continue;
                
                // Find most recent QSO before or at current time
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
                    // Use pre-computed periods for positioning
                    const coords = getStationCoords(call, qsos, currentTime);
                    const detection = isOnCountyLine(call, currentTime);
                    marker.setLatLng(coords);
                    marker.setOpacity(1);
                    
                    // Count QSOs made BEFORE current time (not including current time)
                    const currentQSOs = qsos.filter(q => new Date(q.timestamp + 'Z') < currentTime);
                    const qsoCount = currentQSOs.length;
                    
                    // Set tooltip display
                    let countyDisplay;
                    if (detection.isCountyLine) {{
                        countyDisplay = detection.counties.join('/');
                    }} else {{
                        countyDisplay = currentQSO.county;
                    }}
                    
                    marker.setPopupContent(`<b>${{call}}</b><br>County: ${{countyDisplay}}<br>QSOs: ${{qsoCount}}`);
                }}
            }}
        }}
        
        function updateProgress(percent) {{
            document.getElementById('progressBar').style.width = percent + '%';
        }}
        
        // Progress bar interaction
        function setupProgressBar() {{
            const progressContainer = document.querySelector('.progress-container');
            
            function handleProgressClick(e) {{
                const rect = progressContainer.getBoundingClientRect();
                const clickX = e.clientX - rect.left;
                const percent = (clickX / rect.width) * 100;
                const clampedPercent = Math.max(0, Math.min(100, percent));
                
                // Update animation time based on progress
                const totalDuration = endTime - startTime;
                const newTime = startTime.getTime() + (clampedPercent / 100) * totalDuration;
                currentTime = new Date(newTime);
                
                // Update display and markers
                updateProgress(clampedPercent);
                onTick();
            }}
            
            progressContainer.addEventListener('click', handleProgressClick);
            
            // Add drag support
            let isDragging = false;
            
            progressContainer.addEventListener('mousedown', (e) => {{
                isDragging = true;
                handleProgressClick(e);
            }});
            
            document.addEventListener('mousemove', (e) => {{
                if (isDragging) {{
                    handleProgressClick(e);
                }}
            }});
            
            document.addEventListener('mouseup', () => {{
                isDragging = false;
            }});
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
            
            // Count NY mobile QSOs and counties up to current time
            let totalMobileQSOs = 0;
            const countiesWithMobileQSOs = new Set();
            
            for (const [call, qsos] of Object.entries(mobileData)) {{
                const currentQSOs = qsos.filter(q => new Date(q.timestamp + 'Z') <= currentTime);
                totalMobileQSOs += currentQSOs.length;
                currentQSOs.forEach(q => countiesWithMobileQSOs.add(q.county));
            }}
            
            document.getElementById('qsoCount').textContent = totalMobileQSOs;
            document.getElementById('countyCount').textContent = countiesWithMobileQSOs.size;
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
                    const coords = getStationCoords(call, qsos);
                    const firstHourEnd = new Date('2025-10-18T15:00:00Z');
                    
                    if (call === 'K2Q') {{
                        console.log(`K2Q tooltip QSOs:`, qsos.slice(0, 4).map(q => q.county));
                    }}
                    
                    const detection = isOnCountyLine(call, firstHourEnd);
                    
                    const countyDisplay = detection.isCountyLine ? 
                        detection.counties.join('/') : 
                        qsos[0].county;
                    
                    const marker = L.marker(coords, {{
                        icon,
                        riseOnHover: true
                    }}).bindPopup(`<b>${{call}}</b><br>County: ${{countyDisplay}}<br>Initializing...`);
                    
                    mobileMarkers[call] = marker;
                    marker.addTo(map);
                }}
            }}
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
                    
                    // Reset tooltip to 0 QSOs
                    const firstCounty = qsos[0].county;
                    marker.setPopupContent(`<b>${{call}}</b><br>County: ${{firstCounty}}<br>QSOs: 0`);
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
        setupProgressBar();
        
        // Set initial state
        onTick();
        
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
    
    # Load mobile QSO data from database
    db_path = '../data/ny_mobiles.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT callsign FROM mobile_stations")
    mobile_callsigns = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Load QSO data
    qso_db_path = '../data/contest_qsos.db'
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
    
    # Generate animation
    generator = MobileAnimationGenerator()
    generator.generate_html('../outputs/mobile_animation_complete.html', mobile_data)
