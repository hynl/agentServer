import logging
from typing import Optional
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from datetime import date

from ai.services.news_briefing_service import NewsBriefingService
from ai.tasks import generate_user_news_briefing_task
from ai.models import NewsBriefingReport
from ai.serializers import NewsBriefingReportSerializer

logger = logging.getLogger(__name__)
User = get_user_model()

class NewsBriefingListView(generics.ListAPIView):
    """
    API view to list all news briefing reports for the authenticated user.
    """
    serializer_class = NewsBriefingReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter news briefing reports by the authenticated user.
        """
        return NewsBriefingReport.objects.filter(user=self.request.user).order_by('-generated_at')

class NewsBriefingDetailView(generics.RetrieveAPIView):
    """
    API view to retrieve a specific news briefing report.
    """
    serializer_class = NewsBriefingReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Ensure users can only access their own reports.
        """
        return NewsBriefingReport.objects.filter(user=self.request.user)

class TriggerNewsBriefingView(generics.CreateAPIView):
    """
    API view to trigger the generation of a new news briefing.
    """
    serializer_class = NewsBriefingReportSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Create a new news briefing report and trigger background processing.
        """
        try:
            user = request.user
            user_request = request.data.get('user_request', '')
            
            # 创建一个 pending 状态的报告
            pending_report = NewsBriefingReport.objects.create(
                user=user,
                status='pending',
                report_date=date.today(),  # 添加当前日期
                full_report_content='',
                summary='',
                news_articles=[],  # 空的 JSON 数组
                key_directions='',
                recommendation_score=0,
                related_stocks=[],  # 空的 JSON 数组
                ai_impact_score=0
            )
            
            logger.info(f"{self.__class__.__name__}: 创建新的新闻简报报告 ID {pending_report.id} for user {user.username}.")
            
            # 仅传递report_id，任务将在后台查找并更新该报告。
            try:
                generate_user_news_briefing_task.delay(pending_report.id)
                logger.info(f"{self.__class__.__name__}: 已调度 Celery 任务，报告 ID: {pending_report.id}")
            except Exception as e:
                logger.error(f"{self.__class__.__name__}: 调度 Celery 任务失败: {e}", exc_info=True)
                pending_report.status = 'failed'
                pending_report.error_message = f"Celery task dispatch failed: {e}"
                pending_report.save(update_fields=['status', 'error_message'])
                return Response(
                    {
                        "detail": "新闻简报任务调度失败。请联系管理员。", 
                        "report_id": pending_report.id, 
                        "status": "failed",  # 修复：使用小写状态
                        "error": str(e)
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response(
                {
                    "detail": "新闻简报生成任务已启动。", 
                    "report_id": pending_report.id, 
                    "status": "pending",
                    "user_request": user_request  # 在响应中返回用户请求
                },
                status=status.HTTP_202_ACCEPTED
            )
            
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: 创建新闻简报失败: {e}", exc_info=True)
            return Response(
                {
                    "detail": "创建新闻简报失败。请重试。", 
                    "error": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            