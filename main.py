import os
from pathlib import Path
import shutil
from pdf_preprocessor import main as preprocess_pdf
from transcript_writer import generate_transcript
from podcast_generator import PodcastGenerator
from search_generator import SearchQueryGenerator
import time
import random

class PodcastWorkflow:
    def __init__(
        self, 
        papers_per_query=2, 
        openai_api_key=None, 
        anthropic_api_key=None,
        elevenlabs_api_key=None,
        llm_provider="openai"
    ):
        # Define directory structure
        self.base_dir = Path(os.getcwd())
        self.input_dir = self.base_dir / "input"
        self.processed_pdfs_dir = self.base_dir / "processed_pdfs"
        self.cleaned_text_dir = self.base_dir / "cleanedText"
        self.scripts_dir = self.base_dir / "scripts"
        self.used_scripts_dir = self.base_dir / "used_scripts"
        self.output_dir = self.base_dir / "outputs"
        self.finished_text_dir = self.base_dir / "finished_text"
        
        # Create all necessary directories
        self._setup_directories()
        
        # Initialize search generator with papers_per_query
        self.papers_per_query = papers_per_query
        self.search_generator = SearchQueryGenerator()
        
        # Track downloads for reporting
        self.failed_downloads = []
        self.successful_downloads = []
        
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
        self.elevenlabs_api_key = elevenlabs_api_key
        self.llm_provider = llm_provider
    
    def _setup_directories(self):
        """Create all required directories if they don't exist"""
        for directory in [self.input_dir, self.processed_pdfs_dir, 
                         self.cleaned_text_dir, self.scripts_dir, 
                         self.used_scripts_dir, self.output_dir,
                         self.finished_text_dir]:
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
                
                # Move transcript to used_scripts
                shutil.move(str(transcript_file), 
                          str(self.used_scripts_dir / f"used_{descriptive_name}.txt"))
                print(f"Moved used script to: {self.used_scripts_dir / f'used_{descriptive_name}.txt'}")
                
                # Move cleaned text to finished folder
                cleaned_text_file = self.cleaned_text_dir / f"clean_{descriptive_name}.txt"
                if cleaned_text_file.exists():
                    shutil.move(str(cleaned_text_file), 
                              str(self.finished_text_dir / f"finished_{descriptive_name}.txt"))
                    print(f"Moved cleaned text to: {self.finished_text_dir / f'finished_{descriptive_name}.txt'}")
            
            except Exception as e:
                print(f"Error generating podcast for {descriptive_name}: {str(e)}")
                continue
        
        return True

    def cleanup_processed_files(self):
        """Optional: Clean up processed text files"""
        # Add any additional cleanup steps here if needed
        pass

    def generate_search_and_download(self, research_description):
        """Generate search queries and download papers"""
        print("\nGenerating search queries...")
        queries = self.search_generator.generate_queries(research_description)
        
        if not queries:
            print("Failed to generate valid search queries.")
            return False
            
        print("\nGenerated queries:")
        for i, query in enumerate(queries, 1):
            print(f"{i}. {query}")
        
        print(f"\nAttempting to download {self.papers_per_query} papers per query...")
        papers_downloaded = 0  # Add counter for downloaded papers
        
        for query in queries:
            # If we've already downloaded enough papers, break
            if papers_downloaded >= self.papers_per_query:
                break
                
            try:
                result = self.search_generator.download_papers(
                    [query], 
                    limit_per_query=self.papers_per_query - papers_downloaded  # Adjust limit
                )
                
                if result:
                    self.successful_downloads.extend(result)
                    papers_downloaded += len(result)
                
            except Exception as e:
                self.failed_downloads.append((query, str(e)))
                print(f"\nFailed to download papers for query: {query}")
                print(f"Error: {str(e)}")
            
            # Add small delay between queries if we need more papers
            if papers_downloaded < self.papers_per_query:
                time.sleep(random.uniform(2, 5))
        
        # Report results
        if self.successful_downloads:
            print(f"\nSuccessfully downloaded {len(self.successful_downloads)} papers:")
            for paper in self.successful_downloads:
                print(f"- {paper}")
        
        if self.failed_downloads:
            print(f"\nFailed to download papers for {len(self.failed_downloads)} queries:")
            for query, error in self.failed_downloads:
                print(f"- Query: {query}")
                print(f"  Error: {error}")
        
        # Return True if we got any papers at all
        return bool(self.successful_downloads)

def main():
    # Get number of papers from user
    while True:
        try:
            papers_count = int(input("\nHow many papers would you like to download per search query? (1-5): "))
            if 1 <= papers_count <= 5:
                break
            print("Please enter a number between 1 and 5.")
        except ValueError:
            print("Please enter a valid number.")

    workflow = PodcastWorkflow(papers_per_query=papers_count)
    
    print("\nStarting podcast generation workflow...")
    
    try:
        # Get research description and download papers
        research_description = input("\nPlease describe your research interests or topics:\n")
        print("\n=== Step 0: Generating Searches and Downloading Papers ===")
        
        if workflow.generate_search_and_download(research_description):
            # Step 1: Process PDFs
            print("\n=== Step 1: Processing PDFs ===")
            processed_names = workflow.process_new_pdfs()
            if processed_names:  # Changed condition
                # Step 2: Generate Transcripts
                print("\n=== Step 2: Generating Transcripts ===")
                if workflow.generate_transcripts():
                    # Step 3: Create Podcasts
                    print("\n=== Step 3: Creating Podcasts ===")
                    workflow.create_podcasts()
            else:
                print("\nNo PDFs were successfully processed. Workflow cannot continue.")
        else:
            print("\nNo papers were successfully downloaded. Workflow cannot continue.")
    
    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user.")
    except Exception as e:
        print(f"\n\nAn unexpected error occurred: {str(e)}")
    finally:
        print("\nWorkflow complete!")
        
        # Final summary
        if hasattr(workflow, 'successful_downloads'):
            print(f"\nTotal successful downloads: {len(workflow.successful_downloads)}")
        if hasattr(workflow, 'failed_downloads'):
            print(f"Total failed downloads: {len(workflow.failed_downloads)}")

if __name__ == "__main__":
    main() 