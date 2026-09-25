"""
Event Bus Integrated Analysis Tab for PyNMR

Migrated from analysis_tab.py to use event bus instead of direct parent access.
This version reuses the existing analysis classes but integrates with event bus.
"""

import numpy as np
from scipy import optimize
from PySide6.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, QSizePolicy, QComboBox, QPushButton, QProgressBar, QStackedWidget, QDoubleSpinBox
import pyqtgraph as pg
from lmfit import Model

from core.deuteron_fits import DFits
from core.tab_base import EventBusTab, AnalysisTabEventHandler
from core.event_bus import EventType

# Import the existing analysis classes
from .analysis_tab import (StandardBase, PolyFitBase, CircuitBase, NoBase,
                          PolyFitSub, NoFitSub, SumAllRes, SumRangeRes, 
                          PeakHeightRes, FitPeakRes, FitPeakRes2, FitDeuteron)


class AnalTabNew(EventBusTab):
    """Analysis tab with event bus integration."""

    def __init__(self, parent=None):
        super().__init__("analysis", parent)

        self.base_pen = pg.mkPen(color=(180, 0, 0), width=1.5)
        self.base2_pen = pg.mkPen(color=(0, 0, 150), width=1.5)
        self.base3_pen = pg.mkPen(color=(0, 180, 0), width=1.5)
        self.sub_pen = pg.mkPen(color=(180, 0, 0), width=1.5)
        self.sub2_pen = pg.mkPen(color=(0, 0, 150), width=1.5)
        self.sub3_pen = pg.mkPen(color=(0, 180, 0), width=1.5)
        self.res_pen = pg.mkPen(color=(180, 0, 0), width=1.5)
        self.res2_pen = pg.mkPen(color=(0, 0, 150), width=1.5)
        self.res3_pen = pg.mkPen(color=(0, 180, 0), width=1.5)
        
        self.base_chosen = None
        self.sub_chosen = None
        self.res_chosen = None
        
        self.current_event = None  # Will be updated via event bus
        
        # Create compatibility layer for existing analysis classes
        # They expect self.parent.parent to have event, config, etc.
        self.parent = self  # For compatibility
        
        self._init_ui()
    
    @property
    def event(self):
        """Get current event for compatibility with existing analysis classes."""
        event = self.get_current_event() or self.get_previous_event()
        if event is None:
            # Create a minimal event object for initialization
            # This provides the config during startup
            class MinimalEvent:
                def __init__(self, config):
                    self.config = config
                    # Create a minimal scan object with frequency list
                    class MinimalScan:
                        def __init__(self, config):
                            import numpy as np
                            # Use config frequency list or create a default one
                            if hasattr(config, 'freq_list'):
                                self.freq_list = config.freq_list
                            else:
                                self.freq_list = np.linspace(90, 110, 100)  # Default range
                    self.scan = MinimalScan(config)
            config = self.get_config()
            if config:
                event = MinimalEvent(config)
        return event
    
    @property
    def config(self):
        """Get config for compatibility with existing analysis classes."""
        return self.get_config()
        
    def _init_event_handler(self) -> None:
        """Initialize event handler for analysis tab."""
        self._event_handler = AnalysisTabEventHandler(self)
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.main = QHBoxLayout()
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
        
        # Subtraction options box
        self.sub_box = QGroupBox('Subtraction Options')
        self.sub_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.sub_box)
        self.sub_combo = QComboBox()
        self.sub_box.layout().addWidget(self.sub_combo)
        self.sub_stack = QStackedWidget()
        self.sub_box.layout().addWidget(self.sub_stack)
        
        # Result options box
        self.res_box = QGroupBox('Result Options')
        self.res_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.res_box)
        self.res_combo = QComboBox()
        self.res_box.layout().addWidget(self.res_combo)
        self.res_stack = QStackedWidget()
        self.res_box.layout().addWidget(self.res_stack)
        
        # Right side - plots
        self.right = QVBoxLayout()
        self.main.addLayout(self.right)
        
        # Initialize plots (including regions needed by analysis classes) - MUST come before analysis options
        self._init_plots()
        
        # Initialize analysis options after plots/regions are ready
        self._init_baseline_options()
        self._init_subtraction_options()
        self._init_result_options()
        
        # Connect combo boxes
        self.base_combo.currentIndexChanged.connect(self.change_base)
        self.sub_combo.currentIndexChanged.connect(self.change_sub)
        self.res_combo.currentIndexChanged.connect(self.change_res)
        
        # Initialize default selections
        self._init_defaults()
    
    def _init_baseline_options(self):
        """Initialize baseline analysis options."""
        # Create instances of existing analysis classes, adapted for event bus
        self.base_opts = [
            StandardBase(self),
            PolyFitBase(self), 
            CircuitBase(self),
            NoBase(self)
        ]
        
        # Add baseline analysis methods
        for opt in self.base_opts:
            self.base_combo.addItem(opt.name)
            self.base_stack.addWidget(opt)
    
    def _init_subtraction_options(self):
        """Initialize subtraction options."""
        # Create instances of existing subtraction classes
        self.sub_opts = [
            PolyFitSub(self),
            NoFitSub(self)
        ]
        
        # Add subtraction methods
        for opt in self.sub_opts:
            self.sub_combo.addItem(opt.name)
            self.sub_stack.addWidget(opt)
    
    def _init_result_options(self):
        """Initialize result options."""
        # Create instances of existing result classes
        self.res_opts = [
            SumAllRes(self),
            SumRangeRes(self),
            PeakHeightRes(self),
            FitPeakRes(self),
            FitPeakRes2(self), 
            FitDeuteron(self)
        ]
        
        # Add result methods
        for opt in self.res_opts:
            self.res_combo.addItem(opt.name)
            self.res_stack.addWidget(opt)
    
    def _init_plots(self):
        """Initialize plot widgets."""
        # Analysis plots widget
        self.plots_widget = pg.GraphicsLayoutWidget()
        self.right.addWidget(self.plots_widget)
        
        # Create plots
        self.raw_plot_item = self.plots_widget.addPlot(title="Raw Signal")
        self.raw_plot = self.raw_plot_item.plot(pen=self.base_pen)
        
        self.plots_widget.nextRow()
        self.base_plot_item = self.plots_widget.addPlot(title="Baseline")
        self.base_plot = self.base_plot_item.plot(pen=self.base2_pen)
        
        self.plots_widget.nextRow()
        self.basesub_plot_item = self.plots_widget.addPlot(title="Baseline Subtracted")
        self.basesub_plot = self.basesub_plot_item.plot(pen=self.base3_pen)
        
        self.plots_widget.nextRow()
        self.sub_plot_item = self.plots_widget.addPlot(title="Subtraction")
        self.sub_plot = self.sub_plot_item.plot(pen=self.sub_pen)
        self.fit_plot = self.sub_plot_item.plot(pen=self.sub2_pen)
        
        self.plots_widget.nextRow()
        self.fitsub_plot_item = self.plots_widget.addPlot(title="Fit Subtracted")
        self.fitsub_plot = self.fitsub_plot_item.plot(pen=self.sub3_pen)
        
        self.plots_widget.nextRow()
        self.res_plot_item = self.plots_widget.addPlot(title="Result")
        self.res_plot = self.res_plot_item.plot(pen=self.res_pen)
        self.unc_plot = self.res_plot_item.plot(pen=self.res2_pen)
        
        # Add regions that analysis classes expect
        self.base_region1 = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 180, 0, 0))
        self.base_region2 = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 180, 0, 0))
        self.sub_region1 = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 0, 180, 0))
        self.sub_region2 = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 0, 180, 0))
        self.res_region = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 180, 0, 0))
        
        # Add regions to appropriate plots
        self.basesub_plot_item.addItem(self.base_region1)
        self.basesub_plot_item.addItem(self.base_region2)
        self.sub_plot_item.addItem(self.sub_region1)
        self.sub_plot_item.addItem(self.sub_region2)
        self.res_plot_item.addItem(self.res_region)
    
    def _init_defaults(self):
        """Initialize default selections from config."""
        config = self.get_config()
        if config:
            self.base_combo.setCurrentIndex(config.settings['analysis']['base_def'])
            self.change_base(config.settings['analysis']['base_def'])
            
            self.sub_combo.setCurrentIndex(config.settings['analysis']['sub_def'])
            self.change_sub(config.settings['analysis']['sub_def'])
            
            self.res_combo.setCurrentIndex(config.settings['analysis']['res_def'])
            self.change_res(config.settings['analysis']['res_def'])
    
    def change_base(self, i):
        """Change baseline method."""
        self.base_stack.setCurrentIndex(i)
        
        # Set baseline method from existing analysis classes
        if i < len(self.base_opts):
            self.base_chosen = self.base_opts[i].result
            self.base_opts[i].switch_here()
        
        # Publish parameter change event
        self.publish_analysis_parameters_changed({
            "base_method": i,
            "source": "baseline_combo"
        })
        
        self.run_analysis()
    
    def change_sub(self, i):
        """Change subtraction method."""
        self.sub_stack.setCurrentIndex(i)
        
        # Set subtraction method from existing analysis classes
        if i < len(self.sub_opts):
            self.sub_chosen = self.sub_opts[i].result
            self.sub_opts[i].switch_here()
        
        # Publish parameter change event
        self.publish_analysis_parameters_changed({
            "sub_method": i,
            "source": "subtraction_combo"
        })
        
        self.run_analysis()
    
    def change_res(self, i):
        """Change result method."""
        self.res_stack.setCurrentIndex(i)
        
        # Set result method from existing analysis classes
        if i < len(self.res_opts):
            self.res_chosen = self.res_opts[i].result
            self.res_opts[i].switch_here()
        
        # Publish parameter change event
        self.publish_analysis_parameters_changed({
            "res_method": i,
            "source": "result_combo"
        })
        
        self.run_analysis()
    
    def run_analysis(self):
        """Run event signal analysis if needed and call for new plots if base and sub methods are chosen."""
        # Get previous event via event bus
        self.current_event = self.get_previous_event()
        
        if self.base_chosen and self.sub_chosen and self.res_chosen:
            # Always run analysis when parameters change (re-analysis allowed)
            if self.current_event:
                # Reset the analysis_completed flag to allow re-analysis
                self.current_event.analysis_completed = False
                self.current_event.signal_analysis(self.base_chosen, self.sub_chosen, self.res_chosen)
                self.current_event.analysis_completed = True
            self.update_event_plots()

    def update_event_plots(self):
        """Update analysis tab plots using event bus data."""
        # Get current and previous events via event bus
        current_event = self.get_current_event()
        self.current_event = self.get_previous_event()
        
        # Only update plots if analysis has been completed and data exists
        if (self.current_event and hasattr(self.current_event, 'basesweep') and 
            hasattr(self.current_event, 'basesub') and hasattr(self.current_event, 'fitsub') and
            hasattr(self.current_event, 'rescurve') and hasattr(self.current_event, 'fitcurve') and
            isinstance(self.current_event.basesweep, np.ndarray) and
            isinstance(self.current_event.basesub, np.ndarray)):
            
            # Update plots using event bus data instead of parent access
            if current_event and hasattr(current_event, 'scan'):
                freq_list = current_event.scan.freq_list
                phase_data = current_event.scan.phase
                
                self.raw_plot.setData(freq_list, phase_data - phase_data.max())
                self.base_plot.setData(freq_list, self.current_event.basesweep - self.current_event.basesweep.max())
                self.basesub_plot.setData(freq_list, self.current_event.basesub - self.current_event.basesub.max())
                self.sub_plot.setData(freq_list, self.current_event.basesub - self.current_event.basesub.max())
                self.fit_plot.setData(freq_list, self.current_event.fitcurve - self.current_event.basesub.max())
                self.fitsub_plot.setData(freq_list, self.current_event.fitsub)        
                self.unc_plot.setData(freq_list, self.current_event.fitsub)
                self.res_plot.setData(freq_list, self.current_event.rescurve)
    
    def update_plots(self):
        """Called by event handler when plots need updating."""
        self.update_event_plots()
    
    def refresh_analysis(self):
        """Called by event handler when analysis is completed."""
        self.update_event_plots()
    
    def on_event_updated(self, event_data):
        """Handle event updated from event bus."""
        self.current_event = event_data.get('previous_event')
        self.update_event_plots()
    
    def cleanup(self):
        """Clean up tab resources."""
        super().cleanup()


