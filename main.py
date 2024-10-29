import os
from pathlib import Path
import shutil
from pdf_preprocessor import main as preprocess_pdf
from transcript_writer import generate_transcript
from podcast_generator import PodcastGenerator

class PodcastWorkflow:
    def __init__(self):
        # Define directory structure
        self.base_dir = Path(os.getcwd())
        self.input_dir = self.base_dir / "input"
        self.processed_pdfs_dir = self.base_dir / "processed_pdfs"
        self.cleaned_text_dir = self.base_dir / "cleanedText"
        self.scripts_dir = self.base_dir / "scripts"
        self.used_scripts_dir = self.base_dir / "used_scripts"
        self.output_dir = self.base_dir / "outputs"
        
        # Create all necessary directories
        self._setup_directories()
    
    def _setup_directories(self):
        """Create all required directories if they don't exist"""
        for directory in [self.input_dir, self.processed_pdfs_dir, 
                         self.cleaned_text_dir, self.scripts_dir, 
                         self.used_scripts_dir, self.output_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def process_new_pdfs(self):
        """Process all PDFs in the input directory"""
        pdf_files = list(self.input_dir.glob("*.pdf"))
        
        if not pdf_files:
            print("No PDF files found in input directory.")
            return False
        
        processed_names = []
        for pdf_path in pdf_files:
            print(f"\nProcessing PDF: {pdf_path.name}")
            
            # Step 1: Preprocess PDF and get descriptive name
            descriptive_name = preprocess_pdf(str(pdf_path))
            if not descriptive_name:
                continue
                
            processed_names.append(descriptive_name)
            
            # Move processed PDF to processed directory with new name
            new_pdf_name = f"{descriptive_name}.pdf"
            shutil.move(str(pdf_path), 
                       str(self.processed_pdfs_dir / new_pdf_name))
            
            # Move cleaned text file to cleaned text directory
            cleaned_file = f"clean_{descriptive_name}.txt"
            if os.path.exists(cleaned_file):
                shutil.move(cleaned_file, 
                           str(self.cleaned_text_dir / cleaned_file))
        
        return processed_names if processed_names else False

    def generate_transcripts(self):
        """Generate transcripts for all cleaned text files"""
        cleaned_files = list(self.cleaned_text_dir.glob("*.txt"))
        
        if not cleaned_files:
            print("No cleaned text files found.")
            return False
        
        for cleaned_file in cleaned_files:
            print(f"\nGenerating transcript for: {cleaned_file.name}")
            # Extract descriptive name from cleaned file name
            descriptive_name = cleaned_file.stem.replace('clean_', '')
            output_file = self.scripts_dir / f"transcript_{descriptive_name}.txt"
            
            generate_transcript(str(cleaned_file), str(output_file))
        
        return True

    def create_podcasts(self):
        """Generate podcasts from all transcript files"""
        transcript_files = list(self.scripts_dir.glob("*.txt"))
        
        if not transcript_files:
            print("No transcript files found.")
            return False
        
        generator = PodcastGenerator()
        
        for transcript_file in transcript_files:
            # Extract descriptive name from transcript file name
            descriptive_name = transcript_file.stem.replace('transcript_', '')
            print(f"\nGenerating podcast for: {descriptive_name}")
            output_file = self.output_dir / f"podcast_{descriptive_name}.mp3"
            
            try:
                generator.generate_podcast(str(transcript_file), str(output_file))
                
                # Move to used_scripts with same naming convention
                shutil.move(str(transcript_file), 
                          str(self.used_scripts_dir / f"used_{descriptive_name}.txt"))
                print(f"Moved used script to: {self.used_scripts_dir / f'used_{descriptive_name}.txt'}")
                
            except Exception as e:
                print(f"Error generating podcast for {descriptive_name}: {str(e)}")
                continue
        
        return True

    def cleanup_processed_files(self):
        """Optional: Clean up processed text files"""
        # Add any additional cleanup steps here if needed
        pass

def main():
    workflow = PodcastWorkflow()
    
    print("Starting podcast generation workflow...")
    
    # Step 1: Process PDFs
    print("\n=== Step 1: Processing PDFs ===")
    if workflow.process_new_pdfs():
        # Step 2: Generate Transcripts
        print("\n=== Step 2: Generating Transcripts ===")
        if workflow.generate_transcripts():
            # Step 3: Create Podcasts
            print("\n=== Step 3: Creating Podcasts ===")
            workflow.create_podcasts()
    
    print("\nWorkflow complete!")

if __name__ == "__main__":
    main() 