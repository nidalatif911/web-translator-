"""
Text-to-Speech (TTS) Engine and Audio Playback
Web Translator
"""

import os
import time
import tempfile
import threading
import logging
import ctypes
from typing import Optional
from gtts import gTTS
import pyttsx3
from app.config import LANGUAGES

logger = logging.getLogger(__name__)


class TTSEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._current_audio_file: Optional[str] = None
        self._is_playing = False
        self._last_alias: Optional[str] = None
        
        # Initialize pyttsx3 offline fallback engine
        try:
            self._pyttsx3_engine = pyttsx3.init()
            self._pyttsx3_engine.setProperty("rate", 160)
        except Exception as e:
            logger.warning(f"Offline pyttsx3 could not be initialized: {e}")
            self._pyttsx3_engine = None

    def stop_playback(self):
        """Stops currently playing audio."""
        try:
            if self._last_alias:
                winmm = ctypes.windll.winmm
                winmm.mciSendStringW(f"stop {self._last_alias}", None, 0, None)
                winmm.mciSendStringW(f"close {self._last_alias}", None, 0, None)
                self._last_alias = None
            self._is_playing = False
        except Exception as e:
            logger.debug(f"Error stopping audio: {e}")

    def _play_file_windows(self, file_path: str):
        """Plays an audio file on Windows using MCI without file locks."""
        try:
            self.stop_playback()
            winmm = ctypes.windll.winmm
            alias = f"vox_{int(time.time() * 1000)}"
            self._last_alias = alias
            abs_path = os.path.abspath(file_path).replace("\\", "/")

            winmm.mciSendStringW(f'open "{abs_path}" type mpegvideo alias {alias}', None, 0, None)
            self._is_playing = True
            winmm.mciSendStringW(f"play {alias} wait", None, 0, None)
            winmm.mciSendStringW(f"close {alias}", None, 0, None)
            self._last_alias = None
        except Exception as e:
            logger.error(f"Playback error: {e}")
        finally:
            self._is_playing = False

    def synthesize(self, text: str, lang_name: str) -> Optional[str]:
        """
        Synthesizes text to speech using gTTS and saves to a temp mp3 file.
        Returns the path to the generated audio file.
        """
        if not text or not text.strip():
            return None

        clean_text = text.strip()
        lang_info = LANGUAGES.get(lang_name, {})
        tts_lang = lang_info.get("tts", "en")

        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"voxtrans_{int(time.time() * 1000)}.mp3")

        try:
            tts = gTTS(text=clean_text, lang=tts_lang, slow=False)
            tts.save(output_path)
            
            with self._lock:
                if self._current_audio_file and os.path.exists(self._current_audio_file):
                    try:
                        os.remove(self._current_audio_file)
                    except Exception:
                        pass
                self._current_audio_file = output_path
                
            return output_path
        except Exception as e:
            logger.warning(f"gTTS synthesis failed: {e}. Trying offline pyttsx3 fallback...")
            return None

    def speak(self, text: str, lang_name: str, async_play: bool = True, on_start=None, on_finish=None):
        """
        Synthesizes and speaks text.
        Runs asynchronously in a background thread by default.
        """
        def _worker():
            if on_start:
                try:
                    on_start()
                except Exception:
                    pass

            audio_file = self.synthesize(text, lang_name)
            if audio_file and os.path.exists(audio_file):
                self._play_file_windows(audio_file)
            elif self._pyttsx3_engine:
                try:
                    self._pyttsx3_engine.say(text)
                    self._pyttsx3_engine.runAndWait()
                except Exception as ex:
                    logger.error(f"pyttsx3 fallback failed: {ex}")

            if on_finish:
                try:
                    on_finish()
                except Exception:
                    pass

        if async_play:
            thread = threading.Thread(target=_worker, daemon=True)
            thread.start()
        else:
            _worker()

    def replay_last(self, on_start=None, on_finish=None):
        """Replays the last generated audio file without re-synthesizing."""
        with self._lock:
            last_file = self._current_audio_file

        if last_file and os.path.exists(last_file):
            def _worker():
                if on_start:
                    try:
                        on_start()
                    except Exception:
                        pass
                self._play_file_windows(last_file)
                if on_finish:
                    try:
                        on_finish()
                    except Exception:
                        pass

            thread = threading.Thread(target=_worker, daemon=True)
            thread.start()
            return True
        return False


# Singleton instance
tts_service = TTSEngine()
