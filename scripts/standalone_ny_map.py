#!/usr/bin/env python3
"""
Standalone NY Map Generator with embedded boundaries data
Creates completely self-contained HTML files with no external dependencies
"""

import json
from pathlib import Path

def create_standalone_ny_map():
    """Create standalone NY map with embedded boundaries"""
    
    # Load boundaries data to embed
    boundaries_path = Path('../data/ny-counties-boundaries.json')
    with open(boundaries_path, 'r') as f:
        boundaries_data = json.load(f)
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NY State Map - Standalone</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/@turf/turf@6/turf.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #map {{ height: 100vh; width: 100%; }}
        .county-label {{ 
            background: rgba(255, 255, 255, 0.8); 
            border: 1px solid #ccc; 
            border-radius: 3px; 
            padding: 2px 4px; 
            font-size: 10px; 
            font-weight: bold; 
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <script>
        // Embedded NY county boundaries data
        const boundariesData = {json.dumps(boundaries_data)};
        
        // Initialize map centered on NY
        const map = L.map('map').setView([43.0, -76.0], 7);
        
        // Add base tile layer - REMOVED to show only county outlines
        // L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        //     attribution: '© OpenStreetMap contributors'
        // }}).addTo(map);
        
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
        L.geoJSON(boundariesData, {{
            style: {{
                fillColor: '#e8e8e8',
                weight: 0.5,
                opacity: 0.8,
                color: '#666',
                fillOpacity: 0.7
            }},
            interactive: false
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
        
        // Fit map to NY bounds
        const bounds = L.geoJSON(boundariesData).getBounds();
        map.fitBounds(bounds, {{padding: [20, 20]}});
        
        console.log('NY county boundaries loaded from embedded data');
    </script>
</body>
</html>'''
    
    output_file = Path('../outputs/ny_map_standalone.html')
    with open(output_file, 'w') as f:
        f.write(html_content)
        
    print(f"Standalone NY map generated: {output_file}")
    print("This HTML file is completely self-contained and can be uploaded anywhere.")

if __name__ == "__main__":
    create_standalone_ny_map()
