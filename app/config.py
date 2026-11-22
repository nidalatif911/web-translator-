"""
Application Configuration and Constants
Web Translator
"""

APP_NAME = "Web Translator"
APP_SUBTITLE = "Real-Time Voice, Document & Webpage Translation"
APP_VERSION = "2.5.0"
AUTHOR = "Web Translator"
GITHUB_URL = "https://github.com/krishna-Deshmukh13/real-time-voice-translator"

# Audio Recording Settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION_MS = 100   # 100ms per audio chunk
SILENCE_TIMEOUT_SEC = 1.0  # seconds of silence to trigger end-of-speech
VAD_ENERGY_THRESHOLD = 0.02 # default RMS threshold for speech activity

# Supported Languages mapping
# Key: Display Name
# stt: SpeechRecognition language code (e.g. en-US)
# tts: gTTS language code (e.g. en)
# mymemory: MyMemory language name
# google: Google Translator ISO code
LANGUAGES = {
    "English": {
        "stt": "en-US",
        "tts": "en",
        "mymemory": "english",
        "google": "en",
        "flag": "🇺🇸"
    },
    "Spanish": {
        "stt": "es-ES",
        "tts": "es",
        "mymemory": "spanish",
        "google": "es",
        "flag": "🇪🇸"
    },
    "Hindi": {
        "stt": "hi-IN",
        "tts": "hi",
        "mymemory": "hindi",
        "google": "hi",
        "flag": "🇮🇳"
    },
    "French": {
        "stt": "fr-FR",
        "tts": "fr",
        "mymemory": "french",
        "google": "fr",
        "flag": "🇫🇷"
    },
    "German": {
        "stt": "de-DE",
        "tts": "de",
        "mymemory": "german",
        "google": "de",
        "flag": "🇩🇪"
    },
    "Japanese": {
        "stt": "ja-JP",
        "tts": "ja",
        "mymemory": "japanese",
        "google": "ja",
        "flag": "🇯🇵"
    },
    "Korean": {
        "stt": "ko-KR",
        "tts": "ko",
        "mymemory": "korean",
        "google": "ko",
        "flag": "🇰🇷"
    },
    "Chinese (Simplified)": {
        "stt": "zh-CN",
        "tts": "zh-CN",
        "mymemory": "chinese simplified",
        "google": "zh-CN",
        "flag": "🇨🇳"
    },
    "Russian": {
        "stt": "ru-RU",
        "tts": "ru",
        "mymemory": "russian",
        "google": "ru",
        "flag": "🇷🇺"
    },
    "Italian": {
        "stt": "it-IT",
        "tts": "it",
        "mymemory": "italian",
        "google": "it",
        "flag": "🇮🇹"
    },
    "Portuguese": {
        "stt": "pt-BR",
        "tts": "pt",
        "mymemory": "portuguese brazil",
        "google": "pt",
        "flag": "🇧🇷"
    },
    "Arabic": {
        "stt": "ar-SA",
        "tts": "ar",
        "mymemory": "arabic",
        "google": "ar",
        "flag": "🇸🇦"
    },
    "Bengali": {
        "stt": "bn-IN",
        "tts": "bn",
        "mymemory": "bengali",
        "google": "bn",
        "flag": "🇧🇩"
    },
    "Tamil": {
        "stt": "ta-IN",
        "tts": "ta",
        "mymemory": "tamil india",
        "google": "ta",
        "flag": "🇮🇳"
    },
    "Telugu": {
        "stt": "te-IN",
        "tts": "te",
        "mymemory": "telugu",
        "google": "te",
        "flag": "🇮🇳"
    },
    "Gujarati": {
        "stt": "gu-IN",
        "tts": "gu",
        "mymemory": "gujarati",
        "google": "gu",
        "flag": "🇮🇳"
    },
    "Kannada": {
        "stt": "kn-IN",
        "tts": "kn",
        "mymemory": "kannada",
        "google": "kn",
        "flag": "🇮🇳"
    },
    "Punjabi": {
        "stt": "pa-IN",
        "tts": "pa",
        "mymemory": "punjabi",
        "google": "pa",
        "flag": "🇮🇳"
    },
    "Turkish": {
        "stt": "tr-TR",
        "tts": "tr",
        "mymemory": "turkish",
        "google": "tr",
        "flag": "🇹🇷"
    },
    "Dutch": {
        "stt": "nl-NL",
        "tts": "nl",
        "mymemory": "dutch",
        "google": "nl",
        "flag": "🇳🇱"
    }
}

LANGUAGE_NAMES = list(LANGUAGES.keys())
