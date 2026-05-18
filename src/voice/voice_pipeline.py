from fastapi import UploadFile
from src.voice.stt import process_audio_to_text
from src.voice.tts import process_text_to_audio
from src.api.service import ShopNestService

# Initialize a global service instance for voice context if not passed
voice_service = ShopNestService()

def run_voice_pipeline(audio_file: UploadFile, session_id: str = "default_voice_session") -> str:
    """
    Runs the complete voice pipeline:
    1. STT: audio to text
    2. Agent: text to assistant response
    3. TTS: assistant response to audio
    Returns the path to the TTS generated audio file.
    """
    # 1. Convert audio to text
    user_text = process_audio_to_text(audio_file)
    
    # Check if empty
    if not user_text:
        return process_text_to_audio("I could not hear any speech. Please try again.")

    # 2. Get response from existing shop agent
    # Using existing service method to respect memory, guardrails & tracing
    agent_result = voice_service.ask(session_id=session_id, message=user_text)
    agent_response = agent_result.get("response", "I'm sorry, I could not process your request.")
    
    # 3. Convert response text to speech audio
    audio_path = process_text_to_audio(agent_response)
    
    return audio_path
