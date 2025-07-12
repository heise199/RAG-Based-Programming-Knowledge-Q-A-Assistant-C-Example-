from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    pwd = db.Column(db.String(256), nullable=False)
    avatar = db.Column(db.String(256))

    def set_password(self, password):
        self.pwd = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.pwd, password)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    likes = db.relationship('Like', backref='liker', lazy='dynamic')
    
from datetime import datetime
from datetime import datetime, timezone
from flask import current_app

class Dialogue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    question = db.Column(db.String(500))
    answer = db.Column(db.String(1000))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    
class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True,) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    dialogues = db.relationship('Dialogue', backref='session', lazy=True)

    # 关系定义
    user = db.relationship('User', backref=db.backref('vectors', lazy=True))

class VectorOperationLog(db.Model):
    __tablename__ = 'vector_operation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    operation_type = db.Column(db.String(20), nullable=False)  # upload/delete/update
    file_name = db.Column(db.String(256))
    document_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系定义
    user = db.relationship('User', backref=db.backref('vector_logs', lazy=True))
    


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True)
    likes = db.relationship('Like', backref='post', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class Like(db.Model):
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='uq_user_post'),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)