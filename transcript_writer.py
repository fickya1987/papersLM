import openai
from openai import OpenAI
import pickle
import warnings
import os
from dotenv import load_dotenv
import ast

warnings.filterwarnings('ignore')

# Load environment variables from .env file
load_dotenv()

# System prompt for setting the context
SYSTEM_PROMPT = """You are an AI trained to convert academic papers into engaging podcast transcripts. Create a natural, 10-minute conversation between two speakers discussing the key points, implications, and insights from the provided paper.

Guidelines:
- Start with an introduction of the paper's topic and significance
- Break down complex concepts into digestible explanations
- Include relevant examples and real-world applications
- Discuss methodology and findings
- Address potential implications and future research directions
- Maintain a conversational, engaging tone
- Ensure balanced participation between speakers
- End with key takeaways"""

# Define the JSON schema for structured output
RESPONSE_FORMAT = {
    "type": "object",
    "properties": {
        "conversation": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "speaker": {
                        "type": "string",
                        "enum": ["Speaker 1", "Speaker 2"]
                    },
                    "dialogue": {
                        "type": "string"
                    }
                },
                "required": ["speaker", "dialogue"]
            }
        }
    }
}

def read_file_to_string(filename):
    """Read file content with different encodings."""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except UnicodeDecodeError:
        encodings = ['latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                with open(filename, 'r', encoding=encoding) as file:
                    content = file.read()
                print(f"Successfully read file using {encoding} encoding.")
                return content
            except UnicodeDecodeError:
                continue
        print(f"Error: Could not decode file '{filename}' with any common encoding.")
        return None
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return None
    except IOError:
        print(f"Error: Could not read file '{filename}'.")
        return None

def read_paper(file_path):
    """Read and preprocess the academic paper"""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content

def generate_transcript(input_file, output_file):
    """Generate podcast transcript from academic paper using OpenAI."""
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY environment variable not found")
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        return None
    
    paper_content = read_paper(input_file)
    print(f"Paper content length: {len(paper_content)} characters")
    if len(paper_content) == 0:
        print("Warning: Paper content is empty!")
        return None
    
    print("Sending request to OpenAI...")
    
    # Updated API call with structured output
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""Convert this academic paper into a dialogue following the system guidelines. 
            Structure the output as a JSON object with a 'conversation' array where each entry has 'speaker' (either 'Speaker 1' or 'Speaker 2') 
            and 'dialogue' fields:

            Paper content:
            {paper_content}"""}
        ],
        temperature=0.7,
        max_tokens=4000
    )
    
    # Get the generated text
    generated_text = response.choices[0].message.content
    print(f"Response received. Content length: {len(generated_text) if generated_text else 0}")
    
    if not generated_text:
        print("Warning: Received empty response from OpenAI")
        return None
    
    # Write the response directly to file
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(generated_text)
    
    return generated_text

if __name__ == "__main__":
    input_file = 'cleanedText/clean_testpaper.pdf.txt'
    output_file = 'scripts/transcript.txt'
    
    # Create scripts directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    transcript = generate_transcript(input_file, output_file)
    print(transcript) 