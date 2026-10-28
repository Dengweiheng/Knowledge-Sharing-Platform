from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import User, UserInteraction, Article, Comment
from exts import db
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import os
import uuid

# 个人中心路由蓝图注册
user_bp = Blueprint('user', __name__, url_prefix='/user')

def allowed_file(filename):
    """
    检查上传的文件格式是否合法
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    个人中心主页与个人基本资料更新
    - GET: 查询并展示当前用户点赞的文章、收藏的文章以及发表的历史评论
    - POST: 修改昵称及邮箱（包含邮箱防重复占用校验）
    """
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        email = request.form.get('email')
        
        # 邮箱防重复占用校验（若修改了邮箱，需确保未被其他人使用）
        if email != current_user.email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('邮箱已被占用', 'danger')
                return redirect(url_for('user.profile'))
        
        current_user.nickname = nickname
        current_user.email = email
        db.session.commit()
        flash('个人信息更新成功', 'success')
        return redirect(url_for('user.profile'))
        
    # 查询当前用户点赞过的文章列表
    liked_interactions = UserInteraction.query.filter_by(user_id=current_user.id, interaction_type='like').all()
    # 查询当前用户收藏过的文章列表
    collected_interactions = UserInteraction.query.filter_by(user_id=current_user.id, interaction_type='collect').all()
    
    liked_articles = [interaction.article for interaction in liked_interactions if interaction.article]
    collected_articles = [interaction.article for interaction in collected_interactions if interaction.article]
    
    # 查询当前用户发表的评论列表（按时间倒序）
    comments = Comment.query.filter_by(user_id=current_user.id).order_by(Comment.created_at.desc()).all()

    return render_template('user/profile.html', 
                         liked_articles=liked_articles, 
                         collected_articles=collected_articles,
                         comments=comments)

@user_bp.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    """
    用户头像上传接口
    - 校验图片合法性与扩展名
    - 自动创建 avatars 存储目录
    - 通过 UUID 重命名头像文件防止命名冲突
    - 更新数据库中用户的头像相对路径
    """
    if 'avatar' not in request.files:
        flash('未选择图片', 'danger')
        return redirect(url_for('user.profile'))
    
    file = request.files['avatar']
    if file.filename == '':
        flash('未选择图片', 'danger')
        return redirect(url_for('user.profile'))
    
    if file and allowed_file(file.filename):
        # 确保头像存储目录存在
        avatar_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')
        if not os.path.exists(avatar_dir):
            os.makedirs(avatar_dir)
            
        # 安全处理文件名并追加 UUID 唯一标识
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(avatar_dir, unique_filename)
        
        file.save(file_path)
        
        # 将头像网络访问路径存入数据库
        current_user.avatar = f"/static/uploads/avatars/{unique_filename}"
        db.session.commit()
        
        flash('头像上传成功', 'success')
    else:
        flash('文件类型不支持', 'danger')
        
    return redirect(url_for('user.profile'))

@user_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """
    用户修改密码接口
    - 校验旧密码正确性（check_password_hash）
    - 校验新密码一致性与最小长度限制（>=6位）
    - 新密码哈希散列加密入库（generate_password_hash）
    """
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    from werkzeug.security import check_password_hash
    if not check_password_hash(current_user.password, old_password):
        flash('旧密码错误', 'danger')
        return redirect(url_for('user.profile'))
    
    if new_password != confirm_password:
        flash('两次输入的新密码不一致', 'danger')
        return redirect(url_for('user.profile'))
    
    if len(new_password) < 6:
        flash('新密码长度至少为 6 位', 'danger')
        return redirect(url_for('user.profile'))
    
    # 加密并保存新密码
    current_user.password = generate_password_hash(new_password)
    db.session.commit()
    
    flash('密码修改成功', 'success')
    return redirect(url_for('user.profile'))
