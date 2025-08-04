# NewsBriefingReport 模型字段常量
# 这些常量用于确保 AI Agent 输出与数据库模型字段完全匹配
REPORT_FIELDS = {
    # 模型字段名称
    'SUMMARY': 'summary',
    'FULL_REPORT_CONTENT': 'full_report_content',
    'KEY_DIRECTIONS': 'key_directions',
    'RELATED_STOCKS': 'related_stocks',
    'AI_IMPACT_SCORE': 'ai_impact_score',
    'NEWS_ARTICLES': 'news_articles',
    'USER_FOCUSED_NEWS_ARTICLES': 'user_focused_news_articles',
    'USER_PROFILE_REFERENCES': 'user_profile_references',

    # 嵌套字段
    'MARKET_SENTIMENT': 'market_sentiment',
    'RECOMMENDATIONS': 'recommendations',
}

# 报告状态常量
REPORT_STATUS = {
    'PENDING': 'pending',
    'GENERATING': 'generating',
    'COMPLETED': 'completed',
    'FAILED': 'failed',
}

# AI Agent 输出状态常量
AGENT_STATUS = {
    'COMPLETE': 'COMPLETE',
    'ERROR': 'ERROR',
    'PARTIAL': 'PARTIAL',
}

# 响应结构常量
RESPONSE_FIELDS = {
    'STATUS': 'status',
    'REPORT_DATA': 'report_data',
    'ERROR': 'error',
}
