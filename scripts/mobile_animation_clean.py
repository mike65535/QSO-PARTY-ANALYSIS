#!/usr/bin/env python3
"""
Clean Mobile Animation Generator - uses pre-computed county-line periods
"""

import json
import sqlite3
from pathlib import Path

def generate_mobile_animation():
    """Generate mobile animation HTML using pre-computed periods"""
    
    # Load boundaries data to embed
    boundaries_path = Path('../data/ny-counties-boundaries.json')
    with open(boundaries_path, 'r') as f:
        boundaries_data = json.load(f)
        
    # Load county-line periods
    periods_path = Path('../outputs/county_line_periods.json')
    with open(periods_path, 'r') as f:
        county_line_periods = json.load(f)
        
    # Load mobile QSO data
    db_path = Path('../data/ny_mobiles.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT callsign FROM mobile_stations")
    mobile_callsigns = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Load QSO data
    qso_db_path = Path('../data/contest_qsos.db')
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
    
    # County names mapping
    county_names = {
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
    }
    
    # Mobile icons
    mobile_icons = {
        'AB1BL': '🚗', 'K2A': '🚙', 'K2Q': '🚐', 'K2V': '🚛', 'KQ2R': '🏎️',
        'KV2X': '🚓', 'N1GBE': '🚑', 'N2B': '🚒', 'N2CU': '🚌', 'N2T': '🚚',
        'W1WV': '🛻', 'WI2M': '🚜', 'WT2X': '🏍️', 'KV2X/M': '🚕', 'W1WV/M': '🚖'
    }
    
    # Generate HTML
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NYQP Mobile Animation</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/@turf/turf@6/turf.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #map {{ height: 95vh; width: 100%; background-color: white; margin-top: -5vh; }}
        .leaflet-top {{ top: 40px; }} /* Move zoom controls down */
        
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
        .mobile-marker {{ background: none; border: none; }}
        .mobile-icon {{ font-size: 20px; text-align: center; line-height: 20px; color: #000; font-weight: bold; text-shadow: 1px 1px 2px #fff; }}
        .mobile-label {{ font-size: 10px; font-weight: bold; text-align: center; color: #000; text-shadow: 1px 1px 2px #fff; }}
        .mobile-label {{ font-size: 10px; text-align: center; color: #333; text-shadow: 1px 1px 1px white; }}
        
        .control-btn {{ padding: 8px 12px; border: none; border-radius: 6px; background: #3498db; color: white; cursor: pointer; font-size: 14px; }}
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
        <div style="font-weight: bold; margin-bottom: 5px;">Mobile QSOs</div>
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
            <span id="statusDisplay">NYQP 2025 Mobile Activity | QSOs: 0 | Counties Covered: 0</span>
        </div>
    </div>

    <script>
        // Data
        const mobileData = {json.dumps(mobile_data, indent=8)};
        const countyLinePeriods = {json.dumps(county_line_periods, indent=8)};
        const countyNames = {json.dumps(county_names, indent=8)};
        const mobileIcons = {json.dumps(mobile_icons, indent=8)};
        const boundariesData = {json.dumps(boundaries_data)};
        
        // Animation variables
        let map, mobileMarkers = {{}}, isPlaying = false, animationInterval;
        let currentTime = new Date('2025-10-18T14:00:00Z');
        const startTime = new Date('2025-10-18T14:00:00Z');
        const endTime = new Date('2025-10-19T02:00:00Z');
        const countyCoords = {{}};
        let countyLayer; // Store county layer reference
        
        // Function to get county abbreviation from full name
        function getCountyAbbrev(fullName) {{
            for (const [abbrev, name] of Object.entries(countyNames)) {{
                if (name === fullName + " County") {{
                    return abbrev;
                }}
            }}
            return fullName.substring(0, 3).toUpperCase(); // Fallback
        }}
        
        // Function to update legend
        function updateLegend(maxQSOs) {{
            const legend = document.getElementById('legend');
            if (maxQSOs === 0) {{
                legend.innerHTML = `
                    <div style="font-weight: bold; margin-bottom: 5px;">Mobile QSOs</div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #e8e8e8;"></div>
                        <span>0</span>
                    </div>`;
                return;
            }}
            
            const ranges = [
                {{ color: '#e8e8e8', label: '0' }},
                {{ color: '#ffff99', label: `1-${{Math.ceil(maxQSOs * 0.2)}}` }},
                {{ color: '#d4a574', label: `${{Math.ceil(maxQSOs * 0.2) + 1}}-${{Math.ceil(maxQSOs * 0.4)}}` }},
                {{ color: '#ff8c42', label: `${{Math.ceil(maxQSOs * 0.4) + 1}}-${{Math.ceil(maxQSOs * 0.6)}}` }},
                {{ color: '#ff4444', label: `${{Math.ceil(maxQSOs * 0.6) + 1}}-${{Math.ceil(maxQSOs * 0.8)}}` }},
                {{ color: '#cc0000', label: `${{Math.ceil(maxQSOs * 0.8) + 1}}-${{maxQSOs}}` }}
            ];
            
            legend.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 5px;">Mobile QSOs</div>
                ${{ranges.map(r => `
                    <div class="legend-item">
                        <div class="legend-color" style="background: ${{r.color}};"></div>
                        <span>${{r.label}}</span>
                    </div>
                `).join('')}}`;
        }}
        function getCountyColor(qsoCount, maxCount) {{
            if (qsoCount === 0) return '#e8e8e8';      // Gray - no QSOs
            if (maxCount === 0) return '#e8e8e8';
            
            const ratio = qsoCount / maxCount;
            if (ratio <= 0.2) return '#ffff99';        // Light yellow - 0-20%
            if (ratio <= 0.4) return '#d4a574';        // Tan - 20-40%
            if (ratio <= 0.6) return '#ff8c42';        // Orange - 40-60%
            if (ratio <= 0.8) return '#ff4444';        // Red - 60-80%
            return '#cc0000';                          // Dark red - 80-100%
        }}
        
        // Speed system - simple base speed and multiplier
        const baseSpeed = 10; // 10 minutes per second at 1x
        const speedMultipliers = [5, 25, 50, 250];
        let currentMultiplierIndex = 0;
        let speedMultiplier = speedMultipliers[currentMultiplierIndex];
        
        // Initialize map
        function initMap() {{
            map = L.map('map').setView([43.0, -76.0], 7);
            
            // Create NY state boundary merge (union all counties into one shape)
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
            
            // Add county layers with thin borders
            countyLayer = L.geoJSON(boundariesData, {{
                style: function(feature) {{
                    return {{
                        fillColor: '#e8e8e8',
                        weight: 0.5,
                        opacity: 0.8,
                        color: '#666',
                        fillOpacity: 0.7
                    }};
                }},
                onEachFeature: function(feature, layer) {{
                    const countyName = feature.properties.NAME;
                    const countyAbbrev = getCountyAbbrev(countyName);
                    
                    layer.bindPopup(`<b>${{countyAbbrev}}</b><br>${{countyName}} County<br>Mobile QSOs: 0`);
                    
                    // Store reference for updates
                    layer.countyName = countyName;
                    layer.countyAbbrev = countyAbbrev;
                }}
            }}).addTo(map);
            
            // Add mask layer (white background outside NY)
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
                
                // Add NY state boundary outline (using merged shape, not individual counties)
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
            
            createMobileMarkers();
            resetAnimation(); // Call reset to ensure proper initial positioning
        }}
        
        // Create mobile markers
        function createMobileMarkers() {{
            for (const [call, qsos] of Object.entries(mobileData)) {{
                if (qsos.length === 0) continue;
                
                // Check if station has QSO in first hour (14:00-15:00Z)
                const firstHourEnd = new Date('2025-10-18T15:00:00Z');
                const hasFirstHourQSO = qsos.some(qso => {{
                    const qsoTime = new Date(qso.timestamp + 'Z');
                    return qsoTime <= firstHourEnd;
                }});
                
                const iconSymbol = mobileIcons[call] || '📍';
                const icon = L.divIcon({{
                    html: `<div class="mobile-icon">${{iconSymbol}}</div><div class="mobile-label">${{call}}</div>`,
                    className: 'mobile-marker',
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                }});
                
                // Position marker - same logic as reset
                const periods = countyLinePeriods[call] || [];
                let coords;
                
                if (periods.length > 0) {{
                    // Station has county line periods - position between first period's counties
                    const firstPeriod = periods[0];
                    const county1Name = countyNames[firstPeriod.counties[0]];
                    const county2Name = countyNames[firstPeriod.counties[1]];
                    const coords1 = countyCoords[county1Name] || [42.9, -75.5];
                    const coords2 = countyCoords[county2Name] || [42.9, -75.5];
                    coords = [(coords1[0] + coords2[0]) / 2, (coords1[1] + coords2[1]) / 2];
                }} else {{
                    // Regular station - use first QSO county
                    coords = getStationCoords(call, currentTime);
                }}
                
                const marker = L.marker(coords, {{ icon, riseOnHover: true }});
                
                // Set initial popup content
                if (periods.length > 0) {{
                    const firstPeriod = periods[0];
                    const countyDisplay = firstPeriod.counties.join('/');
                    marker.bindPopup(`<b>${{call}}</b><br>County: ${{countyDisplay}}<br>QSOs: 0`);
                }} else if (qsos.length > 0) {{
                    const firstCounty = qsos[0].county;
                    marker.bindPopup(`<b>${{call}}</b><br>County: ${{firstCounty}}<br>QSOs: 0`);
                }} else {{
                    marker.bindPopup(`<b>${{call}}</b><br>Initializing...`);
                }}
                
                mobileMarkers[call] = marker;
                marker.addTo(map);
                
                // Set initial visibility based on first hour QSO
                if (!hasFirstHourQSO) {{
                    marker.setOpacity(0); // Hide if no first hour QSO
                }}
            }}
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
                    const county1Name = countyNames[period.counties[0]];
                    const county2Name = countyNames[period.counties[1]];
                    const coords1 = countyCoords[county1Name] || [42.9, -75.5];
                    const coords2 = countyCoords[county2Name] || [42.9, -75.5];
                    return [(coords1[0] + coords2[0]) / 2, (coords1[1] + coords2[1]) / 2];
                }}
            }}
            
            // If station has county line periods but not currently in one,
            // check if we're after any period - if so, stay at last county line position
            if (periods.length > 0) {{
                let lastPeriod = null;
                for (const period of periods) {{
                    const startTime = new Date(period.start_time + 'Z');
                    if (time >= startTime) {{
                        lastPeriod = period;
                    }}
                }}
                
                if (lastPeriod) {{
                    // Position at the last county line we were on
                    const county1Name = countyNames[lastPeriod.counties[0]];
                    const county2Name = countyNames[lastPeriod.counties[1]];
                    const coords1 = countyCoords[county1Name] || [42.9, -75.5];
                    const coords2 = countyCoords[county2Name] || [42.9, -75.5];
                    return [(coords1[0] + coords2[0]) / 2, (coords1[1] + coords2[1]) / 2];
                }}
            }}
            
            // Not on county line - find current county from QSOs
            const qsos = mobileData[callsign] || [];
            let currentCounty = null;
            
            // Find the most recent QSO county at or before this time
            for (const qso of qsos) {{
                const qsoTime = new Date(qso.timestamp + 'Z');
                if (qsoTime <= time) {{
                    currentCounty = qso.county;
                }} else {{
                    break;
                }}
            }}
            
            // If no QSO yet, use first QSO county
            if (!currentCounty && qsos.length > 0) {{
                currentCounty = qsos[0].county;
            }}
            
            if (currentCounty) {{
                const fullCountyName = countyNames[currentCounty];
                const baseCoords = countyCoords[fullCountyName] || [42.9, -75.5];
                
                // Add offset to spread out stations in same county
                const stationIndex = Object.keys(mobileData).indexOf(callsign);
                const offsetLat = (stationIndex % 3 - 1) * 0.05;
                const offsetLon = (Math.floor(stationIndex / 3) % 3 - 1) * 0.05;
                
                return [baseCoords[0] + offsetLat, baseCoords[1] + offsetLon];
            }}
            
            return [42.9, -75.5]; // Default position
        }}
        
        // Check if station is on county line
        function isOnCountyLine(callsign, time) {{
            const periods = countyLinePeriods[callsign] || [];
            
            for (const period of periods) {{
                const startTime = new Date(period.start_time + 'Z');
                const endTime = new Date(period.end_time + 'Z');
                
                if (time >= startTime && time <= endTime) {{
                    return {{ isCountyLine: true, counties: period.counties }};
                }}
            }}
            
            return {{ isCountyLine: false, counties: [] }};
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
                    marker.setOpacity(1); // Show when active
                    
                    // Determine county display with abbreviations
                    const detection = isOnCountyLine(call, currentTime);
                    let countyDisplay = currentQSO.county;
                    
                    if (detection.isCountyLine) {{
                        countyDisplay = detection.counties.join('/');
                    }}
                    
                    const qsoCount = qsos.filter(q => new Date(q.timestamp + 'Z') < currentTime).length;
                    marker.getPopup().setContent(
                        `<b>${{call}}</b><br>County: ${{countyDisplay}}<br>QSOs: ${{qsoCount}}`
                    );
                }} else {{
                    // Check if should be visible (has first hour QSO or already made first QSO)
                    const firstHourEnd = new Date('2025-10-18T15:00:00Z');
                    const hasFirstHourQSO = qsos.some(qso => {{
                        const qsoTime = new Date(qso.timestamp + 'Z');
                        return qsoTime <= firstHourEnd;
                    }});
                    
                    if (hasFirstHourQSO) {{
                        marker.setOpacity(1); // Show if has first hour QSO
                    }} else {{
                        marker.setOpacity(0); // Hide until first QSO
                    }}
                }}
            }}
            
            // Update status
            const activeStations = Object.keys(mobileData).filter(call => {{
                const qsos = mobileData[call];
                return qsos.some(qso => new Date(qso.timestamp + 'Z') <= currentTime);
            }}).length;
            
            // Count unique counties covered and total QSOs
            const countiesCovered = new Set();
            let totalQSOs = 0;
            
            Object.values(mobileData).forEach(qsos => {{
                qsos.forEach(qso => {{
                    const qsoTime = new Date(qso.timestamp + 'Z');
                    if (qsoTime < currentTime) {{
                        countiesCovered.add(qso.county);
                        totalQSOs++;
                    }}
                }});
            }});
            
            // Update county colors and tooltips
            const countyQSOs = {{}};
            Object.values(mobileData).forEach(qsos => {{
                qsos.forEach(qso => {{
                    const qsoTime = new Date(qso.timestamp + 'Z');
                    if (qsoTime < currentTime) {{
                        const fullCountyName = countyNames[qso.county];
                        if (fullCountyName) {{
                            countyQSOs[fullCountyName] = (countyQSOs[fullCountyName] || 0) + 1;
                        }}
                    }}
                }});
            }});
            
            // Find maximum QSO count for scaling
            const maxQSOs = Math.max(0, ...Object.values(countyQSOs));
            
            // Update legend
            updateLegend(maxQSOs);
            
            // Update county layer colors and tooltips
            countyLayer.eachLayer(layer => {{
                const countyName = layer.countyName;
                const countyAbbrev = layer.countyAbbrev;
                const qsoCount = countyQSOs[countyName + " County"] || 0;
                
                layer.setStyle({{
                    fillColor: getCountyColor(qsoCount, maxQSOs)
                }});
                
                layer.getPopup().setContent(
                    `<b>${{countyAbbrev}}</b><br>${{countyName}} County<br>Mobile QSOs: ${{qsoCount}}`
                );
            }});
            
            document.getElementById('statusDisplay').textContent = 
                `NYQP 2025 Mobile Activity | QSOs: ${{totalQSOs}} | Counties Covered: ${{countiesCovered.size}}`;
        }}
        
        // Animation controls
        function togglePlay() {{
            if (isPlaying) {{
                clearInterval(animationInterval);
                document.getElementById('playBtn').innerHTML = '▶ Play';
                isPlaying = false;
            }} else {{
                animationInterval = setInterval(() => {{
                    currentTime = new Date(currentTime.getTime() + (1 * 60 * 1000)); // 1 minute steps
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
            
            // Force all markers to reset to their starting positions
            for (const [call, qsos] of Object.entries(mobileData)) {{
                const marker = mobileMarkers[call];
                if (!marker) continue;
                
                // Check if station has any county line periods (if so, position between counties)
                const periods = countyLinePeriods[call] || [];
                let coords;
                
                if (periods.length > 0) {{
                    // Station has county line periods - position between first period's counties
                    const firstPeriod = periods[0];
                    const county1Name = countyNames[firstPeriod.counties[0]];
                    const county2Name = countyNames[firstPeriod.counties[1]];
                    const coords1 = countyCoords[county1Name] || [42.9, -75.5];
                    const coords2 = countyCoords[county2Name] || [42.9, -75.5];
                    coords = [(coords1[0] + coords2[0]) / 2, (coords1[1] + coords2[1]) / 2];
                }} else {{
                    // Regular station - use first QSO county
                    coords = getStationCoords(call, currentTime);
                }}
                
                marker.setLatLng(coords);
                
                // Set popup content for all markers at reset
                if (periods.length > 0) {{
                    const firstPeriod = periods[0];
                    const countyDisplay = firstPeriod.counties.join('/');
                    marker.getPopup().setContent(`<b>${{call}}</b><br>County: ${{countyDisplay}}<br>QSOs: 0`);
                }} else if (qsos.length > 0) {{
                    const firstCounty = qsos[0].county;
                    marker.getPopup().setContent(`<b>${{call}}</b><br>County: ${{firstCounty}}<br>QSOs: 0`);
                }} else {{
                    marker.getPopup().setContent(`<b>${{call}}</b><br>Initializing...`);
                }}
                
                // Reset visibility based on first hour QSO
                const firstHourEnd = new Date('2025-10-18T15:00:00Z');
                const hasFirstHourQSO = qsos.some(qso => {{
                    const qsoTime = new Date(qso.timestamp + 'Z');
                    return qsoTime <= firstHourEnd;
                }});
                
                marker.setOpacity(hasFirstHourQSO ? 1 : 0);
            }}
            
            updateDisplay();
        }}
        
        function cycleSpeed() {{
            currentMultiplierIndex = (currentMultiplierIndex + 1) % speedMultipliers.length;
            speedMultiplier = speedMultipliers[currentMultiplierIndex];
            document.getElementById('speedBtn').textContent = `Speed ${{speedMultiplier}}x`;
            
            // Restart animation with new speed if currently playing
            if (isPlaying) {{
                clearInterval(animationInterval);
                animationInterval = setInterval(() => {{
                    currentTime = new Date(currentTime.getTime() + (1 * 60 * 1000)); // 1 minute steps
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
        
        // Initialize
        document.addEventListener('DOMContentLoaded', initMap);
    </script>
</body>
</html>'''
    
    output_file = Path('../outputs/mobile_animation_complete.html')
    with open(output_file, 'w') as f:
        f.write(html_content)
        
    print(f"Clean mobile animation generated: {output_file}")

if __name__ == "__main__":
    generate_mobile_animation()
