# -*- coding: utf-8 -*-
"""
리뷰(Review) 데이터 모델
사용자 리뷰, 평점, 감정 분석 결과를 관리하는 SQLAlchemy 모델입니다.
"""

from datetime import datetime
#from app import db
from app.config.database import db
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy import Index

class Review(db.Model):
    """
    사용자 리뷰 정보를 저장하는 테이블
    평점, 리뷰 내용, 감정 분석 결과, 유용성 평가를 관리합니다.
    """

    __tablename__ = 'reviews'

    # === 기본 정보 ===
    id = db.Column(db.Integer, primary_key=True, comment='리뷰 고유 ID')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='작성자 ID')

    # 🔽 복합 외래키 구성
    restaurant_id = db.Column(db.String, nullable=False, comment='식당 고유 ID')
    restaurant_address = db.Column(db.String, nullable=False, comment='식당 주소')

    # 복합 외래키 제약 조건
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['restaurant_id', 'restaurant_address'],
            ['restaurants.restaurant_id', 'restaurants.address']
        ),
        Index('idx_review_user', 'user_id'),
        Index('idx_review_restaurant', 'restaurant_id'),
        Index('idx_review_rating', 'rating'),
        Index('idx_review_date', 'created_at'),
        Index('idx_review_sentiment', 'sentiment_score'),
    )

    # === 평점 정보 ===
    rating = db.Column(db.Integer, nullable=False, comment='전체 평점 (1-5)')
    taste_rating = db.Column(db.Integer, comment='맛 평점 (1-5)')
    service_rating = db.Column(db.Integer, comment='서비스 평점 (1-5)')
    atmosphere_rating = db.Column(db.Integer, comment='분위기 평점 (1-5)')
    value_rating = db.Column(db.Integer, comment='가성비 평점 (1-5)')

    # === 리뷰 내용 ===
    title = db.Column(db.String(100), comment='리뷰 제목')
    content = db.Column(db.Text, nullable=False, comment='리뷰 내용')

    # === 방문 정보 ===
    visit_date = db.Column(db.Date, comment='방문 날짜')
    visit_purpose = db.Column(db.String(50), comment='방문 목적 (데이트, 가족, 회식 등)')
    party_size = db.Column(db.Integer, comment='동행 인원 수')

    # === 주문 정보 ===
    ordered_items = db.Column(JSON, default=list, comment='주문한 메뉴들')
    total_cost = db.Column(db.Integer, comment='총 비용')

    # === 감정 분석 ===
    sentiment_score = db.Column(db.Float, comment='감정 점수 (-1.0 ~ 1.0)')
    sentiment_label = db.Column(db.String(20), comment='감정 라벨 (positive, negative, neutral)')
    emotion_tags = db.Column(JSON, default=list, comment='감정 태그들')

    # === 키워드 ===
    keywords = db.Column(JSON, default=list, comment='추출된 키워드들')
    positive_aspects = db.Column(JSON, default=list, comment='긍정적 요소들')
    negative_aspects = db.Column(JSON, default=list, comment='부정적 요소들')

    # === 유용성 평가 ===
    helpful_count = db.Column(db.Integer, default=0, comment='도움됨 수')
    not_helpful_count = db.Column(db.Integer, default=0, comment='도움안됨 수')

    # === 추천 관련 ===
    would_recommend = db.Column(db.Boolean, comment='추천 의사')
    would_revisit = db.Column(db.Boolean, comment='재방문 의사')

    # === 시스템 관리 ===
    is_active = db.Column(db.Boolean, default=True, comment='활성 상태')
    is_verified = db.Column(db.Boolean, default=False, comment='검증된 리뷰 여부')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='작성일')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='수정일')

    # === 관계 설정 (지연 로딩 방식) ===
    @property
    def user(self):
        """사용자 정보를 지연 로딩으로 가져옵니다."""
        from app.models.user import User
        return User.query.get(self.user_id)
    
    @property  
    def restaurant(self):
        """식당 정보를 지연 로딩으로 가져옵니다."""
        from app.models.restaurant import Restaurant
        return Restaurant.query.filter_by(
            restaurant_id=self.restaurant_id,
            address=self.restaurant_address
        ).first()

    def __init__(self, user_id, restaurant_id, restaurant_address, rating, content, **kwargs):
        self.user_id = user_id
        self.restaurant_id = restaurant_id
        self.restaurant_address = restaurant_address
        self.rating = rating
        self.content = content.strip()

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self, include_user=False, include_restaurant=False):
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'restaurant_id': self.restaurant_id,
            'restaurant_address': self.restaurant_address,
            'rating': self.rating,
            'detailed_ratings': {
                'taste': self.taste_rating,
                'service': self.service_rating,
                'atmosphere': self.atmosphere_rating,
                'value': self.value_rating
            },
            'title': self.title,
            'content': self.content,
            'visit_info': {
                'date': self.visit_date.isoformat() if self.visit_date else None,
                'purpose': self.visit_purpose,
                'party_size': self.party_size
            },
            'ordered_items': self.ordered_items or [],
            'total_cost': self.total_cost,
            'sentiment': {
                'score': self.sentiment_score,
                'label': self.sentiment_label,
                'tags': self.emotion_tags or []
            },
            'keywords': self.keywords or [],
            'positive_aspects': self.positive_aspects or [],
            'negative_aspects': self.negative_aspects or [],
            'helpfulness': {
                'helpful': self.helpful_count,
                'not_helpful': self.not_helpful_count,
                'ratio': self.get_helpfulness_ratio()
            },
            'recommendations': {
                'would_recommend': self.would_recommend,
                'would_revisit': self.would_revisit
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_verified': self.is_verified
        }

        if include_user and hasattr(self, 'user') and self.user:
            result['user'] = {
                'username': self.user.username,
                'location': self.user.location
            }

        if include_restaurant and hasattr(self, 'restaurant') and self.restaurant:
            result['restaurant'] = {
                'name': self.restaurant.name,
                'category': self.restaurant.category
            }

        return result

    def analyze_sentiment(self):
        from app.utils.sentiment_analyzer import analyze_text_sentiment
        try:
            result = analyze_text_sentiment(self.content)
            self.sentiment_score = result.get('score', 0.0)
            self.sentiment_label = result.get('label', 'neutral')
            self.emotion_tags = result.get('emotions', [])
            self.keywords = result.get('keywords', [])
            self.positive_aspects = result.get('positive_aspects', [])
            self.negative_aspects = result.get('negative_aspects', [])
            db.session.commit()
        except Exception as e:
            print(f"감정 분석 중 오류 발생: {e}")

    def add_ordered_item(self, item_name, price=None, rating=None):
        if not self.ordered_items:
            self.ordered_items = []
        self.ordered_items.append({
            'name': item_name,
            'price': price,
            'rating': rating,
            'added_at': datetime.utcnow().isoformat()
        })
        db.session.commit()

    def get_helpfulness_ratio(self):
        total = self.helpful_count + self.not_helpful_count
        return round(self.helpful_count / total, 2) if total else 0.0

    def mark_helpful(self, helpful=True):
        if helpful:
            self.helpful_count += 1
        else:
            self.not_helpful_count += 1
        db.session.commit()

    def get_rating_summary(self):
        details = [
            self.taste_rating,
            self.service_rating,
            self.atmosphere_rating,
            self.value_rating
        ]
        valid = [r for r in details if r is not None]
        return {
            'average': round(sum(valid) / len(valid), 1) if valid else self.rating,
            'count': len(valid) or 1,
            'breakdown': {
                'taste': self.taste_rating,
                'service': self.service_rating,
                'atmosphere': self.atmosphere_rating,
                'value': self.value_rating
            }
        }

    def is_positive_review(self):
        return (self.rating >= 4) or (self.sentiment_score and self.sentiment_score > 0.1)

    def get_time_ago(self):
        if not self.created_at:
            return "알 수 없음"
        diff = datetime.utcnow() - self.created_at
        if diff.days >= 30:
            return f"{diff.days // 30}개월 전"
        elif diff.days > 0:
            return f"{diff.days}일 전"
        elif diff.seconds >= 3600:
            return f"{diff.seconds // 3600}시간 전"
        elif diff.seconds >= 60:
            return f"{diff.seconds // 60}분 전"
        return "방금 전"

    def update_after_restaurant_visit(self):
        if self.restaurant:
            self.restaurant.update_rating()

    def __repr__(self):
        return f'<Review {self.id} by User {self.user_id}>'

    def __str__(self):
        return f'평점 {self.rating}/5 - {self.content[:50]}...'