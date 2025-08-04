from dj_rest_auth.serializers import UserDetailsSerializer
from rest_framework import viewsets, permissions, generics, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from apps.users.models import User, UserProfile
from apps.users.serializers import UserPublicSerializer
import logging

logger = logging.getLogger(__name__)

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.filter(is_active=True)
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'me':
            return UserDetailsSerializer
        return UserPublicSerializer

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request, *args, **kwargs):
        user = self.request.user
        serializer = UserDetailsSerializer(user, context={'request': request})
        return Response(serializer.data)

class UserProfileView(generics.GenericAPIView):
    """
    用户画像API
    GET: 获取用户画像（如果不存在则创建默认画像）
    POST: 创建或更新用户画像
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        # 我们需要导入序列化器
        from ai.serializers import UserProfileSerializer, UserProfileCreateUpdateSerializer
        if self.request.method == 'GET':
            return UserProfileSerializer
        return UserProfileCreateUpdateSerializer

    def get_object(self):
        """获取当前用户的画像，如果不存在则创建默认画像"""
        user = self.request.user
        try:
            profile = UserProfile.objects.get(user=user)
            return profile
        except UserProfile.DoesNotExist:
            # 创建默认用户画像 - 删除 preferred_topic_text 引用
            profile = UserProfile.objects.create(
                user=user,
                user_self_portrait=f'{user.username}是一位关注财经市场动态的投资者',
                preferred_topic=['财经', '股市', '投资'],
                excluded_topic=[],
                # 删除这行：preferred_topic_text='关注股市行情、财经新闻、投资机会和市场分析',
                is_processed_for_embedding=False
            )
            logger.info(f"为用户 {user.id} 创建了默认画像")
            return profile

    def get(self, request, *args, **kwargs):
        """获取用户画像"""
        profile = self.get_object()
        from ai.serializers import UserProfileSerializer
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """创建或更新用户画像"""
        user = request.user
        from ai.serializers import UserProfileSerializer, UserProfileCreateUpdateSerializer
        
        try:
            # 尝试获取现有画像
            profile = UserProfile.objects.get(user=user)
            # 如果存在，则更新
            serializer = UserProfileCreateUpdateSerializer(profile, data=request.data)
            action_type = "更新"
            status_code = status.HTTP_200_OK
        except UserProfile.DoesNotExist:
            # 如果不存在，则创建
            serializer = UserProfileCreateUpdateSerializer(data=request.data)
            action_type = "创建"
            status_code = status.HTTP_201_CREATED

        if serializer.is_valid():
            if action_type == "创建":
                # 创建新画像
                profile = serializer.save(
                    user=user,
                    is_processed_for_embedding=False
                )
                logger.info(f"用户 {user.id} 创建了新的画像")
            else:
                # 更新现有画像
                profile = serializer.save(is_processed_for_embedding=False)
                logger.info(f"用户 {user.id} 更新了画像")

            # 异步更新嵌入向量
            self._schedule_embedding_update(profile)

            # 返回完整的画像信息
            response_serializer = UserProfileSerializer(profile)
            return Response(response_serializer.data, status=status_code)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _schedule_embedding_update(self, profile):
        """调度嵌入向量更新任务"""
        try:
            from ai.tasks import update_user_profile_embedding_task
            update_user_profile_embedding_task.delay(profile.id)
            logger.info(f"已调度用户 {profile.user.id} 的嵌入向量更新任务")
        except Exception as e:
            logger.error(f"调度嵌入向量更新任务失败: {e}")

class UserProfileTopicsView(generics.GenericAPIView):
    """
    获取可用的话题选项
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """返回所有可用的话题选项"""
        topics = {
            "available_topics": [
                "财经", "股市", "投资", "基金", "债券", "外汇", "期货", 
                "保险", "银行", "房地产", "科技", "新能源", "医药", 
                "消费", "制造业", "服务业", "政策", "国际"
            ],
            "recommended_topics": ["财经", "股市", "投资", "基金"],
            "description": "选择您感兴趣的话题，系统将为您推荐相关的财经新闻"
        }
        
        return Response(topics, status=status.HTTP_200_OK)
    