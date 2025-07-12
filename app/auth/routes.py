from flask import Blueprint, render_template, redirect, url_for, request, flash,current_app
from werkzeug.utils import secure_filename
from app import db
from app.model import User
from app.config import Config
import os

auth_bp = Blueprint('auth', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS_P

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        avatar = request.files['avatar']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('用户名已存在')
            return redirect(url_for('auth.register'))
        
        if avatar and allowed_file(avatar.filename):
            filename = secure_filename(avatar.filename)
            save_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            avatar.save(save_path)
            avatar_url = f'uploads/{filename}'
        else:
            flash('请上传有效的图片文件')
            return redirect(url_for('auth.register'))

        new_user = User(username=username, avatar=avatar_url)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('注册成功，请登录')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')
from flask_login import login_user ,current_user
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)  # 新增：记录用户登录状态 ⭐️
            flash('登录成功')
            if username == 'admin':
                
                return redirect(url_for('api.index'))
            else:
                return redirect(url_for('api.chat'))
        else:
            flash('用户名或密码错误')
            # 改为渲染模板而不是重定向，保留表单数据
            return render_template('auth/login.html')  # ⭐️

    return render_template('auth/login.html')

from flask_login import logout_user, login_required  # Add these imports at the top

@auth_bp.route('/logout')
@login_required  # Ensures only logged-in users can access this route
def logout():
    logout_user()  # This will clear the user session
    flash('您已成功退出登录')
    return redirect(url_for('auth.login'))  # Redirect to login page after logout


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Handle form submission
        username = request.form.get('username')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        avatar = request.files.get('avatar')

        # Update username if changed
        if username and username != current_user.username:
            # Check if username already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('用户名已存在', 'error')
            else:
                current_user.username = username
                flash('用户名更新成功', 'success')

        # Update password if provided
        if new_password:
            if new_password != confirm_password:
                flash('两次输入的密码不一致', 'error')
            else:
                current_user.set_password(new_password)
                flash('密码更新成功', 'success')

        # Update avatar if provided
        if avatar and allowed_file(avatar.filename):
            # Delete old avatar file if it exists
            if current_user.avatar:
                old_avatar_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 
                                             current_user.avatar.split('/')[-1])
                if os.path.exists(old_avatar_path):
                    os.remove(old_avatar_path)
            
            # Save new avatar
            filename = secure_filename(avatar.filename)
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            avatar.save(save_path)
            current_user.avatar = f'uploads/{filename}'
            flash('头像更新成功', 'success')
        elif avatar and not allowed_file(avatar.filename):
            flash('请上传有效的图片文件', 'error')

        # Commit changes to database
        db.session.commit()

        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html', user=current_user)