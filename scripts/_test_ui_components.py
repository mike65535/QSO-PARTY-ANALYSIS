#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.animation_ui import TimelineControls, ProgressBar, StatusBar, Legend, generate_test_html

if __name__ == "__main__":
    # Generate test HTML for each component
    components = [
        ("TimelineControls", TimelineControls),
        ("ProgressBar", ProgressBar), 
        ("StatusBar", StatusBar),
        ("Legend", Legend)
    ]
    
    for name, component_class in components:
        html = generate_test_html(name, component_class)
        filename = f"../outputs/test_{name.lower()}.html"
        
        with open(filename, 'w') as f:
            f.write(html)
        
        print(f"Generated test file: {filename}")
    
    print("\nOpen the test files in a browser to see each component standalone.")
