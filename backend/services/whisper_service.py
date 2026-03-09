"""
Whisper Service – Speech-to-Text via OpenAI Whisper API.

Sends an uploaded audio file to the OpenAI Whisper API and
returns the transcribed text. Falls back to a placeholder
when no API key is configured (for local development).
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcribe an audio file to text using OpenAI Whisper API.

    Args:
        audio_file_path: Absolute path to the audio file on disk.

    Returns:
        Transcribed text string.

    Raises:
        Exception: If the API call fails.
    """
    api_key = settings.OPENAI_API_KEY

    if not api_key or api_key.startswith("sk-your"):
        logger.warning(
            "OPENAI_API_KEY not set. Returning placeholder transcription."
        )
        return "[DEV MODE] What is my leave balance?"
        
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
            )

        logger.info("Whisper transcription successful.")
        return transcript.strip()

    except Exception as e:
        logger.error(f"Whisper API error: {e}")
        raise
