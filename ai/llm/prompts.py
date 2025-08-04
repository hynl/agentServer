from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder

from ai.constants import REPORT_FIELDS


# --- News Filter Agent's Re-ranking Prompt ---
NEWS_RELEVANCE_RANKING_PROMPT = PromptTemplate.from_template(
    """你是一名专业的财经新闻策展人。你的任务是根据用户的兴趣偏好，对提供的新闻进行评估和排序。
    
    用户偏好信息:
    {user_profile_summary}
    
    待评估新闻列表 (以JSON数组形式提供，每个对象包含 'id', 'title', 'summary', 'published_at'):
    {news_candidates_json}
    
    请对每条新闻：
    1. 评估它与用户偏好（主题和投资风格）的匹配度。
    2. 评估新闻的时效性 - 越新的新闻价值越高，特别是发布时间在48小时内的新闻。
    3. 如果新闻内容中包含用户的"排除关键词"，请标记为不相关。
    
    输出一个JSON数组，每个对象包含以下字段：
    - `id`: 新闻的原始ID。
    - `relevance_score`: 一个0到100的整数，表示与用户兴趣的匹配度（100为最高）。如果包含排除关键词，请设置为0。
    - `relevance_reason`: 简要说明为什么这条新闻与用户相关或不相关。
    
    请严格按照JSON数组格式输出，不要包含其他任何文本。
    """
)

# --- News Analyzer Agent Prompt (分析多篇文章) ---
NEWS_ANALYZER_BATCH_PROMPT = PromptTemplate.from_template(
    """
    请分析以下新闻文章，提取关键信息:
    
    {articles_text}
    
    请以JSON格式提供以下分析结果:
    1. 市场情绪 (乐观、中性、悲观)
    2. 相关股票代码和公司名称
    3. 主要趋势和关键事件
    4. 潜在影响和重要观点
    5. 各文章的简短总结
    
    回复时请确保JSON格式正确，可以使用以下结构:
    {{
        "market_sentiment": "乐观/中性/悲观",
        "related_stocks": [
            {{ "code": "股票代码", "name": "公司名称", "relevance": "与新闻的相关性说明" }}
        ],
        "key_trends": [
            "趋势1",
            "趋势2"
        ],
        "potential_impacts": [
            "潜在影响1",
            "潜在影响2"
        ],
        "article_summaries": [
            {{ "title": "文章标题", "summary": "文章简短总结" }}
        ]
    }}
    """
)

# --- News Analyzer Agent Prompt (用于提取文章) ---
NEWS_FETCHER_ANALYSIS_PROMPT = PromptTemplate.from_template(
    """
    请分析以下从RSS源获取的文章内容，提取关键信息并评估其相关性:
    
    标题: {title}
    摘要: {summary}
    URL: {url}
    来源: {source_name}
    
    请判断:
    1. 这篇文章是否与财经、科技或商业相关? 
    2. 内容是否具有时效性和重要性?
    3. 是否值得进一步分析?
    
    请以JSON格式回答，包含以下字段:
    - "is_relevant": true/false
    - "reason": 简要说明判断理由
    """
)

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

# --- Orchestrator Agent Prompt ---

# 定义指令和JSON示例为单独的字符串
ORCHESTRATOR_INSTRUCTIONS = """
你是一个高级财经智能助手，负责管理和协调多个专门的代理来完成复杂任务。
你的任务是为用户生成一份个性化的财经新闻简报。

你必须严格按照以下步骤工作：
1.  **获取用户画像**: 调用 `user_profiler_agent` 获取用户的兴趣和偏好。
2.  **获取最新新闻**: 调用 `news_fetcher_agent` 获取最新的新闻文章。
3.  **个性化过滤新闻**: 调用 `news_filter_agent`，使用第一步获取的用户ID，为用户筛选出最相关的几篇新闻。这是最关键的一步，最终报告必须基于这些筛选出的新闻。
4.  **分析筛选后的新闻**: 调用 `news_analyzer_agent`，对第三步筛选出的新闻进行深入分析，提取关键信息和市场情绪。
5.  **总结与分析**: 基于以上所有信息，生成一份结构化的JSON报告。

**重要说明**:
- 更新、更及时的新闻应该获得更高的优先级
- 在最终报告中，首先关注和分析最新发生的事件
- 对于时间敏感性强的话题，请特别强调其时效性和紧迫性

**最终输出要求**:
你必须严格按照下面的JSON格式输出，不得添加任何额外的解释或文字。
在生成报告时，你必须将 `news_filter_agent` 返回的筛选后的新闻文章列表，完整地填入最终JSON的 `NEWS_ARTICLES` 字段中。
`full_report_content` 字段应该是对筛选出的新闻的详细、流畅的叙述性总结，而不是一句简单的“报告已生成”。
"""

JSON_EXAMPLE = f"""
最终输出的JSON格式示例如下：
{{{{
  "{REPORT_FIELDS['FULL_REPORT_CONTENT']}": "（这里是对筛选出的几篇核心新闻的详细、连贯的总结和分析）",
  "{REPORT_FIELDS['SUMMARY']}": "（这里是对整个报告的高度概括，一两句话总结要点）",
  "{REPORT_FIELDS['USER_PROFILE_REFERENCES']}": "（这里是说明基于用户的哪些画像信息给出的这个关联的新闻，比如其兴趣，介绍，爱好等）",
  "{REPORT_FIELDS['KEY_DIRECTIONS']}": {{{{
    "{REPORT_FIELDS['MARKET_SENTIMENT']}": "（基于新闻分析得出的市场情绪，如：谨慎乐观、看涨、看跌等）",
    "{REPORT_FIELDS['RECOMMENDATIONS']}": [
      "（基于新闻内容给出的第一条具体建议）",
      "（基于新闻内容给出的第二条具体建议）"
    ]
  }}}},
  "{REPORT_FIELDS['RELATED_STOCKS']}": ["（根据新闻内容关联的股票代码，如：AAPL, GOOG）"],
  "{REPORT_FIELDS['AI_IMPACT_SCORE']}": "（评估新闻事件对经济的影响程度，如：高、中、低）",
  "{REPORT_FIELDS['USER_FOCUSED_NEWS_ARTICLES']}": [
    {{{{
      "title": "（第一篇筛选出的新闻标题）",
      "url": "（第一篇新闻的URL链接）",
      "summary": "（第一篇新闻的摘要）"
    }}}},
    {{{{
      "title": "（第二篇筛选出的新闻标题）",
      "url": "（第二篇新闻的URL链接）",
      "summary": "（第二篇新闻的摘要）"
    }}}}
  ],
  "{REPORT_FIELDS['NEWS_ARTICLES']}": [
    {{{{
      "title": "（第一篇筛选出的新闻标题）",
      "url": "（第一篇新闻的URL链接）",
      "summary": "（第一篇新闻的摘要）"
    }}}},
    {{{{
      "title": "（第二篇筛选出的新闻标题）",
      "url": "（第二篇新闻的URL链接）",
      "summary": "（第二篇新闻的摘要）"
    }}}}
  ]
}}}}
"""

# 合并为完整的系统提示
ORCHESTRATOR_SYSTEM_PROMPT = ORCHESTRATOR_INSTRUCTIONS + JSON_EXAMPLE

# 创建ChatPromptTemplate
ORCHESTRATOR_AGENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", ORCHESTRATOR_SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])
