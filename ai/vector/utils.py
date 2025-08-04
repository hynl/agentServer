import re
import logging
from typing import List

logger = logging.getLogger(__name__)

def split_text_into_chunks(text: str, chunk_size: int = 5000, overlap: int = 200, max_chunks: int = 10) -> List[str]:
    """
    将长文本分割成重叠的块，确保语义连贯性，并限制最大块数
    
    Args:
        text: 要分割的文本
        chunk_size: 每个块的最大字符数
        overlap: 块之间的重叠字符数
        max_chunks: 最大允许的块数
        
    Returns:
        文本块列表
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    # 清理文本
    text = clean_html_content(text)
    
    # 如果文本极长且超过了最大块数限制的处理容量，采用智能截断策略
    if len(text) > chunk_size * max_chunks:
        logger.warning(f"文本长度 ({len(text)} 字符) 超出处理能力，执行智能截断")
        
        # 保留前半部分和后四分之一的内容
        first_portion = int(chunk_size * max_chunks * 0.75)  # 保留前75%的处理容量用于文本前部
        last_portion = int(chunk_size * max_chunks * 0.25)   # 保留25%的处理容量用于文本结尾
        
        # 取文本的前部分
        front_text = text[:first_portion]
        
        # 取文本的后部分（如果文本足够长）
        back_text = ""
        if len(text) > first_portion + 500:  # 确保有足够的后部文本
            back_text = text[-last_portion:]
            
        # 添加说明
        if back_text:
            text = front_text + "\n\n[...内容已省略...]\n\n" + back_text
        else:
            text = front_text
            
        logger.info(f"文本已智能截断至 {len(text)} 字符")
    
    chunks = []
    start = 0
    
    while start < len(text):
        # 确定当前块的结束位置
        end = min(start + chunk_size, len(text))
        
        # 如果不是最后一块且没有达到最大块数，尝试在自然边界处分割
        if end < len(text) and len(chunks) < max_chunks - 1:
            # 尝试在段落结束处分割
            paragraph_end = text.rfind('\n\n', start, end)
            if paragraph_end > start + chunk_size // 2:
                end = paragraph_end + 2  # 包含段落结束符
            else:
                # 尝试在句子结束处分割
                sentence_end = text.rfind('. ', start, end)
                if sentence_end > start + chunk_size // 2:
                    end = sentence_end + 2  # 包含句号和空格
                else:
                    # 最后尝试在单词边界分割
                    space_pos = text.rfind(' ', start + chunk_size // 2, end)
                    if space_pos > start:
                        end = space_pos + 1
        
        # 提取当前块
        current_chunk = text[start:end].strip()
        if current_chunk:  # 只添加非空块
            chunks.append(current_chunk)
        
        # 如果已达到最大块数，跳出循环
        if len(chunks) >= max_chunks:
            remaining_text = len(text) - end
            if remaining_text > 200:  # 如果还有明显剩余文本
                logger.warning(f"已达到最大块数 {max_chunks}，剩余 {remaining_text} 字符未处理")
            break
        
        # 更新下一个块的起始位置，考虑重叠
        start = max(start + 1, end - overlap)
    
    avg_size = sum(len(c) for c in chunks) / len(chunks) if chunks else 0
    logger.debug(f"将文本分割为 {len(chunks)} 个块 (平均大小: {avg_size:.0f} 字符)")
    return chunks
def clean_html_content(text: str) -> str:
    """
    清理HTML标签和多余空白
    """
    if not text:
        return ""
    
    # 移除HTML标签
    clean_text = re.sub(r'<[^>]+>', ' ', text)
    # 替换多个空白为单个空格
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text