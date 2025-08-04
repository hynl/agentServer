
import logging
from typing import Any, Dict, Optional

from ai.agents.base import BaseAgent
from ai.agents.common_tools import get_user_profile, read_rss_feed, scrape_articles_content
from ai.vector.news_vector_excutor import NewsVectorExecutor
from ai.vector.user_vector_executor import UserVectorExecutor
from apps.news.models import NewsSource
from apps.users.models import UserProfile

logger = logging.getLogger(__name__)

class UserProfilerAgent(BaseAgent):
    name = "User Profiler Agent"
    description = "Responsible for profiling users based on their interests, preferences, and behaviors, and generating user embeddings for personalized content recommendations."
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_vector_executor = UserVectorExecutor()
        
    def run(self, 
            user_id: Optional[str] = None, 
            update_profile_embedding: bool = False) -> Dict[str, Any]:
        
        if not user_id:
            logger.error(f"{self.__class__.__name__}: 用户ID不能为空")
            return {"error": "User ID is required."}
        
        # Fetch user profile and update interests
        user_profile = get_user_profile(user_id)
        
        if not user_profile:
            logger.info(f"{self.__class__.__name__}: 用户 {user_id} 的个人资料不存在，尝试创建新的个人资料")
            try:
                user_profile_obj, created = UserProfile.objects.get_or_create(user_id=user_id)
                user_profile = get_user_profile(user_id)
                if created:
                    logger.info(f"{self.__class__.__name__}: 为用户 {user_id} 创建了新的个人资料.")
            except Exception as e:
                logger.error(f"{self.__class__.__name__}: 为用户 {user_id} 创建个人资料时出错: {e}")
                return {"error": "Failed to create user profile."}
        if not user_profile:
            return {"error": "User profile not found."}
        
        if update_profile_embedding:
            try:
                user_profile_obj = UserProfile.objects.get(user_id=user_id)
                text_for_embedding = f"{user_profile_obj.user_self_portrait}, {user_profile_obj.preferred_topic}"
                
                if not text_for_embedding:
                    logger.warning(f"{self.__class__.__name__}: 用户 {user_id} 没有可用的文本内容.")
                    return {"error": "No text content available for embedding."}
                else:
                    success = self.user_vector_executor.update_user_profile_embedding(user_profile_obj, text_for_embedding)
                    if success:
                        user_profile = get_user_profile(user_id)
                        logger.info(f"{self.__class__.__name__}: 更新了用户 {user_id} 的个人资料嵌入.")
                    else:
                        logger.error(f"{self.__class__.__name__}: 更新用户 {user_id} 的个人资料嵌入失败.")
            except UserProfile.DoesNotExist:
                logger.error(f"{self.__class__.__name__}: 用户 {user_id} 的个人资料不存在.")
                   
            except Exception as e:
                logger.error(f"{self.__class__.__name__}: 更新用户 {user_id} 的个人资料嵌入时出错: {e}")

        return user_profile
    