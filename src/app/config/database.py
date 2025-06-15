# -*- coding: utf-8 -*-
"""
FOODI 데이터베이스 설정 및 연결 관리
SQLAlchemy를 통한 데이터베이스 초기화와 연결 풀 관리를 담당합니다.
"""

import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from flask_sqlalchemy import SQLAlchemy

# 로거 설정
logger = logging.getLogger(__name__)

# SQLAlchemy 객체 생성 (순환 import 방지)
db = SQLAlchemy()

class DatabaseManager:
    """
    데이터베이스 연결과 설정을 관리하는 클래스
    """
    
    @staticmethod
    def init_database(app):
        """
        데이터베이스를 초기화하고 앱과 연결하는 메소드
        
        Args:
            app: Flask 애플리케이션 인스턴스
        """
        try:
            # SQLAlchemy 앱과 연결
            db.init_app(app)
            
            # 데이터베이스 디렉토리 생성 (SQLite 사용 시)
            if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
                DatabaseManager._ensure_sqlite_directory(app.config['SQLALCHEMY_DATABASE_URI'])
            
            # SQLAlchemy 엔진 설정
            DatabaseManager._configure_engine(app)
            
            # 데이터베이스 연결 테스트
            with app.app_context():
                db.engine.execute('SELECT 1')
                logger.info("✅ 데이터베이스 연결이 성공적으로 설정되었습니다.")
                
        except Exception as e:
            logger.error(f"❌ 데이터베이스 초기화 중 오류 발생: {e}")
            raise
    
    @staticmethod
    def _ensure_sqlite_directory(database_uri):
        """
        SQLite 데이터베이스 파일을 위한 디렉토리를 생성하는 메소드
        
        Args:
            database_uri (str): 데이터베이스 URI
        """
        if database_uri.startswith('sqlite:///'):
            # SQLite 파일 경로 추출
            db_path = database_uri.replace('sqlite:///', '')
            db_dir = os.path.dirname(db_path)
            
            # 디렉토리가 존재하지 않으면 생성
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"📁 데이터베이스 디렉토리 생성: {db_dir}")
    
    @staticmethod
    def _configure_engine(app):
        """
        SQLAlchemy 엔진 설정을 최적화하는 메소드
        
        Args:
            app: Flask 애플리케이션 인스턴스
        """
        engine_options = {}
        
        # SQLite 특화 설정
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            engine_options.update({
                'poolclass': StaticPool,
                'pool_pre_ping': True,
                'pool_recycle': 300,
                'connect_args': {
                    'check_same_thread': False,  # 멀티스레딩 지원
                    'timeout': 10
                }
            })
        
        # PostgreSQL 특화 설정
        elif 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
            engine_options.update({
                'pool_size': 10,
                'max_overflow': 20,
                'pool_pre_ping': True,
                'pool_recycle': 3600
            })
        
        # 엔진 옵션을 Flask 설정에 추가
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_options
    
    @staticmethod
    def create_tables(app):
        """
        모든 데이터베이스 테이블을 생성하는 메소드
        
        Args:
            app: Flask 애플리케이션 인스턴스
        """
        with app.app_context():
            try:
                # 모델들을 임포트하여 테이블 스키마 등록
                from app.models.user import User
                from app.models.restaurant import Restaurant
                from app.models.review import Review
                from app.models.recommendation import Recommendation
                
                # 테이블 생성
                db.create_all()
                logger.info("📋 모든 데이터베이스 테이블이 생성되었습니다.")
                
                # 기본 데이터 삽입
                DatabaseManager._insert_default_data()
                
            except Exception as e:
                logger.error(f"❌ 테이블 생성 중 오류 발생: {e}")
                raise
    
    @staticmethod
    def _insert_default_data():
        """
        시스템 운영에 필요한 기본 데이터를 삽입하는 메소드
        """
        try:
            # 기본 사용자 생성 (시스템 관리자)
            from app.models.user import User
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@foodi.com',
                    location='대구 달서구',
                    is_admin=True
                )
                db.session.add(admin_user)
            
            # 기본 식당 카테고리나 데이터가 있다면 여기서 추가
            # (실제 식당 데이터는 별도 스크립트로 관리하는 것을 권장)
            
            db.session.commit()
            logger.info("📝 기본 데이터가 성공적으로 삽입되었습니다.")
            
        except Exception as e:
            logger.error(f"❌ 기본 데이터 삽입 중 오류 발생: {e}")
            db.session.rollback()
    
    @staticmethod
    def backup_database(backup_path=None):
        """
        데이터베이스를 백업하는 메소드 (SQLite 전용)
        
        Args:
            backup_path (str): 백업 파일 저장 경로
        """
        try:
            from app.config.settings import Config
        except ImportError:
            logger.error("❌ 설정 모듈을 import할 수 없습니다.")
            return False
        
        if 'sqlite' not in Config.SQLALCHEMY_DATABASE_URI:
            logger.warning("⚠️ 현재는 SQLite 데이터베이스만 백업을 지원합니다.")
            return False
        
        try:
            import shutil
            from datetime import datetime
            
            # 원본 데이터베이스 파일 경로
            db_path = Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
            
            # 백업 파일 경로 설정
            if backup_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"backup_foodi_{timestamp}.db"
            
            # 파일 복사로 백업 수행
            shutil.copy2(db_path, backup_path)
            logger.info(f"💾 데이터베이스 백업 완료: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 데이터베이스 백업 중 오류 발생: {e}")
            return False

# SQLite 성능 최적화를 위한 이벤트 리스너
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    SQLite 연결 시 성능 최적화 설정을 적용하는 이벤트 리스너
    """
    if 'sqlite' in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        
        # 성능 최적화 PRAGMA 설정
        pragma_settings = [
            "PRAGMA foreign_keys=ON",           # 외래 키 제약 조건 활성화
            "PRAGMA journal_mode=WAL",          # WAL 모드로 동시성 향상
            "PRAGMA synchronous=NORMAL",        # 동기화 수준 조정
            "PRAGMA cache_size=1000",           # 캐시 크기 증가
            "PRAGMA temp_store=memory"          # 임시 테이블을 메모리에 저장
        ]
        
        for pragma in pragma_settings:
            try:
                cursor.execute(pragma)
            except Exception as e:
                logger.warning(f"⚠️ PRAGMA 설정 중 오류: {pragma} - {e}")
        
        cursor.close()

# =============================================================================
# 함수 래퍼들 - app.config.__init__.py에서 import하기 위한 호환성 함수들
# =============================================================================

def init_database(app):
    """
    데이터베이스를 초기화하는 함수 (DatabaseManager.init_database의 래퍼)
    
    Args:
        app: Flask 애플리케이션 인스턴스
    
    Returns:
        SQLAlchemy: 데이터베이스 객체
    """
    DatabaseManager.init_database(app)
    return db

def get_database_connection():
    """
    현재 데이터베이스 연결을 반환하는 함수
    
    Returns:
        SQLAlchemy: 데이터베이스 객체
    """
    return db

def create_database_tables(app):
    """
    모든 데이터베이스 테이블을 생성하는 함수 (DatabaseManager.create_tables의 래퍼)
    
    Args:
        app: Flask 애플리케이션 인스턴스
    """
    return DatabaseManager.create_tables(app)

def backup_database(backup_path=None):
    """
    데이터베이스를 백업하는 함수 (DatabaseManager.backup_database의 래퍼)
    
    Args:
        backup_path (str): 백업 파일 저장 경로
    
    Returns:
        bool: 백업 성공 여부
    """
    return DatabaseManager.backup_database(backup_path)

# 전역 접근을 위한 별칭
database = db