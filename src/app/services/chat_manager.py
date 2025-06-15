# -*- coding: utf-8 -*-
"""
채팅 관리 서비스 (ChatManager)
사용자와의 대화 흐름을 제어하고 예제 질문 출력, 세션 관리를 담당합니다.
"""

import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from app import db
from app.models.user import User
from app.utils.session_manager import SessionManager
from app.services.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)

class ChatManager:
		"""
		채팅 세션과 대화 흐름을 관리하는 서비스 클래스
		사용자 입력 처리, 예제 질문 제공, 대화 컨텍스트 유지를 담당합니다.
		"""
		
		def __init__(self):
				"""
				채팅 매니저 초기화
				세션 매니저와 추천 엔진을 설정합니다.
				"""
				self.session_manager = SessionManager()
				self.recommendation_engine = RecommendationEngine()
				
				# 예제 질문들 (카테고리별로 분류)
				self.example_questions = {
						"기본_추천": [
								"오늘 점심 뭐 먹을까요?",
								"2만원 이하로 맛있는 곳 알려주세요",
								"혼밥하기 좋은 곳 추천해주세요",
								"가족끼리 가기 좋은 식당 찾아주세요"
						],
						"음식_종류": [
								"매운 음식 추천해주세요",
								"한식당 중에 맛있는 곳 어디인가요?",
								"고기 먹을 수 있는 곳 알려주세요",
								"중식당 추천 부탁드려요"
						],
						"특별_상황": [
								"데이트하기 좋은 분위기 있는 곳",
								"회식 장소로 좋은 곳 추천해주세요",
								"주차 가능한 식당 찾아주세요",
								"배달 가능한 곳 알려주세요"
						],
						"위치_기반": [
								"성서공단 근처 맛집 알려주세요",
								"월성동 맛집 추천해주세요",
								"용산동에서 가까운 식당 찾아주세요"
						]
				}
				
				# 대화 상태 관리
				self.conversation_states = {
						'GREETING': '인사',
						'ASKING': '질문_접수',
						'RECOMMENDING': '추천_진행',
						'CLARIFYING': '추가_정보_요청',
						'FEEDBACK': '피드백_수집',
						'ENDING': '대화_종료'
				}
		
		def start_new_chat_session(self, user_id: int) -> Dict[str, Any]:
				"""
				새로운 채팅 세션을 시작합니다.
				
				Args:
						user_id (int): 사용자 ID
						
				Returns:
						Dict[str, Any]: 세션 정보와 환영 메시지
				"""
				try:
						# 사용자 정보 조회
						user = User.query.get(user_id)
						if not user:
								raise ValueError(f"사용자를 찾을 수 없습니다: {user_id}")
						
						# 새 세션 ID 생성
						session_id = str(uuid.uuid4())
						
						# 세션 데이터 초기화
						session_data = {
								'user_id': user_id,
								'session_id': session_id,
								'start_time': datetime.utcnow().isoformat(),
								'state': self.conversation_states['GREETING'],
								'message_count': 0,
								'recommendations_given': 0,
								'user_preferences': user.food_preferences or {},
								'conversation_history': []
						}
						
						# 세션 저장
						self.session_manager.create_session(session_id, session_data)
						
						# 사용자 정보 업데이트
						user.update_session(session_id, session_data)
						
						# 환영 메시지 생성
						welcome_message = self._generate_welcome_message(user)
						
						# 예제 질문 선별
						suggested_questions = self._get_suggested_questions(user)
						
						logger.info(f"새로운 채팅 세션 시작: 사용자 {user_id}, 세션 {session_id}")
						
						return {
								'success': True,
								'session_id': session_id,
								'welcome_message': welcome_message,
								'suggested_questions': suggested_questions,
								'user_info': {
										'username': user.username,
										'location': user.location,
										'is_returning_user': user.last_login is not None
								}
						}
						
				except Exception as e:
						logger.error(f"채팅 세션 시작 중 오류 발생: {e}")
						return {
								'success': False,
								'error': str(e),
								'welcome_message': '안녕하세요! FOODI입니다. 무엇을 도와드릴까요?',
								'suggested_questions': self.example_questions['기본_추천'][:3]
						}
		
		def process_user_message(self, 
														session_id: str, 
														user_message: str,
														message_type: str = 'text') -> Dict[str, Any]:
				"""
				사용자 메시지를 처리하고 적절한 응답을 생성합니다.
				
				Args:
						session_id (str): 채팅 세션 ID
						user_message (str): 사용자 메시지
						message_type (str): 메시지 타입 ('text', 'quick_reply' 등)
						
				Returns:
						Dict[str, Any]: 처리 결과와 응답
				"""
				try:
						# 세션 정보 조회
						session_data = self.session_manager.get_session(session_id)
						if not session_data:
								return self._handle_invalid_session()
						
						user_id = session_data['user_id']
						current_state = session_data.get('state', self.conversation_states['ASKING'])
						
						# 메시지 이력에 추가
						self._add_message_to_history(session_data, 'user', user_message)
						
						# 메시지 전처리
						processed_message = self._preprocess_message(user_message)
						
						# 의도 분석
						intent = self._analyze_message_intent(processed_message, session_data)
						
						# 상태별 처리
						response = self._handle_message_by_state(
								current_state, processed_message, intent, session_data
						)
						
						# 세션 상태 업데이트
						session_data['message_count'] += 1
						session_data['last_activity'] = datetime.utcnow().isoformat()
						
						# 응답을 이력에 추가
						self._add_message_to_history(session_data, 'assistant', response['message'])
						
						# 세션 저장
						self.session_manager.update_session(session_id, session_data)
						
						logger.info(f"메시지 처리 완료: 세션 {session_id}, 의도 {intent}")
						
						return response
						
				except Exception as e:
						logger.error(f"메시지 처리 중 오류 발생: {e}")
						return {
								'success': False,
								'message': '죄송합니다. 메시지 처리 중 오류가 발생했습니다. 다시 시도해주세요.',
								'error': str(e),
								'suggestions': ['다시 질문하기', '처음으로 돌아가기']
						}
		
		def get_chat_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
				"""
				채팅 세션의 대화 이력을 조회합니다.
				
				Args:
						session_id (str): 채팅 세션 ID
						limit (int): 조회할 최대 메시지 수
						
				Returns:
						List[Dict[str, Any]]: 대화 이력 리스트
				"""
				try:
						session_data = self.session_manager.get_session(session_id)
						if not session_data:
								return []
						
						history = session_data.get('conversation_history', [])
						
						# 최신 메시지부터 limit 개수만큼 반환
						return history[-limit:] if len(history) > limit else history
						
				except Exception as e:
						logger.error(f"채팅 이력 조회 중 오류 발생: {e}")
						return []
		
		def end_chat_session(self, session_id: str) -> Dict[str, Any]:
				"""
				채팅 세션을 종료합니다.
				
				Args:
						session_id (str): 종료할 세션 ID
						
				Returns:
						Dict[str, Any]: 종료 결과
				"""
				try:
						session_data = self.session_manager.get_session(session_id)
						if not session_data:
								return {'success': False, 'error': '세션을 찾을 수 없습니다.'}
						
						# 세션 통계 계산
						start_time = datetime.fromisoformat(session_data['start_time'])
						end_time = datetime.utcnow()
						duration = (end_time - start_time).total_seconds()
						
						session_stats = {
								'duration_seconds': duration,
								'message_count': session_data.get('message_count', 0),
								'recommendations_given': session_data.get('recommendations_given', 0),
								'end_time': end_time.isoformat()
						}
						
						# 종료 메시지 생성
						farewell_message = self._generate_farewell_message(session_stats)
						
						# 세션 데이터에 통계 추가
						session_data.update(session_stats)
						session_data['state'] = self.conversation_states['ENDING']
						
						# 최종 세션 저장
						self.session_manager.update_session(session_id, session_data)
						
						# 일정 시간 후 세션 삭제 (옵션)
						# self.session_manager.schedule_session_cleanup(session_id, delay_minutes=60)
						
						logger.info(f"채팅 세션 종료: {session_id}, 지속시간: {duration:.1f}초")
						
						return {
								'success': True,
								'farewell_message': farewell_message,
								'session_stats': session_stats
						}
						
				except Exception as e:
						logger.error(f"세션 종료 중 오류 발생: {e}")
						return {
								'success': False,
								'error': str(e),
								'farewell_message': '감사합니다. 또 방문해주세요!'
						}
		
		def _generate_welcome_message(self, user: User) -> str:
				"""
				사용자에게 맞춤화된 환영 메시지를 생성합니다.
				
				Args:
						user (User): 사용자 객체
						
				Returns:
						str: 환영 메시지
				"""
				current_hour = datetime.now().hour
				
				# 시간대별 인사말
				if 5 <= current_hour < 12:
						time_greeting = "좋은 아침이에요"
				elif 12 <= current_hour < 18:
						time_greeting = "좋은 오후에요"
				else:
						time_greeting = "좋은 저녁이에요"
				
				# 재방문 사용자 체크
				if user.last_login and user.last_login > (datetime.utcnow() - timedelta(days=30)):
						welcome_msg = f"{time_greeting}, {user.username}님! 😊\n다시 만나서 반가워요."
				else:
						welcome_msg = f"{time_greeting}! FOODI에 오신 것을 환영해요! 😊"
				
				# 위치 기반 메시지 추가
				if user.location:
						location_msg = f"\n{user.location} 지역의 맛집을 찾아드릴게요!"
				else:
						location_msg = "\n대구 달서구 지역의 맛집을 찾아드릴게요!"
				
				# 도움말 메시지
				help_msg = ("\n\n🍽️ 어떤 음식이 드시고 싶으신가요?\n"
										"예산, 음식 종류, 인원 수 등을 알려주시면 "
										"더 정확한 추천을 드릴 수 있어요!")
				
				return welcome_msg + location_msg + help_msg
		
		def _get_suggested_questions(self, user: User) -> List[str]:
				"""
				사용자에게 맞는 질문 예제들을 선별하여 반환합니다.
				
				Args:
						user (User): 사용자 객체
						
				Returns:
						List[str]: 추천 질문 리스트
				"""
				suggestions = []
				
				# 사용자 선호도 기반 질문 추가
				preferences = user.food_preferences or {}
				favorite_cuisines = preferences.get('favorite_cuisines', [])
				
				if favorite_cuisines:
						# 선호 요리 종류 기반 질문
						for cuisine_info in favorite_cuisines[:2]:
								if isinstance(cuisine_info, dict):
										cuisine = cuisine_info.get('type', '')
										suggestions.append(f"{cuisine} 맛집 추천해주세요")
				
				# 기본 질문들에서 무작위 선택
				import random
				
				# 각 카테고리에서 1개씩
				for category, questions in self.example_questions.items():
						if len(suggestions) < 6:  # 최대 6개까지
								suggestions.append(random.choice(questions))
				
				# 중복 제거 및 섞기
				unique_suggestions = list(set(suggestions))
				random.shuffle(unique_suggestions)
				
				return unique_suggestions[:4]  # 최대 4개 반환
		
		def _preprocess_message(self, message: str) -> str:
				"""
				사용자 메시지를 전처리합니다.
				
				Args:
						message (str): 원본 메시지
						
				Returns:
						str: 전처리된 메시지
				"""
				# 공백 정리
				processed = message.strip()
				
				# 특수문자 정리 (필요한 경우)
				import re
				processed = re.sub(r'[^\w\s가-힣]', ' ', processed)
				processed = re.sub(r'\s+', ' ', processed).strip()
				
				return processed
		
		def _analyze_message_intent(self, 
															message: str, 
															session_data: Dict[str, Any]) -> str:
				"""
				메시지의 의도를 분석합니다.
				
				Args:
						message (str): 사용자 메시지
						session_data (Dict[str, Any]): 세션 데이터
						
				Returns:
						str: 분석된 의도
				"""
				message_lower = message.lower()
				
				# 기본적인 의도 분류
				if any(word in message_lower for word in ['안녕', '처음', '시작']):
						return 'greeting'
				elif any(word in message_lower for word in ['추천', '맛집', '음식', '먹을']):
						return 'restaurant_request'
				elif any(word in message_lower for word in ['리뷰', '후기', '평가']):
						return 'review_related'
				elif any(word in message_lower for word in ['감사', '고마워', '좋아', '만족']):
						return 'positive_feedback'
				elif any(word in message_lower for word in ['아니', '싫어', '별로', '다른']):
						return 'negative_feedback'
				elif any(word in message_lower for word in ['도움', '사용법', '어떻게']):
						return 'help_request'
				elif any(word in message_lower for word in ['끝', '종료', '그만', '바이']):
						return 'end_conversation'
				else:
						return 'restaurant_request'  # 기본값
		
		def _handle_message_by_state(self, 
																current_state: str,
																message: str,
																intent: str,
																session_data: Dict[str, Any]) -> Dict[str, Any]:
				"""
				현재 상태와 의도에 따라 메시지를 처리합니다.
				
				Args:
						current_state (str): 현재 대화 상태
						message (str): 사용자 메시지
						intent (str): 메시지 의도
						session_data (Dict[str, Any]): 세션 데이터
						
				Returns:
						Dict[str, Any]: 처리 결과
				"""
				if intent == 'restaurant_request':
						return self._handle_restaurant_request(message, session_data)
				elif intent == 'positive_feedback':
						return self._handle_positive_feedback(message, session_data)
				elif intent == 'negative_feedback':
						return self._handle_negative_feedback(message, session_data)
				elif intent == 'help_request':
						return self._handle_help_request(session_data)
				elif intent == 'end_conversation':
						return self._handle_end_request(session_data)
				else:
						# 기본 처리: 식당 추천 요청으로 간주
						return self._handle_restaurant_request(message, session_data)
		
		def _handle_restaurant_request(self, 
																	message: str, 
																	session_data: Dict[str, Any]) -> Dict[str, Any]:
				"""
				식당 추천 요청을 처리합니다.
				
				Args:
						message (str): 사용자 메시지
						session_data (Dict[str, Any]): 세션 데이터
						
				Returns:
						Dict[str, Any]: 추천 결과
				"""
				try:
						user_id = session_data['user_id']
						session_id = session_data['session_id']
						
						# 추천 엔진을 통해 맛집 추천 요청
						recommendation_result = self.recommendation_engine.get_recommendations(
								user_id=user_id,
								user_query=message,
								session_id=session_id,
								max_results=5
						)
						
						if recommendation_result['success']:
								# 추천 개수 증가
								session_data['recommendations_given'] += 1
								session_data['state'] = self.conversation_states['RECOMMENDING']
								
								return {
										'success': True,
										'message': recommendation_result['ai_response'],
										'recommendations': recommendation_result['recommendations'],
										'suggestions': ['다른 조건으로 검색', '더 자세한 정보', '리뷰 보기'],
										'message_type': 'recommendation'
								}
						else:
								return {
										'success': False,
										'message': recommendation_result.get('ai_response', '추천을 찾지 못했습니다.'),
										'suggestions': ['다시 질문하기', '조건 바꿔서 검색'],
										'message_type': 'error'
								}
								
				except Exception as e:
						logger.error(f"식당 추천 처리 중 오류 발생: {e}")
						return {
								'success': False,
								'message': '죄송합니다. 추천을 처리하는 중 오류가 발생했습니다.',
								'suggestions': ['다시 시도하기'],
								'message_type': 'error'
						}