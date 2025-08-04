from datetime import timezone
import logging
import json
from typing import Any, Dict, List, Optional

from ai.agents.base import BaseAgent
from ai.llm.prompts import NEWS_RELEVANCE_RANKING_PROMPT
from ai.vector.news_vector_excutor import NewsVectorExecutor
from ai.vector.user_vector_executor import UserVectorExecutor
from apps.news.models import NewsSource
from apps.users.models import UserProfile
from langchain_core.runnables import RunnableSequence # For potential internal LLM chains
from ai.agents.common_tools import get_user_profile, search_similar_news # Ensure tool

logger = logging.getLogger(__name__)

class NewsFilterAgent(BaseAgent):
    name = "News Filter and Prioritizer Agent"
    description = "Filters and prioritizes news articles based on user profile and preferences, using vector similarity search."
    
    def __init__(self, llm=None):
        super().__init__(llm)
        self.re_ranking_chain: RunnableSequence = NEWS_RELEVANCE_RANKING_PROMPT | self.llm
        self.enable_ai_re_ranking = True
        
    def run(self,
            user_id: int,
            news_candidates: Optional[List[Dict[str, Any]]] = None,
            max_articles: int = 10) -> Dict[str, Any]:
        
        try:
            user_profile = get_user_profile(str(user_id))
            if not user_profile:
                logger.warning(f"{self.__class__.__name__}: 用户 {user_id} 的个人资料未找到.")
                return {
                    "status": "ERROR",
                    "error": "User profile not found.",
                    "filtered_articles": []
                }
                
            # 准备过滤条件
            filter_criteria = {
                "preferred_topic": user_profile.get("preferred_topic", []),
                "excluded_topic": user_profile.get("excluded_topic", []),
                "ai_re_ranking_enabled": self.enable_ai_re_ranking
            }
            
            user_interest_embedding = user_profile.get('interest_embedding')
            excluded_topics = user_profile.get('excluded_topic', [])
            preferred_topics = user_profile.get('preferred_topic', [])
            
            # 如果没有提供候选新闻，则搜索相似新闻
            if not news_candidates:
                if not user_interest_embedding:
                    logger.warning(f"{self.__class__.__name__}: 用户 {user_id} 没有兴趣嵌入向量，使用默认查询。")
                    query_for_search = f"最新的财经新闻，关于{', '.join(preferred_topics) if preferred_topics else '股票市场、经济趋势'}。"
                    
                    news_candidates_summaries = search_similar_news.func(
                        query_text=query_for_search, 
                        query_embedding=None,
                        k=max_articles * 5
                    )
                else:
                    logger.info(f"{self.__class__.__name__}: 使用用户兴趣嵌入向量进行相似新闻搜索，用户 ID {user_id}.")
                    news_candidates_summaries = search_similar_news.func(
                        query_text=None,
                        query_embedding=user_interest_embedding, # <--- Direct use of user embedding!
                        k=max_articles * 5
                    )
            else:
                # 使用提供的候选新闻
                news_candidates_summaries = news_candidates
                logger.info(f"{self.__class__.__name__}: 使用提供的候选新闻: {len(news_candidates)} 篇文章")

            if not news_candidates_summaries:
                logger.warning(f"{self.__class__.__name__}: 用户 {user_id} 没有找到任何候选新闻.")
                return {
                    "status": "WARNING",
                    "error": "No news candidates found.",
                    "filtered_articles": []
                }
            
            pre_filtered_news = []
            for news_item in news_candidates_summaries:
                is_excluded = False
                full_text_for_check = f"{news_item.get('title', '')} {news_item.get('summary', '')}"
                for keyword in excluded_topics:
                    if keyword.lower() in full_text_for_check.lower():
                        is_excluded = True
                        logger.debug(f"{self.__class__.__name__}: 排除新闻 {news_item.get('title', 'Unknown')}，包含排除关键词: {keyword}")
                        break
                
                if not is_excluded:
                    pre_filtered_news.append(news_item)
                        
            if not pre_filtered_news:
                logger.warning(f"{self.__class__.__name__}: 用户 {user_id} 没有找到预过滤的新闻.")
                return {
                    "status": "WARNING",
                    "error": "No pre-filtered news found.",
                    "filtered_articles": []
                }
            
            # 增加时间衰减
            if pre_filtered_news:
                from datetime import datetime
                import dateutil.parser
                
                current_time = datetime.now(timezone.utc)
            
                # 为每篇文章计算时间新鲜度分数
                for article in pre_filtered_news:
                    try:
                        # 解析发布时间
                        published_at = article.get('published_at')
                        if isinstance(published_at, str):
                            pub_date = dateutil.parser.parse(published_at)
                        elif hasattr(published_at, 'timestamp'):
                            pub_date = published_at
                        else:
                            # 如果无法解析时间，默认为较低的时间分数
                            article['recency_score'] = 0.5
                            continue
                        
                        # 计算时间差（天）
                        time_diff = (current_time - pub_date).total_seconds() / (24 * 3600)
                        
                        # 时间衰减函数：越新的文章分数越高，指数衰减
                        # 1天内的文章得分接近1，7天前的文章得分约为0.5，更老的文章得分更低
                        recency_score = max(0.1, min(1.0, pow(0.9, time_diff)))
                        article['recency_score'] = recency_score
                        
                        logger.debug(f"{self.__class__.__name__}: 文章 '{article.get('title', 'Unknown')}' 发布于 {pub_date}, 新鲜度分数: {recency_score:.2f}")
                    except Exception as e:
                        logger.warning(f"{self.__class__.__name__}: 计算文章时间分数时出错: {e}")
                        article['recency_score'] = 0.5  # 默认中等分数

            final_selected_news = []
            
            
            # 在 AI 重排序部分修改，加入时间权重
            if self.enable_ai_re_ranking and hasattr(self, 'llm') and self.llm:
                logger.info(f"{self.__class__.__name__}: 正在使用AI模型对新闻文章进行重新排序.")
                user_profile_summary = (
                    f"User ID: {user_id}, "
                    f"Preferred Topics: {', '.join(preferred_topics)}, "
                    f"Excluded Topics: {', '.join(excluded_topics)}"
                )
                
                news_for_llm = []
                for i, news_item in enumerate(pre_filtered_news):
                    # 添加发布时间信息，确保LLM能看到时间信息
                    published_at = news_item.get('published_at', '')
                    # 如果时间不是字符串，转换为ISO格式
                    if not isinstance(published_at, str):
                        try:
                            published_at = published_at.isoformat() if hasattr(published_at, 'isoformat') else str(published_at)
                        except:
                            published_at = ''
                            
                    news_for_llm.append({
                        "id": news_item.get('id', i),
                        "title": news_item.get('title', ''),
                        "summary": news_item.get('summary', ''),
                        "url": news_item.get('url', ''),
                        "published_at": published_at,  # 确保发布时间被传递
                        "author": news_item.get('author', ''),
                        "source_name": news_item.get('source_name', ''),
                        "recency_score": news_item.get('recency_score', 0.5)  # 传递时间分数
                    })
                    
                try:
                    response = self.re_ranking_chain.invoke({
                        "user_profile_summary": user_profile_summary,  # 修复变量名
                        "news_candidates_json": json.dumps(news_for_llm, ensure_ascii=False, indent=2)  # 修复变量名
                    })
                    
                    # 从AIMessage对象中提取内容
                    if hasattr(response, 'content'):
                        response_content = response.content
                    else:
                        response_content = str(response)
                    logger.debug(f"{self.__class__.__name__}: LLM 原始响应: {response_content[:500]}...")
                    # 尝试解析JSON
                    try:
                        ranked_results = json.loads(response_content)
                    except json.JSONDecodeError:
                        # 尝试提取JSON部分
                        import re
                        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_content) or \
                                    re.search(r'\{[\s\S]*\}', response_content)
                        
                        if json_match:
                            try:
                                json_text = json_match.group(1) if '```json' in response_content else json_match.group(0)
                                logger.debug(f"{self.__class__.__name__}: 提取的JSON: {json_text[:200]}...")
                                ranked_results = json.loads(json_text)
                            except json.JSONDecodeError as e:
                                logger.error(f"{self.__class__.__name__}: 无法解析提取的JSON: {e}")
                                # 使用默认排序
                                ranked_results = pre_filtered_news
                        else:
                            logger.error(f"{self.__class__.__name__}: 无法从LLM响应中提取JSON. 原始响应: {response_content[:200]}...")
                            ranked_results = pre_filtered_news
                    
                    if isinstance(ranked_results, list):
                        ranked_results = sorted(ranked_results, key=lambda x: x.get('relevance_score', 0), reverse=True)
                    
                    # 创建映射
                    ranked_articles_map = {item.get('id', i): item for i, item in enumerate(pre_filtered_news)}

                    for ranked_item in ranked_results:
                        original_article = ranked_articles_map.get(ranked_item.get('id'))
                        if original_article and ranked_item.get('relevance_score', 0) > 0:
                            # 计算组合分数，结合LLM相关性分数和时间新鲜度分数
                            relevance_score = ranked_item.get('relevance_score', 0)
                            recency_score = original_article.get('recency_score', 0.5)
                            
                            # 组合分数计算：70%相关性 + 30%时效性
                            # 可以根据需要调整权重
                            combined_score = (0.7 * relevance_score / 100) + (0.3 * recency_score)
                            
                            original_article['relevance_score'] = relevance_score
                            original_article['recency_score'] = recency_score
                            original_article['combined_score'] = combined_score
                            original_article['relevance_reason'] = ranked_item.get('relevance_reason', '')
                            
                            final_selected_news.append(original_article)
                    logger.info(f"{self.__class__.__name__}: AI re-ranking 完成. 选择了 {len(final_selected_news)} 篇文章.")

                except Exception as e:
                    logger.error(f"{self.__class__.__name__}: AI re-ranking 过程中出错: {e}")
                    final_selected_news = pre_filtered_news[:max_articles]
            else:
                logger.info(f"{self.__class__.__name__}: AI re-ranking 被禁用或没有可用的LLM. 使用预过滤的新闻作为最终选择.")
                final_selected_news = pre_filtered_news[:max_articles]
                
             
            final_selected_news = sorted(final_selected_news, key=lambda x: x.get('combined_score', 0), reverse=True)
            final_selected_news = final_selected_news[:max_articles]
                
            # 为没有相关性得分的文章添加默认得分
            for article in final_selected_news:
                if 'relevance_score' not in article:
                    article['relevance_score'] = 0.5
                if 'relevance_reason' not in article:
                    article['relevance_reason'] = 'Default selection based on user preferences'
            
            return {
                "status": "COMPLETED",
                "user_id": user_id,
                "total_candidates": len(news_candidates_summaries),
                "filtered_count": len(final_selected_news),
                "filtered_articles": final_selected_news,
                "filter_criteria": {
                    "preferred_topics": preferred_topics,
                    "excluded_topics": excluded_topics,
                    "max_articles": max_articles,
                    "ai_re_ranking_enabled": self.enable_ai_re_ranking
                }
            }
            
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: 用户 {user_id} 过滤新闻时出错: {e}")
            return {
                "status": "ERROR",
                "error": f"Error filtering news for user {user_id}: {str(e)}",
                "filtered_articles": []
            }
            