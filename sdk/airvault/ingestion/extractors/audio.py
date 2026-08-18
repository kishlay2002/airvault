"""Audio transcription extractor using faster-whisper."""

from pathlib import Path

import structlog

from airvault.ingestion.extractors.base import BaseExtractor, ExtractionResult

logger = structlog.get_logger()


class AudioExtractor(BaseExtractor):
    def extract(self, file_path: Path) -> ExtractionResult:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError(
                "faster-whisper is required for audio extraction. "
                "Install with: pip install airvault[audio]"
            )

        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(str(file_path), beam_size=5)

        texts = []
        for segment in segments:
            texts.append(segment.text.strip())

        full_text = " ".join(texts)

        logger.info(
            "audio_extracted",
            file=file_path.name,
            language=info.language,
            duration=round(info.duration, 1),
            chars=len(full_text),
        )

        return ExtractionResult(
            text=full_text,
            metadata={"language": info.language, "duration_seconds": round(info.duration, 1)},
        )
