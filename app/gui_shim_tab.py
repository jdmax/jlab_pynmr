'''PyNMR, J.Maxwell 2021
'''
import datetime
import re
import json
import time
import numpy as np
from scipy.optimize import minimize
from dateutil.parser import parse
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, QSizePolicy, QComboBox, QPushButton, QTableView, QAbstractItemView, QAbstractScrollArea, QFileDialog, QStackedWidget
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator
import pyqtgraph as pg
from PyQt5.QtCore import QThread, pyqtSignal,Qt
from RsInstrument import * 
import telnetlib
 

class ShimTab(QWidget): 
    '''Creates shim control tab'''   
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.__dict__.update(parent.__dict__)  
        
        self.parent = parent
        self.shim_pen = pg.mkPen(color=(0, 0, 204), width=1.5)
        self.goal_pen = pg.mkPen(color=(0, 200, 0), width=1.5)
        self.back_pen = pg.mkPen(color=(200, 0, 0), width=1.5)
        
        self.shims = ShimControl(self.parent.config)
        self.read_back = self.shims.read_currents()
        self.shim_state = self.shims.read_outstat()
        
        self.z_axis = np.arange(-30,31)        
        self.frost = np.array([4.9995, 4.999595, 4.99969, 4.9997575, 4.999825, 4.9998675,
                      4.99991, 4.9999425, 4.999975, 4.9999975, 5.00002, 5.000035,
                      5.00005, 5.000055, 5.00006, 5.00006, 5.00006, 5.0000575,
                      5.000055, 5.0000525, 5.00005, 5.000045, 5.000035, 5.00003,
                      5.00002, 5.000015, 5.00001, 5.0000075, 5.000005, 5.0000025,
                      5, 5.0000025, 5.000005, 5.0000075, 5.00001, 5.000015, 5.00002,
                      5.0000225, 5.000025, 5.0000325, 5.00004, 5.0000475, 5.000055,
                      5.00006, 5.000065, 5.00007, 5.000075, 5.000075, 5.000075,
                      5.0000675, 5.00006, 5.00005, 5.00004, 5.00002, 5, 4.99997,
                      4.99994, 4.999895, 4.99985, 4.99978, 4.99971])

        self.clas = np.array([4.9990486, 4.9991143, 4.9991774, 4.9992379, 4.9992959,
                         4.9993512, 4.9994041, 4.9994545, 4.9995025, 4.9995481,
                         4.9995913, 4.9996322, 4.9996708, 4.9997072, 4.9997413,
                         4.9997732, 4.9998029, 4.9998304, 4.9998558, 4.9998791,
                         4.9999003, 4.9999194, 4.9999364, 4.9999514, 4.9999644,
                         4.9999753, 4.9999842, 4.9999911, 4.9999961, 4.999999,
                         5, 4.999999, 4.999996, 4.9999911, 4.9999842, 4.9999753,
                         4.9999645, 4.9999517, 4.9999369, 4.9999201, 4.9999013,
                         4.9998805, 4.9998577, 4.9998329, 4.999806, 4.9997771,
                         4.9997461, 4.9997131, 4.9996779, 4.9996406, 4.9996011,
                         4.9995595, 4.9995156, 4.9994696, 4.9994212, 4.9993707,
                         4.9993177, 4.9992625, 4.9992049, 4.9991448, 4.9990824])
 

        #Frostcurrent=1 # percent of 5T
        #background = frost*Frostcurrent
        #background = clas


        #goal = tilt(5,10) # (midpint in T, far edge in G)
        #goal = clas
        #goal = np.zeros(61)+10 # set to 10 for max



        # Populate  Tab 
        self.main = QHBoxLayout()            # main layout
        self.setLayout(self.main) 
        
        # Left Side
        self.left = QVBoxLayout() 
        self.main.addLayout(self.left)
        
        # Shim options box
        self.shim_op_box = QGroupBox('Shim Options')
        self.shim_op_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.shim_op_box)        
        self.shim_op_combo = QComboBox()
        self.shim_op_box.layout().addWidget(self.shim_op_combo)
        self.shim_op_stack = QStackedWidget()    
        self.shim_op_box.layout().addWidget(self.shim_op_stack)
        self.shim_op_combo.currentIndexChanged.connect(self.change_op)


        # Shim controls box
        self.shim_con_box = QGroupBox('Shim Controls')
        self.shim_con_box.setLayout(QGridLayout())
        self.left.addWidget(self.shim_con_box)   


        self.shim_currents = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        self.cur_label = {}
        self.cur_edit = {}
        self.read_label = {}
        self.read_edit = {}
        for i, k in enumerate(self.shim_currents.keys()):
            self.cur_label[k] = QLabel(k+"(Amps)")
            self.shim_con_box.layout().addWidget(self.cur_label[k], i, 0)
            self.cur_edit[k] = QLineEdit(str(self.shim_currents[k]))
            self.shim_con_box.layout().addWidget(self.cur_edit[k], i, 1)
            self.cur_edit[k].setValidator(QDoubleValidator(-10, 10, 4))
            self.read_label[k] = QLabel("Readback (Amps)")
            self.shim_con_box.layout().addWidget(self.read_label[k], i, 3)
            self.read_edit[k] = QLineEdit(str(self.read_back[i]))
            self.read_edit[k].setEnabled(False)
            self.shim_con_box.layout().addWidget(self.read_edit[k], i, 4)
            
        self.set_button = QPushButton('Set Shim Currents') 
        currents = [float(self.cur_edit[k].text()) for k in self.shim_currents.keys()]
        self.set_button.clicked.connect(self.set_clicked)
        self.shim_con_box.layout().addWidget(self.set_button, 0, 2)
        
        self.turn_button = QPushButton('Turn ON', checkable=True) 
        self.turn_button.clicked.connect(self.turn_clicked)
        self.shim_con_box.layout().addWidget(self.turn_button, len(self.shim_currents)-1, 2)
        if '1' in str(self.shim_state):   # change to match inital state of supply
            self.turn_button.toggle()
            self.turn_button.setText('Turn OFF')
 
        self.right = QVBoxLayout()     # right part of main layout
        self.main.addLayout(self.right)
        
        
        self.shim_wid = pg.PlotWidget(title='Shim Output')
        self.shim_wid.showGrid(True,True)
        self.shim_wid.addLegend(offset=(0.5, 0))
        self.right.addWidget(self.shim_wid)
        self.shim_plot = self.shim_wid.plot([], [], pen=self.shim_pen, name='Shimmed Field (T)') 
        self.goal_plot = self.shim_wid.plot([], [], pen=self.goal_pen, name='Goal Field (T)') 
        self.back_plot = self.shim_wid.plot([], [], pen=self.back_pen, name='Background Field (T)') 

        # Set up list of options for each step, putting instances into stack
        self.shim_opts = []
        self.shim_opts.append(Flatten(self))  
        self.shim_opts.append(AllSame(self))  
        self.shim_opts.append(Tilt(self)) 
        self.shim_opts.append(LikeCLAS(self))       
        for o in self.shim_opts:
            self.shim_op_combo.addItem(o.name)
            self.shim_op_stack.addWidget(o)
    
    def change_op(self, i):
        '''Set chosen stack
        '''
        self.shim_op_stack.setCurrentIndex(i)
        
    def set_clicked(self):
        '''
        '''  
        list = [float(self.cur_edit[k].text()) for k in self.shim_currents.keys()]
        self.shims.set_currents(list)
        self.read_back = self.shims.read_currents()
        self.fill_readback()
        return
        
    def turn_clicked(self):
        '''Button clicked, send new state to shim controller, check to be sure button is right
        '''  
        state_to_set = '1' if self.turn_button.isChecked() else '0'     
        out = self.shims.set_outstat(state_to_set) 
        
        if not state_to_set in out:
            self.turn_button.toggle()
            print("Shim state didn't match", state_to_set, out)
        
        if self.turn_button.isChecked():
            self.turn_button.setText('Turn OFF')
        else:
            self.turn_button.setText('Turn ON')
                
    def fill_readback(self):
        '''
        '''          
        for i, k in enumerate(self.shim_currents.keys()):            
            self.read_edit[k].setText(self.read_back[i]) 

        
    def update_plots(self):
        '''Update shim plots
        '''
        self.shim_plot.setData(self.z_axis, self.shimmed)
        self.goal_plot.setData(self.z_axis,self.goals)
        self.back_plot.setData(self.z_axis,self.background)
        
    def enter_currents(self):
        '''Update shim controls
        '''
        for i, k in enumerate(self.shim_currents.keys()):
            self.cur_edit[k].setText(f"{self.x[i]:.4f}")
        

    def calc_currents(self, background, goals):
        self.result = minimize(self.chi, np.array([1,1,1,1]), args=(background,goals), method='Nelder-Mead', bounds=((-10,10),(-10,10),(-10,10),(-10,10)))
           
        just_shims = self.coil_from_shims(self.result.x)
        shimmed = just_shims + background        
        return just_shims, shimmed, self.result.x
        
        

    def tilt(self, MIDinT,PEAKinG):
        steps = PEAKinG/(30*10000) # G to T and divide by steps
        tiltField = (np.arange(-30,31)*steps)+MIDinT
        return tiltField

    def coil_from_shims(self, currents):
        z1 = np.array([-2.4424,-1.0393,0.0644,2.1887]) #left
        z2 = np.array([-2.1887,-0.0644,1.0393,2.4424]) #right    
        z1=z1/39.37 # inch to meter
        z2=z2/39.37 # inch to meter
        w=z2-z1
        Z = np.arange(-30,31)
        Z = Z/1000 # mm to meter
        R = np.array([0.0335, 0.0338]) # inner and out layer radii
        windings=([np.array([35,134,134,35])/w,np.array([34,134,134,34])/w])
        n=windings
        #n=21500/2 # turns per length(one layer)
        mu=12.57e-7 # permeability of free space
        field=np.zeros(len(Z))
        for j in [0,1]: # field at Z from coil (of size z1 -> z2)
            for i in range(len(Z)):
                a = mu*n[j]*currents/2
                b = ( Z[i]-z1 )/( np.sqrt((Z[i]-z1)**2 + R[j]**2) )
                c = ( Z[i]-z2 )/( np.sqrt((Z[i]-z2)**2 + R[j]**2) )
                bz = a*(b-c)
                field[i]=field[i]+np.sum(np.sum(bz))
        return field

    def chi(self, currents, background, goal):
        shimField = self.coil_from_shims(currents) + background
        diff = shimField-goal
        chi = (diff**2)/goal
        chiSUM = np.sum(chi)
        return chiSUM
    
    def divider(self):
        div = QLabel ('')
        div.setStyleSheet ("QLabel {background-color: #eeeeee; padding: 0; margin: 0; border-bottom: 0 solid #eeeeee; border-top: 1 solid #eeeeee;}")
        div.setMaximumHeight (2)
        return div 
                
        
class Flatten(QWidget):
    '''Layout and method for flattening background field to flat
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Flatten Background"
                
        self.grid = QGridLayout()
        self.space.addLayout(self.grid)
        self.current_label = QLabel("FROST Magnet Current (A):")
        self.grid.addWidget(self.current_label, 0, 0)
        self.current_edit = QLineEdit('0')
        self.current_edit.setValidator(QDoubleValidator(0, 90, 4))
        self.grid.addWidget(self.current_edit, 0, 1)
        self.goal_label = QLabel("Goal Field (T):")
        self.grid.addWidget(self.goal_label, 1, 0)
        self.goal_edit = QLineEdit('0')
        self.goal_edit.setValidator(QDoubleValidator(0, 6, 4))
        self.grid.addWidget(self.goal_edit, 1, 1)
        self.calc_button = QPushButton('Calculate Currents')
        self.grid.addWidget(self.calc_button, 1, 2) 
        self.calc_button.clicked.connect(self.calc_clicked)
        
    def calc_clicked(self):
        '''
        '''  
        self.parent.background = self.parent.frost/5*float(self.current_edit.text())*0.061594  # calibration for current at 5T 
        self.parent.goals = [float(self.goal_edit.text())]*61
        self.parent.just_shims, self.parent.shimmed, self.parent.x = self.parent.calc_currents(self.parent.background, self.parent.goals)
        self.parent.update_plots()
        self.parent.enter_currents()
        return
        
         
class AllSame(QWidget):
    '''Layout and method for flattening background field to flat
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Set All Same"
                
        self.grid = QGridLayout()
        self.space.addLayout(self.grid)
        self.current_label = QLabel("FROST Magnet Current (A):")
        self.grid.addWidget(self.current_label, 0, 0)
        self.current_edit = QLineEdit('0')
        self.current_edit.setValidator(QDoubleValidator(0, 90, 4))
        self.grid.addWidget(self.current_edit, 0, 1)
        self.goal_label = QLabel("Set current (A):")
        self.grid.addWidget(self.goal_label, 1, 0)
        self.goal_edit = QLineEdit('0')
        self.goal_edit.setValidator(QDoubleValidator(0, 6, 4))
        self.grid.addWidget(self.goal_edit, 1, 1)
        self.calc_button = QPushButton('Fill Currents')
        self.grid.addWidget(self.calc_button, 1, 2) 
        self.calc_button.clicked.connect(self.calc_clicked)
        
    def calc_clicked(self):
        '''
        '''  
        self.background = self.parent.frost/5*float(self.current_edit.text())*0.061594  # calibration for current at 5T 
        self.parent.goals = [float('nan')]*61
        self.parent.just_shims = [float('nan')]*61
        self.parent.x = [float(self.goal_edit.text())]*4
        self.parent.shimmed = self.background + self.parent.coil_from_shims(self.parent.x)
        self.parent.update_plots()
        self.parent.enter_currents()
        return
        
class Tilt(QWidget):
    '''Layout and method
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Tilted Field"
                
        self.grid = QGridLayout()
        self.space.addLayout(self.grid)
        self.current_label = QLabel("FROST Magnet Current (A):")
        self.grid.addWidget(self.current_label, 0, 0)
        self.current_edit = QLineEdit('0')
        self.current_edit.setValidator(QDoubleValidator(0, 90, 4))
        self.grid.addWidget(self.current_edit, 0, 1)
        self.goal_label = QLabel("Tilt Height (G):")
        self.grid.addWidget(self.goal_label, 1, 0)
        self.goal_edit = QLineEdit('0')
        self.goal_edit.setValidator(QDoubleValidator(0, 6, 4))
        self.grid.addWidget(self.goal_edit, 1, 1)
        self.off_label = QLabel("Center Field (T):")
        self.grid.addWidget(self.off_label, 2, 0)
        self.off_edit = QLineEdit('0')
        self.off_edit.setValidator(QDoubleValidator(0, 6, 4))
        self.grid.addWidget(self.off_edit, 2, 1)
        self.calc_button = QPushButton('Calculate Currents')
        self.grid.addWidget(self.calc_button, 2, 2) 
        self.calc_button.clicked.connect(self.calc_clicked)
        
    def calc_clicked(self):
        '''
        '''  
        self.parent.background = self.parent.frost/5*float(self.current_edit.text())*0.061594  # calibration for current at 5T 
        self.parent.goals = self.parent.tilt(float(self.off_edit.text()), float(self.goal_edit.text()))
        self.parent.just_shims = [float('nan')]*61
        self.parent.just_shims, self.parent.shimmed, self.parent.x = self.parent.calc_currents(self.parent.background, self.parent.goals)
        self.parent.update_plots()
        self.parent.enter_currents()
        return
        
class LikeCLAS(QWidget):
    '''Layout and method for making like CLAS solenoid field
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Make it CLASsy"
                
        self.grid = QGridLayout()
        self.space.addLayout(self.grid)
        self.current_label = QLabel("FROST Magnet Current (A):")
        self.grid.addWidget(self.current_label, 0, 0)
        self.current_edit = QLineEdit('0')
        self.current_edit.setValidator(QDoubleValidator(0, 90, 4))
        self.grid.addWidget(self.current_edit, 0, 1)
        self.goal_label = QLabel("CLAS Field Strength (T):")
        self.grid.addWidget(self.goal_label, 1, 0)
        self.goal_edit = QLineEdit('0')
        self.goal_edit.setValidator(QDoubleValidator(0, 6, 4))
        self.grid.addWidget(self.goal_edit, 1, 1)
        self.calc_button = QPushButton('Calculate Currents')
        self.grid.addWidget(self.calc_button, 1, 2) 
        self.calc_button.clicked.connect(self.calc_clicked)
        
    def calc_clicked(self):
        '''
        '''  
        self.parent.background = self.parent.frost/5*float(self.current_edit.text())*0.061594  # calibration for current at 5T 
        self.parent.goals = self.parent.clas/5*float(self.goal_edit.text())
        self.parent.just_shims, self.parent.shimmed, self.parent.x = self.parent.calc_currents(self.parent.background, self.parent.goals)
        self.parent.update_plots()
        self.parent.enter_currents()
        return  
        
class ShimControl():
    '''Interface with R&S HMP4040
    
    Arguments:
        Config: Current Config object
    '''
        
    def __init__(self, config):    
        '''Open connection to Rsinstrument  
        '''
        self.host = config.settings['shim_settings']['ip']
        self.timeout = config.settings['shim_settings']['timeout']
        self.port = config.settings['shim_settings']['port']   
        
        try:
            self.tn = telnetlib.Telnet(self.host, port=self.port, timeout=self.timeout)
            print("Connected to R&S shim supply on", self.host)
        except Exception as e:
            print("Error connecting to R&S current supply.", e)
        
        
    def set_currents(self, list):
        '''Set currents on R&S from list passed
        '''
        for i, c in enumerate(list):
            try:
                #print("Set shim channel", i+1, "to", {list[i]})
                self.tn.write(bytes(f"INST:NSEL {i+1}\n", 'ascii'))
                volt = list[i] * config.settings['shim_settings']['line_resistance'] + 0.5
                # Set voltage based on current and setting of line resistance, plus 0.5 V
                self.tn.write(bytes(f"VOLT {volt}\n", 'ascii'))
                self.tn.write(bytes(f"CURR {list[i]}\n", 'ascii'))
                time.sleep(0.1)
            except Exception as e:
                print("Error setting currents on R&S current supply.", e) 
            
    def read_currents(self):
        '''Set currents on R&S from list passed
        '''
        reads = [0]*4
        for i in range(0,4):        
            try:
                self.tn.write(bytes(f"INST:NSEL {i+1}\n", 'ascii'))
                self.tn.write(bytes(f"CURR? \n", 'ascii'))
                reads[i] = self.tn.read_some().decode('ascii')     
                time.sleep(0.1)   
            except Exception as e:
                print("Error reading currents on R&S current supply.", e)         
        return reads
    
    def read_outstat(self):
        
        try:
            self.tn.write(bytes(f"OUTP:GEN? \n", 'ascii'))
            out =  self.tn.read_some().decode('ascii') 
            return out
        except Exception as e:
            print("Error reading status on R&S current supply.", e) 
            return 999
        
        
    def set_outstat(self, state):
        '''Takes state as 0 or 1, returns
        '''
        self.tn.write(bytes(f"OUTP:GEN {state} \n", 'ascii'))
        self.tn.write(bytes(f"OUTP:GEN? \n", 'ascii'))
        return self.tn.read_some().decode('ascii') 
        
