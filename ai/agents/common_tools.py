from langchain.tools import tool
import logging
from typing import Any, Dict, List, Optional
from django.utils import timezone
import requests
from ai.vector.news_vector_excutor import NewsVectorExecutor

logger = logging.getLogger(__name__)
_news_vector_executor = NewsVectorExecutor()

@tool("ReadRSSFeedTool")
def read_rss_feed(url: str) -> List[Dict[str, Any]]:
    """
    Read RSS feed and return a list of news articles.
    
    Args:
        url: The URL of the RSS feed to parse
        
    Returns:
        List of dictionaries containing article information
    """
    try:
        import feedparser
        feed = feedparser.parse(url)
        
        if not feed.entries:
            logger.warning(f'read_rss_feed: 没有找到任何条目在RSS源 {url}')
            return []

        results = []
        for entry in feed.entries:
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    # 修复时间处理
                    import time
                    from datetime import datetime
                    timestamp = time.mktime(entry.published_parsed)
                    published_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                except Exception as e:
                    logger.warning(f"read_rss_feed: 解析发布时间失败: {e}")
                    published_date = timezone.now()
                    
            # 提取分类/标签
            categories = []
            if hasattr(entry, 'tags'):
                categories = [tag.term for tag in entry.tags]
            elif hasattr(entry, 'categories'):
                categories = entry.categories
            
            # 提取关键词
            keywords = getattr(entry, 'keywords', '').split(',') if hasattr(entry, 'keywords') else []
            
            
            result = {
                'title': entry.title,
                'url': entry.link,
                'summary': getattr(entry, 'summary', getattr(entry, 'description', '')),
                'published_at': published_date,
                'author': getattr(entry, 'author', ''),
                'source_name': getattr(entry, 'source', {}).get('title', ''),
                'content': getattr(entry, 'content', [{}])[0].get('value', '') if hasattr(entry, 'content') and entry.content else getattr(entry, 'description', ''),
                'categories': categories,
                'keywords': keywords,
            }
            results.append(result)
        return results
    except Exception as e:
        logger.error(f"read_rss_feed: 读取RSS源 {url} 时出错: {e}")
        return []
    
@tool("ScrapeArticlesTool")
def scrape_articles_content(source_url: str) -> str:
    """
    抓取文章内容并提取主要文本。
    
    从网页URL获取内容，清理HTML标签，并返回提取的文本内容。
    使用newspaper3k库进行智能内容提取，去除广告和无关内容。
    
    Args:
        source_url: 要抓取内容的文章URL
        
    Returns:
        提取的纯文本内容
    """
    try:
        response = requests.get(source_url, timeout=10)
        response.raise_for_status()
    
        content = None

        # 方法1: 使用 newspaper3k
        try:
            from newspaper import Article
            article = Article(source_url)
            
            # 使用已获取的响应内容而不是再次下载
            article.download(input_html=response.text)
            article.parse()
            
            if article.text and len(article.text) > 100:
                logger.info(f"scrape_articles_content: 成功使用newspaper3k提取内容: {len(article.text)}字符")
                return article.text
        except ImportError as e:
            logger.warning(f"scrape_articles_content: newspaper3k导入失败: {e}")
        except Exception as e:
            logger.warning(f"scrape_articles_content: newspaper3k解析失败: {e}")

        # 方法2: 使用BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            article_tag = soup.find(['article', 'main', 'div'], 
                                   class_=lambda x: x and ('article' in x or 'content' in x))
            
            if article_tag:
                content = article_tag.get_text(separator='\n', strip=True)
                logger.info(f"scrape_articles_content: 成功使用BeautifulSoup提取内容: {len(content)}字符")
                return content
        except ImportError:
            logger.warning("scrape_articles_content: BeautifulSoup未安装")
        except Exception as e:
            logger.warning(f"scrape_articles_content: BeautifulSoup解析失败: {e}")
            
        # 方法3: 使用正则表达式提取
        import re
        text = re.sub(r'<script.*?>.*?</script>', '', response.text, flags=re.DOTALL)
        text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 尝试简单地提取正文
        paragraphs = re.findall(r'[.!?。！？]["\']?\s+[A-Z一-龥]', text)
        if len(paragraphs) > 5:
            logger.info(f"scrape_articles_content: 成功使用正则表达式提取文本: {len(text[:5000])}字符")
            return text[:5000]  # 限制长度
        
        # 如果所有方法都失败，至少返回标题和元数据
        return f"无法提取正文。URL: {source_url}"
        
    except Exception as e:
        logger.error(f"scrape_articles_content: 抓取内容失败 {source_url}: {e}")
        return f"抓取失败: {str(e)}"
    
@tool("SearchSimilarNewsTool")
def search_similar_news(query_text: Optional[str], query_embedding: Optional[List[float]], k: int = 10) -> List[Dict[str, Any]]:
    """
    Search for similar news articles using vector similarity.
    
    Args:
        query_text: Optional text query for similarity search
        query_embedding: Optional pre-computed embedding vector
        k: Number of similar articles to return (default: 10)
        
    Returns:
        List of dictionaries containing similar article information
    """
    try:
        similar_articles = _news_vector_executor.query_similar_news(query_text=query_text, query_embedding=query_embedding, top_k=k)
        return [{
            'id': article.id,
            'url': article.url,
            'summary': article.summary,
            'published_at': article.published_at.isoformat() if article.published_at else None,
            'author': article.author,
            'source_name': article.source_name,
            'title': article.title,
        } for article in similar_articles]
    except Exception as e:
        logger.error(f"search_similar_news: 查询相似新闻时出错: {e}")
        return []
    
@tool("GetUserProfileTool")
def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Get user profile information including preferences and interests.
    
    Args:
        user_id: The ID of the user whose profile to retrieve
        
    Returns:
        Dictionary containing user profile information
    """
    from apps.users.models import UserProfile
    try:
        user_profile = UserProfile.objects.get(user_id=user_id)
        # 处理嵌入向量 - 如果是 numpy.ndarray，转换为列表
        interest_embedding = user_profile.interest_embedding
        if interest_embedding is not None:
            import numpy as np
            if isinstance(interest_embedding, np.ndarray):
                interest_embedding = interest_embedding.tolist()
        
        return {
            'id': str(user_profile.id),
            'user_id': str(user_profile.user.id),
            'preferred_topics': user_profile.preferred_topic,
            'excluded_topics': user_profile.excluded_topic,
            'user_self_portrait': user_profile.user_self_portrait,
            "is_processed_for_embedding": user_profile.is_processed_for_embedding if hasattr(user_profile, 'is_processed_for_embedding') else False,
            "interest_embedding": interest_embedding
        }
    except UserProfile.DoesNotExist:
        logger.error(f"get_user_profile: 用户 {user_id} 的个人资料不存在.")
        return {}
    except Exception as e:
        logger.error(f"get_user_profile: 获取用户 {user_id} 的个人资料时出错: {e}")
        return {}
    
@tool("ProcessNewsArticlesTool")
def process_news_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process news articles and generate embeddings.
    
    Args:
        articles: List of article dictionaries to process
        
    Returns:
        List of processed article dictionaries with embeddings
    """
    try:
        processed_articles = []
        
        for article in articles:
            processed_article = article.copy()
            
            # Generate embedding for the article
            text_for_embedding = f"{article.get('title', '')} {article.get('summary', '')}"
            if text_for_embedding.strip():
                try:
                    embedding = _news_vector_executor.generate_embedding(text_for_embedding)
                    processed_article['embedding'] = embedding
                    processed_article['processed'] = True
                except Exception as e:
                    logger.error(f"Error generating embedding for article: {e}")
                    processed_article['processed'] = False
            else:
                processed_article['processed'] = False
            
            processed_articles.append(processed_article)
            
        logger.info(f"process_news_articles: 成功处理 {len(processed_articles)} 篇文章")
        return processed_articles
        
    except Exception as e:
        logger.error(f"process_news_articles: 处理新闻文章时出错: {e}")
        return articles
    