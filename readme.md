# Academic Paper to Podcast Converter

This project automatically converts academic papers (PDFs) into engaging podcast conversations using AI. It processes academic papers, generates natural-sounding dialogue transcripts, and converts them into audio podcasts with multiple speakers.

## Features

- Paper search term generation and PDF download (Work in progress) 
- PDF preprocessing and text extraction
- AI-powered conversion of academic content into natural dialogue
- Text-to-speech generation with distinct voices for different speakers
- Automated workflow management
- Organized file structure for inputs, outputs, and intermediate files

## Prerequisites

- Python 3.8+
- OpenAI API key
- ElevenLabs API key

## Installation

1. Clone the repository:
2. Install required dependencies:
3. Create a `.env` file in the project root with your API keys:

## Project Structure

academic-paper-podcast/
├── input/ # Place PDF files here
├── processed_pdfs/ # Storage for processed PDFs
├── cleanedText/ # Extracted and cleaned text
├── scripts/ # Generated dialogue transcripts
├── used_scripts/ # Archived transcripts
├── outputs/ # Final podcast MP3 files
└── src/
├── main.py
├── pdf_preprocessor.py
├── transcript_writer.py
└── podcast_generator.py

## Usage

1. Place your academic PDF files in the `input/` directory.

2. Run the workflow:
main.py

The workflow will:
- Process all PDFs in the input directory
- Generate conversational transcripts
- Create podcast audio files with multiple speakers

## Configuration

- Voice settings can be adjusted in `podcast_generator.py`
- Conversation style and guidelines can be modified in `transcript_writer.py`
- Workflow settings can be customized in `main.py`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Add your chosen license]

## Acknowledgments

- OpenAI GPT-4 for transcript generation
- ElevenLabs for text-to-speech conversion
- scihub.py by zaytoun https://github.com/zaytoun/scihub.py