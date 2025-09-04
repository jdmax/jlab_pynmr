#!/usr/bin/env python3
"""Basic functionality test for reorganized PyNMR"""

import sys
import os
sys.path.insert(0, '/home/jmaxwell/PycharmProjects/jlab_pynmr')

def test_core_functionality():
    """Test core functionality without GUI"""
    print("Testing core functionality...")
    
    try:
        # Test configuration
        from pynmr.config import Config, ConfigItem
        from PySide6.QtGui import QIntValidator
        
        # Create a minimal config
        channel = {
            'species': 'proton',
            'cent_freq': 213.0,
            'mod_freq': 50.0,
            'sweep_file': 'standard_sweep.txt'  # This file may not exist, but that's OK for testing
        }
        settings = {'steps': 100}
        
        config = Config(channel, settings)
        print("✓ Configuration creation works")
        
        # Test data models
        from pynmr.core import Scan, EventData, Baseline, History, HistPoint
        
        scan = Scan(config)
        print("✓ Scan creation works")
        
        # Test calculations if they don't require GUI
        try:
            from pynmr.core import TE
            te = TE()
            print("✓ TE calculation import works")
        except Exception as e:
            print(f"⚠ TE calculation import failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Core functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_hardware_imports():
    """Test hardware module imports"""
    print("\nTesting hardware imports...")
    
    try:
        from pynmr.hardware import DAQConnection, EPICS
        print("✓ Hardware imports work")
        return True
    except Exception as e:
        print(f"⚠ Hardware imports failed (may need optional dependencies): {e}")
        return False

def test_gui_creation():
    """Test GUI creation"""
    print("\nTesting GUI creation...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from pynmr.gui import MainWindow
        
        # Create minimal app (don't show window)
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Try to create main window with a mock config
        config_file = 'pynmr_config.yaml'  # May not exist, but we can catch that
        
        try:
            window = MainWindow(config_file)
            print("✓ MainWindow creation works")
            return True
        except FileNotFoundError:
            print("⚠ Config file not found - create a minimal config for testing")
            return False
        except Exception as e:
            print(f"✗ MainWindow creation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"✗ GUI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_minimal_config():
    """Create a minimal config file for testing"""
    import yaml
    
    config_file = '/home/jmaxwell/PycharmProjects/jlab_pynmr/test_config.yaml'
    
    minimal_config = {
        'settings': {
            'default_channel': 'proton',
            'steps': 100,
            'daq_type': 'UDP',
            'event_dir': './data',
            'history_file': 'history',
            'session_file': 'session',
            'log_dir': './log',
            'ss_dir': '',
            'num_per_chunk': 10,
            'shim_settings': {'enable': False},
            'fm_settings': {'enable': False},
            'compare_tab': {'enable': False},
            'temp_settings': {'enable': False},
            'explorer': {'enable': False}
        },
        'channels': {
            'proton': {
                'species': 'proton',
                'cent_freq': 213.0,
                'mod_freq': 50.0,
                'sweep_file': 'standard_sweep.txt'
            }
        },
        'epics_reads': {},
        'epics_writes': {}
    }
    
    # Create directories
    os.makedirs('./data', exist_ok=True)
    os.makedirs('./log', exist_ok=True)
    os.makedirs('./app', exist_ok=True)
    
    # Create minimal session file
    session_file = './app/session.yaml'
    session_data = {
        'phase_tune': 0,
        'diode_tune': 0,
        'cc': -0.08,
        'channel': 0
    }
    
    with open(session_file, 'w') as f:
        yaml.dump(session_data, f)
    
    with open(config_file, 'w') as f:
        yaml.dump(minimal_config, f)
    
    print(f"✓ Created minimal config: {config_file}")
    return config_file

if __name__ == '__main__':
    print("PyNMR Basic Functionality Test")
    print("=" * 40)
    
    # Test core functionality first
    core_ok = test_core_functionality()
    
    # Test hardware imports
    hardware_ok = test_hardware_imports()
    
    # Create minimal config for GUI testing
    try:
        config_file = create_minimal_config()
        
        # Test GUI with minimal config
        gui_ok = test_gui_creation()
    except Exception as e:
        print(f"Failed to create test config: {e}")
        gui_ok = False
    
    print("\n" + "=" * 40)
    print("RESULTS:")
    print(f"Core functionality: {'✓ PASS' if core_ok else '✗ FAIL'}")
    print(f"Hardware imports: {'✓ PASS' if hardware_ok else '⚠ PARTIAL'}")
    print(f"GUI creation: {'✓ PASS' if gui_ok else '✗ FAIL'}")
    
    if core_ok:
        print("\n🎉 Core functionality works! Ready for basic testing.")
        if not gui_ok:
            print("⚠ GUI issues found - check dependencies and config files")
    else:
        print("\n❌ Core functionality issues - fix these first")
    
    print("\nNext steps:")
    print("1. Install missing dependencies if needed")
    print("2. Test with real config file: python pynmr_main.py -c your_config.yaml")
    print("3. Once working, proceed with modularity improvements")