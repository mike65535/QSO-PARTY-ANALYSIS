#!/usr/bin/env python3

import json

def generate_us_map_html(output_path="outputs/us_map_standalone.html"):
    """Generate a standalone US map HTML file with Alaska and Hawaii insets"""
    
    # Load boundaries data
    with open('data/us-states-boundaries.json', 'r') as f:
        boundaries_data = json.load(f)
    
    html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>US State Map - Standalone</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/@turf/turf@6/turf.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #map {{ height: 100vh; width: 100%; }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <script>
        // Embedded US state boundaries data
        const boundariesData = {json.dumps(boundaries_data)};
        
        // Initialize map centered on lower 48 states
        const map = L.map('map').setView([39.8, -98.6], 4);
        
        // Filter to lower 48 states only (exclude Alaska, Hawaii, Puerto Rico, territories)
        const lower48Features = boundariesData.features.filter(feature => {{
            const stateName = feature.properties.NAME || feature.properties.name || '';
            const excludeStates = ['Alaska', 'Hawaii', 'Puerto Rico', 'American Samoa', 'Guam', 'Northern Mariana Islands', 'U.S. Virgin Islands'];
            return !excludeStates.includes(stateName);
        }});
        
        // Create US boundary merge from lower 48 only
        let merged = null;
        if (lower48Features.length > 0) {{
            merged = lower48Features[0];
            for (let i = 1; i < lower48Features.length; i++) {{
                try {{
                    merged = turf.union(merged, lower48Features[i]);
                }} catch(e) {{
                    console.log('Union failed for feature', i, e);
                }}
            }}
        }}
        
        // White background tile layer
        L.tileLayer('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=', {{
            attribution: ''
        }}).addTo(map);
        
        // Add lower 48 states only
        if (lower48Features.length > 0) {{
            L.geoJSON({{type: "FeatureCollection", features: lower48Features}}, {{
                style: {{
                    fillColor: '#e8e8e8',
                    weight: 0.5,
                    opacity: 0.8,
                    color: '#666',
                    fillOpacity: 0.7
                }},
                onEachFeature: function(feature, layer) {{
                    const stateName = feature.properties.NAME || feature.properties.name || 'Unknown';
                    layer.bindPopup(`<b>${{stateName}}</b>`);
                }},
                interactive: true
            }}).addTo(map);
            
            // Add mask layer (white background outside US)
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
                
                // Add US boundary outline (using merged shape, not individual states)
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
            
            // Fit map to lower 48 bounds only
            const bounds = L.geoJSON({{type: "FeatureCollection", features: lower48Features}}).getBounds();
            map.fitBounds(bounds, {{padding: [20, 20]}});
        }} else {{
            console.log('No boundary data available');
        }}
        
        // Add Alaska and Hawaii as SVG insets
        const alaskaFeature = boundariesData.features.find(f => f.properties.name === 'Alaska');
        const hawaiiFeature = boundariesData.features.find(f => f.properties.name === 'Hawaii');
        
        const insetControl = L.control({{position: 'bottomleft'}});
        insetControl.onAdd = function() {{
            const div = L.DomUtil.create('div', 'insets');
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
        
        function getPathFromCoords(coords, isAlaska = false) {{
            if (!coords || coords.length === 0) return '';
            const paths = [];
            if (coords[0][0][0] && Array.isArray(coords[0][0][0])) {{
                // MultiPolygon
                coords.forEach(polygon => {{
                    polygon.forEach(ring => {{
                        if (isAlaska) {{
                            // Apply latitude scaling for Alaska (cos of average latitude ~64°)
                            paths.push('M' + ring.map(p => (p[0] * 0.44) + ',' + (-p[1])).join('L') + 'Z');
                        }} else {{
                            paths.push('M' + ring.map(p => p[0] + ',' + (-p[1])).join('L') + 'Z');
                        }}
                    }});
                }});
            }} else {{
                // Polygon
                coords.forEach(ring => {{
                    if (isAlaska) {{
                        // Apply latitude scaling for Alaska
                        paths.push('M' + ring.map(p => (p[0] * 0.44) + ',' + (-p[1])).join('L') + 'Z');
                    }} else {{
                        paths.push('M' + ring.map(p => p[0] + ',' + (-p[1])).join('L') + 'Z');
                    }}
                }});
            }}
            return paths.join(' ');
        }}
        
        console.log('US state boundaries loaded');
    </script>
</body>
</html>'''
    
    with open(output_path, 'w') as f:
        f.write(html_template)
    
    print(f"US map generated: {output_path}")

if __name__ == "__main__":
    generate_us_map_html()
