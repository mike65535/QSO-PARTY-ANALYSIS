#!/usr/bin/env python3
"""
US Map Generator - creates standalone US map with state boundaries
Similar to NY state map but for entire US
"""

import json
import requests
from pathlib import Path

def download_us_boundaries():
    """Download US state boundaries from Census Bureau"""
    # US States (lower 48 + AK + HI) at 5m resolution for reasonable file size
    url = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json"
    
    print("Downloading US state boundaries...")
    response = requests.get(url)
    response.raise_for_status()
    
    # This is TopoJSON format, need to convert to GeoJSON
    topojson_data = response.json()
    
    # For now, let's try a different source that's already GeoJSON
    geojson_url = "https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson"
    
    # Actually, let's use a reliable US states GeoJSON source
    us_states_url = "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"
    
    print("Downloading US states GeoJSON...")
    response = requests.get(us_states_url)
    response.raise_for_status()
    
    return response.json()

def create_us_map():
    """Create standalone US map HTML file"""
    
    try:
        # Try to load existing boundaries file first
        boundaries_path = Path('../data/us-states-boundaries.json')
        if boundaries_path.exists():
            print("Loading existing US boundaries data...")
            with open(boundaries_path, 'r') as f:
                boundaries_data = json.load(f)
        else:
            # Download and save boundaries data
            boundaries_data = download_us_boundaries()
            
            # Save for future use
            boundaries_path.parent.mkdir(exist_ok=True)
            with open(boundaries_path, 'w') as f:
                json.dump(boundaries_data, f)
            print(f"Saved US boundaries to {boundaries_path}")
            
    except Exception as e:
        print(f"Error loading boundaries: {e}")
        print("Creating map with placeholder data...")
        boundaries_data = {"type": "FeatureCollection", "features": []}
    
    html_content = f'''<!DOCTYPE html>
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
        }}
            
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
            if (lower48Features.length > 0) {{
                const bounds = L.geoJSON({{type: "FeatureCollection", features: lower48Features}}).getBounds();
                map.fitBounds(bounds, {{padding: [20, 20]}});
            }}
        }} else {{
            console.log('No boundary data available');
        }}
        
        console.log('US state boundaries loaded');
    </script>
</body>
</html>'''
    
    output_file = Path('../outputs/us_map_standalone.html')
    with open(output_file, 'w') as f:
        f.write(html_content)
        
    print(f"US map generated: {output_file}")
    print("This HTML file includes embedded US state boundary data.")

if __name__ == "__main__":
    create_us_map()
