from search_generator import SearchQueryGenerator
import time
import random

def test_scihub():
    generator = SearchQueryGenerator()
    
    # Test with a simple query that should work
    test_query = "machine learning nature 2023"
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            print(f"\nAttempt {retry_count + 1} - Testing search with query: {test_query}")
            
            # First test just the search
            results = generator.scihub.search(test_query, limit=2)
            print("\nSearch results:", results)
            
            if 'err' in results:
                print(f"Error in search: {results['err']}")
                retry_count += 1
                wait_time = random.uniform(60, 120)  # Wait between 1-2 minutes
                print(f"Waiting {wait_time:.0f} seconds before retry...")
                time.sleep(wait_time)
                continue
            
            if 'papers' in results and results['papers']:
                # Try to download the first paper
                paper = results['papers'][0]
                print(f"\nAttempting to download: {paper['name']}")
                result = generator.scihub.download(paper['url'], destination='input')
                print("Download result:", result)
                break
            else:
                print("No papers found in search results")
                break
                
        except Exception as e:
            print(f"Error during attempt {retry_count + 1}: {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                wait_time = random.uniform(60, 120)
                print(f"Waiting {wait_time:.0f} seconds before retry...")
                time.sleep(wait_time)
            continue

if __name__ == "__main__":
    test_scihub()