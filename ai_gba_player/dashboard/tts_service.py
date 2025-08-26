#!/usr/bin/env python3
"""
TTSService - Local Text-to-Speech service for narration playback.
Supports multiple local TTS engines like Coqui TTS, Piper, and system TTS.
"""

import os
import subprocess
import tempfile
import threading
import time
from typing import Dict, Any, Optional, List
from pathlib import Path


class TTSService:
    """Local Text-to-Speech service for converting narration to speech"""
    
    def __init__(self):
        # TTS Configuration
        self.tts_engine = "system"  # system, coqui, piper
        self.voice_model = "en_US-amy-medium"  # Default voice
        self.speaking_rate = 1.0  # Speech rate multiplier
        self.volume = 0.8  # Volume level (0.0 to 1.0)
        
        # Audio output settings
        self.audio_format = "wav"
        self.sample_rate = 22050
        self.output_dir = Path("/tmp/tts_output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Engine availability
        self.available_engines = self._detect_available_engines()
        
        # Select best available engine
        self.tts_engine = self._select_best_engine()
        
        # Audio playback queue
        self.playback_queue = []
        self.playback_thread = None
        self.playback_running = False
        
        print(f"🔊 TTSService initialized with engine: {self.tts_engine}")
        if self.available_engines:
            print(f"📢 Available TTS engines: {', '.join(self.available_engines)}")
        else:
            print("⚠️ No TTS engines detected - will use fallback system TTS")
    
    def _detect_available_engines(self) -> List[str]:
        """Detect which TTS engines are available on the system"""
        available = []
        
        # Check for system TTS (macOS 'say' command)
        if subprocess.run(["which", "say"], capture_output=True).returncode == 0:
            available.append("system_macos")
        
        # Check for espeak (Linux)
        if subprocess.run(["which", "espeak"], capture_output=True).returncode == 0:
            available.append("system_espeak")
        
        # Check for Coqui TTS
        try:
            import TTS
            available.append("coqui")
        except ImportError:
            pass
        
        # Check for Piper TTS
        if subprocess.run(["which", "piper"], capture_output=True).returncode == 0:
            available.append("piper")
        
        # Check for Python pyttsx3
        try:
            import pyttsx3
            available.append("pyttsx3")
        except ImportError:
            pass
        
        return available
    
    def _select_best_engine(self) -> str:
        """Select the best available TTS engine"""
        
        # Priority order: Coqui > Piper > System (macOS) > pyttsx3 > System (espeak)
        priority_order = ["coqui", "piper", "system_macos", "pyttsx3", "system_espeak"]
        
        for engine in priority_order:
            if engine in self.available_engines:
                return engine
        
        # Fallback to system TTS
        return "system"
    
    def speak_narration(self, narration_response: Dict[str, Any], blocking: bool = False):
        """Convert narration to speech and play it"""
        
        if not narration_response.get("success", False):
            print("⚠️ TTSService: Skipping TTS for failed narration")
            return
        
        # Extract text to speak
        narration_text = narration_response.get("narration", "")
        dialogue_text = narration_response.get("dialogue_reading", "")
        excitement_level = narration_response.get("excitement_level", "neutral")
        
        if not narration_text and not dialogue_text:
            print("⚠️ TTSService: No text to speak")
            return
        
        # Combine narration and dialogue
        full_text = ""
        if narration_text:
            full_text += narration_text
        if dialogue_text and dialogue_text.lower() not in ["none", "n/a"]:
            full_text += f" ... {dialogue_text}"
        
        if not full_text.strip():
            return
        
        # Adjust voice parameters based on excitement level
        voice_params = self._get_voice_params(excitement_level)
        
        print(f"🔊 TTSService: Speaking narration ({len(full_text)} chars, {excitement_level} energy)")
        
        if blocking:
            self._speak_text(full_text, voice_params)
        else:
            # Add to queue for background playback
            self.playback_queue.append((full_text, voice_params))
            self._ensure_playback_thread()
    
    def _get_voice_params(self, excitement_level: str) -> Dict[str, Any]:
        """Get voice parameters based on excitement level"""
        
        base_params = {
            "rate": self.speaking_rate,
            "volume": self.volume,
            "pitch": 0  # Neutral pitch
        }
        
        # Adjust parameters based on excitement
        if excitement_level == "low":
            base_params["rate"] = self.speaking_rate * 0.9
            base_params["pitch"] = -10  # Slightly lower pitch
        elif excitement_level == "high":
            base_params["rate"] = self.speaking_rate * 1.1
            base_params["pitch"] = 5  # Slightly higher pitch
        elif excitement_level == "epic":
            base_params["rate"] = self.speaking_rate * 1.2
            base_params["pitch"] = 10  # Higher pitch
            base_params["volume"] = min(1.0, self.volume * 1.1)
        
        return base_params
    
    def _speak_text(self, text: str, voice_params: Dict[str, Any]):
        """Actually speak the text using the selected TTS engine"""
        
        try:
            if self.tts_engine == "system_macos":
                self._speak_system_macos(text, voice_params)
            elif self.tts_engine == "system_espeak":
                self._speak_system_espeak(text, voice_params)
            elif self.tts_engine == "coqui":
                self._speak_coqui(text, voice_params)
            elif self.tts_engine == "piper":
                self._speak_piper(text, voice_params)
            elif self.tts_engine == "pyttsx3":
                self._speak_pyttsx3(text, voice_params)
            else:
                print(f"⚠️ TTSService: Unknown engine {self.tts_engine}, using system fallback")
                self._speak_system_fallback(text)
                
        except Exception as e:
            print(f"❌ TTSService: Error speaking text with {self.tts_engine}: {e}")
            # Try fallback
            try:
                self._speak_system_fallback(text)
            except Exception as fallback_error:
                print(f"❌ TTSService: Fallback TTS also failed: {fallback_error}")
    
    def _speak_system_macos(self, text: str, voice_params: Dict[str, Any]):
        """Speak using macOS 'say' command"""
        
        rate = int(voice_params["rate"] * 200)  # Convert to words per minute
        
        cmd = ["say", "-r", str(rate), text]
        subprocess.run(cmd, check=True)
    
    def _speak_system_espeak(self, text: str, voice_params: Dict[str, Any]):
        """Speak using Linux espeak"""
        
        rate = int(voice_params["rate"] * 175)  # Words per minute
        pitch = int(50 + voice_params["pitch"])  # 0-99 range
        
        cmd = ["espeak", "-s", str(rate), "-p", str(pitch), text]
        subprocess.run(cmd, check=True)
    
    def _speak_coqui(self, text: str, voice_params: Dict[str, Any]):
        """Speak using Coqui TTS"""
        
        try:
            from TTS.api import TTS
            
            # Initialize TTS (cached after first use)
            if not hasattr(self, '_coqui_tts'):
                self._coqui_tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")
            
            # Generate audio file
            output_file = self.output_dir / f"tts_output_{int(time.time())}.wav"
            self._coqui_tts.tts_to_file(text=text, file_path=str(output_file))
            
            # Play audio file
            self._play_audio_file(output_file)
            
            # Cleanup
            output_file.unlink()
            
        except Exception as e:
            print(f"❌ Coqui TTS error: {e}")
            raise
    
    def _speak_piper(self, text: str, voice_params: Dict[str, Any]):
        """Speak using Piper TTS"""
        
        output_file = self.output_dir / f"piper_output_{int(time.time())}.wav"
        
        # Piper command
        cmd = [
            "piper",
            "--model", self.voice_model,
            "--output_file", str(output_file)
        ]
        
        # Feed text via stdin
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
        process.communicate(input=text)
        
        if process.returncode == 0:
            self._play_audio_file(output_file)
            output_file.unlink()
        else:
            raise Exception(f"Piper TTS failed with return code {process.returncode}")
    
    def _speak_pyttsx3(self, text: str, voice_params: Dict[str, Any]):
        """Speak using pyttsx3 library"""
        
        import pyttsx3
        
        if not hasattr(self, '_pyttsx3_engine'):
            self._pyttsx3_engine = pyttsx3.init()
        
        engine = self._pyttsx3_engine
        
        # Set properties
        engine.setProperty('rate', int(voice_params["rate"] * 200))
        engine.setProperty('volume', voice_params["volume"])
        
        # Speak
        engine.say(text)
        engine.runAndWait()
    
    def _speak_system_fallback(self, text: str):
        """Fallback TTS using any available system command"""
        
        if "system_macos" in self.available_engines:
            subprocess.run(["say", text])
        elif "system_espeak" in self.available_engines:
            subprocess.run(["espeak", text])
        else:
            print(f"🔊 TTS Fallback: {text}")  # Just print if no TTS available
    
    def _play_audio_file(self, audio_file: Path):
        """Play an audio file using system audio player"""
        
        if os.name == 'posix':  # Unix-like (macOS, Linux)
            if subprocess.run(["which", "afplay"], capture_output=True).returncode == 0:
                subprocess.run(["afplay", str(audio_file)])
            elif subprocess.run(["which", "aplay"], capture_output=True).returncode == 0:
                subprocess.run(["aplay", str(audio_file)])
            elif subprocess.run(["which", "paplay"], capture_output=True).returncode == 0:
                subprocess.run(["paplay", str(audio_file)])
            else:
                print(f"⚠️ No audio player found to play {audio_file}")
        else:
            # Windows fallback
            os.system(f'start "" "{audio_file}"')
    
    def _ensure_playback_thread(self):
        """Ensure the background playback thread is running"""
        
        if not self.playback_running:
            self.playback_running = True
            self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
            self.playback_thread.start()
    
    def _playback_worker(self):
        """Background thread worker for TTS playback"""
        
        print("🔊 TTSService: Background playback thread started")
        
        while self.playback_running or self.playback_queue:
            if self.playback_queue:
                text, voice_params = self.playback_queue.pop(0)
                try:
                    self._speak_text(text, voice_params)
                except Exception as e:
                    print(f"❌ TTSService: Playback error: {e}")
            else:
                time.sleep(0.1)  # Brief pause when queue is empty
                
                # Auto-stop after 5 seconds of inactivity
                if not self.playback_queue:
                    time.sleep(5)
                    if not self.playback_queue:
                        break
        
        self.playback_running = False
        print("🔊 TTSService: Background playback thread stopped")
    
    def stop_playback(self):
        """Stop all TTS playback and clear queue"""
        
        self.playback_running = False
        self.playback_queue.clear()
        print("🔇 TTSService: Playback stopped and queue cleared")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current TTS service status"""
        
        return {
            "engine": self.tts_engine,
            "available_engines": self.available_engines,
            "queue_size": len(self.playback_queue),
            "playback_active": self.playback_running,
            "voice_model": self.voice_model,
            "speaking_rate": self.speaking_rate,
            "volume": self.volume
        }