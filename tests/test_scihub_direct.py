from scihub import SciHub
import os

def test_direct_download():
    sh = SciHub()
    sh.base_url = "https://sci-hub.se/"
    
    output_dir = 'test_downloads'
    os.makedirs(output_dir, exist_ok=True)
    
    doi = '10.1038/s41586-021-03549-5'
    result = sh.download(doi, destination=output_dir)
    
    if 'err' in result:
        print(f"Error: {result['err']}")
    else:
        print(f"Successfully downloaded to: {result.get('name')}")

if __name__ == "__main__":
    test_direct_download() 