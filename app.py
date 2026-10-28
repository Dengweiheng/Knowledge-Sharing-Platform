from flask import Flask, render_template
import os
from exts import db
from config import Config
from models import User, Category, Article
from flask_login import LoginManager, current_user
from services.recommendation_service import RecommendationService

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.jinja_env.globals.update(zip=zip)

    
    # Initialize extensions
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    from routes.article import article_bp
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.user import user_bp

    
    app.register_blueprint(article_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)


    @app.route('/')
    def index():
        # Get recommendations
        if current_user.is_authenticated:
            recommendations = RecommendationService.get_user_recommendations(current_user.id)
        else:
            recommendations = RecommendationService.get_trending_articles(6)
            
        categories = Category.query.all()
        return render_template('index.html', 
                             recommendations=recommendations, 
                             categories=categories)

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # Ensure database tables are created
        db.create_all()
        
        # Ensure static folders exist
        static_folders = [
            Config.UPLOAD_FOLDER,
            os.path.join(os.getcwd(), 'static/images/covers')
        ]
        for folder in static_folders:
            if not os.path.exists(folder):
                os.makedirs(folder)
                
    app.run(debug=True)
