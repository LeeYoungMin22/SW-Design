# tests/__init__.py
"""
FOODI 프로젝트 테스트 패키지
단위 테스트와 통합 테스트를 포함하는 테스트 모듈
"""

import unittest
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 테스트 설정
TEST_DATABASE_PATH = ':memory:'  # 인메모리 SQLite 데이터베이스 사용
TEST_API_BASE_URL = 'http://localhost:5000/api'