from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt

from ai.views import NewsBriefingDetailView, NewsBriefingListView, TriggerNewsBriefingView
from apps.users.views import UserProfileTopicsView, UserProfileView

app_name = 'ai'

urlpatterns = [
    # 路径： /api/ai/news-briefings/
    # 作用： 获取当前用户的所有新闻简报列表
    path('news-briefings/', NewsBriefingListView.as_view(), name='news-briefing-list'),
    
    # 路径： /api/ai/news-briefings/{id}/
    # 作用： 获取指定ID的新闻简报详情
    path('news-briefings/<int:pk>/', NewsBriefingDetailView.as_view(), name='news-briefing-detail'),
    
    # 路径： /api/ai/news-briefings/generate/
    # 作用： 触发为当前用户生成新的新闻简报（异步任务）
    path('news-briefings/generate/', TriggerNewsBriefingView.as_view(), name='trigger-news-briefing'),
    
    # 用户画像相关 - 超简化版
    path('profile/', UserProfileView.as_view(), name='user-profile'),  # GET/POST
    path('profile/topics/', UserProfileTopicsView.as_view(), name='user-profile-topics'),  # GET
]

