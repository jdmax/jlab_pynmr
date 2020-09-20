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

        self.base_pen = pg.mkPen(color=(180, 0, 0), width=1)
        self.base2_pen = pg.mkPen(color=(0, 0, 150), width=1)
        self.base3_pen = pg.mkPen(color=(0, 180, 0), width=1)
        self.sub_pen = pg.mkPen(color=(180, 0, 0), width=1)
        self.sub2_pen = pg.mkPen(color=(0, 0, 150), width=1)
        self.sub3_pen = pg.mkPen(color=(0, 180, 0), width=1)
        
        self.base_chosen = None
        self.sub_chosen = None
        
        
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
        
        # Set up list of baseline options, putting instances into stack
        self.base_opts = []
        self.base_opts.append(StandardBaseline(self))   
        self.base_opts.append(PolyFitBase(self))        
        for o in self.base_opts:
            self.base_combo.addItem(o.name)
            self.base_stack.addWidget(o)
        
        
        # Subtraction and Sum Box
        self.sub_box = QGroupBox('Subtract and Sum Options')
        self.sub_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.sub_box)
        self.sub_combo = QComboBox()
        self.sub_box.layout().addWidget(self.sub_combo)
        self.sub_stack = QStackedWidget()    
        self.sub_box.layout().addWidget(self.sub_stack)
        
        self.sub_opts = []
        self.sub_opts.append(PolyFitSub(self))
        self.sub_opts.append(JustSum(self))
        for o in self.sub_opts:
            self.sub_combo.addItem(o.name)
            self.sub_stack.addWidget(o)
        
        # Results Box
        self.results_box = QGroupBox('Results')
        self.left.addWidget(self.results_box)

        # Right Side
        self.right = QVBoxLayout() 
        self.main.addLayout(self.right)
        
        self.base_wid = pg.PlotWidget(title='Baseline Subtraction')
        self.base_wid.showGrid(True,True)
        self.raw_plot = self.base_wid.plot([], [], pen=self.base_pen) 
        self.base_plot = self.base_wid.plot([], [], pen=self.base2_pen) 
        self.basesub_plot = self.base_wid.plot([], [], pen=self.base3_pen) 
        self.right.addWidget(self.base_wid)

        self.sub_wid = pg.PlotWidget(title='Fit Subtraction')
        self.sub_wid.showGrid(True,True)
        self.sub_plot = self.sub_wid.plot([], [], pen=self.sub_pen) 
        self.fit_plot = self.sub_wid.plot([], [], pen=self.sub2_pen) 
        self.fitsub_plot = self.sub_wid.plot([], [], pen=self.sub3_pen) 
        self.right.addWidget(self.sub_wid)

        # Setup default methods
        self.base_combo.currentIndexChanged.connect(self.change_base)
        self.sub_combo.currentIndexChanged.connect(self.change_sub)
        self.change_base(0)
        self.change_sub(0)
    
    def change_base(self, i):
        '''Set base_chosen to correct baseline class instance
        '''
        self.base_chosen = self.base_opts[i].result
        self.base_stack.setCurrentIndex(i)
        if self.base_chosen and self.sub_chosen:
            self.parent.event.signal_analysis(self.base_chosen, self.sub_chosen)
            self.update_event_plots()
        
    def change_sub(self, i):
        '''Set sub_chosen to correct subtraction class instance
        '''
        self.sub_chosen = self.sub_opts[i].result
        self.sub_stack.setCurrentIndex(i)
        if self.base_chosen and self.sub_chosen:
            self.parent.event.signal_analysis(self.base_chosen, self.sub_chosen)
            self.update_event_plots()

    def update_event_plots(self):
        '''Update analysis tab plots. Right now doing a DC subtraction on unsubtracted signals.
        '''
        self.raw_plot.setData(self.parent.event.scan.freq_list, self.parent.event.scan.phase - self.parent.event.scan.phase.max())
        self.base_plot.setData(self.parent.event.scan.freq_list, self.parent.event.basesweep - self.parent.event.basesweep.max())
        self.basesub_plot.setData(self.parent.event.scan.freq_list, self.parent.event.basesub - self.parent.event.basesub.max())
        
        self.sub_plot.setData(self.parent.event.scan.freq_list, self.parent.event.basesub - self.parent.event.basesub.max())
        self.fit_plot.setData(self.parent.event.scan.freq_list, self.parent.event.poly_curve - self.parent.event.poly_curve.max())
        self.fitsub_plot.setData(self.parent.event.scan.freq_list, self.parent.event.polysub)
    

class StandardBaseline(QWidget):
    '''Layout and method for standard baseline subtract based on selected baseline from baseline tab
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Baseline Selected from Baseline Tab"
        
        
    def result(self, event):
        '''Perform standard baseline subtraction
        
        Arguments:
            event: Event instance with sweeps to subtract
            
        Returns:
            baseline sweep, baseline subtracted sweep 
        '''
        
        basesweep = event.baseline
        
        return basesweep, event.scan.phase - basesweep
    
class PolyFitBase(QWidget):
    '''Layout for polynomial fit to the background wings, including methods to produce fits
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.name = "Polynomial Fit to Wings"
        
        self.space = QVBoxLayout()
        self.setLayout(self.space)        
        self.grid = QGridLayout()
        self.space.addLayout(self.grid)
        self.poly_label = QLabel("Polynomial order:")
        self.grid.addWidget(self.poly_label, 0, 0)
        self.poly_combo = QComboBox()
        self.grid.addWidget(self.poly_combo, 0, 1)
        self.poly_opts = ['2nd Order', '3rd Order', '4th Order']
        self.poly_combo.addItems(self.poly_opts)
        self.poly_combo.currentIndexChanged.connect(self.change_poly)
        self.change_poly(1)
        self.poly_combo.setCurrentIndex(1)
    
    def change_poly(self, i):
        '''Choose polynomial order method'''
        if i==0:
            self.base_poly = self.poly2
            self.pi = [0.01, 0.8, 0.01]
        elif i==1:
            self.base_poly = self.poly3
            self.pi = [0.01, 0.8, 0.01, 0.001]
        elif i==2:
            self.base_poly = self.poly4
            self.pi = [0.01, 0.8, 0.01, 0.001, 0.00001]
        self.parent.change_base(self.parent.base_combo.currentIndex())
    
    def result(self, event):
        '''Perform standard polyfit baseline subtraction
        
        Arguments:
            event: Event instance with sweeps to subtract
            
        Returns:
            polyfit used, baseline subtracted sweep 
        '''
    
        sweep = event.scan.phase
        wings = [0, .25, .75, 1]
        bounds = [x*len(sweep) for x in wings]
        data = [(x,y) for x,y in enumerate(sweep) if (bounds[0]<x<bounds[1] or bounds[2]<x<bounds[3])]
        X = np.array([x for x,y in data])
        Y = np.array([y for x,y in data])
        
        pi = [0.01, 0.8, 0.01, 0.001, 0.00001]  # initial guess
        #pf, success = optimize.leastsq(errfunc, pi[:], args=(X,Y))  # perform fit
        pf, pcov = optimize.curve_fit(self.base_poly, X, Y, p0 = self.pi)
        fit = self.base_poly(range(len(sweep)), *pf)
        sub = sweep - fit
        return fit, sub
        
        
    def poly2(self, x, *p): 
        return p[0] + p[1]*x + p[2]*np.power(x,2)   
        
    def poly3(self, x, *p): return p[0] + p[1]*x + p[2]*np.power(x,2) + p[3]*np.power(x,3) 
        
    def poly4(self, x, *p): return p[0] + p[1]*x + p[2]*np.power(x,2) + p[3]*np.power(x,3) + p[4]*np.power(x,4)
        

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
        '''Perform standard polyfit subtraction
        
        Arguments:
            event: Event instance with sweeps to subtract
            
        Returns:
            polyfit used, subtracted sweep, integrated area
        '''
    
        sweep = event.basesub
        wings = [0, .25, .75, 1]
        bounds = [x*len(sweep) for x in wings]
        data = [(x,y) for x,y in enumerate(sweep) if (bounds[0]<x<bounds[1] or bounds[2]<x<bounds[3])]
        X = np.array([x for x,y in data])
        Y = np.array([y for x,y in data])
        
        errfunc = lambda p, x, y: self.poly3(p,x) - y
        pi = [0.01, 0.8, 0.01, 0.001, 0.00001]  # initial guess
        pf, success = optimize.leastsq(errfunc, pi[:], args=(X,Y))  # perform fit
        fitcurve = self.poly3(pf, range(len(sweep)))
        sub = sweep - fitcurve
        area = sub.sum()
        return fitcurve, sub, area
        
        
    def poly2(self, p, x):
        '''Third order polynomial for fitting
        
        Args:
            p: List of polynomial coefficients
            x: Sample point
        '''
        return p[0] + p[1]*x + p[2]*np.power(x,2) #+ p[3]*np.power(x,3) #+ p[4]*np.power(x,4)
        
    def poly3(self, p, x):
        '''Third order polynomial for fitting
        
        Args:
            p: List of polynomial coefficients
            x: Sample point
        '''
        return p[0] + p[1]*x + p[2]*np.power(x,2) + p[3]*np.power(x,3) #+ p[4]*np.power(x,4)
        
    def poly4(self, p, x):
        '''Third order polynomial for fitting
        
        Args:
            p: List of polynomial coefficients
            x: Sample point
        '''
        return p[0] + p[1]*x + p[2]*np.power(x,2) + p[3]*np.power(x,3) + p[4]*np.power(x,4)
        


class JustSum(QWidget):
    '''Layout for polynomial fit to the background wings, including methods to produce fits
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Just Integrate"
        self.poly_label = QLabel("No fit subtraction, just sum")
        self.space.addWidget(self.poly_label)
    
    def result(self, event):        
        '''Only performs sum
        '''
        sweep = event.basesub
        fitcurve = np.zeros(len(sweep))
        sub = sweep - fitcurve
        area = sub.sum()
        return fitcurve, sub, area
        

        
