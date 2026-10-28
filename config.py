import os

class Config:
    # Database Configuration - Update with your actual MySQL credentials
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:1234@localhost:3306/article_platform?charset=utf8mb4'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.urandom(24)
    
    # Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
