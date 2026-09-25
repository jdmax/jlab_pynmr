"""
Centralized Event Bus System for PyNMR

Provides decoupled communication between GUI components and business logic
through a publish-subscribe event system.
"""

from abc import ABCMeta, abstractmethod
from typing import Dict, Any, Callable, List, Optional
from PySide6.QtCore import QObject, Signal
import logging
import time
from enum import Enum


class EventType(Enum):
    """Enumeration of all event types in the PyNMR system."""
    
    # Configuration Events
    CONFIG_CHANGED = "config_changed"
    CHANNEL_CHANGED = "channel_changed"
    
    # Event Data Events
    EVENT_STARTED = "event_started"
    EVENT_UPDATED = "event_updated"
    EVENT_FINISHED = "event_finished"
    
    # Baseline Events
    BASELINE_CHANGED = "baseline_changed"
    BASELINE_SELECTED = "baseline_selected"
    
    # Analysis Events
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_PARAMETERS_CHANGED = "analysis_parameters_changed"
    
    # Run Control Events
    RUN_STARTED = "run_started"
    RUN_STOPPED = "run_stopped"
    RUN_TOGGLE = "run_toggle"
    
    # Hardware Events
    DAQ_CONNECTED = "daq_connected"
    DAQ_DISCONNECTED = "daq_disconnected"
    TEMPERATURE_UPDATED = "temperature_updated"
    MAGNET_STATUS_CHANGED = "magnet_status_changed"
    MICROWAVE_STATUS_CHANGED = "microwave_status_changed"
    
    # GUI Events
    STATUS_MESSAGE = "status_message"
    TAB_CHANGED = "tab_changed"
    PLOT_UPDATE_REQUESTED = "plot_update_requested"
    PROGRESS_UPDATED = "progress_updated"
    
    # Tuning Events
    TUNE_STARTED = "tune_started"
    TUNE_STOPPED = "tune_stopped"
    TUNE_VALUES_CHANGED = "tune_values_changed"
    
    # History Events
    HISTORY_UPDATED = "history_updated"
    
    # File Events
    EVENTFILE_CHANGED = "eventfile_changed"
    SESSION_SAVED = "session_saved"
    SESSION_RESTORED = "session_restored"


class BusData:
    """Container for event data passed through the event bus."""
    
    def __init__(self, event_type: EventType, source: str, data: Dict[str, Any] = None):
        """
        Initialize bus event data.
        
        Args:
            event_type: Type of event
            source: Source component name that generated the event
            data: Optional data dictionary
        """
        self.event_type = event_type
        self.source = source
        self.data = data or {}
        self.timestamp = time.time()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get data value by key."""
        return self.data.get(key, default)
    
    def __str__(self) -> str:
        return f"BusData({self.event_type.value}, source={self.source}, data={self.data})"


class EventListener:
    """Base class for event listeners."""
    
    def __init__(self, name: str):
        self.name = name
        self._subscriptions: List[EventType] = []
    
    @abstractmethod
    def handle_event(self, event_data: BusData) -> None:
        """Handle incoming event."""
        pass
    
    def subscribe_to(self, event_types: List[EventType]) -> None:
        """Subscribe to specific event types."""
        self._subscriptions.extend(event_types)
    
    def is_subscribed_to(self, event_type: EventType) -> bool:
        """Check if subscribed to event type."""
        return event_type in self._subscriptions


class EventBus(QObject):
    """
    Centralized event bus for PyNMR application.
    
    Provides publish-subscribe mechanism for decoupled communication
    between GUI components and business logic.
    """
    
    # Qt signals for different event categories
    config_event = Signal(object)  # BusData
    data_event = Signal(object)    # BusData
    gui_event = Signal(object)     # BusData
    hardware_event = Signal(object) # BusData
    analysis_event = Signal(object) # BusData
    
    def __init__(self, parent: QObject = None):
        """Initialize event bus."""
        super().__init__(parent)
        self._listeners: Dict[str, EventListener] = {}
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._logger = logging.getLogger("PyNMR.EventBus")
        
        # Event type to signal mapping
        self._event_signals = {
            EventType.CONFIG_CHANGED: self.config_event,
            EventType.CHANNEL_CHANGED: self.config_event,
            
            EventType.EVENT_STARTED: self.data_event,
            EventType.EVENT_UPDATED: self.data_event,
            EventType.EVENT_FINISHED: self.data_event,
            EventType.BASELINE_CHANGED: self.data_event,
            EventType.BASELINE_SELECTED: self.data_event,
            EventType.HISTORY_UPDATED: self.data_event,
            
            EventType.ANALYSIS_STARTED: self.analysis_event,
            EventType.ANALYSIS_COMPLETED: self.analysis_event,
            EventType.ANALYSIS_PARAMETERS_CHANGED: self.analysis_event,
            
            EventType.STATUS_MESSAGE: self.gui_event,
            EventType.TAB_CHANGED: self.gui_event,
            EventType.PLOT_UPDATE_REQUESTED: self.gui_event,
            EventType.RUN_STARTED: self.gui_event,
            EventType.RUN_STOPPED: self.gui_event,
            EventType.RUN_TOGGLE: self.gui_event,
            
            EventType.DAQ_CONNECTED: self.hardware_event,
            EventType.DAQ_DISCONNECTED: self.hardware_event,
            EventType.TEMPERATURE_UPDATED: self.hardware_event,
            EventType.MAGNET_STATUS_CHANGED: self.hardware_event,
            EventType.MICROWAVE_STATUS_CHANGED: self.hardware_event,
            EventType.TUNE_STARTED: self.hardware_event,
            EventType.TUNE_STOPPED: self.hardware_event,
            EventType.TUNE_VALUES_CHANGED: self.hardware_event,
        }
    
    def register_listener(self, listener: EventListener) -> bool:
        """
        Register an event listener.
        
        Args:
            listener: EventListener instance
            
        Returns:
            bool: True if registered successfully
        """
        if listener.name in self._listeners:
            self._logger.warning(f"Listener {listener.name} already registered")
            return False
        
        self._listeners[listener.name] = listener
        self._logger.info(f"Registered event listener: {listener.name}")
        return True
    
    def unregister_listener(self, name: str) -> bool:
        """
        Unregister an event listener.
        
        Args:
            name: Listener name
            
        Returns:
            bool: True if unregistered successfully
        """
        if name in self._listeners:
            del self._listeners[name]
            self._logger.info(f"Unregistered event listener: {name}")
            return True
        return False
    
    def subscribe(self, event_type: EventType, handler: Callable[[BusData], None]) -> None:
        """
        Subscribe to an event type with a handler function.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Function to call when event occurs
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        self._logger.debug(f"Subscribed handler to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable[[BusData], None]) -> None:
        """
        Unsubscribe handler from event type.
        
        Args:
            event_type: Event type to unsubscribe from
            handler: Handler function to remove
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                self._logger.debug(f"Unsubscribed handler from {event_type.value}")
            except ValueError:
                self._logger.warning(f"Handler not found for {event_type.value}")
    
    def publish(self, event_type: EventType, source: str, data: Dict[str, Any] = None) -> None:
        """
        Publish an event to the bus.
        
        Args:
            event_type: Type of event
            source: Source component name
            data: Optional event data
        """
        event_data = BusData(event_type, source, data)
        
        # Log event publication
        self._logger.debug(f"Publishing event: {event_data}")
        
        # Notify registered listeners
        for listener in self._listeners.values():
            if listener.is_subscribed_to(event_type):
                try:
                    listener.handle_event(event_data)
                except Exception as e:
                    self._logger.error(f"Error in listener {listener.name}: {e}")
        
        # Call subscribed handlers
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(event_data)
                except Exception as e:
                    self._logger.error(f"Error in event handler: {e}")
        
        # Emit Qt signal for the event category
        if event_type in self._event_signals:
            try:
                self._event_signals[event_type].emit(event_data)
            except Exception as e:
                self._logger.error(f"Error emitting Qt signal: {e}")
    
    def get_listener_count(self) -> int:
        """Get number of registered listeners."""
        return len(self._listeners)
    
    def get_subscription_count(self, event_type: EventType) -> int:
        """Get number of subscriptions for an event type."""
        count = 0
        
        # Count listeners
        for listener in self._listeners.values():
            if listener.is_subscribed_to(event_type):
                count += 1
        
        # Count handlers
        if event_type in self._handlers:
            count += len(self._handlers[event_type])
        
        return count
    
    def cleanup(self) -> None:
        """Clean up event bus resources."""
        self._listeners.clear()
        self._handlers.clear()
        self._logger.info("Event bus cleanup completed")


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    Get the global event bus instance.
    
    Returns:
        EventBus: Global event bus
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def cleanup_event_bus() -> None:
    """Clean up the global event bus."""
    global _event_bus
    if _event_bus is not None:
        _event_bus.cleanup()
        _event_bus = None


# Convenience functions for common event publishing
def publish_config_changed(source: str, config_data: Dict[str, Any] = None) -> None:
    """Publish configuration changed event."""
    get_event_bus().publish(EventType.CONFIG_CHANGED, source, config_data)


def publish_status_message(source: str, message: str) -> None:
    """Publish status message event."""
    get_event_bus().publish(EventType.STATUS_MESSAGE, source, {"message": message})


def publish_event_updated(source: str, event_data: Dict[str, Any] = None) -> None:
    """Publish event updated event."""
    get_event_bus().publish(EventType.EVENT_UPDATED, source, event_data)


def publish_analysis_completed(source: str, analysis_data: Dict[str, Any] = None) -> None:
    """Publish analysis completed event."""
    get_event_bus().publish(EventType.ANALYSIS_COMPLETED, source, analysis_data)


def publish_run_toggle(source: str) -> None:
    """Publish run toggle event."""
    get_event_bus().publish(EventType.RUN_TOGGLE, source)