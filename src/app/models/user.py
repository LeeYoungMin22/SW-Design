# -*- coding: utf-8 -*-
"""
사용자(User) 데이터 모델
사용자 정보, 인증, 프로필을 관리하는 SQLAlchemy 모델입니다.
"""

from datetime import datetime
from app.config.database import db
from sqlalchemy.dialects.postgresql import JSON
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    """
    사용자 정보를 저장하는 테이블
    로그인, 프로필, 선호도 등을 관리합니다.
    """

    __tablename__ = 'users'

    # === 기본 정보 ===
    id = db.Column(db.Integer, primary_key=True, comment='사용자 고유 ID')
    username = db.Column(db.String(50), unique=True, nullable=False, comment='사용자명')
    email = db.Column(db.String(120), unique=True, nullable=True, comment='이메일 주소')
    password_hash = db.Column(db.String(128), nullable=False, comment='비밀번호 해시')

    # === 위치 및 지역 정보 ===
    location = db.Column(db.String(100), default='대구 달서구', comment='기본 위치')
    preferred_radius = db.Column(db.Integer, default=5, comment='선호 검색 반경(km)')

    # === 개인 선호도 설정 ===
    food_preferences = db.Column(JSON, default=lambda: {}, comment='음식 선호도 (JSON)')
    budget_range = db.Column(db.String(20), default='20000-30000', comment='예산 범위')
    dietary_restrictions = db.Column(JSON, default=lambda: [], comment='식단 제한사항')

    # === 시스템 관리 정보 ===
    is_active = db.Column(db.Boolean, default=True, comment='계정 활성화 상태')
    is_admin = db.Column(db.Boolean, default=False, comment='관리자 권한')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='계정 생성일')
    last_login = db.Column(db.DateTime, comment='마지막 로그인 시간')
    #last_activity = db.Column(db.DateTime, comment='마지막 활동 시간')

    # === 통계 정보 ===
    review_count = db.Column(db.Integer, default=0, comment='작성한 리뷰 수')
    average_rating_given = db.Column(db.Float, default=0.0, comment='평균 평점')

    # === 세션 및 상태 관리 ===
    current_session_id = db.Column(db.String(100), comment='현재 채팅 세션 ID')
    session_data = db.Column(JSON, default=lambda: {}, comment='세션 데이터 저장')

    # === 관계 설정 ===
    reviews = db.relationship('Review', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    recommendations = db.relationship('Recommendation', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def __init__(self, username, email, password, **kwargs):
        self.username = username
        self.email = email.lower()
        self.set_password(password)

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def review_list(self):
        if not hasattr(self, '_reviews_cache'):
            from app.models.review import Review
            self._reviews_cache = Review.query.filter_by(user_id=self.id).order_by(Review.created_at.desc())
        return self._reviews_cache

    def get_reviews(self, limit=None, active_only=True):
        from app.models.review import Review
        query = Review.query.filter_by(user_id=self.id)
        if active_only:
            query = query.filter_by(is_active=True)
        query = query.order_by(Review.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query

    def get_recent_reviews(self, limit=5):
        return self.get_reviews(limit=limit).all()

    def to_dict(self, include_reviews=False, include_personal=False):
        result = {
            'id': self.id,
            'username': self.username,
            'location': self.location,
            'review_count': self.review_count,
            'average_rating_given': self.average_rating_given,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

        if include_personal:
            result.update({
                'email': self.email,
                'dietary_restrictions': self.dietary_restrictions or []
                #'last_activity': self.last_activity.isoformat() if self.last_activity else None
            })

        if include_reviews:
            result['recent_reviews'] = [
                review.to_dict() for review in self.get_recent_reviews()
            ]

        return result
    
    def update_session(self, session_id, session_info=None):
        """
        사용자의 세션 정보를 업데이트합니다.
    
        :param session_id: 새 세션 ID
        :param session_info: 세션 관련 추가 정보 (dict)
        """
        self.current_session_id = session_id
        if session_info and isinstance(session_info, dict):
            self.session_data.update(session_info)
        self.last_login = datetime.utcnow()
        db.session.commit()


    def update_activity(self):
        self.last_activity = datetime.utcnow()
        db.session.commit()

    def update_review_stats(self):
        reviews = self.get_reviews(active_only=True).all()
        self.review_count = len(reviews)
        if reviews:
            self.average_rating_given = round(sum(r.rating for r in reviews) / len(reviews), 1)
        else:
            self.average_rating_given = 0.0
        db.session.commit()

    def add_dietary_restriction(self, restriction):
        if not self.dietary_restrictions:
            self.dietary_restrictions = []
        if restriction not in self.dietary_restrictions:
            self.dietary_restrictions.append(restriction)
            db.session.commit()

    def get_recommended_restaurants(self, limit=10):
        from app.models.restaurant import Restaurant
        query = Restaurant.query.filter_by(is_active=True)
        query = query.order_by(Restaurant.rating_average.desc(), Restaurant.rating_count.desc())
        return query.limit(limit).all()

    def can_review_restaurant(self, restaurant_id, restaurant_address):
        existing_review = self.get_reviews().filter_by(
            restaurant_id=restaurant_id,
            restaurant_address=restaurant_address
        ).first()
        return existing_review is None

    def __repr__(self):
        return f'<User {self.username}>'

    def __str__(self):
        return f'{self.username} ({self.email})'
