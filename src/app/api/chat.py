# -*- coding: utf-8 -*-
"""
채팅 API 엔드포인트
사용자와의 실시간 채팅 인터페이스를 제공하는 REST API입니다.
"""

import logging
from flask import Blueprint, request, jsonify
from app.services.chat_manager import ChatManager
from app.services.recommendation_engine import RecommendationEngine
from app.models.user import User
from app import db

logger = logging.getLogger(__name__)

# 블루프린트 생성
chat_bp = Blueprint('chat', __name__)

# 서비스 인스턴스 생성
chat_manager = ChatManager()
recommendation_engine = RecommendationEngine()

@chat_bp.route('/start', methods=['POST'])
def start_chat_session():
		"""
		새로운 채팅 세션을 시작합니다.
		
		Request Body:
				{
						"user_id": int (required),
						"context": dict (optional) - 추가 컨텍스트 정보
				}
		
		Returns:
				{
						"success": bool,
						"session_id": str,
						"welcome_message": str,
						"suggested_questions": list,
						"user_info": dict,
						"error": str (if error)
				}
		"""
		try:
				data = request.get_json()
				
				# 필수 파라미터 검증
				if not data or 'user_id' not in data:
						return jsonify({
								'success': False,
								'error': 'user_id는 필수 파라미터입니다.'
						}), 400
				
				user_id = data['user_id']
				context = data.get('context', {})
				
				# 사용자 존재 확인
				user = User.query.get(user_id)
				if not user:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 사용자입니다.'
						}), 404
				
				# 채팅 세션 시작
				result = chat_manager.start_new_chat_session(user_id)
				
				if result['success']:
						logger.info(f"새 채팅 세션 시작: 사용자 {user_id}, 세션 {result['session_id']}")
				
				return jsonify(result), 200 if result['success'] else 500
				
		except Exception as e:
				logger.error(f"채팅 세션 시작 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '서버 내부 오류가 발생했습니다.'
				}), 500

@chat_bp.route('/message', methods=['POST'])
def send_message():
		"""
		채팅 세션에 메시지를 전송합니다.
		
		Request Body:
				{
						"session_id": str (required),
						"message": str (required),
						"message_type": str (optional, default: "text")
				}
		
		Returns:
				{
						"success": bool,
						"message": str,
						"message_type": str,
						"recommendations": list (if applicable),
						"suggestions": list,
						"session_info": dict,
						"error": str (if error)
				}
		"""
		try:
				data = request.get_json()
				
				# 필수 파라미터 검증
				required_fields = ['session_id', 'message']
				for field in required_fields:
						if not data or field not in data:
								return jsonify({
										'success': False,
										'error': f'{field}는 필수 파라미터입니다.'
								}), 400
				
				session_id = data['session_id']
				message = data['message'].strip()
				message_type = data.get('message_type', 'text')
				
				# 메시지 길이 검증
				if not message:
						return jsonify({
								'success': False,
								'error': '메시지 내용이 비어있습니다.'
						}), 400
				
				if len(message) > 1000:
						return jsonify({
								'success': False,
								'error': '메시지가 너무 깁니다. (최대 1000자)'
						}), 400
				
				# 메시지 처리
				result = chat_manager.process_user_message(session_id, message, message_type)
				
				if result['success']:
						logger.info(f"메시지 처리 완료: 세션 {session_id}")
				
				return jsonify(result), 200 if result['success'] else 400
				
		except Exception as e:
				logger.error(f"메시지 처리 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '메시지 처리 중 오류가 발생했습니다.'
				}), 500

@chat_bp.route('/history/<session_id>', methods=['GET'])
def get_chat_history(session_id):
		"""
		채팅 세션의 대화 이력을 조회합니다.
		
		Query Parameters:
				limit: int (optional, default: 20) - 조회할 메시지 수
		
		Returns:
				{
						"success": bool,
						"history": list,
						"session_info": dict,
						"error": str (if error)
				}
		"""
		try:
				limit = request.args.get('limit', 20, type=int)
				
				# limit 범위 검증
				if limit < 1 or limit > 100:
						return jsonify({
								'success': False,
								'error': 'limit은 1-100 사이의 값이어야 합니다.'
						}), 400
				
				# 대화 이력 조회
				history = chat_manager.get_chat_history(session_id, limit)
				
				# 세션 정보 조회
				session_info = chat_manager.session_manager.get_session(session_id)
				
				if session_info is None:
						return jsonify({
								'success': False,
								'error': '존재하지 않거나 만료된 세션입니다.'
						}), 404
				
				return jsonify({
						'success': True,
						'history': history,
						'session_info': {
								'session_id': session_id,
								'created_at': session_info.get('created_at'),
								'message_count': len(history),
								'state': session_info.get('state')
						}
				}), 200
				
		except Exception as e:
				logger.error(f"채팅 이력 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '채팅 이력 조회 중 오류가 발생했습니다.'
				}), 500

@chat_bp.route('/end', methods=['POST'])
def end_chat_session():
		"""
		채팅 세션을 종료합니다.
		
		Request Body:
				{
						"session_id": str (required)
				}
		
		Returns:
				{
						"success": bool,
						"farewell_message": str,
						"session_stats": dict,
						"error": str (if error)
				}
		"""
		try:
				data = request.get_json()
				
				if not data or 'session_id' not in data:
						return jsonify({
								'success': False,
								'error': 'session_id는 필수 파라미터입니다.'
						}), 400
				
				session_id = data['session_id']
				
				# 세션 종료
				result = chat_manager.end_chat_session(session_id)
				
				if result['success']:
						logger.info(f"채팅 세션 종료: {session_id}")
				
				return jsonify(result), 200 if result['success'] else 400
				
		except Exception as e:
				logger.error(f"채팅 세션 종료 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '세션 종료 중 오류가 발생했습니다.'
				}), 500

@chat_bp.route('/suggestions', methods=['GET'])
def get_suggested_questions():
		"""
		사용자를 위한 질문 예제들을 반환합니다.
		
		Query Parameters:
				user_id: int (optional) - 개인화된 질문을 위한 사용자 ID
				category: str (optional) - 특정 카테고리의 질문들
		
		Returns:
				{
						"success": bool,
						"suggestions": list,
						"categories": dict,
						"error": str (if error)
				}
		"""
		try:
				user_id = request.args.get('user_id', type=int)
				category = request.args.get('category')
				
				# 기본 예제 질문들
				all_suggestions = chat_manager.example_questions
				
				if category and category in all_suggestions:
						# 특정 카테고리의 질문들
						suggestions = all_suggestions[category]
				else:
						# 모든 카테고리에서 섞어서
						suggestions = []
						for questions in all_suggestions.values():
								suggestions.extend(questions[:2])  # 각 카테고리에서 2개씩
				
				# 사용자별 개인화 (선택사항)
				if user_id:
						user = User.query.get(user_id)
						if user:
								# 사용자 선호도 기반 추가 질문들
								personalized = chat_manager._get_suggested_questions(user)
								suggestions = personalized + suggestions[:4]  # 개인화 + 기본 4개
				
				# 중복 제거 및 최대 8개로 제한
				unique_suggestions = list(dict.fromkeys(suggestions))[:8]
				
				return jsonify({
						'success': True,
						'suggestions': unique_suggestions,
						'categories': list(all_suggestions.keys())
				}), 200
				
		except Exception as e:
				logger.error(f"질문 예제 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '질문 예제 조회 중 오류가 발생했습니다.'
				}), 500

@chat_bp.route('/feedback', methods=['POST'])
def submit_chat_feedback():
		"""
		채팅 경험에 대한 피드백을 제출합니다.
		
		Request Body:
				{
						"session_id": str (required),
						"rating": int (required, 1-5),
						"feedback_type": str (required),
						"comment": str (optional),
						"improvement_areas": list (optional)
				}
		
		Returns:
				{
						"success": bool,
						"message": str,
						"error": str (if error)
				}
		"""
		try:
				data = request.get_json()
				
				# 필수 파라미터 검증
				required_fields = ['session_id', 'rating', 'feedback_type']
				for field in required_fields:
						if not data or field not in data:
								return jsonify({
										'success': False,
										'error': f'{field}는 필수 파라미터입니다.'
								}), 400
				
				session_id = data['session_id']
				rating = data['rating']
				feedback_type = data['feedback_type']
				comment = data.get('comment', '')
				improvement_areas = data.get('improvement_areas', [])
				
				# 평점 범위 검증
				if not isinstance(rating, int) or rating < 1 or rating > 5:
						return jsonify({
								'success': False,
								'error': '평점은 1-5 사이의 정수여야 합니다.'
						}), 400
				
				# 피드백 타입 검증
				valid_feedback_types = ['positive', 'negative', 'suggestion', 'bug_report']
				if feedback_type not in valid_feedback_types:
						return jsonify({
								'success': False,
								'error': f'feedback_type은 다음 중 하나여야 합니다: {valid_feedback_types}'
						}), 400
				
				# 세션 존재 확인
				session_info = chat_manager.session_manager.get_session(session_id)
				if not session_info:
						return jsonify({
								'success': False,
								'error': '존재하지 않거나 만료된 세션입니다.'
						}), 404
				
				# 피드백 정보를 세션에 저장
				feedback_data = {
						'rating': rating,
						'feedback_type': feedback_type,
						'comment': comment,
						'improvement_areas': improvement_areas,
						'submitted_at': chat_manager.session_manager.datetime.utcnow().isoformat()
				}
				
				# 세션 컨텍스트 업데이트
				chat_manager.session_manager.update_session_context(
						session_id, 'user_feedback', feedback_data
				)
				
				logger.info(f"채팅 피드백 제출: 세션 {session_id}, 평점 {rating}")
				
				return jsonify({
						'success': True,
						'message': '피드백이 성공적으로 제출되었습니다. 감사합니다!'
				}), 200
				
		except Exception as e:
				logger.error(f"채팅 피드백 제출 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '피드백 제출 중 오류가 발생했습니다.'
				}), 500

@chat_bp.route('/status/<session_id>', methods=['GET'])
def get_session_status(session_id):
		"""
		채팅 세션의 현재 상태를 조회합니다.
		
		Returns:
				{
						"success": bool,
						"session_active": bool,
						"session_info": dict,
						"error": str (if error)
				}
		"""
		try:
				# 세션 정보 조회
				session_info = chat_manager.session_manager.get_session(session_id)
				
				if session_info:
						return jsonify({
								'success': True,
								'session_active': True,
								'session_info': {
										'session_id': session_id,
										'user_id': session_info.get('user_id'),
										'state': session_info.get('state'),
										'created_at': session_info.get('created_at'),
										'last_activity': session_info.get('last_activity'),
										'message_count': session_info.get('message_count', 0),
										'recommendations_given': session_info.get('recommendations_given', 0)
								}
						}), 200
				else:
						return jsonify({
								'success': True,
								'session_active': False,
								'session_info': None
						}), 200
						
		except Exception as e:
				logger.error(f"세션 상태 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '세션 상태 조회 중 오류가 발생했습니다.'
				}), 500

# 에러 핸들러
@chat_bp.errorhandler(400)
def bad_request(error):
		"""잘못된 요청 에러 핸들러"""
		return jsonify({
				'success': False,
				'error': '잘못된 요청입니다.',
				'status_code': 400
		}), 400

@chat_bp.errorhandler(404)
def not_found(error):
		"""리소스를 찾을 수 없음 에러 핸들러"""
		return jsonify({
				'success': False,
				'error': '요청한 리소스를 찾을 수 없습니다.',
				'status_code': 404
		}), 404

@chat_bp.errorhandler(500)
def internal_error(error):
		"""내부 서버 에러 핸들러"""
		return jsonify({
				'success': False,
				'error': '서버 내부 오류가 발생했습니다.',
				'status_code': 500
		}), 500