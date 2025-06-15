# app/config/settings.py
import os
from pathlib import Path
from datetime import timedelta

# 현재 파일의 절대 경로를 기준으로 프로젝트 루트 찾기
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 데이터베이스 디렉토리 절대 경로
DATABASE_DIR = BASE_DIR / 'data' / 'database'
UPLOAD_DIR = BASE_DIR / 'uploads'
LOGS_DIR = BASE_DIR / 'logs'

# 필요한 디렉토리들 생성
for directory in [DATABASE_DIR, UPLOAD_DIR, LOGS_DIR]:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ 디렉토리 확인/생성: {directory}")
    except Exception as e:
        print(f"❌ 디렉토리 생성 실패: {directory} - {e}")

class Config:
    """기본 설정 클래스"""
    
    # Flask 기본 설정
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456'
    FLASK_ENV = os.environ.get('FLASK_ENV') or 'development'
    DEBUG = False
    TESTING = False
    
    # 데이터베이스 설정
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_DIR}/foodi.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {
            'check_same_thread': False,
            'timeout': 10
        }
    }
    
    # API 키 설정
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or 'your-openai-api-key-here'
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY') or 'your-google-maps-api-key-here'
    
    # OpenAI 모델 설정
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL') or 'gpt-3.5-turbo'
    OPENAI_TEMPERATURE = float(os.environ.get('OPENAI_TEMPERATURE', '0.7'))
    OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS', '1000'))
    OPENAI_TIMEOUT = int(os.environ.get('OPENAI_TIMEOUT', '30'))
    
    # 채팅 시스템 설정
    MAX_CONVERSATION_HISTORY = int(os.environ.get('MAX_CONVERSATION_HISTORY', '10'))
    DEFAULT_RESPONSE_LANGUAGE = os.environ.get('DEFAULT_RESPONSE_LANGUAGE', 'ko')
    CHAT_TIMEOUT_SECONDS = int(os.environ.get('CHAT_TIMEOUT_SECONDS', '30'))
    
    # 추천 시스템 설정
    MAX_RECOMMENDATIONS = int(os.environ.get('MAX_RECOMMENDATIONS', '5'))
    RECOMMENDATION_RADIUS_KM = float(os.environ.get('RECOMMENDATION_RADIUS_KM', '5.0'))
    MIN_RATING_FOR_RECOMMENDATION = float(os.environ.get('MIN_RATING_FOR_RECOMMENDATION', '3.0'))
    
    # 리뷰 설정
    MIN_REVIEW_LENGTH = int(os.environ.get('MIN_REVIEW_LENGTH', '10'))
    MAX_REVIEW_LENGTH = int(os.environ.get('MAX_REVIEW_LENGTH', '1000'))
    ALLOW_ANONYMOUS_REVIEWS = os.environ.get('ALLOW_ANONYMOUS_REVIEWS', 'false').lower() == 'true'
    
    # 사용자 설정
    DEFAULT_USER_LOCATION = os.environ.get('DEFAULT_USER_LOCATION', '대구 달서구')
    DEFAULT_LOCATION = os.environ.get('DEFAULT_LOCATION', '대구 달서구')  # 별칭
    USER_SESSION_LIFETIME_DAYS = int(os.environ.get('USER_SESSION_LIFETIME_DAYS', '30'))
    
    # 위치 관련 설정
    DEFAULT_LATITUDE = float(os.environ.get('DEFAULT_LATITUDE', '35.8714'))
    DEFAULT_LONGITUDE = float(os.environ.get('DEFAULT_LONGITUDE', '128.6014'))
    DEFAULT_SEARCH_RADIUS = float(os.environ.get('DEFAULT_SEARCH_RADIUS', '5.0'))
    
    # 언어 및 지역 설정
    DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE', 'ko')
    DEFAULT_TIMEZONE = os.environ.get('DEFAULT_TIMEZONE', 'Asia/Seoul')
    DEFAULT_CURRENCY = os.environ.get('DEFAULT_CURRENCY', 'KRW')
    
    # 파일 업로드 설정
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', '16777216'))  # 16MB
    UPLOAD_FOLDER = str(UPLOAD_DIR)
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', '5'))
    
    # 세션 설정
    SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', '30'))
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # 개발 환경에서는 False
    
    # 보안 설정
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1시간
    BCRYPT_LOG_ROUNDS = 12
    
    # 페이지네이션 설정
    DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE', '10'))
    MAX_PAGE_SIZE = int(os.environ.get('MAX_PAGE_SIZE', '100'))
    
    # API 제한 설정
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100 per hour')
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    
    # 지도 설정
    DEFAULT_MAP_ZOOM = int(os.environ.get('DEFAULT_MAP_ZOOM', '15'))
    MAP_CENTER_LAT = float(os.environ.get('MAP_CENTER_LAT', '35.8714'))  # 대구 위도
    MAP_CENTER_LNG = float(os.environ.get('MAP_CENTER_LNG', '128.6014'))  # 대구 경도
    
    # 캐시 설정
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', '300'))  # 5분
    
    # 로깅 설정
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = str(LOGS_DIR / 'foodi.log')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', '5'))
    
    # 이메일 설정 (알림용)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # 데이터베이스 백업 설정
    BACKUP_ENABLED = os.environ.get('BACKUP_ENABLED', 'true').lower() == 'true'
    BACKUP_INTERVAL_HOURS = int(os.environ.get('BACKUP_INTERVAL_HOURS', '24'))
    MAX_BACKUP_FILES = int(os.environ.get('MAX_BACKUP_FILES', '7'))
    BACKUP_DIR = BASE_DIR / 'backups'
    
    # 성능 모니터링 설정
    ENABLE_PROFILING = os.environ.get('ENABLE_PROFILING', 'false').lower() == 'true'
    SLOW_QUERY_THRESHOLD = float(os.environ.get('SLOW_QUERY_THRESHOLD', '2.0'))
    
    # 외부 서비스 설정
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
    
    # CORS 설정
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')
    
    # 애플리케이션 특화 설정
    APP_NAME = 'FOODI'
    APP_VERSION = '1.0.0'
    APP_DESCRIPTION = 'AI 기반 맛집 추천 챗봇'
    
    # 추가적인 설정들 (자주 사용되는 것들)
    DEFAULT_PAGE = int(os.environ.get('DEFAULT_PAGE', '1'))
    DEFAULT_PER_PAGE = int(os.environ.get('DEFAULT_PER_PAGE', '10'))
    MAX_SEARCH_RESULTS = int(os.environ.get('MAX_SEARCH_RESULTS', '50'))
    
    # 이미지 및 미디어 설정
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_IMAGE_SIZE = int(os.environ.get('MAX_IMAGE_SIZE', '5242880'))  # 5MB
    IMAGE_UPLOAD_PATH = 'uploads/images'
    
    # 데이터 검증 설정
    MIN_PASSWORD_LENGTH = int(os.environ.get('MIN_PASSWORD_LENGTH', '8'))
    MAX_USERNAME_LENGTH = int(os.environ.get('MAX_USERNAME_LENGTH', '50'))
    MIN_USERNAME_LENGTH = int(os.environ.get('MIN_USERNAME_LENGTH', '3'))
    
    # 알림 설정
    ENABLE_EMAIL_NOTIFICATIONS = os.environ.get('ENABLE_EMAIL_NOTIFICATIONS', 'false').lower() == 'true'
    ENABLE_PUSH_NOTIFICATIONS = os.environ.get('ENABLE_PUSH_NOTIFICATIONS', 'false').lower() == 'true'
    
    # 시스템 설정
    MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', 'false').lower() == 'true'
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@foodi.com')
    SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'support@foodi.com')
    
    # 외부 API 설정
    WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY')
    PAYMENT_API_KEY = os.environ.get('PAYMENT_API_KEY')
    SMS_API_KEY = os.environ.get('SMS_API_KEY')
    
    # 소셜 로그인 설정
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    NAVER_CLIENT_ID = os.environ.get('NAVER_CLIENT_ID')
    NAVER_CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET')
    KAKAO_CLIENT_ID = os.environ.get('KAKAO_CLIENT_ID')
    KAKAO_CLIENT_SECRET = os.environ.get('KAKAO_CLIENT_SECRET')
    
    # 데이터 처리 설정
    BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '100'))
    QUEUE_TIMEOUT = int(os.environ.get('QUEUE_TIMEOUT', '300'))
    MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '3'))
    
    # 디버그 및 개발 설정
    ENABLE_DEBUG_TOOLBAR = os.environ.get('ENABLE_DEBUG_TOOLBAR', 'false').lower() == 'true'
    ENABLE_SQL_LOGGING = os.environ.get('ENABLE_SQL_LOGGING', 'false').lower() == 'true'
    PROFILE_SLOW_QUERIES = os.environ.get('PROFILE_SLOW_QUERIES', 'false').lower() == 'true'
    
    # 기본 음식 카테고리
    DEFAULT_FOOD_CATEGORIES = [
        '한식', '중식', '일식', '양식', '치킨', '피자', '햄버거', 
        '분식', '카페', '디저트', '술집', '베이커리', '패스트푸드', '기타'
    ]
    
    # 기본 분위기 태그
    DEFAULT_ATMOSPHERE_TAGS = [
        '캐주얼', '격식있는', '로맨틱', '가족친화적', '비즈니스', '조용한', '활기찬',
        '전통적인', '모던한', '아늑한', '럭셔리', '서민적인'
    ]
    
    @staticmethod
    def init_app(app):
        """애플리케이션 초기화 시 호출되는 메소드"""
        # 백업 디렉토리 생성
        if Config.BACKUP_ENABLED:
            Config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_setting(cls, name, default=None):
        """
        설정 값을 안전하게 가져오는 메소드
        누락된 설정에 대한 기본값 제공
        """
        return getattr(cls, name, default)
    
    @classmethod
    def has_setting(cls, name):
        """설정이 존재하는지 확인하는 메소드"""
        return hasattr(cls, name)
    
    @classmethod
    def set_default_if_missing(cls, name, default_value):
        """설정이 누락된 경우 기본값으로 설정하는 메소드"""
        if not hasattr(cls, name):
            setattr(cls, name, default_value)
            print(f"⚠️  누락된 설정 '{name}'에 기본값 설정: {default_value}")
    
    @classmethod
    def setup_defaults(cls):
        """누락될 수 있는 모든 설정에 대한 기본값 설정"""
        default_settings = {
            # 기본 위치 관련
            'DEFAULT_LOCATION': '대구 달서구',
            'DEFAULT_LATITUDE': 35.8714,
            'DEFAULT_LONGITUDE': 128.6014,
            'DEFAULT_RADIUS': 5.0,
            
            # OpenAI 관련
            'OPENAI_MODEL': 'gpt-3.5-turbo',
            'OPENAI_TEMPERATURE': 0.7,
            'OPENAI_MAX_TOKENS': 1000,
            'OPENAI_TIMEOUT': 30,
            
            # 사용자 관련
            'DEFAULT_USER_LOCATION': '대구 달서구',
            'MAX_USERS': 10000,
            'USER_REGISTRATION_ENABLED': True,
            
            # 식당 관련
            'MAX_RESTAURANTS': 100000,
            'DEFAULT_CUISINE_TYPE': '한식',
            'MAX_RESTAURANT_IMAGES': 10,
            
            # 리뷰 관련
            'MAX_REVIEWS_PER_USER': 1000,
            'MIN_REVIEW_RATING': 1.0,
            'MAX_REVIEW_RATING': 5.0,
            
            # 추천 관련
            'MAX_RECOMMENDATIONS_PER_USER': 50,
            'RECOMMENDATION_CACHE_TIMEOUT': 3600,
            'MIN_RESTAURANTS_FOR_RECOMMENDATION': 3,
            
            # 검색 관련
            'DEFAULT_SEARCH_LIMIT': 20,
            'MAX_SEARCH_RADIUS': 50.0,
            'SEARCH_CACHE_TIMEOUT': 300,
            
            # 파일 관련
            'UPLOAD_FOLDER': 'uploads',
            'MAX_FILE_SIZE': 5242880,  # 5MB
            'ALLOWED_EXTENSIONS': ['jpg', 'jpeg', 'png', 'gif'],
            
            # 시스템 관련
            'TIMEZONE': 'Asia/Seoul',
            'LANGUAGE': 'ko',
            'CURRENCY': 'KRW',
            'DATE_FORMAT': '%Y-%m-%d',
            'TIME_FORMAT': '%H:%M:%S',
            
            # API 관련
            'API_VERSION': 'v1',
            'API_TIMEOUT': 30,
            'API_RATE_LIMIT': 100,
            
            # 보안 관련
            'PASSWORD_MIN_LENGTH': 8,
            'SESSION_TIMEOUT': 3600,
            'CSRF_TOKEN_TIMEOUT': 3600,
            
            # 로깅 관련
            'LOG_LEVEL': 'INFO',
            'LOG_MAX_SIZE': 10485760,  # 10MB
            'LOG_BACKUP_COUNT': 5,
            
            # 캐시 관련
            'CACHE_TYPE': 'SimpleCache',
            'CACHE_TIMEOUT': 300,
            'CACHE_KEY_PREFIX': 'foodi_',
            
            # 이메일 관련
            'MAIL_ENABLED': False,
            'MAIL_TIMEOUT': 30,
            'MAIL_USE_SSL': False,
            
            # 기타
            'MAINTENANCE_MODE': False,
            'DEBUG_MODE': False,
            'TESTING_MODE': False,
        }
        
        for setting_name, default_value in default_settings.items():
            cls.set_default_if_missing(setting_name, default_value)
    
    @classmethod
    def initialize(cls):
        """설정 클래스 초기화 - 모든 기본값 설정 및 검증"""
        print("🔧 설정 초기화를 시작합니다...")
        cls.setup_defaults()
        cls.validate_required_settings()
        print("✅ 설정 초기화가 완료되었습니다.")

class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True
    FLASK_ENV = 'development'
    
    # 개발용 데이터베이스
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_DIR}/foodi_dev.db'
    
    # 개발용 로깅
    LOG_LEVEL = 'DEBUG'
    
    # 개발용 보안 설정 (느슨함)
    WTF_CSRF_ENABLED = False  # 개발 편의를 위해 비활성화
    SESSION_COOKIE_SECURE = False
    
    # 개발용 OpenAI 설정
    OPENAI_TEMPERATURE = 0.9  # 더 창의적인 응답
    
    # 개발용 캐시 설정
    CACHE_TYPE = 'NullCache'  # 캐시 비활성화로 개발 편의성 증대

class ProductionConfig(Config):
    """운영 환경 설정"""
    DEBUG = False
    FLASK_ENV = 'production'
    
    # 운영용 데이터베이스
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{DATABASE_DIR}/foodi_prod.db'
    
    # 운영용 보안 설정 (강화)
    SECRET_KEY = os.environ.get('SECRET_KEY')  # 반드시 환경 변수에서 가져와야 함
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True
    
    # 운영용 로깅
    LOG_LEVEL = 'WARNING'
    
    # 운영용 OpenAI 설정
    OPENAI_TEMPERATURE = 0.5  # 더 일관된 응답
    
    # 운영용 캐시 설정
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # 운영 환경 전용 설정
        import logging
        from logging.handlers import SMTPHandler, RotatingFileHandler
        
        # 에러 로그 이메일 전송
        if app.config.get('MAIL_SERVER'):
            auth = None
            if app.config.get('MAIL_USERNAME') or app.config.get('MAIL_PASSWORD'):
                auth = (app.config.get('MAIL_USERNAME'),
                       app.config.get('MAIL_PASSWORD'))
            secure = None
            if app.config.get('MAIL_USE_TLS'):
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config.get('MAIL_SERVER'), app.config.get('MAIL_PORT')),
                fromaddr=app.config.get('MAIL_DEFAULT_SENDER'),
                toaddrs=['admin@foodi.com'],
                subject='FOODI Application Error',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)
        
        # 파일 로깅
        if not os.path.exists(Config.LOGS_DIR):
            os.makedirs(Config.LOGS_DIR)
        file_handler = RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('FOODI production startup')

class TestingConfig(Config):
    """테스트 환경 설정"""
    TESTING = True
    FLASK_ENV = 'testing'
    
    # 테스트용 메모리 데이터베이스
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # 테스트용 설정
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'
    
    # 테스트용 OpenAI 설정 (모의)
    OPENAI_API_KEY = 'test-api-key'
    OPENAI_MODEL = 'gpt-3.5-turbo'
    
    # 테스트용 캐시 설정
    CACHE_TYPE = 'NullCache'
    
    # 테스트용 파일 설정
    MAX_CONTENT_LENGTH = 1024 * 1024  # 1MB

# 환경별 설정 매핑
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """환경에 따른 설정 클래스를 반환하는 함수"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    return config.get(config_name, DevelopmentConfig)

# 디버그 정보 출력 (개발 환경에서만)
if __name__ == '__main__':
    print(f"🔧 FOODI Configuration Debug Info")
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"DATABASE_DIR: {DATABASE_DIR}")
    print(f"UPLOAD_DIR: {UPLOAD_DIR}")
    print(f"LOGS_DIR: {LOGS_DIR}")
    
    dev_config = DevelopmentConfig()
    print(f"Development DB URI: {dev_config.SQLALCHEMY_DATABASE_URI}")
    print(f"OpenAI Model: {dev_config.OPENAI_MODEL}")
    print(f"디렉토리 존재 여부:")
    print(f"  - DATABASE_DIR: {DATABASE_DIR.exists()}")
    print(f"  - UPLOAD_DIR: {UPLOAD_DIR.exists()}")
    print(f"  - LOGS_DIR: {LOGS_DIR.exists()}")
    
    if DATABASE_DIR.exists():
        print(f"  - DATABASE_DIR 쓰기 권한: {os.access(DATABASE_DIR, os.W_OK)}")