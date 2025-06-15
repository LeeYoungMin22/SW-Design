# -*- coding: utf-8 -*-
"""
FOODI Flask 애플리케이션 팩토리
Flask 앱 인스턴스 생성 및 확장 기능들을 초기화합니다.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config.database import db 
from flask_cors import CORS
from flask_caching import Cache
import logging
import os

# Flask 확장 기능들 초기화 (앱 인스턴스 없이 먼저 생성)
#db = SQLAlchemy()
cache = Cache()

def create_app(config_name=None):
		"""
		Flask 애플리케이션 팩토리 함수
		설정에 따라 Flask 앱 인스턴스를 생성하고 초기화합니다.
		
		Args:
				config_name (str): 사용할 설정 이름 (development, production 등)
		
		Returns:
				Flask: 초기화된 Flask 애플리케이션 인스턴스
		"""
		# 현재 파일의 상위 디렉토리를 기준으로 templates 폴더 찾기
		template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
		static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))

		# Flask 앱 인스턴스 생성
		app = Flask(__name__, 
								template_folder=template_dir,
								static_folder=static_dir)
   
		# 설정 로드
		from app.config.settings import Config
		app.config.from_object(Config)
		
		# 로깅 설정
		setup_logging(app)
		
		# 데이터베이스 초기화
		db.init_app(app)
		
		# CORS 설정 (프론트엔드와의 통신을 위해)
		CORS(app, resources={
				r"/api/*": {
						"origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
						"methods": ["GET", "POST", "PUT", "DELETE"],
						"allow_headers": ["Content-Type", "Authorization"]
				}
		})
		
		# 캐시 초기화 (API 응답 속도 향상을 위해)
		cache.init_app(app, config={
				'CACHE_TYPE': 'simple',
				'CACHE_DEFAULT_TIMEOUT': 300
		})
		
		# 블루프린트 등록 (API 라우트들)
		register_blueprints(app)
		
		# 애플리케이션 컨텍스트 내에서 데이터베이스 테이블 생성
		with app.app_context():
				create_tables()
		
		# 에러 핸들러 등록
		register_error_handlers(app)
		
		app.logger.info("🍽️ FOODI 애플리케이션이 성공적으로 초기화되었습니다.")
		
		return app

def register_blueprints(app):
    """
    애플리케이션에 블루프린트를 등록하는 함수
    
    Args:
        app: Flask 애플리케이션 인스턴스
    """
    try:
        # 메인 라우트 블루프린트 등록 (최우선)
        from app.routes import main_bp
        app.register_blueprint(main_bp)
        
        # API 블루프린트들 등록
        try:
            from app.api.chat import chat_bp
            app.register_blueprint(chat_bp, url_prefix='/api/chat')
        except ImportError:
            print("⚠️  Chat API 블루프린트를 찾을 수 없습니다.")
        
        try:
            from app.api.restaurants import restaurants_bp
            app.register_blueprint(restaurants_bp, url_prefix='/api/restaurants')
        except ImportError:
            print("⚠️  Restaurants API 블루프린트를 찾을 수 없습니다.")
        
        try:
            from app.api.reviews import reviews_bp
            app.register_blueprint(reviews_bp, url_prefix='/api/reviews')
        except ImportError:
            print("⚠️  Reviews API 블루프린트를 찾을 수 없습니다.")
        
        try:
            from app.api.recommendations import recommendations_bp
            app.register_blueprint(recommendations_bp, url_prefix='/api/recommendations')
        except ImportError:
            print("⚠️  Recommendations API 블루프린트를 찾을 수 없습니다.")
        
        print("✅ 메인 블루프린트가 등록되었습니다.")
        
    except ImportError as e:
        print(f"❌ 메인 블루프린트 등록 실패: {e}")
        # 기본 라우트를 직접 등록
        @app.route('/')
        def index():
            return {
                'message': '🍽️ FOODI 맛집 추천 챗봇에 오신 것을 환영합니다!',
                'status': 'running',
                'note': '블루프린트 로드 실패로 기본 라우트를 사용 중입니다.'
            }
        print("✅ 기본 라우트가 등록되었습니다.")

def create_tables():
		"""
		데이터베이스 테이블을 생성하는 함수
		앱 시작 시 필요한 테이블들이 존재하지 않으면 자동으로 생성합니다.
		"""
		try:
				# 모든 모델 클래스들을 임포트 (테이블 생성을 위해)
				from app.models.user import User
				from app.models.restaurant import Restaurant
				from app.models.review import Review
				from app.models.recommendation import Recommendation
				
				# 테이블 생성
				db.create_all()
				print("✅ 데이터베이스 테이블이 성공적으로 생성되었습니다.")
				
		except Exception as e:
				print(f"❌ 데이터베이스 테이블 생성 중 오류 발생: {e}")

def setup_logging(app):
		"""
		애플리케이션 로깅을 설정하는 함수
		개발 및 프로덕션 환경에 따라 다른 로깅 레벨을 적용합니다.
		"""
		if not app.debug:
				# 프로덕션 환경에서는 INFO 레벨 이상만 로그 기록
				logging.basicConfig(
						level=logging.INFO,
						format='%(asctime)s %(levelname)s: %(message)s',
						handlers=[
								logging.FileHandler('foodi.log'),
								logging.StreamHandler()
						]
				)
		else:
				# 개발 환경에서는 DEBUG 레벨까지 모든 로그 기록
				logging.basicConfig(level=logging.DEBUG)
    
def setup_app_logging(app):
    """
    애플리케이션 로깅을 설정하는 함수
    
    Args:
        app: Flask 애플리케이션 인스턴스
    """
    try:
        from app.config.logging import setup_logging
        setup_logging(app)
    except ImportError:
        # 로깅 설정 파일이 없어도 기본 로깅은 작동하도록 함
        app.logger.warning("로깅 설정 파일을 찾을 수 없습니다. 기본 로깅을 사용합니다.")

def register_error_handlers(app):
		"""
		전역 에러 핸들러들을 등록하는 함수
		HTTP 오류나 예외 상황에 대한 일관된 응답을 제공합니다.
		"""
		
		@app.errorhandler(404)
		def not_found_error(error):
				"""페이지를 찾을 수 없음 (404) 에러 처리"""
				return {
						'error': 'Not Found',
						'message': '요청하신 페이지를 찾을 수 없습니다.',
						'status_code': 404
				}, 404
		
		@app.errorhandler(500)
		def internal_error(error):
				"""내부 서버 오류 (500) 에러 처리"""
				db.session.rollback()  # 데이터베이스 롤백
				return {
						'error': 'Internal Server Error',
						'message': '서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
						'status_code': 500
				}, 500
		
		@app.errorhandler(400)
		def bad_request_error(error):
				"""잘못된 요청 (400) 에러 처리"""
				return {
						'error': 'Bad Request',
						'message': '잘못된 요청입니다. 입력 데이터를 확인해주세요.',
						'status_code': 400
				}, 400
    
# 전역 접근을 위한 객체들 export
__all__ = ['create_app', 'db']