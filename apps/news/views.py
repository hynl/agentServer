from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from apps.news.models import NewsSource, NewsArticle
from apps.news.serializers import (
    NewsSourceSerializer,
    NewsSourceCreateUpdateSerializer,
    NewsArticleSerializer,
    NewsArticleDetailSerializer,
    NewsArticleSearchSerializer
)
import logging

logger = logging.getLogger(__name__)

class NewsSourceViewSet(viewsets.ModelViewSet):
    """RSS新闻源管理ViewSet"""
    queryset = NewsSource.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return NewsSourceCreateUpdateSerializer
        return NewsSourceSerializer
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def test_fetch(self, request, pk=None):
        """测试RSS源抓取"""
        source = self.get_object()
        
        try:
            # 导入RSS抓取工具
            from ai.agents.common_tools import read_rss_feed
            
            # 测试抓取
            articles = read_rss_feed(source.url)
            
            if articles:
                # 更新最后抓取时间
                source.last_fetched_at = timezone.now()
                source.save(update_fields=['last_fetched_at'])
                
                return Response({
                    'success': True,
                    'message': f'成功抓取到 {len(articles)} 篇文章',
                    'articles_count': len(articles),
                    'last_fetched_at': source.last_fetched_at
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': '未抓取到任何文章'
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"RSS抓取失败: {e}")
            return Response({
                'success': False,
                'message': f'抓取失败: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def batch_fetch(self, request):
        """批量抓取所有活跃的RSS源"""
        active_sources = self.queryset.filter(is_active=True)
        
        results = []
        total_articles = 0
        
        for source in active_sources:
            try:
                from ai.agents.common_tools import read_rss_feed
                articles = read_rss_feed(source.url)
                
                if articles:
                    source.last_fetched_at = timezone.now()
                    source.save(update_fields=['last_fetched_at'])
                    total_articles += len(articles)
                    
                results.append({
                    'source_id': source.id,
                    'source_name': source.name,
                    'success': True,
                    'articles_count': len(articles) if articles else 0
                })
                
            except Exception as e:
                results.append({
                    'source_id': source.id,
                    'source_name': source.name,
                    'success': False,
                    'error': str(e)
                })
        
        return Response({
            'success': True,
            'total_sources': len(active_sources),
            'total_articles': total_articles,
            'results': results
        }, status=status.HTTP_200_OK)

class NewsArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """新闻文章ViewSet（只读）"""
    queryset = NewsArticle.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return NewsArticleDetailSerializer
        return NewsArticleSerializer
    
    def get_queryset(self):
        """自定义查询集，支持筛选"""
        queryset = NewsArticle.objects.all()
        
        # 按来源筛选
        source_name = self.request.query_params.get('source_name')
        if source_name:
            queryset = queryset.filter(source_name=source_name)
        
        # 按分类筛选
        categories = self.request.query_params.getlist('categories')
        if categories:
            queryset = queryset.filter(categories__overlap=categories)
        
        # 按关键词筛选
        keywords = self.request.query_params.getlist('keywords')
        if keywords:
            queryset = queryset.filter(keywords__overlap=keywords)
        
        # 按时间范围筛选
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(published_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(published_at__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """获取所有文章分类"""
        from django.db.models import Func, CharField
        from django.db.models.functions import Cast
        
        # 获取所有分类（去重）
        categories = []
        articles_with_categories = NewsArticle.objects.exclude(categories=[])
        
        for article in articles_with_categories:
            if article.categories:
                categories.extend(article.categories)
        
        unique_categories = list(set(categories))
        
        return Response({
            'categories': sorted(unique_categories),
            'count': len(unique_categories)
        })
    
    @action(detail=False, methods=['get'])
    def keywords(self, request):
        """获取所有文章关键词"""
        keywords = []
        articles_with_keywords = NewsArticle.objects.exclude(keywords=[])
        
        for article in articles_with_keywords:
            if article.keywords:
                keywords.extend(article.keywords)
        
        # 统计关键词频率
        from collections import Counter
        keyword_counts = Counter(keywords)
        
        # 返回前50个最常见的关键词
        top_keywords = [
            {'keyword': keyword, 'count': count}
            for keyword, count in keyword_counts.most_common(50)
        ]
        
        return Response({
            'keywords': top_keywords,
            'total_unique': len(keyword_counts)
        })

class NewsSearchView(generics.GenericAPIView):
    """新闻搜索API"""
    serializer_class = NewsArticleSearchSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def post(self, request, *args, **kwargs):
        """执行新闻搜索"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        query = serializer.validated_data['query']
        source_name = serializer.validated_data.get('source_name')
        categories = serializer.validated_data.get('categories', [])
        keywords = serializer.validated_data.get('keywords', [])
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')
        limit = serializer.validated_data.get('limit', 20)
        
        # 构建查询
        queryset = NewsArticle.objects.all()
        
        # 文本搜索（标题、内容、摘要）
        text_query = Q(title__icontains=query) | Q(content__icontains=query) | Q(summary__icontains=query)
        queryset = queryset.filter(text_query)
        
        # 其他筛选条件
        if source_name:
            queryset = queryset.filter(source_name=source_name)
        if categories:
            queryset = queryset.filter(categories__overlap=categories)
        if keywords:
            queryset = queryset.filter(keywords__overlap=keywords)
        if start_date:
            queryset = queryset.filter(published_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(published_at__lte=end_date)
        
        # 排序和限制
        queryset = queryset.order_by('-published_at')[:limit]
        
        # 序列化结果
        serializer = NewsArticleSerializer(queryset, many=True)
        
        return Response({
            'query': query,
            'count': len(serializer.data),
            'limit': limit,
            'results': serializer.data
        }, status=status.HTTP_200_OK)

class RSSFetchView(generics.GenericAPIView):
    """RSS抓取API"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, source_id, *args, **kwargs):
        """抓取指定RSS源的最新文章"""
        source = get_object_or_404(NewsSource, id=source_id)
        
        if not source.is_active:
            return Response({
                'success': False,
                'message': 'RSS源已被禁用'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 导入RSS抓取和保存工具
            from ai.agents.common_tools import read_rss_feed
            
            # 抓取文章
            articles = read_rss_feed(source.url)
            
            if not articles:
                return Response({
                    'success': True,
                    'message': '未抓取到新文章',
                    'articles_count': 0
                }, status=status.HTTP_200_OK)
            
            # 保存文章到数据库
            new_articles_count = 0
            for article_data in articles:
                article, created = NewsArticle.objects.get_or_create(
                    url=article_data['url'],
                    defaults={
                        'title': article_data.get('title', ''),
                        'source_name': source.name,
                        'published_at': article_data.get('published_at', timezone.now()),
                        'content': article_data.get('content', ''),
                        'author': article_data.get('author', ''),
                        'summary': article_data.get('summary', ''),
                    }
                )
                if created:
                    new_articles_count += 1
            
            # 更新RSS源的最后抓取时间
            source.last_fetched_at = timezone.now()
            source.save(update_fields=['last_fetched_at'])
            
            return Response({
                'success': True,
                'message': f'成功抓取并保存 {new_articles_count} 篇新文章',
                'total_fetched': len(articles),
                'new_articles': new_articles_count,
                'last_fetched_at': source.last_fetched_at
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"RSS抓取失败: {e}")
            return Response({
                'success': False,
                'message': f'抓取失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            