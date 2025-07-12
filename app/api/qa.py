import re
from typing import List, Dict, Any
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import EmbeddingsFilter
from langchain.schema.runnable import RunnablePassthrough
from langchain_community.llms import Ollama
from langchain.memory import ConversationBufferWindowMemory

# 配置参数
CONFIG = {
    "embedding_model": "./bge-large-zh-v1.5",
    "vector_store_path": "./vector_store/bert",
    "llm_model": "deepseek-r1:1.5b",
    "device": "cuda",
    "retrieval_params": {
        "k": 5,
        "nprobe": 20,
        "similarity_threshold": 0.5
    }
}

def load_embeddings() -> HuggingFaceBgeEmbeddings:
    """加载嵌入模型"""
    return HuggingFaceBgeEmbeddings(
        model_name=CONFIG["embedding_model"],
        model_kwargs={'device': CONFIG["device"]},
        encode_kwargs={
            'normalize_embeddings': True,
            'batch_size': 512,
            'use_fp16': True
        }
    )

def load_vectorstore(embeddings: HuggingFaceBgeEmbeddings) -> FAISS:
    """加载向量数据库"""
    return FAISS.load_local(
        CONFIG["vector_store_path"],
        embeddings=embeddings,
        allow_dangerous_deserialization=True
    )

def create_retriever(vectorstore: FAISS) -> ContextualCompressionRetriever:
    """创建增强检索器"""
    base_retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": CONFIG["retrieval_params"]["k"],
            "nprobe": CONFIG["retrieval_params"]["nprobe"]
        }
    )
    
    compressor = EmbeddingsFilter(
        embeddings=vectorstore.embeddings,
        similarity_threshold=CONFIG["retrieval_params"]["similarity_threshold"]
    )
    
    return ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever
    )

def build_prompt_template() -> ChatPromptTemplate:
    template = """你是一个的C++编程助手，请严格根据提供的上下文和对话历史回答问题。
    若上下文不相关，请根据情况回答。严禁编造知识。

    对话历史（按时间倒序）：
    {chat_history}

    问题：{question}

    相关上下文：
    {context}

    请用中文给出分步骤的详细解释，并在关键术语旁标注英文："""
    return ChatPromptTemplate.from_template(template)

def initialize_llm() -> Ollama:
    """初始化大语言模型"""
    return Ollama(
        model=CONFIG["llm_model"],
        temperature=0.9,
        # 可根据需要添加其他参数
        # stop=["<|im_end|>"],
        # top_p=0.9
    )

class QASystem:
    """问答系统封装类"""
    def __init__(self):
        self.embeddings = load_embeddings()
        self.vectorstore = load_vectorstore(self.embeddings)
        self.retriever = create_retriever(self.vectorstore)
        self.prompt = build_prompt_template()
        self.llm = initialize_llm()
        
        self.chain = (
            {"context": self._format_context, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
        )
        self.memory = ConversationBufferWindowMemory(
            k=5, 
            memory_key="chat_history",
            return_messages=True
        )
        
        # 更新Chain结构以支持上下文
        self.chain = (
            RunnablePassthrough.assign(
                chat_history=lambda _: self.memory.load_memory_variables({})["chat_history"]
            )
            | self.prompt
            | self.llm
        )
    
    def _format_context(self, query: str) -> str:
        """格式化检索到的上下文"""
        docs = self.retriever.get_relevant_documents(query)
        # print(f"检索到的文档：{docs[1].page_content}")
        return "\n\n".join([f"来源 {i+1}：{doc.page_content}" for i, doc in enumerate(docs)])
    
    def ask(self, question: str) -> str:
        # 调用Chain时传入记忆
        response = self.chain.invoke({
            "question": question,
            "context": self._format_context(question)
        })
        
        # 保存当前对话到记忆
        self.memory.save_context(
            {"input": question},
            {"output": response}
        )
        
        return self._parse_response(response)
    
    def _parse_response(self, response: Any) -> str:
        """解析模型响应"""
        # 使用更稳健的解析方式
        if hasattr(response, "content"):
            content = response.content
        else:
            content = str(response)
            
        # 提取回答内容（适配不同模型格式）
        match = re.search(r'(?<=</think>).*', response,flags=re.DOTALL)
        return match.group().strip() if match else content