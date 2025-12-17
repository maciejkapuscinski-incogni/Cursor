"""Web scraping module."""
import requests
from bs4 import BeautifulSoup
import logging
from typing import Optional, Dict
from urllib.parse import urljoin, urlparse
import time

logger = logging.getLogger(__name__)


class WebScraper:
    """Web scraper using BeautifulSoup."""
    
    def __init__(self, timeout: int = 10, delay: float = 1.0):
        """
        Initialize web scraper.
        
        Args:
            timeout: Request timeout in seconds
            delay: Delay between requests in seconds
        """
        self.timeout = timeout
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        logger.info("Web scraper initialized")
    
    def scrape_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        Scrape content from a URL.
        
        Args:
            url: URL to scrape
            
        Returns:
            Dictionary with title and content, or None if failed
        """
        try:
            time.sleep(self.delay)  # Rate limiting
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extract title
            title = None
            if soup.title:
                title = soup.title.get_text().strip()
            elif soup.find('h1'):
                title = soup.find('h1').get_text().strip()
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract main content
            content = None
            
            # Try to find main content areas
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
            
            if main_content:
                content = main_content.get_text(separator=' ', strip=True)
            else:
                # Fallback to body text
                body = soup.find('body')
                if body:
                    content = body.get_text(separator=' ', strip=True)
            
            # Clean up content
            if content:
                # Remove extra whitespace
                content = ' '.join(content.split())
                # Limit content length
                if len(content) > 50000:
                    content = content[:50000] + "..."
            
            result = {
                'url': url,
                'title': title or 'No title',
                'content': content or 'No content extracted',
                'status_code': response.status_code
            }
            
            logger.info(f"Successfully scraped: {url}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error scraping {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
    
    def scrape_urls(self, urls: list, max_workers: int = 1) -> list:
        """
        Scrape multiple URLs.
        
        Args:
            urls: List of URLs to scrape
            max_workers: Number of concurrent workers (currently sequential)
            
        Returns:
            List of scraping results
        """
        results = []
        for url in urls:
            result = self.scrape_url(url)
            if result:
                results.append(result)
        return results

