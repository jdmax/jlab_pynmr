"""Analysis thread and related functionality for PyNMR"""

from PySide6.QtCore import QThread, Signal


class AnalThread(QThread):
    """Thread class for analysis. Calls for epics reads and writes once done.
    
    Args:
        parent: Event object
        base_method: Method for baseline subtraction
        sub_method: Method for fit subtraction  
        res_method: Method for result calculation
    """
    
    reply = Signal(tuple)  # reply signal
    finished = Signal()    # finished signal
    
    def __init__(self, parent, base_method, sub_method, res_method):
        QThread.__init__(self)
        self.parent = parent  # event object
        self.base_method = base_method
        self.sub_method = sub_method
        self.res_method = res_method
                
    def __del__(self):
        self.wait()
        
    def run(self):
        """Main analysis loop."""
        self.parent.basesweep, self.parent.basesub = self.base_method(self.parent)        
        self.parent.fitcurve, self.parent.fitsub = self.sub_method(self.parent)
        self.parent.rescurve, self.parent.area, self.parent.pol = self.res_method(self.parent) 
        
        self.parent.parent.epics_update(self.parent)
        self.finished.emit()