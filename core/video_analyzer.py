#!/usr/bin/env python3
"""
Video analysis system for processing captured video segments.
"""

from typing import Dict, List, Any, Optional, Tuple
import PIL.Image
import time
from .base_capture_system import CaptureFrame, VideoSegment

class VideoAnalyzer:
    """Analyzes video segments for AI decision making."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.frame_sampling_strategy = config.get('frame_sampling', 'keyframes')
        self.max_frames_for_analysis = config.get('max_analysis_frames', 5)
        self.motion_threshold = config.get('motion_threshold', 0.1)
    
    def analyze_video_segment(self, segment: VideoSegment) -> Dict[str, Any]:
        """Analyze a video segment and return analysis results."""
        if not segment.frames:
            return {'error': 'No frames in segment'}
        
        analysis = {
            'segment_info': {
                'duration': segment.duration,
                'frame_count': segment.get_frame_count(),
                'fps': segment.get_frame_count() / segment.duration if segment.duration > 0 else 0,
                'start_time': segment.start_time,
                'end_time': segment.end_time
            },
            'key_frames': [],
            'motion_analysis': {},
            'content_changes': [],
            'recommended_frames': []
        }
        
        # Extract key frames for analysis
        key_frames = self._extract_key_frames(segment)
        analysis['key_frames'] = [
            {
                'frame_number': frame.frame_number,
                'timestamp': frame.timestamp,
                'relative_time': frame.timestamp - segment.start_time
            }
            for frame in key_frames
        ]
        
        # Analyze motion and changes
        motion_analysis = self._analyze_motion(segment)
        analysis['motion_analysis'] = motion_analysis
        
        # Detect significant content changes
        content_changes = self._detect_content_changes(segment)
        analysis['content_changes'] = content_changes
        
        # Recommend frames for LLM analysis
        recommended_frames = self._recommend_frames_for_llm(segment, key_frames)
        analysis['recommended_frames'] = recommended_frames
        
        return analysis
    
    def _extract_key_frames(self, segment: VideoSegment) -> List[CaptureFrame]:
        """Extract key frames from video segment based on sampling strategy."""
        frames = segment.frames
        
        if not frames:
            return []
        
        if self.frame_sampling_strategy == 'uniform':
            return self._sample_uniform_frames(frames)
        elif self.frame_sampling_strategy == 'keyframes':
            return self._sample_key_frames(frames)
        elif self.frame_sampling_strategy == 'endpoints':
            return self._sample_endpoint_frames(frames)
        else:
            # Default to first and last frames
            return [frames[0], frames[-1]] if len(frames) > 1 else frames
    
    def _sample_uniform_frames(self, frames: List[CaptureFrame]) -> List[CaptureFrame]:
        """Sample frames uniformly across the video."""
        if len(frames) <= self.max_frames_for_analysis:
            return frames
        
        step = len(frames) // self.max_frames_for_analysis
        return [frames[i * step] for i in range(self.max_frames_for_analysis)]
    
    def _sample_key_frames(self, frames: List[CaptureFrame]) -> List[CaptureFrame]:
        """Sample key frames based on content changes."""
        if len(frames) <= 2:
            return frames
        
        key_frames = [frames[0]]  # Always include first frame
        
        # Look for frames with significant changes
        for i in range(1, len(frames)):
            if len(key_frames) >= self.max_frames_for_analysis:
                break
            
            current_frame = frames[i]
            last_key_frame = key_frames[-1]
            
            # Calculate difference between frames (simplified)
            if self._frames_differ_significantly(last_key_frame, current_frame):
                key_frames.append(current_frame)
        
        # Always include last frame if not already included
        if frames[-1] not in key_frames:
            key_frames.append(frames[-1])
        
        return key_frames
    
    def _sample_endpoint_frames(self, frames: List[CaptureFrame]) -> List[CaptureFrame]:
        """Sample first and last frames only."""
        if len(frames) == 1:
            return frames
        return [frames[0], frames[-1]]
    
    def _frames_differ_significantly(self, frame1: CaptureFrame, frame2: CaptureFrame) -> bool:
        """Check if two frames differ significantly."""
        try:
            # Simple histogram-based comparison
            img1 = frame1.image.convert('RGB')
            img2 = frame2.image.convert('RGB')
            
            # Resize to small size for faster comparison
            size = (32, 32)
            img1_small = img1.resize(size)
            img2_small = img2.resize(size)
            
            # Calculate histogram difference
            hist1 = img1_small.histogram()
            hist2 = img2_small.histogram()
            
            # Simple chi-squared distance
            diff = sum(abs(h1 - h2) for h1, h2 in zip(hist1, hist2))
            total_pixels = size[0] * size[1] * 3  # RGB channels
            normalized_diff = diff / total_pixels
            
            return normalized_diff > self.motion_threshold
        
        except Exception as e:
            print(f"⚠️ Error comparing frames: {e}")
            return True  # Assume different if we can't compare
    
    def _analyze_motion(self, segment: VideoSegment) -> Dict[str, Any]:
        """Analyze motion in the video segment."""
        frames = segment.frames
        
        if len(frames) < 2:
            return {'motion_detected': False, 'motion_level': 0}
        
        total_motion = 0
        motion_points = []
        
        for i in range(1, len(frames)):
            motion = self._calculate_frame_motion(frames[i-1], frames[i])
            total_motion += motion
            motion_points.append({
                'frame_index': i,
                'motion_level': motion,
                'timestamp': frames[i].timestamp
            })
        
        avg_motion = total_motion / (len(frames) - 1) if len(frames) > 1 else 0
        
        return {
            'motion_detected': avg_motion > self.motion_threshold,
            'average_motion': avg_motion,
            'motion_points': motion_points,
            'high_motion_frames': [
                point for point in motion_points 
                if point['motion_level'] > avg_motion * 1.5
            ]
        }
    
    def _calculate_frame_motion(self, frame1: CaptureFrame, frame2: CaptureFrame) -> float:
        """Calculate motion between two frames."""
        try:
            # Simple pixel difference calculation
            img1 = frame1.image.convert('L').resize((64, 64))  # Grayscale and small
            img2 = frame2.image.convert('L').resize((64, 64))
            
            # Calculate average pixel difference
            pixels1 = list(img1.getdata())
            pixels2 = list(img2.getdata())
            
            total_diff = sum(abs(p1 - p2) for p1, p2 in zip(pixels1, pixels2))
            avg_diff = total_diff / len(pixels1)
            
            return avg_diff / 255.0  # Normalize to 0-1
        
        except Exception as e:
            print(f"⚠️ Error calculating motion: {e}")
            return 0.0
    
    def _detect_content_changes(self, segment: VideoSegment) -> List[Dict[str, Any]]:
        """Detect significant content changes in the video."""
        frames = segment.frames
        changes = []
        
        if len(frames) < 2:
            return changes
        
        for i in range(1, len(frames)):
            if self._frames_differ_significantly(frames[i-1], frames[i]):
                change_info = {
                    'frame_index': i,
                    'timestamp': frames[i].timestamp,
                    'relative_time': frames[i].timestamp - segment.start_time,
                    'change_type': 'content_change'
                }
                changes.append(change_info)
        
        return changes
    
    def _recommend_frames_for_llm(self, segment: VideoSegment, key_frames: List[CaptureFrame]) -> List[Dict[str, Any]]:
        """Recommend specific frames for LLM analysis."""
        recommendations = []
        
        # Always recommend first and last frames for before/after comparison
        if segment.frames:
            recommendations.append({
                'frame': segment.get_first_frame(),
                'reason': 'initial_state',
                'priority': 'high'
            })
            
            if segment.get_frame_count() > 1:
                recommendations.append({
                    'frame': segment.get_last_frame(),
                    'reason': 'final_state',
                    'priority': 'high'
                })
        
        # Add key frames with medium priority
        for frame in key_frames:
            if frame not in [r['frame'] for r in recommendations]:
                recommendations.append({
                    'frame': frame,
                    'reason': 'key_frame',
                    'priority': 'medium'
                })
        
        # Sort by priority and timestamp
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        recommendations.sort(key=lambda x: (priority_order[x['priority']], x['frame'].timestamp))
        
        return recommendations[:self.max_frames_for_analysis]
    
    def create_comparison_data(self, before_frame: CaptureFrame, after_frame: CaptureFrame) -> Dict[str, Any]:
        """Create comparison data between before and after frames."""
        return {
            'before_frame': {
                'timestamp': before_frame.timestamp,
                'frame_number': before_frame.frame_number,
                'metadata': before_frame.metadata
            },
            'after_frame': {
                'timestamp': after_frame.timestamp,
                'frame_number': after_frame.frame_number,
                'metadata': after_frame.metadata
            },
            'time_difference': after_frame.timestamp - before_frame.timestamp,
            'frames_differ': self._frames_differ_significantly(before_frame, after_frame),
            'motion_level': self._calculate_frame_motion(before_frame, after_frame)
        }