#!/usr/bin/env python3
"""
Test script for PyNMR ThreadManager and BaseThread system.

This script creates test threads to verify the thread management system works correctly.
"""

import sys
import time
import random
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QObject
from core.thread_manager import BaseThread, ThreadManager, get_thread_manager


class TestThread(BaseThread):
    """Simple test thread for validation."""
    
    def __init__(self, name: str, duration: int = 3, emit_data: bool = True):
        super().__init__(name)
        self.duration = duration
        self.emit_data = emit_data
        self.step_count = 0
    
    def execute(self):
        """Test execution with periodic data emission."""
        steps = self.duration * 10  # 10 steps per second
        
        for i in range(steps):
            if self.should_stop():
                self._logger.info(f"Thread {self.thread_name} stopping early at step {i}")
                return
                
            # Simulate work
            time.sleep(0.1)
            self.step_count = i
            
            # Emit test data periodically
            if self.emit_data and i % 5 == 0:
                test_data = {
                    'thread': self.thread_name,
                    'step': i,
                    'progress': i / steps,
                    'random': random.random()
                }
                self.emit_reply(test_data)
        
        self._logger.info(f"Thread {self.thread_name} completed all {steps} steps")


class TestLongRunningThread(BaseThread):
    """Thread that runs indefinitely until stopped."""
    
    def execute(self):
        """Run until stopped."""
        counter = 0
        while not self.should_stop():
            time.sleep(0.5)
            counter += 1
            
            if counter % 10 == 0:
                self.emit_reply({'thread': self.thread_name, 'counter': counter})


class ThreadManagerTester(QObject):
    """Test coordinator for thread management system."""
    
    def __init__(self):
        super().__init__()
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.thread_manager = get_thread_manager()
        self.test_results = []
        
        # Connect to thread manager signals
        self.thread_manager.thread_started.connect(self.on_thread_started)
        self.thread_manager.thread_stopped.connect(self.on_thread_stopped)
        self.thread_manager.thread_error.connect(self.on_thread_error)
        
        # Timer for test progression
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self.run_next_test)
        self.current_test = 0
        self.tests = [
            self.test_basic_thread_lifecycle,
            self.test_multiple_threads,
            self.test_thread_stopping,
            self.test_long_running_thread,
            self.test_thread_status_monitoring,
            self.cleanup_and_finish
        ]
    
    def run_tests(self):
        """Start running all tests."""
        print("=== PyNMR ThreadManager Test Suite ===\n")
        self.test_timer.start(100)  # Start first test immediately
    
    def run_next_test(self):
        """Run the next test in sequence."""
        self.test_timer.stop()
        
        if self.current_test < len(self.tests):
            test_func = self.tests[self.current_test]
            print(f"Running test {self.current_test + 1}/{len(self.tests)}: {test_func.__name__}")
            test_func()
            self.current_test += 1
        else:
            self.app.quit()
    
    def schedule_next_test(self, delay_ms: int = 2000):
        """Schedule the next test after a delay."""
        self.test_timer.start(delay_ms)
    
    def test_basic_thread_lifecycle(self):
        """Test 1: Basic thread creation, start, and completion."""
        print("  Creating and starting a basic test thread...")
        
        thread = TestThread("test_basic", duration=2)
        thread.reply.connect(lambda data: print(f"    Received data: {data}"))
        thread.finished.connect(lambda: print("    Thread finished successfully"))
        
        success = self.thread_manager.register_thread(thread)
        if not success:
            print("    FAIL: Could not register thread")
            return
        
        success = self.thread_manager.start_thread("test_basic")
        if not success:
            print("    FAIL: Could not start thread")
            return
        
        print("    PASS: Thread started successfully")
        self.schedule_next_test(3000)  # Wait for thread to complete
    
    def test_multiple_threads(self):
        """Test 2: Multiple threads running concurrently."""
        print("  Creating and starting multiple threads...")
        
        thread_names = ["multi_1", "multi_2", "multi_3"]
        
        for name in thread_names:
            thread = TestThread(name, duration=2, emit_data=False)
            thread.finished.connect(lambda n=name: print(f"    Thread {n} finished"))
            
            self.thread_manager.register_thread(thread)
            self.thread_manager.start_thread(name)
        
        print("    PASS: Multiple threads started")
        self.schedule_next_test(3000)
    
    def test_thread_stopping(self):
        """Test 3: Thread stopping functionality."""
        print("  Testing thread stopping...")
        
        thread = TestLongRunningThread("stop_test")
        thread.reply.connect(lambda data: print(f"    Long running thread data: {data}"))
        
        self.thread_manager.register_thread(thread)
        self.thread_manager.start_thread("stop_test")
        
        # Schedule stop after 2 seconds
        QTimer.singleShot(2000, lambda: self.stop_test_thread("stop_test"))
        
        print("    PASS: Long running thread started, will stop in 2s")
        self.schedule_next_test(4000)
    
    def stop_test_thread(self, name: str):
        """Helper to stop a test thread."""
        print(f"    Stopping thread {name}...")
        success = self.thread_manager.stop_thread(name)
        if success:
            print(f"    PASS: Thread {name} stopped successfully")
        else:
            print(f"    FAIL: Could not stop thread {name}")
    
    def test_long_running_thread(self):
        """Test 4: Long running thread management."""
        print("  Testing long running thread...")
        
        thread = TestLongRunningThread("long_runner")
        self.thread_manager.register_thread(thread)
        self.thread_manager.start_thread("long_runner")
        
        print("    PASS: Long running thread started")
        self.schedule_next_test(1000)
    
    def test_thread_status_monitoring(self):
        """Test 5: Thread status monitoring."""
        print("  Testing thread status monitoring...")
        
        all_status = self.thread_manager.get_all_thread_status()
        print(f"    Current thread count: {len(all_status)}")
        
        for name, status in all_status.items():
            if status['exists']:
                print(f"    Thread '{name}': running={status['running']}, runtime={status['runtime']:.1f}s")
        
        print("    PASS: Status monitoring working")
        self.schedule_next_test(1000)
    
    def cleanup_and_finish(self):
        """Final test: Cleanup all threads."""
        print("  Cleaning up all threads...")
        
        success = self.thread_manager.stop_all_threads(timeout=3000)
        if success:
            print("    PASS: All threads stopped successfully")
        else:
            print("    WARN: Some threads may not have stopped gracefully")
        
        final_status = self.thread_manager.get_all_thread_status()
        running_count = sum(1 for status in final_status.values() if status.get('running', False))
        
        print(f"    Final running thread count: {running_count}")
        print("\n=== Test Suite Complete ===")
        
        # Schedule app quit
        QTimer.singleShot(1000, self.app.quit)
    
    def on_thread_started(self, name: str):
        """Handle thread started signal."""
        print(f"    Signal: Thread '{name}' started")
    
    def on_thread_stopped(self, name: str):
        """Handle thread stopped signal."""
        print(f"    Signal: Thread '{name}' stopped")
    
    def on_thread_error(self, name: str, error: str):
        """Handle thread error signal."""
        print(f"    ERROR: Thread '{name}' error: {error}")


def main():
    """Main test function."""
    try:
        tester = ThreadManagerTester()
        tester.run_tests()
        return tester.app.exec()
    except Exception as e:
        print(f"Test failed with exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())