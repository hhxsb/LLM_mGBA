#!/usr/bin/env python3
"""
Screen capture implementation for external video capture.
"""

import time
import threading
from typing import Dict, List, Any, Optional, Tuple
import PIL.Image
import os
from .base_capture_system import BaseCaptureSystem, CaptureFrame, VideoSegment, CaptureSystemFactory

class ScreenCaptureSystem(BaseCaptureSystem):
    """Screen capture system using external screen recording."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.capture_method = config.get('screen_capture_method', 'auto')
        self.capture_region = config.get('capture_region', None)  # (x, y, width, height)
        self.recording_frames = []
        self.recording_thread = None
        self.recording_stop_event = None
        self.fps = config.get('capture_fps', 10)
        self._debug_logged = False
        
        # Try to import screen capture libraries
        self.pyautogui = None
        self.mss = None
        self.pillow_imagegrab = None
        
        self._initialize_capture_backends()
    
    def _initialize_capture_backends(self):
        """Initialize available capture backends."""
        # Try pyautogui
        try:
            import pyautogui
            self.pyautogui = pyautogui
            # Note: Logging is handled by the controller that creates this instance
        except ImportError:
            print("⚠️ PyAutoGUI not available (pip install pyautogui)")
        
        # Try mss (faster screen capture)
        try:
            import mss
            self.mss = mss
            print("✅ MSS screen capture available")
        except ImportError:
            print("⚠️ MSS not available (pip install mss)")
        
        # Try PIL ImageGrab (Windows/macOS)
        try:
            from PIL import ImageGrab
            self.pillow_imagegrab = ImageGrab
            print("✅ PIL ImageGrab screen capture available")
        except ImportError:
            print("⚠️ PIL ImageGrab not available")
    
    def initialize(self) -> bool:
        """Initialize the screen capture system."""
        if not self.is_available():
            print("❌ No screen capture backend available")
            return False
        
        # Determine best capture method
        if self.capture_method == 'auto':
            if self.mss:
                self.capture_method = 'mss'
            elif self.pillow_imagegrab:
                self.capture_method = 'imagegrab'
            elif self.pyautogui:
                self.capture_method = 'pyautogui'
        
        # Auto-detect mGBA window if no capture region specified
        if self.capture_region is None:
            self.capture_region = self._find_mgba_window()
            if self.capture_region:
                x, y, w, h = self.capture_region
                print(f"🎯 Found mGBA window at ({x}, {y}) size {w}x{h}")
                print(f"🔧 Setting capture region to: x={x}, y={y}, width={w}, height={h}")
            else:
                print("⚠️ mGBA window not found - capturing full screen")
        else:
            x, y, w, h = self.capture_region
            print(f"🔧 Using configured capture region: x={x}, y={y}, width={w}, height={h}")
        
        print(f"🎥 Screen capture initialized using {self.capture_method}")
        return True
    
    def _find_mgba_window(self) -> Optional[Tuple[int, int, int, int]]:
        """Find mGBA window and return its bounds (x, y, width, height)."""
        try:
            import subprocess
            import platform
            
            system = platform.system()
            
            if system == "Darwin":  # macOS
                # Use AppleScript to find mGBA window
                script = '''
                tell application "System Events"
                    try
                        set mgbaProcess to missing value
                        
                        -- Try multiple variations of the mGBA process name
                        set processNames to {"mGBA", "mgba", "mgba-qt", "mGBA-qt"}
                        repeat with processName in processNames
                            try
                                set mgbaProcess to first process whose name is processName
                                exit repeat
                            on error
                                -- Continue to next process name
                            end try
                        end repeat
                        
                        -- If still not found, try partial name matching
                        if mgbaProcess is missing value then
                            set allProcesses to processes
                            repeat with currentProcess in allProcesses
                                set processName to name of currentProcess
                                if processName contains "mGBA" or processName contains "mgba" then
                                    set mgbaProcess to currentProcess
                                    exit repeat
                                end if
                            end repeat
                        end if
                        
                        if mgbaProcess is missing value then
                            return "not_found"
                        end if
                        
                        -- Find the best game window
                        set mgbaWindows to windows of mgbaProcess
                        set mgbaWindow to missing value
                        set bestWindow to missing value
                        set bestScore to 0
                        
                        -- Score windows to find the most likely game window
                        repeat with currentWindow in mgbaWindows
                            set windowSize to size of currentWindow
                            set windowWidth to item 1 of windowSize
                            set windowHeight to item 2 of windowSize
                            set windowTitle to ""
                            
                            try
                                set windowTitle to title of currentWindow
                            on error
                                set windowTitle to ""
                            end try
                            
                            set score to 0
                            
                            -- Prefer windows with game-like aspect ratios (close to 4:3 or 16:10)
                            set aspectRatio to windowWidth / windowHeight
                            if aspectRatio > 1.2 and aspectRatio < 1.8 then
                                set score to score + 50
                            end if
                            
                            -- Prefer reasonably sized windows (not tiny, not huge)
                            if windowWidth > 300 and windowWidth < 1500 and windowHeight > 200 and windowHeight < 1200 then
                                set score to score + 30
                            end if
                            
                            -- Prefer windows with game-related titles
                            if windowTitle contains "Pokémon" or windowTitle contains "Pokemon" or windowTitle contains "Emerald" or windowTitle contains "Red" or windowTitle contains "Blue" then
                                set score to score + 40
                            end if
                            
                            -- Avoid very small windows (likely dialogs)
                            if windowWidth < 200 or windowHeight < 150 then
                                set score to score - 100
                            end if
                            
                            -- Avoid very large windows (likely fullscreen or desktop)
                            if windowWidth > 2000 or windowHeight > 1400 then
                                set score to score - 50
                            end if
                            
                            if score > bestScore then
                                set bestScore to score
                                set bestWindow to currentWindow
                            end if
                        end repeat
                        
                        -- Use best window or fallback to first window
                        if bestWindow is not missing value then
                            set mgbaWindow to bestWindow
                        else
                            set mgbaWindow to first window of mgbaProcess
                        end if
                        
                        set windowPosition to position of mgbaWindow
                        set windowSize to size of mgbaWindow
                        return (item 1 of windowPosition as string) & "," & (item 2 of windowPosition as string) & "," & (item 1 of windowSize as string) & "," & (item 2 of windowSize as string)
                    on error
                        return "not_found"
                    end try
                end tell
                '''
                result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
                print(f"🔍 AppleScript result: {result.stdout.strip()}")
                if result.returncode == 0 and result.stdout.strip() != "not_found":
                    parts = result.stdout.strip().split(',')
                    if len(parts) == 4:
                        x, y, w, h = map(int, parts)
                        print(f"🔍 Parsed window bounds: x={x}, y={y}, w={w}, h={h}")
                        return (x, y, w, h)
            
            elif system == "Linux":
                # Use xwininfo to find mGBA window
                try:
                    result = subprocess.run(['xwininfo', '-name', 'mGBA'], capture_output=True, text=True)
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        x = y = w = h = 0
                        for line in lines:
                            if 'Absolute upper-left X:' in line:
                                x = int(line.split(':')[1].strip())
                            elif 'Absolute upper-left Y:' in line:
                                y = int(line.split(':')[1].strip())
                            elif 'Width:' in line:
                                w = int(line.split(':')[1].strip())
                            elif 'Height:' in line:
                                h = int(line.split(':')[1].strip())
                        if w > 0 and h > 0:
                            return (x, y, w, h)
                except FileNotFoundError:
                    print("⚠️ xwininfo not available - install x11-utils package")
            
            elif system == "Windows":
                # Use pywin32 to find mGBA window
                try:
                    import win32gui
                    import win32con
                    
                    def enum_windows_callback(hwnd, windows):
                        if win32gui.IsWindowVisible(hwnd):
                            window_text = win32gui.GetWindowText(hwnd)
                            if 'mGBA' in window_text:
                                rect = win32gui.GetWindowRect(hwnd)
                                windows.append((rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]))
                        return True
                    
                    windows = []
                    win32gui.EnumWindows(enum_windows_callback, windows)
                    if windows:
                        return windows[0]  # Return first mGBA window found
                
                except ImportError:
                    print("⚠️ pywin32 not available - install pywin32 package")
        
        except Exception as e:
            print(f"⚠️ Error finding mGBA window: {e}")
        
        return None
    
    def cleanup(self):
        """Cleanup resources."""
        if self.is_recording:
            self.stop_recording()
    
    def is_available(self) -> bool:
        """Check if screen capture is available."""
        return any([self.pyautogui, self.mss, self.pillow_imagegrab])
    
    def capture_frame(self) -> Optional[CaptureFrame]:
        """Capture a single frame from the screen."""
        try:
            timestamp = time.time()
            
            if self.capture_method == 'mss' and self.mss:
                image = self._capture_with_mss()
            elif self.capture_method == 'imagegrab' and self.pillow_imagegrab:
                image = self._capture_with_imagegrab()
            elif self.capture_method == 'pyautogui' and self.pyautogui:
                image = self._capture_with_pyautogui()
            else:
                print(f"❌ Capture method {self.capture_method} not available")
                return None
            
            if image is None:
                return None
            
            self.capture_count += 1
            self.last_capture_time = timestamp
            
            return CaptureFrame(
                image=image,
                timestamp=timestamp,
                frame_number=self.capture_count,
                metadata={
                    'capture_method': self.capture_method,
                    'capture_region': self.capture_region
                }
            )
        
        except Exception as e:
            print(f"❌ Error capturing frame: {e}")
            return None
    
    def _capture_with_mss(self) -> Optional[PIL.Image.Image]:
        """Capture using MSS library."""
        with self.mss.mss() as sct:
            if self.capture_region:
                x, y, width, height = self.capture_region
                monitor = {"top": y, "left": x, "width": width, "height": height}
                # Debug: Log what region we're capturing
                if hasattr(self, '_debug_logged') and not self._debug_logged:
                    print(f"🔍 MSS capturing region: top={y}, left={x}, width={width}, height={height}")
                    self._debug_logged = True
            else:
                monitor = sct.monitors[1]  # Primary monitor
                if hasattr(self, '_debug_logged') and not self._debug_logged:
                    print(f"🔍 MSS capturing full monitor: {monitor}")
                    self._debug_logged = True
            
            screenshot = sct.grab(monitor)
            return PIL.Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
    
    def _capture_with_imagegrab(self) -> Optional[PIL.Image.Image]:
        """Capture using PIL ImageGrab."""
        if self.capture_region:
            x, y, width, height = self.capture_region
            bbox = (x, y, x + width, y + height)
            return self.pillow_imagegrab.grab(bbox)
        else:
            return self.pillow_imagegrab.grab()
    
    def _capture_with_pyautogui(self) -> Optional[PIL.Image.Image]:
        """Capture using PyAutoGUI."""
        if self.capture_region:
            x, y, width, height = self.capture_region
            return self.pyautogui.screenshot(region=(x, y, width, height))
        else:
            return self.pyautogui.screenshot()
    
    def start_recording(self) -> bool:
        """Start recording video frames."""
        if self.is_recording:
            print("⚠️ Already recording")
            return False
        
        if not self.is_available():
            print("❌ Screen capture not available")
            return False
        
        self.recording_frames = []
        self.recording_stop_event = threading.Event()
        self.is_recording = True
        
        # Start recording thread
        self.recording_thread = threading.Thread(target=self._recording_loop)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
        print(f"🎬 Started screen recording at {self.fps} FPS")
        return True
    
    def stop_recording(self) -> Optional[VideoSegment]:
        """Stop recording and return video segment."""
        if not self.is_recording:
            print("⚠️ Not currently recording")
            return None
        
        # Signal stop and wait for thread
        self.recording_stop_event.set()
        if self.recording_thread:
            self.recording_thread.join(timeout=2.0)
        
        self.is_recording = False
        
        if not self.recording_frames:
            print("⚠️ No frames captured during recording")
            return None
        
        # Create video segment
        start_time = self.recording_frames[0].timestamp
        end_time = self.recording_frames[-1].timestamp
        duration = end_time - start_time
        
        segment = VideoSegment(
            frames=self.recording_frames.copy(),
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            metadata={
                'capture_method': self.capture_method,
                'fps': self.fps,
                'frame_count': len(self.recording_frames)
            }
        )
        
        print(f"🎬 Stopped recording: {len(self.recording_frames)} frames, {duration:.2f}s")
        self.recording_frames = []
        
        return segment
    
    def _recording_loop(self):
        """Recording loop that runs in a separate thread."""
        frame_interval = 1.0 / self.fps
        next_capture_time = time.time()
        
        while not self.recording_stop_event.is_set():
            current_time = time.time()
            
            if current_time >= next_capture_time:
                frame = self.capture_frame()
                if frame:
                    self.recording_frames.append(frame)
                
                next_capture_time = current_time + frame_interval
            
            # Small sleep to prevent busy waiting
            sleep_time = max(0, next_capture_time - time.time())
            if sleep_time > 0:
                time.sleep(min(sleep_time, 0.01))  # Sleep at most 10ms

class EmulatorCaptureSystem(BaseCaptureSystem):
    """Emulator-based capture system (existing screenshot method)."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.screenshot_path = config.get('screenshot_path', 'data/screenshots/screenshot.png')
        self.socket_client = None
    
    def initialize(self) -> bool:
        """Initialize the emulator capture system."""
        return True
    
    def cleanup(self):
        """Cleanup resources."""
        pass
    
    def is_available(self) -> bool:
        """Check if emulator capture is available."""
        return True  # Always available as fallback
    
    def capture_frame(self) -> Optional[CaptureFrame]:
        """Capture a frame from the emulator screenshot."""
        if not os.path.exists(self.screenshot_path):
            return None
        
        try:
            timestamp = time.time()
            image = PIL.Image.open(self.screenshot_path)
            
            self.capture_count += 1
            self.last_capture_time = timestamp
            
            return CaptureFrame(
                image=image.copy(),  # Make a copy to avoid file locking issues
                timestamp=timestamp,
                frame_number=self.capture_count,
                metadata={
                    'capture_method': 'emulator_screenshot',
                    'source_path': self.screenshot_path
                }
            )
        
        except Exception as e:
            print(f"❌ Error loading emulator screenshot: {e}")
            return None
    
    def start_recording(self) -> bool:
        """Start recording (not applicable for emulator captures)."""
        print("⚠️ Emulator capture doesn't support continuous recording")
        return False
    
    def stop_recording(self) -> Optional[VideoSegment]:
        """Stop recording (not applicable for emulator captures)."""
        return None

# Register capture systems
CaptureSystemFactory.register_system('screen', ScreenCaptureSystem)
CaptureSystemFactory.register_system('emulator', EmulatorCaptureSystem)