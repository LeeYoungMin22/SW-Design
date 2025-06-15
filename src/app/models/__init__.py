# app/models/__init__.py
"""
FOODI 프로젝트 모델 패키지 초기화
데이터 모델 클래스들을 통합 관리하는 패키지
"""

from .user import User
from .restaurant import Restaurant
from .review import Review
from .recommendation import Recommendation

__all__ = ['User', 'Restaurant', 'Review', 'Recommendation']