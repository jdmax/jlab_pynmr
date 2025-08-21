#!/usr/bin/env python3
"""PyNMR, J.Maxwell 2020

Main entry point for the PyNMR application.
"""

import sys
import getopt
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from pynmr.gui import MainWindow


def main():
    """Main executable calls main gui"""
    config_file = 'pynmr_config.yaml'  
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hc:")
    except getopt.GetoptError:
        print('Error: pynmr_main.py [-c <config_file>]')
        sys.exit(2)
        
    for opt, arg in opts:
        if opt in ['-h']:
            print('Usage: pynmr_main.py [-c <config_file>]')
            sys.exit()
        elif opt in ['-c']:
            config_file = arg          
        
    app = QApplication(sys.argv)
    # app.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # enable highdpi scaling
    app.setApplicationName("JLab Polarization Display")
    
    gui = MainWindow(config_file)
    gui.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()