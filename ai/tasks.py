import logging
import time
import os
import traceback
from celery import shared_task
from ai.services.news_briefing_service import NewsBriefingService


logger = logging.getLogger(__name__)

@shared_task
def debug_env_vars():
    """调试环境变量的任务"""
    try:
        # 检查所有环境变量
        openai_key = os.environ.get('OPENAI_API_KEY')
        openai_key_getenv = os.getenv('OPENAI_API_KEY')
        
        logger.info(f"os.environ.get('OPENAI_API_KEY'): {openai_key[:10] if openai_key else 'None'}...")
        logger.info(f"os.getenv('OPENAI_API_KEY'): {openai_key_getenv[:10] if openai_key_getenv else 'None'}...")
        
        # 检查 Django settings
        try:
            from django.conf import settings
            settings_key = getattr(settings, 'OPENAI_API_KEY', 'Not found')
            logger.info(f"Django settings OPENAI_API_KEY: {settings_key[:10] if settings_key and settings_key != 'Not found' else settings_key}...")
        except Exception as e:
            logger.error(f"Django settings error: {e}")
        
        # 打印所有环境变量中包含 OPENAI 的
        openai_vars = {k: v for k, v in os.environ.items() if 'OPENAI' in k}
        logger.info(f"所有包含 OPENAI 的环境变量: {list(openai_vars.keys())}")
        
        return {
            'environ_get': openai_key[:10] if openai_key else None,
            'getenv': openai_key_getenv[:10] if openai_key_getenv else None,
            'all_openai_vars': list(openai_vars.keys())
        }
    except Exception as e:
        logger.error(f"调试环境变量时出错: {e}")
        return f"Error: {e}"


@shared_task
def debug_task_test(message, duration = 5):
    logger.info(f"------CELERY DEBUG TASK------")
    logger.info(f'Request: {message!r}')
    print(f"Duration: {duration}")
    time.sleep(duration)
    print(f"Task Complete")
    

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def fetch_and_process_news(self):
    """
    周期性任务：从RSS源抓取新闻并处理嵌入。
    """
    
    try:
        from ai.services.news_briefing_service import NewsBriefingService
        service = NewsBriefingService() 
        logger.info(f"{self.__class__.__name__}: 实例创建成功: {type(service)}, 正在抓取新闻...")
        result = service.fetch_news_and_embedding()
        if result.get('error'):
            logger.error(f"{self.__class__.__name__}: 抓取新闻时出错: {result['error']}")
            raise Exception(result['error'])
        logger.info(f"{self.__class__.__name__}: 成功抓取 {len(result.get('articles', []))} 篇文章.")
    except Exception as e:
        logger.error(f"{self.__class__.__name__}: fetch_and_process_news 任务出错: {str(e)}")
        self.retry(exc=e)
        
        
@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def generate_user_news_briefing_task(self, report_id: int):
    """
    周期性任务：为用户生成新闻简报。
    """
    logger.info(f"{self.__class__.__name__}: 🚀 [TASK START] 报告: {report_id} Task 开始")

    try:
        from ai.services.news_briefing_service import NewsBriefingService
        logger.info(f"{self.__class__.__name__}: ✅ [STEP 1] 开始执行任务: generate_user_news_briefing_task, 报告 ID: {report_id}")

        service = NewsBriefingService()
        logger.info(f"{self.__class__.__name__}: ✅ [STEP 2] 实例创建成功: {type(service)}")

        report_instance = service.process_briefing_generation(report_id)
        logger.info(f"{self.__class__.__name__}: ✅ [STEP 3] 方法调用成功，返回: {report_instance}")


        if not report_instance:
            logger.error(f"{self.__class__.__name__}: ❌ [STEP 4] 返回 None")
            raise Exception("Failed to process news briefing generation.")

        logger.info(f"{self.__class__.__name__}: 📊 [STEP 4] 报告状态: {report_instance.status}")
        if report_instance.status == 'completed':
            logger.info(f"{self.__class__.__name__}: 🎉 [SUCCESS] 报告 {report_id} 生成成功")
                # 使用模型的序列化方法
            return {
                 "status": "success",
                "report_data": report_instance.to_celery_dict()
            }
        else:
            error_msg = f"报告生成失败: {report_instance.error_message}"
            logger.error(f"{self.__class__.__name__}: ❌ 生成失败[ERROR] {error_msg}")
            raise Exception(f"News briefing generation failed: {report_instance.error_message}")
        
    except Exception as e:
        logger.error("💥" * 20)
        logger.error(f"{self.__class__.__name__}: ❌ [ERROR] 任务失败 - 报告 ID {report_id}")
        logger.error(f"{self.__class__.__name__}: ❌ [ERROR] 错误信息: {str(e)}")
        logger.error(f"{self.__class__.__name__}: ❌ [ERROR] 错误类型: {type(e).__name__}")
        logger.error(f"{self.__class__.__name__}: Error in generate_user_news_briefing_task for report ID {report_id}: {str(e)}")
        if "'module' object is not callable" in str(e):
            logger.error(f"{self.__class__.__name__}: 🔍 [ANALYSIS] 'module' object is not callable 错误")
            logger.error(f"{self.__class__.__name__}: 💡 [HINT] 检查是否有语法错误或导入问题")

        # 完整堆栈追踪
        logger.error(f"{self.__class__.__name__}: 📋 [TRACEBACK] 完整错误堆栈:")
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                logger.error(f"    {line}")
        
        logger.error("💥" * 20)
        self.retry(exc=e)
    
@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def update_user_profile_embedding_task(self, profile_id: int):
    """
    异步更新用户画像的嵌入向量
    """
    try:
        from apps.users.models import UserProfile
        from ai.vector.user_vector_executor import UserVectorExecutor

        logger.info(f"{self.__class__.__name__}: 开始更新用户画像 {profile_id} 的嵌入向量")

        profile = UserProfile.objects.get(id=profile_id)
        user_vector_executor = UserVectorExecutor()
        
        # 构建用于嵌入的文本
        portrait = profile.user_self_portrait or "投资者"
        topics = ", ".join(profile.preferred_topic) if profile.preferred_topic else "财经"
        topic_text = profile.perferred_topic_text or "关注财经市场"
        
        text_for_embedding = f"{portrait}。{topic_text}。关注话题：{topics}"
        
        # 更新嵌入向量
        success = user_vector_executor.update_user_profile_embedding(
            profile, text_for_embedding
        )
        
        if success:
            logger.info(f"{self.__class__.__name__}: 用户画像 {profile_id} 的嵌入向量更新成功")
            return {"status": "success", "profile_id": profile_id}
        else:
            logger.error(f"{self.__class__.__name__}: 用户画像 {profile_id} 的嵌入向量更新失败")
            return {"status": "failed", "profile_id": profile_id}
            
    except UserProfile.DoesNotExist:
        logger.error(f"{self.__class__.__name__}: 用户画像 {profile_id} 不存在")
        return {"status": "not_found", "profile_id": profile_id}
    except Exception as e:
        logger.error(f"{self.__class__.__name__}: 更新用户画像 {profile_id} 嵌入向量时出错: {e}")
        return {"status": "error", "profile_id": profile_id, "error": str(e)}
