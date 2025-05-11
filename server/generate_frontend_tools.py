#!/usr/bin/env python
"""
Script to generate frontend_tools.py from frontend_tools.ts

This script runs the Node.js generator script to create the Python file.
It should be run before starting the server.
"""

import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Run the generator script and check if it succeeded."""
    # Get the project root directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..'))
    common_dir = os.path.join(project_root, 'common')
    
    # Check if the TypeScript file exists
    ts_file = os.path.join(common_dir, 'frontend_tools.ts')
    if not os.path.exists(ts_file):
        logger.error(f"TypeScript file not found: {ts_file}")
        return False
    
    # Check if Node.js is installed
    try:
        subprocess.run(['node', '--version'], check=True, capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("Node.js is not installed or not in PATH. Please install Node.js to generate the Python file.")
        return False
    
    # Run the generator script
    generator_script = os.path.join(common_dir, 'generate_python.js')
    logger.info(f"Running generator script: {generator_script}")
    
    try:
        result = subprocess.run(
            ['node', generator_script], 
            check=True, 
            cwd=common_dir,
            capture_output=True,
            text=True
        )
        logger.info(f"Generator output: {result.stdout}")
        
        # Check if the Python file was created
        py_file = os.path.join(common_dir, 'frontend_tools.py')
        if os.path.exists(py_file):
            logger.info(f"Successfully generated Python file: {py_file}")
            return True
        else:
            logger.error(f"Failed to generate Python file: {py_file}")
            return False
    except subprocess.SubprocessError as e:
        logger.error(f"Error running generator script: {e}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
