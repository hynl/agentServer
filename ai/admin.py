import logging
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.shortcuts import redirect
from django.contrib import messages
from ai.models import NewsBriefingReport
from ai.tasks import generate_user_news_briefing_task
from datetime import date

logger = logging.getLogger(__name__)

@admin.register(NewsBriefingReport)
class NewsBriefingReportAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user_link',
        'status', 
        'report_date',
        'generated_at',
        'summary_preview',
        'ai_impact_score',
        'action_buttons'
    ]
    list_display_links = ['id', 'summary_preview', 'user_link']
    
    list_filter = [
        'status',
        'report_date',
        'generated_at',
        'ai_impact_score'
    ]
    search_fields = [
        'user__username',
        'user__email',
        'summary',
        'full_report_content'
    ]
    readonly_fields = [
        'id',
        'generated_at',
        'formatted_key_directions',
        'formatted_related_stocks',
        'formatted_news_articles',
        'formatted_user_profile_references'
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'user', 'status', 'report_date', 'generated_at')
        }),
        ('报告内容', {
            'fields': ('summary', 'full_report_content', 'formatted_news_articles')
        }),
        ('用户关联信息', {
            'fields': ('formatted_user_profile_references',),
        }),
        ('AI 分析', {
            'fields': (
                'ai_impact_score',
                'recommendation_score',
                'formatted_key_directions',
                'formatted_related_stocks'
            )
        }),
        ('系统信息', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def user_link(self, obj):
        """用户链接 - 修复URL反向解析"""
        try:
            url = reverse("admin:users_user_change", args=[obj.user.pk])
            return format_html('<a href="{}">{} ({})</a>', url, obj.user.username, obj.user.email)
        except:
            return f"{obj.user.username} ({obj.user.email})"
    user_link.short_description = "用户"
    user_link.admin_order_field = 'user__username'
    
    def summary_preview(self, obj):
        """摘要预览"""
        if not obj.summary:
            return "无摘要"
        
        preview = obj.summary[:100]
        if len(obj.summary) > 100:
            preview += "..."
        return preview
    summary_preview.short_description = "摘要预览"
    
    def json_pretty_print(self, obj_dict):
        """将JSON字典转换为漂亮的HTML格式"""
        if not obj_dict:
            return ""
        
        html = "<dl>"
        for key, value in obj_dict.items():
            html += f"<dt><strong>{key}</strong></dt>"
            
            # 递归处理嵌套字典
            if isinstance(value, dict):
                html += f"<dd>{self.json_pretty_print(value)}</dd>"
            # 处理列表
            elif isinstance(value, list):
                html += "<dd><ul>"
                for item in value:
                    if isinstance(item, dict):
                        html += f"<li>{self.json_pretty_print(item)}</li>"
                    else:
                        html += f"<li>{item}</li>"
                html += "</ul></dd>"
            # 处理基本类型
            else:
                html += f"<dd>{value}</dd>"
        
        html += "</dl>"
        return html
    
    def formatted_key_directions(self, obj):
        """格式化显示关键方向"""
        if not obj.key_directions:
            return "无关键方向"
        
        try:
            return format_html(self.json_pretty_print(obj.key_directions))
        except:
            return str(obj.key_directions)
    formatted_key_directions.short_description = "关键方向"
    
    def formatted_related_stocks(self, obj):
        """格式化显示相关股票"""
        if not obj.related_stocks:
            return "无相关股票"
        
        try:
            if isinstance(obj.related_stocks, list):
                return format_html("<ul>{}</ul>", "".join([f"<li>{stock}</li>" for stock in obj.related_stocks]))
            else:
                return str(obj.related_stocks)
        except:
            return "格式错误"
    formatted_related_stocks.short_description = "相关股票"
    
    def formatted_news_articles(self, obj):
        """最简单的新闻文章显示方法"""
        from django.utils.safestring import mark_safe
        
        if not obj.news_articles:
            return "无新闻文章"
        
        try:
            # 将所有复杂对象转换为字符串表示
            articles_str = str(obj.news_articles)
            # 限制长度以避免显示过大的对象
            if len(articles_str) > 1000:
                articles_str = articles_str[:1000] + "..."
            # 返回预格式化文本
            return mark_safe(f"<pre>{articles_str}</pre>")
        except:
            return "无法显示新闻文章"

    formatted_news_articles.short_description = "新闻文章列表"
    
    def formatted_user_profile_references(self, obj):
        """格式化显示用户画像引用"""
        import html
        
        if not obj.user_profile_references:
            return "无用户画像引用"
        
        try:
            # 直接构建HTML字符串，不使用format_html的参数替换
            escaped_content = html.escape(str(obj.user_profile_references))
            html_content = f"<div>{escaped_content}</div>"
            return format_html(html_content)  # format_html仅用于标记字符串为安全HTML
        except Exception as e:
            return f"格式化错误: {str(e)}"
    formatted_user_profile_references.short_description = "用户画像引用"
    
    def action_buttons(self, obj):
        """操作按钮"""
        buttons = []
        
        # 添加查看详情按钮
        try:
            buttons.append(
                format_html(
                    '<a class="button" href="{}">查看详情</a>',
                    reverse('admin:ai_newsbriefingreport_change', args=[obj.pk])
                )
            )
        except:
            pass
            
        if obj.status in ['failed', 'pending']:
            try:
                buttons.append(
                    format_html(
                        '<a class="button" href="{}">重新生成</a>',
                        reverse('admin:ai_newsbriefingreport_regenerate', args=[obj.pk])
                    )
                )
            except:
                pass
        
        return format_html(' '.join(buttons)) if buttons else "无操作"
    action_buttons.short_description = "操作"
    
    # 其余代码保持不变...