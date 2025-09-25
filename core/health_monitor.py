"""
Core health monitoring functionality for Safe Warner
"""
import cv2
import time
import numpy as np
from datetime import datetime
import json
import os
from utils.notifications import fast_notify
from collections import deque
import warnings

from utils.constants import *
from utils.voice import voice

# Handle optional MediaPipe dependency
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("Warning: mediapipe not available. Some features will be disabled.")
    # Create mock classes for MediaPipe
    class MockMediaPipe:
        class solutions:
            class face_mesh:
                class FaceMesh:
                    def __init__(self, *args, **kwargs): pass
                    def process(self, image): return type('obj', (object,), {'multi_face_landmarks': None})()
            class pose:
                class Pose:
                    def __init__(self, *args, **kwargs): pass
                    def process(self, image): return type('obj', (object,), {'pose_landmarks': None})()
            drawing_utils = type('obj', (object,), {})()
            drawing_styles = type('obj', (object,), {})()
    
    mp = MockMediaPipe()

class HealthMonitor:
    def __init__(self, auto_mode=False):
        # Initialize MediaPipe solutions only if available
        if MEDIAPIPE_AVAILABLE:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.mp_pose = mp.solutions.pose
            self.mp_drawing = mp.solutions.drawing_utils
            self.mp_drawing_styles = mp.solutions.drawing_styles
            
            # Models
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            
            self.pose = self.mp_pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        else:
            self.face_mesh = None
            self.pose = None
            print("MediaPipe not available - camera features disabled")
        
        # Mode settings
        self.auto_mode = auto_mode
        self.auto_mode_interval = AUTO_MODE_INTERVAL
        
        # Eye landmarks
        self.LEFT_EYE_LANDMARKS = LEFT_EYE_LANDMARKS
        self.RIGHT_EYE_LANDMARKS = RIGHT_EYE_LANDMARKS
        
        # Pose landmarks
        self.NOSE_TIP = NOSE_TIP
        self.LEFT_SHOULDER = LEFT_SHOULDER
        self.RIGHT_SHOULDER = RIGHT_SHOULDER
        self.LEFT_EAR = LEFT_EAR
        self.RIGHT_EAR = RIGHT_EAR
        
        # Thresholds
        self.EAR_THRESHOLD = EAR_THRESHOLD
        self.PROXIMITY_THRESHOLD = PROXIMITY_THRESHOLD
        self.POSTURE_TILT_THRESHOLD = POSTURE_TILT_THRESHOLD
        self.SLOUCH_THRESHOLD = SLOUCH_THRESHOLD
        self.GAZE_THRESHOLD = GAZE_THRESHOLD
        
        # Timing parameters
        self.BLINK_WINDOW = BLINK_WINDOW
        self.SCREEN_TIME_BREAK = SCREEN_TIME_BREAK
        self.NOTIFICATION_COOLDOWN = NOTIFICATION_COOLDOWN
        self.EYE_EXERCISE_DURATION = EYE_EXERCISE_DURATION
        
        # Data tracking
        self.blink_timestamps = deque(maxlen=100)
        self.session_start = time.time()
        self.last_break_time = time.time()
        self.last_notification = {}
        self.alert_stats = {
            'proximity': 0,
            'posture': 0,
            'blink_rate': 0,
            'screen_time': 0,
            'system_health': 0,
            'eye_exercise': 0
        }
        
        # Eye exercise state machine
        self.eye_exercise_active = False
        self.eye_exercise_start_time = 0
        self.time_left = 15.0
        self.exercise_done = False
        self.current_phase = "right"
        self.countdown_active = False
        self.last_detection = "center"
        self.phase_start_time = 0
        self.paused_time_left = 15.0
        
        # Auto-mode tracking
        self.auto_mode_last_check = time.time()
        self.auto_mode_camera_active = False
        
        # Session logging
        self.session_data = {
            'start_time': datetime.now().isoformat(),
            'alerts': [],
            'eye_exercises': [],
            'mode': 'auto' if auto_mode else 'manual'
        }
        
        # Initialize psutil_available attribute
        self.psutil_available = False
        
        # Try to import psutil and set the flag
        try:
            import psutil
            self.psutil = psutil
            self.psutil_available = True
        except ImportError:
            print("psutil not available. System monitoring will be limited.")
            self.psutil_available = False
        
        # MediaPipe availability flag
        self.mediapipe_available = MEDIAPIPE_AVAILABLE
        
        # Other existing initialization code...
        self.performance_warnings = []
        self.last_check_time = time.time()
        self.check_interval = 30  # Check every 30 seconds

    def is_camera_available(self):
        """Check if camera functionality is available"""
        return self.mediapipe_available

    def set_auto_mode(self, enabled):
        """Set automatic mode on/off"""
        self.auto_mode = enabled
        self.session_data['mode'] = 'auto' if enabled else 'manual'
        
    def should_check_auto_mode(self):
        """Check if it's time to perform auto-mode check"""
        if not self.auto_mode:
            return False
            
        current_time = time.time()
        return current_time - self.auto_mode_last_check >= self.auto_mode_interval

    def detect_gaze_direction(self, face_landmarks, image_width, image_height):
        """Detect if user is looking left, right, or center"""
        if not self.mediapipe_available:
            return 'center'
        
        try:
            # Use relative position of iris landmarks to detect gaze
            left_eye_inner = face_landmarks[133]
            left_eye_outer = face_landmarks[33]
            right_eye_inner = face_landmarks[362]
            right_eye_outer = face_landmarks[263]
            
            left_eye_center_x = (left_eye_inner.x + left_eye_outer.x) / 2
            right_eye_center_x = (right_eye_inner.x + right_eye_outer.x) / 2
            
            left_eye_width = abs(left_eye_outer.x - left_eye_inner.x)
            right_eye_width = abs(right_eye_outer.x - right_eye_inner.x)
            
            nose_tip = face_landmarks[1]
            
            left_eye_relative = (left_eye_center_x - nose_tip.x) / left_eye_width
            right_eye_relative = (right_eye_center_x - nose_tip.x) / right_eye_width
            
            gaze_direction = (left_eye_relative + right_eye_relative) / 2
            
            if gaze_direction > self.GAZE_THRESHOLD:
                return 'right'
            elif gaze_direction < -self.GAZE_THRESHOLD:
                return 'left'
            else:
                return 'center'
                
        except Exception as e:
            print(f"Gaze detection error: {e}")
            return 'center'

    def start_eye_exercise(self):
        """Start the 15-second eye exercise routine"""
        self.eye_exercise_active = True
        self.eye_exercise_start_time = time.time()
        self.time_left = 15.0
        self.exercise_done = False
        self.current_phase = "right"
        self.countdown_active = False
        self.phase_start_time = time.time()
        self.paused_time_left = 15.0
        
        print("=== EYE EXERCISE STARTED ===")
        print("Please look to the RIGHT side for 15 seconds")
        # Voice guidance
        voice.speak("Eye exercise starting. Please look to the right for fifteen seconds.")
        
        # Send initial notification
        self.send_notification(
            "👀 Eye Exercise Time!",
            "Please look to the RIGHT side for 15 seconds",
            'eye_exercise'
        )

    def update_eye_exercise(self, detection):
        """Update the eye exercise state based on current gaze direction"""
        if not self.eye_exercise_active or self.exercise_done:
            return
            
        current_time = time.time()
        
        # Step 1: Watch Right
        if self.current_phase == "right":
            if detection == "right":
                if not self.countdown_active:
                    # Start countdown for right phase
                    self.countdown_active = True
                    self.phase_start_time = current_time
                    self.time_left = self.paused_time_left
                    print("✓ Correct! Looking right detected. Starting countdown...")
                
                # Update countdown
                elapsed = current_time - self.phase_start_time
                self.time_left = max(0, self.paused_time_left - elapsed)
                
                # Check if right phase is complete
                if self.time_left <= 0:
                    print("=== RIGHT SIDE COMPLETE ===")
                    print("Now please look to the LEFT side")
                    # Voice guidance
                    voice.speak("Good. Now look to the left for fifteen seconds.")
                    self.current_phase = "left"
                    self.countdown_active = False
                    self.paused_time_left = 15.0
                    self.time_left = 15.0
                    
                    self.send_notification(
                        "👀 Good! Now look LEFT",
                        "Please look to the LEFT side for 15 seconds",
                        'eye_exercise'
                    )
            else:
                # User is not looking right
                if self.countdown_active:
                    # Pause the countdown
                    self.countdown_active = False
                    self.paused_time_left = self.time_left
                    print("⚠️  Please maintain looking RIGHT. Timer paused.")
                    # Voice guidance
                    voice.speak("Please keep looking right to continue.")
                    self.send_notification(
                        "👀 Keep Looking Right",
                        "Please maintain your gaze to the RIGHT side to continue the exercise",
                        'eye_exercise'
                    )
                else:
                    # Still waiting for user to look right
                    if self.paused_time_left < 15.0:
                        print(f"→ Timer paused at {self.paused_time_left:.1f}s. Look RIGHT to resume.")
                    else:
                        print("→ Waiting for you to look RIGHT...")
        
        # Step 2: Watch Left
        elif self.current_phase == "left":
            if detection == "left":
                if not self.countdown_active:
                    # Start countdown for left phase
                    self.countdown_active = True
                    self.phase_start_time = current_time
                    self.time_left = self.paused_time_left
                    print("✓ Correct! Looking left detected. Starting countdown...")
                
                # Update countdown
                elapsed = current_time - self.phase_start_time
                self.time_left = max(0, self.paused_time_left - elapsed)
                
                # Check if left phase is complete
                if self.time_left <= 0:
                    # Exercise complete
                    self.eye_exercise_active = False
                    self.exercise_done = True
                    total_duration = current_time - self.eye_exercise_start_time
                    
                    print(f"=== EYE EXERCISE COMPLETED in {total_duration:.1f} seconds ===")
                    # Voice guidance
                    voice.speak("Exercise complete. Great job.")
                    
                    self.send_notification(
                        "✅ Exercise Complete!",
                        "Great job! Your eye exercise is complete.",
                        'eye_exercise'
                    )
                    
                    # Log the exercise
                    self.session_data['eye_exercises'].append({
                        'timestamp': datetime.now().isoformat(),
                        'duration': total_duration,
                        'success': True
                    })
                    
                    # Reset auto-mode timer after exercise completion
                    if self.auto_mode:
                        self.auto_mode_last_check = time.time()
            else:
                # User is not looking left
                if self.countdown_active:
                    # Pause the countdown
                    self.countdown_active = False
                    self.paused_time_left = self.time_left
                    print("⚠️  Please maintain looking LEFT. Timer paused.")
                    # Voice guidance
                    voice.speak("Please keep looking left to continue.")
                    self.send_notification(
                        "👀 Keep Looking Left",
                        "Please maintain your gaze to the LEFT side to continue the exercise",
                        'eye_exercise'
                    )
                else:
                    # Still waiting for user to look left
                    if self.paused_time_left < 15.0:
                        print(f"← Timer paused at {self.paused_time_left:.1f}s. Look LEFT to resume.")
                    else:
                        print("← Waiting for you to look LEFT...")

    def get_eye_exercise_status(self):
        """Get current status of eye exercise for display"""
        if not self.eye_exercise_active:
            return None
            
        status = {
            'phase': self.current_phase,
            'remaining_time': self.time_left,
            'total_elapsed': time.time() - self.eye_exercise_start_time,
            'paused': not self.countdown_active,
            'exercise_done': self.exercise_done
        }
        
        return status

    def eye_aspect_ratio(self, landmarks, image_width, image_height):
        """Calculate Eye Aspect Ratio for blink detection"""
        def calculate_ear(eye_landmarks):
            points = []
            for idx in eye_landmarks:
                landmark = landmarks[idx]
                x = landmark.x * image_width
                y = landmark.y * image_height
                points.append((x, y))
            
            vertical1 = np.linalg.norm(np.array(points[1]) - np.array(points[5]))
            vertical2 = np.linalg.norm(np.array(points[2]) - np.array(points[4]))
            horizontal = np.linalg.norm(np.array(points[0]) - np.array(points[3]))
            
            return (vertical1 + vertical2) / (2.0 * horizontal) if horizontal != 0 else 0.0
        
        left_ear = calculate_ear(self.LEFT_EYE_LANDMARKS)
        right_ear = calculate_ear(self.RIGHT_EYE_LANDMARKS)
        
        return (left_ear + right_ear) / 2.0

    def analyze_posture(self, pose_landmarks, image_width, image_height):
        """Analyze posture based on pose landmarks"""
        if not pose_landmarks or not self.mediapipe_available:
            return None
        
        landmarks = pose_landmarks.landmark
        
        try:
            # Calculate head tilt
            nose = landmarks[self.NOSE_TIP]
            left_ear = landmarks[self.LEFT_EAR]
            right_ear = landmarks[self.RIGHT_EAR]
            
            # Convert to pixel coordinates
            nose_x, nose_y = nose.x * image_width, nose.y * image_height
            left_ear_x, left_ear_y = left_ear.x * image_width, left_ear.y * image_height
            right_ear_x, right_ear_y = right_ear.x * image_width, right_ear.y * image_height
            
            # Calculate head tilt angle
            ear_center_x = (left_ear_x + right_ear_x) / 2
            ear_center_y = (left_ear_y + right_ear_y) / 2
            tilt_angle = np.degrees(np.arctan2(nose_x - ear_center_x, ear_center_y - nose_y))
            
            # Calculate slouching (shoulder-to-ear distance ratio)
            left_shoulder = landmarks[self.LEFT_SHOULDER]
            right_shoulder = landmarks[self.RIGHT_SHOULDER]
            
            left_ear_shoulder_dist = abs(left_ear.y - left_shoulder.y)
            right_ear_shoulder_dist = abs(right_ear.y - right_shoulder.y)
            slouch_ratio = (left_ear_shoulder_dist + right_ear_shoulder_dist) / 2
            
            return {
                'tilt_angle': tilt_angle,
                'slouch_ratio': slouch_ratio,
                'is_tilted': abs(tilt_angle) > self.POSTURE_TILT_THRESHOLD,
                'is_slouching': slouch_ratio > self.SLOUCH_THRESHOLD
            }
        except (IndexError, AttributeError) as e:
            print(f"Posture analysis error: {e}")
            return None

    def check_system_health(self):
        """Check system temperature and battery health"""
        system_info = {'available': False}
        
        if not self.psutil_available:
            system_info['message'] = 'psutil not available'
            return system_info
        
        try:
            # Check battery
            battery = self.psutil.sensors_battery()
            if battery:
                system_info['battery_percent'] = battery.percent
                system_info['power_plugged'] = battery.power_plugged
                system_info['battery_seconds_left'] = battery.secsleft
                
            # Check temperatures
            temps = self.psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        system_info[f'temp_{name}'] = entries[0].current
            else:
                system_info['temperature'] = 'unavailable'
                        
            system_info['available'] = True
                
        except Exception as e:
            system_info['error'] = str(e)
            print(f"System health monitoring error: {e}")
            
        return system_info

    def should_notify(self, alert_type):
        """Check if we should send notification (cooldown)"""
        current_time = time.time()
        last_time = self.last_notification.get(alert_type, 0)
        return current_time - last_time >= self.NOTIFICATION_COOLDOWN

    def send_notification(self, title, message, alert_type):
        """Send desktop notification"""
        if not self.should_notify(alert_type) and alert_type != 'eye_exercise':
            return
            
        try:
            delivered = fast_notify(title, message, duration=5, app_id="Safe Warner")
            self.last_notification[alert_type] = time.time()
            self.alert_stats[alert_type] += 1
            
            # Log the alert
            self.session_data['alerts'].append({
                'timestamp': datetime.now().isoformat(),
                'type': alert_type,
                'title': title,
                'message': message
            })
            print(f"Alert: {title} - {message}")
            
        except Exception as e:
            print(f"Notification error: {e}")

    def check_proximity(self, face_landmarks, image_height):
        """Check if face is too close to screen"""
        try:
            ys = [lm.y for lm in face_landmarks]
            bbox_height = max(ys) - min(ys)
            return bbox_height > self.PROXIMITY_THRESHOLD
        except Exception as e:
            print(f"Proximity check error: {e}")
            return False

    def check_blink_rate(self):
        """Check if blink rate is too low"""
        try:
            current_time = time.time()
            window_start = current_time - self.BLINK_WINDOW
            
            recent_blinks = sum(1 for t in self.blink_timestamps if t >= window_start)
            expected_min_blinks = (self.BLINK_WINDOW / 60) * 8
            
            return recent_blinks < expected_min_blinks
        except Exception as e:
            print(f"Blink rate check error: {e}")
            return False

    def check_screen_time(self):
        """Check if screen time break is needed"""
        current_time = time.time()
        return current_time - self.last_break_time > self.SCREEN_TIME_BREAK

    def process_frame(self, frame):
        """Process a single frame and check all health metrics"""
        results = {}
        h, w = frame.shape[:2]
        
        # Check if MediaPipe is available
        if not self.mediapipe_available:
            results['error'] = 'MediaPipe not available'
            return results
            
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Auto-mode logic
        if self.auto_mode and self.should_check_auto_mode():
            print("Auto-mode: Performing periodic health check...")
            self.auto_mode_last_check = time.time()
        
        # Face detection and analysis
        try:
            face_results = self.face_mesh.process(rgb_frame)
            if face_results.multi_face_landmarks:
                face_landmarks = face_results.multi_face_landmarks[0]
                
                # Gaze detection
                gaze_direction = self.detect_gaze_direction(face_landmarks.landmark, w, h)
                results['gaze_direction'] = gaze_direction
                self.last_detection = gaze_direction
                
                # Update eye exercise if active
                if self.eye_exercise_active:
                    self.update_eye_exercise(gaze_direction)
                
                # Proximity check
                results['proximity_alert'] = self.check_proximity(face_landmarks.landmark, h)
                if results['proximity_alert'] and self.should_notify('proximity') and not self.eye_exercise_active:
                    self.send_notification(
                        "📱 Move Back Slightly",
                        "You're sitting too close to the screen. Maintain 20-30cm distance.",
                        'proximity'
                    )
                
                # Blink detection
                ear = self.eye_aspect_ratio(face_landmarks.landmark, w, h)
                results['ear'] = ear
                
                if ear < self.EAR_THRESHOLD:
                    self.blink_timestamps.append(time.time())
                
                # Blink rate check
                results['low_blink_rate'] = self.check_blink_rate()
                if results['low_blink_rate'] and self.should_notify('blink_rate') and not self.eye_exercise_active:
                    self.send_notification(
                        "👁️ Rest Your Eyes",
                        "Your blink rate is low. Remember to blink regularly.",
                        'blink_rate'
                    )
                    
                # Auto-mode: Trigger exercise if issues detected (only after interval)
                if self.auto_mode and not self.eye_exercise_active and self.should_check_auto_mode():
                    if (results['proximity_alert'] or results['low_blink_rate'] or 
                        self.check_screen_time()):
                        print("Auto-mode: Health issues detected, starting exercise...")
                        self.start_eye_exercise()
                        self.last_break_time = time.time()
                        
        except Exception as e:
            print(f"Face processing error: {e}")
            results['face_error'] = str(e)
        
        # Pose detection and posture analysis
        try:
            pose_results = self.pose.process(rgb_frame)
            if pose_results.pose_landmarks:
                posture_data = self.analyze_posture(pose_results.pose_landmarks, w, h)
                results['posture'] = posture_data
                
                if posture_data and not self.eye_exercise_active:
                    if posture_data['is_tilted'] and self.should_notify('posture'):
                        self.send_notification(
                            "🎯 Adjust Your Posture",
                            "Your head is tilted. Keep your head straight and aligned.",
                            'posture'
                        )
                    
                    if posture_data['is_slouching'] and self.should_notify('posture'):
                        self.send_notification(
                            "💪 Sit Up Straight",
                            "You're slouching. Straighten your back and relax your shoulders.",
                            'posture'
                        )
                    
                    # Auto-mode: Trigger exercise for posture issues (only after interval)
                    if self.auto_mode and not self.eye_exercise_active and self.should_check_auto_mode():
                        if (posture_data['is_tilted'] or posture_data['is_slouching']):
                            print("Auto-mode: Posture issues detected, starting exercise...")
                            self.start_eye_exercise()
                            self.last_break_time = time.time()
                            
        except Exception as e:
            print(f"Pose processing error: {e}")
            results['pose_error'] = str(e)
        
        # Screen time check - trigger eye exercise
        results['screen_time_alert'] = self.check_screen_time()
        if results['screen_time_alert'] and self.should_notify('screen_time') and not self.eye_exercise_active:
            if not self.auto_mode:  # In manual mode, notify user
                self.send_notification(
                    "⏰ Time for a Break!",
                    "You've been using the screen for 20 minutes. Consider taking a break.",
                    'screen_time'
                )
            
        # System health check (run less frequently)
        if int(time.time()) % 10 == 0 and not self.eye_exercise_active:
            system_info = self.check_system_health()
            results['system_info'] = system_info
            
            if system_info.get('available'):
                for key, temp in system_info.items():
                    if 'temp' in key and temp > 70:
                        if self.should_notify('system_health'):
                            self.send_notification(
                                "🔥 System Running Hot",
                                f"High temperature detected ({temp}°C). Consider taking a break.",
                                'system_health'
                            )
        
        return results

    def draw_overlay(self, frame, results):
        """Draw analysis results on the frame"""
        h, w = frame.shape[:2]
        
        try:
            # Mode indicator
            mode_text = "AUTO MODE" if self.auto_mode else "MANUAL MODE"
            mode_color = (0, 255, 255) if self.auto_mode else (255, 255, 0)
            cv2.putText(frame, mode_text, (w - 150, h - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, mode_color, 2)
            
            # Auto-mode status
            if self.auto_mode and not self.eye_exercise_active:
                next_check = max(0, self.auto_mode_interval - (time.time() - self.auto_mode_last_check))
                check_min, check_sec = divmod(int(next_check), 60)
                auto_text = f"Next check: {check_min:02d}:{check_sec:02d}"
                cv2.putText(frame, auto_text, (10, h - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            # Eye exercise overlay (priority display)
            if self.eye_exercise_active:
                exercise_status = self.get_eye_exercise_status()
                if exercise_status:
                    # Semi-transparent background for exercise info
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (0, 0), (w, 150), (0, 0, 0), -1)
                    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
                    
                    phase_text = f"Look {exercise_status['phase'].upper()}"
                    time_text = f"Time left: {exercise_status['remaining_time']:.1f}s"
                    instruction = "Hold your gaze in the direction shown"
                    
                    if exercise_status.get('paused', False):
                        status_text = "PAUSED - Look in correct direction"
                        status_color = (0, 0, 255)  # Red for paused
                    else:
                        status_text = "ACTIVE"
                        status_color = (0, 255, 0)  # Green for active
                    
                    cv2.putText(frame, "=== EYE EXERCISE ===", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                    cv2.putText(frame, phase_text, (10, 70), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
                    cv2.putText(frame, time_text, (10, 110), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    cv2.putText(frame, instruction, (10, 140), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                    cv2.putText(frame, status_text, (w - 200, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
                    
                    # Draw arrow indicating direction
                    arrow_x = w // 2
                    if exercise_status['phase'] == 'right':
                        cv2.arrowedLine(frame, (arrow_x - 100, h//2), (arrow_x + 100, h//2), 
                                      status_color, 5, tipLength=0.3)
                        cv2.putText(frame, ">>> LOOK RIGHT >>>", (arrow_x - 150, h//2 - 20), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                    else:
                        cv2.arrowedLine(frame, (arrow_x + 100, h//2), (arrow_x - 100, h//2), 
                                      status_color, 5, tipLength=0.3)
                        cv2.putText(frame, "<<< LOOK LEFT <<<", (arrow_x - 150, h//2 - 20), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
            
            # Regular health status overlay (only if no active exercise)
            elif not self.eye_exercise_active:
                # Status text
                status_bg = frame.copy()
                cv2.rectangle(status_bg, (0, 0), (w, 200), (0, 0, 0), -1)
                cv2.addWeighted(status_bg, 0.6, frame, 0.4, 0, frame)

                status_lines = []
                status_colors = []

                ALERT_COLORS = {
                    'proximity': (0, 0, 255),      # Red for proximity alerts
                    'blink_rate': (0, 165, 255),   # Orange for blink rate
                    'screen_time': (255, 255, 0),  # Cyan for screen time
                    'posture': (255, 0, 255),      # Magenta for posture
                    'good': (0, 255, 0),           # Green for good status
                    'gaze': (255, 255, 255)        # White for gaze info
                }
                
                if results.get('proximity_alert'):
                    status_lines.append("⚠️ Too close to screen")
                    status_colors.append(ALERT_COLORS['proximity'])
                if results.get('low_blink_rate'):
                    status_lines.append("⚠️ Low blink rate")
                    status_colors.append(ALERT_COLORS['blink_rate'])
                if results.get('screen_time_alert'):
                    status_lines.append("⏰ Time for a break")
                    status_colors.append(ALERT_COLORS['screen_time'])
                if results.get('posture', {}).get('is_tilted'):
                    status_lines.append("⚠️ Head tilted")
                    status_colors.append(ALERT_COLORS['posture'])
                if results.get('posture', {}).get('is_slouching'):
                    status_lines.append("⚠️ Slouching detected")
                    status_colors.append(ALERT_COLORS['posture'])
                
                # Add gaze direction if available
                if 'gaze_direction' in results:
                    gaze_map = {'left': '👈 Looking LEFT', 'right': '👉 Looking RIGHT', 'center': '👀 Looking CENTER'}
                    status_lines.append(gaze_map.get(results['gaze_direction'], '👀 Gaze: Unknown'))
                    status_colors.append(ALERT_COLORS['gaze'])

                if not any([results.get('proximity_alert'), 
                       results.get('low_blink_rate'), 
                       results.get('screen_time_alert'),
                       results.get('posture', {}).get('is_tilted'),
                       results.get('posture', {}).get('is_slouching')]):
                    status_lines.append("✅ All good!")
                    status_colors.append(ALERT_COLORS['good'])   
                
                # Display status lines with their respective colors
                for i, (line, color) in enumerate(zip(status_lines, status_colors)):
                    cv2.putText(frame, line, (10, 30 + i*25), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    # Add colored dot before each alert
                    cv2.circle(frame, (5, 25 + i*25), 5, color, -1)
            
            # Add timestamp at bottom
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, timestamp, (10, h - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)   
            
            # Add colored border based on overall status
            border_color = (0, 255, 0)  # Green by default (good)
            border_thickness = 3
            if any([results.get('proximity_alert'), 
                results.get('low_blink_rate'),
                results.get('posture', {}).get('is_tilted'),
                results.get('posture', {}).get('is_slouching')]):
                border_color = (0, 0, 255)  # Red if any critical alerts
                border_thickness = 5
            elif results.get('screen_time_alert'):
                border_color = (255, 255, 0)  # Yellow for screen time warning
                border_thickness = 4   
            
            # Draw border around the frame
            cv2.rectangle(frame, (0, 0), (w-1, h-1), border_color, border_thickness) 
    
        except Exception as e:
            print(f"Overlay drawing error: {e}")
        
        return frame

    def save_session_data(self):
        """Save session data to JSON file"""
        try:
            filename = f"safe_warner_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(self.session_data, f, indent=2)
            print(f"Session data saved to {filename}")
            return filename
        except Exception as e:
            print(f"Error saving session data: {e}")
            return None

    def should_switch_to_background(self, results):
        """Determine if we can switch to background mode"""
        try:
            # Check if all conditions are good for background operation
            conditions = [
                not results.get('proximity_alert', True),  # Good distance
                not results.get('low_blink_rate', True),   # Good blink rate
                not self.eye_exercise_active,              # No active exercise
                not any([results.get('posture', {}).get('is_tilted', False),
                        results.get('posture', {}).get('is_slouching', False)]),  # Good posture
                time.time() - self.session_start > 60      # Minimum session time
            ]
        
            return all(conditions)
        except Exception as e:
            print(f"Background check error: {e}")
            return False