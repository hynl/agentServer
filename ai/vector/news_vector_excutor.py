from typing import List, Dict, Any, Optional
from ai.llm.constants import DEFAULT_EMBEDDING_MODEL_PROVIDER
from apps.news.models import NewsArticle
from ai.vector.pgvector_client import PGVectorClient
import logging

logger = logging.getLogger(__name__)
class NewsVectorExecutor:
    def __init__(self, embedding_provider: Optional[str] = None):
        self.embedding_provider = embedding_provider or DEFAULT_EMBEDDING_MODEL_PROVIDER
        self.vector_client = PGVectorClient(
            model_class=NewsArticle,
            embedding_field_name='embedding',
            processed_flag_field_name='is_processed_for_embedding',
            text_content_field_name='content',
            embedding_provider=self.embedding_provider
        )

    def add_news_document(self, news: NewsArticle) -> bool:
        """
        添加新闻文章到向量存储，使用分块嵌入策略处理长文本
        
        Args:
            news: 新闻文章对象
            
        Returns:
            是否成功添加
        """
        try:
            document_id = str(news.id)
            logger.info(f'{self.__class__.__name__}: 添加新闻文章 {document_id} 到向量存储')

            content_is_valid = news.content and len(news.content.strip()) > 50
            if not content_is_valid:
                logger.warning(f"文章内容为空或过短: {len(news.content) if news.content else 0} 字符")
                backup_content = f"标题: {news.title or ''}"
                if news.summary:
                    backup_content += f"\n摘要: {news.summary}"
                    
                if not news.content:
                    news.content = backup_content
                    news.save(update_fields=['content'])
                    logger.info(f"已使用标题和摘要作为备用内容: {len(backup_content)} 字符")
            
            text_for_embedding = f"标题: {news.title or ''}\n"
            
            if news.summary:
                text_for_embedding += f"摘要: {news.summary}\n"
                
            # 限制内容长度
            max_content_length = 7000  # 避免触发分块
            if news.content:
                truncated_content = news.content[:max_content_length]
                text_for_embedding += f"\n内容: {truncated_content}"
                if len(news.content) > max_content_length:
                    logger.info(f"内容已截断: {max_content_length}/{len(news.content)} 字符")
            
            # 确保文本不为空
            if not text_for_embedding.strip():
                text_for_embedding = f"标题: {news.title or 'Untitled'}"
                
            logger.info(f"准备嵌入文本，长度: {len(text_for_embedding)} 字符")
            
            # 构建元数据
            metadata = {
                'title': news.title,
                'url': news.url,
                'source_name': news.source_name,
                'published_at': news.published_at.isoformat() if news.published_at else None,
                'author': news.author,
                'summary': news.summary
            }
            
            try:
                success = self.vector_client.add_document(document_id, text_for_embedding, metadata)
                if success:
                    logger.info(f"成功添加新闻文章 {document_id} 到向量存储")
                    return True
                else:
                    logger.warning(f"添加新闻文章 {document_id} 到向量存储失败")
                    return False
            except Exception as e:
                logger.error(f"向量存储操作失败: {e}", exc_info=True)
                return False
                
        except Exception as e:
            logger.error(f"处理新闻文章 {getattr(news, 'id', 'unknown')} 时出错: {e}", exc_info=True)
            return False
        
    def update_news_document(self, news: NewsArticle) -> bool:
        """更新新闻文章"""
        return self.add_news_document(news)
    
    def query_similar_news(self, query_text: Optional[str], query_embedding: Optional[List[float]], top_k: int = 5, categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        查询相似新闻文章
        
        Args:
            query: 查询文本
            query_embedding: 查询嵌入（如已计算）
            top_k: 返回结果数量
            categories: 可选的分类过滤
            
        Returns:
            相似新闻文章列表
        """
        try:
            # 添加过滤条件
            filters = {}
            if categories:
                filters['categories__contains'] = categories
            
            # 执行查询
            results = self.vector_client.query_similar_documents(
                query_text=query_text,
                query_embedding=query_embedding,
                top_k=top_k,
                distance_metric="cosine",
                filters=filters
            )
            
            # 获取新闻文章实例
            article_ids = [result['id'] for result in results]
            articles = NewsArticle.objects.filter(id__in=article_ids)
            
            # 按照相似度分数排序
            id_to_article = {str(article.id): article for article in articles}
            sorted_articles = []
            
            for result in results:
                article_id = str(result['id'])
                if article_id in id_to_article:
                    article = id_to_article[article_id]
                    # 将分数附加到文章对象
                    # article.similarity_score = result['score']
                    sorted_articles.append(article)
            
            logger.info(f"Found {len(sorted_articles)} similar news articles")
            return sorted_articles
            
        except Exception as e:
            logger.error(f"Error querying similar news: {e}", exc_info=True)
            return []

    
    def get_news_embedding(self, news_id: str) -> Optional[List[float]]:
        return self.vector_client.get_document_embedding(news_id)
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        为给定文本生成嵌入向量
        
        Args:
            text: 需要嵌入的文本
            
        Returns:
            嵌入向量
        """
        return self.vector_client._get_embedding(text)

    def delete_news_document(self, news_article_id: str) -> bool:
        """
        删除新闻文章
        
        Args:
            news_article_id: 新闻文章ID
            
        Returns:
            是否成功删除
        """
        return self.vector_client.delete_document(document_id=news_article_id)
