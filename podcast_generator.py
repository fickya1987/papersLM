import os
from pathlib import Path
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment
from dotenv import load_dotenv
import ast
from tqdm import tqdm

class PodcastGenerator:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.client = ElevenLabs(
            api_key=os.getenv('ELEVENLABS_API_KEY')
        )
        
        # Define voice IDs for speakers
        self.SPEAKER1_VOICE_ID = "pFZP5JQG7iQjIQuC4Bku"
        self.SPEAKER2_VOICE_ID = "flq6f7yk4E4fJM5XTYuZ"
        
        # Define voice settings
        self.voice_settings = VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True
        )
        
    def generate_speaker_audio(self, text, voice_id):
        """Generate audio using ElevenLabs API"""
        response = self.client.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_44100_128",
            text=text,
            model_id="eleven_turbo_v2_5",
            voice_settings=self.voice_settings
        )
        
        # Save temporary file and load as AudioSegment
        temp_path = f"temp_{voice_id}.mp3"
        with open(temp_path, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)
                    
        audio_segment = AudioSegment.from_mp3(temp_path)
        os.remove(temp_path)
        
        return audio_segment

    def generate_podcast(self, script_path, output_path):
        """Generate full podcast from script file"""
        # Read script file
        with open(script_path, 'r') as file:
            script_content = file.read()
        
        # Parse JSON script
        dialogue_data = ast.literal_eval(script_content)
        conversation = dialogue_data['conversation']
        
        # Initialize final audio
        final_audio = None
        
        # Generate audio for each segment
        for segment in tqdm(conversation, desc="Generating podcast segments"):
            voice_id = self.SPEAKER1_VOICE_ID if segment['speaker'] == "Speaker 1" else self.SPEAKER2_VOICE_ID
            audio_segment = self.generate_speaker_audio(segment['dialogue'], voice_id)
            
            # Add to final audio
            if final_audio is None:
                final_audio = audio_segment
            else:
                final_audio += audio_segment
        
        # Export final podcast
        final_audio.export(output_path, format="mp3", bitrate="192k")
        print(f"Podcast saved to: {output_path}")

def main():
    generator = PodcastGenerator()
    
    # Define input/output paths
    script_path = "/Users/parker/SciHub/scripts/transcript.txt"
    output_path = "outputs/final_podcast.mp3"
    
    # Create output directory if it doesn't exist
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Generate podcast
    generator.generate_podcast(script_path, output_path)

if __name__ == "__main__":
    main() 