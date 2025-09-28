"""
Event Bus Service Layer for PyNMR

Manages shared application state and business logic through the event bus,
providing a clean separation between GUI and business logic.
"""

import datetime
import time
import os
import logging
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject

from .event_bus import get_event_bus, EventType, EventListener
from .data_models import EventData, Baseline, History, HistPoint
from config import Config


class PyNMRService(EventListener):
    """
    Central service that manages PyNMR application state and business logic.
    
    This service coordinates between different components through the event bus,
    maintaining shared state without direct GUI coupling.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the PyNMR service.
        
        Args:
            config: Application configuration
        """
        super().__init__("PyNMRService")
        self._logger = logging.getLogger("PyNMR.Service")
        
        # Core application state
        self.config = config
        self.current_event: Optional[EventData] = None
        self.previous_event: Optional[EventData] = None
        self.baseline: Optional[Baseline] = None
        self.history = History()
        
        # Hardware state
        self.chassis_temp = 0.0
        self.shimA = 0.0
        self.shimB = 0.0
        self.shimC = 0.0
        self.shimD = 0.0
        
        # Analysis state
        self.analysis_in_progress = False
        
        # Running state
        self.running = False
        self.pending_next_run = False
        
        # File handles
        self.eventfile = None
        self.eventfile_start = None
        self.eventfile_lines = 0
        
        # Subscribe to relevant events
        self.subscribe_to([
            EventType.CONFIG_CHANGED,
            EventType.EVENT_STARTED,
            EventType.EVENT_FINISHED,
            EventType.ANALYSIS_COMPLETED,
            EventType.BASELINE_CHANGED,
            EventType.RUN_STARTED,
            EventType.RUN_STOPPED,
            EventType.TEMPERATURE_UPDATED,
        ])
        
        # Register with event bus
        event_bus = get_event_bus()
        event_bus.register_listener(self)
        
        self._logger.info("PyNMR Service initialized")
    
    def handle_event(self, event_data) -> None:
        """Handle incoming events from the event bus."""
        try:
            event_type = event_data.event_type
            
            if event_type == EventType.CONFIG_CHANGED:
                self._handle_config_changed(event_data)
            elif event_type == EventType.EVENT_STARTED:
                self._handle_event_started(event_data)
            elif event_type == EventType.EVENT_FINISHED:
                self._handle_event_finished(event_data)
            elif event_type == EventType.ANALYSIS_COMPLETED:
                self._handle_analysis_completed(event_data)
            elif event_type == EventType.BASELINE_CHANGED:
                self._handle_baseline_changed(event_data)
            elif event_type == EventType.RUN_STARTED:
                self._handle_run_started(event_data)
            elif event_type == EventType.RUN_STOPPED:
                self._handle_run_stopped(event_data)
            elif event_type == EventType.TEMPERATURE_UPDATED:
                self._handle_temperature_updated(event_data)
                
        except Exception as e:
            self._logger.error(f"Error handling event {event_data.event_type}: {e}")
    
    def _handle_config_changed(self, event_data) -> None:
        """Handle configuration change events."""
        config_data = event_data.get('config')
        if config_data:
            # Update configuration
            self._logger.info(f"Configuration changed by {event_data.source}")
            # Notify other components of config change
            event_bus = get_event_bus()
            event_bus.publish(EventType.CONFIG_CHANGED, "PyNMRService", {
                "config": self.config
            })
    
    def _handle_event_started(self, event_data) -> None:
        """Handle event start."""
        # Create new event
        self.previous_event = self.current_event
        self.current_event = EventData(self)
        
        self._logger.info("New event started")
        
        # Notify components
        event_bus = get_event_bus()
        event_bus.publish(EventType.EVENT_UPDATED, "PyNMRService", {
            "event": self.current_event,
            "previous_event": self.previous_event
        })
    
    def _handle_event_finished(self, event_data) -> None:
        """Handle event completion."""
        if self.current_event:
            # Add to history
            hist_point = HistPoint(self.current_event)
            self.history.add_hist(hist_point, self.eventfile)
            
            self._logger.info(f"Event completed: pol={self.current_event.pol:.6f}")
            
            # Notify components
            event_bus = get_event_bus()
            event_bus.publish(EventType.HISTORY_UPDATED, "PyNMRService", {
                "history_point": hist_point,
                "event": self.current_event
            })
    
    def _handle_analysis_completed(self, event_data) -> None:
        """Handle analysis completion."""
        self.analysis_in_progress = False
        
        # If there's a pending run, start it
        if self.pending_next_run:
            self.pending_next_run = False
            event_bus = get_event_bus()
            event_bus.publish(EventType.RUN_STARTED, "PyNMRService")
    
    def _handle_baseline_changed(self, event_data) -> None:
        """Handle baseline change."""
        baseline_data = event_data.get('baseline')
        if baseline_data:
            self.baseline = baseline_data
            self._logger.info("Baseline updated")
    
    def _handle_run_started(self, event_data) -> None:
        """Handle run start."""
        if self.analysis_in_progress:
            self.pending_next_run = True
            self._logger.info("Run requested while analysis in progress, will start after completion")
        else:
            self.running = True
            self._logger.info("Run started")
    
    def _handle_run_stopped(self, event_data) -> None:
        """Handle run stop."""
        self.running = False
        self.pending_next_run = False
        self._logger.info("Run stopped")
    
    def _handle_temperature_updated(self, event_data) -> None:
        """Handle temperature updates."""
        temp = event_data.get('temperature', 0)
        self.chassis_temp = temp
    
    def get_current_config(self) -> Config:
        """Get current configuration."""
        return self.config
    
    def get_current_event(self) -> Optional[EventData]:
        """Get current event."""
        return self.current_event
    
    def get_previous_event(self) -> Optional[EventData]:
        """Get previous event."""
        return self.previous_event
    
    def get_baseline(self) -> Optional[Baseline]:
        """Get current baseline."""
        return self.baseline
    
    def get_history(self) -> History:
        """Get history."""
        return self.history
    
    def set_baseline(self, baseline: Baseline) -> None:
        """Set new baseline."""
        self.baseline = baseline
        
        # Notify components
        event_bus = get_event_bus()
        event_bus.publish(EventType.BASELINE_CHANGED, "PyNMRService", {
            "baseline": baseline
        })
    
    def update_config(self, config_updates: Dict[str, Any]) -> None:
        """Update configuration."""
        # Apply updates to config
        for key, value in config_updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Notify components
        event_bus = get_event_bus()
        event_bus.publish(EventType.CONFIG_CHANGED, "PyNMRService", {
            "config": self.config,
            "updates": config_updates
        })
    
    def request_run_toggle(self) -> None:
        """Request run toggle."""
        event_bus = get_event_bus()
        if self.running:
            event_bus.publish(EventType.RUN_STOPPED, "PyNMRService")
        else:
            event_bus.publish(EventType.RUN_STARTED, "PyNMRService")
    
    def update_status_message(self, message: str) -> None:
        """Update status message."""
        event_bus = get_event_bus()
        event_bus.publish(EventType.STATUS_MESSAGE, "PyNMRService", {
            "message": message
        })
    
    def request_plot_update(self) -> None:
        """Request plot updates."""
        event_bus = get_event_bus()
        event_bus.publish(EventType.PLOT_UPDATE_REQUESTED, "PyNMRService", {
            "event": self.current_event,
            "previous_event": self.previous_event,
            "baseline": self.baseline
        })
    
    def start_analysis(self, base_method, sub_method, res_method) -> None:
        """Start analysis process."""
        if self.current_event and not self.analysis_in_progress:
            self.analysis_in_progress = True
            
            # Notify analysis start
            event_bus = get_event_bus()
            event_bus.publish(EventType.ANALYSIS_STARTED, "PyNMRService", {
                "event": self.current_event,
                "base_method": base_method,
                "sub_method": sub_method,
                "res_method": res_method
            })
    
    def cleanup(self) -> None:
        """Clean up service resources."""
        if self.eventfile:
            try:
                self.eventfile.close()
            except:
                pass
        
        self._logger.info("PyNMR Service cleanup completed")


# Global service instance
_service: Optional[PyNMRService] = None


def get_pynmr_service() -> Optional[PyNMRService]:
    """
    Get the global PyNMR service instance.
    
    Returns:
        PyNMRService or None if not initialized
    """
    return _service


def initialize_pynmr_service(config: Config) -> PyNMRService:
    """
    Initialize the global PyNMR service.
    
    Args:
        config: Application configuration
        
    Returns:
        PyNMRService: Initialized service
    """
    global _service
    if _service is None:
        _service = PyNMRService(config)
    return _service


def cleanup_pynmr_service() -> None:
    """Clean up the global PyNMR service."""
    global _service
    if _service is not None:
        _service.cleanup()
        _service = None