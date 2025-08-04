
from datetime import timedelta
from django.utils import timezone
import logging
from typing import Any, Dict, Optional

from ai.agents.base import BaseAgent
from ai.agents.common_tools import read_rss_feed, scrape_articles_content
from ai.vector.news_vector_excutor import NewsVectorExecutor
from apps.news.models import NewsSource, NewsArticle

logger = logging.getLogger(__name__)

class NewsFetcherAgent(BaseAgent):
    name = "News Fetcher Agent"
    description = "An agent that fetches news articles from RSS feeds, scrapes full content, stores them in the database, and generates embeddings for similarity search."
    
    # 添加时间阈值常量
    FETCH_INTERVAL = timedelta(hours=1)  # 每小时抓取一次
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.news_vector_executor = NewsVectorExecutor()
        
    def run(self, 
            source_name: Optional[str] = None, 
            source_url: Optional[str] = None, 
            limit_new_articles: int = 20, 
            force_refresh: bool = False) -> Dict[str, Any]:
            
        news_source_to_fetch = []
        current_time = timezone.now()
        
        if source_name and source_url:
            source, created = NewsSource.objects.get_or_create(
                name=source_name,
                defaults={
                    'url': source_url,
                    'description': f'News source for {source_name}', 
                    'is_active': True
                }
            )
            # 检查是否需要抓取（新创建的或已过期的或强制刷新的）
            if created or force_refresh or self._is_fetch_needed(source, current_time):
                news_source_to_fetch.append(source)
                if created:
                    logger.info(f"{self.__class__.__name__}: 创建新的新闻源: {source.name}")
            else:
                logger.info(f"{self.__class__.__name__}: 跳过源 {source.name} - 最近抓取于 {source.last_fetched_at}")

        else:
            # 获取所有活跃的新闻源
            all_active_sources = NewsSource.objects.filter(is_active=True)
            
            # 筛选需要抓取的新闻源
            for source in all_active_sources:
                if force_refresh or self._is_fetch_needed(source, current_time):
                    news_source_to_fetch.append(source)
                    logger.info(f"{self.__class__.__name__}: 准备抓取源 {source.name} - 最近抓取于 {source.last_fetched_at}")
                else:
                    logger.info(f"{self.__class__.__name__}: 跳过源 {source.name} - 最近抓取于 {source.last_fetched_at}")

            logger.info(f"{self.__class__.__name__}: 从 {len(news_source_to_fetch)} 个活跃源抓取新闻")

        # 如果没有需要抓取的源，提前返回
        if not news_source_to_fetch:
            logger.info(f"{self.__class__.__name__}: 当前没有需要抓取的源")
            return {
                'status': 'COMPLETED',
                'fetched_count': 0,
                'processed_embedding_count': 0,
                'message': "No sources needed fetching at this time. All sources are up to date."
            }
            
        fetched_count = 0
        processed_embedding_count = 0
        
        for source in news_source_to_fetch:
            logger.info(f"{self.__class__.__name__}: 正在从RSS源获取新闻...")
            raw_articles = read_rss_feed(source.url)
            
            if not raw_articles:
                logger.warning(f"{self.__class__.__name__}: 没有从源 {source.name} 获取到任何文章")
                source.last_fetched_at = current_time
                source.save(update_fields=['last_fetched_at'])
                continue

            logger.info(f"{self.__class__.__name__}: 从 {source.name} 获取到 {len(raw_articles)} 篇文章")
            
            for article in raw_articles:
                if NewsArticle.objects.filter(url=article['url']).exists():
                    logger.info(f"{self.__class__.__name__}: 文章已存在: {article['url']}")
                    continue
                
                try:
                    logger.info(f"{self.__class__.__name__}: 正在抓取文章内容: {article['url']}")
                    full_article_content = scrape_articles_content(article['url'])
                    # 检查内容是否有效
                    if not full_article_content or len(full_article_content.strip()) < 50:
                        logger.warning(f"{self.__class__.__name__}: 抓取内容为空或过短，使用RSS内容作为备用: {article['url']}")
                        # 使用RSS提供的内容作为备用
                        full_article_content = article.get('content', '') or article.get('summary', '')

                    logger.info(f"{self.__class__.__name__}: 抓取内容长度: {len(full_article_content)} 字符")

                    news_article = NewsArticle(
                        title=article['title'],
                        url=article['url'],
                        summary=article.get('summary', ''),
                        content=full_article_content or article.get('content', ''),
                        published_at=article.get('published_at'),
                        author=article.get('author', ''),
                        source_name=source.name,
                        keywords=article.get('keywords', []),
                        categories=article.get('categories', []),
                        is_processed_for_embedding=False
                    )
                    logger.info(f"{self.__class__.__name__}: 正在保存新闻到数据库...")
                    news_article.save()
                    fetched_count += 1
                    logger.info(f"{self.__class__.__name__}: 成功保存文章: {news_article.title} ({news_article.url})")

                    # 处理嵌入向量
                    try:
                        logger.info(f"{self.__class__.__name__}: 开始生成新闻嵌入向量...{news_article.title}")
                        if self.news_vector_executor.add_news_document(news_article):
                            processed_embedding_count += 1
                            news_article.is_processed_for_embedding = True
                            news_article.save(update_fields=['is_processed_for_embedding'])
                            logger.info(f"{self.__class__.__name__}: 结束生成新闻嵌入向量...{news_article.title}")
                        else:
                            logger.warning(f"{self.__class__.__name__}: 无法为文章生成嵌入向量: {news_article.title}")
                    except Exception as e:
                        logger.error(f"{self.__class__.__name__}: 处理文章 {news_article.title} 的嵌入时出错: {e}")

                    if fetched_count >= limit_new_articles:
                        logger.info(f"{self.__class__.__name__}: 达到 {limit_new_articles} 篇新文章的限制. 停止抓取.")
                        break
                except Exception as e:
                    logger.error(f"{self.__class__.__name__}: 处理文章 {article['url']} 时出错: {e}")
                    continue
                
            source.last_fetched_at = timezone.now()
            source.save(update_fields=['last_fetched_at'])
            
            if fetched_count >= limit_new_articles:
                logger.info(f"{self.__class__.__name__}: 达到 {limit_new_articles} 篇新文章的限制. 停止抓取.")
                break
        return {
            'status': 'COMPLETED',
            'fetched_count': fetched_count,
            'processed_embedding_count': processed_embedding_count,
            'message': f"Fetched {fetched_count} articles and processed embeddings for {processed_embedding_count} articles.",
            'sources_fetched': [source.name for source in news_source_to_fetch]
        }
    

    def _is_fetch_needed(self, source: NewsSource, current_time: timezone.datetime) -> bool:
            """
            判断是否需要抓取指定的新闻源
            
            Args:
                source: 新闻源对象
                current_time: 当前时间
                
            Returns:
                是否需要抓取
            """
            # 如果没有最后抓取时间，则需要抓取
            if not source.last_fetched_at:
                return True
                
            # 如果超过抓取间隔，则需要抓取
            time_since_last_fetch = current_time - source.last_fetched_at
            return time_since_last_fetch > self.FETCH_INTERVAL
    