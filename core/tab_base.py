"""
Base class for PyNMR GUI tabs with event bus integration.

Provides standardized event bus access and common patterns for GUI tabs.
"""

from abc import abstractmethod
from typing import Dict, Any, Optional, List
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QObject

from .event_bus import get_event_bus, EventType, EventListener
from .event_bus_service import get_pynmr_service


class TabEventHandler(EventListener):
    """Event handler for GUI tabs that need event bus integration."""
    
    def __init__(self, tab_name: str, parent_tab: QWidget):
        """
        Initialize tab event handler.
        
        Args:
            tab_name: Name of the tab for identification
            parent_tab: The GUI tab widget
        """
        super().__init__(f"Tab_{tab_name}")
        self.tab_name = tab_name
        self.parent_tab = parent_tab
        self._event_bus = get_event_bus()
        
        # Register with event bus
        self._event_bus.register_listener(self)
    
    @abstractmethod
    def handle_event(self, event_data) -> None:
        """Handle incoming events. Override in subclass."""
        pass
    
    def publish_event(self, event_type: EventType, data: Dict[str, Any] = None) -> None:
        """Publish an event from this tab."""
        self._event_bus.publish(event_type, self.name, data)
    
    def cleanup(self) -> None:
        """Clean up event handler."""
        self._event_bus.unregister_listener(self.name)


class EventBusTab(QWidget):
    """
    Base class for PyNMR tabs that provides event bus integration.
    
    This replaces direct parent access with event bus communication.
    """
    
    def __init__(self, tab_name: str, parent=None):
        """
        Initialize event bus integrated tab.
        
        Args:
            tab_name: Name of the tab
            parent: Parent widget (for Qt hierarchy only)
        """
        super().__init__(parent)
        self.tab_name = tab_name
        self._service = get_pynmr_service()
        self._event_bus = get_event_bus()
        
        # Create event handler
        self._event_handler = None
        self._init_event_handler()
    
    def _init_event_handler(self) -> None:
        """Initialize event handler. Override in subclasses that need event handling."""
        pass
    
    # Convenience methods for common operations
    
    def get_config(self):
        """Get current configuration."""
        return self._service.get_current_config() if self._service else None
    
    def get_current_event(self):
        """Get current event."""
        return self._service.get_current_event() if self._service else None
    
    def get_previous_event(self):
        """Get previous event.""" 
        return self._service.get_previous_event() if self._service else None
    
    def get_baseline(self):
        """Get current baseline."""
        return self._service.get_baseline() if self._service else None
    
    def get_history(self):
        """Get history."""
        return self._service.get_history() if self._service else None
    
    def publish_status_message(self, message: str) -> None:
        """Publish status message."""
        self._event_bus.publish(EventType.STATUS_MESSAGE, self.tab_name, {
            "message": message
        })
    
    def publish_config_change(self, config_data: Dict[str, Any]) -> None:
        """Publish configuration change."""
        self._event_bus.publish(EventType.CONFIG_CHANGED, self.tab_name, config_data)
    
    def request_run_toggle(self) -> None:
        """Request run toggle."""
        self._event_bus.publish(EventType.RUN_TOGGLE, self.tab_name)
    
    def request_plot_update(self) -> None:
        """Request plot update."""
        self._event_bus.publish(EventType.PLOT_UPDATE_REQUESTED, self.tab_name)
    
    def publish_analysis_parameters_changed(self, params: Dict[str, Any]) -> None:
        """Publish analysis parameters change."""
        self._event_bus.publish(EventType.ANALYSIS_PARAMETERS_CHANGED, self.tab_name, params)
    
    def publish_baseline_selected(self, baseline_data: Dict[str, Any]) -> None:
        """Publish baseline selection."""
        self._event_bus.publish(EventType.BASELINE_SELECTED, self.tab_name, baseline_data)
    
    def publish_tune_values_changed(self, tune_data: Dict[str, Any]) -> None:
        """Publish tune values change."""
        self._event_bus.publish(EventType.TUNE_VALUES_CHANGED, self.tab_name, tune_data)
    
    def publish_hardware_status(self, status_data: Dict[str, Any]) -> None:
        """Publish hardware status update."""
        event_type = None
        if 'temperature' in status_data:
            event_type = EventType.TEMPERATURE_UPDATED
        elif 'magnet' in status_data:
            event_type = EventType.MAGNET_STATUS_CHANGED
        elif 'microwave' in status_data:
            event_type = EventType.MICROWAVE_STATUS_CHANGED
        
        if event_type:
            self._event_bus.publish(event_type, self.tab_name, status_data)
    
    def cleanup(self) -> None:
        """Clean up tab resources."""
        if self._event_handler:
            self._event_handler.cleanup()


class AnalysisTabEventHandler(TabEventHandler):
    """Event handler specifically for the analysis tab."""
    
    def __init__(self, parent_tab):
        super().__init__("analysis", parent_tab)
        
        # Subscribe to relevant events
        self.subscribe_to([
            EventType.EVENT_UPDATED,
            EventType.EVENT_FINISHED,
            EventType.ANALYSIS_COMPLETED,
            EventType.ANALYSIS_PARAMETERS_CHANGED,
        ])
    
    def handle_event(self, event_data) -> None:
        """Handle events for analysis tab."""
        if event_data.event_type == EventType.EVENT_UPDATED:
            # Update plots when event data changes
            if hasattr(self.parent_tab, 'update_plots'):
                self.parent_tab.update_plots()
        
        elif event_data.event_type == EventType.ANALYSIS_COMPLETED:
            # Refresh analysis results
            if hasattr(self.parent_tab, 'refresh_analysis'):
                self.parent_tab.refresh_analysis()
        
        elif event_data.event_type == EventType.EVENT_FINISHED:
            # Update plots when event finishes (equivalent to old direct call)
            if hasattr(self.parent_tab, 'update_event_plots'):
                self.parent_tab.update_event_plots()
        
        elif event_data.event_type == EventType.ANALYSIS_PARAMETERS_CHANGED:
            # Re-run analysis with new parameters
            if hasattr(self.parent_tab, 'run_analysis'):
                self.parent_tab.run_analysis()


class RunTabEventHandler(TabEventHandler):
    """Event handler specifically for the run tab."""
    
    def __init__(self, parent_tab):
        super().__init__("run", parent_tab)
        
        # Subscribe to relevant events
        self.subscribe_to([
            EventType.RUN_STARTED,
            EventType.RUN_STOPPED,
            EventType.EVENT_FINISHED,
        ])
    
    def handle_event(self, event_data) -> None:
        """Handle events for run tab."""
        if event_data.event_type == EventType.RUN_STARTED:
            # Update run controls
            if hasattr(self.parent_tab, 'on_run_started'):
                self.parent_tab.on_run_started()
        
        elif event_data.event_type == EventType.RUN_STOPPED:
            # Update run controls
            if hasattr(self.parent_tab, 'on_run_stopped'):
                self.parent_tab.on_run_stopped()
        
        elif event_data.event_type == EventType.EVENT_FINISHED:
            # Handle event completion
            if hasattr(self.parent_tab, 'on_event_finished'):
                self.parent_tab.on_event_finished()


class BaseTabEventHandler(TabEventHandler):
    """Event handler specifically for the baseline tab."""
    
    def __init__(self, parent_tab):
        super().__init__("baseline", parent_tab)
        
        # Subscribe to relevant events
        self.subscribe_to([
            EventType.BASELINE_CHANGED,
            EventType.EVENT_UPDATED,
        ])
    
    def handle_event(self, event_data) -> None:
        """Handle events for baseline tab."""
        if event_data.event_type == EventType.BASELINE_CHANGED:
            # Update baseline display
            if hasattr(self.parent_tab, 'on_baseline_changed'):
                self.parent_tab.on_baseline_changed(event_data.get('baseline'))
        
        elif event_data.event_type == EventType.EVENT_UPDATED:
            # Update baseline comparison
            if hasattr(self.parent_tab, 'update_baseline_comparison'):
                self.parent_tab.update_baseline_comparison()


class StatusMessageHandler:
    """Simple handler for status messages that updates status bar."""
    
    def __init__(self, status_bar):
        self.status_bar = status_bar
        event_bus = get_event_bus()
        event_bus.subscribe(EventType.STATUS_MESSAGE, self.handle_status_message)
    
    def handle_status_message(self, event_data) -> None:
        """Handle status message events."""
        message = event_data.get('message', '')
        if self.status_bar and message:
            self.status_bar.showMessage(message)