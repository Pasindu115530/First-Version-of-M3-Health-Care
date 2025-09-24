"""
Video processing thread for Safe Warner
"""
import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

class VideoThread(QThread):
    """Thread for handling video processing"""
    frame_signal = pyqtSignal(np.ndarray)
    results_signal = pyqtSignal(dict)
    
    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor
        self.running = False
        self.cap = None
        
    def run(self):
        """Main video processing loop"""
        self.cap = cv2.VideoCapture(0)
        
        if not self.cap.isOpened():
            print("Error: Could not open camera")
            return
            
        self.running = True
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
                
            # Process frame
            results = self.monitor.process_frame(frame)
            
            # Draw overlay
            frame_with_overlay = self.monitor.draw_overlay(frame.copy(), results)
            
            # Emit signals
            self.frame_signal.emit(frame_with_overlay)
            self.results_signal.emit(results)
            
            # Small delay to prevent overwhelming the system
            self.msleep(30)
            
    def stop(self):
        """Stop the video thread"""
        self.running = False
        if self.cap:
            self.cap.release()
        self.wait()