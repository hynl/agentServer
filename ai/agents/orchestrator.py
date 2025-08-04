import json
import re
from typing import Any, Dict
import logging
from ai.agents.base import BaseAgent
from ai.agents.news_analyzer import NewsAnalyzerAgent
from ai.agents.news_fetcher import NewsFetcherAgent
from ai.agents.news_filter import NewsFilterAgent
from ai.agents.user_profiler import UserProfilerAgent
from langchain.agents import AgentExecutor, create_openai_tools_agent
from ai.agents.common_tools import get_user_profile, read_rss_feed, scrape_articles_content
from ai.constants import AGENT_STATUS, RESPONSE_FIELDS
from ai.llm.prompts import ORCHESTRATOR_AGENT_PROMPT

logger = logging.getLogger(__name__)

class NewsBriefingOrchestratorAgent(BaseAgent):
    name = "News Briefing Orchestrator"
    description = "An intelligent agent that coordinates other specialized agents to generate personalized financial news briefings based on user requests."
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.news_fetcher_agent = NewsFetcherAgent()
        self.news_analyzer_agent = NewsAnalyzerAgent()
        self.user_profiler_agent = UserProfilerAgent()
        self.news_filter_agent = NewsFilterAgent()
        # self.stock_linker_agent = StockLinkerAgent(llm=self.llm)
        # self.report_generator_agent = ReportGeneratorAgent(llm=self.llm)
        
        self.tools = [
            self.news_fetcher_agent.as_tool(),
            self.news_analyzer_agent.as_tool(),
            self.user_profiler_agent.as_tool(),
            self.news_filter_agent.as_tool(),
            # self.stock_linker_agent,
            # self.report_generator_agent,
            # getNewsArticleByIdTool,
        ]
        
        self.prompt = ORCHESTRATOR_AGENT_PROMPT
        
        self.agent_executor = AgentExecutor(
            agent=create_openai_tools_agent(self.llm, self.tools, self.prompt),
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=15,
            max_execution_time=600,
            return_intermediate_steps=True,  # 返回中间步骤
        )
        
        for tool in self.tools:
            logger.info(f"{self.__class__.__name__}: 实际 Tool name: {tool.name}")  # 这会显示工具的实际名称

    def run(self, user_id: str, user_request: str = "") -> Dict[str, Any]:
        logger.info(f"{self.__class__.__name__}: 正在执行Agent任务 for user {user_id} with request: {user_request}")

        full_agent_input = {
            "user_id": str(user_id),
            "input": user_request,
            "chat_history": [],
        }
        
        try:
            result = self.agent_executor.invoke(full_agent_input)
            logger.info(f"{self.__class__.__name__}: Agent执行结果: {result}")

            # 检查是否执行了所有必要的工具
            steps = result.get('intermediate_steps', [])
            executed_tools = set()
            
            for step in steps:
                if step and isinstance(step, tuple) and len(step) >= 2:
                    tool_name = step[0].tool if hasattr(step[0], 'tool') else str(step[0])
                    executed_tools.add(tool_name)

            logger.info(f"{self.__class__.__name__}: 执行用到的工具: {executed_tools}")

            # 检查必要的工具是否被执行
            required_tools = {'user_profiler_agent', 'news_fetcher_agent', 'news_analyzer_agent', 'news_filter_agent'}
            missing_tools = required_tools - executed_tools
        
            if missing_tools:
                logger.warning(f"{self.__class__.__name__}: 注意，这些agent没有被调用: {missing_tools}")

            final_output = result.get('output', "No output generated.")
            logger.info(f"{self.__class__.__name__}: 最终输出 for user {user_id}: {final_output}")

            json_content = self._extract_json_from_output(final_output)
            
            try:
                parsed_report_data = json.loads(json_content)
                if isinstance(parsed_report_data, dict) and parsed_report_data.get('full_report_content'):
                    logger.info(f"{self.__class__.__name__}: 解析后的报告内容 for user {user_id}: {parsed_report_data['full_report_content']}")
                    return {
                        RESPONSE_FIELDS['STATUS']: AGENT_STATUS['COMPLETE'], 
                        RESPONSE_FIELDS['REPORT_DATA']: parsed_report_data
                    }
                else:
                    logger.warning(f"{self.__class__.__name__}: 最终输出 for user {user_id} 不是有效的报告格式: {final_output}")
                    return {
                        RESPONSE_FIELDS['STATUS']: AGENT_STATUS['ERROR'],
                        RESPONSE_FIELDS['ERROR']: "Failed to parse report data from LLM output"
                    }
            except json.JSONDecodeError:
                logger.error(f"{self.__class__.__name__}: 解析最终输出为JSON时出错 for user {user_id}: {final_output}")
                return {
                    RESPONSE_FIELDS['STATUS']: AGENT_STATUS['ERROR'],
                    RESPONSE_FIELDS['ERROR']: str(e)
                }
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: 用户 {user_id} 的 orchestrator agent 发生错误: {e}")
            return {
                RESPONSE_FIELDS['STATUS']: AGENT_STATUS['ERROR'],
                RESPONSE_FIELDS['ERROR']: str(e)
            }

    def _extract_json_from_output(self, output: str) -> str:
            """从输出中提取JSON内容，移除markdown代码块标记"""
            # 移除markdown代码块标记
            if '```json' in output:
                # 使用正则表达式提取JSON内容
                json_match = re.search(r'```json\s*\n(.*?)\n```', output, re.DOTALL)
                if json_match:
                    return json_match.group(1).strip()
            
            # 如果没有markdown标记，尝试找到JSON对象
            json_start = output.find('{')
            json_end = output.rfind('}')
            if json_start != -1 and json_end != -1 and json_end > json_start:
                return output[json_start:json_end+1]
            
            return output.strip()
        