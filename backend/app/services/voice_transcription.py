import os
import logging
import tempfile
import threading
import time

from faster_whisper import WhisperModel

from app.core.config import settings

_model: WhisperModel | None = None
_model_lock = threading.Lock()
logger = logging.getLogger(__name__)


def _whisper_model() -> WhisperModel:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                started = time.perf_counter()
                _model = WhisperModel(settings.whisper_model_size, device="cpu", compute_type="int8")
                logger.info("voice_model_warm seconds=%.3f model=%s", time.perf_counter() - started, settings.whisper_model_size)
    return _model


def warm_whisper_model() -> None:
    """Initialize Faster Whisper once; safe to run in an app startup thread."""
    _whisper_model()


def transcribe_audio(data: bytes, suffix: str) -> tuple[str, str | None, float | None]:
    started = time.perf_counter()
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            temporary.write(data)
            temporary_path = temporary.name
        segments, info = _whisper_model().transcribe(temporary_path, task="transcribe", beam_size=settings.whisper_beam_size, vad_filter=True, condition_on_previous_text=False)
        if info.duration > settings.voice_max_duration_seconds:
            raise ValueError(f"Recording exceeds the {settings.voice_max_duration_seconds}-second limit")
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
        if not text:
            raise ValueError("No speech was detected in the recording")
        logger.info("voice_timing stage=transcription seconds=%.3f audio_seconds=%.3f bytes=%d", time.perf_counter() - started, info.duration, len(data))
        return text, info.language, float(info.language_probability) if info.language_probability is not None else None
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)
