#!/usr/bin/env python3
"""
Choropleth Legend Generator
Generates configurable legends for choropleth map visualizations
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class LegendConfig:
    """Configuration for choropleth legend"""
    title: str
    max_value: int
    num_steps: int = 5
    color_scheme: str = "blue_red"  # "blue_red", "green_red", "grayscale"
    position: str = "bottomright"  # "topright", "topleft", "bottomright", "bottomleft"
    width: int = 200
    height: int = 150
    show_zero: bool = True


class ChoroplethLegendGenerator:
    """Generates legends for choropleth maps"""
    
    def __init__(self):
        self.color_schemes = {
            "blue_red": {
                "zero": "#e8e8e8",
                "start": "#0066cc", 
                "end": "#cc0000"
            },
            "green_red": {
                "zero": "#e8e8e8",
                "start": "#00cc66",
                "end": "#cc0000"
            },
            "grayscale": {
                "zero": "#f0f0f0",
                "start": "#cccccc",
                "end": "#333333"
            }
        }
    
    def generate_legend_data(self, config: LegendConfig) -> Dict:
        """Generate legend data structure"""
        scheme = self.color_schemes[config.color_scheme]
        
        # Calculate step values
        if config.show_zero:
            step_size = config.max_value / (config.num_steps - 1)
            values = [0] + [int(i * step_size) for i in range(1, config.num_steps)]
        else:
            step_size = config.max_value / config.num_steps
            values = [int((i + 1) * step_size) for i in range(config.num_steps)]
        
        # Generate colors for each step
        legend_items = []
        
        for i, value in enumerate(values):
            if value == 0 and config.show_zero:
                color = scheme["zero"]
                label = "0"
            else:
                # Interpolate between start and end colors
                if config.show_zero:
                    intensity = (i - 1) / (config.num_steps - 2) if config.num_steps > 2 else 1.0
                else:
                    intensity = i / (config.num_steps - 1) if config.num_steps > 1 else 1.0
                
                intensity = max(0, min(1, intensity))  # Clamp to [0,1]
                color = self._interpolate_color(scheme["start"], scheme["end"], intensity)
                
                if value == config.max_value:
                    label = f"{value}+"
                else:
                    label = str(value)
            
            legend_items.append({
                "value": value,
                "color": color,
                "label": label
            })
        
        return {
            "title": config.title,
            "items": legend_items,
            "position": config.position,
            "width": config.width,
            "height": config.height,
            "max_value": config.max_value
        }
    
    def _interpolate_color(self, start_color: str, end_color: str, intensity: float) -> str:
        """Interpolate between two hex colors"""
        # Parse hex colors
        start_rgb = self._hex_to_rgb(start_color)
        end_rgb = self._hex_to_rgb(end_color)
        
        # Interpolate each component
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * intensity)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * intensity)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * intensity)
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def generate_css(self, legend_data: Dict) -> str:
        """Generate CSS for legend styling"""
        return f'''
.choropleth-legend {{
    position: absolute;
    {legend_data["position"].replace("top", "top: 10px;").replace("bottom", "bottom: 10px;").replace("left", "left: 10px;").replace("right", "right: 10px;")}
    background: rgba(255, 255, 255, 0.9);
    border: 2px solid #333;
    border-radius: 5px;
    padding: 10px;
    font-family: Arial, sans-serif;
    font-size: 12px;
    width: {legend_data["width"]}px;
    z-index: 1000;
}}

.legend-title {{
    font-weight: bold;
    margin-bottom: 8px;
    text-align: center;
    font-size: 14px;
}}

.legend-item {{
    display: flex;
    align-items: center;
    margin-bottom: 3px;
}}

.legend-color {{
    width: 20px;
    height: 15px;
    border: 1px solid #666;
    margin-right: 8px;
    flex-shrink: 0;
}}

.legend-label {{
    font-size: 11px;
}}
'''
    
    def generate_html(self, legend_data: Dict) -> str:
        """Generate HTML for legend"""
        items_html = []
        for item in legend_data["items"]:
            items_html.append(f'''
        <div class="legend-item">
            <div class="legend-color" style="background-color: {item["color"]};"></div>
            <span class="legend-label">{item["label"]}</span>
        </div>''')
        
        return f'''
    <div class="choropleth-legend">
        <div class="legend-title">{legend_data["title"]}</div>
        {''.join(items_html)}
    </div>'''
    
    def generate_javascript_function(self, legend_data: Dict) -> str:
        """Generate JavaScript function to get color for value"""
        items = legend_data["items"]
        
        js_code = f'''
function getColorForValue(value, maxValue) {{
    if (value === 0) return "{items[0]["color"]}";
    
    const legendItems = {items};
    
    // Find appropriate color based on value
    for (let i = legendItems.length - 1; i >= 0; i--) {{
        if (value >= legendItems[i].value) {{
            return legendItems[i].color;
        }}
    }}
    
    return "{items[0]["color"]}"; // Default to zero color
}}

function updateLegendForMaxValue(newMaxValue) {{
    // Could regenerate legend items for new max value
    // For now, just update the max label
    const maxLabel = document.querySelector('.legend-item:last-child .legend-label');
    if (maxLabel) {{
        maxLabel.textContent = newMaxValue + '+';
    }}
}}
'''
        return js_code


def create_mobile_legend(max_qsos: int) -> Dict:
    """Create legend for mobile station QSO counts"""
    config = LegendConfig(
        title="Mobile QSOs",
        max_value=max_qsos,
        num_steps=5,
        color_scheme="blue_red",
        position="bottomright"
    )
    
    generator = ChoroplethLegendGenerator()
    return generator.generate_legend_data(config)


def create_all_stations_legend(max_qsos: int) -> Dict:
    """Create legend for all station QSO counts"""
    config = LegendConfig(
        title="Total QSOs",
        max_value=max_qsos,
        num_steps=6,
        color_scheme="green_red",
        position="bottomright"
    )
    
    generator = ChoroplethLegendGenerator()
    return generator.generate_legend_data(config)


def main():
    """Test the legend generator"""
    import json
    
    # Test mobile legend
    mobile_legend = create_mobile_legend(966)  # K2Q max from earlier
    print("Mobile Legend:")
    print(json.dumps(mobile_legend, indent=2))
    
    # Test all stations legend  
    all_legend = create_all_stations_legend(5779)  # ERI max from earlier
    print("\nAll Stations Legend:")
    print(json.dumps(all_legend, indent=2))
    
    # Generate HTML/CSS
    generator = ChoroplethLegendGenerator()
    
    print("\nCSS:")
    print(generator.generate_css(mobile_legend))
    
    print("\nHTML:")
    print(generator.generate_html(mobile_legend))
    
    print("\nJavaScript:")
    print(generator.generate_javascript_function(mobile_legend))


if __name__ == "__main__":
    main()
