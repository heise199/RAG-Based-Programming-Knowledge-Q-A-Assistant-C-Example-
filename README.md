# RAG-Based-Programming-Knowledge-Q-A-Assistant-C-Example-
本文设计开发了一种基于RAG（检索增强生成）架构的程序设计课程智能问答系统。该系统通过LangChain框架实现文档处理与检索增强流程，利用Ollama平台本地化部署7B参数的Deepseek-R1大模型，并搭配Flask + HTML5构建轻量化Web服务，实现了从知识预处理到智能交互的技术闭环。系统支持多模态数据知识库动态扩增，采用bge-large-zh-v1.5模型生成词向量，利用FAISS管理向量库，成功构建出一个高效、精准且实用的程序设计学习问答平台。实验结果表明，该系统在知识检索效率、回答准确性和用户交互体验方面均表现出色，具备实用性和可部署性质。
