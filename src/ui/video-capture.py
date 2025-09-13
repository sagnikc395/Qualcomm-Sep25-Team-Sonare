import cv2
import numpy as np
import threading
import queue
import time
import json
import requests
import logging
import sys
import os
from datetime import datetime

# Add server directory to path to import server functions
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))
from main import add_keypoint_data, stats

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KeypointExtractor:
    """Handles keypoint extraction from video frames"""
    
    def __init__(self, detector_type='ORB'):
        self.detector_type = detector_type
        self.detector = self._create_detector()
    
    def _create_detector(self):
        """Create the keypoint detector based on type"""
        if self.detector_type == 'ORB':
            return cv2.ORB_create()
        elif self.detector_type == 'SIFT':
            return cv2.SIFT_create()
        elif self.detector_type == 'SURF':
            # Note: SURF requires opencv-contrib-python
            try:
                return cv2.xfeatures2d.SURF_create()
            except AttributeError:
                logger.warning("SURF not available, falling back to ORB")
                return cv2.ORB_create()
        else:
            raise ValueError(f"Unsupported detector type: {self.detector_type}")
    
    def extract_keypoints(self, frame):
        """Extract keypoints from a frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        keypoints, descriptors = self.detector.detectAndCompute(gray, None)
        
        # Convert keypoints to serializable format
        kp_data = []
        for kp in keypoints:
            kp_dict = {
                'x': float(kp.pt[0]),
                'y': float(kp.pt[1]),
                'size': float(kp.size),
                'angle': float(kp.angle),
                'response': float(kp.response),
                'octave': int(kp.octave),
                'class_id': int(kp.class_id)
            }
            kp_data.append(kp_dict)
        
        return kp_data, descriptors

class VideoCapture:
    """Video capture and keypoint processing"""
    
    def __init__(self, source=0, server_url="http://localhost:8000"):
        self.source = source
        self.server_url = server_url
        self.cap = None
        self.keypoint_extractor = KeypointExtractor()
        self.running = False
        self.frame_count = 0
        self.display_queue = queue.Queue(maxsize=5)
        
    def start_capture(self):
        """Initialize video capture"""
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video source: {self.source}")
        
        # Set capture properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        logger.info("Video capture initialized")
        
        # Notify server that processing is starting
        try:
            requests.post(f"{self.server_url}/start")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not notify server of start: {e}")
    
    def process_stream(self):
        """Main processing loop"""
        self.running = True
        stats['running'] = True
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Failed to read frame")
                break
            
            self.frame_count += 1
            timestamp = time.time()
            
            try:
                # Extract keypoints
                keypoints, descriptors = self.keypoint_extractor.extract_keypoints(frame)
                
                # Create data packet
                data_packet = {
                    'timestamp': timestamp,
                    'frame_id': self.frame_count,
                    'keypoints': keypoints,
                    'num_keypoints': len(keypoints),
                    'frame_shape': list(frame.shape)
                }
                
                # Send to server queue
                add_keypoint_data(data_packet)
                
                # Create display frame
                display_frame = self._draw_keypoints(frame, keypoints)
                
                # Add to display queue
                try:
                    self.display_queue.put_nowait(display_frame)
                except queue.Full:
                    try:
                        self.display_queue.get_nowait()
                        self.display_queue.put_nowait(display_frame)
                    except queue.Empty:
                        pass
                
                # Log progress every 100 frames
                if self.frame_count % 100 == 0:
                    logger.info(f"Processed {self.frame_count} frames")
                
            except Exception as e:
                logger.error(f"Error processing frame {self.frame_count}: {e}")
            
            # Small delay to prevent overwhelming the system
            time.sleep(0.001)
    
    def _draw_keypoints(self, frame, keypoints):
        """Draw keypoints on frame for visualization"""
        display_frame = frame.copy()
        
        # Draw keypoints
        for kp in keypoints:
            x, y = int(kp['x']), int(kp['y'])
            size = int(kp['size'])
            cv2.circle(display_frame, (x, y), max(2, size//4), (0, 255, 0), 2)
        
        # Add info overlay
        info_text = [
            f"Frame: {self.frame_count}",
            f"Keypoints: {len(keypoints)}",
            f"FPS: {self._calculate_fps():.1f}",
            "Press 'q' to quit, 's' for stats"
        ]
        
        y_offset = 30
        for text in info_text:
            cv2.putText(display_frame, text, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += 25
        
        return display_frame
    
    def _calculate_fps(self):
        """Calculate approximate FPS"""
        if hasattr(self, 'start_time') and self.frame_count > 0:
            elapsed = time.time() - self.start_time
            return self.frame_count / elapsed
        return 0.0
    
    def get_display_frame(self):
        """Get display frame from queue"""
        try:
            return self.display_queue.get_nowait()
        except queue.Empty:
            return None
    
    def stop(self):
        """Stop processing"""
        self.running = False
        stats['running'] = False
        
        if self.cap:
            self.cap.release()
        
        # Notify server that processing is stopping
        try:
            requests.post(f"{self.server_url}/stop")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not notify server of stop: {e}")

def display_video(video_capture):
    """Display video in OpenCV window"""
    while video_capture.running:
        frame = video_capture.get_display_frame()
        if frame is not None:
            cv2.imshow('Video Keypoint Capture', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                video_capture.stop()
                break
            elif key == ord('s'):
                # Print stats
                print(f"\n--- Stats ---")
                print(f"Frames processed: {video_capture.frame_count}")
                print(f"Current FPS: {video_capture._calculate_fps():.1f}")
                try:
                    response = requests.get(f"{video_capture.server_url}/stats")
                    if response.status_code == 200:
                        server_stats = response.json()
                        print(f"Server queue size: {server_stats['queue_size']}")
                except:
                    print("Could not get server stats")
                print("-------------\n")
        
        time.sleep(0.01)
    
    cv2.destroyAllWindows()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Video Keypoint Capture')
    parser.add_argument('--source', type=int, default=0, help='Video source (default: 0 for webcam)')
    parser.add_argument('--server', default='http://localhost:8000', help='Server URL')
    parser.add_argument('--detector', choices=['ORB', 'SIFT', 'SURF'], default='ORB', help='Keypoint detector type')
    
    args = parser.parse_args()
    
    try:
        # Test server connection
        try:
            response = requests.get(f"{args.server}/health", timeout=5)
            logger.info("Server connection established")
        except requests.exceptions.RequestException:
            logger.error(f"Cannot connect to server at {args.server}")
            logger.error("Make sure the server is running: cd server && just dev")
            return
        
        # Initialize video capture
        video_capture = VideoCapture(source=args.source, server_url=args.server)
        video_capture.keypoint_extractor = KeypointExtractor(args.detector)
        video_capture.start_capture()
        video_capture.start_time = time.time()
        
        # Start processing thread
        processing_thread = threading.Thread(target=video_capture.process_stream)
        processing_thread.daemon = True
        processing_thread.start()
        
        logger.info("Video capture started!")
        logger.info(f"Using {args.detector} detector")
        logger.info(f"Server: {args.server}")
        logger.info("Press 'q' in video window to quit, 's' for stats")
        
        # Start display (blocking)
        display_video(video_capture)
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        if 'video_capture' in locals():
            video_capture.stop()

if __name__ == "__main__":
    main()