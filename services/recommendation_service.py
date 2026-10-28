from models import UserInteraction, Article, Category
from exts import db
from sqlalchemy import func, desc

class RecommendationService:
    """
    个性化推荐服务类
    提供基于用户历史行为画像的混合推荐（基于内容/分类偏好 + 全站热度兜底）及热门文章榜单功能。
    """

    @staticmethod
    def get_user_recommendations(user_id, limit=6):
        """
        获取指定用户的个性化推荐文章列表

        推荐算法策略（混合推荐）：
        1. 基于内容（分类偏好）：分析用户历史交互（浏览、点赞、收藏等），计算各分类兴趣得分，召回用户偏好分类下的高热度文章。
        2. 热度兜底（冷启动/补齐）：针对新用户（无历史记录）或推荐列表数量不足的情况，使用全站热门文章进行补齐。
        3. 去重机制：过滤掉用户已经产生过交互行为的文章，避免重复推荐。

        :param user_id: 用户ID
        :param limit: 返回推荐文章的数量，默认 6 篇
        :return: 推荐的文章对象列表（List[Article]）
        """
        
        # 1. 构建用户偏好画像：分析用户的历史交互行为
        # 联表查询用户交互过的文章所属分类，并按行为权重分求和（pref_score），计算用户在各分类下的偏好得分
        preferences = db.session.query(
            Article.category_id, 
            func.sum(UserInteraction.score).label('pref_score')
        ).join(UserInteraction, Article.id == UserInteraction.article_id) \
         .filter(UserInteraction.user_id == user_id) \
         .group_by(Article.category_id) \
         .order_by(desc('pref_score')).all()
         
        # 查询用户已经交互过的文章ID列表（用于去重过滤，防止重复推荐用户已看/已点赞的文章）
        interacted_article_ids = db.session.query(UserInteraction.article_id) \
            .filter(UserInteraction.user_id == user_id).distinct().all()
        interacted_article_ids = [r[0] for r in interacted_article_ids]
        
        recommended_articles = []
        
        # 2. 基于偏好分类的内容召回（Content-Based Recommendation）
        if preferences:
            # 提取用户感兴趣的分类ID列表（按偏好得分由高到低）
            pref_category_ids = [p[0] for p in preferences if p[0] is not None]
            
            # 召回用户偏好分类中未读的高质量文章（按 浏览量 + 点赞量*2 降序排序）
            content_recs = Article.query.filter(
                Article.category_id.in_(pref_category_ids),
                Article.id.not_in(interacted_article_ids) if interacted_article_ids else True
            ).order_by(desc(Article.view_count + Article.like_count * 2)).limit(limit).all()
            
            recommended_articles.extend(content_recs)
            
        # 3. 热门兜底与补全（Popularity Fallback）
        # 若推荐结果不足 limit 篇（如新用户冷启动或偏好分类文章较少），使用全站热门文章补齐
        if len(recommended_articles) < limit:
            remaining_limit = limit - len(recommended_articles)
            existing_ids = [a.id for a in recommended_articles]
            
            # 排除已在推荐列表中和用户已交互过的文章，按综合热度（浏览量 + 点赞量*5）排序取前 N 篇
            popular_recs = Article.query.filter(
                Article.id.not_in(existing_ids + interacted_article_ids) if (existing_ids + interacted_article_ids) else True
            ).order_by(desc(Article.view_count + Article.like_count * 5)).limit(remaining_limit).all()
            
            recommended_articles.extend(popular_recs)
            
        return recommended_articles

    @staticmethod
    def get_trending_articles(limit=5):
        """
        获取全站综合热度排行榜文章（适用于未登录用户或全站热门推荐）

        热度计算权重公式：
        综合热度 = 浏览量 * 0.1 + 点赞数 * 2 + 收藏数 * 3

        :param limit: 获取的热门文章数量，默认 5 篇
        :return: 热门文章对象列表（List[Article]）
        """
        return Article.query.order_by(
            desc(Article.view_count * 0.1 + Article.like_count * 2 + Article.collect_count * 3)
        ).limit(limit).all()
