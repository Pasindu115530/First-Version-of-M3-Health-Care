"""
Safe Warner - Main Entry Point
"""
import sys
import time
from gui.main_window import SafeWarnerGUI
from PyQt5.QtWidgets import QApplication

def main():
    # Check if running in auto-mode (system boot)
    auto_mode = "--auto-mode" in sys.argv
    minimal_mode = "--minimal" in sys.argv
    
    app = QApplication(sys.argv)
    app.setApplicationName("Safe Warner")
    
    # Create and show the main window
    window = SafeWarnerGUI()
    
    # If starting in auto-mode (system boot), enable special behavior
    if auto_mode:
        window.monitor.set_auto_mode(True)
        window.mode_toggle.setText("Switch to Manual Mode")
        window.mode_status.setText("Current Mode: AUTO")
        window.mode_status.setStyleSheet("color: green;")
        
        # Hide the window initially for system boot
        if minimal_mode:
            window.hide()  # Start hidden in system tray
        else:
            window.showMinimized()  # Start minimized
        
        # Auto-start camera and begin monitoring
        window.start_camera_auto_mode()
    else:
        # Normal manual startup
        window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()