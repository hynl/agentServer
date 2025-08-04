import logging
from typing import Any, Dict, List, Optional

from ai.agents.base import BaseAgent
from ai.llm.client import LLMClient
from ai.llm.prompts import NEWS_ANALYZER_BATCH_PROMPT
from apps.news.models import NewsArticle

logger = logging.getLogger(__name__)

class NewsAnalyzerAgent(BaseAgent):
    name = "News Analyzer Agent"
    description = "负责对新闻文章进行深度分析，提取关键信息、情感、实体、潜在影响、要点、关键词和类别。"
    
    def run(self, article_ids: List[int] = None, news_articles: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析新闻文章，从文本中提取有用信息
        
        Args:
            article_ids: 需要分析的新闻文章ID列表
            news_articles: 已经过滤的新闻文章列表（直接输入，避免重复查询）
            
        Returns:
            分析结果，包含市场情绪、股票相关性、关键趋势等
        """
        try:
            articles_to_analyze = []
            
            if article_ids and len(article_ids) > 0:
                db_articles = NewsArticle.objects.filter(id__in=article_ids)
                for article in db_articles:
                    articles_to_analyze.append({
                        "id": article.id,
                        "title": article.title,
                        "content": article.content,
                        "summary": article.summary,
                        "url": article.url,
                        "source_name": article.source_name,
                        "published_at": article.published_at.isoformat() if article.published_at else None
                    })
            
            if news_articles and len(news_articles) > 0:
                articles_to_analyze = news_articles
                
            if not articles_to_analyze:
                logger.warning(f"{self.__class__.__name__}: 没有提供需要分析的文章")
                return {
                    "status": "WARNING",
                    "message": "没有提供需要分析的文章",
                    "analysis_results": {}
                }
                
            # 使用LLM分析文章
            logger.info(f"{self.__class__.__name__}: 正在分析 {len(articles_to_analyze)} 篇文章")
            
            # 构造分析提示
            analysis_results = self._analyze_articles_with_llm(articles_to_analyze)
            
            return {
                "status": "COMPLETED",
                "analyzed_count": len(articles_to_analyze),
                "analysis_results": analysis_results
            }
            
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: 分析新闻文章时出错: {e}", exc_info=True)
            return {
                "status": "ERROR",
                "error": str(e),
                "analysis_results": {}
            }
            
    def _analyze_articles_with_llm(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """使用LLM对文章进行深度分析"""
        try:
            # 构建文章文本
            article_texts = []
            for article in articles:
                article_text = f"标题: {article.get('title', '')}\n"
                article_text += f"来源: {article.get('source_name', '')}\n"
                article_text += f"内容: {article.get('content', article.get('summary', ''))}\n"
                article_texts.append(article_text)
            
            all_texts = "\n===文章分割线===\n".join(article_texts)
            
            # 使用提示模板
            prompt = NEWS_ANALYZER_BATCH_PROMPT.format(articles_text=all_texts)
            
            # 调用LLM进行分析
            response = self.llm.invoke(prompt)
            
            # 从响应中提取JSON分析结果
            import json
            import re
            
            # 尝试提取JSON部分
            response_text = response.content if hasattr(response, "content") else str(response)
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text) or \
                        re.search(r'\{[\s\S]*\}', response_text)
            
            if json_match:
                json_text = json_match.group(1) if '```json' in response_text else json_match.group(0)
                analysis_results = json.loads(json_text)
                return analysis_results
            else:
                # 如果无法提取JSON，返回原始响应
                return {"raw_analysis": response_text}
                
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: 使用LLM分析文章时出错: {e}", exc_info=True)
            return {"error": str(e)}
        