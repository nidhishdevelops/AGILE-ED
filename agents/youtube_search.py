from googleapiclient.discovery import build
from config import Config
import logging
import threading

logger = logging.getLogger(__name__)

_thread_local = threading.local()

try:
    from utils.result_logger import result_logger
except ImportError:
    class DummyLogger:
        def log_web_content(self, *args, **kwargs): pass
    result_logger = DummyLogger()

def search_youtube_videos(topic):
    if not hasattr(_thread_local, 'logged_videos'):
        _thread_local.logged_videos = set()
    
    try:
        youtube = build('youtube', 'v3', developerKey=Config.YOUTUBE_API_KEY)
        request = youtube.search().list(
            q=f"{topic} tutorial",
            part="snippet",
            type="video",
            maxResults=3,
            videoDuration="medium",
            relevanceLanguage="en",
            order="relevance"
        )
        response = request.execute()
        videos = []
        for item in response.get('items', [])[:3]:
            video_id = item['id'].get('videoId')
            if video_id:
                videos.append({
                    "title": item['snippet']['title'],
                    "video_id": video_id,
                    "channel": item['snippet']['channelTitle']
                })
        
        if topic not in _thread_local.logged_videos:
            result_logger.log_web_content("youtube_videos", topic, videos)
            _thread_local.logged_videos.add(topic)
            logger.info(f"Logged YouTube videos for: {topic}")
        
        return videos
    except Exception as e:
        logger.error(f"YouTube error: {str(e)}")
        error_result = [{"title": "Error fetching videos", "video_id": "", "channel": "Check API config"}]
        if topic not in _thread_local.logged_videos:
            result_logger.log_web_content("youtube_videos", topic, error_result)
            _thread_local.logged_videos.add(topic)
        return error_result