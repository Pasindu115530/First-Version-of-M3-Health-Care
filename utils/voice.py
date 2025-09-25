"""
Lightweight text-to-speech helper for Windows using SAPI.SpVoice.
No external dependencies beyond pywin32, which is already required on Windows.
"""

from typing import Optional

try:
    import win32com.client  # type: ignore
    _SAPI_AVAILABLE = True
except Exception:
    _SAPI_AVAILABLE = False


class VoiceGuide:
    """Simple singleton-style TTS wrapper to speak instructions."""

    _instance: Optional["VoiceGuide"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._voice = None
        if _SAPI_AVAILABLE:
            try:
                self._voice = win32com.client.Dispatch("SAPI.SpVoice")
                # Slightly slower rate improves clarity for instructions
                try:
                    self._voice.Rate = -1
                except Exception:
                    pass
            except Exception:
                self._voice = None

    def speak(self, text: str) -> None:
        """Speak text asynchronously; fail silently if unavailable."""
        if not text:
            return
        try:
            if self._voice is not None:
                # Speak asynchronously so we never block UI/video thread
                self._voice.Speak(text, 1)  # 1 = SVSFlagsAsync
        except Exception:
            # Silently ignore TTS errors; visual UI remains the source of truth
            pass


voice = VoiceGuide()


