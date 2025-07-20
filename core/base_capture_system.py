#!/usr/bin/env python3
"""
Abstract base classes for video/image capture systems.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
import PIL.Image
from dataclasses import dataclass
import time

@dataclass
class CaptureFrame:
    """Represents a captured frame with metadata."""
    image: PIL.Image.Image
    timestamp: float
    frame_number: int
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class VideoSegment:
    """Represents a video segment with multiple frames."""
    frames: List[CaptureFrame]
    start_time: float
    end_time: float
    duration: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def get_first_frame(self) -> Optional[CaptureFrame]:
        """Get the first frame of the segment."""
        return self.frames[0] if self.frames else None
    
    def get_last_frame(self) -> Optional[CaptureFrame]:
        """Get the last frame of the segment."""
        return self.frames[-1] if self.frames else None
    
    def get_frame_count(self) -> int:
        """Get the number of frames in the segment."""
        return len(self.frames)

class BaseCaptureSystem(ABC):
    """Abstract base class for capture systems."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_recording = False
        self.capture_count = 0
        self.last_capture_time = 0
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the capture system."""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Cleanup resources."""
        pass
    
    @abstractmethod
    def capture_frame(self) -> Optional[CaptureFrame]:
        """Capture a single frame."""
        pass
    
    @abstractmethod
    def start_recording(self) -> bool:
        """Start recording video."""
        pass
    
    @abstractmethod
    def stop_recording(self) -> Optional[VideoSegment]:
        """Stop recording and return video segment."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if capture system is available."""
        pass
    
    def get_capture_info(self) -> Dict[str, Any]:
        """Get information about the capture system."""
        return {
            "type": self.__class__.__name__,
            "is_recording": self.is_recording,
            "capture_count": self.capture_count,
            "last_capture_time": self.last_capture_time
        }
    
    def enhance_frame(self, frame: CaptureFrame, enhancement_config: Dict[str, Any] = None) -> CaptureFrame:
        """Enhance a captured frame for better AI processing."""
        if enhancement_config is None:
            enhancement_config = self.config.get('frame_enhancement', {})
        
        enhanced_image = self._apply_enhancements(frame.image, enhancement_config)
        
        return CaptureFrame(
            image=enhanced_image,
            timestamp=frame.timestamp,
            frame_number=frame.frame_number,
            metadata={**frame.metadata, 'enhanced': True}
        )
    
    def _apply_enhancements(self, image: PIL.Image.Image, config: Dict[str, Any]) -> PIL.Image.Image:
        """Apply image enhancements."""
        enhanced = image.copy()
        
        # Scale image
        scale_factor = config.get('scale_factor', 3)
        if scale_factor != 1:
            new_width = int(enhanced.width * scale_factor)
            new_height = int(enhanced.height * scale_factor)
            enhanced = enhanced.resize((new_width, new_height), PIL.Image.LANCZOS)
        
        # Apply enhancements
        from PIL import ImageEnhance
        
        # Contrast
        contrast_factor = config.get('contrast', 1.5)
        if contrast_factor != 1.0:
            enhancer = ImageEnhance.Contrast(enhanced)
            enhanced = enhancer.enhance(contrast_factor)
        
        # Color saturation
        saturation_factor = config.get('saturation', 1.8)
        if saturation_factor != 1.0:
            enhancer = ImageEnhance.Color(enhanced)
            enhanced = enhancer.enhance(saturation_factor)
        
        # Brightness
        brightness_factor = config.get('brightness', 1.1)
        if brightness_factor != 1.0:
            enhancer = ImageEnhance.Brightness(enhanced)
            enhanced = enhancer.enhance(brightness_factor)
        
        return enhanced

class CaptureSystemFactory:
    """Factory for creating capture system instances."""
    
    _systems = {}
    
    @classmethod
    def register_system(cls, name: str, system_class):
        """Register a capture system."""
        cls._systems[name] = system_class
    
    @classmethod
    def create_system(cls, capture_type: str, config: Dict[str, Any]) -> BaseCaptureSystem:
        """Create a capture system instance."""
        if capture_type not in cls._systems:
            raise ValueError(f"Unknown capture system: {capture_type}")
        
        system_class = cls._systems[capture_type]
        return system_class(config)
    
    @classmethod
    def list_available_systems(cls) -> List[str]:
        """List all available capture systems."""
        return list(cls._systems.keys())
    
    @classmethod
    def get_best_available_system(cls, config: Dict[str, Any]) -> Optional[str]:
        """Get the best available capture system."""
        for system_name, system_class in cls._systems.items():
            try:
                system = system_class(config)
                if system.is_available():
                    return system_name
            except Exception:
                continue
        return None