import PyPDF2
import os
from typing import Optional
from anthropic import Anthropic
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

# Initialize Anthropic client with API key
client = Anthropic(api_key=api_key)

SYS_PROMPT = """
You are a world class text pre-processor. Please parse and return the raw PDF data in a way that is crispy and usable to send to a podcast writer.

Remove or clean up:
- Messy newlines
- LaTeX math
- Unnecessary formatting
- Any details useless for a podcast transcript

Be aggressive with removing technical details but preserve the core meaning.
DO NOT summarize the content, only clean and rewrite when needed.
DO NOT add markdown formatting or special characters.
Start your response directly with the processed text.
"""

def validate_pdf(file_path: str) -> bool:
    if not os.path.exists(file_path):
        print(f"Error: File not found at path: {file_path}")
        return False
    if not file_path.lower().endswith('.pdf'):
        print("Error: File is not a PDF")
        return False
    return True

def extract_text_from_pdf(file_path: str, max_chars: int = 100000) -> Optional[str]:
    # ... existing extract_text_from_pdf function remains unchanged ...
    if not validate_pdf(file_path):
        return None
    
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            print(f"Processing PDF with {num_pages} pages...")
            
            extracted_text = []
            total_chars = 0
            
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                if total_chars + len(text) > max_chars:
                    remaining_chars = max_chars - total_chars
                    extracted_text.append(text[:remaining_chars])
                    print(f"Reached {max_chars} character limit at page {page_num + 1}")
                    break
                
                extracted_text.append(text)
                total_chars += len(text)
                print(f"Processed page {page_num + 1}/{num_pages}")
            
            final_text = '\n'.join(extracted_text)
            print(f"\nExtraction complete! Total characters: {len(final_text)}")
            return final_text
            
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return None

def create_word_bounded_chunks(text: str, target_chunk_size: int) -> list:
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + 1  # +1 for the space
        if current_length + word_length > target_chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def process_chunk(text_chunk: str, chunk_num: int) -> str:
    """Process a chunk of text using Anthropic's Claude API"""
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",  # or other Claude models
            max_tokens=1000,
            temperature=0.7,
            system=SYS_PROMPT,
            messages=[
                {"role": "user", "content": text_chunk}
            ]
        )
        
        processed_text = response.content[0].text.strip()
        
        # Print chunk information for monitoring
        print(f"\nProcessing chunk {chunk_num}:")
        print(f"INPUT TEXT:\n{text_chunk[:200]}...")
        print(f"\nPROCESSED TEXT:\n{processed_text[:200]}...")
        print("=" * 80)
        
        return processed_text
    
    except Exception as e:
        print(f"Error processing chunk {chunk_num}: {str(e)}")
        return text_chunk  # Return original chunk if processing fails

def generate_descriptive_name(text: str) -> str:
    """Generate a descriptive filename using Claude"""
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=50,
            temperature=0.7,
            system="Generate a short, descriptive filename (without extension) for an academic paper. Use only lowercase letters, numbers, and underscores. Maximum 20 characters, 1 or 2 words. The filename should capture the main topic and key focus.",
            messages=[
                {"role": "user", "content": f"Generate a filename for this paper:\n\n{text[:2000]}"}
            ]
        )
        
        filename = response.content[0].text.strip().lower()
        # Clean filename of any invalid characters
        filename = ''.join(c for c in filename if c.isalnum() or c == '_')
        return filename
    
    except Exception as e:
        print(f"Error generating filename: {str(e)}")
        return None

def main(pdf_path: str, chunk_size: int = 1000):
    # Extract text from PDF
    extracted_text = extract_text_from_pdf(pdf_path)
    if not extracted_text:
        return None
    
    # Generate descriptive name
    descriptive_name = generate_descriptive_name(extracted_text)
    if not descriptive_name:
        descriptive_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # Create output filename with descriptive name
    output_dir = "cleanedText"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"clean_{descriptive_name}.txt")
    
    # Process chunks as before
    chunks = create_word_bounded_chunks(extracted_text, chunk_size)
    processed_text = ""
    
    print(f"\nProcessing {len(chunks)} chunks...")
    
    with open(output_file, 'w', encoding='utf-8') as out_file:
        for chunk_num, chunk in enumerate(tqdm(chunks)):
            processed_chunk = process_chunk(chunk, chunk_num)
            processed_text += processed_chunk + "\n"
            out_file.write(processed_chunk + "\n")
            out_file.flush()
    
    print(f"\nProcessing complete!")
    print(f"Output saved to: {output_file}")
    
    return descriptive_name

if __name__ == "__main__":
    main(pdf_path)