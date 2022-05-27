#!/usr/bin/python3
'''PyNMR, J.Maxwell 2020
'''
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from app.gui import MainWindow
import sys
import getopt

def main():
    '''Main executable calls main gui
    '''
    config_file = 'pynmr_config.yaml'  
    try:
        opts, args = getopt.getopt(sys.argv[1:],"hc:")
    except getopt.GetoptError:
        print('Error: main.py [-c <config_file>]')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ['-h',]:
            print('Usage: main.py [-c <config_file>]')
            sys.exit()
        elif opt in ['-c',]:
            config_file = arg          
        
    app = QtWidgets.QApplication([])
    #app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True) #enable highdpi scaling
    app.setApplicationName("JLab Polarization Display")
    gui = MainWindow(config_file)
    gui.show()
    app.exec_()

if __name__ == '__main__':
    main()
