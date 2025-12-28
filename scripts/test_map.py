#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.map_generator import NYMapGenerator

if __name__ == "__main__":
    # Test the generator
    boundaries_file = '../data/ny-counties-boundaries.json'
    output_file = '../outputs/test_static_map.html'
    
    generator = NYMapGenerator(boundaries_file)
    generator.generate_static_map_html(output_file, "Test NY Static Map")
