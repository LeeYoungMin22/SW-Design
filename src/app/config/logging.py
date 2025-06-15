# app/config/logging.py
"""
FOODI 프로젝트 로깅 설정
애플리케이션 전체의 로깅 정책을 관리
"""

import logging
import logging.handlers
import os
from datetime import datetime

def setup_logging(app):
		"""
		Flask 애플리케이션의 로깅을 설정하는 함수
		
		Args:
				app: Flask 애플리케이션 인스턴스
		"""
		
		# 로그 디렉토리 생성
		log_dir = app.config.get('LOG_DIR', 'logs')
		if not os.path.exists(log_dir):
				os.makedirs(log_dir)
		
		# 로그 레벨 설정
		log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper())
		
		# 로그 포맷 설정
		formatter = logging.Formatter(
				'[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
		)
		
		# 파일 핸들러 설정 (일반 로그)
		file_handler = logging.handlers.RotatingFileHandler(
				filename=os.path.join(log_dir, 'foodi.log'),
				maxBytes=10 * 1024 * 1024,  # 10MB
				backupCount=5
		)
		file_handler.setFormatter(formatter)
		file_handler.setLevel(log_level)
		
		# 에러 파일 핸들러 설정
		error_file_handler = logging.handlers.RotatingFileHandler(
				filename=os.path.join(log_dir, 'foodi_error.log'),
				maxBytes=10 * 1024 * 1024,  # 10MB
				backupCount=5
		)
		error_file_handler.setFormatter(formatter)
		error_file_handler.setLevel(logging.ERROR)
		
		# 콘솔 핸들러 설정 (개발 환경용)
		if app.config.get('DEBUG', False):
				console_handler = logging.StreamHandler()
				console_handler.setFormatter(formatter)
				console_handler.setLevel(logging.DEBUG)
				app.logger.addHandler(console_handler)
		
		# Flask 앱 로거에 핸들러 추가
		app.logger.addHandler(file_handler)
		app.logger.addHandler(error_file_handler)
		app.logger.setLevel(log_level)
		
		# 다른 모듈의 로거 설정
		for module_name in ['app.services', 'app.api', 'app.utils']:
				module_logger = logging.getLogger(module_name)
				module_logger.addHandler(file_handler)
				module_logger.addHandler(error_file_handler)
				module_logger.setLevel(log_level)
				
				if app.config.get('DEBUG', False):
						module_logger.addHandler(console_handler)
		
		# 외부 라이브러리 로깅 레벨 조정
		logging.getLogger('requests').setLevel(logging.WARNING)
		logging.getLogger('urllib3').setLevel(logging.WARNING)
		
		app.logger.info(f"로깅 시스템이 초기화되었습니다. 로그 레벨: {logging.getLevelName(log_level)}")

def get_logger(name):
		"""
		모듈별 로거를 반환하는 헬퍼 함수
		
		Args:
				name (str): 로거 이름 (보통 __name__ 사용)
		
		Returns:
				logging.Logger: 설정된 로거 인스턴스
		"""
		return logging.getLogger(name)

def log_api_request(func):
		"""
		API 요청을 로깅하는 데코레이터
		
		Args:
				func: 로깅할 API 함수
		
		Returns:
				wrapper: 래핑된 함수
		"""
		def wrapper(*args, **kwargs):
				logger = get_logger(func.__module__)
				
				# 요청 시작 로그
				logger.info(f"API 요청 시작: {func.__name__}")
				start_time = datetime.now()
				
				try:
						# 실제 함수 실행
						result = func(*args, **kwargs)
						
						# 성공 로그
						duration = (datetime.now() - start_time).total_seconds()
						logger.info(f"API 요청 완료: {func.__name__} (소요시간: {duration:.2f}초)")
						
						return result
						
				except Exception as e:
						# 에러 로그
						duration = (datetime.now() - start_time).total_seconds()
						logger.error(f"API 요청 실패: {func.__name__} - {str(e)} (소요시간: {duration:.2f}초)")
						raise
		
		return wrapper