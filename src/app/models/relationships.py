# -*- coding: utf-8 -*-
"""
모델 간의 관계를 설정하는 파일
모든 모델이 로드된 후에 관계를 설정합니다.
"""

from sqlalchemy.orm import relationship, backref
from app import db

def configure_relationships():
    """
    모든 모델이 로드된 후 관계를 설정합니다.
    이 함수는 app/__init__.py에서 호출되어야 합니다.
    """
    from app.models.user import User
    from app.models.restaurant import Restaurant
    from app.models.review import Review
    
    # Review와 User 관계 설정
    Review.user = relationship(
        'User',
        backref=backref('reviews', lazy='dynamic', cascade='all, delete-orphan'),
        lazy='select'
    )
    
    # Review와 Restaurant 관계 설정
    Review.restaurant = relationship(
        'Restaurant',
        backref=backref('reviews', lazy='dynamic', cascade='all, delete-orphan'),
        foreign_keys=[Review.restaurant_id, Review.restaurant_address],
        lazy='select'
    )
    
    print("모델 관계 설정 완료!")

def setup_event_listeners():
    """
    SQLAlchemy 이벤트 리스너를 설정합니다.
    """
    from sqlalchemy import event
    from app.models.review import Review
    
    @event.listens_for(Review, 'after_insert')
    def update_restaurant_rating_after_insert(mapper, connection, target):
        """리뷰가 추가된 후 식당 평점 업데이트"""
        # 별도 세션에서 처리하여 트랜잭션 충돌 방지
        pass  # 필요시 구현
    
    @event.listens_for(Review, 'after_update')
    def update_restaurant_rating_after_update(mapper, connection, target):
        """리뷰가 수정된 후 식당 평점 업데이트"""
        # 별도 세션에서 처리하여 트랜잭션 충돌 방지
        pass  # 필요시 구현