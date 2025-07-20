#!/usr/bin/env python3
"""
Video inspection tool for Pokemon AI system.
Allows you to browse and view captured video segments and AI frames.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def list_video_segments(data_dir="data/videos"):
    """List all captured video segments."""
    inspection_dir = os.path.join(data_dir, "inspection")
    if not os.path.exists(inspection_dir):
        print(f"❌ No inspection directory found at {inspection_dir}")
        print("   Make sure debug_mode is enabled and you've captured some videos!")
        return []
    
    segments = []
    for item in os.listdir(inspection_dir):
        segment_path = os.path.join(inspection_dir, item)
        if os.path.isdir(segment_path) and item.startswith("video_segment_"):
            # Get metadata
            metadata_path = os.path.join(segment_path, "metadata.txt")
            metadata = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    for line in f:
                        if ':' in line:
                            key, value = line.strip().split(':', 1)
                            metadata[key.strip()] = value.strip()
            
            segments.append({
                'name': item,
                'path': segment_path,
                'metadata': metadata
            })
    
    return sorted(segments, key=lambda x: x['name'])

def list_ai_frames(data_dir="data/videos"):
    """List all AI frame requests."""
    ai_frames_dir = os.path.join(data_dir, "ai_frames")
    if not os.path.exists(ai_frames_dir):
        print(f"❌ No AI frames directory found at {ai_frames_dir}")
        return []
    
    requests = []
    for item in os.listdir(ai_frames_dir):
        request_path = os.path.join(ai_frames_dir, item)
        if os.path.isdir(request_path) and item.startswith("ai_request_"):
            # Get metadata
            metadata_path = os.path.join(request_path, "ai_request_metadata.txt")
            metadata = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    for line in f:
                        if ':' in line:
                            key, value = line.strip().split(':', 1)
                            metadata[key.strip()] = value.strip()
            
            requests.append({
                'name': item,
                'path': request_path,
                'metadata': metadata
            })
    
    return sorted(requests, key=lambda x: x['name'])

def open_directory(path):
    """Open directory in system file manager."""
    try:
        if sys.platform == "darwin":  # macOS
            subprocess.run(["open", path])
        elif sys.platform == "win32":  # Windows
            subprocess.run(["explorer", path])
        else:  # Linux
            subprocess.run(["xdg-open", path])
        print(f"📂 Opened {path}")
    except Exception as e:
        print(f"❌ Failed to open directory: {e}")
        print(f"   Manually navigate to: {path}")

def main():
    parser = argparse.ArgumentParser(description="Inspect captured video segments and AI frames")
    parser.add_argument("--data-dir", default="data/videos", 
                       help="Directory containing video data (default: data/videos)")
    parser.add_argument("--list-segments", action="store_true",
                       help="List all captured video segments")
    parser.add_argument("--list-ai-frames", action="store_true", 
                       help="List all AI frame requests")
    parser.add_argument("--open-segment", metavar="SEGMENT_NAME",
                       help="Open specific video segment directory")
    parser.add_argument("--open-ai-request", metavar="REQUEST_NAME",
                       help="Open specific AI request directory")
    parser.add_argument("--open-latest", action="store_true",
                       help="Open the latest video segment or AI request")
    parser.add_argument("--clean", action="store_true",
                       help="Remove all inspection files")

    args = parser.parse_args()

    if args.clean:
        inspection_dir = os.path.join(args.data_dir, "inspection")
        ai_frames_dir = os.path.join(args.data_dir, "ai_frames")
        
        import shutil
        if os.path.exists(inspection_dir):
            shutil.rmtree(inspection_dir)
            print(f"🗑️ Cleaned {inspection_dir}")
        if os.path.exists(ai_frames_dir):
            shutil.rmtree(ai_frames_dir)
            print(f"🗑️ Cleaned {ai_frames_dir}")
        return

    if args.list_segments or (not any([args.list_ai_frames, args.open_segment, args.open_ai_request, args.open_latest])):
        print("📹 Video Segments:")
        print("=" * 50)
        segments = list_video_segments(args.data_dir)
        if not segments:
            print("   No video segments found.")
        else:
            for segment in segments:
                print(f"📁 {segment['name']}")
                if segment['metadata']:
                    duration = segment['metadata'].get('Duration', 'Unknown')
                    frames = segment['metadata'].get('Frame Count', 'Unknown')
                    print(f"   Duration: {duration}, Frames: {frames}")
                print(f"   Path: {segment['path']}")
                print()

    if args.list_ai_frames:
        print("🤖 AI Frame Requests:")
        print("=" * 50)
        requests = list_ai_frames(args.data_dir)
        if not requests:
            print("   No AI frame requests found.")
        else:
            for request in requests:
                print(f"📁 {request['name']}")
                if request['metadata']:
                    duration = request['metadata'].get('Duration', 'Unknown')
                    frames = request['metadata'].get('Frames Sent', 'Unknown')
                    print(f"   Duration: {duration}, Frames Sent: {frames}")
                print(f"   Path: {request['path']}")
                print()

    if args.open_segment:
        segments = list_video_segments(args.data_dir)
        for segment in segments:
            if segment['name'] == args.open_segment:
                open_directory(segment['path'])
                return
        print(f"❌ Video segment '{args.open_segment}' not found")

    if args.open_ai_request:
        requests = list_ai_frames(args.data_dir)
        for request in requests:
            if request['name'] == args.open_ai_request:
                open_directory(request['path'])
                return
        print(f"❌ AI request '{args.open_ai_request}' not found")

    if args.open_latest:
        segments = list_video_segments(args.data_dir)
        requests = list_ai_frames(args.data_dir)
        
        if segments:
            latest_segment = segments[-1]
            print(f"📹 Opening latest video segment: {latest_segment['name']}")
            open_directory(latest_segment['path'])
        
        if requests:
            latest_request = requests[-1]
            print(f"🤖 Opening latest AI request: {latest_request['name']}")
            open_directory(latest_request['path'])

if __name__ == "__main__":
    main()