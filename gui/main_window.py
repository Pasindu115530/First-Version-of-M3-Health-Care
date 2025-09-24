"""
Main GUI Window for Safe Warner with Auto-Mode System Boot Support
"""
import time
from datetime import datetime
import cv2
import os
import json
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QWidget, QTextEdit, QGroupBox,
                             QProgressBar, QCheckBox, QMessageBox, QSystemTrayIcon, 
                             QMenu, QAction, QApplication)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QImage, QPixmap, QIcon

from gui.video_thread import VideoThread
from core.health_monitor import HealthMonitor
from core.auto_start import AutoStartManager

class SafeWarnerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.monitor = HealthMonitor()
        self.video_thread = None
        self.is_camera_active = False
        self.auto_start_manager = AutoStartManager()
        self.auto_mode_active = False
        self.background_mode = False
        self.tray_icon = None
        
        self.init_ui()
        self.setup_timers()
        self.setup_system_tray()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Safe Warner - Eye Health Monitor")
        self.setGeometry(100, 100, 900, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Safe Warner - Eye Health & Posture Monitor")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Mode control section (hidden in auto-mode)
        self.mode_group = QGroupBox("Operation Mode")
        mode_layout = QHBoxLayout(self.mode_group)
        
        # Mode toggle button
        self.mode_toggle = QPushButton("Switch to Auto Mode")
        self.mode_toggle.setCheckable(True)
        self.mode_toggle.clicked.connect(self.toggle_mode)
        mode_layout.addWidget(self.mode_toggle)
        
        # Mode status
        self.mode_status = QLabel("Current Mode: MANUAL")
        self.mode_status.setFont(QFont("Arial", 10, QFont.Bold))
        mode_layout.addWidget(self.mode_status)
        
        layout.addWidget(self.mode_group)
        
        # Settings section
        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout(settings_group)
        self.auto_start_checkbox = QCheckBox("Start automatically after system boot")
        self.auto_start_checkbox.stateChanged.connect(self.on_auto_start_changed)
        settings_layout.addWidget(self.auto_start_checkbox)
        layout.addWidget(settings_group)
        
        # Camera feed section
        camera_group = QGroupBox("Camera Feed")
        camera_layout = QVBoxLayout(camera_group)
        
        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setText("Camera feed will appear here")
        self.camera_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        camera_layout.addWidget(self.camera_label)
        
        # Camera controls
        camera_controls = QHBoxLayout()
        self.camera_button = QPushButton("Start Camera")
        self.camera_button.clicked.connect(self.toggle_camera)
        camera_controls.addWidget(self.camera_button)
        
        self.eye_exercise_button = QPushButton("Start Eye Exercise")
        self.eye_exercise_button.clicked.connect(self.start_eye_exercise)
        self.eye_exercise_button.setEnabled(False)
        camera_controls.addWidget(self.eye_exercise_button)
        
        camera_layout.addLayout(camera_controls)
        layout.addWidget(camera_group)
        
        # Status section
        status_group = QGroupBox("Status Information")
        status_layout = QVBoxLayout(status_group)
        
        # Exercise countdown
        self.exercise_status = QLabel("No active exercise")
        self.exercise_status.setFont(QFont("Arial", 12))
        status_layout.addWidget(self.exercise_status)
        
        # Countdown progress bar
        self.countdown_bar = QProgressBar()
        self.countdown_bar.setVisible(False)
        status_layout.addWidget(self.countdown_bar)
        
        # Health status display
        self.health_status = QTextEdit()
        self.health_status.setMaximumHeight(100)
        self.health_status.setReadOnly(True)
        status_layout.addWidget(self.health_status)
        
        layout.addWidget(status_group)
        
        # Auto-mode information
        auto_info_group = QGroupBox("Auto-Mode Information")
        auto_info_layout = QVBoxLayout(auto_info_group)
        
        self.auto_info = QLabel("Auto-mode: Will check health every 20 minutes")
        auto_info_layout.addWidget(self.auto_info)
        
        self.next_check_label = QLabel("Next check: --:--")
        auto_info_layout.addWidget(self.next_check_label)
        
        self.background_status = QLabel("Background: Inactive")
        self.background_status.setStyleSheet("color: orange; font-weight: bold;")
        auto_info_layout.addWidget(self.background_status)
        
        layout.addWidget(auto_info_group)
        
        # Statistics section
        stats_group = QGroupBox("Session Statistics")
        stats_layout = QHBoxLayout(stats_group)
        
        self.stats_label = QLabel("Alerts: 0 | Exercises: 0 | Session: 0m")
        stats_layout.addWidget(self.stats_label)
        
        # Save session button
        self.save_button = QPushButton("Save Session Data")
        self.save_button.clicked.connect(self.save_session_data)
        stats_layout.addWidget(self.save_button)
        
        # Show window button (for background mode)
        self.show_button = QPushButton("Show Window")
        self.show_button.clicked.connect(self.show_normal)
        self.show_button.setVisible(False)
        stats_layout.addWidget(self.show_button)
        
        layout.addWidget(stats_group)

        # Load settings and initialize auto-start checkbox
        self.settings_path = os.path.join(os.getcwd(), "safe_warner_settings.json")
        self.load_settings()

    def toggle_camera(self): 
        if not self.is_camera_active:
            self.start_camera()
        else:
            self.stop_camera()

    def update_camera_feed(self, frame):
        """Receive frame from thread and display in QLabel"""
        try:
            # Convert BGR (OpenCV) to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.camera_label.setPixmap(QPixmap.fromImage(qimg).scaled(
                self.camera_label.width(),
                self.camera_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        except Exception as e:
            print(f"Error updating camera feed: {e}")

    def update_health_data(self, results):
        """Handle results from video processing if needed for additional UI updates"""
        # For now, rely on update_status timer to refresh textual info
        pass

    def start_eye_exercise(self):
        """Start eye exercise via monitor"""
        try:
            self.monitor.start_eye_exercise()
            self.exercise_status.setText("Exercise: Starting...")
            self.countdown_bar.setVisible(True)
            self.countdown_bar.setValue(0)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not start eye exercise: {e}")

    def save_session_data(self):
        """Save session data and inform the user"""
        try:
            filename = self.monitor.save_session_data()
            if filename:
                QMessageBox.information(self, "Saved", f"Session data saved to {filename}")
            else:
                QMessageBox.warning(self, "Warning", "Failed to save session data.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving session data: {e}")

    def setup_system_tray(self):
        """Setup system tray icon for background operation"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            # Use a simple fallback icon to ensure it shows in packaged .exe
            self.tray_icon.setIcon(self.style().standardIcon(QApplication.style().SP_ComputerIcon))
            
            # Create tray menu
            tray_menu = QMenu()
            
            show_action = QAction("Show Window", self)
            show_action.triggered.connect(self.show_normal)
            tray_menu.addAction(show_action)
            
            exit_action = QAction("Exit", self)
            exit_action.triggered.connect(self.cleanup_and_exit)
            tray_menu.addAction(exit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)
            self.tray_icon.show()
            
    def tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_normal()
            
    def setup_timers(self):
        """Setup QTimers for periodic updates"""
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Update every second
        
        # Auto-mode background timer
        self.background_timer = QTimer()
        self.background_timer.timeout.connect(self.check_background_operation)
        self.background_timer.start(30000)  # Check every 30 seconds
        
    def start_camera_auto_mode(self):
        """Start camera in auto-mode (system boot)"""
        self.auto_mode_active = True
        self.mode_group.setVisible(False)  # Hide mode controls in auto-mode
        # Delay exercises until first interval completes
        self.monitor.auto_mode_last_check = time.time()
        self.start_camera()
        # Attempt early background switch after a short warm-up
        QTimer.singleShot(3000, self.try_background_after_start)
        
    def check_background_operation(self):
        """Check if we should switch to background mode"""
        if not self.auto_mode_active or not self.is_camera_active:
            return
            
        # Check if user distance is correct and no active alerts
        if self.monitor.auto_mode and not self.monitor.eye_exercise_active:
            # Simulate distance check (you'll need to implement actual distance logic)
            distance_ok = self.check_user_distance()
            
            if distance_ok and not self.has_active_alerts():
                # Switch to background mode after 30 seconds of good posture
                self.switch_to_background_mode()
                
    def check_user_distance(self):
        """Check if user is at correct distance (simplified implementation)"""
        # TODO: integrate real distance detection; for now allow quick backgrounding
        # Assume OK after short warm-up to let camera initialize and first frames process
        session_duration = time.time() - self.monitor.session_start
        return session_duration > 3
        
    def has_active_alerts(self):
        """Check if there are any active alerts"""
        # Implement based on your alert system
        return False
        
    def switch_to_background_mode(self):
        """Switch to background operation"""
        if self.background_mode:
            return
            
        self.background_mode = True
        self.stop_camera()
        self.hide()
        self.show_button.setVisible(True)
        self.background_status.setText("Background: Active")
        self.background_status.setStyleSheet("color: green; font-weight: bold;")
        
        # Schedule next check in 20 minutes
        self.schedule_next_check()
        
    def schedule_next_check(self):
        """Schedule next health check in 20 minutes"""
        QTimer.singleShot(int(self.monitor.auto_mode_interval * 1000), self.wake_up_for_check)
        
    def wake_up_for_check(self):
        """Wake up from background mode for health check"""
        if not self.auto_mode_active:
            return
            
        self.background_mode = False
        # Restore GUI properly
        try:
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        except Exception:
            pass
        self.show()
        self.raise_()
        self.activateWindow()
        # Ensure auto-mode allows immediate exercise upon wake
        self.monitor.auto_mode_last_check = time.time() - self.monitor.auto_mode_interval
        self.start_camera()
        self.background_status.setText("Background: Checking...")
        self.background_status.setStyleSheet("color: orange; font-weight: bold;")

        # After brief camera warm-up, check distance and start exercise
        QTimer.singleShot(2000, self.perform_wake_check_and_exercise)

    def perform_wake_check_and_exercise(self):
        """On wake: verify distance, then run exercise, then return to background"""
        try:
            distance_ok = self.check_user_distance()
            if distance_ok:
                self.monitor.start_eye_exercise()
            else:
                # If distance not OK, notify via status text; next timers will re-evaluate
                self.health_status.append("Distance not ideal. Adjust position.")
        except Exception as e:
            print(f"Wake check error: {e}")

    def try_background_after_start(self):
        """After startup, quickly check distance and hide to tray if OK"""
        if not self.auto_mode_active or not self.is_camera_active:
            return
        try:
            if self.check_user_distance() and not self.has_active_alerts():
                self.switch_to_background_mode()
        except Exception as e:
            print(f"Startup background check error: {e}")
        
    def show_normal(self):
        """Show window normally"""
        self.background_mode = False
        self.show()
        self.show_button.setVisible(False)
        self.background_status.setText("Background: Inactive")
        self.background_status.setStyleSheet("color: orange; font-weight: bold;")
        
    def toggle_mode(self):
        """Toggle between manual and auto modes"""
        if self.monitor.auto_mode:
            # Switch to manual mode
            self.monitor.set_auto_mode(False)
            self.auto_mode_active = False
            self.mode_toggle.setText("Switch to Auto Mode")
            self.mode_status.setText("Current Mode: MANUAL")
            self.mode_status.setStyleSheet("color: blue;")
            self.mode_group.setVisible(True)
            print("Switched to MANUAL mode")
        else:
            # Switch to auto mode
            self.monitor.set_auto_mode(True)
            self.auto_mode_active = True
            self.mode_toggle.setText("Switch to Manual Mode")
            self.mode_status.setText("Current Mode: AUTO")
            self.mode_status.setStyleSheet("color: green;")
            print("Switched to AUTO mode")
            
            # If camera is not running, start it for auto-mode
            if not self.is_camera_active:
                self.start_camera()

    def on_auto_start_changed(self, state):
        """Handle auto-start preference changes"""
        enabled = state == Qt.Checked
        try:
            self.auto_start_manager.set_auto_start(enabled)
            self.save_settings({'auto_start_enabled': enabled})
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update auto-start: {e}")
            # Revert checkbox to actual state
            try:
                current = self.auto_start_manager.is_auto_start_enabled()
                self.auto_start_checkbox.setChecked(current)
            except Exception:
                pass

    def load_settings(self):
        """Load saved settings and apply to UI"""
        data = {}
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r') as f:
                    data = json.load(f)
        except Exception:
            data = {}

        auto_start_enabled = data.get('auto_start_enabled')
        if auto_start_enabled is None:
            # Default unchecked on first launch
            auto_start_enabled = False
        self.auto_start_checkbox.setChecked(bool(auto_start_enabled))

    def save_settings(self, updates: dict):
        """Persist settings to disk"""
        data = {}
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r') as f:
                    data = json.load(f)
        except Exception:
            data = {}
        data.update(updates)
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")
    
    # ... (keep the existing methods for camera control, eye exercises, etc.)
    
    def start_camera(self):
        """Start the camera feed"""
        try:
            # Check if MediaPipe is available
            if not self.monitor.is_camera_available():
                QMessageBox.warning(self, "Dependency Missing", 
                                  "MediaPipe is not installed. Camera features are disabled.\n\n"
                                  "Please install it using: pip install mediapipe")
                return
                
            self.video_thread = VideoThread(self.monitor)
            self.video_thread.frame_signal.connect(self.update_camera_feed)
            self.video_thread.results_signal.connect(self.update_health_data)
            self.video_thread.start()
            
            self.is_camera_active = True
            self.camera_button.setText("Stop Camera")
            self.eye_exercise_button.setEnabled(True)
            print("Camera started")
            
        except Exception as e:
            print(f"Error starting camera: {e}")
            QMessageBox.critical(self, "Camera Error", f"Could not start camera: {e}")
    
    def stop_camera(self):
        """Stop the camera feed"""
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread = None
            
        self.is_camera_active = False
        self.camera_button.setText("Start Camera")
        self.eye_exercise_button.setEnabled(False)
        self.camera_label.setText("Camera feed stopped")
        print("Camera stopped")
    
    def update_status(self):
        """Update the status display"""
        try:
            # Update exercise status
            exercise_status = self.monitor.get_eye_exercise_status()
            if exercise_status:
                phase_text = exercise_status['phase'].upper()
                time_left = exercise_status['remaining_time']
                status_text = f"Exercise: Look {phase_text} - {time_left:.1f}s remaining"
                
                if exercise_status.get('paused', False):
                    status_text += " (PAUSED)"
                    self.exercise_status.setStyleSheet("color: red; font-weight: bold;")
                else:
                    self.exercise_status.setStyleSheet("color: orange; font-weight: bold;")
                
                self.exercise_status.setText(status_text)
                
                # Update progress bar
                self.countdown_bar.setVisible(True)
                progress = int((15 - time_left) / 15 * 100)
                self.countdown_bar.setValue(progress)
                
                # Auto-complete exercise handling
                if exercise_status.get('exercise_done', False) and self.auto_mode_active:
                    # Exercise completed, prepare to go back to background
                    QTimer.singleShot(5000, self.complete_exercise_cycle)  # Wait 5 seconds
            else:
                self.exercise_status.setText("No active exercise")
                self.exercise_status.setStyleSheet("color: black;")
                self.countdown_bar.setVisible(False)
            
            # Update health status
            status_text = ""
            if hasattr(self.monitor, 'last_detection'):
                gaze_map = {'left': '👈 Looking LEFT', 'right': '👉 Looking RIGHT', 'center': '👀 Looking CENTER'}
                status_text += f"Gaze: {gaze_map.get(self.monitor.last_detection, 'Unknown')}\n"
            
            # Add auto-mode info
            if self.monitor.auto_mode:
                next_check = max(0, self.monitor.auto_mode_interval - (time.time() - self.monitor.auto_mode_last_check))
                check_min, check_sec = divmod(int(next_check), 60)
                self.next_check_label.setText(f"Next check: {check_min:02d}:{check_sec:02d}")
                
                session_duration = int((time.time() - self.monitor.session_start) / 60)
                status_text += f"Auto-mode active | Session: {session_duration} min\n"
                
                if self.background_mode:
                    status_text += "🔵 Running in background\n"
            else:
                self.next_check_label.setText("Next check: --:--")
                session_duration = int((time.time() - self.monitor.session_start) / 60)
                status_text += f"Manual mode | Session: {session_duration} min\n"
            
            # Update statistics
            total_alerts = sum(self.monitor.alert_stats.values())
            exercise_count = len(self.monitor.session_data['eye_exercises'])
            self.stats_label.setText(f"Alerts: {total_alerts} | Exercises: {exercise_count} | Session: {session_duration}m")
            
            self.health_status.setText(status_text)
            
        except Exception as e:
            print(f"Error updating status: {e}")
    
    def complete_exercise_cycle(self):
        """Complete the exercise cycle and return to background"""
        if self.auto_mode_active and not self.background_mode:
            self.switch_to_background_mode()
    
    def cleanup_and_exit(self):
        """Cleanup and exit application"""
        if self.is_camera_active:
            self.stop_camera()
        
        # Save session data on close
        self.monitor.save_session_data()
        
        if self.tray_icon:
            self.tray_icon.hide()
            
        QApplication.quit()
    
    def closeEvent(self, event):
        """Handle application close"""
        if self.auto_mode_active and self.background_mode:
            # Minimize to tray instead of closing
            event.ignore()
            self.hide()
            if self.tray_icon:
                self.tray_icon.showMessage(
                    "Safe Warner",
                    "Application is still running in background",
                    QSystemTrayIcon.Information,
                    2000
                )
        else:
            self.cleanup_and_exit()
            event.accept()