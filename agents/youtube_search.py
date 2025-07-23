from googleapiclient.discovery import build
from config import Config
import logging

logger = logging.getLogger(__name__)

def search_youtube_videos(topic):
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
        return videos
    except Exception as e:
        logger.error(f"YouTube error: {str(e)}")
        return [{"title": "Error fetching videos", "video_id": "", "channel": "Check API config"}]