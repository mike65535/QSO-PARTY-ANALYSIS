#!/usr/bin/env python3
"""
Standalone NY State Map Generator
Creates HTML maps with county boundaries - no dependencies on other modules
"""

import json

class NYStateMapGenerator:
    def __init__(self):
        """Initialize with embedded NY county boundaries data"""
        # This would normally load from a file, but for standalone use we embed minimal data
        self.county_names = {
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
        
    def generate_map_html(self, output_file, title="NY State Map", boundaries_file=None):
        """Generate standalone NY map HTML"""
        
        # Use provided boundaries file or default
        if boundaries_file is None:
            boundaries_file = '../data/ny-counties-boundaries.json'
            
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
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
        // Initialize map centered on NY
        const map = L.map('map').setView([43.0, -76.0], 7);
        
        // Add base tile layer
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        
        // Load and display NY county boundaries
        fetch('{boundaries_file}')
            .then(response => response.json())
            .then(data => {{
                L.geoJSON(data, {{
                    style: {{
                        color: '#2c3e50',
                        weight: 2,
                        opacity: 1,
                        fillColor: '#ecf0f1',
                        fillOpacity: 0.3
                    }},
                    onEachFeature: function(feature, layer) {{
                        const countyName = feature.properties.NAME;
                        
                        // Add popup with county info
                        layer.bindPopup(`<b>${{countyName}}</b>`);
                        
                        // Add hover effects
                        layer.on('mouseover', function() {{
                            this.setStyle({{
                                fillColor: '#3498db',
                                fillOpacity: 0.6
                            }});
                        }});
                        
                        layer.on('mouseout', function() {{
                            this.setStyle({{
                                fillColor: '#ecf0f1',
                                fillOpacity: 0.3
                            }});
                        }});
                    }}
                }}).addTo(map);
                
                console.log('NY county boundaries loaded successfully');
            }})
            .catch(error => {{
                console.error('Error loading county boundaries:', error);
                alert('Could not load county boundaries. Check that {boundaries_file} exists.');
            }});
    </script>
</body>
</html>'''
        
        with open(output_file, 'w') as f:
            f.write(html_content)
            
        print(f"NY State map generated: {output_file}")

def main():
    """Generate a test NY state map"""
    generator = NYStateMapGenerator()
    generator.generate_map_html('../outputs/ny_state_map.html', "NY State Counties Map")

if __name__ == "__main__":
    main()
