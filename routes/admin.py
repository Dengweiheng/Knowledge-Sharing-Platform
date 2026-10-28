from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from exts import db
from models import User, Article, Category, Tag, Comment, UserInteraction
from sqlalchemy import func
from functools import wraps

# 后台管理路由蓝图注册
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """
    管理员权限校验装饰器（垂直权限控制）
    非管理员用户或未登录用户访问时自动拦截并重定向至首页
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('您没有权限访问管理后台')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@admin_required
def index():
    """
    后台数据看板（Dashboard）首页
    统计与可视化：
    1. 核心指标统计：用户总数、文章总数、评论总数、全站总阅读量
    2. 最近动态：最新注册的 5 个用户、最新发布的 5 篇文章
    3. ECharts 图表数据：
       - 各分类下的文章数量分布（分类占比柱状/饼图）
       - 最近 7 天全站交互活跃度趋势（点赞/收藏/评论折线图）
    """
    # 基础指标统计
    user_count = User.query.count()
    article_count = Article.query.count()
    comment_count = Comment.query.count()
    total_views = db.session.query(func.sum(Article.view_count)).scalar() or 0
    
    # 最近数据
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_articles = Article.query.order_by(Article.created_at.desc()).limit(5).all()
    
    # ECharts 数据源 1：各分类文章数量统计（左外连接确保 0 篇文章的分类也被统计到）
    category_data = db.session.query(
        Category.name, func.count(Article.id)
    ).join(Article, Category.id == Article.category_id, isouter=True) \
     .group_by(Category.name).all()
    
    cat_names = [r[0] for r in category_data]
    cat_counts = [r[1] for r in category_data]
    
    # ECharts 数据源 2：统计近 7 天互动热度趋势（排除仅浏览）
    import datetime
    today = datetime.datetime.now()
    trend_data = []
    for i in range(6, -1, -1):
        date = (today - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
        count = UserInteraction.query.filter(
            func.date(UserInteraction.created_at) == date,
            UserInteraction.interaction_type != 'view'
        ).count()
        trend_data.append({'date': date, 'count': count})
    
    return render_template('admin/index.html', 
                         user_count=user_count, 
                         article_count=article_count,
                         comment_count=comment_count,
                         total_views=total_views,
                         recent_users=recent_users,
                         recent_articles=recent_articles,
                         cat_names=cat_names,
                         cat_counts=cat_counts,
                         trend_data=trend_data)

@admin_bp.route('/users')
@admin_required
def users():
    """
    后台用户管理列表
    """
    users_list = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users_list)

@admin_bp.route('/articles')
@admin_required
def articles():
    """
    后台文章管理列表
    """
    articles_list = Article.query.order_by(Article.created_at.desc()).all()
    return render_template('admin/articles.html', articles=articles_list)

@admin_bp.route('/user/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """
    管理员删除用户接口
    包含防误删自身的安全限制
    """
    if user_id == current_user.id:
        return jsonify({'code': 400, 'msg': '不能删除自己'})
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'code': 200, 'msg': '用户已删除'})

@admin_bp.route('/article/delete/<int:article_id>', methods=['POST'])
@admin_required
def delete_article(article_id):
    """
    管理员删除文章接口
    """
    article = Article.query.get_or_404(article_id)
    db.session.delete(article)
    db.session.commit()
    return jsonify({'code': 200, 'msg': '文章已删除'})

@admin_bp.route('/comments')
@admin_required
def comments():
    """
    后台评论管理列表
    """
    comments_list = Comment.query.order_by(Comment.created_at.desc()).all()
    return render_template('admin/comments.html', comments=comments_list)

@admin_bp.route('/comment/delete/<int:comment_id>', methods=['POST'])
@admin_required
def delete_comment(comment_id):
    """
    管理员删除违规评论接口
    """
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({'code': 200, 'msg': '评论已删除'})
