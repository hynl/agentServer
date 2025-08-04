from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.urls import reverse
from apps.users.models import UserProfile
from ai.models import NewsBriefingReport
from ai.tasks import generate_user_news_briefing_task
import json

User = get_user_model()

class NewsBriefingInline(admin.TabularInline):
    """在用户页面显示新闻简报"""
    model = NewsBriefingReport
    extra = 0
    readonly_fields = ['status', 'report_date', 'generated_at', 'summary']
    fields = ['status', 'report_date', 'generated_at', 'summary']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 
        'user_self_portrait_preview', 
        'preferred_topics_display',
        'is_processed_for_embedding',
        'created_at',
        'action_buttons'
    ]
    list_filter = [
        'is_processed_for_embedding', 
        'created_at',
        'preferred_topic'
    ]
    search_fields = [
        'user__username', 
        'user__email', 
        'user_self_portrait'  # 删除 preferred_topic_text
    ]
    readonly_fields = [
        'id',
        'created_at', 
        'updated_at',
        'formatted_embedding',
        'profile_summary'
    ]
    
    fieldsets = (
        ('用户信息', {
            'fields': ('id', 'user', 'profile_summary')
        }),
        ('画像描述', {
            'fields': ('user_self_portrait',)  # 删除 preferred_topic_text
        }),
        ('偏好设置', {
            'fields': ('preferred_topic', 'excluded_topic')
        }),
        ('系统信息', {
            'fields': (
                'is_processed_for_embedding', 
                'formatted_embedding',
                'created_at', 
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['update_embeddings', 'generate_news_briefing']
    
    def user_link(self, obj):
        """用户链接 - 修复URL反向解析"""
        try:
            # 尝试使用正确的URL模式
            url = reverse("admin:users_user_change", args=[obj.user.pk])
            return format_html('<a href="{}">{} ({})</a>', url, obj.user.username, obj.user.email)
        except:
            # 如果反向解析失败，只显示用户名
            return f"{obj.user.username} ({obj.user.email})"
    user_link.short_description = "用户"
    user_link.admin_order_field = 'user__username'
    
    def user_self_portrait_preview(self, obj):
        """画像预览"""
        if not obj.user_self_portrait:
            return "未设置"
        
        preview = obj.user_self_portrait[:50]
        if len(obj.user_self_portrait) > 50:
            preview += "..."
        return preview
    user_self_portrait_preview.short_description = "用户画像"
    
    def preferred_topics_display(self, obj):
        """偏好话题显示"""
        if not obj.preferred_topic:
            return "未设置"
        
        topics = obj.preferred_topic[:3]  # 只显示前3个
        display = ", ".join(topics)
        if len(obj.preferred_topic) > 3:
            display += f" (+{len(obj.preferred_topic) - 3}个)"
        return display
    preferred_topics_display.short_description = "偏好话题"
    
    def action_buttons(self, obj):
        """操作按钮"""
        buttons = []
        
        # 生成新闻简报按钮
        try:
            buttons.append(
                format_html(
                    '<a class="button" href="{}">生成新闻简报</a>',
                    reverse('admin:users_userprofile_generate_briefing', args=[obj.pk])
                )
            )
        except:
            pass
        
        # 更新嵌入向量按钮
        if not obj.is_processed_for_embedding:
            try:
                buttons.append(
                    format_html(
                        '<a class="button" href="{}">更新嵌入向量</a>',
                        reverse('admin:users_userprofile_update_embedding', args=[obj.pk])
                    )
                )
            except:
                pass
        
        return format_html(' '.join(buttons)) if buttons else "无操作"
    action_buttons.short_description = "操作"
    
    def formatted_embedding(self, obj):
        """格式化显示嵌入向量"""
        if not obj.interest_embedding:
            return "无嵌入向量"
        
        try:
            embedding = obj.interest_embedding
            if isinstance(embedding, list):
                return f"向量维度: {len(embedding)}, 前5个值: {embedding[:5]}"
            elif hasattr(embedding, '__len__'):
                return f"向量长度: {len(embedding)}"
            else:
                return "嵌入向量已设置"
        except:
            return "嵌入向量格式错误"
    formatted_embedding.short_description = "嵌入向量"
    
    def profile_summary(self, obj):
        """画像摘要"""
        summary = []
        summary.append(f"用户: {obj.user.username}")
        summary.append(f"邮箱: {obj.user.email}")
        summary.append(f"偏好话题数: {len(obj.preferred_topic) if obj.preferred_topic else 0}")
        summary.append(f"排除话题数: {len(obj.excluded_topic) if obj.excluded_topic else 0}")
        summary.append(f"嵌入状态: {'已处理' if obj.is_processed_for_embedding else '未处理'}")
        
        return format_html('<br>'.join(summary))
    profile_summary.short_description = "画像摘要"
    
    def update_embeddings(self, request, queryset):
        """批量更新嵌入向量"""
        try:
            from ai.tasks import update_user_profile_embedding_task
            count = 0
            for profile in queryset:
                try:
                    update_user_profile_embedding_task.delay(profile.id)
                    count += 1
                except Exception as e:
                    self.message_user(request, f"更新用户 {profile.user.username} 的嵌入向量失败: {e}", level='ERROR')
            
            self.message_user(request, f"成功触发 {count} 个用户的嵌入向量更新任务")
        except ImportError:
            self.message_user(request, "无法导入更新任务模块", level='ERROR')
    update_embeddings.short_description = "更新选中用户的嵌入向量"
    
    def generate_news_briefing(self, request, queryset):
        """批量生成新闻简报"""
        try:
            count = 0
            for profile in queryset:
                try:
                    # 创建新闻简报报告
                    from datetime import date
                    report = NewsBriefingReport.objects.create(
                        user=profile.user,
                        status='pending',
                        report_date=date.today(),
                        full_report_content='',
                        summary='',
                        key_directions={},
                        related_stocks=[],
                        ai_impact_score=0
                    )
                    
                    # 触发生成任务
                    generate_user_news_briefing_task.delay(report.id)
                    count += 1
                except Exception as e:
                    self.message_user(request, f"为用户 {profile.user.username} 生成新闻简报失败: {e}", level='ERROR')
            
            self.message_user(request, f"成功触发 {count} 个用户的新闻简报生成任务")
        except Exception as e:
            self.message_user(request, f"批量生成新闻简报失败: {e}", level='ERROR')
    generate_news_briefing.short_description = "为选中用户生成新闻简报"
    
    def get_urls(self):
        """添加自定义URL - 修复UUID路径问题"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:profile_id>/generate-briefing/',
                self.admin_site.admin_view(self.generate_single_briefing),
                name='users_userprofile_generate_briefing'
            ),
            path(
                '<path:profile_id>/update-embedding/',
                self.admin_site.admin_view(self.update_single_embedding),
                name='users_userprofile_update_embedding'
            ),
        ]
        return custom_urls + urls
    
    def generate_single_briefing(self, request, profile_id):
        """为单个用户生成新闻简报"""
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        from datetime import date
        
        try:
            profile = get_object_or_404(UserProfile, id=profile_id)
            
            report = NewsBriefingReport.objects.create(
                user=profile.user,
                status='pending',
                report_date=date.today(),
                full_report_content='',
                summary='',
                key_directions={},
                related_stocks=[],
                ai_impact_score=0
            )
            
            generate_user_news_briefing_task.delay(report.id)
            messages.success(request, f"为用户 {profile.user.username} 的新闻简报生成任务已启动")
        except Exception as e:
            messages.error(request, f"启动新闻简报生成任务失败: {e}")
        
        return redirect('admin:users_userprofile_change', profile_id)
    
    def update_single_embedding(self, request, profile_id):
        """更新单个用户的嵌入向量"""
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        
        try:
            profile = get_object_or_404(UserProfile, id=profile_id)
            
            from ai.tasks import update_user_profile_embedding_task
            update_user_profile_embedding_task.delay(profile.id)
            messages.success(request, f"用户 {profile.user.username} 的嵌入向量更新任务已启动")
        except Exception as e:
            messages.error(request, f"启动嵌入向量更新任务失败: {e}")
        
        return redirect('admin:users_userprofile_change', profile_id)

# 扩展用户Admin
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = '用户画像'
    fields = ['user_self_portrait', 'preferred_topic', 'excluded_topic']  # 删除 preferred_topic_text

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, NewsBriefingInline)
    
    def get_inline_instances(self, request, obj=None):
        """只有在编辑现有用户时才显示内联"""
        if obj:
            return super().get_inline_instances(request, obj)
        return []

# 检查是否已经注册，避免重复注册错误
if admin.site.is_registered(User):
    admin.site.unregister(User)

# 注册用户管理
admin.site.register(User, UserAdmin)
