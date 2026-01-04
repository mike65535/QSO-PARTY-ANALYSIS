#!/usr/bin/env python3

import json
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.animation_controls import get_controls_html, get_controls_css, get_controls_js
from lib.animation_legend import get_legend_html, get_legend_css, get_legend_js

# Configuration constants
MAP_CENTER = [39.8, -98.6]
MAP_ZOOM = 4
ANIMATION_SPEEDS = [1, 5, 10, 50]
COLOR_THRESHOLDS = [0, 0.05, 0.15, 0.35, 0.65]
COLOR_PALETTE = ['#f0f0f0', '#d4c5a9', '#f4e4a6', '#f7b32b', '#d73027', '#a50f15']
ALASKA_SCALE_FACTOR = 0.44
EXCLUDED_STATES = ['Alaska', 'Hawaii', 'Puerto Rico']

def get_state_mapping():
    """Return state name to abbreviation mapping"""
    return {
        'Alabama': 'AL', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
        'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL',
        'Georgia': 'GA', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN',
        'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA',
        'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI',
        'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT',
        'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
        'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND',
        'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA',
        'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN',
        'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA',
        'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
        'District of Columbia': 'DC'
    }

def generate_state_animation_html(host_state='NY', output_file='outputs/nyqp_2025_all_US_station_animation.html'):
    """Generate state-level QSO animation HTML"""
    
    # Load contest metadata
    with open('data/contest_metadata.json', 'r') as f:
        contest_meta = json.load(f)
    
    # Load animation data
    with open('outputs/state_qso_animation_data.json', 'r') as f:
        animation_data = json.load(f)
    
    # Load US boundaries
    with open('data/us-states-boundaries.json', 'r') as f:
        boundaries_data = json.load(f)
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NYQP 2025 - US State QSO Animation</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/@turf/turf@6/turf.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #map {{ height: 100vh; width: 100%; }}
        {get_controls_css()}
        {get_legend_css()}
        button {{ margin: 0 3px; padding: 8px 12px; border: none; border-radius: 4px; background: #007cba; color: white; cursor: pointer; }}
        button:hover {{ background: #005a87; }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    {get_controls_html()}
    
    {get_legend_html()}
    
    <script>
        const animationData = {json.dumps(animation_data)};
        const boundariesData = {json.dumps(boundaries_data)};
        const contestMeta = {json.dumps(contest_meta)};
        const hostState = '{host_state}';
        
        let map, stateLayer;
        {get_controls_js(str(ANIMATION_SPEEDS))}
        {get_legend_js(str(COLOR_THRESHOLDS), str(COLOR_PALETTE), "QSOs per State")}
        
        // Initialize map
        map = L.map('map').setView({MAP_CENTER}, {MAP_ZOOM});
        
        // White background
        L.tileLayer('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=').addTo(map);
        
        // Filter to lower 48 states
        const lower48Features = boundariesData.features.filter(feature => {{
            const stateName = feature.properties.name || '';
            return !{EXCLUDED_STATES}.includes(stateName);
        }});
        
        // Add state layer
        stateLayer = L.geoJSON({{type: "FeatureCollection", features: lower48Features}}, {{
            style: getStateStyle,
            onEachFeature: function(feature, layer) {{
                const stateName = feature.properties.name || 'Unknown';
                layer.bindPopup(`<b>${{stateName}}</b><br>QSOs: <span id="popup-${{feature.id}}">0</span>`);
            }}
        }}).addTo(map);
        
        // Fit map to bounds
        map.fitBounds(stateLayer.getBounds(), {{padding: [20, 20]}});
        
        // Add Alaska and Hawaii insets
        addInsets();
        
        function getStateStyle(feature) {{
            const stateName = feature.properties.name;
            const stateCode = getStateCode(stateName);
            const frame = animationData.frames[currentFrame];
            const qsoCount = frame && frame.states[stateCode] || 0;
            
            return {{
                fillColor: getColor(qsoCount),
                weight: 0.5,
                opacity: 0.8,
                color: '#666',
                fillOpacity: 0.7
            }};
        }}
        
        function getStateCode(stateName) {{
            const stateMap = {json.dumps(get_state_mapping())};
            return stateMap[stateName] || stateName;
        }}
        
        
        function updateFrame() {{
            const frame = animationData.frames[currentFrame];
            
            // Use the date from the frame data
            document.getElementById('dateDisplay').textContent = frame.date;
            document.getElementById('timeDisplay').textContent = frame.time + 'Z';
            document.getElementById('progressBar').style.width = ((currentFrame / (animationData.frames.length - 1)) * 100) + '%';
            
            const totalQsos = Object.values(frame.states || {{}}).reduce((sum, count) => sum + count, 0);
            const usStateCodes = new Set(['AL','AZ','AR','CA','CO','CT','DE','FL','GA','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']);
            const usStates = Object.keys(frame.states || {{}}).filter(state => {{
                return usStateCodes.has(state) && frame.states[state] > 0;
            }});
            const activeStates = usStates.length;
            document.getElementById('statusDisplay').textContent = `${{contestMeta.contest_name}} US State Activity | QSOs: ${{totalQsos}} | Active States: ${{activeStates}}`;
            
            // Update state colors - exclude host state from scaling to prevent outlier dominance
            const stateValues = Object.values(frame.states || {{}});
            const nonHostValues = Object.entries(frame.states || {{}})
                .filter(([state, count]) => state !== hostState)
                .map(([state, count]) => count);
            const maxQSOs = nonHostValues.length > 0 ? Math.max(...nonHostValues) : 1;
            
            stateLayer.eachLayer(layer => {{
                const stateName = layer.feature.properties.name;
                const stateCode = getStateCode(stateName);
                const qsoCount = frame.states[stateCode] || 0;
                
                layer.setStyle({{
                    fillColor: getColor(qsoCount, maxQSOs)
                }});
                
                // Update tooltip
                layer.bindPopup(`<b>${{stateName}}</b><br>QSOs: ${{qsoCount}}`);
            }});
            
            updateLegend(maxQSOs);
        }}
        
        function updateLegend(maxCount) {{
            const thresholds = {COLOR_THRESHOLDS}.map(t => maxCount * t);
            const colors = {COLOR_PALETTE};
            
            let legendHtml = '<h4 style="margin: 0 0 10px 0; font-size: 14px;">QSOs per State</h4>';
            for (let i = 0; i < colors.length; i++) {{
                const min = i === 0 ? 0 : Math.round(thresholds[i - 1]) + 1;
                const max = i < thresholds.length ? Math.round(thresholds[i]) : Math.round(maxCount);
                legendHtml += `<div class="legend-item">
                    <div class="legend-color" style="background-color: ${{colors[i]}}"></div>
                    <span style="font-size: 12px;">${{min}} - ${{max}}</span>
                </div>`;
            }}
            document.getElementById('legend').innerHTML = legendHtml;
        }}
        
        
        function addInsets() {{
            const alaskaFeature = boundariesData.features.find(f => f.properties.name === 'Alaska');
            const hawaiiFeature = boundariesData.features.find(f => f.properties.name === 'Hawaii');
            
            const insetControl = L.control({{position: 'bottomleft'}});
            insetControl.onAdd = function() {{
                const div = L.DomUtil.create('div', 'insets');
                div.style.marginBottom = '120px';
                div.innerHTML = `
                    <div style="background:white;border:1px solid #666;margin:5px;padding:5px;width:170px;height:140px;box-sizing:border-box;">
                        <div style="font-size:12px;margin-bottom:2px;">Alaska</div>
                        <svg width="162" height="120" viewBox="-84 -75 22 30" preserveAspectRatio="xMidYMid meet" style="width:162px;height:120px;display:block;">
                            <path d="${{alaskaFeature ? getPathFromCoords(alaskaFeature.geometry.coordinates, true) : ''}}" 
                                  fill="#e8e8e8" stroke="#666" stroke-width="0.2"/>
                        </svg>
                    </div>
                    <div style="background:white;border:1px solid #666;margin:5px;padding:5px;width:170px;height:90px;box-sizing:border-box;">
                        <div style="font-size:12px;margin-bottom:2px;">Hawaii</div>
                        <svg width="160" height="80" viewBox="-161 -23 6 6">
                            <path d="${{hawaiiFeature ? getPathFromCoords(hawaiiFeature.geometry.coordinates) : ''}}" 
                                  fill="#e8e8e8" stroke="#666" stroke-width="0.1"/>
                        </svg>
                    </div>
                `;
                return div;
            }};
            insetControl.addTo(map);
        }}
        
        function getPathFromCoords(coords, isAlaska = false) {{
            if (!coords || coords.length === 0) return '';
            const paths = [];
            if (coords[0][0][0] && Array.isArray(coords[0][0][0])) {{
                coords.forEach(polygon => {{
                    polygon.forEach(ring => {{
                        if (isAlaska) {{
                            paths.push('M' + ring.map(p => (p[0] * {ALASKA_SCALE_FACTOR}) + ',' + (-p[1])).join('L') + 'Z');
                        }} else {{
                            paths.push('M' + ring.map(p => p[0] + ',' + (-p[1])).join('L') + 'Z');
                        }}
                    }});
                }});
            }} else {{
                coords.forEach(ring => {{
                    if (isAlaska) {{
                        paths.push('M' + ring.map(p => (p[0] * {ALASKA_SCALE_FACTOR}) + ',' + (-p[1])).join('L') + 'Z');
                    }} else {{
                        paths.push('M' + ring.map(p => p[0] + ',' + (-p[1])).join('L') + 'Z');
                    }}
                }});
            }}
            return paths.join(' ');
        }}
        
        // Initialize
        updateFrame();
    </script>
</body>
</html>'''
    
    with open('outputs/nyqp_2025_all_US_station_animation.html', 'w') as f:
        f.write(html_content)
    
    print("US state animation generated: outputs/nyqp_2025_all_US_station_animation.html")

if __name__ == "__main__":
    generate_state_animation_html()
