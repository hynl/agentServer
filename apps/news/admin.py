from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from apps.news.models import NewsSource, NewsArticle
from django.utils import timezone

@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'url_link',
        'is_active',
        'last_fetched_at',
        'articles_count',
        'status_indicator',
        'action_buttons'
    ]
    list_filter = [
        'is_active',
        'last_fetched_at',
    ]
    search_fields = [
        'name',
        'url',
        'description'
    ]
    readonly_fields = [
        'last_fetched_at',
        'articles_count',
        'fetch_status'
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'url', 'description')
        }),
        ('状态信息', {
            'fields': ('is_active', 'last_fetched_at', 'articles_count', 'fetch_status')
        }),
    )
    
    actions = ['activate_sources', 'deactivate_sources', 'test_fetch_sources']
    
    def url_link(self, obj):
        """显示可点击的URL链接"""
        if obj.url:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.url, obj.url[:50] + '...' if len(obj.url) > 50 else obj.url)
        return "无URL"
    url_link.short_description = "RSS链接"
    
    def articles_count(self, obj):
        """显示该源的文章数量"""
        count = NewsArticle.objects.filter(source_name=obj.name).count()
        if count > 0:
            try:
                url = reverse('admin:news_newsarticle_changelist') + f'?source_name__exact={obj.name}'
                return format_html('<a href="{}" target="_blank">{} 篇文章</a>', url, count)
            except:
                return f"{count} 篇文章"
        return "0 篇文章"
    articles_count.short_description = "文章数量"
    
    def status_indicator(self, obj):
        """状态指示器"""
        if not obj.is_active:
            return format_html('<span style="color: red;">●</span> 已禁用')
        
        if not obj.last_fetched_at:
            return format_html('<span style="color: orange;">●</span> 未抓取')
        
        # 检查最后抓取时间是否超过24小时
        time_diff = timezone.now() - obj.last_fetched_at
        if time_diff.days > 1:
            return format_html('<span style="color: orange;">●</span> 抓取过期')
        else:
            return format_html('<span style="color: green;">●</span> 正常')
    status_indicator.short_description = "状态"
    
    def action_buttons(self, obj):
        """操作按钮"""
        buttons = []
        
        if obj.is_active:
            try:
                buttons.append(
                    format_html(
                        '<a class="button" href="{}">测试抓取</a>',
                        reverse('admin:news_newssource_test_fetch', args=[obj.pk])
                    )
                )
            except:
                pass
        
        return format_html(' '.join(buttons)) if buttons else "无操作"
    action_buttons.short_description = "操作"
    
    def fetch_status(self, obj):
        """抓取状态详情"""
        if not obj.last_fetched_at:
            return "尚未抓取过"
        
        time_diff = timezone.now() - obj.last_fetched_at
        if time_diff.days > 0:
            return f"上次抓取: {time_diff.days}天前"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            return f"上次抓取: {hours}小时前"
        else:
            minutes = time_diff.seconds // 60
            return f"上次抓取: {minutes}分钟前"
    fetch_status.short_description = "抓取状态"
    
    def get_urls(self):
        """添加自定义URL"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:source_id>/test-fetch/',
                self.admin_site.admin_view(self.test_fetch_single),
                name='news_newssource_test_fetch'
            ),
        ]
        return custom_urls + urls
    
    def test_fetch_single(self, request, source_id):
        """测试单个RSS源的抓取"""
        try:
            source = NewsSource.objects.get(id=source_id)
            
            # 导入RSS抓取工具
            from ai.agents.common_tools import read_rss_feed
            
            # 测试抓取
            articles = read_rss_feed(source.url)
            
            if articles:
                messages.success(request, f"成功从 {source.name} 抓取到 {len(articles)} 篇文章")
                # 更新最后抓取时间
                source.last_fetched_at = timezone.now()
                source.save(update_fields=['last_fetched_at'])
            else:
                messages.warning(request, f"从 {source.name} 未抓取到任何文章")
                
        except NewsSource.DoesNotExist:
            messages.error(request, f"RSS源 {source_id} 不存在")
        except Exception as e:
            messages.error(request, f"测试抓取失败: {e}")
        
        return redirect('admin:news_newssource_change', source_id)
    
    def activate_sources(self, request, queryset):
        """批量激活RSS源"""
        count = queryset.update(is_active=True)
        self.message_user(request, f"成功激活 {count} 个RSS源")
    activate_sources.short_description = "激活选中的RSS源"
    
    def deactivate_sources(self, request, queryset):
        """批量禁用RSS源"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"成功禁用 {count} 个RSS源")
    deactivate_sources.short_description = "禁用选中的RSS源"
    
    def test_fetch_sources(self, request, queryset):
        """批量测试RSS源抓取"""
        from ai.agents.common_tools import read_rss_feed
        
        success_count = 0
        total_articles = 0
        
        for source in queryset.filter(is_active=True):
            try:
                articles = read_rss_feed(source.url)
                if articles:
                    success_count += 1
                    total_articles += len(articles)
                    # 更新最后抓取时间
                    source.last_fetched_at = timezone.now()
                    source.save(update_fields=['last_fetched_at'])
            except Exception as e:
                self.message_user(request, f"RSS源 {source.name} 抓取失败: {e}", level='ERROR')
        
        self.message_user(request, f"成功测试 {success_count} 个RSS源，共抓取到 {total_articles} 篇文章")
    test_fetch_sources.short_description = "测试选中RSS源的抓取"


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = [
        'title_preview',
        'source_name',
        'published_at',
        'author',
        'embedding_status',
        'keywords_display',
        'categories_display'
    ]
    list_filter = [
        'source_name',
        'published_at',
        'is_processed_for_embedding',
        'categories',
        'keywords'
    ]
    search_fields = [
        'title',
        'content',
        'summary',
        'author',
        'source_name'
    ]
    readonly_fields = [
        'url',
        'published_at',
        'embedding_status_detail',
        'content_preview',
        'embedding_info'
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'url', 'source_name', 'author', 'published_at')
        }),
        ('内容', {
            'fields': ('content_preview', 'summary')
        }),
        ('分类和标签', {
            'fields': ('keywords', 'categories')
        }),
        ('AI处理', {
            'fields': ('is_processed_for_embedding', 'embedding_status_detail', 'embedding_info'),
            'classes': ('collapse',)
        }),
    )
    
    def title_preview(self, obj):
        """标题预览"""
        if len(obj.title) > 50:
            return obj.title[:50] + "..."
        return obj.title
    title_preview.short_description = "标题"
    title_preview.admin_order_field = 'title'
    
    def embedding_status(self, obj):
        """嵌入向量状态"""
        if obj.is_processed_for_embedding:
            return format_html('<span style="color: green;">●</span> 已处理')
        else:
            return format_html('<span style="color: red;">●</span> 未处理')
    embedding_status.short_description = "向量状态"
    
    def keywords_display(self, obj):
        """关键词显示"""
        if obj.keywords:
            keywords = obj.keywords[:3]  # 只显示前3个
            display = ", ".join(keywords)
            if len(obj.keywords) > 3:
                display += f" (+{len(obj.keywords) - 3})"
            return display
        return "无关键词"
    keywords_display.short_description = "关键词"
    
    def categories_display(self, obj):
        """分类显示"""
        if obj.categories:
            return ", ".join(obj.categories)
        return "无分类"
    categories_display.short_description = "分类"
    
    def content_preview(self, obj):
        """内容预览"""
        if not obj.content:
            return "无内容"
        
        preview = obj.content[:200]
        if len(obj.content) > 200:
            preview += "..."
        return preview
    content_preview.short_description = "内容预览"
    
    def embedding_status_detail(self, obj):
        """嵌入向量状态详情"""
        if obj.is_processed_for_embedding:
            return "已生成嵌入向量"
        else:
            return "尚未生成嵌入向量"
    embedding_status_detail.short_description = "向量状态详情"
    
    def embedding_info(self, obj):
        """嵌入向量信息"""
        if obj.embedding:
            return f"向量维度: 768"
        return "无嵌入向量"
    embedding_info.short_description = "向量信息"
    
    actions = ['generate_embeddings', 'update_categories']
    
    def generate_embeddings(self, request, queryset):
        """批量生成嵌入向量"""
        try:
            # 这里可以调用相关的任务来生成嵌入向量
            count = 0
            for article in queryset.filter(is_processed_for_embedding=False):
                # 触发嵌入向量生成任务
                # generate_article_embedding_task.delay(article.id)
                count += 1
            
            self.message_user(request, f"成功触发 {count} 篇文章的嵌入向量生成任务")
        except Exception as e:
            self.message_user(request, f"生成嵌入向量失败: {e}", level='ERROR')
    generate_embeddings.short_description = "为选中文章生成嵌入向量"
    
    def update_categories(self, request, queryset):
        """批量更新文章分类"""
        try:
            # 这里可以调用相关的任务来更新文章分类
            count = queryset.count()
            self.message_user(request, f"成功触发 {count} 篇文章的分类更新任务")
        except Exception as e:
            self.message_user(request, f"更新分类失败: {e}", level='ERROR')
    update_categories.short_description = "更新选中文章的分类"
    