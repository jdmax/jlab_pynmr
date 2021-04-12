'''PyNMR, J.Maxwell 2020
'''
import numpy as np
from scipy import optimize
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, QSizePolicy, QComboBox, QPushButton, QProgressBar, QStackedWidget, QDoubleSpinBox
import pyqtgraph as pg
from lmfit import Model

class AnalTab(QWidget):
    '''Creates analysis tab. '''

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
        self.res_chosen = None
        
        
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
        
               
        # Subtraction and Sum Box
        self.sub_box = QGroupBox('Fit Options')
        self.sub_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.sub_box)
        self.sub_combo = QComboBox()
        self.sub_box.layout().addWidget(self.sub_combo)
        self.sub_stack = QStackedWidget()    
        self.sub_box.layout().addWidget(self.sub_stack)
           
        # Results Box
        self.res_box = QGroupBox('Results')
        self.res_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.res_box)
        self.res_combo = QComboBox()
        self.res_box.layout().addWidget(self.res_combo)
        self.res_stack = QStackedWidget()    
        self.res_box.layout().addWidget(self.res_stack)

        # Right Side
        self.right = QVBoxLayout() 
        self.main.addLayout(self.right)
        
        self.base_wid = pg.PlotWidget(title='Baseline Subtraction')
        self.base_wid.showGrid(True,True)
        self.base_wid.addLegend(offset=(0.5, 0))
        self.raw_plot = self.base_wid.plot([], [], pen=self.base_pen, name='Raw Signal') 
        self.base_plot = self.base_wid.plot([], [], pen=self.base2_pen, name='Baseline') 
        self.basesub_plot = self.base_wid.plot([], [], pen=self.base3_pen, name='Subtracted') 
        self.base_region1 = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 180, 0, 0))
        self.base_region1.setMovable(False)
        self.base_region1.setRegion([self.parent.event.scan.freq_list.min(), self.parent.event.scan.freq_list.min()])
        self.base_wid.addItem(self.base_region1)
        self.base_region2 = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 180, 0, 0))
        self.base_region2.setMovable(False)
        self.base_region2.setRegion([self.parent.event.scan.freq_list.max(), self.parent.event.scan.freq_list.max()])
        self.base_wid.addItem(self.base_region2)
        self.right.addWidget(self.base_wid)

        self.sub_wid = pg.PlotWidget(title='Fit Subtraction and Results')
        self.sub_wid.showGrid(True,True)
        self.sub_wid.addLegend(offset=(0.5, 0))
        self.sub_plot = self.sub_wid.plot([], [], pen=self.sub_pen, name='Unchanged') 
        self.fit_plot = self.sub_wid.plot([], [], pen=self.sub2_pen, name='Fit') 
        self.fitsub_plot = self.sub_wid.plot([], [], pen=self.sub3_pen, name='Subtracted') 
        self.sub_region1 = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 0, 180, 0))
        self.sub_region1.setMovable(False)
        self.sub_region1.setRegion([self.parent.event.scan.freq_list.min(), self.parent.event.scan.freq_list.min()])
        self.sub_wid.addItem(self.sub_region1)
        self.sub_region2 = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 0, 180, 0))
        self.sub_region2.setMovable(False)
        self.sub_region2.setRegion([self.parent.event.scan.freq_list.max(), self.parent.event.scan.freq_list.max()])
        self.sub_wid.addItem(self.sub_region2)
        self.res_region = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 180, 0, 0))
        self.res_region.setMovable(False)
        self.res_region.setRegion([self.parent.event.scan.freq_list.max(), self.parent.event.scan.freq_list.max()])
        self.sub_wid.addItem(self.res_region)
        self.right.addWidget(self.sub_wid)
     
        # Set up list of baseline options, putting instances into stack
        self.base_opts = []
        self.base_opts.append(StandardBaseline(self))   
        self.base_opts.append(PolyFitBase(self))  
        # self.base_opts.append(CircuitBase(self))   Not ready for prime time
        self.base_opts.append(NoBase(self))        
        for o in self.base_opts:
            self.base_combo.addItem(o.name)
            self.base_stack.addWidget(o)
        self.sub_opts = []
        self.sub_opts.append(PolyFitSub(self))
        self.sub_opts.append(NoFit(self))
        for o in self.sub_opts:
            self.sub_combo.addItem(o.name)
            self.sub_stack.addWidget(o)
        self.res_opts = []
        self.res_opts.append(SumAll(self))
        self.res_opts.append(SumRange(self))
        self.res_opts.append(PeakHeight(self))
        for o in self.res_opts:
            self.res_combo.addItem(o.name)
            self.res_stack.addWidget(o)
        
        # Setup default methods
        self.base_combo.currentIndexChanged.connect(self.change_base)
        self.base_combo.setCurrentIndex(self.event.config.settings['analysis']['base_def'])
        self.change_base(self.event.config.settings['analysis']['base_def'])
        self.sub_combo.currentIndexChanged.connect(self.change_sub)
        self.sub_combo.setCurrentIndex(self.event.config.settings['analysis']['sub_def'])
        self.change_sub(self.event.config.settings['analysis']['sub_def'])
        self.res_combo.currentIndexChanged.connect(self.change_res)
        self.res_combo.setCurrentIndex(self.event.config.settings['analysis']['res_def'])
        self.change_res(self.event.config.settings['analysis']['res_def'])
    
    def change_base(self, i):
        '''Set base_chosen to correct baseline class instance
        '''
        self.base_chosen = self.base_opts[i].result
        self.base_opts[i].switch_here()
        self.base_stack.setCurrentIndex(i)
        self.run_analysis()
        
    def change_sub(self, i):
        '''Set sub_chosen to desired subtraction class instance
        '''
        self.sub_chosen = self.sub_opts[i].result
        self.sub_opts[i].switch_here()
        self.sub_stack.setCurrentIndex(i)
        self.run_analysis()
        
    def change_res(self, i):
        '''Set res_chosen to desired subtraction class instance
        '''
        self.res_chosen = self.res_opts[i].result
        self.res_opts[i].switch_here()
        self.res_stack.setCurrentIndex(i)
        self.run_analysis()
            
    def run_analysis(self):
        '''Run event signal analysis and call for new plots if base and sub methods are chosen'''
        if self.base_chosen and self.sub_chosen and self.res_chosen:
            self.parent.event.signal_analysis(self.base_chosen, self.sub_chosen, self.res_chosen)
            self.update_event_plots()

    def update_event_plots(self):
        '''Update analysis tab plots. Right now doing a DC subtraction on unsubtracted signals.
        '''
        self.raw_plot.setData(self.parent.event.scan.freq_list, self.parent.event.scan.phase - self.parent.event.scan.phase.max())
        self.base_plot.setData(self.parent.event.scan.freq_list, self.parent.event.basesweep - self.parent.event.basesweep.max())
        self.basesub_plot.setData(self.parent.event.scan.freq_list, self.parent.event.basesub - self.parent.event.basesub.max())
        
        #print(self.parent.event.basesub, self.parent.event.poly_curve, self.parent.event.polysub)
        self.sub_plot.setData(self.parent.event.scan.freq_list, self.parent.event.basesub - self.parent.event.basesub.max())
        self.fit_plot.setData(self.parent.event.scan.freq_list, self.parent.event.fitcurve - self.parent.event.fitcurve.max())
        self.fitsub_plot.setData(self.parent.event.scan.freq_list, self.parent.event.fitsub)
        
class StandardBaseline(QWidget):
    '''Layout and method for standard baseline subtract based on selected baseline from baseline tab
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Baseline Selected from Baseline Tab"
        self.message = QLabel()
        self.space.layout().addWidget(self.message)
        

    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.base_region1.setBrush(pg.mkBrush(0, 0, 180, 0))
        self.parent.base_region2.setBrush(pg.mkBrush(0, 0, 180, 0))
    
    def result(self, event):
        '''Perform standard baseline subtraction, 
        
        Arguments:
            event: Event instance with sweeps to subtract
            
        Returns:
            baseline sweep, baseline subtracted sweep 
        '''      
        
        basesweep = event.baseline
        self.message.setText(f"Baseline from {event.base_time.strftime('%D %H:%M:%S')} UTC")
        
        
        return basesweep, event.scan.phase - basesweep
    
class PolyFitBase(QWidget):
    '''Layout for polynomial fit to the background wings, including methods to produce fits
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.name = "Polynomial Fit to Wings"
        self.wings = self.parent.event.config.settings['analysis']['wings']
                        
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
        
        self.grid2 = QGridLayout()
        self.space.addLayout(self.grid2)
        self.bounds_label = QLabel("Fit bounds (0 to 1):")
        self.grid2.addWidget(self.bounds_label, 0, 0)
        self.bounds_sb = []
        for i, n in enumerate(self.wings):    # setup spin boxes for each bound
            self.bounds_sb.append(QDoubleSpinBox())
            self.bounds_sb[i].setValue(n)
            self.bounds_sb[i].setSingleStep(0.01)
            self.bounds_sb[i].valueChanged.connect(self.change_wings)
            
            self.grid2.addWidget(self.bounds_sb[i], 0, i+1)
        self.change_wings()    
        
        self.message = QLabel()
        self.space.layout().addWidget(self.message)
    
    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.base_region1.setBrush(pg.mkBrush(0, 0, 180, 20))
        self.parent.base_region2.setBrush(pg.mkBrush(0, 0, 180, 20))
    
    
    def change_poly(self, i):
        '''Choose polynomial order method'''
        if i==0:
            self.poly = self.poly2
            self.pi = [0.01, 0.8, 0.01]
        elif i==1:
            self.poly = self.poly3
            self.pi = [0.01, 0.8, 0.01, 0.001]
        elif i==2:
            self.poly = self.poly4
            self.pi = [0.01, 0.8, 0.01, 0.001, 0.00001]
        self.parent.run_analysis()
    
    def change_wings(self):
        '''Choose fit frequency bounds'''
        wings = [n.value() for n in self.bounds_sb]     
        self.wings =  sorted(wings)
        for w, b in zip(self.wings, self.bounds_sb):
            b.setValue(w)      
        min = self.parent.parent.event.scan.freq_list.min()
        max = self.parent.parent.event.scan.freq_list.max() 
        
        bounds = [w*(max-min)+min for w in self.wings]  
        self.parent.base_region1.setRegion(bounds[:2])
        self.parent.base_region2.setRegion(bounds[2:])
        self.parent.run_analysis()
        
    def result(self, event):
        '''Perform standard polyfit baseline subtraction
        
        Arguments:
            event: Event instance with sweeps to subtract
            
        Returns:
            polyfit used, baseline subtracted sweep 
        '''
        sweep = event.scan.phase
        freqs = event.scan.freq_list
        bounds = [x*len(sweep) for x in self.wings]
        data = [z for x,z in enumerate(zip(freqs, sweep)) if (bounds[0]<x<bounds[1] or bounds[2]<x<bounds[3])]
        X = np.array([x for x,y in data])
        Y = np.array([y for x,y in data])
        pf, pcov = optimize.curve_fit(self.poly, X, Y, p0 = self.pi)
        pstd = np.sqrt(np.diag(pcov))
        fit = self.poly(freqs, *pf)
        sub = sweep - fit
        
        residuals = Y - self.poly(X, *pf)
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((Y - np.mean(Y))**2)
        r_squared = 1 - (ss_res / ss_tot)        
        
        text_list = [f"{f:.2e} ± {s:.2e}" for f, s in zip(pf, pstd)]
        self.message.setText(f"Fit coefficients: \t \t \t R-squared: {r_squared:.2f}\n"+"\n".join(text_list))
        return fit, sub
        
    def poly2(self, x, *p): return p[0] + p[1]*x + p[2]*np.power(x,2)   
        
    def poly3(self, x, *p): return p[0] + p[1]*x + p[2]*np.power(x,2) + p[3]*np.power(x,3) 
        
    def poly4(self, x, *p): return p[0] + p[1]*x + p[2]*np.power(x,2) + p[3]*np.power(x,3) + p[4]*np.power(x,4)
        

   
class CircuitBase(QWidget):
    '''Layout for circuit model fit to the background wings, including methods to produce fits
    
    NOT IMPLEMENTED. Fits not quite converging, slow.
    
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.name = "Circuit Model Fit"
        self.wings = self.parent.event.config.settings['analysis']['wings']
                        
        self.space = QVBoxLayout()
        self.setLayout(self.space)        
        self.grid = QGridLayout()
        
        self.grid2 = QGridLayout()
        self.space.addLayout(self.grid2)
        self.bounds_label = QLabel("Fit bounds (0 to 1):")
        self.grid2.addWidget(self.bounds_label, 0, 0)
        self.bounds_sb = []
        for i, n in enumerate(self.wings):    # setup spin boxes for each bound
            self.bounds_sb.append(QDoubleSpinBox())
            self.bounds_sb[i].setValue(n)
            self.bounds_sb[i].setSingleStep(0.01)
            self.bounds_sb[i].valueChanged.connect(self.change_wings)
            
            self.grid2.addWidget(self.bounds_sb[i], 0, i+1)
        self.change_wings()    
        
        self.message = QLabel()
        self.space.layout().addWidget(self.message)
    
    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.base_region1.setBrush(pg.mkBrush(0, 0, 180, 0))
        self.parent.base_region2.setBrush(pg.mkBrush(0, 0, 180, 0))
            
    def change_wings(self):
        '''Choose fit frequency bounds'''
        wings = [n.value() for n in self.bounds_sb]     
        self.wings =  sorted(wings)
        for w, b in zip(self.wings, self.bounds_sb):
            b.setValue(w)      
        min = self.parent.parent.event.scan.freq_list.min()
        max = self.parent.parent.event.scan.freq_list.max() 
        
        bounds = [w*(max-min)+min for w in self.wings]  
        self.parent.base_region1.setRegion(bounds[:2])
        self.parent.base_region2.setRegion(bounds[2:])
        self.parent.run_analysis()
        
    def result(self, event):
        '''Perform circuit model fit baseline subtraction
        
        Arguments:
            event: Event instance with sweeps to subtract
            
        Returns:
            fit used, baseline subtracted sweep 
        '''
        sweep = event.scan.phase
        bounds = [x*len(sweep) for x in self.wings]
        data = [(x,y) for x,y in enumerate(sweep) if (bounds[0]<x<bounds[1] or bounds[2]<x<bounds[3])]
        f = np.array([x for x,y in data])
        Y = np.array([y for x,y in data])        
            
        mod = Model(self.real_curve)
        params = mod.make_params()
        params.add('cap', value=18.62, min=1.0, max=60.0)
        params.add('phase', value=-140, min=-180, max=180)
        params.add('coil_l', value=30, min=1.0, max=120)
        params.add('offset', value=0.19, min=-10, max=10)
        params.add('scale', value=5, min=4.99, max=5.001)
                
        result = mod.fit(Y, params, f=f)
        print(result.best_values)      
        fit = self.real_curve(range(len(event.scan.phase)), **result.best_values)
        sub = sweep - fit
        #text_list = [f"{f:.2e} ± {s:.2e}" for f, s in zip(pf, pstd)]
        #self.message.setText("Fit coefficients:\n"+"\n".join(text_list))
        return fit, sub

    def full_curve(self, f, cap, phase, coil_l):
        '''
        Returns full complex voltage out of Q-curve.  
        
        Arguments:
            f: frequency f in MHz
            cap: tuning capacitance in pF
            phase: phase in degrees
            coil_l: coil inductance in nanoHenries
        '''
        w = 2*np.pi*f*1e6         # angular frequency 
        c = cap*1e-12             # Cap in F
        u = 0.6                   # Input RF voltage
        r_cc = 681                # Constant current resistor
        i = u/r_cc                # Constant current
        c_stray = 0.0000001e-12   # Stray capacitance
        l_coil = coil_l*1e-9      # Inductance of coil
        r_coil = 0.3              # Resistance of coil
        r_amp = 50                # Impedance of detector
        r = 10                    # Damping resistor

        zc = 1/np.complex(0,w*c)                     # impedance of cap
        zc_stray = 1/np.complex(0,w*c_stray)         # impedance of stray cap
        zl_pure  = np.complex(r_coil,w*l_coil)       # impedance of coil only
        zl = zl_pure*zc_stray/(zl_pure+zc_stray)     # impedance of coil and stray capacitance
        z_leg = r + zc + zl                          # impedance of the damping resistor, cap, coil
        z_tot = r_amp/(1+r_amp/z_leg)                # total impedance of coil, trans line and detector (voltage divider)

        phi = phase*np.pi/180                        # phase bet. constant current and output voltage
        v_out = i*z_tot*np.exp(np.complex(0,phi))
        return (v_out)
        
    def mag_curve(self, f, cap, phase, coil_l, offset=0, scale=1):
        ''' Passed list of frequency points, calls full_curve at each point to get magnitude of Q-curve'''
        v_out = [np.absolute(self.full_curve(k, cap, phase, coil_l)) for k in f]
        return ([vout*scale+offset for vout in v_out])
        
    def real_curve(self, f, cap, phase, coil_l, offset=0, scale=1):
        ''' Passed list of frequency points, calls full_curve at each point to get real portion of Q-curve'''
        v_out = [-np.real(self.full_curve(k, cap, phase, coil_l)) for k in f]
        return ([vout*scale+offset for vout in v_out])



class NoBase(QWidget):
    '''Layout for no fit to the background wings, including methods to produce fits
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "No Baseline Subtraction"
        self.poly_label = QLabel("No baseline subtraction")
        self.space.addWidget(self.poly_label)
        self.message = QLabel()
        self.space.layout().addWidget(self.message)
    
    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.base_region1.setBrush(pg.mkBrush(0, 0, 180, 0))
        self.parent.base_region2.setBrush(pg.mkBrush(0, 0, 180, 0))        
        
    def result(self, event):        
        '''Only performs sum
        '''
        sweep = event.scan.phase
        fitcurve = np.zeros(len(sweep))
        sub = sweep - fitcurve
        area = sub.sum()
        return fitcurve, sub        

class PolyFitSub(QWidget):
    '''Layout for polynomial fit to the background wings, including methods to produce fits
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.name = "Polynomial Fit to Wings"
        self.wings = self.parent.event.config.settings['analysis']['wings']
        
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
        
        self.grid2 = QGridLayout()
        self.space.addLayout(self.grid2)
        self.bounds_label = QLabel("Fit bounds (0 to 1):")
        self.grid2.addWidget(self.bounds_label, 0, 0)
        self.bounds_sb = []
        for i, n in enumerate(self.wings):    # setup spin boxes for each bound
            self.bounds_sb.append(QDoubleSpinBox())
            self.bounds_sb[i].setValue(n)
            self.bounds_sb[i].setSingleStep(0.01)
            self.bounds_sb[i].valueChanged.connect(self.change_wings)
            
            self.grid2.addWidget(self.bounds_sb[i], 0, i+1)
        self.change_wings()    
    
        self.message = QLabel()
        self.space.layout().addWidget(self.message)
    def change_poly(self, i):
        '''Choose polynomial order method'''
        if i==0:
            self.poly = self.poly2
            self.pi = [0.01, 0.8, 0.01]
        elif i==1:
            self.poly = self.poly3
            self.pi = [0.01, 0.8, 0.01, 0.001]
        elif i==2:
            self.poly = self.poly4
            self.pi = [0.01, 0.8, 0.01, 0.001, 0.00001]
        self.parent.run_analysis()        
    
    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.sub_region1.setBrush(pg.mkBrush(0, 0, 180, 20))
        self.parent.sub_region2.setBrush(pg.mkBrush(0, 0, 180, 20))
     

    def change_wings(self):
        '''Choose fit frequency bounds'''
        wings = [n.value() for n in self.bounds_sb]     
        self.wings =  sorted(wings)
        for w, b in zip(self.wings, self.bounds_sb):
            b.setValue(w)      
        min = self.parent.parent.event.scan.freq_list.min()
        max = self.parent.parent.event.scan.freq_list.max() 
        
        bounds = [w*(max-min)+min for w in self.wings]  
        self.parent.sub_region1.setRegion(bounds[:2])
        self.parent.sub_region2.setRegion(bounds[2:])
        self.parent.run_analysis()   
     
    def result(self, event):
        '''Perform standard polyfit baseline subtraction
        
        Arguments:
            event: Event instance with sweeps to subtract
            
        Returns:
            polyfit used, baseline subtracted sweep 
        '''
        
        sweep = event.basesub
        freqs = event.scan.freq_list
        bounds = [x*len(sweep) for x in self.wings]
        data = [z for x,z in enumerate(zip(freqs, sweep)) if (bounds[0]<x<bounds[1] or bounds[2]<x<bounds[3])]
        X = np.array([x for x,y in data])
        Y = np.array([y for x,y in data])
        print(X,Y)
        pf, pcov = optimize.curve_fit(self.poly, X, Y, p0 = self.pi)
        pstd = np.sqrt(np.diag(pcov))
        fit = self.poly(freqs, *pf)
        sub = sweep - fit
        
        area = sub.sum()
        
        residuals = Y - self.poly(X, *pf)
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((Y - np.mean(Y))**2)
        r_squared = 1 - (ss_res / ss_tot)    
        
        text_list = [f"{f:.2e} ± {s:.2e}" for f, s in zip(pf, pstd)]
        self.message.setText(f"Fit coefficients: \t \t \t R-squared: {r_squared:.2f}\n"+"\n".join(text_list))
        return fit, sub
        
    def poly2(self, x, *p): return p[0] + p[1]*x + p[2]*np.power(x,2)   
        
    def poly3(self, x, *p): return p[0] + p[1]*x + p[2]*np.power(x,2) + p[3]*np.power(x,3) 
        
    def poly4(self, x, *p): return p[0] + p[1]*x + p[2]*np.power(x,2) + p[3]*np.power(x,3) + p[4]*np.power(x,4)
        


class NoFit(QWidget):
    '''Layout for no fit to the background wings, including methods 
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "No Fit Subtraction"
        self.poly_label = QLabel("No fit subtraction")
        self.space.addWidget(self.poly_label)
        self.message = QLabel()
        self.space.layout().addWidget(self.message)
    
    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.sub_region1.setBrush(pg.mkBrush(0, 0, 180, 20))
        self.parent.sub_region2.setBrush(pg.mkBrush(0, 0, 180, 20))        
        
    def result(self, event):        
        '''Only performs sum
        '''
        sweep = event.basesub
        fitcurve = np.zeros(len(sweep))
        sub = sweep - fitcurve
        area = sub.sum()
        return fitcurve, sub
        
class SumAll(QWidget):
    '''Layout and methods for integrtation over full signal range
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Integrate Full Range"
        self.poly_label = QLabel("Sum Full Range")
        self.space.addWidget(self.poly_label)
        self.message = QLabel()
        self.space.layout().addWidget(self.message)
    
    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.res_region.setBrush(pg.mkBrush(0, 0, 180, 0))   
        
    def result(self, event):        
        '''Only performs sum
        '''
        sweep = event.fitsub
        fitcurve = np.zeros(len(sweep))
        sub = sweep - fitcurve
        area = sub.sum()
        pol = area*event.cc
        self.message.setText(f"Area: {area}")
        return area, pol
        

class SumRange(QWidget):
    '''Layout and methods for integration within a given range
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.name = "Integrate within Range"
        self.range = self.parent.event.config.settings['analysis']['sum_range']
        
        self.space = QVBoxLayout()
        self.setLayout(self.space)      
        
        self.grid2 = QGridLayout()
        self.space.addLayout(self.grid2)
        self.bounds_label = QLabel("Integration bounds (0 to 1):")
        self.grid2.addWidget(self.bounds_label, 0, 0)
        self.bounds_sb = []
        for i, n in enumerate(self.range):    # setup spin boxes for each bound
            self.bounds_sb.append(QDoubleSpinBox())
            self.bounds_sb[i].setValue(n)
            self.bounds_sb[i].setSingleStep(0.01)
            self.bounds_sb[i].valueChanged.connect(self.change_wings)
            
            self.grid2.addWidget(self.bounds_sb[i], 0, i+1)
        self.change_wings()    
        self.message = QLabel()
        self.space.layout().addWidget(self.message)
         
    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.res_region.setBrush(pg.mkBrush(0, 180, 0, 20))

    def change_wings(self):
        '''Choose fit frequency bounds'''
        wings = [n.value() for n in self.bounds_sb]     
        self.wings =  sorted(wings)
        for w, b in zip(self.wings, self.bounds_sb):
            b.setValue(w)      
        min = self.parent.parent.event.scan.freq_list.min()
        max = self.parent.parent.event.scan.freq_list.max() 
        
        bounds = [w*(max-min)+min for w in self.wings]  
        self.parent.res_region.setRegion(bounds)
        self.parent.run_analysis()   
     
    def result(self, event):
        '''Perform standard polyfit baseline subtraction
        
        Arguments:
            event: Event instance with sweeps to subtract
            
        Returns:
            polyfit used, baseline subtracted sweep 
        '''
    
        sweep = event.fitsub
        bounds = [x*len(sweep) for x in self.wings]
        data = [(x,y) for x,y in enumerate(sweep) if bounds[0]<x<bounds[1]]
        Y = np.array([y for x,y in data])
        area = Y.sum()
        pol = area*event.cc
        self.message.setText(f"Area: {area}")
        return area, pol
        
class PeakHeight(QWidget):
    '''Layout and methods for peak height results method. Area attribute is filled with peak height instead.
    '''
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Peak Height"
        self.poly_label = QLabel("When using this method, the peak height replaces\nthe area throughout the application.")
        self.space.addWidget(self.poly_label)
        self.message = QLabel()
        self.space.layout().addWidget(self.message)
    
    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.res_region.setBrush(pg.mkBrush(0, 0, 180, 0))   
        
    def result(self, event):        
        '''Find peak height
        '''
        sweep = event.fitsub
        max = np.max(sweep)
        min = np.min(sweep)        
        area = max if abs(max)>abs(min) else min   # Using peak height represent area
        
        pol = area*event.cc
        self.message.setText(f"Peak height: {area}")
        return area, pol
                
        