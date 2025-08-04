from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.news.views import (
    NewsSourceViewSet,
    NewsArticleViewSet,
    NewsSearchView,
    RSSFetchView
)

# 创建路由器
router = DefaultRouter()
router.register(r'sources', NewsSourceViewSet, basename='newssource')
router.register(r'articles', NewsArticleViewSet, basename='newsarticle')

app_name = 'news'

urlpatterns = [
    # RESTful API 路由
    path('api/', include(router.urls)),
    
    # 自定义API端点
    path('api/search/', NewsSearchView.as_view(), name='news-search'),
    path('api/sources/<int:source_id>/fetch/', RSSFetchView.as_view(), name='rss-fetch'),
]
