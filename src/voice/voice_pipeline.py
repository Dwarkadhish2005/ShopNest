from fastapi import UploadFile
from src.voice.stt import process_audio_to_text
from src.voice.tts import process_text_to_audio
from src.api.service import ShopNestService


voice_service = ShopNestService()

def run_voice_pipeline(audio_file: UploadFile, session_id: str = "default_voice_session") -> str:
    
    user_text = process_audio_to_text(audio_file)
    
    
    if not user_text:
        return process_text_to_audio("I could not hear any speech. Please try again.")

    
    
    agent_result = voice_service.ask(session_id=session_id, message=user_text)
    agent_response = agent_result.get("response", "I'm sorry, I could not process your request.")
    
    
    audio_path = process_text_to_audio(agent_response)
    
    return audio_path
