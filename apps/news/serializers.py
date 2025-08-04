from rest_framework import serializers
from apps.news.models import NewsSource, NewsArticle
from django.utils import timezone

class NewsSourceSerializer(serializers.ModelSerializer):
    """RSS新闻源序列化器"""
    articles_count = serializers.SerializerMethodField()
    last_fetch_status = serializers.SerializerMethodField()
    
    class Meta:
        model = NewsSource
        fields = [
            'id',
            'name',
            'url',
            'description',
            'is_active',
            'last_fetched_at',
            'articles_count',
            'last_fetch_status'
        ]
        read_only_fields = ['id', 'last_fetched_at', 'articles_count', 'last_fetch_status']
    
    def get_articles_count(self, obj):
        """获取该源的文章数量"""
        return NewsArticle.objects.filter(source_name=obj.name).count()
    
    def get_last_fetch_status(self, obj):
        """获取最后抓取状态"""
        if not obj.last_fetched_at:
            return "never_fetched"
        
        time_diff = timezone.now() - obj.last_fetched_at
        if time_diff.days > 1:
            return "outdated"
        elif time_diff.seconds > 3600:
            return "recent"
        else:
            return "fresh"

class NewsSourceCreateUpdateSerializer(serializers.ModelSerializer):
    """RSS新闻源创建/更新序列化器"""
    
    class Meta:
        model = NewsSource
        fields = ['name', 'url', 'description', 'is_active']
    
    def validate_url(self, value):
        """验证RSS URL"""
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("URL必须以http://或https://开头")
        return value
    
    def validate_name(self, value):
        """验证名称"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("名称至少需要2个字符")
        return value.strip()

class NewsArticleSerializer(serializers.ModelSerializer):
    """新闻文章序列化器"""
    keywords_display = serializers.SerializerMethodField()
    categories_display = serializers.SerializerMethodField()
    content_preview = serializers.SerializerMethodField()
    embedding_status = serializers.SerializerMethodField()
    
    class Meta:
        model = NewsArticle
        fields = [
            'id',
            'title',
            'url',
            'source_name',
            'published_at',
            'author',
            'summary',
            'content_preview',
            'keywords',
            'categories',
            'keywords_display',
            'categories_display',
            'is_processed_for_embedding',
            'embedding_status'
        ]
        read_only_fields = [
            'id', 'url', 'source_name', 'published_at', 'author',
            'content_preview', 'keywords_display', 'categories_display',
            'is_processed_for_embedding', 'embedding_status'
        ]
    
    def get_keywords_display(self, obj):
        """关键词显示"""
        if obj.keywords:
            return ", ".join(obj.keywords[:5])  # 最多显示5个关键词
        return "无关键词"
    
    def get_categories_display(self, obj):
        """分类显示"""
        if obj.categories:
            return ", ".join(obj.categories)
        return "无分类"
    
    def get_content_preview(self, obj):
        """内容预览"""
        if obj.content:
            return obj.content[:200] + "..." if len(obj.content) > 200 else obj.content
        return "无内容"
    
    def get_embedding_status(self, obj):
        """嵌入向量状态"""
        return "已处理" if obj.is_processed_for_embedding else "未处理"

class NewsArticleDetailSerializer(NewsArticleSerializer):
    """新闻文章详情序列化器"""
    content = serializers.CharField(read_only=True)
    
    class Meta(NewsArticleSerializer.Meta):
        fields = NewsArticleSerializer.Meta.fields + ['content']

class NewsArticleSearchSerializer(serializers.Serializer):
    """新闻搜索序列化器"""
    query = serializers.CharField(max_length=200, required=True, help_text="搜索关键词")
    source_name = serializers.CharField(max_length=100, required=False, help_text="指定新闻源")
    categories = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        help_text="分类筛选"
    )
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        help_text="关键词筛选"
    )
    start_date = serializers.DateTimeField(required=False, help_text="开始时间")
    end_date = serializers.DateTimeField(required=False, help_text="结束时间")
    limit = serializers.IntegerField(min_value=1, max_value=100, default=20, help_text="返回数量限制")
    
    def validate(self, data):
        """验证搜索参数"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("开始时间必须早于结束时间")
        
        return data
    