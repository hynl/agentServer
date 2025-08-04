"""
独立测试各个Agent的脚本
"""
import os
import sys
import django
import logging

# 添加项目路径
sys.path.append('/Users/songyang/agentServer')

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agentrtw.settings')
django.setup()

logging.basicConfig(
    level=logging.DEBUG,  # 设置为 DEBUG 级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # 输出到控制台
        logging.FileHandler('test_agents.log', mode='w')  # 同时写入文件
    ]
)
logger = logging.getLogger(__name__)
from ai.agents.user_profiler import UserProfilerAgent
from ai.agents.news_fetcher import NewsFetcherAgent
from ai.agents.news_filter import NewsFilterAgent

def test_user_profiler():
    print("🧪 测试 UserProfilerAgent...")
    agent = UserProfilerAgent()
    try:
        result = agent.run(user_id="2")
        print(f"✅ UserProfilerAgent 成功: {result}")
        return True
    except Exception as e:
        print(f"❌ UserProfilerAgent 失败: {e}")
        return False

def test_news_fetcher():
    print("🧪 测试 NewsFetcherAgent...")
    agent = NewsFetcherAgent()
    try:
        result = agent.run(limit_new_articles=3)
        print(f"✅ NewsFetcherAgent 成功: 获取 {result.get('fetched_count', 0)} 条新闻")
        return True
    except Exception as e:
        print(f"❌ NewsFetcherAgent 失败: {e}")
        return False

def test_news_filter():
    print("🧪 测试 NewsFilterAgent...")
    agent = NewsFilterAgent()
    try:
        test_news = [
            {"id": 1, "title": "AI技术突破", "summary": "人工智能领域重大进展"},
            {"id": 2, "title": "新能源汽车", "summary": "电动汽车销量创新高"}
        ]
        result = agent.run(user_id="2", news_candidates=test_news)
        print(f"✅ NewsFilterAgent 成功: {result}")
        return True
    except Exception as e:
        print(f"❌ NewsFilterAgent 失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试各个Agent...")
    os.environ["DJANGO_LOG_LEVEL"] = "DEBUG"

    tests = [
        ("UserProfilerAgent", test_user_profiler),
        ("NewsFetcherAgent", test_news_fetcher),
        ("NewsFilterAgent", test_news_filter),
    ]
    
    results = {}
    for name, test_func in tests:
        print(f"\n{'='*50}")
        success = test_func()
        results[name] = success
        print(f"{'='*50}")
    
    print(f"\n📊 测试结果总结:")
    for name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {name}: {status}")
    
    all_pass = all(results.values())
    print(f"\n🎯 总体结果: {'全部通过' if all_pass else '存在失败'}")