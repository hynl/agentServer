import logging
from django.contrib.auth import get_user_model
from ai.agents.news_fetcher import NewsFetcherAgent
from ai.agents.orchestrator import NewsBriefingOrchestratorAgent
from ai.constants import AGENT_STATUS, REPORT_FIELDS, REPORT_STATUS, RESPONSE_FIELDS
from ai.models import NewsBriefingReport

logger = logging.getLogger(__name__)
User = get_user_model()

class NewsBriefingService:
    """
    负责协调AI Agent和Django模型的业务逻辑服务。
    """
    def __init__(self):
        self.orchestrator = NewsBriefingOrchestratorAgent()
        self.news_fetcher = NewsFetcherAgent()
        
    def fetch_news_and_embedding(self):
        """
        调用新闻抓取器和嵌入生成器，获取最新的新闻和嵌入。
        """
        logger.info(f"{self.__class__.__name__}: 开始抓取最新新闻和生成嵌入。")
        result = self.news_fetcher.run()
        logger.info(f"{self.__class__.__name__}: 已抓取 {len(result.get('articles', []))} 篇文章。")
        return result


    def create_news_briefing_report(self, user) -> NewsBriefingReport:
        
        report_instance = NewsBriefingReport.objects.create(
            user=user,
            summary="新闻简报请求已接收，正在后台生成中，请稍后刷新查看...",
            status='pending'
        )
        logger.info(f'{self.__class__.__name__}: 创建新的新闻简报报告，ID: {report_instance.id} for user {user.id}.')
        return report_instance
    
    def process_briefing_generation(self, report_id: int) -> NewsBriefingReport:
        try:
            report_instance = NewsBriefingReport.objects.get(id=report_id)
            user = report_instance.user
            report_instance.status = 'generating'
            report_instance.save(update_fields=['status'])
            user_request = f"Please generate a comprehensive financial news briefing. The user ID is {user.id} and the username is {user.username}. Focus on creating personalized content based on this user's profile and interests."
            logger.info(f"{self.__class__.__name__}: 开始生成新闻简报 for user {user.id} with report ID {report_id}.")
            orchestration_result = self.orchestrator.run(
                user_id=str(user.id), 
                user_request=user_request
            )

            if orchestration_result[RESPONSE_FIELDS['STATUS']] == AGENT_STATUS['COMPLETE']:

                report_data = orchestration_result.get('report_data', {})          
                report_instance.summary = report_data.get(REPORT_FIELDS['SUMMARY'], f"用户 {user.username} 的财经新闻简报")
                report_instance.full_report_content = report_data.get(REPORT_FIELDS['FULL_REPORT_CONTENT'], "简报生成完成")
                report_instance.key_directions = report_data.get(REPORT_FIELDS['KEY_DIRECTIONS'], {})
                report_instance.related_stocks = report_data.get(REPORT_FIELDS['RELATED_STOCKS'], [])
                report_instance.ai_impact_score = report_data.get(REPORT_FIELDS['AI_IMPACT_SCORE'], 'Medium')
                report_instance.user_profile_references = report_data.get(REPORT_FIELDS['USER_PROFILE_REFERENCES'], "用户画像信息未提供")
                report_instance.news_articles = report_data.get(REPORT_FIELDS['NEWS_ARTICLES'], [])
                report_instance.status = REPORT_STATUS['COMPLETED']
                report_instance.error_message = None
                report_instance.save()
                
                 # 处理关联新闻文章（如果存在）
                user_focused_news_articles_ids = report_data.get('user_focused_news_articles', [])
                if user_focused_news_articles_ids:
                    # 如果需要使用，需要取消注释
                    pass
                logger.info(f'{self.__class__.__name__}: 新闻简报报告 {report_id} 已成功生成 for user {user.id}.')
            elif orchestration_result.get('status') == 'ERROR':
                error_msg = orchestration_result.get('error', 'Unknown error occurred during briefing generation.')
                report_instance.status = 'failed'
                report_instance.error_message = error_msg
                report_instance.save(update_fields=['status', 'error_message'])
                logger.error(f'{self.__class__.__name__}: 新闻简报生成失败 for user {user.id} with report ID {report_id}. Error: {error_msg}')
            else:
                # 处理其他状态或没有明确状态的情况
                report_data = orchestration_result.get('report_data', {})
                if report_data:
                    report_instance.summary = report_data.get('summary', f"用户 {user.username} 的财经简报")
                    report_instance.full_report_content = report_data.get('full_report_content', "简报已生成")
                    report_instance.key_directions = report_data.get('key_directions', {})
                    report_instance.related_stocks = report_data.get('related_stocks', [])
                    report_instance.ai_impact_score = report_data.get('ai_impact_score', 'Medium')
                    report_instance.status = 'completed'
                    report_instance.error_message = None
                    report_instance.save()
                    logger.info(f'{self.__class__.__name__}: 新闻简报报告 {report_id} 已成功生成 for user {user.id}.')
                else:
                    report_instance.status = 'failed'
                    report_instance.error_message = f"Unexpected status: {orchestration_result.get('status', 'Unknown')}"
                    report_instance.save(update_fields=['status', 'error_message'])
                    logger.error(f'{self.__class__.__name__}: 新闻简报生成失败 for user {user.id} with report ID {report_id}. Error: {report_instance.error_message}')     
        except NewsBriefingReport.DoesNotExist:
            logger.error(f'{self.__class__.__name__}: 新闻简报报告 with ID {report_id} 不存在.')
            return None
        except Exception as e:
            logger.error(f'{self.__class__.__name__}: 处理用户 {user.id} 的新闻简报生成时出错，报告 ID {report_id}: {e}')
            report_instance.status = 'failed'
            report_instance.error_message = str(e)
            report_instance.save()
            return None
        
        return report_instance
    
    
    def get_user_briefing_reports(self, user) -> list:
        """
        获取指定用户的所有新闻简报报告。
        """
        reports = NewsBriefingReport.objects.filter(user=user).order_by('-generated_at')
        logger.info(f"{self.__class__.__name__}: 获取用户 {user.id} 的新闻简报报告，共计 {reports.count()} 条。")
        return reports

    def get_briefing_details(self, briefing_id: int):
        """
        获取指定ID的新闻简报报告详情。
        """
        return NewsBriefingReport.objects.get(id=briefing_id)

            
        