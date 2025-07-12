from flask import Blueprint, render_template, redirect, url_for, request, flash,current_app
from werkzeug.utils import secure_filename
from app import db
from app.api.qa import QASystem
from app.api.qa import load_embeddings,load_vectorstore
import os
from flask_login import current_user, login_required
from app.model import Dialogue
from app.model import Session
from datetime import datetime
from flask import jsonify
from langchain.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from werkzeug.utils import secure_filename
import time
import torch  
from app.config import Config
api_bp = Blueprint('api', __name__)
qa_system = QASystem()
embedding = load_embeddings()

# embedding = NotImplementedError

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@api_bp.route('/')
@login_required
def index():
    return render_template('api/index.html')

@api_bp.route('/upload', methods=['POST'])
@login_required
def upload():
    # 计时开始
    start_time = time.time()
    process_details = {
        'chunks': 0,
        'duration': 0.0,
        'filename': '',
        'file_size': 0
    }

    try:
        # 基础验证
        if 'file' not in request.files:
            raise ValueError('没有选择文件')

        file = request.files['file']
        if file.filename == '':
            raise ValueError('没有选择文件')

        # 打印原始文件名进行调试
        print(f"原始文件名: {file.filename}")

        # 分离文件名和后缀
        name, ext = os.path.splitext(file.filename)
        # 文件信息记录
        process_details['filename'] = file.filename
        process_details['file_size'] = len(file.read())
        file.seek(0)  # 重置文件指针

        # 打印处理后的文件名进行调试
        print(f"处理后的文件名: {process_details['filename']}")

        # 类型验证
        if not allowed_file(file.filename):
            raise ValueError('不支持的文件类型，请上传PDF或DOCX文件')

        filename = file.filename
        user_folder = os.path.join(
            current_app.config['UPLOAD_FOLDER_FILES'],
            f"user_{current_user.id}",  # 按用户隔离
            datetime.now().strftime("%Y%m%d")  # 按日期分类
        )
        os.makedirs(user_folder, exist_ok=True)
        save_path = os.path.join(user_folder, filename)
        print(f"📂 保存路径: {save_path}")
        counter = 1
        while os.path.exists(save_path):
            new_name = f"{counter}_{filename}"  # 构建新文件名
            save_path = os.path.join(user_folder, new_name)
            counter += 1
        file.save(save_path)
        # 文档处理流水线
        print('开始加载')
        documents = load_document(save_path)

        split_docs = split_text(documents)
        print(f"📄 文档分块: {len(split_docs)}")
        process_details['chunks'] = len(split_docs)
        print('开始向量化')
        update_vector_store(split_docs)

        # 计算耗时
        process_details['duration'] = round(time.time() - start_time, 2)

        # 响应处理
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'success',
                'message': '文件已成功添加到知识库',
                'data': process_details
            })
        else:
            flash(f"成功添加 {process_details['chunks']} 个文本块")
            return redirect(url_for('api.index'))

    except Exception as e:
        error_message = f'文件处理失败: {str(e)}'
        process_details['error'] = error_message
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'error',
                'message': error_message,
                'data': process_details
            }), 500
        else:
            flash(error_message)
            return redirect(url_for('api.index'))



import logging
logger = logging.getLogger('vector_store')

def update_vector_store(docs):
    vector_store_path = './vector_store/bert'
    try:
        print(f"▶️ 开始加载向量库 | 路径: {vector_store_path}")
        
        # 检查嵌入模型状态
        if not hasattr(embedding, 'client'):
            print("❌ 错误：嵌入模型未初始化")
            raise RuntimeError("嵌入模型未初始化")

        # 加载/创建向量库
        if os.path.exists(os.path.join(vector_store_path, "index.faiss")):
            print("检测到已有向量库文件")
            # db = FAISS.load_local(vector_store_path, embedding, allow_dangerous_deserialization=True)
            db = load_vectorstore()
            print(f"✅ 成功加载现有向量库 | 当前文档数: {db.index.ntotal}")
        else:
            print("⚠️ 未找到向量库，创建新库")
            # db = FAISS.from_documents([], embedding)
            print("✅ 新建空向量库完成")

        # 增量更新
        print(f"🔄 开始增量更新 | 待添加分块数: {len(docs)}")
        db.add_documents(docs)
        print(f"✅ 向量添加完成 | 更新后文档数: {db.index.ntotal}")

        # 保存操作
        print("💾 开始保存向量库...")
        # if os.path.exists(save):
        #     os.remove(save)
        # else:
            # os.makedirs(os.path.dirname(save), exist_ok=True)
        db.save_local(vector_store_path)

        print(f"✅ 向量库保存成功 | 存储路径: {vector_store_path}")

        return True

    except Exception as e:
        print(f"❌ 更新失败 | 错误类型: {type(e).__name__}")
        print(f"错误详情: {str(e)}")
        print("追踪信息:")
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"向量操作失败: {str(e)}") from e


def load_document(file_path):
    from langchain.document_loaders import (
        PyPDFium2Loader, 
        Docx2txtLoader,
        UnstructuredFileLoader
    )
    
    try:
        print(f"\n🔍 开始加载文件: {file_path}")
        
        if file_path.endswith('.pdf'):
            # PDF使用pypdfium2解析
            loader = PyPDFium2Loader(file_path)
            documents = loader.load()
            
        elif file_path.endswith('.docx'):
            # DOCX使用专用解析器
            loader = Docx2txtLoader(file_path)
            documents = loader.load()
            
        else:
            # 兜底解析器
            loader = UnstructuredFileLoader(file_path)  
            documents = loader.load()
            
        print(f"✅ 成功加载 {len(documents)} 页内容")
        return documents
        
    except Exception as e:
        error_msg = f"文档加载失败: {str(e)}"
        print(f"❌ {error_msg}")
        raise RuntimeError(error_msg)

# 增强版文本分块
def split_text(documents):
    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,  # 更适合中文的块大小
            chunk_overlap=50,
            separators=["\n\n", "。", "！", "？", "；"]
        )
        return text_splitter.split_documents(documents)
    except Exception as e:
        raise RuntimeError(f"文本分块失败: {str(e)}")
from sqlalchemy import text, asc
@api_bp.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    if request.method == 'POST':
        # 处理POST请求（来自历史记录页的查看按钮）
        data = request.get_json()
        chat_id = data.get('chatId')
        user_id = current_user.id  # 确保用户只能访问自己的会话

        # 查询指定会话
        current_session = Session.query.filter_by(user_id=user_id, id=chat_id).first()
        if not current_session:
            return jsonify({"error": "会话不存在或无权访问"}), 404
        
        # 获取当前会话的所有对话记录
        current_dialogues = Dialogue.query.filter_by(session_id=current_session.id).all()
        # 返回重定向指令，而非直接渲染模板
        return jsonify({"redirect": url_for('api.chat', session_id=chat_id ,
                                            dialogues=current_dialogues,
                                            current_session = current_session, 
                                            current_dialogues = current_session.dialogues[0] if current_session.dialogues else None)}), 200

    else:
        # 处理GET请求（含直接访问或重定向）
        session_id = request.args.get('session_id')

        # 根据是否携带session_id决定加载方式
        if session_id:
            # 验证会话存在且属于当前用户
            current_session = Session.query.filter_by(
                user_id=current_user.id, 
                id=session_id
            ).first()
            if not current_session:
                new_session = Session(user_id=current_user.id)
                db.session.add(new_session)
                db.session.commit()
                current_session = Session.query.filter_by(
                user_id=current_user.id, 
                id=session_id
            ).first()
        else:
            # 默认加载最新会话（兼容旧逻辑）
            current_session = Session.query.filter_by(user_id=current_user.id)\
                .order_by(Session.created_at.desc()).first()
        
        # 用户无会话时创建新会话
        if not current_session:
            try:
                
                existing_ids = [id_tuple[0] for id_tuple in db.session.query(Session.id)
                                .order_by(asc(Session.id)).all()]
                
                next_id = 1
                if existing_ids:
                    for index, session_id in enumerate(existing_ids):
                        if session_id > next_id:
                            break
                        next_id = session_id + 1
                
                current_session = Session(id=next_id, user_id=current_user.id)
                db.session.add(current_session)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise e

    # 获取当前会话的所有对话记录
    current_dialogues = Dialogue.query.filter_by(session_id=current_session.id).all()
    
    return render_template('api/chat.html',
                          dialogues=current_dialogues,
                          current_session=current_session,
                          current_dialogues=current_dialogues[0] if current_dialogues else None)
@api_bp.route('/new_session', methods=['POST'])
@login_required
def new_session():
        # 创建新会话
        new_session = Session(user_id=current_user.id)
        db.session.add(new_session)
        db.session.commit()

        # 获取对话数量（使用关系更高效）
        dialogues_count = len(new_session.dialogues)

        # 构造响应数据
        response_data = {
            "redirect": url_for('api.chat', session_id=new_session.id),
                "session_id": new_session.id,
                "created_at": new_session.created_at.isoformat(),
                "dialogues_count": dialogues_count
            
        }

        # 当有新对话时添加首条对话
        current_dialogue = None
        if dialogues_count > 0:
            current_dialogue = {
                "id": new_session.dialogues[0].id,
                "question": new_session.dialogues[0].question,
                "answer": new_session.dialogues[0].answer
            }
            response_data["current_dialogue"] = current_dialogue

        return jsonify({"redirect":url_for('api.chat', session=new_session)},response_data), 201   # 201 Created 状态码 


@api_bp.route('/ask', methods=['POST'])
@login_required
def ask():
    question = request.form['question']
    session_id = request.form.get('session_id')
    current_session = Session.query.filter_by(user_id=current_user.id)\
        .order_by(Session.created_at.desc()).first()
    
    if not current_session:
        current_session = Session(user_id=current_user.id)
        db.session.add(current_session)
        db.session.commit()  # 必须提交才能获取ID
    
    raw_markdown = qa_system.ask(question)
    # raw_markdown = "好的，我会尽快给您回复。"
    dialogue = Dialogue(
        user_id=current_user.id,
        session_id=session_id,
        question=question,
        answer=raw_markdown,
        timestamp=datetime.utcnow()
    )
    db.session.add(dialogue)
    db.session.commit()
    
    return jsonify({
        'answer': raw_markdown,
        'session_id': session_id
    })
  
@api_bp.route('/sessions')
@login_required
def get_sessions():
    sessions = Session.query.filter_by(user_id=current_user.id)\
        .options(db.joinedload(Session.dialogues))\
        .order_by(Session.created_at.desc()).all()
    
    return render_template('api/history.html', sessions=sessions)
from flask import abort
# 删除会话
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

@api_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def delete_session(session_id):
    try:
        session = Session.query.get_or_404(session_id)
        if session.user_id != current_user.id:
            abort(403)
        
        # 先删除关联的对话记录
        Dialogue.query.filter_by(session_id=session_id).delete()
        
        db.session.delete(session)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/dialogues/<int:dialogue_id>', methods=['DELETE'])
@login_required
@csrf.exempt  # 如果使用API token认证可以豁免CSRF
def delete_dialogue(dialogue_id):
    try:
        dialogue = Dialogue.query.filter_by(
            id=dialogue_id,
            user_id=current_user.id
        ).first_or_404()
        
        session_id = dialogue.session_id  # 获取会话ID用于更新计数
        
        db.session.delete(dialogue)
        db.session.commit()
        
        # 返回会话ID以便前端更新计数
        return jsonify({
            'status': 'success',
            'session_id': session_id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
    
def allowed_file_C(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS_L


# 论坛
