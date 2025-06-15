# -*- coding: utf-8 -*-
"""
FOODI 메인 라우트
웹 페이지 및 기본 API 엔드포인트를 정의합니다.
"""

from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.session_manager import SessionManager
from datetime import datetime
import os
from app import db
import re
import random
import logging
import uuid 
from app.models.user import User
from app.config.database import db
import traceback
from app.models.review import Review

# OpenAI 서비스 임포트
try:
    from app.services.openai_service import OpenAIService
    openai_service = OpenAIService()
except ImportError as e:
    print(f"OpenAI 서비스 임포트 오류: {e}")
    openai_service = None

logger = logging.getLogger(__name__)

# Blueprint 정의
main_bp = Blueprint('main', __name__)

# SessionManager 인스턴스 (전역으로 관리하거나 앱에서 주입받음)
session_manager = None

def get_session_manager():
    """SessionManager 인스턴스를 가져옵니다"""
    global session_manager
    try:
        if session_manager is None:
            from app.utils.session_manager import SessionManager
            session_manager = SessionManager(
                session_timeout=3600,
                max_sessions=1000,
                cleanup_interval=300
            )
            logger.info("SessionManager 초기화 완료")
        return session_manager
    except ImportError as e:
        logger.warning(f"SessionManager 모듈을 찾을 수 없음: {e}")
        return None
    except Exception as e:
        logger.error(f"SessionManager 초기화 오류: {e}")
        return None

# 메인 블루프린트 생성
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """메인 페이지"""

    # SessionManager 인스턴스 가져오기
    sm = get_session_manager()
    
    # Flask session에서 session_id 가져오기
    session_id = session.get('session_id')
    
    # session_id가 없으면 로그인되지 않은 상태
    if not session_id:
        flash('로그인이 필요합니다.', 'warning')
        return redirect(url_for('auth.login'))
    
    # SessionManager에서 세션 데이터 조회
    session_data = sm.get_session(session_id)

    try:
        # 통계 데이터 조회
        from app.models.restaurant import Restaurant
        from app.models.user import User
        from app.models.review import Review
        from app.models.recommendation import Recommendation
        
        stats = {
            'restaurants': Restaurant.query.count(),
            'users': User.query.count(),
            'reviews': Review.query.count(),
            'recommendations': Recommendation.query.count()
        }
        
        return render_template('index.html', stats=stats)
        
    except Exception as e:
        # 모델이 없거나 DB 연결 실패 시 기본값
        stats = {
            'restaurants': 0,
            'users': 0,
            'reviews': 0,
            'recommendations': 0
        }
        
        return render_template('index.html', stats=stats)

# SessionManager 및 모델 임포트
try:
    from app.models.user import User
    from app.config.database import db
    from app.utils.session_manager import SessionManager
except ImportError as e:
    print(f"모델 또는 SessionManager 임포트 오류: {e}")
    User = None
    db = None
    SessionManager = None

# 로깅 설정
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# 전역 SessionManager 인스턴스 (싱글톤 패턴)
session_manager = None

def get_session_manager():
    """SessionManager 인스턴스를 가져옵니다 (싱글톤)"""
    global session_manager
    if session_manager is None and SessionManager:
        session_manager = SessionManager(
            session_timeout=3600,  # 1시간
            max_sessions=1000,
            cleanup_interval=300   # 5분
        )
        logger.info("SessionManager 초기화 완료")
    return session_manager

def validate_email(email):
    """이메일 형식 검증"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """비밀번호 강도 검증"""
    if len(password) < 8:
        return False, "비밀번호는 최소 8자 이상이어야 합니다."
    if not re.search(r'[A-Za-z]', password):
        return False, "비밀번호는 영문자를 포함해야 합니다."
    if not re.search(r'[0-9]', password):
        return False, "비밀번호는 숫자를 포함해야 합니다."
    return True, "유효한 비밀번호입니다."

def create_session_id(user_id: int) -> str:
    """고유한 세션 ID 생성"""
    timestamp = int(datetime.utcnow().timestamp())
    unique_id = str(uuid.uuid4()).replace('-', '')[:8]
    return f"foodi_session_{user_id}_{timestamp}_{unique_id}"


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """회원가입 처리"""
    if request.method == 'POST':
        try:
            # 폼 데이터 수집
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            location = request.form.get('location', '대구 달서구').strip()
            preferred_radius = request.form.get('preferred_radius', 5, type=int)
            
            # === 입력 데이터 검증 ===
            if not username or not email or not password:
                flash('모든 필수 필드를 입력해주세요.', 'error')
                return render_template('auth/register.html')
            
            # 사용자명 길이 검증
            if len(username) < 3 or len(username) > 50:
                flash('사용자명은 3-50자 사이여야 합니다.', 'error')
                return render_template('auth/register.html')
            
            # 이메일 형식 검증
            if not validate_email(email):
                flash('올바른 이메일 형식을 입력해주세요.', 'error')
                return render_template('auth/register.html')
            
            # 비밀번호 강도 검증
            is_valid, message = validate_password(password)
            if not is_valid:
                flash(message, 'error')
                return render_template('auth/register.html')
            
            if not User or not db:
                flash('시스템 오류: 데이터베이스를 사용할 수 없습니다.', 'error')
                return render_template('auth/register.html')
            
            # === 중복 검사 ===
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('이미 사용 중인 사용자명입니다.', 'error')
                return render_template('auth/register.html')
            
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                flash('이미 사용 중인 이메일입니다.', 'error')
                return render_template('auth/register.html')
            
            # === 새 사용자 생성 ===
            password_hash = generate_password_hash(password)
            
            # User 모델의 생성자 활용
            new_user = User(
                username=username,
                email=email,
                password=password,  # ✅ 필수 인자로 전달
                location=location,
                preferred_radius=preferred_radius
            )
            
            
            # 기본 선호도 설정
            new_user.food_preferences = {
                'favorite_cuisines': [],
                'spice_level': 'medium',
                'price_sensitivity': 'medium',
                'atmosphere_preference': 'casual'
            }
            
            new_user.dietary_restrictions = []
            new_user.budget_range = '20000-30000'
            new_user.is_active = True
            
            # 데이터베이스에 저장
            db.session.add(new_user)
            db.session.commit()
            
            logger.info(f"새 사용자 등록: {username} (ID: {new_user.id})")
            flash(f'회원가입이 완료되었습니다, {username}님! 로그인해주세요.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            if db:
                db.session.rollback()
            logger.error(f"회원가입 오류: {e}")
            flash(f'회원가입 중 오류가 발생했습니다: {str(e)}', 'error')
            return render_template('auth/register.html')
    
    # GET 요청 시 회원가입 페이지 표시
    return render_template('auth/register.html')

@auth_bp.route('/loginpage', methods=['GET', 'POST'])
def loginpage():
    """로그인 페이지 및 로그인 처리"""
    
    if request.method == 'GET':
        # GET 요청 시 로그인 페이지 렌더링
        return render_template('login.html')
    
    elif request.method == 'POST':
        # POST 요청 시 로그인 처리
        username = request.form.get('username')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me')
        
        # 입력값 검증
        if not username or not password:
            flash('사용자명과 비밀번호를 모두 입력해주세요.', 'error')
            return render_template('login.html')
        
        # 데이터베이스에서 사용자 조회
        user = User.query.filter_by(username=username).first()
        
        # 사용자 존재 여부 및 비밀번호 확인
        if user and check_password_hash(user.password, password):
            # 로그인 성공
            session['user_id'] = user.id
            session['username'] = user.username
            
            # remember_me 처리
            if remember_me:
                session.permanent = True
            
            flash('로그인에 성공했습니다!', 'success')
            
            # 로그인 후 리다이렉트할 페이지 (예: 대시보드)
            return redirect(url_for('main.dashboard'))  # 또는 원하는 페이지
            
        else:
            # 로그인 실패
            flash('사용자명 또는 비밀번호가 올바르지 않습니다.', 'error')
            return render_template('login.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 처리 (SessionManager 통합)"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            remember_me = request.form.get('remember_me', False)
            
            if not username or not password:
                flash('사용자명과 비밀번호를 입력해주세요.', 'error')
                return render_template('auth/login.html')
            
            if not User or not db:
                flash('시스템 오류: 데이터베이스를 사용할 수 없습니다.', 'error')
                return render_template('auth/login.html')
            
            # 사용자 찾기
            user = User.query.filter(
                (User.username == username) | (User.email == username)
            ).first()
            
            if user and hasattr(user, 'password_hash') and check_password_hash(user.password_hash, password):
                if not user.is_active:
                    flash('비활성화된 계정입니다. 관리자에게 문의하세요.', 'error')
                    return render_template('auth/login.html')
                
                # === SessionManager를 사용한 세션 생성 ===
                sm = get_session_manager()
                if sm:
                    # 고유한 세션 ID 생성
                    session_id = create_session_id(user.id)
                    
                    # 세션 초기 데이터 준비
                    session_data = {
                        'user_id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'location': user.location,
                        'login_time': datetime.utcnow().isoformat(),
                        'ip_address': request.remote_addr,
                        'user_agent': request.headers.get('User-Agent', ''),
                        'login_method': 'web',
                        'preferences': user.food_preferences or {},
                        'dietary_restrictions': user.dietary_restrictions or [],
                        'budget_range': user.budget_range,
                        'preferred_radius': user.preferred_radius
                    }
                    
                    # SessionManager에 세션 생성
                    if sm.create_session(session_id, session_data):
                        # Flask 세션에 기본 정보만 저장
                        session['session_id'] = session_id
                        session['user_id'] = user.id
                        session['username'] = user.username
                        session['is_authenticated'] = True
                        
                        # User 모델의 세션 정보도 업데이트 (호환성 유지)
                        user.update_session(session_id, {
                            'managed_by': 'SessionManager',
                            'flask_session_id': session.get('_permanent_id')
                        })
                        
                        logger.info(f"사용자 로그인: {username} (세션: {session_id})")
                        flash(f'환영합니다, {user.username}님!', 'success')
                        
                        # 이전 페이지로 리다이렉트 또는 메인 페이지로
                        next_page = request.args.get('next')
                        if next_page:
                            return redirect(next_page)
                        return redirect(url_for('main.index'))
                    else:
                        flash('세션 생성에 실패했습니다. 다시 시도해주세요.', 'error')
                else:
                    # SessionManager가 없는 경우 기본 세션 처리
                    session['user_id'] = user.id
                    session['username'] = user.username
                    session['is_authenticated'] = True
                    
                    # User 모델 세션 업데이트
                    session_id = f"fallback_session_{user.id}_{int(datetime.utcnow().timestamp())}"
                    user.update_session(session_id, {'login_method': 'web_fallback'})
                    
                    flash(f'환영합니다, {user.username}님!', 'success')
                    return redirect(url_for('main.index'))
            else:
                flash('잘못된 사용자명 또는 비밀번호입니다.', 'error')
                
        except Exception as e:
            logger.error(f"로그인 오류: {e}")
            flash(f'로그인 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """로그아웃 처리 (SessionManager 통합)"""
    try:
        session_id = session.get('session_id')
        user_id = session.get('user_id')
        username = session.get('username', '사용자')
        
        # SessionManager에서 세션 삭제
        sm = get_session_manager()
        if sm and session_id:
            if sm.delete_session(session_id):
                logger.info(f"SessionManager에서 세션 삭제: {session_id}")
            else:
                logger.warning(f"SessionManager 세션 삭제 실패: {session_id}")
        
        # User 모델의 세션 정보도 클리어
        if user_id and User and db:
            user = User.query.get(user_id)
            if user:
                user.current_session_id = None
                db.session.commit()
                logger.info(f"사용자 세션 정보 클리어: {username}")
        
        # Flask 세션 클리어
        session.clear()
        
        flash(f'{username}님, 성공적으로 로그아웃되었습니다.', 'info')
        
    except Exception as e:
        logger.error(f"로그아웃 오류: {e}")
        session.clear()  # 오류가 있어도 세션은 클리어
        flash('로그아웃 처리 중 오류가 발생했지만 로그아웃되었습니다.', 'warning')
    
    return redirect(url_for('main.index'))

@auth_bp.route('/profile')
def profile():
    """사용자 프로필 페이지 (SessionManager 연동)"""
    if not session.get('is_authenticated'):
        flash('로그인이 필요합니다.', 'warning')
        return redirect(url_for('auth.login'))
    
    try:
        session_id = session.get('session_id')
        user_id = session.get('user_id')
        
        # SessionManager에서 세션 정보 조회
        sm = get_session_manager()
        session_data = None
        if sm and session_id:
            session_data = sm.get_session(session_id)
            if not session_data:
                flash('세션이 만료되었습니다. 다시 로그인해주세요.', 'warning')
                return redirect(url_for('auth.login'))
        
        # User 모델에서 사용자 정보 조회
        if not User or not db:
            flash('시스템 오류: 사용자 정보를 불러올 수 없습니다.', 'error')
            return redirect(url_for('main.index'))
        
        user = User.query.get(user_id)
        if not user:
            flash('사용자를 찾을 수 없습니다.', 'error')
            session.clear()
            return redirect(url_for('auth.login'))
        
        # User 모델의 메서드들 활용
        satisfaction_score = user.calculate_satisfaction_score()
        dietary_restrictions = user.get_dietary_restrictions_text()
        recent_recommendations = user.get_recommendation_history(5)
        
        # SessionManager에서 채팅 히스토리 조회
        conversation_history = []
        if sm and session_id:
            conversation_history = sm.get_conversation_history(session_id, limit=10)
        
        # 프로필 데이터 구성
        profile_data = {
            'user': user,
            'satisfaction_score': satisfaction_score,
            'dietary_restrictions': dietary_restrictions,
            'recent_recommendations': recent_recommendations,
            'conversation_history': conversation_history,
            'total_reviews': user.reviews.count(),
            'total_recommendations': user.recommendations.count(),
            'member_since': user.created_at.strftime('%Y년 %m월') if user.created_at else '알 수 없음',
            'session_expired': user.is_session_expired(),
            'current_session_data': session_data
        }
        
        return render_template('auth/profile.html', **profile_data)
        
    except Exception as e:
        logger.error(f"프로필 로딩 오류: {e}")
        flash(f'프로필 로딩 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('main.index'))

@auth_bp.route('/session/info')
def session_info():
    """현재 세션 정보 조회 (디버깅/관리용)"""
    if not session.get('is_authenticated'):
        return jsonify({'error': '로그인이 필요합니다'}), 401
    
    try:
        session_id = session.get('session_id')
        sm = get_session_manager()
        
        if not sm or not session_id:
            return jsonify({'error': 'SessionManager를 사용할 수 없습니다'}), 500
        
        # 세션 정보 조회
        session_data = sm.get_session(session_id)
        if not session_data:
            return jsonify({'error': '세션을 찾을 수 없습니다'}), 404
        
        # 민감한 정보 제거
        safe_session_data = session_data.copy()
        safe_session_data.pop('password_hash', None)
        safe_session_data.pop('user_agent', None)
        
        return jsonify({
            'success': True,
            'session_data': safe_session_data,
            'flask_session': {
                'session_id': session_id,
                'user_id': session.get('user_id'),
                'username': session.get('username')
            }
        })
        
    except Exception as e:
        logger.error(f"세션 정보 조회 오류: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/chat/add-message', methods=['POST'])
def add_chat_message():
    """채팅 메시지를 세션에 추가 (SessionManager 활용)"""
    if not session.get('is_authenticated'):
        return jsonify({'error': '로그인이 필요합니다'}), 401
    
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        role = data.get('role', 'user')  # 'user' 또는 'assistant'
        
        if not message:
            return jsonify({'error': '메시지를 입력해주세요'}), 400
        
        session_id = session.get('session_id')
        sm = get_session_manager()
        
        if not sm or not session_id:
            return jsonify({'error': 'SessionManager를 사용할 수 없습니다'}), 500
        
        # 메시지 메타데이터
        metadata = {
            'ip_address': request.remote_addr,
            'timestamp': datetime.utcnow().isoformat(),
            'message_id': str(uuid.uuid4())
        }
        
        # SessionManager에 메시지 추가
        success = sm.add_message_to_session(session_id, role, message, metadata)
        
        if success:
            return jsonify({
                'success': True,
                'message': '메시지가 추가되었습니다',
                'metadata': metadata
            })
        else:
            return jsonify({'error': '메시지 추가에 실패했습니다'}), 500
            
    except Exception as e:
        logger.error(f"채팅 메시지 추가 오류: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/chat/history')
def get_chat_history():
    """채팅 히스토리 조회 (SessionManager 활용)"""
    if not session.get('is_authenticated'):
        return jsonify({'error': '로그인이 필요합니다'}), 401
    
    try:
        session_id = session.get('session_id')
        limit = request.args.get('limit', 20, type=int)
        
        sm = get_session_manager()
        if not sm or not session_id:
            return jsonify({'error': 'SessionManager를 사용할 수 없습니다'}), 500
        
        # 대화 히스토리 조회
        history = sm.get_conversation_history(session_id, limit)
        
        return jsonify({
            'success': True,
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        logger.error(f"채팅 히스토리 조회 오류: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/session/stats')
def session_stats():
    """세션 관리 통계 (관리자용)"""
    if not session.get('is_authenticated'):
        return jsonify({'error': '로그인이 필요합니다'}), 401
    
    try:
        sm = get_session_manager()
        if not sm:
            return jsonify({'error': 'SessionManager를 사용할 수 없습니다'}), 500
        
        stats = sm.get_session_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"세션 통계 조회 오류: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/check-username', methods=['POST'])
def check_username():
    """사용자명 중복 확인 API"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        
        if not username:
            return jsonify({'available': False, 'message': '사용자명을 입력해주세요.'})
        
        if len(username) < 3 or len(username) > 50:
            return jsonify({'available': False, 'message': '사용자명은 3-50자 사이여야 합니다.'})
        
        if not User:
            return jsonify({'available': False, 'message': '시스템 오류'})
        
        existing_user = User.query.filter_by(username=username).first()
        
        if existing_user:
            return jsonify({'available': False, 'message': '이미 사용 중인 사용자명입니다.'})
        else:
            return jsonify({'available': True, 'message': '사용 가능한 사용자명입니다.'})
            
    except Exception as e:
        logger.error(f"사용자명 중복 확인 오류: {e}")
        return jsonify({'available': False, 'message': f'오류가 발생했습니다: {str(e)}'})

@auth_bp.route('/api/check-email', methods=['POST'])
def check_email():
    """이메일 중복 확인 API"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({'available': False, 'message': '이메일을 입력해주세요.'})
        
        if not validate_email(email):
            return jsonify({'available': False, 'message': '올바른 이메일 형식이 아닙니다.'})
        
        if not User:
            return jsonify({'available': False, 'message': '시스템 오류'})
        
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            return jsonify({'available': False, 'message': '이미 사용 중인 이메일입니다.'})
        else:
            return jsonify({'available': True, 'message': '사용 가능한 이메일입니다.'})
            
    except Exception as e:
        logger.error(f"이메일 중복 확인 오류: {e}")
        return jsonify({'available': False, 'message': f'오류가 발생했습니다: {str(e)}'})


def login_required(f):
    """로그인이 필요한 페이지에 사용하는 데코레이터 (SessionManager 검증 포함)"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_authenticated'):
            flash('로그인이 필요합니다.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        # SessionManager로 세션 유효성 추가 검증
        session_id = session.get('session_id')
        sm = get_session_manager()
        
        if sm and session_id:
            session_data = sm.get_session(session_id)
            if not session_data:
                flash('세션이 만료되었습니다. 다시 로그인해주세요.', 'warning')
                session.clear()
                return redirect(url_for('auth.login', next=request.url))
        
        return f(*args, **kwargs)
    return decorated_function

# 컨텍스트 프로세서 (템플릿에서 사용자 정보 접근)
@auth_bp.app_context_processor
def inject_user():
    """템플릿에서 current_user 및 session_info 사용 가능하게 함"""
    if session.get('is_authenticated') and User and db:
        try:
            current_user = User.query.get(session['user_id'])
            
            # SessionManager에서 추가 세션 정보 조회
            session_id = session.get('session_id')
            sm = get_session_manager()
            session_info = None
            
            if sm and session_id:
                session_data = sm.get_session(session_id)
                if session_data:
                    session_info = {
                        'created_at': session_data.get('created_at'),
                        'last_activity': session_data.get('last_activity'),
                        'conversation_count': len(session_data.get('conversation_history', []))
                    }
            
            return {
                'current_user': current_user,
                'session_info': session_info
            }
        except Exception as e:
            logger.error(f"컨텍스트 프로세서 오류: {e}")
    
    return {'current_user': None, 'session_info': None}

# 에러 핸들러
@auth_bp.errorhandler(401)
def unauthorized(error):
    """인증 오류 처리"""
    flash('접근 권한이 없습니다. 로그인해주세요.', 'error')
    return redirect(url_for('auth.login'))

@auth_bp.errorhandler(403)
def forbidden(error):
    """권한 없음 오류 처리"""
    flash('해당 페이지에 접근할 권한이 없습니다.', 'error')
    return redirect(url_for('main.index'))

# SessionManager 초기화 함수 (앱 시작 시 호출)
def init_session_manager():
    """애플리케이션 시작 시 SessionManager 초기화"""
    try:
        sm = get_session_manager()
        if sm:
            logger.info("SessionManager가 성공적으로 초기화되었습니다.")
            return True
        else:
            logger.error("SessionManager 초기화에 실패했습니다.")
            return False
    except Exception as e:
        logger.error(f"SessionManager 초기화 오류: {e}")
        return False

# 애플리케이션 종료 시 정리 함수
def cleanup_session_manager():
    """애플리케이션 종료 시 SessionManager 정리"""
    global session_manager
    try:
        if session_manager:
            # 현재 활성 세션 수 로깅
            stats = session_manager.get_session_stats()
            logger.info(f"SessionManager 종료: 활성 세션 {stats['active_sessions']}개")
            session_manager = None
    except Exception as e:
        logger.error(f"SessionManager 정리 오류: {e}")


@main_bp.route('/chat')
def chat_page():
    """채팅 페이지"""
    try:
        # 채팅 관련 데이터 조회
        chat_data = {
            'user_name': '사용자',
            'ai_name': 'FOODI AI',
            'welcome_message': True,
            'total_restaurants': get_restaurant_count(),
            'categories': get_available_categories(),
            'openai_enabled': openai_service is not None,
            'model_name': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        }
        
        return render_template('chat.html', chat_data=chat_data)
        
    except Exception as e:
        # 오류 발생 시 기본값
        chat_data = {
            'user_name': '사용자',
            'ai_name': 'FOODI AI',
            'welcome_message': True,
            'total_restaurants': 50,
            'categories': ['한식', '중식', '일식', '양식', '카페'],
            'openai_enabled': False,
            'model_name': 'fallback'
        }
        
        return render_template('chat.html', chat_data=chat_data)
      
      
@main_bp.route('/api/chat', methods=['POST'])
def chat_recommendation():
    """AI 맛집 추천 API (OpenAI GPT-3.5-turbo 사용)"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': '메시지를 입력해주세요.'
            })
        
        # OpenAI 서비스가 사용 가능한 경우
        if openai_service:
            result = openai_service.get_restaurant_recommendation(user_message)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'response': result['response'],
                    'restaurants': result['restaurants'],
                    'analysis': result['analysis'],
                    'total_candidates': result.get('total_candidates', 0),
                    'powered_by': f"OpenAI {os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')}"
                })
            else:
                # OpenAI 서비스 오류 시 fallback
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'AI 서비스 오류'),
                    'fallback_response': result.get('response', '죄송합니다. 다시 시도해주세요.')
                })
        
        # OpenAI 서비스가 없는 경우 기본 응답
        else:
            fallback_result = get_fallback_recommendation(user_message)
            return jsonify({
                'success': True,
                'response': fallback_result['response'],
                'restaurants': fallback_result['restaurants'],
                'analysis': fallback_result['analysis'],
                'powered_by': 'Fallback System'
            })
        
    except Exception as e:
        print(f"채팅 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'추천 중 오류가 발생했습니다: {str(e)}',
            'fallback_response': '일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
        })
             
             
def get_fallback_recommendation(user_message: str) -> dict:
    """OpenAI 서비스가 없을 때의 기본 추천 시스템"""
    
    message_lower = user_message.lower()
    
    # 기본 맛집 데이터
    fallback_restaurants = [
        {
            "name": "한우마당",
            "category": "한식",
            "location": "성서동",
            "address": "대구 달서구 성서로 123",
            "phone": "053-123-4567",
            "rating": 4.2,
            "review_count": 128,
            "price_range": "중간",
            "specialties": ["갈비탕", "불고기", "된장찌개"],
            "description": "고품질 한우와 깔끔한 분위기의 한식당입니다.",
            "business_hours": "11:00-22:00",
            "parking": True,
            "room_available": True
        },
        {
            "name": "파스타팩토리",
            "category": "양식",
            "location": "본리동",
            "address": "대구 달서구 본리로 654",
            "phone": "053-567-8901",
            "rating": 4.4,
            "review_count": 92,
            "price_range": "중간",
            "specialties": ["파스타", "리조또", "스테이크"],
            "description": "정통 이탈리안 파스타와 로맨틱한 분위기가 매력적인 곳입니다.",
            "business_hours": "11:00-22:00",
            "parking": True,
            "room_available": False
        },
        {
            "name": "원두마을",
            "category": "카페",
            "location": "죽전동",
            "address": "대구 달서구 죽전로 987",
            "phone": "053-678-9012",
            "rating": 4.3,
            "review_count": 205,
            "price_range": "저렴",
            "specialties": ["아메리카노", "라떼", "디저트"],
            "description": "넓은 공간과 좋은 커피, 작업하기에도 완벽한 카페입니다.",
            "business_hours": "07:00-23:00",
            "parking": True,
            "room_available": False
        }
    ]
    
    # 간단한 키워드 매칭
    selected_restaurants = []
    response_message = ""
    
    if any(word in message_lower for word in ['가족', '모임', '한식']):
        selected_restaurants = [fallback_restaurants[0]]
        response_message = "가족 모임에 완벽한 한식당을 추천드려요! 👨‍👩‍👧‍👦"
    elif any(word in message_lower for word in ['데이트', '분위기', '양식', '파스타']):
        selected_restaurants = [fallback_restaurants[1]]
        response_message = "로맨틱한 데이트를 위한 완벽한 이탈리안 레스토랑이에요! 💕"
    elif any(word in message_lower for word in ['카페', '커피', '작업', '공부']):
        selected_restaurants = [fallback_restaurants[2]]
        response_message = "작업하기 좋은 넓은 카페를 추천드려요! ☕"
    else:
        selected_restaurants = fallback_restaurants
        response_message = "인기 맛집들을 추천드려요! 🍽️"
    
    return {
        'response': response_message,
        'restaurants': selected_restaurants,
        'analysis': {
            'method': 'keyword_matching',
            'keywords': message_lower.split()
        }
    }
                  
      
@main_bp.route('/api/restaurants/search', methods=['GET'])
def search_restaurants():
    """맛집 검색 API"""
    try:
        query = request.args.get('q', '').strip()
        category = request.args.get('category', '')
        limit = request.args.get('limit', 10, type=int)
        
        # 실제로는 DB 검색, 여기서는 샘플 데이터
        sample_results = [
            {
                'id': 1,
                'name': '한우마당',
                'category': '한식',
                'location': '성서동',
                'rating': 4.2,
                'address': '대구 달서구 성서로 123'
            },
            {
                'id': 2,
                'name': '파스타팩토리',
                'category': '양식',
                'location': '본리동',
                'rating': 4.4,
                'address': '대구 달서구 본리로 654'
            }
        ]
        
        # 검색 필터링
        results = []
        for restaurant in sample_results:
            if query.lower() in restaurant['name'].lower() or not query:
                if category == restaurant['category'] or not category:
                    results.append(restaurant)
        
        return jsonify({
            'success': True,
            'results': results[:limit],
            'total': len(results)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })      
      

@main_bp.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    """채팅 이력 조회 API"""
    try:
        # 실제로는 세션이나 DB에서 채팅 이력 조회
        # 여기서는 샘플 데이터
        sample_history = [
            {
                'id': 1,
                'timestamp': '2024-06-07 14:30:00',
                'user_message': '가족과 함께 갈 수 있는 한식당 추천해줘',
                'ai_response': '가족과 함께하는 시간을 위한 한식 맛집을 추천해드릴게요!',
                'recommended_restaurants': [
                    {'name': '한우마당', 'category': '한식', 'rating': 4.2}
                ]
            }
        ]
        
        return jsonify({
            'success': True,
            'history': sample_history
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@main_bp.route('/restaurants')
def restaurants_page():
    """식당 목록 페이지"""
    try:
        from app.models.restaurant import Restaurant
        
        # 페이지네이션 파라미터
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int)
        
        # 검색 파라미터
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        
        # 쿼리 구성
        query = Restaurant.query
        
        if search:
            query = query.filter(Restaurant.name.contains(search))
        
        if category:
            query = query.filter(Restaurant.category == category)
        
        # 페이지네이션 적용
        restaurants = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # 카테고리 목록
        categories = ['한식', '중식', '일식', '양식', '치킨', '피자', '햄버거', 
                     '분식', '카페', '디저트', '술집', '베이커리', '기타']
        
        return render_template('restaurants.html', 
                             restaurants=restaurants, 
                             categories=categories,
                             current_search=search,
                             current_category=category)
                             
    except Exception as e:
        # 모델이 없거나 DB 연결 실패 시 기본값
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        
        # 카테고리 목록
        categories = ['한식', '중식', '일식', '양식', '치킨', '피자', '햄버거', 
                     '분식', '카페', '디저트', '술집', '베이커리', '기타']
        
        return render_template('restaurants.html', 
                             restaurants=None,  # 빈 상태로 전달
                             categories=categories, 
                             current_search=search, 
                             current_category=category)

@main_bp.route('/reviews')
def reviews_page():
    """리뷰 페이지"""
    try:
        from flask import request
        from app.models.review import Review
        from datetime import datetime

        # 🔽 쿼리스트링에서 restaurant_name, restaurant_address 받기
        restaurant_id = request.args.get('restaurant_name', '').strip()

        restaurant_address = request.args.get('restaurant_address', '').strip()

        if not restaurant_id:
            raise ValueError("식당 이름이 제공되지 않았습니다.")

        if not restaurant_address:
            raise ValueError("식당 주소가 제공되지 않았습니다.")

        print("✅ 식당명:", repr(restaurant_id))
        print("✅ 주소:", repr(restaurant_address))

        # 필드명이 실제 모델에 맞게 작성되어야 함
        reviews = Review.query.filter_by(
            restaurant_id=restaurant_id,
            restaurant_address=restaurant_address
        ).order_by(Review.created_at.desc()).all()

        print(f"📦 리뷰 개수: {len(reviews)}")

        today = datetime.now().strftime('%Y-%m-%d')

        return render_template(
            'review.html',
            restaurant_id=restaurant_id,  # 필요시 변경
            restaurant_name=restaurant_id,
            restaurant_address=restaurant_address,
            today=today,
            reviews=reviews
        )

    except Exception as e:
        import traceback
        print("❌ 예외 발생:", e)
        traceback.print_exc()

        return render_template(
            'error.html',
            restaurant_id=None,
            restaurant_name=None,
            restaurant_address=None,
            today=datetime.now().strftime('%Y-%m-%d'),
            reviews=[]
        )



@main_bp.route('/reviews/submit', methods=['POST'])
def submit_review():
    """중복 저장 오류가 수정된 리뷰 제출"""
    from flask import request, jsonify, session
    from datetime import datetime
    import json
    import sqlite3
    import os
    import sys
    
    try:
        data = request.get_json()
        print("받은 데이터:", json.dumps(data, ensure_ascii=False, indent=2))
        
        # 사용자 인증 확인
        user_id = session.get('user_id', 1)  # 테스트용 기본값
        print(f"사용자 ID: {user_id}")
        
        # 필수 필드 검증
        required_fields = ['rating', 'content', 'restaurant_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field}는 필수 항목입니다.'}), 400
        
        # === 데이터 정리 및 표준화 (수정된 부분) ===
        restaurant_name = data.get('restaurant_name', '').strip()
        
        # restaurant_address 처리 로직 수정
        raw_address = data.get('restaurant_address', '').strip()
        print(f"원본 주소 데이터: '{raw_address}'")
        
        # 주소 표준화 (더 명확한 로직)
        if raw_address and raw_address != f"{restaurant_name}_기본주소":
            # 유효한 주소가 있는 경우
            restaurant_address = raw_address
            print(f"✅ 유효한 주소 사용: '{restaurant_address}'")
        else:
            # 주소가 없거나 기본값인 경우
            restaurant_address = "주소미제공"
            print(f"⚠️ 기본 주소 사용: '{restaurant_address}'")
        
        rating = int(data['rating'])
        content = data['content'].strip()
        
        print(f"=== 정리된 데이터 ===")
        print(f"사용자 ID: {user_id}")
        print(f"식당명: '{restaurant_name}'")
        print(f"주소: '{restaurant_address}'")
        print(f"평점: {rating}")
        print(f"내용: '{content[:50]}...'")
        
        # === 데이터베이스 경로 설정 ===
        target_db_file = "/home/youngmin/anaconda3/envs/foodi_chatbot/src/data/database/foodi.db"
        target_db_dir = os.path.dirname(target_db_file)
        
        # 디렉토리 생성
        if not os.path.exists(target_db_dir):
            os.makedirs(target_db_dir, exist_ok=True)
            print(f"✅ 디렉토리 생성: {target_db_dir}")
        
        print(f"🎯 DB 파일: {target_db_file}")
        
        # === SQLite 연결 및 저장 ===
        try:
            conn = sqlite3.connect(target_db_file, timeout=30.0)
            
            # 트랜잭션 시작
            conn.execute("BEGIN TRANSACTION;")
            cursor = conn.cursor()
            
            print("✅ SQLite 연결 및 트랜잭션 시작")
            
            # === 테이블 구조 확인 및 생성 ===
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    restaurant_id TEXT NOT NULL,
                    restaurant_address TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    title TEXT,
                    taste_rating INTEGER,
                    service_rating INTEGER,
                    atmosphere_rating INTEGER,
                    value_rating INTEGER,
                    visit_date DATE,
                    visit_purpose TEXT,
                    party_size INTEGER,
                    total_cost INTEGER,
                    sentiment_score REAL,
                    sentiment_label TEXT,
                    would_recommend BOOLEAN,
                    would_revisit BOOLEAN,
                    is_active BOOLEAN DEFAULT 1,
                    is_verified BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            print("✅ 테이블 생성/확인 완료")
            
            # === 중복 확인 강화 ===
            # 1. 동일한 사용자, 식당명에 대한 모든 리뷰 확인
            cursor.execute("""
                SELECT id, restaurant_address, rating, content, created_at 
                FROM reviews 
                WHERE user_id = ? AND restaurant_id = ?
                ORDER BY created_at DESC
            """, (user_id, restaurant_name))
            
            existing_reviews = cursor.fetchall()
            print(f"기존 리뷰 개수: {len(existing_reviews)}")
            
            # 2. 완전히 동일한 리뷰 체크 (주소와 상관없이)
            for existing in existing_reviews:
                existing_id, existing_address, existing_rating, existing_content, existing_time = existing
                
                # 내용과 평점이 완전히 동일한 경우
                if existing_rating == rating and existing_content.strip() == content.strip():
                    # 시간 체크 (10분 이내)
                    try:
                        from datetime import datetime, timedelta
                        last_time = datetime.fromisoformat(existing_time.replace('Z', '+00:00'))
                        if (datetime.utcnow() - last_time).total_seconds() < 600:  # 10분
                            conn.rollback()
                            conn.close()
                            print(f"⚠️ 중복 리뷰 감지: ID {existing_id}")
                            return jsonify({
                                'success': False,
                                'error': '동일한 내용의 리뷰가 최근에 이미 등록되었습니다.',
                                'duplicate_review_id': existing_id,
                                'existing_address': existing_address,
                                'note': '10분 후에 다시 시도하거나 다른 내용으로 작성해주세요.'
                            }), 409
                    except Exception as time_error:
                        print(f"시간 파싱 오류: {time_error}")
                        # 시간 파싱 실패 시에도 중복으로 간주
                        conn.rollback()
                        conn.close()
                        return jsonify({
                            'success': False,
                            'error': '동일한 내용의 리뷰가 이미 존재합니다.',
                            'duplicate_review_id': existing_id
                        }), 409
            
            # === 현재 상태 확인 ===
            cursor.execute("SELECT COUNT(*) FROM reviews")
            current_count = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM reviews 
                WHERE user_id = ? AND restaurant_id = ?
            """, (user_id, restaurant_name))
            user_restaurant_count = cursor.fetchone()[0]
            
            print(f"현재 총 리뷰 수: {current_count}")
            print(f"이 사용자의 이 식당 리뷰 수: {user_restaurant_count}")
            
            # === 데이터 삽입 (정확한 순서로) ===
            print("💾 리뷰 데이터 삽입 시작...")
            
            # 선택적 필드 처리
            visit_date = None
            if data.get('visit_date'):
                try:
                    visit_date = data['visit_date']
                    # 날짜 형식 검증
                    datetime.strptime(visit_date, '%Y-%m-%d')
                except:
                    visit_date = None
            
            # NULL 체크 함수
            def safe_int(value):
                try:
                    return int(value) if value is not None and str(value).strip() else None
                except:
                    return None
            
            def safe_float(value):
                try:
                    return float(value) if value is not None and str(value).strip() else None
                except:
                    return None
            
            def safe_bool(value):
                if value is None:
                    return None
                return bool(value)
            
            # 정확한 순서로 INSERT
            insert_sql = """
                INSERT INTO reviews (
                    user_id, restaurant_id, restaurant_address, rating, content,
                    title, taste_rating, service_rating, atmosphere_rating, value_rating,
                    visit_date, visit_purpose, party_size, total_cost,
                    sentiment_score, sentiment_label, would_recommend, would_revisit
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            insert_values = (
                user_id,                                    # user_id
                restaurant_name,                            # restaurant_id
                restaurant_address,                         # restaurant_address (수정된 로직으로 처리됨)
                rating,                                     # rating
                content,                                    # content
                data.get('title'),                         # title
                safe_int(data.get('taste_rating')),        # taste_rating
                safe_int(data.get('service_rating')),      # service_rating
                safe_int(data.get('atmosphere_rating')),   # atmosphere_rating
                safe_int(data.get('value_rating')),        # value_rating
                visit_date,                                # visit_date
                data.get('visit_purpose'),                 # visit_purpose
                safe_int(data.get('party_size')),          # party_size
                safe_int(data.get('total_cost')),          # total_cost
                safe_float(data.get('sentiment_score')),   # sentiment_score
                data.get('sentiment_label'),               # sentiment_label
                safe_bool(data.get('would_recommend')),    # would_recommend
                safe_bool(data.get('would_revisit'))       # would_revisit
            )
            
            print("삽입할 값들:")
            for i, val in enumerate(insert_values):
                print(f"  {i+1}: {repr(val)}")
            
            cursor.execute(insert_sql, insert_values)
            review_id = cursor.lastrowid
            
            print(f"✅ INSERT 완료: 새 리뷰 ID = {review_id}")
            
            # === 즉시 확인 ===
            cursor.execute("SELECT * FROM reviews WHERE id = ?", (review_id,))
            saved_row = cursor.fetchone()
            
            if not saved_row:
                raise Exception("저장 후 즉시 확인에서 데이터를 찾을 수 없습니다!")
            
            print(f"✅ 저장 확인: ID={saved_row[0]}, user_id={saved_row[1]}, restaurant={saved_row[2]}, address={saved_row[3]}, rating={saved_row[4]}")
            
            # 트랜잭션 커밋
            conn.commit()
            print("✅ 트랜잭션 커밋 완료")
            
            # === 최종 확인 ===
            cursor.execute("SELECT COUNT(*) FROM reviews")
            new_total = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM reviews 
                WHERE user_id = ? AND restaurant_id = ?
            """, (user_id, restaurant_name))
            new_user_restaurant_count = cursor.fetchone()[0]
            
            conn.close()
            
            # 파일 정보
            file_size = os.path.getsize(target_db_file)
            
            print(f"🎉 저장 완료!")
            print(f"   총 리뷰 수: {current_count} → {new_total}")
            print(f"   사용자-식당 리뷰 수: {user_restaurant_count} → {new_user_restaurant_count}")
            print(f"   파일 크기: {file_size} bytes")
            
            # === 성공 응답 ===
            return jsonify({
                'success': True,
                'message': f'리뷰가 정확히 저장되었습니다! (ID: {review_id})',
                'review_id': review_id,
                'restaurant_name': restaurant_name,
                'restaurant_address': restaurant_address,
                'user_id': user_id,
                'rating': rating,
                'total_reviews': new_total,
                'user_restaurant_reviews': new_user_restaurant_count,
                'database_file': target_db_file,
                'database_size': file_size,
                'method': 'fixed_address_logic',
                'verification': {
                    'insert_successful': True,
                    'immediate_check_passed': True,
                    'transaction_committed': True,
                    'address_used': restaurant_address
                },
                'sqlite_commands': {
                    'check_this_review': f"sqlite3 '{target_db_file}' \"SELECT * FROM reviews WHERE id = {review_id};\"",
                    'check_table_structure': f"sqlite3 '{target_db_file}' \".schema reviews\"",
                    'list_all_reviews': f"sqlite3 '{target_db_file}' \"SELECT id, user_id, restaurant_id, restaurant_address, rating, content, created_at FROM reviews ORDER BY id DESC LIMIT 10;\"",
                    'user_restaurant_reviews': f"sqlite3 '{target_db_file}' \"SELECT id, rating, content, created_at FROM reviews WHERE user_id = {user_id} AND restaurant_id = '{restaurant_name}' ORDER BY created_at DESC;\"",
                    'duplicate_check': f"sqlite3 '{target_db_file}' \"SELECT user_id, restaurant_id, restaurant_address, rating, content, COUNT(*) as count FROM reviews GROUP BY user_id, restaurant_id, rating, content HAVING COUNT(*) > 1;\""
                }
            })
                
        except Exception as sqlite_error:
            # 롤백
            try:
                conn.rollback()
                conn.close()
                print("❌ 트랜잭션 롤백 완료")
            except:
                pass
            
            print(f"❌ SQLite 오류: {sqlite_error}")
            import traceback
            traceback.print_exc()
            
            return jsonify({
                'success': False,
                'error': f'데이터베이스 저장 실패: {str(sqlite_error)}',
                'attempted_data': {
                    'user_id': user_id,
                    'restaurant_name': restaurant_name,
                    'restaurant_address': restaurant_address,
                    'rating': rating,
                    'content': content[:100] + '...' if len(content) > 100 else content
                }
            }), 500
    
    except Exception as e:
        print(f"❌ 전체 오류: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': f'서버 오류: {str(e)}'
        }), 500


# 추가: 중복 리뷰 정리 및 검증 엔드포인트
@main_bp.route('/admin/cleanup-duplicate-reviews', methods=['POST'])
def cleanup_duplicate_reviews():
    """중복된 리뷰를 찾아 정리합니다."""
    import sqlite3
    import os
    from flask import jsonify, request
    
    try:
        target_db_file = "/home/youngmin/anaconda3/envs/foodi_chatbot/src/data/database/foodi.db"
        
        if not os.path.exists(target_db_file):
            return jsonify({'success': False, 'error': '데이터베이스 파일을 찾을 수 없습니다.'})
        
        # 확인용 매개변수
        dry_run = request.json.get('dry_run', True) if request.is_json else True
        
        conn = sqlite3.connect(target_db_file)
        cursor = conn.cursor()
        
        # 중복 데이터 찾기 (내용과 평점이 동일한 리뷰)
        cursor.execute("""
            SELECT user_id, restaurant_id, rating, content, 
                   GROUP_CONCAT(id || '|' || restaurant_address || '|' || created_at) as records,
                   COUNT(*) as count
            FROM reviews 
            GROUP BY user_id, restaurant_id, rating, content
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """)
        
        duplicates = cursor.fetchall()
        
        if not duplicates:
            conn.close()
            return jsonify({
                'success': True,
                'message': '중복된 리뷰가 없습니다.',
                'duplicates_found': 0
            })
        
        removed_count = 0
        cleanup_details = []
        
        if not dry_run:
            # 실제 삭제 (가장 오래된 것 하나만 남기고 나머지 삭제)
            for duplicate in duplicates:
                records = duplicate[4].split(',')
                
                # 시간순으로 정렬하여 가장 오래된 것을 찾음
                parsed_records = []
                for record in records:
                    parts = record.split('|')
                    if len(parts) >= 3:
                        parsed_records.append({
                            'id': int(parts[0]),
                            'address': parts[1],
                            'created_at': parts[2]
                        })
                
                # 시간순 정렬
                parsed_records.sort(key=lambda x: x['created_at'])
                
                # 첫 번째(가장 오래된) 것을 제외하고 나머지 삭제
                ids_to_remove = [r['id'] for r in parsed_records[1:]]
                
                for id_to_remove in ids_to_remove:
                    cursor.execute("DELETE FROM reviews WHERE id = ?", (id_to_remove,))
                    removed_count += 1
                
                cleanup_details.append({
                    'user_id': duplicate[0],
                    'restaurant_id': duplicate[1],
                    'rating': duplicate[2],
                    'content': duplicate[3][:50] + '...' if len(duplicate[3]) > 50 else duplicate[3],
                    'kept_id': parsed_records[0]['id'] if parsed_records else None,
                    'kept_address': parsed_records[0]['address'] if parsed_records else None,
                    'removed_ids': ids_to_remove,
                    'total_count': duplicate[5]
                })
            
            conn.commit()
        else:
            # 시뮬레이션만
            for duplicate in duplicates:
                records = duplicate[4].split(',')
                cleanup_details.append({
                    'user_id': duplicate[0],
                    'restaurant_id': duplicate[1],
                    'rating': duplicate[2],
                    'content': duplicate[3][:50] + '...' if len(duplicate[3]) > 50 else duplicate[3],
                    'would_remove_count': duplicate[5] - 1,
                    'total_count': duplicate[5],
                    'records': records
                })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{"시뮬레이션 완료" if dry_run else "중복 리뷰 정리 완료"}',
            'duplicates_found': len(duplicates),
            'duplicates_removed': removed_count if not dry_run else sum(d.get('would_remove_count', 0) for d in cleanup_details),
            'dry_run': dry_run,
            'cleanup_details': cleanup_details
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 추가: 테이블 구조 확인 엔드포인트
@main_bp.route('/debug/table-structure', methods=['GET'])
def check_table_structure():
    """reviews 테이블 구조를 확인합니다."""
    import sqlite3
    import os
    from flask import jsonify
    
    try:
        target_db_file = "/home/youngmin/anaconda3/envs/foodi_chatbot/src/data/database/foodi.db"
        
        if not os.path.exists(target_db_file):
            return jsonify({'success': False, 'error': '데이터베이스 파일을 찾을 수 없습니다.'})
        
        conn = sqlite3.connect(target_db_file)
        cursor = conn.cursor()
        
        # 테이블 구조 확인
        cursor.execute("PRAGMA table_info(reviews)")
        columns = cursor.fetchall()
        
        # 샘플 데이터 확인
        cursor.execute("SELECT * FROM reviews ORDER BY id DESC LIMIT 3")
        sample_data = cursor.fetchall()
        
        # 중복 데이터 확인
        cursor.execute("""
            SELECT user_id, restaurant_id, restaurant_address, rating, content, COUNT(*) as count
            FROM reviews 
            GROUP BY user_id, restaurant_id, restaurant_address, rating, content
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """)
        duplicates = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'table_info': {
                'columns': [{'index': col[0], 'name': col[1], 'type': col[2], 'not_null': col[3], 'default': col[4], 'pk': col[5]} for col in columns],
                'column_count': len(columns)
            },
            'sample_data': [list(row) for row in sample_data],
            'duplicate_analysis': {
                'duplicate_count': len(duplicates),
                'duplicates': [list(row) for row in duplicates[:5]]  # 상위 5개만
            },
            'sqlite_commands': {
                'table_info': f"sqlite3 '{target_db_file}' '.schema reviews'",
                'show_data': f"sqlite3 '{target_db_file}' 'SELECT id, user_id, restaurant_id, restaurant_address, rating, content FROM reviews ORDER BY id DESC LIMIT 10;'",
                'find_duplicates': f"sqlite3 '{target_db_file}' \"SELECT user_id, restaurant_id, COUNT(*) FROM reviews GROUP BY user_id, restaurant_id HAVING COUNT(*) > 1;\""
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 추가: 중복 데이터 정리 엔드포인트
@main_bp.route('/admin/clean-duplicates', methods=['POST'])
def clean_duplicate_reviews():
    """중복된 리뷰 데이터를 정리합니다."""
    import sqlite3
    import os
    from flask import jsonify, request
    
    try:
        target_db_file = "/home/youngmin/anaconda3/envs/foodi_chatbot/src/data/database/foodi.db"
        
        if not os.path.exists(target_db_file):
            return jsonify({'success': False, 'error': '데이터베이스 파일을 찾을 수 없습니다.'})
        
        # 확인용 매개변수
        dry_run = request.json.get('dry_run', True) if request.is_json else True
        
        conn = sqlite3.connect(target_db_file)
        cursor = conn.cursor()
        
        # 중복 데이터 찾기 (완전히 동일한 리뷰)
        cursor.execute("""
            SELECT user_id, restaurant_id, restaurant_address, rating, content, 
                   GROUP_CONCAT(id) as ids, COUNT(*) as count
            FROM reviews 
            GROUP BY user_id, restaurant_id, restaurant_address, rating, content
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """)
        
        duplicates = cursor.fetchall()
        
        if not duplicates:
            conn.close()
            return jsonify({
                'success': True,
                'message': '중복된 리뷰가 없습니다.',
                'duplicates_found': 0
            })
        
        removed_count = 0
        
        if not dry_run:
            # 실제 삭제 (가장 오래된 것들만 남기고 나머지 삭제)
            for duplicate in duplicates:
                ids = duplicate[5].split(',')
                # 첫 번째 ID (가장 오래된 것)를 제외하고 나머지 삭제
                ids_to_remove = ids[1:]
                
                for id_to_remove in ids_to_remove:
                    cursor.execute("DELETE FROM reviews WHERE id = ?", (int(id_to_remove),))
                    removed_count += 1
            
            conn.commit()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{"시뮬레이션 완료" if dry_run else "중복 리뷰 정리 완료"}',
            'duplicates_found': len(duplicates),
            'duplicates_removed': removed_count if not dry_run else 0,
            'dry_run': dry_run,
            'duplicate_details': [
                {
                    'user_id': dup[0],
                    'restaurant_id': dup[1], 
                    'restaurant_address': dup[2],
                    'rating': dup[3],
                    'content': dup[4][:50] + '...' if len(dup[4]) > 50 else dup[4],
                    'count': dup[6],
                    'ids': dup[5]
                } for dup in duplicates
            ]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 추가: 데이터베이스 상태 확인 엔드포인트
@main_bp.route('/debug/database-info', methods=['GET'])
def database_info():
    """src/data/database/foodi.db 파일 정보 확인"""
    import sqlite3
    import os
    from flask import jsonify
    
    try:
        current_dir = os.getcwd()
        db_dir = os.path.join(current_dir, 'data', 'database')
        db_file = os.path.join(db_dir, 'foodi.db')
        abs_db_file = os.path.abspath(db_file)
        
        result = {
            'paths': {
                'current_directory': current_dir,
                'database_directory': db_dir,
                'database_file': db_file,
                'absolute_path': abs_db_file
            },
            'file_status': {
                'directory_exists': os.path.exists(db_dir),
                'file_exists': os.path.exists(abs_db_file)
            }
        }
        
        # 디렉토리 정보
        if os.path.exists(db_dir):
            result['directory_info'] = {
                'contents': os.listdir(db_dir),
                'permissions': oct(os.stat(db_dir).st_mode)[-3:]
            }
        
        # 파일 정보
        if os.path.exists(abs_db_file):
            file_size = os.path.getsize(abs_db_file)
            file_mtime = os.path.getmtime(abs_db_file)
            
            result['file_info'] = {
                'size': file_size,
                'modified_time': datetime.fromtimestamp(file_mtime).isoformat(),
                'permissions': oct(os.stat(abs_db_file).st_mode)[-3:]
            }
            
            # SQLite 정보
            try:
                conn = sqlite3.connect(abs_db_file)
                cursor = conn.cursor()
                
                # 테이블 목록
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                result['sqlite_info'] = {
                    'tables': tables,
                    'can_connect': True
                }
                
                # reviews 테이블 정보
                if 'reviews' in tables:
                    cursor.execute("SELECT COUNT(*) FROM reviews")
                    review_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT * FROM reviews ORDER BY id DESC LIMIT 5")
                    recent_reviews = []
                    for row in cursor.fetchall():
                        recent_reviews.append({
                            'id': row[0],
                            'user_id': row[1],
                            'restaurant': row[2],
                            'rating': row[4],
                            'content': row[5][:100] + '...' if len(row[5]) > 100 else row[5]
                        })
                    
                    result['reviews_info'] = {
                        'count': review_count,
                        'recent': recent_reviews
                    }
                
                conn.close()
                
            except Exception as sqlite_error:
                result['sqlite_info'] = {
                    'error': str(sqlite_error),
                    'can_connect': False
                }
        
        # 유용한 명령어들
        result['commands'] = {
            'create_directory': f"mkdir -p '{db_dir}'",
            'check_file': f"ls -la '{abs_db_file}'",
            'sqlite_connect': f"sqlite3 '{abs_db_file}'",
            'sqlite_tables': f"sqlite3 '{abs_db_file}' '.tables'",
            'sqlite_reviews': f"sqlite3 '{abs_db_file}' 'SELECT * FROM reviews LIMIT 10;'"
        }
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# 추가: 디렉토리 및 파일 초기화 엔드포인트
@main_bp.route('/admin/init-database', methods=['POST'])
def init_database():
    """src/data/database 디렉토리와 foodi.db 파일 초기화"""
    import sqlite3
    import os
    from flask import jsonify
    
    try:
        current_dir = os.getcwd()
        db_dir = os.path.join(current_dir, 'src', 'data', 'database')
        db_file = os.path.join(db_dir, 'foodi.db')
        abs_db_file = os.path.abspath(db_file)
        
        print(f"데이터베이스 초기화: {abs_db_file}")
        
        # 1. 디렉토리 생성
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"✅ 디렉토리 생성: {db_dir}")
        else:
            print(f"✅ 디렉토리 존재: {db_dir}")
        
        # 2. 데이터베이스 파일 생성 및 초기화
        conn = sqlite3.connect(abs_db_file)
        cursor = conn.cursor()
        
        # 기존 테이블 삭제 (주의!)
        cursor.execute("DROP TABLE IF EXISTS reviews")
        
        # 새 테이블 생성
        cursor.execute("""
            CREATE TABLE reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_id TEXT NOT NULL,
                restaurant_address TEXT NOT NULL,
                rating INTEGER NOT NULL,
                content TEXT NOT NULL,
                title TEXT,
                taste_rating INTEGER,
                service_rating INTEGER,
                atmosphere_rating INTEGER,
                value_rating INTEGER,
                visit_date DATE,
                visit_purpose TEXT,
                party_size INTEGER,
                total_cost INTEGER,
                sentiment_score REAL,
                sentiment_label TEXT,
                would_recommend BOOLEAN,
                would_revisit BOOLEAN,
                is_active BOOLEAN DEFAULT 1,
                is_verified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 테스트 데이터 추가
        cursor.execute("""
            INSERT INTO reviews (user_id, restaurant_id, restaurant_address, rating, content)
            VALUES (1, '초기화테스트식당', '테스트주소', 5, '데이터베이스 초기화 테스트 리뷰입니다.')
        """)
        
        conn.commit()
        test_id = cursor.lastrowid
        
        # 확인
        cursor.execute("SELECT COUNT(*) FROM reviews")
        count = cursor.fetchone()[0]
        
        conn.close()
        
        file_size = os.path.getsize(abs_db_file)
        
        return jsonify({
            'success': True,
            'message': '데이터베이스가 성공적으로 초기화되었습니다!',
            'database_file': abs_db_file,
            'test_review_id': test_id,
            'review_count': count,
            'file_size': file_size,
            'sqlite_command': f"sqlite3 '{abs_db_file}' 'SELECT * FROM reviews;'"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'초기화 실패: {str(e)}'
        }), 500

# 추가: DB 파일 위치와 내용 확인 엔드포인트
@main_bp.route('/debug/database', methods=['GET'])
def debug_database():
    """데이터베이스 파일 위치와 내용을 확인합니다."""
    import sqlite3
    import os
    from flask import jsonify
    
    try:
        result = {
            'working_directory': os.getcwd(),
            'database_files': [],
            'recommended_sqlite_command': None
        }
        
        # 가능한 모든 DB 파일 찾기
        search_paths = [
            'foodi.db',
            'foodi_confirmed.db',
            'instance/foodi.db',
            'app/foodi.db',
            '../foodi.db',
            'database.db'
        ]
        
        for path in search_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(path):
                try:
                    size = os.path.getsize(path)
                    mtime = os.path.getmtime(path)
                    
                    # SQLite로 내용 확인
                    conn = sqlite3.connect(path)
                    cursor = conn.cursor()
                    
                    # 테이블 확인
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    review_count = 0
                    if 'reviews' in tables:
                        cursor.execute("SELECT COUNT(*) FROM reviews")
                        review_count = cursor.fetchone()[0]
                    
                    conn.close()
                    
                    result['database_files'].append({
                        'path': path,
                        'absolute_path': abs_path,
                        'size': size,
                        'modified_time': datetime.fromtimestamp(mtime).isoformat(),
                        'tables': tables,
                        'review_count': review_count,
                        'is_main': 'foodi' in path.lower()
                    })
                    
                except Exception as db_error:
                    result['database_files'].append({
                        'path': path,
                        'absolute_path': abs_path,
                        'error': str(db_error)
                    })
        
        # 가장 적절한 DB 파일 찾기
        if result['database_files']:
            # 리뷰가 가장 많은 파일 또는 가장 큰 파일
            main_db = max(
                [db for db in result['database_files'] if 'error' not in db],
                key=lambda x: (x.get('review_count', 0), x.get('size', 0)),
                default=None
            )
            
            if main_db:
                result['recommended_sqlite_command'] = f"sqlite3 '{main_db['absolute_path']}' \"SELECT * FROM reviews ORDER BY id DESC LIMIT 10;\""
                result['main_database'] = main_db
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# 추가: 리뷰 확인 엔드포인트
@main_bp.route('/debug/reviews', methods=['GET'])
def debug_reviews():
    """모든 DB 파일에서 리뷰를 확인합니다."""
    import sqlite3
    import os
    from flask import jsonify, request
    
    try:
        limit = int(request.args.get('limit', 10))
        result = {'databases': []}
        
        search_paths = ['foodi.db', 'foodi_confirmed.db', 'instance/foodi.db', 'app/foodi.db']
        
        for path in search_paths:
            if os.path.exists(path):
                try:
                    conn = sqlite3.connect(path)
                    cursor = conn.cursor()
                    
                    # 최근 리뷰들
                    cursor.execute(f"""
                        SELECT id, user_id, restaurant_id, rating, content, created_at 
                        FROM reviews 
                        ORDER BY id DESC 
                        LIMIT {limit}
                    """)
                    
                    reviews = []
                    for row in cursor.fetchall():
                        reviews.append({
                            'id': row[0],
                            'user_id': row[1],
                            'restaurant': row[2],
                            'rating': row[3],
                            'content': row[4][:100] + '...' if len(row[4]) > 100 else row[4],
                            'created_at': row[5]
                        })
                    
                    cursor.execute("SELECT COUNT(*) FROM reviews")
                    total_count = cursor.fetchone()[0]
                    
                    conn.close()
                    
                    result['databases'].append({
                        'path': os.path.abspath(path),
                        'total_reviews': total_count,
                        'recent_reviews': reviews
                    })
                    
                except Exception as db_error:
                    result['databases'].append({
                        'path': os.path.abspath(path),
                        'error': str(db_error)
                    })
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# 저장된 리뷰 확인용 엔드포인트
@main_bp.route('/reviews/list', methods=['GET'])
def list_reviews():
    """저장된 리뷰 목록을 가져옵니다."""
    import sqlite3
    import os
    from flask import request, jsonify
    
    try:
        # 데이터베이스 파일 찾기
        possible_db_files = ['foodi.db', 'instance/foodi.db', 'app/foodi.db']
        db_file = None
        
        for path in possible_db_files:
            if os.path.exists(path):
                db_file = path
                break
        
        if not db_file:
            return jsonify({
                'success': False,
                'error': '데이터베이스 파일을 찾을 수 없습니다.'
            })
        
        # 쿼리 파라미터
        restaurant_name = request.args.get('restaurant_name')
        restaurant_address = request.args.get('restaurant_address')
        limit = int(request.args.get('limit', 10))
        
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 전체 리뷰 수
        cursor.execute("SELECT COUNT(*) FROM reviews")
        total_count = cursor.fetchone()[0]
        
        # 조건부 쿼리
        if restaurant_name and restaurant_address:
            cursor.execute("""
                SELECT id, user_id, restaurant_id, restaurant_address, rating, content, 
                       visit_date, created_at 
                FROM reviews 
                WHERE restaurant_id = ? AND restaurant_address = ?
                ORDER BY created_at DESC 
                LIMIT ?
            """, (restaurant_name, restaurant_address, limit))
        else:
            cursor.execute("""
                SELECT id, user_id, restaurant_id, restaurant_address, rating, content,
                       visit_date, created_at
                FROM reviews 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        
        reviews = []
        for row in rows:
            reviews.append({
                'id': row[0],
                'user_id': row[1],
                'restaurant_name': row[2],
                'restaurant_address': row[3],
                'rating': row[4],
                'content': row[5][:200] + '...' if len(row[5]) > 200 else row[5],
                'visit_date': row[6],
                'created_at': row[7]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_reviews': total_count,
            'reviews': reviews,
            'database_file': os.path.abspath(db_file)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'리뷰 조회 오류: {str(e)}'
        })

# 데이터베이스 상태 확인 엔드포인트
@main_bp.route('/reviews/status', methods=['GET'])
def database_status():
    """데이터베이스 상태를 확인합니다."""
    import sqlite3
    import os
    from flask import jsonify
    
    try:
        status = {
            'sqlalchemy_available': False,
            'direct_sqlite_available': False,
            'database_files': [],
            'total_reviews': 0,
            'recent_reviews': []
        }
        
        # SQLAlchemy 테스트
        try:
            from app import db
            from app.models.review import Review
            status['total_reviews'] = Review.query.count()
            status['sqlalchemy_available'] = True
            print("✅ SQLAlchemy 사용 가능")
        except Exception as sqlalchemy_error:
            print(f"❌ SQLAlchemy 사용 불가: {sqlalchemy_error}")
        
        # 직접 SQLite 테스트
        possible_files = ['foodi.db', 'instance/foodi.db', 'app/foodi.db', '../foodi.db']
        
        for db_file in possible_files:
            if os.path.exists(db_file):
                status['database_files'].append({
                    'path': os.path.abspath(db_file),
                    'size': os.path.getsize(db_file),
                    'modified': os.path.getmtime(db_file)
                })
                
                try:
                    conn = sqlite3.connect(db_file)
                    cursor = conn.cursor()
                    
                    # 테이블 확인
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    if 'reviews' in tables:
                        cursor.execute("SELECT COUNT(*) FROM reviews")
                        count = cursor.fetchone()[0]
                        status['total_reviews'] = max(status['total_reviews'], count)
                        
                        # 최근 리뷰 5개
                        cursor.execute("""
                            SELECT id, restaurant_id, rating, content, created_at
                            FROM reviews ORDER BY created_at DESC LIMIT 5
                        """)
                        recent = cursor.fetchall()
                        status['recent_reviews'] = [
                            {
                                'id': row[0],
                                'restaurant': row[1],
                                'rating': row[2],
                                'content': row[3][:100] + '...' if len(row[3]) > 100 else row[3],
                                'created_at': row[4]
                            } for row in recent
                        ]
                    
                    conn.close()
                    status['direct_sqlite_available'] = True
                    
                except Exception as sqlite_error:
                    print(f"SQLite 파일 {db_file} 오류: {sqlite_error}")
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })



@main_bp.route('/history')
def history_page():
    """추천 이력 페이지"""
    try:
        from app.models.recommendation import Recommendation
        
        # 추천 통계 계산
        total = Recommendation.query.count()
        visited = Recommendation.query.filter(Recommendation.visited == True).count()
        
        # 가장 많이 추천받은 카테고리 (실제로는 GROUP BY 쿼리 필요)
        # 임시로 기본값 설정
        favorite_category = '한식'  # 실제로는 DB에서 계산
        
        stats = {
            'total': total,
            'visited': visited,
            'favorite_category': favorite_category
        }
        
        return render_template('history.html', stats=stats)
        
    except Exception as e:
        # 모델이 없거나 DB 연결 실패 시 기본값
        stats = {
            'total': 0,
            'visited': 0,
            'favorite_category': '한식'
        }
        
        return render_template('history.html', stats=stats)


@main_bp.route('/about')
def about():
    """서비스 소개 페이지"""
    return jsonify({
        'name': 'FOODI',
        'description': '대구 달서구 맛집 추천 AI 챗봇',
        'version': '1.0.0',
        'features': {
            'ai_recommendation': 'OpenAI GPT 기반 맛집 추천',
            'location_based': '위치 기반 식당 검색',
            'review_system': '사용자 리뷰 및 평점 시스템',
            'map_integration': 'Google Maps 연동',
            'natural_language': '자연어 대화 인터페이스'
        },
        'coverage_area': '대구광역시 달서구',
        'contact': {
            'email': 'support@foodi.com',
            'github': 'https://github.com/your-repo/foodi'
        }
    })

@main_bp.route('/api')
def api_info():
    """API 정보 엔드포인트"""
    return jsonify({
        'api_version': 'v1',
        'description': 'FOODI REST API',
        'endpoints': {
            'chat': {
                'url': '/api/chat',
                'methods': ['POST'],
                'description': '챗봇과 대화'
            },
            'restaurants': {
                'url': '/api/restaurants',
                'methods': ['GET', 'POST'],
                'description': '식당 정보 조회 및 등록'
            },
            'reviews': {
                'url': '/api/reviews',
                'methods': ['GET', 'POST'],
                'description': '리뷰 조회 및 작성'
            },
            'recommendations': {
                'url': '/api/recommendations',
                'methods': ['GET', 'POST'],
                'description': '맞춤 추천 요청'
            }
        },
        'authentication': {
            'type': 'API Key',
            'header': 'Authorization',
            'format': 'Bearer {token}'
        },
        'rate_limits': {
            'default': '100 requests per hour',
            'chat': '30 requests per minute'
        }
    })
    
@main_bp.route('/api/analytics', methods=['GET'])
def get_analytics():
    """추천 시스템 분석 데이터 API"""
    try:
        analytics_data = {
            'popular_categories': [
                {'category': '한식', 'count': 45},
                {'category': '양식', 'count': 32},
                {'category': '중식', 'count': 28},
                {'category': '일식', 'count': 25},
                {'category': '카페', 'count': 38}
            ],
            'popular_situations': [
                {'situation': '가족', 'count': 28},
                {'situation': '데이트', 'count': 35},
                {'situation': '친구', 'count': 22},
                {'situation': '혼밥', 'count': 18}
            ],
            'recommendation_accuracy': 0.87,
            'user_satisfaction': 4.3,
            'total_recommendations': 150
        }
        
        return jsonify({
            'success': True,
            'analytics': analytics_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
    

# OpenAI 서비스 관련 API들
@main_bp.route('/api/restaurants/similar/<restaurant_name>')
def get_similar_restaurants(restaurant_name):
    """비슷한 맛집 추천 API"""
    try:
        if openai_service:
            similar_restaurants = openai_service.get_similar_restaurants(restaurant_name)
            return jsonify({
                'success': True,
                'similar_restaurants': similar_restaurants
            })
        else:
            return jsonify({
                'success': False,
                'error': 'AI 서비스를 사용할 수 없습니다.'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# 추가: 헬스 체크 엔드포인트
@main_bp.route('/api/health', methods=['GET'])
def health_check():
    """API 서버 상태 확인"""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'session_manager': get_session_manager() is not None,
            'version': '1.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# 추가: 세션 상태 확인 엔드포인트
@main_bp.route('/api/session/status', methods=['GET'])
def session_status():
    """현재 세션 상태 확인"""
    try:
        session_id = session.get('session_id')
        user_id = session.get('user_id')
        
        if not session_id or not user_id:
            return jsonify({
                'authenticated': False,
                'message': '세션 정보 없음'
            })
        
        sm = get_session_manager()
        session_valid = False
        
        if sm:
            session_data = sm.get_session(session_id)
            session_valid = (session_data is not None and 
                           session_data.get('state') == 'active')
        
        return jsonify({
            'authenticated': True,
            'session_id': session_id[:8] + '...',  # 보안을 위해 일부만 표시
            'user_id': user_id,
            'session_manager_valid': session_valid,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"세션 상태 확인 오류: {e}")
        return jsonify({
            'authenticated': False,
            'error': str(e)
        }), 500

@main_bp.route('/api/debug/test', methods=['POST'])
def debug_test():
    """개발용 디버그 테스트"""
    try:
        if os.environ.get('FLASK_ENV') != 'development':
            return jsonify({'error': '개발 환경에서만 사용 가능'}), 403
        
        data = request.get_json()
        
        return jsonify({
            'success': True,
            'message': '디버그 테스트 성공',
            'received_data': data,
            'session_info': {
                'session_id': session.get('session_id'),
                'user_id': session.get('user_id'),
                'keys': list(session.keys())
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500

def check_dependencies():
    """시스템 의존성 확인"""
    issues = []
    
    # SessionManager 확인
    try:
        from app.utils.session_manager import SessionManager
        logger.info("✓ SessionManager 사용 가능")
    except ImportError as e:
        issues.append(f"SessionManager 없음: {e}")
        logger.warning(f"⚠️ SessionManager 없음: {e}")
    
    # 데이터베이스 모델 확인
    try:
        from app.models.recommendation import Recommendation
        from app.config.database import db
        logger.info("✓ 데이터베이스 모델 사용 가능")
    except ImportError as e:
        issues.append(f"DB 모델 없음: {e}")
        logger.warning(f"⚠️ DB 모델 없음: {e}")
    
    # datetime 확인
    try:
        from datetime import datetime
        test_time = datetime.utcnow()
        logger.info("✓ datetime 모듈 사용 가능")
    except Exception as e:
        issues.append(f"datetime 오류: {e}")
        logger.error(f"❌ datetime 오류: {e}")
    
    return issues

@main_bp.route('/api/history/plan', methods=['POST'])
def mark_as_planned_safe():
    """완전히 안전한 버전의 mark_as_planned"""
    
    # 의존성 확인
    dependency_issues = check_dependencies()
    if dependency_issues:
        logger.warning(f"의존성 문제: {dependency_issues}")
    
    # 모든 변수 초기화
    data = None
    restaurant_id = None
    restaurant_name = "알 수 없는 맛집"
    status = "planned"
    user_query = ""
    action_type = "status_change"
    user_id = None
    session_id = None
    
    try:
        logger.info("=== API 호출 시작 ===")
        
        # 1. 요청 데이터 파싱
        try:
            data = request.get_json()
            logger.info(f"요청 데이터: {data}")
        except Exception as e:
            logger.error(f"JSON 파싱 오류: {e}")
            return jsonify({
                'success': False,
                'message': 'JSON 데이터 파싱 오류',
                'error_type': 'JSON_PARSE_ERROR'
            }), 400
        
        if not data:
            return jsonify({
                'success': False,
                'message': '요청 데이터가 없습니다.',
                'error_type': 'NO_DATA'
            }), 400
        
        # 2. 파라미터 추출
        try:
            restaurant_id = data.get('restaurant_id')
            restaurant_name = data.get('restaurant_name', '알 수 없는 맛집')
            status = data.get('status', 'planned')
            user_query = data.get('user_query', f'{restaurant_name} 상태 변경')
            action_type = data.get('action_type', 'status_change')
            
            logger.info(f"파라미터: id={restaurant_id}, name={restaurant_name}, status={status}")
            
        except Exception as e:
            logger.error(f"파라미터 추출 오류: {e}")
            return jsonify({
                'success': False,
                'message': '파라미터 처리 오류',
                'error_type': 'PARAMETER_ERROR'
            }), 400
        
        # 3. 기본 검증
        if not restaurant_id:
            return jsonify({
                'success': False,
                'message': 'restaurant_id가 필요합니다.',
                'error_type': 'MISSING_RESTAURANT_ID'
            }), 400
        
        # 4. 세션 확인 (기본)
        try:
            session_id = session.get('session_id')
            user_id = session.get('user_id')
            
            logger.info(f"세션: session_id={session_id}, user_id={user_id}")
            
            if not session_id or not user_id:
                return jsonify({
                    'success': False,
                    'message': '로그인이 필요합니다.',
                    'error_type': 'NOT_LOGGED_IN'
                }), 401
                
        except Exception as e:
            logger.error(f"세션 확인 오류: {e}")
            return jsonify({
                'success': False,
                'message': '세션 확인 중 오류',
                'error_type': 'SESSION_ERROR'
            }), 401
        
        # 5. SessionManager 확인 (선택적)
        sm = None
        try:
            sm = get_session_manager()
            if sm:
                session_data = sm.get_session(session_id)
                if session_data and session_data.get('state') == 'active':
                    logger.info("SessionManager 세션 검증 성공")
                else:
                    logger.warning("SessionManager 세션 검증 실패")
        except Exception as e:
            logger.warning(f"SessionManager 확인 오류 (계속 진행): {e}")
        
        # 6. 데이터 저장 시도
        storage_success = False
        storage_message = ""
        
        # 6-1. 데이터베이스 저장 시도
        try:
            from app.models.recommendation import Recommendation
            from app.config.database import db
            
            # 기존 레코드 확인
            existing = Recommendation.query.filter_by(
                user_id=user_id,
                restaurant_id=restaurant_id
            ).first()
            
            current_time = datetime.utcnow()
            
            if existing:
                existing.status = status
                if hasattr(existing, 'updated_at'):
                    existing.updated_at = current_time
            else:
                new_record = Recommendation(
                    user_id=user_id,
                    restaurant_id=restaurant_id,
                    status=status
                )
                if hasattr(new_record, 'created_at'):
                    new_record.created_at = current_time
                if hasattr(new_record, 'updated_at'):
                    new_record.updated_at = current_time
                
                db.session.add(new_record)
            
            db.session.commit()
            storage_success = True
            storage_message = "데이터베이스에 저장됨"
            logger.info("DB 저장 성공")
            
        except ImportError:
            storage_message = "DB 모델 없음, 메모리에만 저장"
            logger.warning("DB 모델 import 실패")
        except Exception as db_error:
            storage_message = f"DB 저장 실패: {str(db_error)}"
            logger.error(f"DB 저장 오류: {db_error}")
            try:
                db.session.rollback()
            except:
                pass
        
        # 6-2. SessionManager에 저장 시도
        if sm and session_id:
            try:
                sm.add_message_to_session(
                    session_id=session_id,
                    role='system',
                    content=f"맛집 상태 변경: {restaurant_name} -> {status}",
                    metadata={
                        'restaurant_id': restaurant_id,
                        'restaurant_name': restaurant_name,
                        'status': status,
                        'action': action_type,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                )
                logger.info("SessionManager 저장 성공")
            except Exception as sm_error:
                logger.error(f"SessionManager 저장 오류: {sm_error}")
        
        # 7. 성공 응답
        status_messages = {
            'planned': '방문 예정으로 등록되었습니다',
            'visited': '방문 완료로 등록되었습니다',
            'not-visited': '계획에서 제거되었습니다',
            'favorite': '즐겨찾기에 추가되었습니다'
        }
        
        message = status_messages.get(status, f'상태가 {status}로 변경되었습니다')
        
        response = {
            'success': True,
            'message': f'"{restaurant_name}"이(가) {message}.',
            'data': {
                'restaurant_id': restaurant_id,
                'restaurant_name': restaurant_name,
                'status': status,
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat()
            },
            'storage_info': {
                'database_success': storage_success,
                'storage_message': storage_message,
                'session_manager_available': sm is not None
            }
        }
        
        logger.info("성공 응답 전송")
        return jsonify(response)
        
    except Exception as e:
        # 최종 예외 처리
        error_message = str(e)
        error_type = type(e).name
        
        logger.error(f"=== 전체 오류 ===")
        logger.error(f"오류 타입: {error_type}")
        logger.error(f"오류 메시지: {error_message}")
        logger.error(f"스택 트레이스: {traceback.format_exc()}")
        
        # 개발 환경에서는 상세 정보 제공
        if os.environ.get('FLASK_ENV') == 'development':
            return jsonify({
                'success': False,
                'message': f'서버 오류: {error_message}',
                'error_type': error_type,
                'debug_info': {
                    'restaurant_id': restaurant_id,
                    'restaurant_name': restaurant_name,
                    'user_id': user_id,
                    'session_id': session_id,
                    'traceback': traceback.format_exc().split('\n')[-5:]
                }
            }), 500
        else:
            return jsonify({
                'success': False,
                'message': '서버 처리 중 오류가 발생했습니다.',
                'error_type': 'INTERNAL_ERROR'
            }), 500

    except Exception as e:
        logger.error(f"방문 예정 등록 API 오류: {e}")
        return jsonify({
            'success': False,
            'message': f'서버 오류가 발생했습니다: {str(e)}'
        }), 500

@main_bp.route('/api/restaurants/details/<restaurant_name>')
def get_restaurant_details(restaurant_name):
    """맛집 상세 정보 API"""
    try:
        if openai_service:
            details = openai_service.get_restaurant_details(restaurant_name)
            if details:
                return jsonify({
                    'success': True,
                    'restaurant': details
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '해당 맛집을 찾을 수 없습니다.'
                })
        else:
            return jsonify({
                'success': False,
                'error': 'AI 서비스를 사용할 수 없습니다.'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@main_bp.route('/status')
def status():
    """시스템 상태 상세 정보"""
    try:
        from app.models.restaurant import Restaurant
        from app.models.user import User
        from app.models.review import Review
        
        restaurant_count = Restaurant.query.count()
        user_count = User.query.count()
        review_count = Review.query.count()
        
        stats = {
            'restaurants': restaurant_count,
            'users': user_count,
            'reviews': review_count
        }
    except:
        stats = {
            'restaurants': 0,
            'users': 0,
            'reviews': 0
        }
    
    return jsonify({
        'service': 'FOODI',
        'status': 'operational',
        'last_updated': datetime.utcnow().isoformat(),
        'statistics': stats,
        'services': {
            'database': 'operational',
            'ai_service': 'operational',
            'map_service': 'operational'
        }
    })

def get_restaurant_count():
    """등록된 맛집 수 조회"""
    try:
        if openai_service:
            return len(openai_service.restaurant_database)
        from app.models.restaurant import Restaurant
        return Restaurant.query.count()
    except:
        return 50  # 기본값

def get_available_categories():
    """이용 가능한 카테고리 목록"""
    try:
        if openai_service:
            return list(set(r['category'] for r in openai_service.restaurant_database))
        from app.models.restaurant import Restaurant
        # 실제로는 DB에서 distinct 카테고리 조회
        return ['한식', '중식', '일식', '양식', '치킨', '피자', '카페', '분식', '술집']
    except:
        return ['한식', '중식', '일식', '양식', '카페']

# 에러 핸들러
@main_bp.errorhandler(404)
def not_found(error):
    """404 오류 처리"""
    return jsonify({
        'error': 'Page Not Found',
        'message': '요청하신 페이지를 찾을 수 없습니다.',
        'status_code': 404,
        'available_endpoints': [
            '/',
            '/chat',
            '/restaurants',
            '/reviews',
            '/health',
            '/about',
            '/api'
        ]
    }), 404

@main_bp.errorhandler(500)
def internal_error(error):
    """500 오류 처리"""
    return jsonify({
        'error': 'Internal Server Error',
        'message': '서버 내부 오류가 발생했습니다.',
        'status_code': 500
    }), 500
    
    
def analyze_and_recommend(message):
    """사용자 메시지를 분석하고 맛집을 추천"""
    
    # 메시지 분석
    analysis = analyze_user_intent(message)
    
    # 추천 맛집 생성
    restaurants = generate_recommendations(analysis)
    
    # 응답 메시지 생성
    response = generate_response_message(analysis, restaurants)
    
    return {
        'response': response,
        'restaurants': restaurants,
        'analysis': analysis
    }

def analyze_user_intent(message):
    """사용자 의도 분석"""
    message_lower = message.lower()
    
    analysis = {
        'category': None,
        'situation': None,
        'budget': None,
        'location': None,
        'preferences': [],
        'keywords': []
    }
    
    # 음식 카테고리 분석
    category_keywords = {
        '한식': ['한식', '한국', '갈비', '불고기', '삼겹살', '김치', '된장', '냉면', '비빔밥'],
        '중식': ['중식', '중국', '짜장면', '짬뽕', '탕수육', '마파두부', '양장피'],
        '일식': ['일식', '일본', '초밥', '라멘', '우동', '돈까스', '텐동', '사시미'],
        '양식': ['양식', '서양', '파스타', '스테이크', '피자', '햄버거', '샐러드', '리조또'],
        '치킨': ['치킨', '닭', '후라이드', '양념', '간장', '허니'],
        '피자': ['피자', '페퍼로니', '치즈', '콤비네이션'],
        '카페': ['카페', '커피', '라떼', '아메리카노', '디저트', '케이크', '빵'],
        '분식': ['분식', '떡볶이', '순대', '김밥', '라면', '어묵'],
        '술집': ['술집', '호프', '맥주', '소주', '안주', '치킨', '포차']
    }
    
    for category, keywords in category_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            analysis['category'] = category
            break
    
    # 상황 분석
    situation_keywords = {
        '가족': ['가족', '부모', '아이', '어린이', '온가족', '패밀리'],
        '데이트': ['데이트', '연인', '남친', '여친', '커플', '로맨틱', '분위기'],
        '친구': ['친구', '동료', '회사', '모임', '친구들과'],
        '혼밥': ['혼자', '혼밥', '1인', '개인'],
        '회식': ['회식', '야식', '술자리', '회사']
    }
    
    for situation, keywords in situation_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            analysis['situation'] = situation
            break
    
    # 예산 분석
    budget_keywords = {
        '저렴': ['저렴', '싸', '가성비', '만원', '학생', '가격'],
        '중간': ['적당', '보통', '중간'],
        '고급': ['고급', '비싸', '특별', '명품', '프리미엄']
    }
    
    for budget, keywords in budget_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            analysis['budget'] = budget
            break
    
    # 위치 분석
    location_keywords = {
        '성서': ['성서', '성서동', '성서역'],
        '월배': ['월배', '월배동'],
        '상인': ['상인', '상인동'],
        '감삼': ['감삼', '감삼동'],
        '본리': ['본리', '본리동'],
        '죽전': ['죽전', '죽전동']
    }
    
    for location, keywords in location_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            analysis['location'] = location
            break
    
    # 선호도 분석
    preference_keywords = {
        '매운': ['매운', '매워', '매콤', '불', '고추'],
        '달콤': ['달콤', '달', '단맛', '달달'],
        '담백': ['담백', '깔끔', '시원', '개운'],
        '진한': ['진한', '짙은', '깊은', '진짜'],
        '건강': ['건강', '다이어트', '샐러드', '채소']
    }
    
    for preference, keywords in preference_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            analysis['preferences'].append(preference)
    
    # 키워드 추출
    analysis['keywords'] = message_lower.split()
    
    return analysis

def generate_recommendations(analysis):
    """분석 결과를 바탕으로 맛집 추천"""
    
    # 샘플 맛집 데이터베이스 (실제로는 DB에서 조회)
    sample_restaurants = {
        '한식': [
            {
                'id': 1,
                'name': '한우마당',
                'category': '한식',
                'location': '성서동',
                'address': '대구 달서구 성서로 123',
                'rating': 4.2,
                'review_count': 128,
                'price_range': '중간',
                'description': '고품질 한우와 깔끔한 분위기의 한식당입니다. 가족 모임에 인기가 높아요.',
                'specialties': ['갈비탕', '불고기', '된장찌개'],
                'phone': '053-123-4567',
                'situation': ['가족', '회식'],
                'budget': '중간'
            },
            {
                'id': 2,
                'name': '할머니 손맛',
                'category': '한식',
                'location': '월배동',
                'address': '대구 달서구 월배로 456',
                'rating': 4.5,
                'review_count': 89,
                'price_range': '저렴',
                'description': '전통 한식의 진정한 맛을 느낄 수 있는 곳입니다.',
                'specialties': ['김치찌개', '제육볶음', '된장국'],
                'phone': '053-234-5678',
                'situation': ['혼밥', '친구'],
                'budget': '저렴'
            }
        ],
        '중식': [
            {
                'id': 3,
                'name': '차이나타운',
                'category': '중식',
                'location': '상인동',
                'address': '대구 달서구 상인로 789',
                'rating': 4.1,
                'review_count': 156,
                'price_range': '중간',
                'description': '정통 중화요리와 합리적인 가격의 중식당입니다.',
                'specialties': ['짜장면', '짬뽕', '탕수육'],
                'phone': '053-345-6789',
                'situation': ['친구', '가족'],
                'budget': '중간'
            }
        ],
        '일식': [
            {
                'id': 4,
                'name': '스시마스터',
                'category': '일식',
                'location': '감삼동',
                'address': '대구 달서구 감삼로 321',
                'rating': 4.6,
                'review_count': 73,
                'price_range': '고급',
                'description': '신선한 회와 정통 스시를 맛볼 수 있는 일식 전문점입니다.',
                'specialties': ['초밥', '사시미', '우동'],
                'phone': '053-456-7890',
                'situation': ['데이트', '회식'],
                'budget': '고급'
            }
        ],
        '양식': [
            {
                'id': 5,
                'name': '파스타팩토리',
                'category': '양식',
                'location': '본리동',
                'address': '대구 달서구 본리로 654',
                'rating': 4.4,
                'review_count': 92,
                'price_range': '중간',
                'description': '정통 이탈리안 파스타와 로맨틱한 분위기가 매력적인 곳입니다.',
                'specialties': ['파스타', '리조또', '스테이크'],
                'phone': '053-567-8901',
                'situation': ['데이트', '친구'],
                'budget': '중간'
            }
        ],
        '카페': [
            {
                'id': 6,
                'name': '원두마을',
                'category': '카페',
                'location': '죽전동',
                'address': '대구 달서구 죽전로 987',
                'rating': 4.3,
                'review_count': 205,
                'price_range': '저렴',
                'description': '넓은 공간과 좋은 커피, 작업하기에도 완벽한 카페입니다.',
                'specialties': ['아메리카노', '라떼', '디저트'],
                'phone': '053-678-9012',
                'situation': ['혼밥', '친구'],
                'budget': '저렴'
            }
        ]
    }
    
    # 추천 로직
    recommendations = []
    
    # 1. 카테고리 기반 추천
    if analysis['category']:
        if analysis['category'] in sample_restaurants:
            recommendations.extend(sample_restaurants[analysis['category']])
    
    # 2. 상황 기반 필터링
    if analysis['situation']:
        recommendations = [r for r in recommendations if analysis['situation'] in r.get('situation', [])]
    
    # 3. 예산 기반 필터링
    if analysis['budget']:
        recommendations = [r for r in recommendations if r.get('budget') == analysis['budget']]
    
    # 4. 위치 기반 필터링
    if analysis['location']:
        recommendations = [r for r in recommendations if analysis['location'] in r.get('location', '')]
    
    # 추천이 없으면 인기 맛집 추천
    if not recommendations:
        all_restaurants = []
        for category_restaurants in sample_restaurants.values():
            all_restaurants.extend(category_restaurants)
        recommendations = sorted(all_restaurants, key=lambda x: x['rating'], reverse=True)[:3]
    
    # 최대 3개까지 추천
    return recommendations[:3]

def generate_response_message(analysis, restaurants):
    """추천 결과에 대한 응답 메시지 생성"""
    
    if not restaurants:
        return "죄송합니다. 요청하신 조건에 맞는 맛집을 찾지 못했습니다. 다른 조건으로 다시 시도해보세요."
    
    # 분석 결과를 바탕으로 개인화된 메시지 생성
    message_parts = []
    
    # 인사말
    if analysis['situation']:
        situation_greetings = {
            '가족': '가족과 함께하는 시간을 위한',
            '데이트': '로맨틱한 데이트를 위한',
            '친구': '친구들과의 즐거운 시간을 위한',
            '혼밥': '혼자서도 편안하게 즐길 수 있는',
            '회식': '회식자리에 완벽한'
        }
        message_parts.append(situation_greetings.get(analysis['situation'], ''))
    
    if analysis['category']:
        message_parts.append(f"{analysis['category']} 맛집을")
    else:
        message_parts.append("맛집을")
    
    message_parts.append("추천해드릴게요! 🍽️")
    
    intro = " ".join(filter(None, message_parts))
    
    # 추천 이유 설명
    reasons = []
    if analysis['budget']:
        budget_messages = {
            '저렴': '가성비가 훌륭하고',
            '중간': '합리적인 가격대에',
            '고급': '특별한 날에 어울리는'
        }
        reasons.append(budget_messages.get(analysis['budget'], ''))
    
    if analysis['location']:
        reasons.append(f"{analysis['location']} 지역의")
    
    if analysis['preferences']:
        pref_messages = {
            '매운': '매콤한 맛이 일품인',
            '달콤': '달콤한 맛이 매력적인',
            '담백': '깔끔하고 담백한',
            '진한': '진한 맛이 특징인',
            '건강': '건강한 재료로 만든'
        }
        for pref in analysis['preferences']:
            if pref in pref_messages:
                reasons.append(pref_messages[pref])
    
    if reasons:
        reason_text = f"\n\n{', '.join(reasons)} 곳들로 선별했습니다."
    else:
        reason_text = f"\n\n평점과 리뷰를 바탕으로 엄선한 곳들입니다."
    
    return intro + reason_text

def get_restaurant_count():
    """등록된 맛집 수 조회"""
    try:
        from app.models.restaurant import Restaurant
        return Restaurant.query.count()
    except:
        return 50  # 기본값

def get_available_categories():
    """이용 가능한 카테고리 목록"""
    try:
        from app.models.restaurant import Restaurant
        # 실제로는 DB에서 distinct 카테고리 조회
        return ['한식', '중식', '일식', '양식', '치킨', '피자', '카페', '분식', '술집']
    except:
        return ['한식', '중식', '일식', '양식', '카페']