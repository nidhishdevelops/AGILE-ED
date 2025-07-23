from agents import content_router, rag_agent, web_agent, youtube_search, email_agent
import json
from config import Config
import logging
import re
from datetime import datetime
import concurrent.futures

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('app.log')]
)
logger = logging.getLogger(__name__)

def handle_query(user_query):
    routing_info = content_router.determine_module_and_style(user_query)
    logger.info(f"Routing Info: {routing_info}")
    
    if not routing_info.get("in_domain", True):
        subject = f"Out-of-Domain: {routing_info['topic']}"
        body = f"Query: {user_query}\nTopic outside data science domain"
        email_sent = email_agent.send_notification(subject, body) if Config.EMAIL_PASSWORD else False
        
        message = "This topic is outside our data science domain."
        if email_sent:
            message += " We've notified our team!"
        return {
            "status": "domain_error",
            "message": message,
            "query": user_query,
            "topic": routing_info["topic"]
        }
    
    rag_result = rag_agent.retrieve_and_generate(
        routing_info["module"],
        routing_info["topic"],
        routing_info["style"]
    )
    
    if rag_result.get("response") == "TOPIC_NOT_FOUND":
        subject = f"Missing Content: {routing_info['topic']}"
        body = f"Query: {user_query}\nModule: {routing_info['module']}"
        email_sent = email_agent.send_notification(subject, body) if Config.EMAIL_PASSWORD else False
        
        message = "This topic isn't in our system yet."
        if email_sent:
            message += " We've notified our team!"
        return {
            "status": "error",
            "message": message,
            "query": user_query,
            "topic": routing_info["topic"]
        }
    
    # Run web searches in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_advancements = executor.submit(web_agent.search_advancements, routing_info["topic"])
        future_papers = executor.submit(web_agent.search_research_papers, routing_info["topic"])
        future_videos = executor.submit(youtube_search.search_youtube_videos, routing_info["topic"])
        future_books = executor.submit(web_agent.search_reference_books, routing_info["topic"])
        
        advancements = future_advancements.result()
        research_papers = future_papers.result()
        videos = future_videos.result()
        reference_books_web = future_books.result()
    
    return {
        "status": "success",
        "query": user_query,
        "topic": routing_info["topic"],
        "module": routing_info["module"],
        "learning_style": routing_info["style"],
        "explanation": rag_result["response"],
        "sources": rag_result["sources"],
        "llm_used": rag_result["llm_source"],
        "recent_advancements": advancements,
        "research_papers": research_papers,
        "video_recommendations": videos,
        "reference_books_web": reference_books_web
    }

def format_section(title, content):
    return f"\n\033[1;34m{title}:\033[0m\n{content}\n"

def print_response(response):
    if response["status"] != "success":
        print(f"\n\033[1;31m⚠️ {response['message']}\033[0m")
        return
    
    print(f"\n\033[1;35m{'='*80}")
    print(f"RESPONSE FOR: {response['query']}")
    print(f"{'='*80}\033[0m")
    print(f"Topic: \033[1m{response['topic']}\033[0m | Module: \033[1m{response['module']}\033[0m")
    print(f"Learning Style: \033[1m{response['learning_style']}\033[0m | LLM: \033[1m{response['llm_used']}\033[0m")
    
    explanation = response['explanation']
    
    # Replace source markers with actual source information
    if response['sources']:
        for i, source in enumerate(response['sources']):
            marker = f"[Source {i+1}]"
            source_info = f"{source['original_file']} ({source['location']})"
            explanation = explanation.replace(marker, source_info)
    
    # Clean up markdown
    explanation = re.sub(r'#{2,}', '', explanation)
    explanation = re.sub(r'\*{2}(.*?)\*{2}', r'\1', explanation)
    explanation = re.sub(r'\*(.*?)\*', r'\1', explanation)
    
    print(format_section("Detailed Explanation", explanation))
    
    if response['sources']:
        sources_text = "Material References:\n"
        for i, source in enumerate(response['sources']):
            sources_text += f"\n\033[1m{i+1}. {source['original_file']}\033[0m"
            sources_text += f"\n   📍 Location: {source['location']}"
            sources_text += f"\n   📝 Content: {source['text']}\n"
        print(format_section("Source References", sources_text))
    
    if response.get('reference_books_web'):
        books_text = ""
        for i, book in enumerate(response['reference_books_web']):
            books_text += f"\n\033[1m{i+1}. {book['title']}\033[0m by {book['authors']} ({book['year']})"
            books_text += f"\n   📘 Description: {book['description']}"
            books_text += f"\n   🔗 Link: {book['link']}\n"
        print(format_section("Recommended Reference Books", books_text))
    
    if response['recent_advancements']:
        advancements_text = ""
        for i, adv in enumerate(response['recent_advancements']):
            advancements_text += f"\n\033[1m{i+1}. {adv['title']}\033[0m ({adv['date']})"
            advancements_text += f"\n   📰 Source: {adv['source']}"
            advancements_text += f"\n   📝 Summary: {adv['summary']}"
            advancements_text += f"\n   🔗 Link: {adv['link']}\n"
        print(format_section("Recent Advancements", advancements_text))
    
    if response['research_papers']:
        papers_text = ""
        for i, paper in enumerate(response['research_papers']):
            papers_text += f"\n\033[1m{i+1}. {paper['title']}\033[0m ({paper['year']})"
            papers_text += f"\n   👤 Authors: {paper['authors']}"
            papers_text += f"\n   📝 Summary: {paper['summary']}"
            papers_text += f"\n   🔗 Link: {paper['link']}\n"
        print(format_section("Research Papers", papers_text))
    
    if response['video_recommendations']:
        videos_text = ""
        for i, video in enumerate(response['video_recommendations']):
            videos_text += f"\n\033[1m{i+1}. {video['title']}\033[0m"
            videos_text += f"\n   📺 Channel: {video['channel']}"
            videos_text += f"\n   🔗 URL: https://youtu.be/{video['video_id']}\n"
        print(format_section("Recommended Videos", videos_text))
    
    print(f"\n\033[1;35m{'='*80}")
    print(f"Response generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\033[0m")

if __name__ == "__main__":
    queries = [
        "Explain Types of Data in depth",
        "What is Binomial Distribution?",
        "What's the history of calculus?"
    ]
    
    for query in queries:
        print(f"\n\033[1;36m{'='*80}")
        print(f"QUERY: {query}")
        print(f"{'='*80}\033[0m")
        response = handle_query(query)
        print_response(response)
        print("\n\n")