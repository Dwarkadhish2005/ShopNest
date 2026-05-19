from fastapi import UploadFile
import os
import tempfile
from groq import Groq
from src.config import GROQ_API_KEY

def process_audio_to_text(audio_file: UploadFile) -> str:
    """
    Converts speech to text using Groq's Whisper API (runs locally or via API).
    """
    if not GROQ_API_KEY:
        return "I heard you, but my STT service (Groq API Key) is not configured."
        
    client = Groq(api_key=GROQ_API_KEY)
    
    # Save the uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_file.file.read())
        temp_audio_path = temp_audio.name
        
    try:
        with open(temp_audio_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(audio_file.filename or "audio.wav", file.read()),
                model="whisper-large-v3",
                prompt="The audio is a customer asking a shopping query.",
                response_format="text",
                language="en"
            )
        return transcription.strip()
    finally:
        os.remove(temp_audio_path)
