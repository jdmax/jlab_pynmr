#!/usr/bin/env python3
"""Test script to verify reorganized PyNMR imports work correctly"""

import sys
import traceback

def test_imports():
    """Test that all major modules can be imported"""
    
    print("Testing PyNMR reorganized imports...")
    
    tests = [
        ("pynmr", "Main package"),
        ("pynmr.config", "Configuration module"),
        ("pynmr.config.config", "Config classes"),
        ("pynmr.core", "Core data models"),
        ("pynmr.core.data_models", "Data model classes"),
        ("pynmr.core.analysis", "Analysis thread"),
        ("pynmr.hardware", "Hardware interfaces"),
        ("pynmr.hardware.daq", "DAQ connections"),
        ("pynmr.hardware.epics", "EPICS interface"),
        ("pynmr.gui", "GUI module"),
        ("pynmr.gui.main_window", "Main window"),
    ]
    
    passed = 0
    failed = 0
    
    for module_name, description in tests:
        try:
            __import__(module_name)
            print(f"✓ {description} ({module_name})")
            passed += 1
        except ImportError as e:
            print(f"✗ {description} ({module_name}): {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {description} ({module_name}): Unexpected error - {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All imports successful! The reorganization appears to be working.")
        return True
    else:
        print("⚠️  Some imports failed. Check the errors above.")
        return False

if __name__ == '__main__':
    success = test_imports()
    sys.exit(0 if success else 1)