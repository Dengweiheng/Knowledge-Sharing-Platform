from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from models import User
from exts import db
from werkzeug.security import generate_password_hash, check_password_hash

# 用户认证路由蓝图注册
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    用户注册接口
    - GET: 渲染注册页面
    - POST: 处理注册表单，包括用户名唯一性校验、邮箱唯一性校验、密码哈希加盐加密入库
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        # 1. 校验用户名是否已被注册
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('用户名已存在')
            return redirect(url_for('auth.register'))
            
        # 2. 校验邮箱是否已被注册
        email_exists = User.query.filter_by(email=email).first()
        if email_exists:
            flash('该邮箱已被注册')
            return redirect(url_for('auth.register'))
            
        # 3. 创建新用户（密码使用 generate_password_hash 进行安全散列加密）
        new_user = User(
            username=username,
            password=generate_password_hash(password),
            email=email
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('注册成功，请登录')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    用户登录接口
    - GET: 渲染登录页面
    - POST: 验证用户名与密码散列值（check_password_hash），登录成功后根据角色自动跳转（管理员进后台，普通用户进首页）
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        # 校验用户存在且密码 Hash 匹配
        if user and check_password_hash(user.password, password):
            login_user(user) # 写入 Flask-Login Session 会话
            if user.role == 'admin':
                return redirect(url_for('admin.index'))
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误')
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """
    用户退出登录接口
    清除当前会话状态并重定向至首页
    """
    logout_user()
    return redirect(url_for('index'))
