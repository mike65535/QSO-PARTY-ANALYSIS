#!/usr/bin/env python3
"""
All QSO Animation Generator - shows county activity for all stations
"""

import json
import sqlite3
from pathlib import Path

def generate_all_qso_animation():
    """Generate animation showing all QSO activity by county"""
    
    # Load boundaries data to embed
    boundaries_path = Path('../data/ny-counties-boundaries.json')
    with open(boundaries_path, 'r') as f:
        boundaries_data = json.load(f)
        
    # Load all QSO data from database
    qso_db_path = Path('../data/contest_qsos.db')
    conn = sqlite3.connect(qso_db_path)
    
    # Get all QSOs from NY stations
    cursor = conn.execute("""
        SELECT datetime, station_call, tx_county, freq, mode 
        FROM qsos 
        WHERE tx_county IS NOT NULL AND tx_county != ''
        ORDER BY datetime
    """)
    
    all_qsos = []
    for row in cursor.fetchall():
        all_qsos.append({
            't': row[0].replace(' ', 'T'),  # timestamp -> t
            's': row[1],                    # station -> s  
            'c': row[2]                     # county -> c
            # Remove freq and mode - not needed for county coloring
        })
    
    conn.close()
        
    # County names mapping
    county_names = {
        "ALB": "Albany County", "ALL": "Allegany County", "BRX": "Bronx County", "BRM": "Broome County",
        "CAT": "Cattaraugus County", "CAY": "Cayuga County", "CHA": "Chautauqua County", "CHE": "Chemung County",
        "CGO": "Chenango County", "CLI": "Clinton County", "COL": "Columbia County", "COR": "Cortland County",
        "DEL": "Delaware County", "DUT": "Dutchess County", "ERI": "Erie County", "ESS": "Essex County",
        "FRA": "Franklin County", "FUL": "Fulton County", "GEN": "Genesee County", "GRE": "Greene County",
        "HAM": "Hamilton County", "HER": "Herkimer County", "JEF": "Jefferson County", "KIN": "Kings County",
        "LEW": "Lewis County", "LIV": "Livingston County", "MAD": "Madison County", "MON": "Monroe County",
        "MOT": "Montgomery County", "NAS": "Nassau County", "NEW": "New York County", "NIA": "Niagara County",
        "ONE": "Oneida County", "ONO": "Onondaga County", "ONT": "Ontario County", "ORA": "Orange County",
        "ORL": "Orleans County", "OSW": "Oswego County", "OTS": "Otsego County", "PUT": "Putnam County",
        "QUE": "Queens County", "REN": "Rensselaer County", "RIC": "Richmond County", "ROC": "Rockland County",
        "SAR": "Saratoga County", "SCH": "Schenectady County", "SCO": "Schoharie County", "SCU": "Schuyler County",
        "SEN": "Seneca County", "STL": "St. Lawrence County", "STE": "Steuben County", "SUF": "Suffolk County",
        "SUL": "Sullivan County", "TIO": "Tioga County", "TOM": "Tompkins County", "ULS": "Ulster County",
        "WAR": "Warren County", "WAS": "Washington County", "WAY": "Wayne County", "WES": "Westchester County",
        "WYO": "Wyoming County", "YAT": "Yates County", "NIA": "Niagara County"
    }
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NYQP 2025 All Station Activity Animation</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/@turf/turf@6/turf.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #map {{ height: 95vh; width: 100%; background-color: white; margin-top: -5vh; }}
        
        .leaflet-top {{ top: 40px; }}
        
        .legend {{ 
            position: fixed; 
            top: 50px; 
            right: 20px; 
            background: rgba(255,255,255,0.9); 
            padding: 10px; 
            border-radius: 5px; 
            border: 1px solid #ccc; 
            font-size: 12px; 
            z-index: 1000; 
        }}
        .legend-item {{ 
            display: flex; 
            align-items: center; 
            margin: 2px 0; 
        }}
        .legend-color {{ 
            width: 20px; 
            height: 15px; 
            margin-right: 8px; 
            border: 1px solid #666; 
        }}
        
        .control-btn {{ 
            background: #3498db; 
            color: white; 
            border: none; 
            padding: 8px 12px; 
            margin: 0 2px; 
            border-radius: 4px; 
            cursor: pointer; 
            font-size: 12px; 
        }}
        .control-btn:hover {{ background: #2980b9; }}
        .control-btn:disabled {{ background: #7f8c8d; cursor: not-allowed; }}
        
        .control-panel {{ position: fixed; bottom: 0; left: 0; right: 0; background: #2c3e50; padding: 10px; z-index: 1000; }}
        .top-controls {{ display: flex; justify-content: center; gap: 10px; margin-bottom: 8px; }}
        .middle-row {{ display: flex; align-items: center; margin-bottom: 8px; }}
        .time-info {{ width: 10%; color: white; font-weight: bold; display: flex; gap: 5px; }}
        .progress-section {{ width: 85%; margin-left: 2%; }}
        .progress-container {{ width: 100%; height: 8px; background: #34495e; border-radius: 4px; cursor: pointer; }}
        .progress-bar {{ height: 100%; background: #e74c3c; border-radius: 4px; width: 0%; transition: width 0.1s; }}
        .bottom-info {{ text-align: center; color: white; font-size: 12px; }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div class="legend" id="legend">
        <div style="font-weight: bold; margin-bottom: 5px;">All Station QSOs</div>
        <div class="legend-item">
            <div class="legend-color" style="background: #e8e8e8;"></div>
            <span>0</span>
        </div>
    </div>
    
    <div class="control-panel">
        <div class="top-controls">
            <button class="control-btn" id="playBtn" onclick="togglePlay()">▶ Play</button>
            <button class="control-btn" id="resetBtn" onclick="resetAnimation()">⏮ Reset</button>
            <button class="control-btn" id="speedBtn" onclick="cycleSpeed()">Speed 1x</button>
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
            <span id="statusDisplay">NYQP 2025 All Station Activity | QSOs: 0 | Active Counties: 0</span>
        </div>
    </div>

    <script>
        // Data
        const countyNames = {json.dumps(county_names, indent=8)};
        const boundariesData = {json.dumps(boundaries_data)};
        const allQSOs = {json.dumps(all_qsos, indent=8)};
        
        // Animation variables
        let map, isPlaying = false, animationInterval;
        let currentTime = new Date('2025-10-18T14:00:00Z');
        const startTime = new Date('2025-10-18T14:00:00Z');
        const endTime = new Date('2025-10-19T02:00:00Z');
        const countyCoords = {{}};
        let countyLayer;
        
        // Speed system
        const baseSpeed = 10;
        const speedMultipliers = [1, 5, 10, 50];
        let currentMultiplierIndex = 0;
        let speedMultiplier = speedMultipliers[currentMultiplierIndex];
        
        // Function to get county abbreviation from full name
        function getCountyAbbrev(fullName) {{
            for (const [abbrev, name] of Object.entries(countyNames)) {{
                if (name === fullName + " County") {{
                    return abbrev;
                }}
            }}
            return fullName.substring(0, 3).toUpperCase();
        }}
        
        // Function to update legend
        function updateLegend(maxQSOs) {{
            const legend = document.getElementById('legend');
            const colorConfig = getColorConfig(maxQSOs);
            const ranges = colorConfig.getRanges();
            
            legend.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 5px;">All Station QSOs</div>
                ${{ranges.map(r => `
                    <div class="legend-item">
                        <div class="legend-color" style="background: ${{r.color}};"></div>
                        <span>${{r.label}}</span>
                    </div>
                `).join('')}}`;
        }}
        
        // Single function that defines color ranges and thresholds
        function getColorConfig(maxCount) {{
            const thresholds = [0.05, 0.15, 0.35, 0.65, 1.0];
            const colors = ['#e8e8e8', '#ffff99', '#d4a574', '#ff8c42', '#ff4444', '#cc0000'];
            
            return {{
                getColor: function(qsoCount) {{
                    if (qsoCount === 0) return colors[0];
                    if (maxCount === 0) return colors[0];
                    
                    const ratio = qsoCount / maxCount;
                    for (let i = 0; i < thresholds.length; i++) {{
                        if (ratio <= thresholds[i]) {{
                            return colors[i + 1];
                        }}
                    }}
                    return colors[colors.length - 1];
                }},
                getRanges: function() {{
                    if (maxCount === 0) {{
                        return [{{ color: colors[0], label: '0' }}];
                    }}
                    
                    const ranges = [{{ color: colors[0], label: '0' }}];
                    let prevThreshold = 0;
                    
                    for (let i = 0; i < thresholds.length; i++) {{
                        const start = Math.ceil(maxCount * prevThreshold) + (prevThreshold > 0 ? 1 : 1);
                        const end = Math.ceil(maxCount * thresholds[i]);
                        ranges.push({{
                            color: colors[i + 1],
                            label: i === thresholds.length - 1 ? `${{start}}-${{maxCount}}` : `${{start}}-${{end}}`
                        }});
                        prevThreshold = thresholds[i];
                    }}
                    
                    return ranges;
                }}
            }};
        }}
        
        // Initialize map
        function initMap() {{
            map = L.map('map').setView([43.0, -76.0], 7);
            
            // Create NY state boundary merge
            const allFeatures = boundariesData.features;
            let merged = allFeatures[0];
            for (let i = 1; i < allFeatures.length; i++) {{
                try {{
                    merged = turf.union(merged, allFeatures[i]);
                }} catch(e) {{
                    console.log('Union failed for feature', i, e);
                }}
            }}
            
            // White background tile layer
            L.tileLayer('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=', {{
                attribution: ''
            }}).addTo(map);
            
            // Add county layers
            countyLayer = L.geoJSON(boundariesData, {{
                style: function(feature) {{
                    return {{
                        fillColor: '#e8e8e8',
                        weight: 0.5,
                        opacity: 0.8,
                        color: '#666',
                        fillOpacity: 1.0
                    }};
                }},
                onEachFeature: function(feature, layer) {{
                    const countyName = feature.properties.NAME;
                    const countyAbbrev = getCountyAbbrev(countyName);
                    
                    layer.bindPopup(`<b>${{countyAbbrev}}</b><br>${{countyName}} County<br>QSOs: 0<br><br>Top Stations:<br>No activity yet`);
                    
                    layer.countyName = countyName;
                    layer.countyAbbrev = countyAbbrev;
                }}
            }}).addTo(map);
            
            // Add mask and state outline
            if (merged) {{
                const worldPolygon = turf.bboxPolygon([-180, -90, 180, 90]);
                
                try {{
                    const mask = turf.difference(worldPolygon, merged);
                    if (mask) {{
                        L.geoJSON(mask, {{
                            style: {{
                                fillColor: 'white',
                                fillOpacity: 1,
                                weight: 0,
                                stroke: false
                            }},
                            interactive: false,
                            pane: 'overlayPane'
                        }}).addTo(map);
                    }}
                }} catch(e) {{
                    console.log('Mask creation failed:', e);
                }}
                
                L.geoJSON(merged, {{
                    style: {{
                        fillColor: 'transparent',
                        weight: 3,
                        opacity: 1,
                        color: '#1a252f',
                        fillOpacity: 0
                    }},
                    interactive: false
                }}).addTo(map);
            }}
            
            // Calculate county coordinates
            boundariesData.features.forEach(feature => {{
                const countyName = feature.properties.NAME;
                const fullCountyName = countyName + " County";
                const bbox = turf.bbox(feature);
                const centerLon = (bbox[0] + bbox[2]) / 2;
                const centerLat = (bbox[1] + bbox[3]) / 2;
                countyCoords[fullCountyName] = [centerLat, centerLon];
            }});
            
            resetAnimation();
        }}
        
        // Load QSO data and update display
        function updateDisplay() {{
            // Update time display
            document.getElementById('dateDisplay').textContent = currentTime.toISOString().split('T')[0];
            document.getElementById('timeDisplay').textContent = currentTime.toISOString().split('T')[1].substring(0, 5) + 'Z';
            
            // Update progress bar
            const totalDuration = endTime - startTime;
            const elapsed = currentTime - startTime;
            const progress = Math.max(0, Math.min(100, (elapsed / totalDuration) * 100));
            document.getElementById('progressBar').style.width = progress + '%';
            
            // Process QSO data up to current time
            const countyQSOs = {{}};
            const countyStations = {{}};
            let totalQSOs = 0;
            
            allQSOs.forEach(qso => {{
                const qsoTime = new Date(qso.t + 'Z');
                if (qsoTime < currentTime && qsoTime >= startTime) {{
                    const fullCountyName = countyNames[qso.c];
                    if (fullCountyName) {{
                        // Count QSOs per county
                        countyQSOs[fullCountyName] = (countyQSOs[fullCountyName] || 0) + 1;
                        
                        // Track stations per county
                        if (!countyStations[fullCountyName]) {{
                            countyStations[fullCountyName] = {{}};
                        }}
                        countyStations[fullCountyName][qso.s] = (countyStations[fullCountyName][qso.s] || 0) + 1;
                        
                        totalQSOs++;
                    }}
                }}
            }});
            
            // Find maximum QSO count for scaling
            const maxQSOs = Math.max(0, ...Object.values(countyQSOs));
            
            // Update legend
            updateLegend(maxQSOs);
            
            // Update county layer colors and tooltips
            countyLayer.eachLayer(layer => {{
                const countyName = layer.countyName;
                const countyAbbrev = layer.countyAbbrev;
                const fullCountyName = countyName + " County";
                const qsoCount = countyQSOs[fullCountyName] || 0;
                
                const colorConfig = getColorConfig(maxQSOs);
                
                layer.setStyle({{
                    fillColor: colorConfig.getColor(qsoCount)
                }});
                
                // Get top 5 stations for this county
                let topStationsText = "No activity yet";
                if (countyStations[fullCountyName]) {{
                    const stations = Object.entries(countyStations[fullCountyName])
                        .sort((a, b) => b[1] - a[1])
                        .slice(0, 5);
                    
                    if (stations.length > 0) {{
                        topStationsText = stations.map(([call, count]) => `${{call}}: ${{count}}`).join('<br>');
                    }}
                }}
                
                layer.getPopup().setContent(
                    `<b>${{countyAbbrev}}</b><br>${{countyName}} County<br>QSOs: ${{qsoCount}}<br><br>Top Stations:<br>${{topStationsText}}`
                );
            }});
            
            // Count active counties
            const activeCounties = Object.keys(countyQSOs).length;
            
            document.getElementById('statusDisplay').textContent = 
                `NYQP 2025 All Station Activity | QSOs: ${{totalQSOs}} | Active Counties: ${{activeCounties}}`;
        }}
        
        function togglePlay() {{
            if (isPlaying) {{
                clearInterval(animationInterval);
                document.getElementById('playBtn').innerHTML = '▶ Play';
                isPlaying = false;
            }} else {{
                animationInterval = setInterval(() => {{
                    currentTime = new Date(currentTime.getTime() + (1 * 60 * 1000));
                    if (currentTime > endTime) {{
                        currentTime = endTime;
                        togglePlay();
                    }}
                    updateDisplay();
                }}, 1000 / speedMultiplier);
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
            currentMultiplierIndex = (currentMultiplierIndex + 1) % speedMultipliers.length;
            speedMultiplier = speedMultipliers[currentMultiplierIndex];
            document.getElementById('speedBtn').textContent = `Speed ${{speedMultiplier}}x`;
            
            if (isPlaying) {{
                clearInterval(animationInterval);
                animationInterval = setInterval(() => {{
                    currentTime = new Date(currentTime.getTime() + (1 * 60 * 1000));
                    if (currentTime > endTime) {{
                        currentTime = endTime;
                        togglePlay();
                    }}
                    updateDisplay();
                }}, 1000 / speedMultiplier);
            }}
        }}
        
        function seekToPosition(event) {{
            const rect = event.target.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const percentage = x / rect.width;
            const totalDuration = endTime - startTime;
            currentTime = new Date(startTime.getTime() + (percentage * totalDuration));
            updateDisplay();
        }}
        
        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', initMap);
    </script>

</body></html>'''
    
    output_file = Path('../outputs/nyqp_2025_all_NY_station_animation.html')
    with open(output_file, 'w') as f:
        f.write(html_content)
        
    print(f"All station animation generated: {output_file}")

if __name__ == "__main__":
    generate_all_qso_animation()
