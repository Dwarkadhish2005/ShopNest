import os
import tempfile
import requests
from src.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
import gtts

def process_text_to_audio(text: str) -> str:
    """
    Converts text to speech using ElevenLabs (if configured) or falls back to gTTS (Google TTS).
    Returns the path to the generated audio file.
    """
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    audio_path = temp_audio.name
    temp_audio.close()
    
    if ELEVENLABS_API_KEY:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": ELEVENLABS_API_KEY
            }
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                with open(audio_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                return audio_path
            else:
                print(f"ElevenLabs TTS failed: {response.text}")
                # Fall through to fallback
        except Exception as e:
            print(f"ElevenLabs TTS exception: {str(e)}")
            # Fall through to fallback
            
    # Fallback to gtts (free) if ElevenLabs fails or is not configured
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang='en')
        tts.save(audio_path)
    except Exception as e:
        print(f"gTTS fallback failed: {str(e)}")
        # Create an empty file just so it doesn't crash
        with open(audio_path, 'wb') as f:
            pass
            
    return audio_path
