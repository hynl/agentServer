from django.contrib.auth import get_user_model
from rest_framework import serializers

from ai.models import NewsBriefingReport
from apps.news.models import NewsArticle
from apps.users.models import User
from django.contrib.auth import get_user_model
from rest_framework import serializers

from ai.models import NewsBriefingReport
from apps.news.models import NewsArticle
from apps.users.models import User, UserProfile  # 添加UserProfile导入

User = get_user_model()


class NewsArticleMinimalSerializer(serializers.ModelSerializer):
    
    source_name = serializers.CharField(source='source.name', read_only=True)
    
    class Meta:
        model = NewsArticle
        fields = ['id', 'title', 'url', 'source_name']
        read_only_fields = fields # All fields read-only for this serializer
        
class NewsBriefingReportSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_focused_news_articles_details = NewsArticleMinimalSerializer(source='user_focused_news_articles', many=True, read_only=True)
    
    class Meta:
        model = NewsBriefingReport
        fields = [
            'id', 
            'user_username', 
            'generated_at', 
            'report_date',
            'news_articles', 
            'summary', 
            'full_report_content', 
            'key_directions',
            'recommendation_score', 
            'related_stocks', 
            'ai_impact_score',
            'status', 
            'error_message', 
            'user_focused_news_articles_details'
        ]
        read_only_fields = fields
        
        
        
class TriggerBriefingSerializer(serializers.Serializer):
    """
    用于触发新闻简报生成请求的空序列化器，主要用于DRF的API文档。
    """
    # 无需输入，用户通过认证获取
    pass
        

class UserProfileSerializer(serializers.ModelSerializer):
    """用户画像序列化器"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id',
            'user_id',
            'user_username',
            'user_self_portrait',
            'preferred_topic',
            'excluded_topic',
            'is_processed_for_embedding',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user_id', 'user_username', 'is_processed_for_embedding', 'created_at', 'updated_at']

    def validate_preferred_topic(self, value):
        """验证偏好话题"""
        if not isinstance(value, list):
            raise serializers.ValidationError("偏好话题必须是数组格式")
        
        # 验证话题选项
        valid_topics = ['财经', '股市', '投资', '基金', '债券', '外汇', '期货', '保险', '银行', '房地产', 
                       '科技', '新能源', '医药', '消费', '制造业', '服务业', '政策', '国际']
        
        for topic in value:
            if topic not in valid_topics:
                raise serializers.ValidationError(f"无效的话题选项: {topic}")
        
        return value

    def validate_excluded_topic(self, value):
        """验证排除话题"""
        if not isinstance(value, list):
            raise serializers.ValidationError("排除话题必须是数组格式")
        return value

    def validate_user_self_portrait(self, value):
        """验证用户画像描述"""
        if value and len(value.strip()) < 10:
            raise serializers.ValidationError("用户画像描述至少需要10个字符")
        return value

class UserProfileCreateUpdateSerializer(serializers.ModelSerializer):
    """用于创建和更新用户画像的序列化器"""
    
    class Meta:
        model = UserProfile
        fields = [
            'user_self_portrait',
            'preferred_topic',
            'excluded_topic'
        ]

    def validate_preferred_topic(self, value):
        """验证偏好话题"""
        if not isinstance(value, list):
            raise serializers.ValidationError("偏好话题必须是数组格式")
        
        valid_topics = ['财经', '股市', '投资', '基金', '债券', '外汇', '期货', '保险', '银行', '房地产', 
                       '科技', '新能源', '医药', '消费', '制造业', '服务业', '政策', '国际']
        
        for topic in value:
            if topic not in valid_topics:
                raise serializers.ValidationError(f"无效的话题选项: {topic}")
        
        if len(value) > 10:
            raise serializers.ValidationError("最多只能选择10个偏好话题")
        
        return value

    def validate_excluded_topic(self, value):
        """验证排除话题"""
        if not isinstance(value, list):
            raise serializers.ValidationError("排除话题必须是数组格式")
        
        if len(value) > 5:
            raise serializers.ValidationError("最多只能选择5个排除话题")
        
        return value

    def validate_user_self_portrait(self, value):
        """验证用户画像描述"""
        if value:
            if len(value.strip()) < 10:
                raise serializers.ValidationError("用户画像描述至少需要10个字符")
            if len(value.strip()) > 500:
                raise serializers.ValidationError("用户画像描述不能超过500个字符")
        return value


    