# PyNMR Reorganization & Migration Guide

## Overview

This document describes the reorganization and migration of the PyNMR application from PyQt5 to PySide6, along with improved code organization for better maintainability.

## Key Changes

### 1. Framework Migration: PyQt5 → PySide6

- **Replaced PyQt5 with PySide6** for improved licensing and future compatibility
- **Updated all signal declarations**: `pyqtSignal` → `Signal`
- **Migrated validator classes**: `QRegExpValidator` → `QRegularExpressionValidator`
- **Updated import statements** throughout the codebase

### 2. Improved Code Organization

#### New Directory Structure

```
pynmr/
├── main.py → pynmr_main.py           # Main entry point
├── requirements.txt → pynmr_requirements.txt
├── config/
│   ├── __init__.py
│   └── config.py                     # Configuration classes (Config, ConfigItem)
├── core/
│   ├── __init__.py
│   ├── data_models.py               # Core data classes (Scan, Event, Baseline, etc.)
│   ├── analysis.py                  # Analysis thread
│   ├── calculations.py              # TE calculations
│   └── deuteron_fits.py             # Deuteron fitting functions
├── hardware/
│   ├── __init__.py
│   ├── daq.py                       # DAQ connections
│   ├── epics.py                     # EPICS interface
│   ├── instruments.py               # Microwave equipment
│   ├── magnet.py                    # Magnet control
│   └── rf_switch.py                 # RF switch control
├── gui/
│   ├── __init__.py
│   ├── main_window.py               # Main application window
│   └── tabs/
│       ├── __init__.py
│       ├── run_tab.py               # Run control tab
│       ├── base_tab.py              # Baseline tab
│       ├── analysis_tab.py          # Analysis tab
│       ├── tune_tab.py              # Tuning tab
│       ├── te_tab.py                # TE calculation tab
│       └── ...other tabs
└── utils/
    ├── __init__.py
    └── combiner/                    # Data combination utilities
        ├── combiner.py
        └── exporter.py
```

#### Benefits of New Structure

1. **Clear Separation of Concerns**
   - Configuration management isolated in `config/`
   - Core data models and business logic in `core/`
   - Hardware interfaces organized in `hardware/`
   - GUI components structured in `gui/`

2. **Improved Maintainability**
   - Smaller, focused modules instead of monolithic files
   - Reduced circular dependencies
   - Clear import hierarchy

3. **Better Testing**
   - Core logic separated from GUI for easier unit testing
   - Hardware interfaces can be mocked more easily

4. **Enhanced Extensibility**
   - New hardware interfaces can be added easily
   - GUI tabs can be developed independently
   - Core functionality is reusable

## Migration Details

### Import Statement Changes

**Old imports:**
```python
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QWidget
from app.classes import Config, Event
```

**New imports:**
```python
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QMainWindow, QWidget
from pynmr.config import Config
from pynmr.core import Event
```

### Signal Declaration Changes

**Old:**
```python
reply = pyqtSignal(tuple)
```

**New:**
```python
reply = Signal(tuple)
```

### Entry Point Changes

**Old:** `main.py`
**New:** `pynmr_main.py`

## Installation & Usage

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Application

```bash
python pynmr_main.py
```

Or with custom config:
```bash
python pynmr_main.py -c custom_config.yaml
```

### 3. Development

For development, you can import modules directly:

```python
from pynmr.core import Event, Scan
from pynmr.config import Config
from pynmr.hardware import EPICS, DAQConnection
```

## Testing

Run the structure verification:
```bash
python test_structure.py
```

Test imports (requires dependencies):
```bash
python test_imports.py
```

## Backward Compatibility

The original `app/` directory structure is preserved for reference, but the new `pynmr/` package structure should be used going forward.

Configuration files and data formats remain unchanged, ensuring seamless transition for existing users.

## Key Benefits

1. **Better Licensing**: PySide6 has more permissive licensing than PyQt5
2. **Future-Proof**: PySide6 is actively maintained by Qt Company
3. **Improved Organization**: Clear module boundaries and responsibilities
4. **Enhanced Maintainability**: Smaller, focused files are easier to maintain
5. **Better Testing**: Core logic can be tested independently of GUI
6. **Professional Structure**: Follows Python packaging best practices

## Next Steps

1. **Gradual Migration**: Teams can migrate tab-by-tab if needed
2. **Testing**: Comprehensive testing with real hardware
3. **Documentation**: Update user documentation for new structure
4. **CI/CD**: Set up automated testing for the new structure