"""
批量处理新闻和用户兴趣嵌入向量的脚本
"""
import os
import sys
import django
import logging
import argparse
import time
from tqdm import tqdm  # 如果没有安装，使用 pip install tqdm

# 添加项目路径
sys.path.append('/Users/songyang/agentServer')

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agentrtw.settings')
django.setup()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# 导入所需模块
from apps.news.models import NewsArticle
from apps.users.models import UserProfile
from ai.vector.news_vector_excutor import NewsVectorExecutor
from ai.llm.client import LLMClient
from django.db.models import Q

def process_news_embeddings(limit=None, retry_failed=False, batch_size=10, sleep_seconds=0):
    """
    处理新闻文章的嵌入向量
    
    Args:
        limit: 最多处理的文章数量
        retry_failed: 是否重试之前失败的文章
        batch_size: 批量处理的大小
        sleep_seconds: 批次之间的休眠时间（秒）
    """
    # 创建向量执行器
    news_vector_executor = NewsVectorExecutor()
    
    # 构建查询条件
    query = Q(is_processed_for_embedding=False)
    if retry_failed:
        # 包括那些已标记为处理但嵌入为空的文章
        query |= Q(is_processed_for_embedding=True, embedding__isnull=True)
    
    # 获取需要处理的文章
    articles = NewsArticle.objects.filter(query)
    
    # 应用限制
    if limit:
        articles = articles[:limit]
    
    total_count = articles.count()
    logger.info(f"找到 {total_count} 篇需要处理嵌入向量的文章")
    
    if total_count == 0:
        logger.info("没有文章需要处理")
        return
    
    # 初始化计数器
    success_count = 0
    failed_count = 0
    
    # 创建进度条
    progress_bar = tqdm(total=total_count, desc="处理嵌入向量")
    
    # 分批处理
    for i in range(0, total_count, batch_size):
        batch = articles[i:i+batch_size]
        
        for article in batch:
            try:
                logger.info(f"正在处理文章: {article.title} (ID: {article.id})")
                
                # 生成嵌入
                if news_vector_executor.add_news_document(article):
                    # 标记为已处理
                    article.is_processed_for_embedding = True
                    article.save(update_fields=['is_processed_for_embedding'])
                    success_count += 1
                    logger.info(f"✅ 成功处理文章: {article.title}")
                else:
                    failed_count += 1
                    logger.warning(f"❌ 无法生成文章嵌入: {article.title}")
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ 处理文章时出错 {article.title}: {e}")
            
            # 更新进度条
            progress_bar.update(1)
        
        # 批次间休眠
        if sleep_seconds > 0 and i + batch_size < total_count:
            logger.info(f"批次休眠 {sleep_seconds} 秒...")
            time.sleep(sleep_seconds)
    
    # 关闭进度条
    progress_bar.close()
    
    # 打印摘要
    logger.info(f"处理完成! 总计: {total_count}, 成功: {success_count}, 失败: {failed_count}")


def process_user_interest_embeddings(limit=None, retry_failed=False, batch_size=10, sleep_seconds=0):
    """
    为用户资料生成兴趣嵌入向量
    
    Args:
        limit: 最多处理的用户资料数量
        retry_failed: 是否重试之前失败的用户资料
        batch_size: 批量处理的大小
        sleep_seconds: 批次之间的休眠时间（秒）
    """
    # 初始化嵌入模型
    try:
        embedding_model = LLMClient.get_embedding_model()
    except Exception as e:
        logger.error(f"无法初始化嵌入模型: {e}")
        return
    
    # 构建查询条件 - 修正字段名为 interest_embedding
    query = Q(interest_embedding__isnull=True)
    if not retry_failed:
        # 排除没有兴趣主题的用户
        query &= ~Q(preferred_topic=[])
    
    # 获取需要处理的用户资料
    profiles = UserProfile.objects.filter(query)
    
    # 应用限制
    if limit:
        profiles = profiles[:limit]
    
    total_count = profiles.count()
    logger.info(f"找到 {total_count} 个需要生成兴趣嵌入的用户资料")
    
    if total_count == 0:
        logger.info("没有用户资料需要处理")
        return
    
    # 初始化计数器
    success_count = 0
    failed_count = 0
    
    # 创建进度条
    progress_bar = tqdm(total=total_count, desc="处理用户兴趣嵌入")
    
    # 分批处理
    for i in range(0, total_count, batch_size):
        batch = profiles[i:i+batch_size]
        
        for profile in batch:
            try:
                # 获取用户兴趣文本
                preferred_topics = profile.preferred_topic or []
                excluded_topics = profile.excluded_topic or []
                
                if not preferred_topics:
                    logger.warning(f"用户 {profile.user.username} (ID: {profile.user.id}) 没有设置偏好主题，使用默认主题")
                    preferred_topics = ["财经新闻", "股票市场", "经济趋势"]
                
                # 构建用户兴趣文本
                interest_text = f"用户对这些主题感兴趣: {', '.join(preferred_topics)}. "
                if excluded_topics:
                    interest_text += f"用户不想看这些主题: {', '.join(excluded_topics)}."
                
                logger.info(f"正在为用户 {profile.user.username} (ID: {profile.user.id}) 生成兴趣嵌入")
                logger.info(f"兴趣文本: {interest_text}")
                
                # 生成嵌入向量
                embedding = embedding_model.embed_query(interest_text)
                
                if embedding and len(embedding) > 0:
                    # 保存嵌入向量 - 修正字段名为 interest_embedding
                    profile.interest_embedding = embedding
                    profile.save(update_fields=['interest_embedding'])
                    success_count += 1
                    logger.info(f"✅ 成功为用户 {profile.user.username} 生成兴趣嵌入 (维度: {len(embedding)})")
                else:
                    failed_count += 1
                    logger.warning(f"❌ 无法为用户 {profile.user.username} 生成兴趣嵌入: 嵌入向量为空")
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ 处理用户 {profile.user.username if hasattr(profile, 'user') else 'Unknown'} 兴趣嵌入时出错: {e}")
            
            # 更新进度条
            progress_bar.update(1)
        
        # 批次间休眠
        if sleep_seconds > 0 and i + batch_size < total_count:
            logger.info(f"批次休眠 {sleep_seconds} 秒...")
            time.sleep(sleep_seconds)
    
    # 关闭进度条
    progress_bar.close()
    
    # 打印摘要
    logger.info(f"用户兴趣嵌入处理完成! 总计: {total_count}, 成功: {success_count}, 失败: {failed_count}")

if __name__ == "__main__":
    os.environ["DJANGO_LOG_LEVEL"] = "DEBUG"
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='批量处理新闻文章和用户兴趣的嵌入向量')
    parser.add_argument('--limit', type=int, help='最多处理的数量')
    parser.add_argument('--retry-failed', action='store_true', help='重试之前失败的记录')
    parser.add_argument('--batch-size', type=int, default=10, help='批量处理的大小')
    parser.add_argument('--sleep', type=int, default=0, help='批次之间的休眠时间（秒）')
    parser.add_argument('--mode', choices=['news', 'user', 'all'], default='all', 
                        help='处理模式: news=只处理新闻, user=只处理用户兴趣, all=两者都处理 (默认: all)')
    
    args = parser.parse_args()
    
    print("🚀 开始批量处理嵌入向量...")
    start_time = time.time()
    
    # 根据模式执行不同的处理
    if args.mode in ['news', 'all']:
        print("\n=== 处理新闻文章嵌入向量 ===")
        process_news_embeddings(
            limit=args.limit, 
            retry_failed=args.retry_failed,
            batch_size=args.batch_size,
            sleep_seconds=args.sleep
        )
    
    if args.mode in ['user', 'all']:
        print("\n=== 处理用户兴趣嵌入向量 ===")
        process_user_interest_embeddings(
            limit=args.limit,
            retry_failed=args.retry_failed,
            batch_size=args.batch_size,
            sleep_seconds=args.sleep
        )
    
    elapsed_time = time.time() - start_time
    print(f"✨ 处理完成! 总耗时: {elapsed_time:.2f} 秒")