#!/usr/bin/env python3
"""
Meta script to process NYQP logs in order.
Calls individual processing scripts in sequence.
"""

import subprocess
import sys
from pathlib import Path

def run_script(script_name, args=None):
    """Run a script and handle errors."""
    cmd = [sys.executable, script_name]
    if args:
        cmd.extend(args)
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"ERROR in {script_name}:")
        print(result.stderr)
        sys.exit(1)
    
    print(result.stdout)

def main():
    if len(sys.argv) != 2:
        print("Usage: python process_nyqp.py <logs_directory>")
        sys.exit(1)
    
    logs_dir = sys.argv[1]
    
    print("=== NYQP Processing Pipeline ===")
    
    # Step 1: Create databases
    print("\n1. Creating databases...")
    run_script("create_sql_db.py", [logs_dir])
    
    # Step 2: Generate county line periods
    print("\n2. Generating county line periods...")
    run_script("county_line_periods.py", ["--db", "../data/contest_qsos.db", "--mobiles", "../data/ny_mobiles.db"])
    
    # Step 3: Generate county QSO counts
    print("\n3. Generating county QSO counts...")
    run_script("county_qso_counts.py")
    
    # Step 4: Generate mobile animation
    print("\n4. Generating mobile animation...")
    run_script("mobile_animation_generator.py")
    
    print("\n=== Processing Complete ===")

if __name__ == '__main__':
    main()
