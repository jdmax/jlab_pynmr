"""Analysis thread and related functionality for PyNMR"""

from PySide6.QtCore import QThread, Signal
from .thread_manager import BaseThread


class AnalThread(BaseThread):
    """Thread class for analysis. Calls for epics reads and writes once done.
    
    Args:
        parent: Event object
        base_method: Method for baseline subtraction
        sub_method: Method for fit subtraction  
        res_method: Method for result calculation
    """
    
    def __init__(self, parent, base_method, sub_method, res_method):
        # EventData is not a QObject, so pass None as Qt parent
        import time
        timestamp = int(time.time() * 1000000)  # microsecond precision
        super().__init__(name=f"analysis_{timestamp}", parent=None)
        self.event_parent = parent  # event object (not a QObject)
        self.base_method = base_method
        self.sub_method = sub_method
        self.res_method = res_method
                
    def execute(self):
        """Main analysis loop."""
        try:
            # Perform baseline subtraction
            self.event_parent.basesweep, self.event_parent.basesub = self.base_method(self.event_parent)
            
            # Check if we should stop before next step
            if self.should_stop():
                return
                
            # Perform fit subtraction  
            self.event_parent.fitcurve, self.event_parent.fitsub = self.sub_method(self.event_parent)
            
            # Check if we should stop before next step
            if self.should_stop():
                return
                
            # Calculate results
            self.event_parent.rescurve, self.event_parent.area, self.event_parent.pol = self.res_method(self.event_parent)
            
            # Check if we should stop before EPICS update
            if self.should_stop():
                return
                
            # Update EPICS
            self.event_parent.parent.epics_update(self.event_parent)
            
        except Exception as e:
            self._logger.error(f"Analysis failed: {e}")
            raise


# Legacy compatibility class - use AnalThread directly for new code
class LegacyAnalThread(QThread):
    """Legacy compatibility wrapper for old AnalThread interface."""
    
    reply = Signal(tuple)  # reply signal
    finished = Signal()    # finished signal
    
    def __init__(self, parent, base_method, sub_method, res_method):
        QThread.__init__(self)
        self.parent = parent  # event object
        self.base_method = base_method
        self.sub_method = sub_method
        self.res_method = res_method
                
    def __del__(self):
        try:
            if self.isRunning():
                self.quit()
                # Don't wait in destructor to avoid thread waiting on itself
        except RuntimeError:
            # C++ object already deleted, ignore
            pass
        
    def run(self):
        """Main analysis loop."""
        self.parent.basesweep, self.parent.basesub = self.base_method(self.parent)        
        self.parent.fitcurve, self.parent.fitsub = self.sub_method(self.parent)
        self.parent.rescurve, self.parent.area, self.parent.pol = self.res_method(self.parent) 
        
        self.parent.parent.epics_update(self.parent)
        self.finished.emit()