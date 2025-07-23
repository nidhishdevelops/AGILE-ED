import requests
from config import Config
import logging
import re
import urllib.parse

logger = logging.getLogger(__name__)

def get_valid_url(url):
    """Resolve URL redirects and validate URLs"""
    if not url or url == "#":
        return ""
    
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.url
    except:
        return url

def clean_text(text):
    """Clean and sanitize text input"""
    if not text:
        return ""
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Remove non-ASCII characters
    text = re.sub(r'\s+', ' ', text).strip()  # Collapse multiple whitespaces
    return text[:300] + "..." if len(text) > 300 else text

def extract_actual_url(search_url):
    """Extract actual URL from Google search results"""
    try:
        if search_url.startswith("/url?q="):
            parsed_url = urllib.parse.urlparse(search_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if 'q' in query_params:
                return query_params['q'][0]
        return search_url
    except:
        return search_url

def search_advancements(topic):
    params = {
        "q": f"latest advancements in {topic} after:2023",
        "api_key": Config.SERPAPI_KEY,
        "engine": "google",
        "num": 5,
        "tbm": "nws",
        "gl": "us",
        "hl": "en"
    }
    
    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=15)
        results = response.json()
        advancements = []
        
        for r in results.get("news_results", [])[:5]:
            link = extract_actual_url(r.get("link", ""))
            valid_url = get_valid_url(link)
            
            advancements.append({
                "title": clean_text(r.get("title", "Untitled")),
                "link": valid_url,
                "source": clean_text(r.get("source", {}).get("name", "Unknown")),
                "date": clean_text(r.get("date", "Date unknown")),
                "summary": clean_text(r.get("snippet", ""))
            })
        return advancements
    except Exception as e:
        logger.error(f"Web search error: {str(e)}")
        return [{
            "title": "Error fetching advancements", 
            "link": "", 
            "source": "System", 
            "summary": "Check SerpAPI config"
        }]

def search_research_papers(topic):
    params = {
        "q": f"{topic} research paper",
        "api_key": Config.SERPAPI_KEY,
        "engine": "google_scholar",
        "num": 5,
        "as_ylo": 2020
    }
    
    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=20)
        results = response.json()
        papers = []
        
        for r in results.get("organic_results", [])[:5]:
            # Extract PDF link
            pdf_link = ""
            for link in r.get("resources", []):
                if "PDF" in link.get("title", ""):
                    pdf_link = get_valid_url(link.get("link", ""))
                    break
            
            # Extract main link
            main_link = extract_actual_url(r.get("link", ""))
            main_link = get_valid_url(main_link)
            
            # Prefer PDF link if available
            paper_link = pdf_link or main_link
            
            papers.append({
                "title": clean_text(r.get("title", "Untitled paper")),
                "link": paper_link,
                "authors": clean_text(", ".join(r.get("publication_info", {}).get("authors", [])) or "Authors unknown"),
                "year": clean_text(r.get("publication_info", {}).get("year", "Year unknown")),
                "summary": clean_text(r.get("snippet", ""))
            })
        return papers
    except Exception as e:
        logger.error(f"Research paper error: {str(e)}")
        return [{
            "title": "Error fetching papers", 
            "link": "", 
            "authors": "System", 
            "summary": "Check SerpAPI config"
        }]

def search_reference_books(topic):
    params = {
        "q": f"{topic} reference book",
        "api_key": Config.SERPAPI_KEY,
        "engine": "google",
        "num": 3,
        "tbm": "bks"
    }
    
    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=15)
        results = response.json()
        books = []
        
        for r in results.get("book_results", [])[:3]:
            # Get direct Amazon/Google Books link
            purchase_link = ""
            for link in r.get("purchase_links", []):
                if "Amazon" in link.get("name", "") or "Google Books" in link.get("name", ""):
                    purchase_link = get_valid_url(link.get("link", ""))
                    break
            
            main_link = extract_actual_url(r.get("link", ""))
            main_link = get_valid_url(main_link)
            
            books.append({
                "title": clean_text(r.get("title", "Untitled book")),
                "link": purchase_link or main_link,
                "authors": clean_text(", ".join(r.get("authors", [])) or "Authors unknown"),
                "year": clean_text(r.get("year", "Year unknown")),
                "description": clean_text(r.get("description", ""))
            })
        return books
    except Exception as e:
        logger.error(f"Book search error: {str(e)}")
        return [{
            "title": "Error fetching books", 
            "link": "", 
            "authors": "System", 
            "description": "Check SerpAPI config"
        }]