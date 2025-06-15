# app/api/__init__.py
"""
FOODI 프로젝트 API 패키지 초기화
REST API 엔드포인트들을 통합 관리하는 패키지
"""

from flask import Blueprint

# API 블루프린트 등록
def register_blueprints(app):
		"""Flask 앱에 모든 API 블루프린트를 등록하는 함수"""
		
		from .chat import chat_bp
		from .restaurants import restaurants_bp
		from .reviews import reviews_bp
		from .recommendations import recommendations_bp
		
		# 각 API 블루프린트를 앱에 등록
		app.register_blueprint(chat_bp, url_prefix='/api/chat')
		app.register_blueprint(restaurants_bp, url_prefix='/api/restaurants')
		app.register_blueprint(reviews_bp, url_prefix='/api/reviews')
		app.register_blueprint(recommendations_bp, url_prefix='/api/recommendations')