# -*- coding: utf-8 -*-
"""
식당(Restaurant) 데이터 모델
식당 정보, 메뉴, 위치, 운영시간 등을 관리하는 SQLAlchemy 모델입니다.
"""

from datetime import datetime
#from app import db
from sqlalchemy.dialects.postgresql import JSON
from app.config.database import db
from sqlalchemy.orm import relationship
from sqlalchemy import Index

class Restaurant(db.Model):
    """
    식당 정보를 저장하는 메인 테이블
    기본 정보, 위치, 메뉴, 운영시간, 평점 등을 관리합니다.
    """
    
    __tablename__ = 'restaurants'

    # === 복합 기본키 ===
    restaurant_id = db.Column(db.String, nullable=False, comment='식당 고유 ID')
    address = db.Column(db.String(200), nullable=False, comment='주소')

    # === 복합 기본키 설정 ===
    __table_args__ = (
        db.PrimaryKeyConstraint('restaurant_id', 'address'),
        Index('idx_restaurant_name', 'name'),
        Index('idx_restaurant_category', 'category'),
        Index('idx_restaurant_district', 'district'),
        Index('idx_restaurant_location', 'latitude', 'longitude'),
        Index('idx_restaurant_rating', 'rating_average'),
        Index('idx_restaurant_price', 'average_price'),
    )

    # === 일반 정보 ===
    name = db.Column(db.String(100), nullable=False, comment='식당 이름')
    description = db.Column(db.Text, comment='식당 설명')

    # === 위치 정보 ===
    district = db.Column(db.String(50), default='달서구', comment='구/군')
    neighborhood = db.Column(db.String(50), comment='동/면')
    latitude = db.Column(db.Float, comment='위도')
    longitude = db.Column(db.Float, comment='경도')

    # === 연락처 ===
    phone = db.Column(db.String(20), comment='전화번호')
    website = db.Column(db.String(200), comment='웹사이트 URL')

    # === 카테고리 ===
    category = db.Column(db.String(50), nullable=False, comment='주요 카테고리')
    cuisine_type = db.Column(db.String(50), comment='요리 종류')
    sub_categories = db.Column(JSON, default=list, comment='세부 카테고리들')

    # === 메뉴 및 가격 ===
    menu_items = db.Column(JSON, default=list, comment='메뉴 목록 (JSON)')
    average_price = db.Column(db.Integer, comment='평균 가격 (1인당)')
    price_range = db.Column(db.String(20), comment='가격대 (예: 10000-20000)')

    # === 운영 정보 ===
    business_hours = db.Column(JSON, default=dict, comment='운영시간 (JSON)')
    closed_days = db.Column(JSON, default=list, comment='휴무일')
    parking_available = db.Column(db.Boolean, default=False, comment='주차 가능 여부')
    delivery_available = db.Column(db.Boolean, default=False, comment='배달 가능 여부')
    takeout_available = db.Column(db.Boolean, default=True, comment='포장 가능 여부')

    # === 평점 ===
    rating_average = db.Column(db.Float, default=0.0, comment='평균 평점')
    rating_count = db.Column(db.Integer, default=0, comment='리뷰 개수')
    foodi_score = db.Column(db.Float, default=0.0, comment='FOODI 자체 점수')

    # === 태그 ===
    special_features = db.Column(JSON, default=list, comment='특별한 특징들')
    atmosphere_tags = db.Column(JSON, default=list, comment='분위기 태그들')

    # === 시스템 관리 ===
    is_active = db.Column(db.Boolean, default=True, comment='운영 상태')
    is_verified = db.Column(db.Boolean, default=False, comment='정보 검증 여부')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='등록일')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='수정일')

    # === 관계 설정 (지연 로딩 + 캐싱) ===
    @property
    def reviews(self):
        """식당의 모든 리뷰를 가져옵니다."""
        if not hasattr(self, '_reviews_cache'):
            from app.models.review import Review
            self._reviews_cache = Review.query.filter_by(
                restaurant_id=self.restaurant_id,
                restaurant_address=self.address
            ).order_by(Review.created_at.desc())
        return self._reviews_cache
    
    def get_reviews(self, limit=None, active_only=True):
        """식당의 리뷰를 가져옵니다."""
        from app.models.review import Review
        query = Review.query.filter_by(
            restaurant_id=self.restaurant_id,
            restaurant_address=self.address
        )
        if active_only:
            query = query.filter_by(is_active=True)
        query = query.order_by(Review.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query
    
    def get_recent_reviews(self, limit=5):
        """최근 리뷰를 가져옵니다."""
        return self.get_reviews(limit=limit).all()

    def __init__(self, restaurant_id, address, name, category, **kwargs):
        self.restaurant_id = restaurant_id
        self.address = address
        self.name = name
        self.category = category

        # 기본 운영시간 설정
        self.business_hours = {
            'monday': {'open': '11:00', 'close': '22:00'},
            'tuesday': {'open': '11:00', 'close': '22:00'},
            'wednesday': {'open': '11:00', 'close': '22:00'},
            'thursday': {'open': '11:00', 'close': '22:00'},
            'friday': {'open': '11:00', 'close': '22:00'},
            'saturday': {'open': '11:00', 'close': '22:00'},
            'sunday': {'open': '11:00', 'close': '22:00'}
        }

        # 추가 속성 초기화
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self, include_reviews=False):
        result = {
            'restaurant_id': self.restaurant_id,
            'address': self.address,
            'name': self.name,
            'description': self.description,
            'district': self.district,
            'neighborhood': self.neighborhood,
            'phone': self.phone,
            'website': self.website,
            'category': self.category,
            'cuisine_type': self.cuisine_type,
            'sub_categories': self.sub_categories or [],
            'menu_items': self.menu_items or [],
            'average_price': self.average_price,
            'price_range': self.price_range,
            'business_hours': self.business_hours or {},
            'closed_days': self.closed_days or [],
            'parking_available': self.parking_available,
            'delivery_available': self.delivery_available,
            'takeout_available': self.takeout_available,
            'rating_average': self.rating_average,
            'rating_count': self.rating_count,
            'foodi_score': self.foodi_score,
            'special_features': self.special_features or [],
            'atmosphere_tags': self.atmosphere_tags or [],
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'location': {
                'latitude': self.latitude,
                'longitude': self.longitude
            } if self.latitude and self.longitude else None
        }

        if include_reviews:
            result['recent_reviews'] = [
                review.to_dict() for review in self.get_recent_reviews()
            ]
        return result

    def add_menu_item(self, name, price, description=None, category=None):
        if not self.menu_items:
            self.menu_items = []

        self.menu_items.append({
            'name': name,
            'price': price,
            'description': description,
            'category': category,
            'added_at': datetime.utcnow().isoformat()
        })

        self._update_average_price()
        db.session.commit()

    def _update_average_price(self):
        if self.menu_items:
            prices = [item['price'] for item in self.menu_items if item.get('price')]
            if prices:
                self.average_price = int(sum(prices) / len(prices))
                self.price_range = f"{min(prices)}-{max(prices)}"

    def is_open_now(self):
        from datetime import datetime
        now = datetime.now()
        day = now.strftime('%A').lower()

        if day in (self.closed_days or []):
            return False

        hours = self.business_hours.get(day)
        if not hours:
            return False

        try:
            now_time = now.time()
            open_time = datetime.strptime(hours['open'], '%H:%M').time()
            close_time = datetime.strptime(hours['close'], '%H:%M').time()
            if close_time < open_time:
                return now_time >= open_time or now_time <= close_time
            else:
                return open_time <= now_time <= close_time
        except:
            return False

    def update_rating(self):
        reviews = self.get_reviews(active_only=True).all()
        if reviews:
            self.rating_average = round(sum(r.rating for r in reviews) / len(reviews), 1)
            self.rating_count = len(reviews)
        else:
            self.rating_average = 0.0
            self.rating_count = 0
        self.foodi_score = self._calculate_foodi_score()
        db.session.commit()

    def _calculate_foodi_score(self):
        base = self.rating_average
        review_bonus = min(self.rating_count * 0.01, 0.5)
        verified_bonus = 0.1 if self.is_verified else 0
        feature_bonus = len(self.special_features or []) * 0.05
        return min(round(base + review_bonus + verified_bonus + feature_bonus, 1), 5.0)

    def __repr__(self):
        return f'<Restaurant {self.name}>'

    def __str__(self):
        return f'{self.name} ({self.district})'