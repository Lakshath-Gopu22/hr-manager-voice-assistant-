"""
Voice AI – Main Orchestrator View.

This is the heart of the system. It receives an audio file OR text,
runs the full pipeline (STT → NLP → HR → TTS), logs the
conversation, and returns the result.

Pipeline:
    1. Save uploaded audio to disk (or accept text directly)
    2. Whisper API transcription (or use provided text)
    3. Intent detection → intent string
    4. HR service → text response
    5. gTTS → audio response file
    6. Log conversation
    7. Return JSON + audio URL
"""

import os
import uuid
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from services.whisper_service import transcribe_audio
from services.intent_service import detect_intent
from services.hr_service import handle_intent
from services.tts_service import generate_audio
from apps.audit_logs.models import ConversationLog

logger = logging.getLogger(__name__)

# Allowed audio MIME types for upload validation
ALLOWED_AUDIO_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/webm",
    "audio/flac",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
}


@api_view(["POST"])
def voice_query_view(request):
    """
    POST /api/voice/query/

    Accepts an audio file upload, processes the full
    voice pipeline, and returns a JSON response with
    the text answer and a URL to the audio response.

    Request:
        - Form-data field: "audio" (file)

    Response:
        {
            "query_text": "...",
            "detected_intent": "...",
            "response_text": "...",
            "audio_response_url": "http://.../media/audio/response_xxx.mp3"
        }
    """
    # ------- 1. Validate audio upload -------
    audio_file = request.FILES.get("audio")
    if not audio_file:
        return Response(
            {"error": "No audio file provided. Use the 'audio' form field."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    content_type = audio_file.content_type
    if content_type not in ALLOWED_AUDIO_TYPES:
        return Response(
            {"error": f"Unsupported audio type: {content_type}. Allowed: wav, mp3, ogg, webm, flac, m4a."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ------- 2. Save uploaded audio to disk -------
    upload_dir = os.path.join(settings.MEDIA_ROOT, "audio", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"upload_{uuid.uuid4().hex[:12]}{_get_extension(audio_file.name)}"
    upload_path = os.path.join(upload_dir, filename)

    with open(upload_path, "wb+") as dest:
        for chunk in audio_file.chunks():
            dest.write(chunk)

    logger.info(f"Audio saved: {upload_path}")

    try:
        # ------- 3. Speech-to-Text (Whisper) -------
        query_text = transcribe_audio(upload_path)
        logger.info(f"Transcription: {query_text}")

        # Use the shared pipeline for the rest
        return _process_query(query_text, request)

    except Exception as e:
        logger.error(f"Voice pipeline error: {e}", exc_info=True)
        return Response(
            {"error": f"Processing failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def text_query_view(request):
    """
    POST /api/voice/text-query/

    Accepts a text query directly (e.g. from browser speech
    recognition or manual typing). Runs the same pipeline
    as the voice endpoint but skips Whisper transcription.

    Request:
        - JSON body: {"text": "What is my leave balance?"}

    Response:
        Same as /api/voice/query/
    """
    query_text = request.data.get("text", "").strip()
    if not query_text:
        return Response(
            {"error": "No text provided. Send {'text': 'your question'}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        return _process_query(query_text, request)

    except Exception as e:
        logger.error(f"Text query pipeline error: {e}", exc_info=True)
        return Response(
            {"error": f"Processing failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _process_query(query_text, request):
    """
    Shared pipeline: Intent → HR response → TTS → Log → Return.
    Used by both voice_query_view and text_query_view.
    """
    # ------- Intent Detection (NLP) -------
    intent = detect_intent(query_text)
    logger.info(f"Detected intent: {intent}")

    # ------- HR Data Retrieval -------
    result = handle_intent(intent, request.user, query_text)

    # handle_intent returns a dict: {text, action, data}
    response_text = result["text"]
    action = result.get("action")
    action_data = result.get("data")

    logger.info(f"HR response generated for intent '{intent}' (action={action})")

    # ------- Text-to-Speech (gTTS) -------
    audio_relative_path = generate_audio(response_text)
    audio_url = request.build_absolute_uri(
        f"{settings.MEDIA_URL}{audio_relative_path}"
    )

    # ------- Log Conversation -------
    ConversationLog.objects.create(
        employee=request.user,
        query_text=query_text,
        detected_intent=intent,
        response_text=response_text,
        audio_file=audio_relative_path,
    )

    # ------- Return Response -------
    response_data = {
        "query_text": query_text,
        "detected_intent": intent,
        "response_text": response_text,
        "audio_response_url": audio_url,
    }

    # Include action fields for multi-step conversation flows
    if action:
        response_data["action"] = action
    if action_data:
        response_data["action_data"] = action_data

    return Response(response_data)


def _get_extension(filename: str) -> str:
    """Extract file extension (e.g. '.wav') from a filename."""
    _, ext = os.path.splitext(filename)
    return ext if ext else ".wav"
