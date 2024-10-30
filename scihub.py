# -*- coding: utf-8 -*-

"""
Sci-API Unofficial API
[Search|Download] research papers from [scholar.google.com|sci-hub.io].

@author zaytoun
"""

import re
import argparse
import hashlib
import logging
import os
import random
import time
import urllib.parse

import requests
import urllib3
from bs4 import BeautifulSoup
from retrying import retry
from fake_useragent import UserAgent

# log config
logging.basicConfig()
logger = logging.getLogger('Sci-Hub')
logger.setLevel(logging.DEBUG)

#
urllib3.disable_warnings()

# constants
SCHOLARS_BASE_URL = 'https://scholar.google.com/scholar'
USER_AGENT = UserAgent()
BASE_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

class SciHub(object):
    """
    SciHub class can search for papers on Google Scholars 
    and fetch/download papers from sci-hub.io
    """

    def __init__(self):
        self.sess = requests.Session()
        self.sess.headers = self._get_random_headers()
        self.available_base_url_list = self._get_available_scihub_urls()
        self.base_url = self.available_base_url_list[0] + '/'
        self.proxy_list = [
            'socks5h://127.0.0.1:9050',  # Tor proxy if available
            # Add your proxies here
        ]
        self.current_proxy_index = 0
        self.max_retries = 3
        self.retry_delay = 30
        self.captcha_wait = 60  # seconds to wait when CAPTCHA is encountered

    def _get_random_headers(self):
        """Generate random headers for each request"""
        headers = BASE_HEADERS.copy()
        headers['User-Agent'] = USER_AGENT.random
        return headers

    def _get_available_scihub_urls(self):
        '''
        Finds available scihub urls via https://sci-hub.now.sh/
        '''
        urls = []
        res = requests.get('https://sci-hub.now.sh/')
        s = self._get_soup(res.content)
        for a in s.find_all('a', href=True):
            if 'sci-hub.' in a['href']:
                urls.append(a['href'])
        return urls

    def set_proxy(self, proxy):
        '''
        set proxy for session
        :param proxy_dict:
        :return:
        '''
        if proxy:
            self.sess.proxies = {
                "http": proxy,
                "https": proxy, }

    def _change_base_url(self):
        if not self.available_base_url_list:
            raise Exception('Ran out of valid sci-hub urls')
        del self.available_base_url_list[0]
        self.base_url = self.available_base_url_list[0] + '/'
        logger.info("I'm changing to {}".format(self.available_base_url_list[0]))

    def search(self, query, limit=10, download=False):
        """
        Performs a query on scholar.google.com, and returns a dictionary
        of results in the form {'papers': ...}
        """
        print(f"Searching Google Scholar for: {query}")
        start = 0
        results = {'papers': []}

        while True:
            try:
                # Add random delay between requests
                time.sleep(random.uniform(2, 5))
                
                # Update headers for each request
                self.sess.headers = self._get_random_headers()
                
                search_url = f"{SCHOLARS_BASE_URL}?q={query}&start={start}"
                print(f"Requesting URL: {search_url}")
                
                # Add parameters to avoid bot detection
                params = {
                    'q': query,
                    'start': start,
                    'hl': 'en',
                    'as_sdt': '0,5'
                }
                
                res = self.sess.get(
                    SCHOLARS_BASE_URL,
                    params=params,
                    timeout=30
                )
                
                print(f"Response status code: {res.status_code}")
                
                if res.status_code == 429:
                    print("Rate limit reached. Waiting 60 seconds...")
                    time.sleep(60)
                    continue
                
                if res.status_code != 200:
                    print(f"Error response content: {res.content}")
                    results['err'] = f'Search failed with status code {res.status_code}'
                    return results

                s = self._get_soup(res.content)
                papers = s.find_all('div', class_="gs_r")

                if not papers:
                    if 'CAPTCHA' in str(res.content):
                        results['err'] = 'Failed to complete search with query %s (captcha)' % query
                    return results

                for paper in papers:
                    if not paper.find('table'):
                        source = None
                        pdf = paper.find('div', class_='gs_ggs gs_fl')
                        link = paper.find('h3', class_='gs_rt')

                        if pdf:
                            source = pdf.find('a')['href']
                        elif link.find('a'):
                            source = link.find('a')['href']
                        else:
                            continue

                        results['papers'].append({
                            'name': link.text,
                            'url': source
                        })

                        if len(results['papers']) >= limit:
                            return results

                start += 10

            except requests.exceptions.RequestException as e:
                results['err'] = 'Failed to complete search with query %s (connection error)' % query
                return results

    @retry(wait_random_min=100, wait_random_max=1000, stop_max_attempt_number=10)
    def download(self, identifier, destination='', path=None):
        """
        Downloads a paper from sci-hub given an indentifier (DOI, PMID, URL).
        Currently, this can potentially be blocked by a captcha if a certain
        limit has been reached.
        """
        data = self.fetch(identifier)

        if not data.get('pdf'):
            return {'err': 'Failed to fetch PDF for the paper'}
            
        if not path:
            path = os.path.join(destination, data['name'])
        
        # Clean up the filename
        path = path.replace('?download=true', '')  # Remove download parameter
        if not path.endswith('.pdf'):
            path += '.pdf'
        
        # Verify we have PDF content
        if data['pdf'].startswith(b'%PDF-'):
            self._save(data['pdf'], path)
            return {'name': os.path.basename(path)}
        else:
            return {'err': 'Downloaded content is not a valid PDF'}

    def fetch(self, identifier):
        """
        Fetches the paper by first retrieving the direct link to the pdf.
        """
        for attempt in range(self.max_retries):
            try:
                url = self._get_direct_url(identifier)
                if not url:
                    return {'err': f'Unable to find valid URL for identifier: {identifier}'}
                    
                res = self.sess.get(url, verify=False, timeout=30)

                if not res.headers.get('Content-Type', '').startswith('application/pdf'):
                    if 'captcha' in res.text.lower():
                        if not self._handle_captcha():
                            return {'err': 'Failed to bypass CAPTCHA'}
                        continue
                    return {'err': f'Response is not a PDF (Content-Type: {res.headers.get("Content-Type")})'}
                
                return {
                    'pdf': res.content,
                    'url': url,
                    'name': self._generate_name(res)
                }

            except requests.exceptions.RequestException as e:
                logger.error(f'Request failed: {str(e)}')
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return {'err': f'Failed to fetch PDF after {self.max_retries} attempts'}

        return {'err': 'Maximum retries exceeded'}

    def _get_direct_url(self, identifier):
        """
        Finds the direct source url for a given identifier.
        """
        id_type = self._classify(identifier)

        return identifier if id_type == 'url-direct' \
            else self._search_direct_url(identifier)

    def _search_direct_url(self, identifier):
        """
        Enhanced version of _search_direct_url that handles HTML pages and ScienceDirect URLs
        """
        try:
            # Handle ScienceDirect URLs specifically
            if 'sciencedirect.com' in identifier:
                # Extract the article ID and construct direct PDF URL
                article_id = identifier.split('/')[-1]
                return f"https://pdf.sciencedirectassets.com/article/{article_id}/pdf"
                
            # Handle HTML pages
            if '[HTML]' in identifier:
                # Strip HTML tags and clean URL
                identifier = identifier.replace('[HTML]', '').strip()
                
            # Validate and clean the URL first
            if not identifier:
                logger.info("Empty identifier provided")
                return None
                
            # Handle DOI-style identifiers
            if identifier.startswith('10.'):
                identifier = f"https://doi.org/{identifier}"
                
            # Ensure URL has scheme
            if not identifier.startswith(('http://', 'https://')):
                if identifier.startswith('www.'):
                    identifier = f"https://{identifier}"
                else:
                    identifier = f"https://www.{identifier}"

            # Add timeout and better error handling
            res = self.sess.get(
                self.base_url + identifier, 
                headers=self._get_random_headers(),
                verify=False,
                timeout=30
            )
            
            if res.status_code != 200:
                logger.info(f"Failed to fetch URL with status code: {res.status_code}")
                # Try alternative methods for known publishers
                alt_url = self._try_alternative_sources(identifier)
                if alt_url:
                    return alt_url
                return None
                
            s = self._get_soup(res.content)
            
            # Try multiple methods to find PDF URL
            pdf_url = None
            
            # Method 1: iframe
            iframe = s.find('iframe')
            if iframe and iframe.get('src'):
                pdf_url = iframe.get('src')
                
            # Method 2: embed
            if not pdf_url:
                embed = s.find('embed')
                if embed and embed.get('src'):
                    pdf_url = embed.get('src')
            
            # Method 3: regex patterns
            if not pdf_url:
                patterns = [
                    r'iframe src="(.*?)"',
                    r"location.href='(.*?)'",
                    r'pdf_url\s*=\s*[\'"]([^\'"]+)[\'"]',
                    r'<embed src="(.*?)"'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, res.text)
                    if matches:
                        pdf_url = matches[0]
                        break
            
            if pdf_url:
                return self._clean_pdf_url(pdf_url)
                
            logger.info(f"No PDF URL found for identifier: {identifier}")
            return None
            
        except Exception as e:
            logger.error(f"Error in _search_direct_url: {str(e)}")
            return None

    def _try_alternative_sources(self, url):
        """Try alternative methods to get PDF for known publishers"""
        known_publishers = {
            'sciencedirect.com': self._handle_sciencedirect,
            'ncbi.nlm.nih.gov': self._handle_pubmed,
            'springer.com': self._handle_springer
            # Add more publishers as needed
        }
        
        for domain, handler in known_publishers.items():
            if domain in url:
                return handler(url)
        return None

    def _handle_sciencedirect(self, url):
        """Handle ScienceDirect articles specifically"""
        try:
            # First try to get the article through Sci-Hub
            article_id = url.split('/')[-1]
            doi_url = f"https://doi.org/10.1016/j.{article_id}"
            return self._get_direct_url(doi_url)
        except:
            return None

    def _clean_pdf_url(self, pdf_url):
        """Clean and construct proper PDF URL"""
        if pdf_url.startswith('/'):
            base_domain = urllib.parse.urlparse(self.base_url).netloc
            return f"https://{base_domain}{pdf_url}"
        elif pdf_url.startswith('//'):
            return 'https:' + pdf_url
        elif not pdf_url.startswith('http'):
            base_domain = urllib.parse.urlparse(self.base_url).netloc
            return f"https://{base_domain}/{pdf_url.lstrip('/')}"
        return pdf_url

    def _clean_pdf_url(self, pdf_url):
        """Clean and construct proper PDF URL"""
        if pdf_url.startswith('/'):
            base_domain = urllib.parse.urlparse(self.base_url).netloc
            return f"https://{base_domain}{pdf_url}"
        elif pdf_url.startswith('//'):
            return 'https:' + pdf_url
        elif not pdf_url.startswith('http'):
            base_domain = urllib.parse.urlparse(self.base_url).netloc
            return f"https://{base_domain}/{pdf_url.lstrip('/')}"
        return pdf_url

    def _classify(self, identifier):
        """
        Classify the type of identifier:
        url-direct - openly accessible paper
        url-non-direct - pay-walled paper
        pmid - PubMed ID
        doi - digital object identifier
        """
        if (identifier.startswith('http') or identifier.startswith('https')):
            if identifier.endswith('pdf'):
                return 'url-direct'
            else:
                return 'url-non-direct'
        elif identifier.isdigit():
            return 'pmid'
        else:
            return 'doi'

    def _save(self, data, path):
        """
        Save a file give data and a path.
        """
        with open(path, 'wb') as f:
            f.write(data)

    def _get_soup(self, html):
        """
        Return html soup.
        """
        return BeautifulSoup(html, 'html.parser')

    def _generate_name(self, res):
        """
        Generate unique filename for paper. Returns a name by calcuating 
        md5 hash of file contents, then appending the last 20 characters
        of the url which typically provides a good paper identifier.
        """
        name = res.url.split('/')[-1]
        name = re.sub('#view=(.+)', '', name)
        pdf_hash = hashlib.md5(res.content).hexdigest()
        return '%s-%s' % (pdf_hash, name[-20:])

    def _rotate_proxy(self):
        """Rotate to next proxy in the list"""
        if self.proxy_list:
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
            new_proxy = self.proxy_list[self.current_proxy_index]
            self.set_proxy(new_proxy)
            logger.info(f"Rotating to proxy: {new_proxy}")

    def fetch(self, identifier):
        """
        Fetches the paper by first retrieving the direct link to the pdf.
        """
        max_retries = 3
        retry_delay = 30  # Initial delay in seconds
        
        for attempt in range(max_retries):
            try:
                url = self._get_direct_url(identifier)
                res = self.sess.get(url, verify=False)

                if res.headers['Content-Type'] != 'application/pdf':
                    if 'captcha' in res.text.lower():
                        self._rotate_proxy()  # Try a different proxy
                        logger.info(f'Encountered CAPTCHA. Attempt {attempt + 1}/{max_retries}')
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                            logger.info(f'Waiting {wait_time} seconds before retrying...')
                            time.sleep(wait_time)
                            self._change_base_url()  # Try a different mirror
                            continue
                        
                    raise CaptchaNeedException('Failed to fetch pdf due to captcha')
                
                return {
                    'pdf': res.content,
                    'url': url,
                    'name': self._generate_name(res)
                }

            except requests.exceptions.ConnectionError:
                logger.info('Cannot access {}, changing url'.format(self.available_base_url_list[0]))
                self._change_base_url()

            except requests.exceptions.RequestException as e:
                logger.info('Failed to fetch pdf: %s' % str(e))
                return {'err': 'Failed to fetch pdf due to request exception'}

        return {'err': 'Failed to fetch pdf after maximum retries'}

    def _handle_captcha(self):
        """Handle CAPTCHA encounter"""
        logger.info(f"CAPTCHA detected. Waiting {self.captcha_wait} seconds...")
        time.sleep(self.captcha_wait)
        self._rotate_proxy()
        self._change_base_url()
        return True

class CaptchaNeedException(Exception):
    pass

def main():
    sh = SciHub()
    sh.proxy_list = [
        'socks5://proxy1:port',
        'socks5://proxy2:port',
        # Add more proxies...
    ]

    parser = argparse.ArgumentParser(description='SciHub - To remove all barriers in the way of science.')
    parser.add_argument('-d', '--download', metavar='(DOI|PMID|URL)', help='tries to find and download the paper',
                        type=str)
    parser.add_argument('-f', '--file', metavar='path', help='pass file with list of identifiers and download each',
                        type=str)
    parser.add_argument('-s', '--search', metavar='query', help='search Google Scholars', type=str)
    parser.add_argument('-sd', '--search_download', metavar='query',
                        help='search Google Scholars and download if possible', type=str)
    parser.add_argument('-l', '--limit', metavar='N', help='the number of search results to limit to', default=10,
                        type=int)
    parser.add_argument('-o', '--output', metavar='path', help='directory to store papers', default='', type=str)
    parser.add_argument('-v', '--verbose', help='increase output verbosity', action='store_true')
    parser.add_argument('-p', '--proxy', help='via proxy format like socks5://user:pass@host:port', action='store', type=str)

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    if args.proxy:
        sh.set_proxy(args.proxy)

    if args.download:
        result = sh.download(args.download, args.output)
        if 'err' in result:
            logger.debug('%s', result['err'])
        else:
            logger.debug('Successfully downloaded file with identifier %s', args.download)
    elif args.search:
        results = sh.search(args.search, args.limit)
        if 'err' in results:
            logger.debug('%s', results['err'])
        else:
            logger.debug('Successfully completed search with query %s', args.search)
        print(results)
    elif args.search_download:
        results = sh.search(args.search_download, args.limit)
        if 'err' in results:
            logger.debug('%s', results['err'])
        else:
            logger.debug('Successfully completed search with query %s', args.search_download)
            for paper in results['papers']:
                result = sh.download(paper['url'], args.output)
                if 'err' in result:
                    logger.debug('%s', result['err'])
                else:
                    logger.debug('Successfully downloaded file with identifier %s', paper['url'])
    elif args.file:
        with open(args.file, 'r') as f:
            identifiers = f.read().splitlines()
            for identifier in identifiers:
                result = sh.download(identifier, args.output)
                if 'err' in result:
                    logger.debug('%s', result['err'])
                else:
                    logger.debug('Successfully downloaded file with identifier %s', identifier)


if __name__ == '__main__':
    main()