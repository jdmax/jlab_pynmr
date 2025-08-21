#!/usr/bin/env python3
"""Script to migrate PyQt5 imports to PySide6 across all Python files"""

import os
import re
import glob

def migrate_file(filepath):
    """Migrate a single file from PyQt5 to PySide6"""
    print(f"Processing {filepath}")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Store original content to compare
    original_content = content
    
    # Replace PyQt5 imports with PySide6
    replacements = [
        (r'from PyQt5\.QtWidgets import', r'from PySide6.QtWidgets import'),
        (r'from PyQt5\.QtCore import', r'from PySide6.QtCore import'),
        (r'from PyQt5\.QtGui import', r'from PySide6.QtGui import'),
        (r'from PyQt5 import QtWidgets', r'from PySide6 import QtWidgets'),
        (r'from PyQt5 import QtCore', r'from PySide6 import QtCore'),
        (r'from PyQt5 import QtGui', r'from PySide6 import QtGui'),
        (r'import PyQt5\.QtWidgets', r'import PySide6.QtWidgets'),
        (r'import PyQt5\.QtCore', r'import PySide6.QtCore'),
        (r'import PyQt5\.QtGui', r'import PySide6.QtGui'),
        # Replace signal names
        (r'pyqtSignal', r'Signal'),
        # Replace QRegExpValidator with QRegularExpressionValidator
        (r'QRegExpValidator', r'QRegularExpressionValidator'),
    ]
    
    # Apply replacements
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # Update old app imports to new pynmr imports
    import_replacements = [
        (r'from app\.classes import', r'from pynmr.core import'),
        (r'from app\.epics import', r'from pynmr.hardware import'),
        (r'from app\.daq import', r'from pynmr.hardware import'),
        (r'from app\.te_calc import', r'from pynmr.core.calculations import'),
        (r'from app\.deuteron_fits import', r'from pynmr.core.deuteron_fits import'),
        (r'from app\.microwaves import', r'from pynmr.hardware.instruments import'),
        (r'from app\.gui import', r'from pynmr.gui import'),
    ]
    
    for pattern, replacement in import_replacements:
        content = re.sub(pattern, replacement, content)
    
    # Write back only if changed
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  Updated {filepath}")
    else:
        print(f"  No changes needed for {filepath}")

def main():
    """Main migration function"""
    # Find all Python files in the pynmr directory
    python_files = glob.glob('/home/jmaxwell/PycharmProjects/jlab_pynmr/pynmr/**/*.py', recursive=True)
    
    print(f"Found {len(python_files)} Python files to process")
    
    for filepath in python_files:
        try:
            migrate_file(filepath)
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
    
    print("Migration completed!")

if __name__ == '__main__':
    main()