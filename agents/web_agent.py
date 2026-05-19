import requests
from config import Config
import logging
import re
import urllib.parse
import threading

logger = logging.getLogger(__name__)
_thread_local = threading.local()
try:
    from utils.result_logger import result_logger
except ImportError:
    class DummyLogger:
        def log_web_content(self, *args, **kwargs): pass
    result_logger = DummyLogger()

def get_valid_url(url):
    if not url or url == "#":
        return ""
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.url
    except:
        return url

def clean_text(text):
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:300] + "..." if len(text) > 300 else text

def extract_actual_url(search_url):
    if not search_url or not isinstance(search_url, str):
        return ""
    try:
        if search_url.startswith("/url?q="):
            parsed_url = urllib.parse.urlparse(search_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if 'q' in query_params:
                return query_params['q'][0]
        return search_url
    except:
        return search_url

def safe_get_source(item):
    """Extract source name safely, handling string or dict."""
    source = item.get('source')
    if source is None:
        return item.get('displayed_link', 'Unknown')
    if isinstance(source, dict):
        return source.get('name', 'Unknown')
    # If source is a string, return it directly
    return str(source)

def safe_get_date(item):
    """Extract date safely."""
    date = item.get('date')
    if date is None:
        return 'Recent'
    return clean_text(str(date))

def safe_iterate(items):
    """Yield only dictionary items."""
    if not items or not isinstance(items, list):
        return
    for item in items:
        if isinstance(item, dict):
            yield item

def search_advancements(topic):
    """Search for recent advancements using news query"""
    if not hasattr(_thread_local, 'logged_advancements'):
        _thread_local.logged_advancements = set()
    
    params = {
        "q": f"{topic} latest news",
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
        
        # Try news_results
        news_items = results.get('news_results')
        if not news_items:
            # Fallback to organic_results
            news_items = results.get('organic_results', [])
        
        for r in safe_iterate(news_items):
            title = r.get('title', '')
            if not title:
                continue
            link = extract_actual_url(r.get('link', ''))
            valid_url = get_valid_url(link)
            advancements.append({
                "title": clean_text(title),
                "link": valid_url,
                "source": safe_get_source(r),
                "date": safe_get_date(r),
                "summary": clean_text(r.get('snippet', ''))
            })
            if len(advancements) >= 5:
                break
        
        if topic not in _thread_local.logged_advancements:
            result_logger.log_web_content("advancements", topic, advancements)
            _thread_local.logged_advancements.add(topic)
        
        return advancements
    except Exception as e:
        logger.error(f"Web search error: {str(e)}")
        return []

def search_research_papers(topic):
    """Search for research papers using Google Scholar"""
    if not hasattr(_thread_local, 'logged_papers'):
        _thread_local.logged_papers = set()
    
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
        
        for r in safe_iterate(results.get('organic_results', [])):
            title = r.get('title', '')
            if not title:
                continue
            # Find PDF link
            pdf_link = ''
            resources = r.get('resources', [])
            if isinstance(resources, list):
                for link in resources:
                    if isinstance(link, dict) and 'PDF' in link.get('title', ''):
                        pdf_link = get_valid_url(link.get('link', ''))
                        break
            
            main_link = extract_actual_url(r.get('link', ''))
            main_link = get_valid_url(main_link)
            paper_link = pdf_link or main_link
            
            pub_info = r.get('publication_info', {})
            authors = []
            if isinstance(pub_info, dict):
                author_list = pub_info.get('authors', [])
                if isinstance(author_list, list):
                    for a in author_list:
                        if isinstance(a, dict) and a.get('name'):
                            authors.append(a['name'])
            year = pub_info.get('year', 'Year unknown') if isinstance(pub_info, dict) else 'Year unknown'
            
            papers.append({
                "title": clean_text(title),
                "link": paper_link,
                "authors": clean_text(", ".join(authors) or "Authors unknown"),
                "year": clean_text(str(year)),
                "summary": clean_text(r.get('snippet', ''))
            })
            if len(papers) >= 5:
                break
        
        if topic not in _thread_local.logged_papers:
            result_logger.log_web_content("research_papers", topic, papers)
            _thread_local.logged_papers.add(topic)
        
        return papers
    except Exception as e:
        logger.error(f"Research paper error: {str(e)}")
        return []

def search_reference_books(topic):
    """Search for reference books using SerpAPI or fallback to Google Books API"""
    if not hasattr(_thread_local, 'logged_books'):
        _thread_local.logged_books = set()
    
    books = []
    
    # First attempt: SerpAPI Google Books tab
    params = {
        "q": f"{topic} textbook OR book",
        "api_key": Config.SERPAPI_KEY,
        "engine": "google",
        "num": 5,
        "tbm": "bks"
    }
    
    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=15)
        results = response.json()
        
        # Try book_results
        book_items = results.get('book_results', [])
        if not book_items:
            # Fallback to organic_results that look like books
            organic = results.get('organic_results', [])
            if isinstance(organic, list):
                for r in organic:
                    if not isinstance(r, dict):
                        continue
                    link = r.get('link', '').lower()
                    title = r.get('title', '').lower()
                    if any(domain in link for domain in ['books.google', 'amazon', 'goodreads', 'springer', 'oreilly', 'packt']) \
                       or any(word in title for word in ['book', 'textbook', 'guide', 'handbook']):
                        book_items.append(r)
                    if len(book_items) >= 3:
                        break
                if not book_items and organic:
                    book_items = organic[:3]
        
        for r in safe_iterate(book_items):
            title = r.get('title', '')
            if not title:
                continue
            purchase_link = ''
            purchase_links = r.get('purchase_links')
            if isinstance(purchase_links, list):
                for pl in purchase_links:
                    if isinstance(pl, dict):
                        name = pl.get('name', '')
                        if 'Amazon' in name or 'Google Books' in name:
                            purchase_link = get_valid_url(pl.get('link', ''))
                            break
            main_link = extract_actual_url(r.get('link', ''))
            main_link = get_valid_url(main_link)
            authors_raw = r.get('authors', [])
            if isinstance(authors_raw, list):
                authors = ', '.join(str(a) for a in authors_raw if a)
            else:
                authors = str(authors_raw) if authors_raw else 'Various'
            books.append({
                "title": clean_text(title),
                "link": purchase_link or main_link,
                "authors": clean_text(authors),
                "year": clean_text(r.get('year', 'Unknown')),
                "description": clean_text(r.get('description', r.get('snippet', '')))
            })
            if len(books) >= 3:
                break
    except Exception as e:
        logger.error(f"SerpAPI book search error: {str(e)}")
    
    # If no books found, fallback to Google Books API (free, no key)
    if not books:
        try:
            # Google Books API search
            gb_url = "https://www.googleapis.com/books/v1/volumes"
            params = {
                "q": f"{topic} machine learning data science",
                "maxResults": 3,
                "printType": "books"
            }
            response = requests.get(gb_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('items', []):
                    volume = item.get('volumeInfo', {})
                    title = volume.get('title', '')
                    if not title:
                        continue
                    authors = ', '.join(volume.get('authors', ['Unknown']))
                    year = volume.get('publishedDate', 'Unknown')[:4]
                    description = volume.get('description', '')
                    link = volume.get('infoLink', '')
                    books.append({
                        "title": clean_text(title),
                        "link": link,
                        "authors": clean_text(authors),
                        "year": year,
                        "description": clean_text(description)[:200]
                    })
                    if len(books) >= 3:
                        break
        except Exception as e:
            logger.error(f"Google Books API fallback error: {str(e)}")
    
    if topic not in _thread_local.logged_books:
        result_logger.log_web_content("reference_books", topic, books)
        _thread_local.logged_books.add(topic)
    
    return books