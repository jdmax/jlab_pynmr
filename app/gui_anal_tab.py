'''PyNMR, J.Maxwell 2020
'''
import numpy as np
from scipy import optimize
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, QSizePolicy, QComboBox, QPushButton, QProgressBar, QStackedWidget
import pyqtgraph as pg

class AnalTab(QWidget):
    '''Creates analysis tab. Starts threads for run and to update plots'''

    def __init__(self, parent):
        super(QWidget,self).__init__(parent)
        self.__dict__.update(parent.__dict__)
        
        self.parent = parent

        self.base_pen = pg.mkPen(color=(0, 0, 204), width=1)
        self.base2_pen = pg.mkPen(color=(0, 0, 150), width=1)
        self.sub_pen = pg.mkPen(color=(0, 180, 0), width=1)
        self.sub2_pen = pg.mkPen(color=(0, 130, 0), width=1)
        
        
        self.main = QHBoxLayout()            # main layout
        self.setLayout(self.main)   
        
        # Left Side
        self.left = QVBoxLayout() 
        self.main.addLayout(self.left)
        
        # Baseline options box
        self.base_box = QGroupBox('Baseline Options')
        self.base_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.base_box)        
        self.base_combo = QComboBox()
        self.base_box.layout().addWidget(self.base_combo)
        self.base_stack = QStackedWidget()    
        self.base_box.layout().addWidget(self.base_stack)
        self.base_combo.currentIndexChanged.connect(self.change_base)
        
        # Set up list of baseline options, putting instances into stack
        self.base_opts = []
        self.base_opts.append(PolyFitBase(self))        
        for o in self.base_opts:
            self.base_combo.addItem(o.name)
            self.base_stack.addWidget(o)
        self.change_base(0)
        
        
        # Subtraction and Sum Box
        self.sub_box = QGroupBox('Subtract and Sum Options')
        self.sub_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.sub_box)
        self.sub_combo = QComboBox()
        self.sub_box.layout().addWidget(self.sub_combo)
        self.sub_stack = QStackedWidget()    
        self.sub_box.layout().addWidget(self.sub_stack)
        self.sub_combo.currentIndexChanged.connect(self.change_sub)
        
        self.sub_opts = []
        self.sub_opts.append(PolyFitSub(self))
        for o in self.sub_opts:
            self.sub_combo.addItem(o.name)
            self.sub_stack.addWidget(o)
        self.change_sub(0)
        
        # Results Box
        self.results_box = QGroupBox('Results')
        self.left.addWidget(self.results_box)

        # Right Side
        self.right = QVBoxLayout() 
        self.main.addLayout(self.right)
        
        self.base_wid = pg.PlotWidget(title='Baseline')
        self.base_wid.showGrid(True,True)
        self.base_plot = self.base_wid.plot([], [], pen=self.base_pen) 
        self.right.addWidget(self.base_wid)

        self.sub_wid = pg.PlotWidget(title='Subtraction and Integration')
        self.sub_wid.showGrid(True,True)
        self.sub_plot = self.sub_wid.plot([], [], pen=self.sub_pen) 
        self.right.addWidget(self.sub_wid)

    
    def change_base(self, i):
        '''Set base_chosen to correct baseline class instance
        '''
        self.base_chosen = self.base_opts[i].result
        
    def change_sub(self, i):
        '''Set sub_chosen to correct subtraction class instance
        '''
        self.sub_chosen = self.sub_opts[i].result

    

class PolyFitBase(QWidget):
    '''Layout for polynomial fit to the background wings, including methods to produce fits
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Polynomial Fit to Wings"
        self.poly_label = QLabel("Polynomial order")
        self.space.addWidget(self.poly_label)
    
    
    def result(self, event):
    
        sweep = event.scan.phase
        wings = [0, .25, .75, 1]
        bounds = [x*len(sweep) for x in wings]
        data = [(x,y) for x,y in enumerate(sweep) if (bounds[0]<x<bounds[1] or bounds[2]<x<bounds[3])]
        x = np.array([x for x,y in data])
        y = np.array([y for x,y in data])
        
        p0 = [0.01, 0.8, 0.01, 0.001, 0.00001]  # initial guess
        pf, pcov = optimize.curve_fit(poly4, x, y, p0 = p0)
        pstd = np.sqrt(np.diag(pcov))
        string = f"Parameters: "
        for p, std in zip(pf, pstd):
            string += f"{p} ± {std}, "
        string = string[:-2]    
        
        return sweep - poly4(pf, range(0, len(sweep))), string
        

class PolyFitSub(QWidget):
    '''Layout for polynomial fit to the background wings, including methods to produce fits
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Polynomial Fit to Wings"
        self.poly_label = QLabel("Polynomial order")
        self.space.addWidget(self.poly_label)
    
    def result(self, event):
        sub = event.sweep
        area = sub.sum()
        return sub, area
        
        

def poly3(self, p, x):
    '''Third order polynomial for fitting
    
    Args:
        p: List of polynomial coefficients
        x: Sample point
    '''
    return p[0] + p[1]*x + p[2]*np.power(x,2) + p[3]*np.power(x,3) #+ p[4]*np.power(x,4)
    
def poly4(self, p, x):
    '''Fourth order polynomial for fitting
    
    Args:
        p: List of polynomial coefficients
        x: Sample point
    '''
    return p[0] + p[1]*x + p[2]*np.power(x,2) + p[3]*np.power(x,3) + p[4]*np.power(x,4)        
       