from typing import Optional, List, Dict, Any
from ai.vector.base_vector_client import BaseVectorClient
from django.db.models import F, Model
from pgvector.django import L2Distance, CosineDistance
from pgvector.django import MaxInnerProduct
from ai.llm.client import LLMClient
import logging
from ai.vector.utils import split_text_into_chunks, clean_html_content

logger = logging.getLogger(__name__)

class PGVectorClient(BaseVectorClient):
    def __init__(self, 
                 model_class: Model,
                 embedding_field_name: str = 'embedding',
                 processed_flag_field_name: str = 'is_processed_for_embedding',
                 text_content_field_name: str = 'content',
                 embedding_provider: Optional[str] = None):
        self.model_class = model_class
        self.embedding_field_name = embedding_field_name
        self.processed_flag_field_name = processed_flag_field_name
        self.text_content_field_name = text_content_field_name
        self.embedding_provider = embedding_provider
        
        if not hasattr(self.model_class, self.embedding_field_name):
            raise ValueError(f"The model {self.model_class.__name__} does not have an embedding field named '{self.embedding_field_name}'")
        if not hasattr(self.model_class, self.processed_flag_field_name):
            raise ValueError(f"The model {self.model_class.__name__} does not have a processed flag field named '{self.processed_flag_field_name}'")
        
    def _get_model_instance(self, document_id: str) -> Optional[Model]:
        try:
            return self.model_class.objects.get(id=document_id)
        except self.model_class.DoesNotExist:
            logger.warning(f"Document with ID {document_id} does not exist in the model {self.model_class.__name__}.")
            return None 
        
    def _get_embedding(self, query_text: str) -> List[float]:
        logger.info(f"{self.__class__.__name__}: 开始生成嵌入向量，文本长度: {len(query_text)}")

        # 确保文本不为空
        if not query_text or not query_text.strip():
            logger.warning(f"{self.__class__.__name__}: 尝试为空文本生成嵌入，使用默认向量")
            # 返回默认向量而不是空列表
            try:
                # 尝试获取正确维度
                test_embedding = self._get_embedding_model().embed_query("测试文本")
                return [0.0] * len(test_embedding)
            except:
                # 默认使用768维向量
                return [0.0] * 768
        
        # 如果文本过短，增加一些上下文
        if len(query_text.strip()) < 50:
            query_text = f"{query_text}\n\n这是一篇关于{query_text[:20]}的文章。"
            logger.info(f"{self.__class__.__name__}: 文本过短，增加上下文至 {len(query_text)} 字符")

        try:
            # 对于短文本，直接尝试生成嵌入
            if len(query_text) <= 8000:
                logger.info(f"{self.__class__.__name__}: 使用直接嵌入方法 (文本 <= 8000)")
                embedding_model = self._get_embedding_model()
                try:
                    logger.info(f"{self.__class__.__name__}: 正在调用嵌入模型API...")
                    embedding = embedding_model.embed_query(query_text)
                    logger.info(f"{self.__class__.__name__}: 嵌入向量生成成功，维度: {len(embedding)}")
                    return embedding
                except Exception as e:
                    logger.warning(f"{self.__class__.__name__}: 直接嵌入失败: {e}, 尝试分块方法")
            else:
                logger.info(f"{self.__class__.__name__}: 文本过长，使用分块嵌入方法")
                
            # 长文本使用分块处理
            return self._get_chunked_embedding(query_text)
                
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: 嵌入生成完全失败: {e}", exc_info=True)

            try:
                # 尝试获取正确维度
                test_embedding = self._get_embedding_model().embed_query("测试文本")
                logger.warning(f"{self.__class__.__name__}: 返回零向量，维度: {len(test_embedding)}")
                return [0.0] * len(test_embedding)
            except:
                # 默认使用768维向量
                logger.warning(f"{self.__class__.__name__}: 无法确定向量维度，使用默认768维")
                return [0.0] * 768
        
    def _get_embedding_model(self):
        """获取embedding模型，添加错误处理和重试逻辑"""
        try:
            if self.embedding_provider:
                return LLMClient.get_embedding_model(provider=self.embedding_provider)
            else:
                return LLMClient.get_embedding_model()  # 使用默认provider
        except Exception as e:
            # 如果指定的提供商失败，尝试回退到OpenAI
            logger.warning(f"{self.__class__.__name__}: 获取嵌入模型失败，尝试回退到OpenAI: {e}")
            try:
                return LLMClient.get_embedding_model(provider="OPENAI")
            except Exception as fallback_e:
                logger.error(f"{self.__class__.__name__}: 回退到OpenAI也失败: {fallback_e}")
                raise
            
    def _get_chunked_embedding(self, text: str, chunk_size: int = 5000, overlap: int = 200) -> List[float]:
        """
        通过分块和加权平均生成长文本的嵌入
        
        Args:
            text: 需要嵌入的长文本
            chunk_size: 每个块的最大字符数
            overlap: 块之间的重叠字符数
                
        Returns:
            合并后的嵌入向量
        """
        # 设置最大块数
        max_chunks = 10
        
        # 分割文本，传入最大块数参数
        chunks = split_text_into_chunks(text, chunk_size, overlap, max_chunks)
        
        if not chunks:
            logger.warning(f"{self.__class__.__name__}: 未从文本创建任何块")
            return []
        
        # 对块进行优先级排序，确保最重要的块被处理
        prioritized_chunks = self._prioritize_chunks(chunks)

        logger.info(f"{self.__class__.__name__}: 处理 {len(prioritized_chunks)} 个块进行嵌入")

        # 为每个块获取嵌入
        chunk_embeddings = []
        weights = []
        
        embedding_model = None
        # 尝试获取embedding模型
        try:
            embedding_model = self._get_embedding_model()
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: 获取嵌入模型失败: {e}")
            return []
    
        # 为每个块生成嵌入
        for i, chunk in enumerate(prioritized_chunks):
            try:
                embedding = embedding_model.embed_query(chunk)
                
                if embedding:
                    chunk_embeddings.append(embedding)
                    # 调整权重策略
                    chunk_weight = len(chunk)
                    
                    # 给予第一块和最后一块更高权重（通常包含更重要的信息）
                    if i == 0 or i == len(prioritized_chunks) - 1:
                        chunk_weight *= 1.5
                        
                    weights.append(chunk_weight)
                    logger.debug(f"{self.__class__.__name__}: 生成第 {i+1}/{len(prioritized_chunks)} 块的嵌入")
            except Exception as e:
                logger.warning(f"{self.__class__.__name__}: 为第 {i+1} 块生成嵌入失败: {e}")

        if not chunk_embeddings:
            logger.error(f"{self.__class__.__name__}: 未能为任何块生成嵌入")
            return []
        
        # 合并所有块的嵌入
        if len(chunk_embeddings) == 1:
            # 只有一个块时直接返回
            return chunk_embeddings[0]
        
        # 计算加权平均
        embedding_dim = len(chunk_embeddings[0])
        total_weight = sum(weights)
        
        if total_weight == 0:
            # 避免除以零，所有权重相等
            weights = [1.0] * len(chunk_embeddings)
            total_weight = float(len(weights))
        
        # 计算加权平均
        final_embedding = [0.0] * embedding_dim
        for i, emb in enumerate(chunk_embeddings):
            weight = weights[i] / total_weight
            for j in range(embedding_dim):
                final_embedding[j] += emb[j] * weight
    
        # 标准化为单位向量
        magnitude = sum(x**2 for x in final_embedding) ** 0.5
        if magnitude > 0:
            final_embedding = [x / magnitude for x in final_embedding]

        logger.info(f"{self.__class__.__name__}: 成功从 {len(chunk_embeddings)} 个块创建合并嵌入")
        return final_embedding

    # 添加块优先级排序方法
    def _prioritize_chunks(self, chunks: List[str]) -> List[str]:
        """
        按照信息重要性对文本块进行优先级排序
        
        策略:
        1. 保留第一块（通常包含标题和介绍）
        2. 保留最后一块（可能包含结论）
        3. 对中间块，根据信息密度选择更有价值的块
        
        Args:
            chunks: 原始文本块列表
            
        Returns:
            优先级排序后的文本块列表
        """
        if len(chunks) <= 10:
            return chunks
            
        # 对于超过最大块数的情况，进行智能选择
        selected_chunks = []
        
        # 始终保留第一块
        selected_chunks.append(chunks[0])
        
        # 如果块数多于2，保留最后一块
        if len(chunks) > 2:
            last_chunk = chunks[-1]
        else:
            last_chunk = None
        
        # 计算中间块的信息密度
        middle_chunks = chunks[1:-1] if len(chunks) > 2 else chunks[1:]
        
        # 简单的信息密度估算（这里可以用更复杂的算法）
        chunk_scores = []
        for chunk in middle_chunks:
            # 评分标准：句子数、特殊标记词（如"重要"、"结论"等）
            sentences = chunk.split('. ')
            special_terms = sum(1 for term in ['重要', '关键', '结论', '总结', '分析', '数据'] 
                            if term in chunk.lower())
            
            # 信息密度评分
            score = len(sentences) + special_terms * 2
            chunk_scores.append((score, chunk))
        
        # 根据评分选择中间块
        middle_chunks_to_keep = min(8, len(chunk_scores))  # 最多保留8个中间块
        selected_middle_chunks = [chunk for _, chunk in 
                                sorted(chunk_scores, key=lambda x: x[0], reverse=True)
                                [:middle_chunks_to_keep]]
        
        selected_chunks.extend(selected_middle_chunks)
        
        # 添加最后一块
        if last_chunk:
            selected_chunks.append(last_chunk)

        logger.info(f"{self.__class__.__name__}: 从原始的 {len(chunks)} 个块中优先选择了 {len(selected_chunks)} 个块")
        return selected_chunks
    
    def add_document(self, document_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        将文档添加到向量存储
        
        Args:
            document_id: 文档ID
            text: 文档文本内容
            metadata: 可选的元数据
            
        Returns:
            是否成功添加
        """
        try:
            logger.info(f"{self.__class__.__name__}: 添加文档到向量存储: ID {document_id}, 文本长度 {len(text)}")
            
            # 获取模型实例
            instance = self._get_model_instance(document_id)
            if not instance:
                logger.error(f"{self.__class__.__name__}: 找不到ID为 {document_id} 的文档")
                return False
                
            # 生成嵌入向量
            try:
                logger.info(f"{self.__class__.__name__}: 为文档 {document_id} 生成嵌入向量")
                embedding = self._get_embedding(text)
                
                if not embedding or len(embedding) == 0:
                    logger.error(f"{self.__class__.__name__}: 嵌入向量生成失败: 结果为空 (ID: {document_id})")
                    return False
                    
                # 设置嵌入向量
                setattr(instance, self.embedding_field_name, embedding)
                
                # 标记为已处理
                if hasattr(instance, self.processed_flag_field_name):
                    setattr(instance, self.processed_flag_field_name, True)
                
                # 准备更新字段列表
                update_fields = [self.embedding_field_name]
                if hasattr(instance, self.processed_flag_field_name):
                    update_fields.append(self.processed_flag_field_name)
                
                # 保存到数据库
                instance.save(update_fields=update_fields)
                logger.info(f"{self.__class__.__name__}: 成功添加嵌入向量到文档 {document_id}, 维度: {len(embedding)}")
                return True
                
            except Exception as e:
                logger.error(f"{self.__class__.__name__}: 生成嵌入向量失败 (ID: {document_id}): {e}", exc_info=True)
                return False
                
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: 添加文档失败 (ID: {document_id}): {e}", exc_info=True)
            return False

    def update_document(self, document_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        # Implement logic to update an existing document in the PGVector store
        return self.add_document(document_id, text, metadata)  # Reuse add_document logic for simplicity
        pass

    def query_similar_documents(self, 
                                query_text: Optional[str], 
                                query_embedding: Optional[List[float]] = None,
                                top_k: int = 5, 
                                distance_metric: float = 0.5,
                                filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        查询相似文档
        
        Args:
            query_text: 查询文本
            query_embedding: 查询嵌入（如已计算）
            top_k: 返回结果数量
            distance_metric: 距离度量 (cosine, l2, ip)
            filters: 查询过滤条件
            
        Returns:
            相似文档列表
        """
        try:
            if query_embedding is None:
                if query_text is None:
                    logger.warning(f"{self.__class__.__name__}: 查询文本和嵌入都为空，无法执行查询")
                    return []
                query_embedding = self._get_embedding(query_text)
                
            if not query_embedding:
                logger.warning(f"{self.__class__.__name__}: 查询嵌入为空，返回空结果")
                return []
            
            queryset = self.model_class.objects.filter(
                **{self.embedding_field_name + '__isnull': False}
            )
            if hasattr(self.model_class, self.processed_flag_field_name):
                queryset = queryset.filter(
                    **{self.processed_flag_field_name: True}
                )
                
            if filters:
                queryset = queryset.filter(**filters)

            score_field_name = "score"

            if distance_metric == "l2":
                relevant_docs = queryset.annotate(
                    **{score_field_name: L2Distance(self.embedding_field_name, query_embedding)}
                ).order_by(score_field_name)[:top_k]
            
            elif distance_metric == "cosine":
                relevant_docs = queryset.annotate(
                    **{score_field_name: CosineDistance(self.embedding_field_name, query_embedding)}
                ).order_by(score_field_name)[:top_k]
            elif distance_metric == "ip":
                relevant_docs = queryset.annotate(
                    **{score_field_name: MaxInnerProduct(self.embedding_field_name, query_embedding)}
                ).order_by(f'-{score_field_name}')[:top_k]
            else:
                logger.error(f"{self.__class__.__name__}: 不支持的距离度量: {distance_metric}. 支持的度量有 'l2', 'cosine', 和 'ip'.")
                return []
            
            results = []
            for doc in relevant_docs:
                doc_data = {
                    'id': doc.id,
                    'score': getattr(doc, score_field_name),
                    'embedding': getattr(doc, self.embedding_field_name),
                }
                if hasattr(doc, self.text_content_field_name):
                    doc_data['text'] = getattr(doc, self.text_content_field_name)

                if hasattr(doc, 'metadata'):
                    doc_data['metadata'] = getattr(doc, 'metadata')
                results.append(doc_data)

            logger.info(f"{self.__class__.__name__}: 找到 {len(results)} 个与查询 '{query_text}' 相似的文档，使用模型 {self.model_class.__name__}.")
            return results

        except Exception as e:
            logger.error(f"{self.__class__.__name__}: 从模型 {self.model_class.__name__} 查询相似文档失败: {e}")
            return []

    def get_document_embedding(self, document_id: str) -> Optional[List[float]]:
        """获取文档的嵌入向量"""
        instance = self._get_model_instance(document_id)
        if instance and hasattr(instance, self.embedding_field_name):
            embedding = getattr(instance, self.embedding_field_name)
            if embedding is not None:
                return embedding
        logger.warning(f"{self.__class__.__name__}: 文档 {document_id} 不存在或没有嵌入向量")
        return None  # Return None if the document does not exist or has no embedding
        pass

    def delete_document(self, document_id: str) -> bool:
        # Implement logic to delete a document from the PGVector store
        instance = self._get_model_instance(document_id)
        if instance:
            instance.delete()
            logger.info(f"{self.__class__.__name__}: 文档 {document_id} 已从模型 {self.model_class.__name__} 中删除.")
            return True
        logger.warning(f"{self.__class__.__name__}: 文档 {document_id} 不存在于模型 {self.model_class.__name__} 中.")
        return False
        pass
    
    