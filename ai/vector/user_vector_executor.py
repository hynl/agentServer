
from typing import List, Dict, Any, Optional
from ai.llm.constants import DEFAULT_EMBEDDING_MODEL_PROVIDER
from apps.news.models import NewsArticle
from ai.vector.pgvector_client import PGVectorClient
import logging

from apps.users.models import UserProfile

logger = logging.getLogger(__name__)
class UserVectorExecutor:
    def __init__(self, embedding_provider: Optional[str] = None):
        self.embedding_provider = embedding_provider or DEFAULT_EMBEDDING_MODEL_PROVIDER
        self.vector_client = PGVectorClient(
            model_class=UserProfile,
            embedding_field_name='interest_embedding',
            processed_flag_field_name='is_processed_for_embedding',
            text_content_field_name='preferred_topics_text',
            embedding_provider=self.embedding_provider
        )

    def add_user_profile_embedding(self, user_profile: UserProfile, preferred_topics_text: str) -> bool:
        """
        添加用户画像到向量存储
        
        Args:
            user_profile: 用户画像对象
            
        Returns:
            是否成功添加
        """
        try:
            document_id = str(user_profile.id)
            
            # 构建用于嵌入的文本
            text_for_embedding = ""
            
            if hasattr(user_profile, 'user_self_portrait') and user_profile.user_self_portrait:
                text_for_embedding += f"个人描述: {user_profile.user_self_portrait}\n"
            
            if hasattr(user_profile, 'preferred_topics') and user_profile.preferred_topic:
                text_for_embedding += f"感兴趣话题: {user_profile.preferred_topic}\n"
                
            if hasattr(user_profile, 'excluded_topics') and user_profile.excluded_topic:
                text_for_embedding += f"不感兴趣话题: {user_profile.excluded_topic}\n"
                
            if not text_for_embedding.strip():
                logger.warning(f"{self.__class__.__name__}: 用户 {user_profile.id} 的个人资料没有可用的文本内容.")
                return False
                
            # 构建元数据
            metadata = {
                'user_id': str(user_profile.id),
                }
        
            # 添加到向量数据库
            success = self.vector_client.add_document(document_id, text_for_embedding, metadata)
            
            if success:
                logger.info(f"{self.__class__.__name__}: 成功将用户画像 {document_id} 添加到向量存储")
            else:
                logger.warning(f"{self.__class__.__name__}: 添加用户画像 {document_id} 到向量存储失败")

            return success
            
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: 添加用户画像 {getattr(user_profile, 'id', 'unknown')} 到向量存储时出错: {e}", exc_info=True)
            return False

    def update_user_profile_embedding(self, user_profile: UserProfile) -> bool:
        """更新用户画像"""
        return self.add_user_profile_embedding(user_profile)
    
    def query_similar_users(self, query_text: str, query_embedding: Optional[List[float]] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        查询相似用户
        
        Args:
            query: 查询文本
            query_embedding: 查询嵌入（如已计算）
            top_k: 返回结果数量
            
        Returns:
            相似用户列表
        """
        try:
            # 执行查询
            results = self.vector_client.query_similar_documents(
                query_text=query_text,
                query_embedding=query_embedding,
                top_k=top_k,
                distance_metric="cosine"
            )
            
            # 获取用户实例
            user_ids = [result['id'] for result in results]
            users = UserProfile.objects.filter(id__in=user_ids)
            
            # 按照相似度分数排序
            id_to_user = {str(user.id): user for user in users}
            sorted_users = []
            
            for result in results:
                user_id = str(result['id'])
                if user_id in id_to_user:
                    user = id_to_user[user_id]
                    # 将分数附加到用户对象
                    # user.similarity_score = result['score']
                    sorted_users.append(user)

            logger.info(f"{self.__class__.__name__}: 找到 {len(sorted_users)} 个相似用户")
            return sorted_users
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: 查询相似用户时出错: {e}", exc_info=True)
            return []

    def get_user_profile_embedding(self, user_profile_id: str) -> Optional[List[float]]:
        return self.vector_client.get_document_embedding(user_profile_id)
