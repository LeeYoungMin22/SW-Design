# wsgi.py
"""
WSGI 배포를 위한 진입점
프로덕션 환경에서 Gunicorn, uWSGI 등의 WSGI 서버가 사용하는 파일
"""

import os
import sys
from app import create_app

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Flask 애플리케이션 생성
app = create_app()

if __name__ == "__main__":
		app.run()