"""Transcription locale (sans API) via faster-whisper. Optionnel :
    pip install faster-whisper   puis   TRANSCRIPTION_PROVIDER=faster_whisper
"""
from ai.base import AIConfigError, Transcript, segments_from_whisper
from core.config import get_settings

_model = None


class FasterWhisperTranscriber:
    name = "faster_whisper"

    def __init__(self):
        global _model
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise AIConfigError("faster-whisper n'est pas installé (pip install faster-whisper).")
        if _model is None:
            try:
                _model = WhisperModel(get_settings().faster_whisper_model, device="auto", compute_type="int8")
            except Exception as e:
                raise AIConfigError(f"Chargement du modèle Whisper local impossible : {e}")
        self.model = _model

    def transcribe(self, audio_path: str) -> Transcript:
        segments, info = self.model.transcribe(audio_path, vad_filter=True, temperature=0.0)
        raw = [{"start": s.start, "end": s.end, "text": s.text,
                "avg_logprob": s.avg_logprob, "no_speech_prob": s.no_speech_prob} for s in segments]
        return Transcript(language=info.language or "", segments=segments_from_whisper(raw))
