from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from exts import db
from models import Article, Category, Tag, article_tag, UserInteraction, Comment
import os
import uuid
from werkzeug.utils import secure_filename
from config import Config
from services.recommendation_service import RecommendationService

# 文章路由蓝图注册
article_bp = Blueprint('article', __name__, url_prefix='/article')

def allowed_file(filename):
    """
    检查上传的文件格式是否合法
    :param filename: 文件名
    :return: True/False
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@article_bp.route('/publish', methods=['GET', 'POST'])
@login_required
def publish():
    """
    文章发布接口
    - GET: 渲染发布文章页面，并传入所有分类供下拉选择
    - POST: 处理文章发布表单数据（封面上传、文章创建、多标签关联）
    """
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category_id = request.form.get('category_id')
        tags_str = request.form.get('tags')  # 前端传入的逗号分隔标签字符串
        summary = request.form.get('summary')
        
        # 1. 处理封面图片上传
        cover_image = None
        file = request.files.get('cover_image')
        if file and file.filename != '':
            if allowed_file(file.filename):
                # 使用 UUID 重命名文件，防止同名文件冲突覆盖
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                
                # 确保上传目录存在
                if not os.path.exists(Config.UPLOAD_FOLDER):
                    os.makedirs(Config.UPLOAD_FOLDER)
                file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
                cover_image = f'/static/uploads/{filename}'
            else:
                flash('不支持的文件格式，仅支持 png, jpg, jpeg, gif, webp')

        # 2. 实例化新文章对象
        new_article = Article(
            title=title,
            content=content,
            summary=summary,
            author_id=current_user.id,
            category_id=category_id if category_id else None,
            cover_image=cover_image
        )
        
        # 3. 处理多对多标签关联（Tag Association）
        if tags_str:
            tag_names = [t.strip() for t in tags_str.split(',') if t.strip()]
            for name in tag_names:
                # 若标签已存在则复用，不存在则新增
                tag = Tag.query.filter_by(name=name).first()
                if not tag:
                    tag = Tag(name=name)
                    db.session.add(tag)
                new_article.tags.append(tag)
        
        db.session.add(new_article)
        db.session.commit()
        
        flash('文章发布成功！')
        return redirect(url_for('article.detail', article_id=new_article.id))
        
    categories = Category.query.all()
    return render_template('article/publish.html', categories=categories)

@article_bp.route('/edit/<int:article_id>', methods=['GET', 'POST'])
@login_required
def edit(article_id):
    """
    文章编辑接口
    - 权限校验：仅文章作者本人或系统管理员有权编辑
    - POST: 更新文章标题、内容、摘要、所属分类、封面及标签
    """
    article = Article.query.get_or_404(article_id)
    # 水平越权校验：防篡改他人文章
    if article.author_id != current_user.id and current_user.role != 'admin':
        flash('您没有权限修改此文章')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        article.title = request.form.get('title')
        article.content = request.form.get('content')
        article.summary = request.form.get('summary')
        article.category_id = request.form.get('category_id')
        
        # 更新标签：先清空原有标签关联，再重新绑定新标签
        tags_str = request.form.get('tags')
        article.tags = [] # 清空旧关联
        if tags_str:
            tag_names = [t.strip() for t in tags_str.split(',') if t.strip()]
            for name in tag_names:
                tag = Tag.query.filter_by(name=name).first()
                if not tag:
                    tag = Tag(name=name)
                    db.session.add(tag)
                article.tags.append(tag)
                
        # 更新封面图（若用户上传了新封面）
        file = request.files.get('cover_image')
        if file and file.filename != '':
            if allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                
                if not os.path.exists(Config.UPLOAD_FOLDER):
                    os.makedirs(Config.UPLOAD_FOLDER)
                file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
                article.cover_image = f'/static/uploads/{filename}'
            else:
                flash('不支持的文件格式，仅支持 png, jpg, jpeg, gif, webp')
            
        db.session.commit()
        flash('文章更新成功！')
        return redirect(url_for('article.detail', article_id=article.id))
        
    categories = Category.query.all()
    tags_str = ', '.join([t.name for t in article.tags])
    return render_template('article/publish.html', article=article, categories=categories, tags_str=tags_str)

@article_bp.route('/detail/<int:article_id>')
def detail(article_id):
    """
    文章详情页接口
    - 累加文章浏览量（view_count）
    - 隐式反馈收集：若用户已登录，记录一条浏览行为（score=1.0），为个性化推荐提供数据
    - 加载并展示该文章的所有评论
    """
    article = Article.query.get_or_404(article_id)
    # 浏览量自增
    article.view_count += 1
    
    # 收集用户浏览行为（用于后续画像偏好统计）
    if current_user.is_authenticated:
        interaction = UserInteraction(
            user_id=current_user.id,
            article_id=article_id,
            interaction_type='view',
            score=1.0 # 浏览行为基础分为 1.0
        )
        db.session.add(interaction)
        
    # 查询当前文章的所有评论（按创建时间倒序）
    comments = Comment.query.filter_by(article_id=article_id).order_by(Comment.created_at.desc()).all()
    
    db.session.commit()
    return render_template('article/detail.html', article=article, comments=comments)

@article_bp.route('/comment/<int:article_id>', methods=['POST'])
@login_required
def post_comment(article_id):
    """
    发表评论接口（AJAX POST 请求）
    - 校验评论内容非空
    - 保存评论记录
    - 记录强兴趣交互行为（评论赋以较高权重分 score=4.0）
    """
    content = request.json.get('content')
    if not content or not content.strip():
        return jsonify({'code': 400, 'msg': '评论内容不能为空'})
        
    comment = Comment(
        content=content,
        user_id=current_user.id,
        article_id=article_id
    )
    
    # 记录交互行为：评论代表强兴趣信号
    interaction = UserInteraction(
        user_id=current_user.id,
        article_id=article_id,
        interaction_type='comment',
        score=4.0 # 评论行为权重分为 4.0
    )
    
    db.session.add(comment)
    db.session.add(interaction)
    db.session.commit()
    
    return jsonify({
        'code': 200, 
        'msg': '评论成功',
        'comment': {
            'username': current_user.nickname or current_user.username,
            'content': content,
            'created_at': '刚刚'
        }
    })

@article_bp.route('/interact/<int:article_id>', methods=['POST'])
@login_required
def interact(article_id):
    """
    文章交互接口：点赞 / 收藏（AJAX POST 请求）
    - 幂等性与防重复校验：同一用户对同一文章的同种操作仅能生效一次
    - 记录交互行为并赋予推荐权重：点赞=3.0分，收藏=5.0分
    - 实时累加文章的点赞数或收藏数
    """
    type = request.json.get('type') # 'like' 点赞 或 'collect' 收藏
    if type not in ['like', 'collect']:
        return jsonify({'code': 400, 'msg': '无效操作'})
        
    article = Article.query.get_or_404(article_id)
    
    # 防刷/幂等校验：检查是否已经操作过
    existing = UserInteraction.query.filter_by(
        user_id=current_user.id, 
        article_id=article_id, 
        interaction_type=type
    ).first()
    
    if existing:
        return jsonify({'code': 201, 'msg': '已经操作过了'})
        
    # 赋予行为权重分：收藏行为权重高于点赞
    score = 3.0 if type == 'like' else 5.0
    interaction = UserInteraction(
        user_id=current_user.id,
        article_id=article_id,
        interaction_type=type,
        score=score
    )
    
    # 同步更新文章表中的计数统计
    if type == 'like':
        article.like_count += 1
    else:
        article.collect_count += 1
        
    db.session.add(interaction)
    db.session.commit()
    return jsonify({'code': 200, 'msg': '操作成功', 'count': (article.like_count if type == 'like' else article.collect_count)})

@article_bp.route('/list')
def list_articles():
    """
    文章列表与动态复合检索接口
    支持多维度联合筛选：
    1. 分类筛选（category_id）
    2. 标签筛选（tag_id，涉及多表连接）
    3. 全文模糊搜索（q，匹配标题、内容或摘要）
    按发布时间降序分页/展示
    """
    category_id = request.args.get('category_id', type=int)
    tag_id = request.args.get('tag_id', type=int)
    search_query = request.args.get('q', '')
    
    query = Article.query
    
    # 动态构建 SQL 过滤条件
    if category_id:
        query = query.filter(Article.category_id == category_id)
    
    if tag_id:
        query = query.join(Article.tags).filter(Tag.id == tag_id)
        
    if search_query:
        query = query.filter(
            (Article.title.contains(search_query)) | 
            (Article.content.contains(search_query)) |
            (Article.summary.contains(search_query))
        )
        
    articles = query.order_by(Article.created_at.desc()).all()
    categories = Category.query.all()
    
    return render_template('article/list.html', 
                         articles=articles, 
                         categories=categories, 
                         current_category=category_id,
                         search_query=search_query)

@article_bp.route('/delete/<int:article_id>', methods=['POST'])
@login_required
def delete(article_id):
    """
    文章删除接口
    - 权限校验：仅作者本人或系统管理员可删除
    """
    article = Article.query.get_or_404(article_id)
    if article.author_id != current_user.id and current_user.role != 'admin':
        return jsonify({'code': 403, 'msg': '无权删除'})
    
    db.session.delete(article)
    db.session.commit()
    return jsonify({'code': 200, 'msg': '已删除'})

@article_bp.route('/recommendations')
@login_required
def recommendations():
    """
    独立个性化推荐页面
    调用 RecommendationService 召回更多篇（limit=20）个性化推荐文章
    """
    recs = RecommendationService.get_user_recommendations(current_user.id, limit=20)
    return render_template('article/recommendations.html', articles=recs)
