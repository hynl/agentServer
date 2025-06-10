from agentrtw.settings import NEWS_NEWS_API_KEY
from constants import DEFAULT_NEWS_CONFIG


class NewsFetcherService:
    def __init__(self, news_api_client):
        self.source_config = DEFAULT_NEWS_CONFIG
        self.news_news_api_key = NEWS_NEWS_API_KEY

    def get_rss_by(self, news_type):
        """
        Get the RSS feeds by news type.
        """
        all_rss_feeds_config = self.source_config.get('rss', {})
        if news_type is None:
            all_rss_feeds = []
            for rss_url in all_rss_feeds_config.values():
                if isinstance(rss_url, list):
                    all_rss_feeds.extend(rss_url)
                else:
                    print(f"Invalid RSS feed format: {rss_url}")
                    pass
            return all_rss_feeds
        else:
            return all_rss_feeds_config.get(news_type, [])








