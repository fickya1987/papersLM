from openai import OpenAI
import os
from dotenv import load_dotenv
from scihub import SciHub
import time

load_dotenv()

SYSTEM_PROMPT = """You are an expert at converting research interests into effective academic search queries. 
Given a description of research interests or topics, generate 3-5 specific keyword-based search queries that will find relevant academic papers. Focus on conceptual papers, like reviews.

Guidelines:
- Use Boolean operators (AND, OR) and quotation marks for precise searching
- Focus on technical and specific terms used in academic literature
- Keep queries to 2-4 key terms connected with operators
- Format example: "machine learning" AND healthcare
- Format example: "neural networks" AND "computer vision" AND optimization
- Avoid complete sentences or natural language queries
- Each query should target a specific aspect of the research topic"""

class SearchQueryGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.scihub = SciHub()
        self.input_dir = "input"
        os.makedirs(self.input_dir, exist_ok=True)

    def generate_queries(self, research_description):
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Generate keyword-based search queries for: {research_description}"}
            ],
            temperature=0.7
        )
        
        # Clean up the queries by removing numbering and quotes
        queries = response.choices[0].message.content.strip().split('\n')
        cleaned_queries = []
        for q in queries:
            # Remove numbering and leading/trailing whitespace
            q = q.strip()
            q = q.lstrip('123456789.').strip()
            # Keep the quotes and operators in the query
            if q:
                cleaned_queries.append(q)
        
        return cleaned_queries

    def download_papers(self, queries, limit_per_query=1):
        downloaded_files = []
        total_papers_needed = limit_per_query  # Now this is the total papers we want
        
        for query in queries:
            # Stop if we've already downloaded enough papers in total
            if len(downloaded_files) >= total_papers_needed:
                break
            
            print(f"\nSearching for: {query}")
            try:
                results = self.scihub.search(query, limit=1)  # Only search for one at a time
                
                if 'err' in results:
                    print(f"Error in search: {results['err']}")
                    continue
                
                print(f"Found {len(results['papers'])} papers")
                
                for paper in results['papers']:
                    # Stop if we've reached our total limit
                    if len(downloaded_files) >= total_papers_needed:
                        break
                        
                    try:
                        print(f"\nAttempting to download: {paper['name']}")
                        
                        # Generate a safe filename
                        safe_name = "".join(x for x in paper['name'][:50] if x.isalnum() or x in (' ', '-', '_'))
                        filename = f"{safe_name}.pdf"
                        filepath = os.path.join(self.input_dir, filename)
                        
                        # Download the paper
                        result = self.scihub.download(paper['url'], destination=self.input_dir)
                        
                        if 'err' not in result:
                            print(f"Successfully downloaded: {filename}")
                            downloaded_files.append(filepath)
                        else:
                            print(f"Error downloading paper: {result['err']}")
                        
                        # Add delay between downloads
                        time.sleep(3)
                        
                    except Exception as e:
                        print(f"Error downloading paper: {str(e)}")
                        continue
                    
            except Exception as e:
                print(f"Error searching for papers: {str(e)}")
                continue
            
            # Add delay between queries
            time.sleep(5)
        
        return downloaded_files

