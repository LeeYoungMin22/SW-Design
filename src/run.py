#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FOODI 애플리케이션 실행 스크립트
개발 서버를 시작하는 진입점입니다.
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from app import create_app

def main():
    """메인 함수"""
    # 환경 설정
    config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Flask 앱 생성
    app = create_app(config_name)
    
    # 기본 라우트 추가 (임시)
    @app.route('/')
    def index():
        """메인 페이지"""
        return {
            'message': '🍽️ FOODI 맛집 추천 챗봇에 오신 것을 환영합니다!',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'api': '/api',
                'chat': '/api/chat',
                'restaurants': '/api/restaurants',
                'reviews': '/api/reviews',
                'recommendations': '/api/recommendations'
            }
        }
    
    @app.route('/health')
    def health_check():
        """헬스 체크 엔드포인트"""
        return {
            'status': 'healthy',
            'timestamp': str(datetime.utcnow()),
            'database': 'connected'
        }
    
    # 개발 서버 실행
    if __name__ == '__main__':
        print("🚀 FOODI 서버를 시작합니다...")
        print(f"📍 환경: {config_name}")
        print(f"🌐 URL: http://localhost:5000")
        print("⏹️  종료하려면 Ctrl+C를 누르세요")
        
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True if config_name == 'development' else False
        )

if __name__ == '__main__':
    from datetime import datetime
    main()