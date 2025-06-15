# -*- coding: utf-8 -*-
"""
FOODI Flask 앱 메인 파일
OpenAI GPT-3.5-turbo 연동된 맛집 추천 시스템
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from flask import Flask, render_template
from app.config.database import db
from flask_cors import CORS
from flask_migrate import Migrate  # ✅ 추가
from dotenv import load_dotenv
import atexit

from app.routes import init_session_manager, cleanup_session_manager

# 환경변수 로드
load_dotenv()

# 로깅 설정
def setup_logging():
    """로깅 시스템 설정"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_filename = os.path.join(log_dir, f"foodi_{datetime.now().strftime('%Y%m%d')}.log")

    log_format = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger

# 로깅 초기화
logger = setup_logging()

# Flask-Migrate 및 DB 설정 추가
from app.config.database import db  # ✅ db 인스턴스 import
migrate = None  # 글로벌 선언

# 앱 팩토리 패턴
def create_app():
    """Flask 앱 팩토리"""
    app = Flask(__name__)
    CORS(app)

    app.logger.setLevel(logging.INFO)

    # 환경설정
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///foodi.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS 사용 시
    app.config['SESSION_COOKIE_HTTPONLY'] = True

    # DB, Migrate 초기화
    db.init_app(app)
    global migrate
    migrate = Migrate(app, db)  # ✅ Migrate 등록

    # OpenAI 환경확인 출력
    openai_api_key = os.getenv('OPENAI_API_KEY')
    openai_model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    if not openai_api_key:
        print("⚠️  OPENAI_API_KEY가 설정되지 않았습니다.")
    else:
        print(f"✅ OpenAI API 설정 완료: {openai_model}")

    # 블루프린트 등록
    from app.routes import main_bp, auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    app.template_folder = 'templates'
    app.static_folder = 'static'
    

    @app.context_processor
    def inject_global_vars():
        return {
            'app_name': 'FOODI',
            'app_version': '1.0.0',
            'openai_enabled': bool(openai_api_key),
            'openai_model': openai_model
        }

    # 애플리케이션 종료 시 정리
    atexit.register(cleanup_session_manager)

    # 오류 페이지 핸들러
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('error.html', error_code=404, error_message="페이지를 찾을 수 없습니다."), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('error.html', error_code=500, error_message="서버 내부 오류가 발생했습니다."), 500

    return app

# 앱 실행 엔트리포인트
app = create_app()

if __name__ == '__main__':
    print("🚀 FOODI 서버 시작")
    print(f"📍 환경: {os.getenv('FLASK_ENV', 'development')}")
    print(f"🤖 AI 모델: {os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')}")
    print(f"🔑 API 키 설정: {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}")

    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    )
