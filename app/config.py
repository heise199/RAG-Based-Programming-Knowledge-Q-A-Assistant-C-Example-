import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'your-secret-key'
    
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI') or \
        'mysql+pymysql://root:root@localhost/c++'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    UPLOAD_FOLDER_FILES = os.path.join(os.path.dirname(__file__), 'static', 'konwlage_files')
    FAISS_STORE_PATH = os.path.join(os.path.dirname(__file__), 'static', 'faiss_files')
    ALLOWED_EXTENSIONS_P = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB
    # UPLOAD_FOLDER = os.path.abspath('./storage/documents')  # 持久化存储目录
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}
    ALLOWED_EXTENSIONS_L = {'png', 'jpg', 'jpeg', 'gif'}
    # 自动创建目录
    os.makedirs(UPLOAD_FOLDER_FILES, exist_ok=True)

    UPLOAD_FOLDER_L = os.path.join(os.path.dirname(__file__), 'static', 'uploads_L')