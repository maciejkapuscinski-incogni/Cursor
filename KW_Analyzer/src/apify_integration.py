"""Apify integration module for web scraping."""
import requests
import logging
from typing import Optional, Dict, List
import time

from src.config import Config

logger = logging.getLogger(__name__)


class ApifyScraper:
    """Web scraper using Apify API."""
    
    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize Apify scraper.
        
        Args:
            api_token: Apify API token (defaults to config)
        """
        self.api_token = api_token or Config.APIFY_API_TOKEN
        if not self.api_token:
            logger.warning("Apify API token not provided")
        
        self.base_url = "https://api.apify.com/v2"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        })
    
    def scrape_url(self, url: str, actor_id: str = "apify/website-content-crawler") -> Optional[Dict[str, str]]:
        """
        Scrape content from a URL using Apify.
        
        Args:
            url: URL to scrape
            actor_id: Apify actor ID to use
            
        Returns:
            Dictionary with title and content, or None if failed
        """
        if not self.api_token:
            logger.error("Apify API token is required")
            return None
        
        try:
            # Start actor run
            run_response = self.session.post(
                f"{self.base_url}/acts/{actor_id}/runs",
                json={
                    "startUrls": [{"url": url}],
                    "maxCrawlPages": 1,
                    "maxCrawlDepth": 1
                }
            )
            run_response.raise_for_status()
            run_data = run_response.json()
            run_id = run_data['data']['id']
            
            logger.info(f"Started Apify run {run_id} for {url}")
            
            # Wait for run to complete
            max_wait = 300  # 5 minutes max
            wait_time = 0
            while wait_time < max_wait:
                status_response = self.session.get(
                    f"{self.base_url}/actor-runs/{run_id}"
                )
                status_response.raise_for_status()
                status_data = status_response.json()['data']
                
                if status_data['status'] == 'SUCCEEDED':
                    # Get results
                    results_response = self.session.get(
                        f"{self.base_url}/actor-runs/{run_id}/dataset/items"
                    )
                    results_response.raise_for_status()
                    results = results_response.json()
                    
                    if results and len(results) > 0:
                        result = results[0]
                        return {
                            'url': url,
                            'title': result.get('title', 'No title'),
                            'content': result.get('text', result.get('html', 'No content')),
                            'status_code': 200
                        }
                    break
                elif status_data['status'] in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                    logger.error(f"Apify run failed with status: {status_data['status']}")
                    break
                
                time.sleep(5)
                wait_time += 5
            
            logger.warning(f"Apify run did not complete in time for {url}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Apify API error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error using Apify for {url}: {e}")
            return None
    
    def scrape_urls(self, urls: List[str], actor_id: str = "apify/website-content-crawler") -> List[Dict[str, str]]:
        """
        Scrape multiple URLs using Apify.
        
        Args:
            urls: List of URLs to scrape
            actor_id: Apify actor ID to use
            
        Returns:
            List of scraping results
        """
        results = []
        for url in urls:
            result = self.scrape_url(url, actor_id)
            if result:
                results.append(result)
        return results

