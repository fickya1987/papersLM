import streamlit as st
from main import PodcastWorkflow
import os
from pathlib import Path

def initialize_session_state():
    if 'workflow' not in st.session_state:
        st.session_state.workflow = None
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'testing_mode' not in st.session_state:
        st.session_state.testing_mode = False
    if 'llm_choice' not in st.session_state:
        st.session_state.llm_choice = "OpenAI"
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = ""
    if 'anthropic_api_key' not in st.session_state:
        st.session_state.anthropic_api_key = ""
    if 'elevenlabs_api_key' not in st.session_state:
        st.session_state.elevenlabs_api_key = ""

def main():
    st.title("Research Paper Podcast Generator")
    
    initialize_session_state()
    
    # Testing mode toggle
    testing_mode = st.toggle(
        "Testing Mode (Skip API Validation)", 
        value=st.session_state.testing_mode,
        help="Enable this to bypass API key requirements during testing"
    )
    st.session_state.testing_mode = testing_mode
    
    # LLM choice (moved outside the expander)
    llm_choice = st.radio(
        "Select Language Model",
        options=["OpenAI", "Anthropic"],
        horizontal=True,
        help="Choose which LLM to use for processing",
        key="llm_choice"
    )
    
    # API Keys section
    with st.expander("API Settings", expanded=not testing_mode):
        col1, col2, col3 = st.columns(3)
        with col1:
            openai_key = st.text_input(
                "OpenAI API Key",
                type="password",
                value=st.session_state.openai_api_key,
                help="Enter your OpenAI API key"
            )
        with col2:
            anthropic_key = st.text_input(
                "Anthropic API Key",
                type="password",
                value=st.session_state.anthropic_api_key,
                help="Enter your Anthropic API key"
            )
        with col3:
            elevenlabs_key = st.text_input(
                "ElevenLabs API Key",
                type="password",
                value=st.session_state.elevenlabs_api_key,
                help="Enter your ElevenLabs API key"
            )

        if not testing_mode:
            # Only show API validation when not in testing mode
            required_keys_present = (
                (llm_choice == "OpenAI" and st.session_state.openai_api_key) or
                (llm_choice == "Anthropic" and st.session_state.anthropic_api_key)
            ) and st.session_state.elevenlabs_api_key

            if not required_keys_present:
                st.warning("Please enter the required API keys before proceeding.")
                return

    # Remove sidebar and move slider to main content
    papers_count = st.slider(
        "Papers per search query",
        min_value=1,
        max_value=5,
        value=2,
        help="Number of papers to download for each generated search query"
    )
    
    if st.button("Initialize Workflow"):
        st.session_state.workflow = PodcastWorkflow(papers_per_query=papers_count)
        st.success("Workflow initialized!")

    # Main content
    if st.session_state.workflow is None:
        st.info("Please initialize the workflow using the button above.")
        return

    # Research interests input
    research_description = st.text_area(
        "Describe your research interests or topics",
        height=100,
        help="Enter keywords or a description of the research topics you're interested in"
    )

    # Process button
    if st.button("Generate Podcasts"):
        if not research_description:
            st.error("Please enter research interests before proceeding.")
            return

        with st.spinner("Generating search queries and downloading papers..."):
            if st.session_state.workflow.generate_search_and_download(research_description):
                st.success("Papers downloaded successfully!")
                
                with st.spinner("Processing PDFs..."):
                    processed_names = st.session_state.workflow.process_new_pdfs()
                    if processed_names:
                        st.success("PDFs processed successfully!")
                        
                        with st.spinner("Generating transcripts..."):
                            if st.session_state.workflow.generate_transcripts():
                                st.success("Transcripts generated successfully!")
                                
                                with st.spinner("Creating podcasts..."):
                                    if st.session_state.workflow.create_podcasts():
                                        st.success("Podcasts created successfully!")
                                        st.session_state.processing_complete = True
                            else:
                                st.error("Failed to generate transcripts.")
                    else:
                        st.error("No PDFs were successfully processed.")
            else:
                st.error("Failed to download papers.")

    # Display results
    if st.session_state.processing_complete:
        st.header("Results")
        
        # Show successful downloads
        if st.session_state.workflow.successful_downloads:
            st.subheader("Successfully Downloaded Papers")
            for paper in st.session_state.workflow.successful_downloads:
                st.write(f"- {paper}")

        # Show failed downloads
        if st.session_state.workflow.failed_downloads:
            st.subheader("Failed Downloads")
            for query, error in st.session_state.workflow.failed_downloads:
                st.write(f"- Query: {query}")
                st.write(f"  Error: {error}")

        # Display generated podcasts
        output_dir = Path(os.getcwd()) / "outputs"
        podcast_files = list(output_dir.glob("*.mp3"))
        
        if podcast_files:
            st.subheader("Generated Podcasts")
            for podcast in podcast_files:
                # Extract title from filename (removing .mp3 extension)
                title = podcast.stem.replace('_', ' ').title()
                
                # Create a container for each podcast
                with st.container():
                    st.write(f"**{title}**")
                    with open(podcast, "rb") as f:
                        st.audio(f.read(), format="audio/mp3")
                    st.divider()  # Add a visual separator between podcasts

if __name__ == "__main__":
    main()