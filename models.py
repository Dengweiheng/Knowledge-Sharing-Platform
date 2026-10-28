from datetime import datetime
from exts import db
from flask_login import UserMixin

# Article-Tag Association Table
article_tag = db.Table('article_tag',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), primary_key=True)
)

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True)
    nickname = db.Column(db.String(50))
    avatar = db.Column(db.String(255), default='/static/images/default_avatar.png')
    role = db.Column(db.Enum('user', 'admin'), default='user')
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    articles = db.relationship('Article', backref='author', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='user', lazy=True)
    interactions = db.relationship('UserInteraction', backref='user', lazy=True)

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)

    articles = db.relationship('Article', backref='category', lazy=True)

class Tag(db.Model):
    __tablename__ = 'tag'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class Article(db.Model):
    __tablename__ = 'article'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.String(500))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id', ondelete='SET NULL'))
    cover_image = db.Column(db.String(255))
    view_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    collect_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Many-to-Many Relationship with Tags
    tags = db.relationship('Tag', secondary=article_tag, backref=db.backref('articles', lazy='dynamic'))
    comments = db.relationship('Comment', backref='article', lazy=True, cascade="all, delete-orphan")
    interactions = db.relationship('UserInteraction', backref='article', lazy=True, cascade="all, delete-orphan")


class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id', ondelete='CASCADE'), nullable=False)
    parent_id = db.Column(db.Integer, default=None)
    created_at = db.Column(db.DateTime, default=datetime.now)

class UserInteraction(db.Model):
    __tablename__ = 'user_interaction'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id', ondelete='CASCADE'), nullable=False)
    interaction_type = db.Column(db.Enum('view', 'like', 'collect', 'comment'), nullable=False)
    score = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.now)



