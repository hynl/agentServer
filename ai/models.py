from django.db import models
from django.contrib.postgres.fields import ArrayField
from apps.news.models import NewsArticle
from apps.users.models import User


class NewsBriefingReport(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='news_briefing_reports',
        verbose_name="User"
    )
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name="Report Generated At")
    report_date = models.DateField(db_index=True)
    news_articles = ArrayField(models.CharField(max_length=500), blank=True, default=list, verbose_name="News Articles")
    summary = models.TextField(null=True, blank=True, verbose_name="Report Summary")
    full_report_content = models.TextField(null=True, blank=True, verbose_name="Full Report Content")
    key_directions = models.JSONField(null=True, blank=True, verbose_name="Key Directions")
    recommendation_score = models.IntegerField(default=0, verbose_name="Recommendation Score")
    related_stocks = models.JSONField(null=True, blank=True, verbose_name="Related Stocks")
    ai_impact_score = models.TextField(blank=True, null=True, verbose_name="AI Impact Score")
    user_profile_references = models.TextField(null=True, blank=True, verbose_name="User Profile References")
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ("generating", "Generating"),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ],
        default='pending',
        verbose_name="Status"
    )
    error_message = models.TextField(null=True, blank=True, verbose_name="Error Message")
    # user_focused_news_articles = models.ManyToManyField(NewsArticle, blank=True, related_name='focused_reports', verbose_name="User Focused News Articles") 

    class Meta:
        ordering = ['-report_date']
        verbose_name = "News Briefing Report"
        verbose_name_plural = "News Briefing Reports"

    def __str__(self):
        return f"Report for User {self.user_id} on {self.report_date}"
    
    def to_celery_dict(self):
        """为Celery任务提供安全的序列化数据"""
        return {
            'id': self.id,
            'user_id': self.user.id,
            'user_username': getattr(self.user, 'username', None),
            'summary': self.summary,
            'full_report_content': self.full_report_content,
            'key_directions': self.key_directions,
            'related_stocks': self.related_stocks,
            'ai_impact_score': self.ai_impact_score,
            'user_profile_references': self.user_profile_references,
            'status': self.status,
            'error_message': self.error_message,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
        }
    