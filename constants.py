


NEWS_NEWS_WEB_URL = 'NEWS_NEWS_WEB_URL'

RSS = 'rss'
API = 'api'

NEWS_TYPE_BUSINESS = 'business'
NEWS_TYPE_TOP = 'tops'
NEWS_TYPE_WORLD = 'world'

DEFAULT_NEWS_RSS_FEEDS = {
    NEWS_TYPE_BUSINESS: ['https://feeds.reuters.com/reuters/businessNews'],
    NEWS_TYPE_TOP: ['https://feeds.reuters.com/reuters/topNews'],
    NEWS_TYPE_WORLD: ['https://feeds.reuters.com/reuters/worldNews'],
}


DEFAULT_NEWS_URL_FEEDS = {(NEWS_TYPE_BUSINESS, (NEWS_NEWS_WEB_URL, 'https://newsapi.org/')),
                          (NEWS_TYPE_TOP, (NEWS_NEWS_WEB_URL, 'https://newsapi.org/')),
                          (NEWS_TYPE_WORLD, (NEWS_NEWS_WEB_URL, 'https://newsapi.org/'))}

DEFAULT_NEWS_CONFIG = {
    RSS: DEFAULT_NEWS_RSS_FEEDS,
    API: DEFAULT_NEWS_URL_FEEDS
}


DEFAULT_USER_AGENT = 'Mozilla/5.0 (compatible; Django News Fetcher/1.0; +https://songtop.space/contact)'
