#!/usr/bin/env python3
"""
Integration test for PyNMR Event Bus System

Tests the event bus architecture, service layer, and tab integration.
"""

import sys
import time
import logging
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PySide6.QtCore import QTimer

# Add the project root to path
sys.path.insert(0, '/home/jmaxwell/PycharmProjects/jlab_pynmr')

from core.event_bus import get_event_bus, cleanup_event_bus, EventType
from core.event_bus_service import initialize_pynmr_service, cleanup_pynmr_service, get_pynmr_service
from core.tab_base import EventBusTab, StatusMessageHandler
from config import Config


class TestEventListener:
    """Simple test listener for event bus testing."""
    
    def __init__(self, name):
        self.name = name
        self.received_events = []
        
        # Subscribe to events
        event_bus = get_event_bus()
        event_bus.subscribe(EventType.STATUS_MESSAGE, self.handle_status_message)
        event_bus.subscribe(EventType.CONFIG_CHANGED, self.handle_config_changed)
        event_bus.subscribe(EventType.RUN_TOGGLE, self.handle_run_toggle)
    
    def handle_status_message(self, event_data):
        """Handle status messages."""
        message = event_data.get('message', '')
        print(f"{self.name} received status: {message}")
        self.received_events.append(('status', message))
    
    def handle_config_changed(self, event_data):
        """Handle config changes."""
        print(f"{self.name} received config change from {event_data.source}")
        self.received_events.append(('config', event_data.source))
    
    def handle_run_toggle(self, event_data):
        """Handle run toggle."""
        print(f"{self.name} received run toggle from {event_data.source}")
        self.received_events.append(('run_toggle', event_data.source))


class TestTab(EventBusTab):
    """Test tab using event bus integration."""
    
    def __init__(self):
        super().__init__("test_tab")
        
        # Create simple UI
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)
        
        # Buttons to test event publishing
        self.status_button = QPushButton("Send Status Message")
        self.status_button.clicked.connect(self.send_status_message)
        layout.addWidget(self.status_button)
        
        self.config_button = QPushButton("Change Config")
        self.config_button.clicked.connect(self.change_config)
        layout.addWidget(self.config_button)
        
        self.run_button = QPushButton("Toggle Run")
        self.run_button.clicked.connect(self.toggle_run)
        layout.addWidget(self.run_button)
        
        # Event counter
        self.event_count = 0
        self.event_label = QLabel("Events sent: 0")
        layout.addWidget(self.event_label)
    
    def send_status_message(self):
        """Send a test status message."""
        self.event_count += 1
        message = f"Test status message #{self.event_count}"
        self.publish_status_message(message)
        self.event_label.setText(f"Events sent: {self.event_count}")
        print(f"TestTab published status: {message}")
    
    def change_config(self):
        """Send a test config change."""
        self.event_count += 1
        self.publish_config_change({
            "test_setting": f"value_{self.event_count}",
            "timestamp": time.time()
        })
        self.event_label.setText(f"Events sent: {self.event_count}")
        print(f"TestTab published config change #{self.event_count}")
    
    def toggle_run(self):
        """Send a test run toggle."""
        self.event_count += 1
        self.request_run_toggle()
        self.event_label.setText(f"Events sent: {self.event_count}")
        print(f"TestTab published run toggle #{self.event_count}")


class EventBusTestWindow(QMainWindow):
    """Main test window for event bus system."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyNMR Event Bus Test")
        self.setGeometry(100, 100, 600, 400)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Add title
        title = QLabel("PyNMR Event Bus Integration Test")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Add test tab
        self.test_tab = TestTab()
        layout.addWidget(self.test_tab)
        
        # Initialize event bus system
        self.init_event_bus_system()
        
        # Create test listeners
        self.listener1 = TestEventListener("Listener1")
        self.listener2 = TestEventListener("Listener2")
        
        # Set up status message handler for status bar
        self.status_handler = StatusMessageHandler(self.statusBar())
        
        # Set up automatic testing
        self.setup_automatic_tests()
        
        print("Event Bus Test Window initialized")
        print("Event bus listeners:", get_event_bus().get_listener_count())
    
    def init_event_bus_system(self):
        """Initialize the event bus system."""
        try:
            # Create a minimal config for testing
            test_channel_dict = {
                'name': 'test_channel',
                'sweep_file': '/tmp/test_sweep.txt',
                'cent_freq': 100.0,
                'mod_freq': 1000.0
            }
            
            test_settings = {
                'event_dir': '/tmp',
                'daq_type': 'test',
                'steps': 100,
                'analysis': {
                    'base_def': 0,
                    'sub_def': 0, 
                    'res_def': 0,
                    'wings': [0.1, 0.3, 0.7, 0.9]
                }
            }
            
            # Create a temporary sweep file
            import os
            os.makedirs('/tmp', exist_ok=True)
            with open('/tmp/test_sweep.txt', 'w') as f:
                f.write('90.0\n95.0\n100.0\n105.0\n110.0\n')
            
            config = Config(test_channel_dict, test_settings)
            
            # Initialize service
            service = initialize_pynmr_service(config)
            print(f"PyNMR Service initialized: {service}")
            
        except Exception as e:
            print(f"Error initializing event bus system: {e}")
            import traceback
            traceback.print_exc()
    
    def setup_automatic_tests(self):
        """Set up automatic tests to run periodically."""
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self.run_automatic_test)
        self.test_count = 0
        
        # Start timer after 2 seconds, then every 3 seconds
        QTimer.singleShot(2000, lambda: self.test_timer.start(3000))
    
    def run_automatic_test(self):
        """Run an automatic test."""
        self.test_count += 1
        
        if self.test_count <= 3:
            # Test different event types
            if self.test_count == 1:
                self.test_tab.send_status_message()
            elif self.test_count == 2:
                self.test_tab.change_config()
            elif self.test_count == 3:
                self.test_tab.toggle_run()
        else:
            # Stop automatic tests
            self.test_timer.stop()
            self.show_test_results()
    
    def show_test_results(self):
        """Show test results."""
        print("\n=== Test Results ===")
        print(f"Listener1 received {len(self.listener1.received_events)} events:")
        for event_type, data in self.listener1.received_events:
            print(f"  {event_type}: {data}")
        
        print(f"Listener2 received {len(self.listener2.received_events)} events:")
        for event_type, data in self.listener2.received_events:
            print(f"  {event_type}: {data}")
        
        # Test service state
        service = get_pynmr_service()
        if service:
            print(f"Service config available: {service.get_current_config() is not None}")
            print(f"Service running state: {service.running}")
        
        print("=== Test Complete ===\n")
    
    def closeEvent(self, event):
        """Clean up on window close."""
        print("Cleaning up event bus system...")
        
        # Clean up service and event bus
        cleanup_pynmr_service()
        cleanup_event_bus()
        
        super().closeEvent(event)


def main():
    """Run the event bus integration test."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Starting PyNMR Event Bus Integration Test...")
    
    app = QApplication(sys.argv)
    
    # Create and show test window
    window = EventBusTestWindow()
    window.show()
    
    print("Test window created. Event bus system should be operational.")
    print("The window will automatically run tests and show results.")
    print("You can also manually click buttons to test event publishing.")
    
    # Run the application
    exit_code = app.exec()
    
    print(f"Application exited with code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())