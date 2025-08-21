#!/usr/bin/env python3
"""Test script to verify the reorganized directory structure and files exist"""

import os
import sys

def test_structure():
    """Test that the reorganized file structure is correct"""
    
    print("Testing PyNMR reorganized structure...")
    
    base_path = "/home/jmaxwell/PycharmProjects/jlab_pynmr"
    
    files_to_check = [
        # Main files
        "pynmr_main.py",
        "pynmr_requirements.txt",
        
        # Package structure
        "pynmr/__init__.py",
        "pynmr/config/__init__.py",
        "pynmr/config/config.py",
        "pynmr/core/__init__.py", 
        "pynmr/core/data_models.py",
        "pynmr/core/analysis.py",
        "pynmr/core/calculations.py",
        "pynmr/core/deuteron_fits.py",
        "pynmr/hardware/__init__.py",
        "pynmr/hardware/daq.py",
        "pynmr/hardware/epics.py",
        "pynmr/hardware/instruments.py",
        "pynmr/hardware/magnet.py",
        "pynmr/hardware/rf_switch.py",
        "pynmr/gui/__init__.py",
        "pynmr/gui/main_window.py",
        "pynmr/gui/tabs/__init__.py",
        "pynmr/gui/tabs/run_tab.py",
        "pynmr/gui/tabs/base_tab.py",
        "pynmr/gui/tabs/tune_tab.py",
        "pynmr/gui/tabs/te_tab.py",
        "pynmr/gui/tabs/analysis_tab.py",
        "pynmr/utils/__init__.py",
    ]
    
    passed = 0
    failed = 0
    
    for file_path in files_to_check:
        full_path = os.path.join(base_path, file_path)
        if os.path.exists(full_path):
            print(f"✓ {file_path}")
            passed += 1
        else:
            print(f"✗ {file_path} - NOT FOUND")
            failed += 1
    
    print(f"\nResults: {passed} files found, {failed} missing")
    
    if failed == 0:
        print("🎉 All expected files are present! The reorganization structure is complete.")
        return True
    else:
        print("⚠️  Some files are missing from the reorganized structure.")
        return False

def check_migrations():
    """Check that PyQt5 imports have been migrated to PySide6"""
    
    print("\nChecking PyQt5 to PySide6 migration...")
    
    import glob
    import re
    
    python_files = glob.glob('/home/jmaxwell/PycharmProjects/jlab_pynmr/pynmr/**/*.py', recursive=True)
    
    pyqt5_files = []
    
    for filepath in python_files:
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                if re.search(r'PyQt5', content):
                    pyqt5_files.append(filepath)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    if pyqt5_files:
        print("✗ Files still containing PyQt5 references:")
        for filepath in pyqt5_files:
            print(f"   - {filepath}")
        return False
    else:
        print("✓ No PyQt5 references found - migration appears successful!")
        return True

if __name__ == '__main__':
    structure_ok = test_structure()
    migration_ok = check_migrations()
    
    if structure_ok and migration_ok:
        print("\n🎉 PyNMR reorganization and migration completed successfully!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r pynmr_requirements.txt")
        print("2. Run application: python pynmr_main.py")
    else:
        print("\n⚠️  Some issues were found. Please review the output above.")
    
    sys.exit(0 if (structure_ok and migration_ok) else 1)