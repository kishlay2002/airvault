import asyncio
import structlog

from app.extractors.base import BaseExtractor, ExtractionResult

logger = structlog.get_logger()


class AudioExtractor(BaseExtractor):
    async def extract(self, file_path: str) -> ExtractionResult:
        return await asyncio.to_thread(self._extract_sync, file_path)

    def _extract_sync(self, file_path: str) -> ExtractionResult:
        try:
            from faster_whisper import WhisperModel

            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, info = model.transcribe(file_path, beam_size=5)

            transcript_parts: list[str] = []
            for segment in segments:
                transcript_parts.append(segment.text.strip())

            full_text = " ".join(transcript_parts)

            logger.info(
                "audio_transcribed",
                file_path=file_path,
                language=info.language,
                duration_s=round(info.duration, 2),
                chars=len(full_text),
            )

            return ExtractionResult(
                text=full_text,
                metadata={
                    "language": info.language,
                    "duration_seconds": round(info.duration, 2),
                },
            )
        except ImportError:
            logger.error("faster_whisper_not_installed")
            raise RuntimeError("faster-whisper is required for audio extraction")
        except Exception as e:
            logger.error("audio_extraction_failed", file_path=file_path, error=str(e))
            raise
