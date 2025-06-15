# app/config/__init__.py
"""
FOODI 프로젝트 설정 패키지 초기화
애플리케이션 전체 설정을 통합 관리하는 패키지
"""

from .settings import DevelopmentConfig, ProductionConfig, TestingConfig
from .database import init_database, get_database_connection
from .logging import setup_logging

# 환경별 설정 매핑
config_mapping = {
		'development': DevelopmentConfig,
		'production': ProductionConfig,
		'testing': TestingConfig
}

def get_config(environment='development'):
		"""
		환경에 따른 설정 클래스를 반환하는 함수
		
		Args:
				environment (str): 환경 이름 (development, production, testing)
		
		Returns:
				Config: 해당 환경의 설정 클래스
		"""
		return config_mapping.get(environment, DevelopmentConfig)

__all__ = [
		'DevelopmentConfig',
		'ProductionConfig', 
		'TestingConfig',
		'init_database',
		'get_database_connection',
		'setup_logging',
		'get_config'
]