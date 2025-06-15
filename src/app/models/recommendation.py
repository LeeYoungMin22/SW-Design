# -*- coding: utf-8 -*-
"""
추천(Recommendation) 데이터 모델
AI 추천 이력, 사용자 질문, 추천 결과를 관리하는 SQLAlchemy 모델입니다.
"""

from datetime import datetime
#from app import db
from sqlalchemy.dialects.postgresql import JSON
from app.config.database import db
from sqlalchemy import Index
from sqlalchemy.orm import relationship
from app.config.database import db

class Recommendation(db.Model):
		"""
		AI 추천 기록을 저장하는 테이블
		사용자 질문, 추천 알고리즘 결과, 만족도 등을 관리합니다.
		"""
		
		__tablename__ = 'recommendations'
		
		# === 기본 정보 ===
		id = db.Column(db.Integer, primary_key=True, comment='추천 고유 ID')
		user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='사용자 ID')
		restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False, comment='추천된 식당 ID')
		session_id = db.Column(db.String(100), comment='채팅 세션 ID')
		
		# === 사용자 질문 정보 ===
		user_query = db.Column(db.Text, nullable=False, comment='사용자 원래 질문')
		processed_query = db.Column(db.Text, comment='전처리된 질문')
		query_intent = db.Column(db.String(50), comment='질문 의도 분류')
		extracted_preferences = db.Column(JSON, default=dict, comment='추출된 선호도 정보')
		
		# === 추천 알고리즘 정보 ===
		algorithm_version = db.Column(db.String(20), default='1.0', comment='사용된 알고리즘 버전')
		confidence_score = db.Column(db.Float, comment='추천 신뢰도 점수 (0.0-1.0)')
		ranking_score = db.Column(db.Float, comment='추천 순위 점수')
		recommendation_reason = db.Column(db.Text, comment='추천 이유 설명')
		
		# === 추천 컨텍스트 ===
		recommendation_factors = db.Column(JSON, default=dict, comment='추천에 영향을 준 요소들')
		alternative_suggestions = db.Column(JSON, default=list, comment='대안 추천 목록')
		
		# === 사용자 반응 ===
		user_feedback = db.Column(db.String(20), comment='사용자 피드백 (interested, not_interested, visited)')
		satisfaction_rating = db.Column(db.Integer, comment='만족도 평점 (1-5)')
		feedback_comment = db.Column(db.Text, comment='사용자 피드백 코멘트')
		status = db.Column(db.String(20), default='not-visited', comment='추천 상태 (not-visited, visited)')
		
		# === 결과 추적 ===
		was_clicked = db.Column(db.Boolean, default=False, comment='클릭 여부')
		was_visited = db.Column(db.Boolean, default=False, comment='실제 방문 여부')
		visit_confirmed_at = db.Column(db.DateTime, comment='방문 확인 시간')
		
		# === 시스템 메타데이터 ===
		ai_model_used = db.Column(db.String(50), comment='사용된 AI 모델명')
		processing_time = db.Column(db.Float, comment='추천 처리 시간 (초)')
		api_cost = db.Column(db.Float, comment='API 호출 비용')
		
		# === 시간 정보 ===
		created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='추천 생성 시간')
		clicked_at = db.Column(db.DateTime, comment='클릭 시간')
		feedback_at = db.Column(db.DateTime, comment='피드백 제공 시간')
		
		# === 인덱스 설정 ===
		__table_args__ = (
				Index('idx_recommendation_user', 'user_id'),
				Index('idx_recommendation_restaurant', 'restaurant_id'),
				Index('idx_recommendation_session', 'session_id'),
				Index('idx_recommendation_date', 'created_at'),
				Index('idx_recommendation_score', 'confidence_score'),
		)
		
		def __init__(self, user_id, restaurant_id, user_query, **kwargs):
				"""
				추천 인스턴스 초기화
				
				Args:
						user_id (int): 사용자 ID
						restaurant_id (int): 추천된 식당 ID
						user_query (str): 사용자 질문
						**kwargs: 추가 속성들
				"""
				self.user_id = user_id
				self.restaurant_id = restaurant_id
				self.user_query = user_query
				
				# 기본값 설정
				self.extracted_preferences = {}
				self.recommendation_factors = {}
				self.alternative_suggestions = []
				
				# 추가 속성 설정
				for key, value in kwargs.items():
						if hasattr(self, key):
								setattr(self, key, value)
		
		def to_dict(self, include_restaurant=True, include_user=False):
				"""
				추천 객체를 딕셔너리로 변환 (API 응답용)
				
				Args:
						include_restaurant (bool): 식당 정보 포함 여부
						include_user (bool): 사용자 정보 포함 여부
						
				Returns:
						dict: 추천 정보 딕셔너리
				"""
				result = {
						'id': self.id,
						'user_id': self.user_id,
						'restaurant_id': self.restaurant_id,
						'session_id': self.session_id,
						'query_info': {
								'original': self.user_query,
								'processed': self.processed_query,
								'intent': self.query_intent,
								'preferences': self.extracted_preferences or {}
						},
						'algorithm_info': {
								'version': self.algorithm_version,
								'confidence': self.confidence_score,
								'ranking_score': self.ranking_score,
								'reason': self.recommendation_reason
						},
						'factors': self.recommendation_factors or {},
						'alternatives': self.alternative_suggestions or [],
						'user_interaction': {
								'feedback': self.user_feedback,
								'satisfaction_rating': self.satisfaction_rating,
								'feedback_comment': self.feedback_comment,
								'was_clicked': self.was_clicked,
								'was_visited': self.was_visited
						},
						'metadata': {
								'ai_model': self.ai_model_used,
								'processing_time': self.processing_time,
								'created_at': self.created_at.isoformat() if self.created_at else None
						}
				}
				
				if include_restaurant and self.restaurant:
						result['restaurant'] = self.restaurant.to_dict()
				
				if include_user and self.user:
						result['user'] = {
								'username': self.user.username,
								'location': self.user.location
						}
				
				return result
		
		def record_click(self):
				"""
				사용자가 추천 결과를 클릭했을 때 기록
				"""
				self.was_clicked = True
				self.clicked_at = datetime.utcnow()
				db.session.commit()
		
		def record_visit(self, visited=True):
				"""
				실제 식당 방문 여부를 기록
				
				Args:
						visited (bool): 방문 여부
				"""
				self.was_visited = visited
				if visited:
						self.visit_confirmed_at = datetime.utcnow()
				db.session.commit()
		
		def record_feedback(self, feedback_type, rating=None, comment=None):
				"""
				사용자 피드백을 기록
				
				Args:
						feedback_type (str): 피드백 타입 (interested, not_interested, visited)
						rating (int, optional): 만족도 평점 (1-5)
						comment (str, optional): 추가 코멘트
				"""
				self.user_feedback = feedback_type
				self.satisfaction_rating = rating
				self.feedback_comment = comment
				self.feedback_at = datetime.utcnow()
				
				# 방문 피드백인 경우 방문 기록도 업데이트
				if feedback_type == 'visited':
						self.record_visit(True)
				
				db.session.commit()
		
		def calculate_success_score(self):
				"""
				추천의 성공도를 계산
				클릭률, 방문률, 만족도 등을 종합하여 점수화합니다.
				
				Returns:
						float: 성공 점수 (0.0 - 1.0)
				"""
				score = 0.0
				
				# 클릭 여부 (0.2점)
				if self.was_clicked:
						score += 0.2
				
				# 방문 여부 (0.4점)
				if self.was_visited:
						score += 0.4
				
				# 만족도 점수 (0.4점)
				if self.satisfaction_rating:
						score += (self.satisfaction_rating / 5.0) * 0.4
				
				return round(score, 2)
		
		def get_recommendation_summary(self):
				"""
				추천에 대한 요약 정보를 반환
				
				Returns:
						dict: 추천 요약 정보
				"""
				return {
						'restaurant_name': self.restaurant.name if self.restaurant else '알 수 없음',
						'reason': self.recommendation_reason or '맞춤 추천',
						'confidence': self.confidence_score,
						'user_query': self.user_query[:100] + '...' if len(self.user_query) > 100 else self.user_query,
						'success_score': self.calculate_success_score(),
						'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
				}
		
		def extract_query_keywords(self):
				"""
				사용자 질문에서 키워드를 추출하여 반환
				
				Returns:
						list: 추출된 키워드 목록
				"""
				if not self.user_query:
						return []
				
				# 간단한 키워드 추출 (실제로는 NLP 라이브러리 사용 권장)
				import re
				
				# 한글, 영문, 숫자만 추출
				text = re.sub(r'[^\w\s가-힣]', ' ', self.user_query)
				words = text.split()
				
				# 불용어 제거 및 의미있는 단어만 필터링
				stopwords = {'이', '가', '을', '를', '에', '에서', '으로', '로', '와', '과', '의', '은', '는'}
				keywords = [word for word in words if len(word) > 1 and word not in stopwords]
				
				return keywords[:10]  # 최대 10개까지
		
		def update_alternatives(self, alternative_restaurants):
				"""
				대안 추천 목록을 업데이트
				
				Args:
						alternative_restaurants (list): 대안 식당 정보 리스트
				"""
				self.alternative_suggestions = []
				
				for alt in alternative_restaurants:
						if isinstance(alt, dict):
								self.alternative_suggestions.append(alt)
						else:
								# Restaurant 객체인 경우
								self.alternative_suggestions.append({
										'id': alt.id,
										'name': alt.name,
										'category': alt.category,
										'rating': alt.rating_average,
										'distance': getattr(alt, 'distance', None)
								})
				
				db.session.commit()
		
		def is_recent(self, hours=24):
				"""
				최근 추천인지 확인
				
				Args:
						hours (int): 기준 시간 (시간 단위)
						
				Returns:
						bool: 최근 추천 여부
				"""
				if not self.created_at:
						return False
				
				from datetime import timedelta
				threshold = datetime.utcnow() - timedelta(hours=hours)
				return self.created_at > threshold
		
		def get_performance_metrics(self):
				"""
				이 추천의 성능 지표를 반환
				
				Returns:
						dict: 성능 지표 딕셔너리
				"""
				return {
						'confidence_score': self.confidence_score,
						'ranking_score': self.ranking_score,
						'click_through_rate': 1.0 if self.was_clicked else 0.0,
						'conversion_rate': 1.0 if self.was_visited else 0.0,
						'satisfaction_score': self.satisfaction_rating / 5.0 if self.satisfaction_rating else None,
						'success_score': self.calculate_success_score(),
						'processing_time': self.processing_time
				}
		
		def __repr__(self):
				"""객체의 문자열 표현"""
				return f'<Recommendation {self.id} for User {self.user_id}>'
		
		def __str__(self):
				"""사용자 친화적인 문자열 표현"""
				restaurant_name = self.restaurant.name if self.restaurant else '알 수 없음'
				return f'{restaurant_name} 추천 (신뢰도: {self.confidence_score:.2f})'