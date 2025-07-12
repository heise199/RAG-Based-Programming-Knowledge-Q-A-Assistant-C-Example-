from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config import Config
from flask_login import LoginManager
import markdown
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
csrf = CSRFProtect()
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['WTF_CSRF_CHECK_DEFAULT'] = False  # 禁用默认检查
    app.config['WTF_CSRF_METHODS'] = [ 'DELETE']  # 指定需要验证的方法
    app.config.from_object(Config)
    db.init_app(app)
    app.config['SECRET_KEY'] = 'your-secret-key-here'  # 必须设置密钥
    
    # 初始化 CSRF
    csrf.init_app(app)
    

    # 必须先初始化login_manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # 设置登录路由端点
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.model import User  # 避免循环导入
        return User.query.get(int(user_id))
    
    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    from app.api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    @app.template_filter('datetime_format')
    def datetime_format_filter(dt):
        if dt is None:
            return ""
        try:
            # 格式化为：2023-07-20 14:30
            return dt.strftime("%Y-%m-%d %H:%M")
        except AttributeError:
            # 处理非日期类型的情况
            return str(dt)
    @app.template_filter('time_since')
    def time_since(dt):
        now = datetime.datetime.utcnow()
        diff = now - dt
        periods = (
            (diff.days // 365, '年'),
            (diff.days // 30, '月'),
            (diff.days // 7, '周'),
            (diff.days, '天'),
            (diff.seconds // 3600, '小时'),
            (diff.seconds // 60, '分钟'),
            (diff.seconds, '秒'),
        )
        for period, unit in periods:
            if period >= 1:
                return f'{period}{unit}前'
        return '刚刚'
    return app