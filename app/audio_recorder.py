"""
Audio Recording & Speech Detection with SoundDevice
Web Translator
"""

import threading
import time
import logging
from typing import Callable, List, Optional, Tuple
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from app.config import SAMPLE_RATE, CHANNELS

logger = logging.getLogger(__name__)


def list_microphones() -> List[Tuple[int, str]]:
    """Lists available input audio devices."""
    devices = []
    try:
        host_apis = sd.query_hostapis()
        device_list = sd.query_devices()
        for idx, dev in enumerate(device_list):
            if dev["max_input_channels"] > 0:
                name = dev["name"]
                api_name = host_apis[dev["hostapi"]]["name"]
                devices.append((idx, f"{name} ({api_name})"))
    except Exception as e:
        logger.error(f"Error querying audio devices: {e}")
        devices.append((0, "Default Microphone"))
    return devices


class AudioRecorder:
    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        silence_timeout: float = 1.2,
        energy_threshold: float = 0.02
    ):
        self.sample_rate = sample_rate
        self.channels = CHANNELS
        self.silence_timeout = silence_timeout
        self.energy_threshold = energy_threshold

        self._is_recording = False
        self._stream: Optional[sd.InputStream] = None
        self._device_index: Optional[int] = None

        # Callbacks
        self.on_audio_level: Optional[Callable[[float], None]] = None
        self.on_phrase_complete: Optional[Callable[[sr.AudioData], None]] = None
        self.on_status_change: Optional[Callable[[str], None]] = None

        # Audio accumulation state
        self._speech_frames: List[np.ndarray] = []
        self._is_speaking = False
        self._silence_start_time = 0.0
        self._lock = threading.Lock()

    def set_device(self, device_index: Optional[int]):
        """Sets the active input device index."""
        self._device_index = device_index

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Audio stream callback running on sounddevice audio thread."""
        if status:
            logger.debug(f"Audio stream status: {status}")

        mono_data = indata[:, 0] if indata.ndim > 1 else indata
        rms = float(np.sqrt(np.mean(mono_data**2)))
        normalized_level = min(1.0, rms * 5.0)

        if self.on_audio_level:
            try:
                self.on_audio_level(normalized_level)
            except Exception:
                pass

        with self._lock:
            now = time.time()
            if rms > self.energy_threshold:
                if not self._is_speaking:
                    self._is_speaking = True
                    self._speech_frames = []
                    if self.on_status_change:
                        self.on_status_change("Speaking detected...")

                self._speech_frames.append(mono_data.copy())
                self._silence_start_time = now
            elif self._is_speaking:
                self._speech_frames.append(mono_data.copy())
                if now - self._silence_start_time > self.silence_timeout:
                    self._is_speaking = False
                    self._dispatch_phrase()

    def _dispatch_phrase(self):
        """Packages accumulated speech frames and dispatches to recognizer callback."""
        if not self._speech_frames:
            return

        full_audio = np.concatenate(self._speech_frames, axis=0)
        self._speech_frames = []

        min_samples = int(self.sample_rate * 0.4)
        if len(full_audio) < min_samples:
            return

        int16_data = (np.clip(full_audio, -1.0, 1.0) * 32767).astype(np.int16)
        raw_bytes = int16_data.tobytes()

        audio_data = sr.AudioData(raw_bytes, self.sample_rate, 2)

        if self.on_phrase_complete:
            threading.Thread(
                target=self.on_phrase_complete,
                args=(audio_data,),
                daemon=True
            ).start()

    def start(self):
        """Starts recording audio stream."""
        if self._is_recording:
            return

        self._is_recording = True
        self._speech_frames = []
        self._is_speaking = False

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                device=self._device_index,
                blocksize=int(self.sample_rate * 0.05),
                callback=self._audio_callback
            )
            self._stream.start()
            if self.on_status_change:
                self.on_status_change("Listening for voice...")
        except Exception as e:
            self._is_recording = False
            logger.error(f"Failed to start audio stream: {e}")
            raise e

    def stop(self):
        """Stops recording audio stream and processes any remaining speech."""
        if not self._is_recording:
            return

        self._is_recording = False

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.debug(f"Error stopping stream: {e}")
            self._stream = None

        with self._lock:
            if self._is_speaking and self._speech_frames:
                self._is_speaking = False
                self._dispatch_phrase()

        if self.on_audio_level:
            try:
                self.on_audio_level(0.0)
            except Exception:
                pass

        if self.on_status_change:
            self.on_status_change("Idle / Stopped")

    @property
    def is_recording(self) -> bool:
        return self._is_recording
