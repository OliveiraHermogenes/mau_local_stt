# Import faster-whisper
from typing import Any

try:
    from faster_whisper import WhisperModel

    WHISPER_INSTALLED = True  # faster-whisper is installed
except ModuleNotFoundError:
    faster_whisper = type("faster_whisper", (object,), {"WhisperModel": Any})  # Set faster_whisper for type hints
    WHISPER_INSTALLED = False  # faster-whisper is not installed

# Import vosk
try:
    import vosk

    VOSK_INSTALLED = True  # vosk is installed
except ModuleNotFoundError:
    vosk = type("vosk", (object,), {"Model": Any, "KaldiRecognizer": Any})  # Set vosk for type hints
    VOSK_INSTALLED = False  # vosk is not installed
