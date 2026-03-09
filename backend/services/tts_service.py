"""
TTS Service – Text-to-Speech using Google gTTS.

Converts a text response into an MP3 audio file and saves
it under media/audio/ so Django can serve it.
"""

import os
import uuid
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def generate_audio(text: str) -> str:
    """
    Convert text to an MP3 audio file using gTTS.

    Args:
        text: The response text to convert to speech.

    Returns:
        Relative path (from MEDIA_ROOT) to the generated audio file.
        e.g. "audio/response_abc123.mp3"
    """
    try:
        from gtts import gTTS

       
        audio_dir = os.path.join(settings.MEDIA_ROOT, "audio")
        os.makedirs(audio_dir, exist_ok=True)

      
        filename = f"response_{uuid.uuid4().hex[:12]}.mp3"
        file_path = os.path.join(audio_dir, filename)

        
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(file_path)

        logger.info(f"TTS audio saved: {filename}")
        return f"audio/{filename}"

    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        raise
