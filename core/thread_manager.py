"""
Thread Management System for PyNMR

Provides centralized thread management with consistent base classes and lifecycle management.
"""

from abc import ABCMeta, abstractmethod
from typing import Dict, Optional, Any, Callable
from PySide6.QtCore import QThread, Signal, QObject, QTimer
import logging
import threading
import time


class QThreadMeta(type(QThread), ABCMeta):
    """Metaclass to resolve conflict between QThread and ABC metaclasses."""
    pass


class BaseThread(QThread, metaclass=QThreadMeta):
    """
    Base class for all PyNMR threads with standardized signals and lifecycle management.
    
    Signals:
        reply: Emitted with data during thread execution
        finished: Emitted when thread completes
        error: Emitted when an error occurs
        status_changed: Emitted when thread status changes
    """
    
    # Standardized signals
    reply = Signal(object)  # Generic data signal
    finished = Signal()     # Thread completion signal  
    error = Signal(str)     # Error signal with message
    status_changed = Signal(str)  # Status update signal
    
    def __init__(self, name: str, parent: QObject = None, config: Optional[Any] = None):
        """
        Initialize base thread.
        
        Args:
            name: Unique name for this thread
            parent: Parent QObject
            config: Configuration object
        """
        super().__init__(parent)
        self.thread_name = name
        self.config = config
        self._is_stopping = False
        self._start_time = None
        self._logger = logging.getLogger(f"PyNMR.Thread.{name}")
        
    def start_thread(self) -> bool:
        """
        Start the thread with proper error handling.
        
        Returns:
            bool: True if thread started successfully
        """
        try:
            if self.isRunning():
                self._logger.warning(f"Thread {self.thread_name} is already running")
                return False
                
            self._is_stopping = False
            self._start_time = time.time()
            self.status_changed.emit("starting")
            self.start()
            self._logger.info(f"Thread {self.thread_name} started")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to start thread {self.thread_name}: {e}")
            self.error.emit(str(e))
            return False
    
    def stop_thread(self, timeout: int = 5000) -> bool:
        """
        Stop the thread gracefully with timeout.
        
        Args:
            timeout: Maximum time to wait for thread to stop (ms)
            
        Returns:
            bool: True if thread stopped successfully
        """
        if not self.isRunning():
            return True
            
        try:
            self._is_stopping = True
            self.status_changed.emit("stopping")
            
            # Request interruption and quit
            self.requestInterruption()
            self.quit()
            
            # Wait for thread to finish
            if self.wait(timeout):
                self._logger.info(f"Thread {self.thread_name} stopped gracefully")
                self.status_changed.emit("stopped")
                return True
            else:
                self._logger.warning(f"Thread {self.thread_name} did not stop within timeout, terminating")
                self.terminate()
                self.wait(1000)  # Give it a moment to clean up
                self.status_changed.emit("terminated")
                return False
                
        except Exception as e:
            self._logger.error(f"Error stopping thread {self.thread_name}: {e}")
            self.error.emit(str(e))
            return False
    
    def run(self):
        """
        Main thread execution. Calls setup, execute, and cleanup methods.
        """
        try:
            self.status_changed.emit("running")
            self.setup()
            self.execute()
            
        except Exception as e:
            self._logger.error(f"Error in thread {self.thread_name}: {e}")
            self.error.emit(str(e))
            
        finally:
            try:
                self.cleanup()
            except Exception as e:
                self._logger.error(f"Error in cleanup for thread {self.thread_name}: {e}")
            
            self.status_changed.emit("finished")
            self.finished.emit()
    
    def setup(self):
        """Override to perform thread initialization."""
        pass
    
    @abstractmethod 
    def execute(self):
        """Override to implement main thread logic."""
        pass
    
    def cleanup(self):
        """Override to perform thread cleanup."""
        pass
    
    def should_stop(self) -> bool:
        """
        Check if thread should stop execution.
        
        Returns:
            bool: True if thread should stop
        """
        return self._is_stopping or self.isInterruptionRequested()
    
    def emit_reply(self, data: Any):
        """
        Emit reply signal with data.
        
        Args:
            data: Data to emit
        """
        self.reply.emit(data)
    
    def get_runtime(self) -> float:
        """
        Get thread runtime in seconds.
        
        Returns:
            float: Runtime in seconds, 0 if not started
        """
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time
    
    def __del__(self):
        """Destructor ensuring thread is stopped."""
        try:
            if hasattr(self, '_is_stopping') and hasattr(self, 'isRunning'):
                if self.isRunning() and not self._is_stopping:
                    self.stop_thread(timeout=1000)
        except (RuntimeError, AttributeError):
            # C++ object already deleted or attributes missing, ignore
            pass


class ThreadManager(QObject):
    """
    Centralized manager for all PyNMR threads.
    
    Provides thread lifecycle management, monitoring, and cleanup.
    """
    
    # Signals for thread management events
    thread_started = Signal(str)  # thread_name
    thread_stopped = Signal(str)  # thread_name
    thread_error = Signal(str, str)  # thread_name, error_message
    
    def __init__(self, parent: QObject = None):
        """Initialize thread manager."""
        super().__init__(parent)
        self._threads: Dict[str, BaseThread] = {}
        self._thread_lock = threading.Lock()
        self._logger = logging.getLogger("PyNMR.ThreadManager")
        
        # Status monitoring timer
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._check_thread_status)
        self._status_timer.start(5000)  # Check every 5 seconds
    
    def register_thread(self, thread: BaseThread) -> bool:
        """
        Register a thread with the manager.
        
        Args:
            thread: Thread instance to register
            
        Returns:
            bool: True if registered successfully
        """
        with self._thread_lock:
            if thread.thread_name in self._threads:
                # Clean up old thread if it's not running
                old_thread = self._threads[thread.thread_name]
                if not old_thread.isRunning():
                    self._logger.info(f"Replacing finished thread: {thread.thread_name}")
                    try:
                        old_thread.deleteLater()
                    except:
                        pass
                    del self._threads[thread.thread_name]
                else:
                    self._logger.warning(f"Thread {thread.thread_name} already registered and running")
                    return False
            
            # Connect thread signals
            thread.error.connect(lambda msg: self.thread_error.emit(thread.thread_name, msg))
            thread.finished.connect(lambda: self._on_thread_finished(thread.thread_name))
            
            self._threads[thread.thread_name] = thread
            self._logger.info(f"Registered thread: {thread.thread_name}")
            return True
    
    def start_thread(self, name: str) -> bool:
        """
        Start a registered thread.
        
        Args:
            name: Name of thread to start
            
        Returns:
            bool: True if started successfully
        """
        with self._thread_lock:
            if name not in self._threads:
                self._logger.error(f"Thread {name} not registered")
                return False
            
            thread = self._threads[name]
            if thread.start_thread():
                self.thread_started.emit(name)
                return True
            return False
    
    def stop_thread(self, name: str, timeout: int = 5000) -> bool:
        """
        Stop a registered thread.
        
        Args:
            name: Name of thread to stop
            timeout: Maximum time to wait (ms)
            
        Returns:
            bool: True if stopped successfully
        """
        with self._thread_lock:
            if name not in self._threads:
                self._logger.error(f"Thread {name} not registered")
                return False
            
            thread = self._threads[name]
            if thread.stop_thread(timeout):
                self.thread_stopped.emit(name)
                return True
            return False
    
    def stop_all_threads(self, timeout: int = 5000) -> bool:
        """
        Stop all registered threads.
        
        Args:
            timeout: Maximum time to wait for each thread (ms)
            
        Returns:
            bool: True if all threads stopped successfully
        """
        success = True
        thread_names = list(self._threads.keys())
        
        for name in thread_names:
            if not self.stop_thread(name, timeout):
                success = False
                
        return success
    
    def get_thread(self, name: str) -> Optional[BaseThread]:
        """
        Get a registered thread by name.
        
        Args:
            name: Thread name
            
        Returns:
            BaseThread or None if not found
        """
        with self._thread_lock:
            return self._threads.get(name)
    
    def get_thread_status(self, name: str) -> Dict[str, Any]:
        """
        Get status information for a thread.
        
        Args:
            name: Thread name
            
        Returns:
            Dict with thread status information
        """
        with self._thread_lock:
            if name not in self._threads:
                return {"exists": False}
            
            thread = self._threads[name]
            return {
                "exists": True,
                "running": thread.isRunning(),
                "runtime": thread.get_runtime(),
                "name": thread.thread_name
            }
    
    def get_all_thread_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status for all registered threads.
        
        Returns:
            Dict mapping thread names to status info
        """
        with self._thread_lock:
            return {name: self.get_thread_status(name) for name in self._threads.keys()}
    
    def _on_thread_finished(self, name: str):
        """Handle thread finished signal."""
        self.thread_stopped.emit(name)
        self._logger.info(f"Thread {name} finished")
        
        # Disable auto-cleanup to prevent segfaults during rapid thread creation
        # Cleanup will happen during application shutdown or manual cleanup
        # try:
        #     from PySide6.QtCore import QTimer
        #     QTimer.singleShot(5000, lambda: self._cleanup_finished_thread(name))
        # except:
        #     pass
    
    def _cleanup_finished_thread(self, name: str):
        """Clean up a finished thread."""
        with self._thread_lock:
            if name in self._threads:
                thread = self._threads[name]
                if not thread.isRunning():
                    self._logger.debug(f"Auto-cleaning up finished thread: {name}")
                    try:
                        thread.deleteLater()
                    except:
                        pass
                    del self._threads[name]
    
    def _check_thread_status(self):
        """Periodic status check for all threads."""
        with self._thread_lock:
            for name, thread in self._threads.items():
                if thread.isRunning() and thread.get_runtime() > 3600:  # 1 hour
                    self._logger.warning(f"Thread {name} has been running for {thread.get_runtime():.1f} seconds")
    
    def cleanup(self):
        """Clean up all threads and resources."""
        try:
            self._status_timer.stop()
        except:
            pass  # Timer might already be stopped
            
        self.stop_all_threads(timeout=2000)
        
        # Give Qt event loop time to process deleteLater() calls
        try:
            from PySide6.QtCore import QApplication
            app = QApplication.instance()
            if app:
                app.processEvents()  # Process any pending deleteLater() calls
        except:
            pass
        
        with self._thread_lock:
            # Safely clean up thread references
            for name, thread in list(self._threads.items()):
                try:
                    if hasattr(thread, 'deleteLater'):
                        thread.deleteLater()
                except:
                    pass
            self._threads.clear()
        
        self._logger.info("Thread manager cleanup completed")
    
    def __del__(self):
        """Destructor ensuring cleanup."""
        try:
            self.cleanup()
        except:
            pass


# Global thread manager instance
_thread_manager: Optional[ThreadManager] = None


def get_thread_manager() -> ThreadManager:
    """
    Get the global thread manager instance.
    
    Returns:
        ThreadManager: Global thread manager
    """
    global _thread_manager
    if _thread_manager is None:
        _thread_manager = ThreadManager()
    return _thread_manager


def cleanup_thread_manager():
    """Clean up the global thread manager."""
    global _thread_manager
    if _thread_manager is not None:
        _thread_manager.cleanup()
        _thread_manager = None