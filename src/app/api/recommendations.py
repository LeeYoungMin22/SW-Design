# -*- coding: utf-8 -*-
"""
추천 API 엔드포인트
맛집 추천 및 추천 이력 관리를 위한 REST API입니다.
"""

import logging
from flask import Blueprint, request, jsonify
from app.models.recommendation import Recommendation
from app.models.user import User
from app.models.restaurant import Restaurant
from app.services.recommendation_engine import RecommendationEngine
from app.services.database_manager import DatabaseManager
from app import db

logger = logging.getLogger(__name__)

# 블루프린트 생성
recommendations_bp = Blueprint('recommendations', __name__)

# 서비스 인스턴스 생성
recommendation_engine = RecommendationEngine()
db_manager = DatabaseManager()

@recommendations_bp.route('/', methods=['POST'])
def get_recommendations():
		"""
		사용자 질문에 대한 맛집 추천을 생성합니다.
		
		Request Body:
				{
						"user_id": int (required),
						"query": str (required),
						"session_id": str (optional),
						"max_results": int (optional, default: 5),
						"filters": dict (optional)
				}
		
		Returns:
				{
						"success": bool,
						"recommendations": list,
						"ai_response": str,
						"query_analysis": dict,
						"metadata": dict,
						"error": str (if error)
				}
		"""
		try:
				data = request.get_json()
				
				# 필수 파라미터 검증
				if not data or 'user_id' not in data or 'query' not in data:
						return jsonify({
								'success': False,
								'error': 'user_id와 query는 필수 파라미터입니다.'
						}), 400
				
				user_id = data['user_id']
				query = data['query'].strip()
				session_id = data.get('session_id')
				max_results = min(data.get('max_results', 5), 10)  # 최대 10개로 제한
				filters = data.get('filters', {})
				
				# 사용자 존재 확인
				user = User.query.get(user_id)
				if not user:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 사용자입니다.'
						}), 404
				
				# 질문 길이 검증
				if not query or len(query) < 3:
						return jsonify({
								'success': False,
								'error': '질문은 최소 3자 이상이어야 합니다.'
						}), 400
				
				if len(query) > 500:
						return jsonify({
								'success': False,
								'error': '질문이 너무 깁니다. (최대 500자)'
						}), 400
				
				# 추천 생성
				result = recommendation_engine.get_recommendations(
						user_id=user_id,
						user_query=query,
						session_id=session_id,
						max_results=max_results
				)
				
				if result['success']:
						logger.info(f"추천 생성 완료: 사용자 {user_id}, {len(result['recommendations'])}개 식당")
				
				return jsonify(result), 200 if result['success'] else 500
				
		except Exception as e:
				logger.error(f"추천 생성 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '추천 생성 중 오류가 발생했습니다.'
				}), 500

@recommendations_bp.route('/history/<int:user_id>', methods=['GET'])
def get_recommendation_history(user_id):
		"""
		사용자의 추천 이력을 조회합니다.
		
		Query Parameters:
				limit: int (optional, default: 20) - 조회할 최대 개수
				include_restaurants: bool (optional, default: true) - 식당 정보 포함 여부
		
		Returns:
				{
						"success": bool,
						"recommendations": list,
						"user_info": dict,
						"statistics": dict,
						"error": str (if error)
				}
		"""
		try:
				limit = min(request.args.get('limit', 20, type=int), 100)
				include_restaurants = request.args.get('include_restaurants', 'true').lower() == 'true'
				
				# 사용자 존재 확인
				user = User.query.get(user_id)
				if not user:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 사용자입니다.'
						}), 404
				
				# 추천 이력 조회
				recommendations = db_manager.get_user_recommendation_history(
						user_id, limit, include_restaurants
				)
				
				# 사용자 추천 통계 계산
				total_recommendations = Recommendation.query.filter_by(user_id=user_id).count()
				successful_visits = Recommendation.query.filter_by(
						user_id=user_id, was_visited=True
				).count()
				
				statistics = {
						'total_recommendations': total_recommendations,
						'successful_visits': successful_visits,
						'visit_rate': (successful_visits / total_recommendations * 100) 
													if total_recommendations > 0 else 0,
						'favorite_categories': user.get_favorite_categories() if hasattr(user, 'get_favorite_categories') else []
				}
				
				return jsonify({
						'success': True,
						'recommendations': recommendations,
						'user_info': {
								'user_id': user_id,
								'username': user.username,
								'location': user.location
						},
						'statistics': statistics
				}), 200
				
		except Exception as e:
				logger.error(f"추천 이력 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '추천 이력 조회 중 오류가 발생했습니다.'
				}), 500

@recommendations_bp.route('/<int:recommendation_id>/feedback', methods=['POST'])
def submit_recommendation_feedback(recommendation_id):
		"""
		추천에 대한 사용자 피드백을 제출합니다.
		
		Request Body:
				{
						"feedback_type": str (required) - 'interested', 'not_interested', 'visited'
						"rating": int (optional, 1-5) - 만족도 평점
						"comment": str (optional) - 추가 코멘트
						"was_visited": bool (optional) - 실제 방문 여부
				}
		
		Returns:
				{
						"success": bool,
						"message": str,
						"updated_recommendation": dict,
						"error": str (if error)
				}
		"""
		try:
				data = request.get_json()
				
				if not data or 'feedback_type' not in data:
						return jsonify({
								'success': False,
								'error': 'feedback_type은 필수 파라미터입니다.'
						}), 400
				
				feedback_type = data['feedback_type']
				rating = data.get('rating')
				comment = data.get('comment')
				was_visited = data.get('was_visited')
				
				# 피드백 타입 검증
				valid_feedback_types = ['interested', 'not_interested', 'visited']
				if feedback_type not in valid_feedback_types:
						return jsonify({
								'success': False,
								'error': f'feedback_type은 다음 중 하나여야 합니다: {valid_feedback_types}'
						}), 400
				
				# 평점 검증 (있는 경우)
				if rating is not None and (not isinstance(rating, int) or rating < 1 or rating > 5):
						return jsonify({
								'success': False,
								'error': '평점은 1-5 사이의 정수여야 합니다.'
						}), 400
				
				# 추천 존재 확인
				recommendation = Recommendation.query.get(recommendation_id)
				if not recommendation:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 추천입니다.'
						}), 404
				
				# 피드백 데이터 구성
				feedback_data = {
						'feedback_type': feedback_type,
						'rating': rating,
						'comment': comment
				}
				
				if was_visited is not None:
						feedback_data['was_visited'] = was_visited
				
				# 피드백 업데이트
				result = db_manager.update_recommendation_feedback(recommendation_id, feedback_data)
				
				if result['success']:
						# 사용자 선호도 업데이트 (긍정적 피드백인 경우)
						if feedback_type in ['interested', 'visited'] and recommendation.restaurant:
								recommendation_engine.update_user_preferences(
										recommendation.user_id, 
										{'liked_restaurant': recommendation.restaurant_id}
								)
						
						logger.info(f"추천 피드백 제출: 추천 {recommendation_id}, 타입 {feedback_type}")
						
						return jsonify({
								'success': True,
								'message': '피드백이 성공적으로 제출되었습니다.',
								'updated_recommendation': recommendation.to_dict()
						}), 200
				else:
						return jsonify(result), 400
				
		except Exception as e:
				logger.error(f"추천 피드백 제출 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '피드백 제출 중 오류가 발생했습니다.'
				}), 500

@recommendations_bp.route('/similar/<int:restaurant_id>', methods=['GET'])
def get_similar_restaurants(restaurant_id):
		"""
		특정 식당과 유사한 식당들을 추천합니다.
		
		Query Parameters:
				limit: int (optional, default: 5) - 추천할 식당 수
		
		Returns:
				{
						"success": bool,
						"base_restaurant": dict,
						"similar_restaurants": list,
						"similarity_criteria": list,
						"error": str (if error)
				}
		"""
		try:
				limit = min(request.args.get('limit', 5, type=int), 10)
				
				# 기준 식당 존재 확인
				base_restaurant = Restaurant.query.get(restaurant_id)
				if not base_restaurant or not base_restaurant.is_active:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 식당입니다.'
						}), 404
				
				# 유사한 식당들 조회
				similar_restaurants = recommendation_engine.get_similar_restaurants(restaurant_id, limit)
				
				# 유사도 기준 설명
				similarity_criteria = [
						"같은 카테고리의 식당",
						"비슷한 가격대",
						"유사한 평점",
						"같은 지역",
						"비슷한 분위기와 특징"
				]
				
				return jsonify({
						'success': True,
						'base_restaurant': base_restaurant.to_dict(),
						'similar_restaurants': [
								{
										**restaurant.to_dict(),
										'similarity_score': getattr(restaurant, 'similarity_score', 0)
								}
								for restaurant in similar_restaurants
						],
						'similarity_criteria': similarity_criteria
				}), 200
				
		except Exception as e:
				logger.error(f"유사 식당 추천 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '유사 식당 추천 중 오류가 발생했습니다.'
				}), 500

@recommendations_bp.route('/personalized/<int:user_id>', methods=['GET'])
def get_personalized_suggestions(user_id):
		"""
		사용자 개인화된 추천을 제공합니다.
		
		Query Parameters:
				limit: int (optional, default: 5) - 추천할 식당 수
		
		Returns:
				{
						"success": bool,
						"personalized_restaurants": list,
						"recommendation_basis": dict,
						"user_preferences": dict,
						"error": str (if error)
				}
		"""
		try:
				limit = min(request.args.get('limit', 5, type=int), 10)
				
				# 사용자 존재 확인
				user = User.query.get(user_id)
				if not user:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 사용자입니다.'
						}), 404
				
				# 개인화된 추천 생성
				personalized_restaurants = recommendation_engine.get_personalized_suggestions(user_id, limit)
				
				# 추천 근거 정보
				recommendation_basis = {
						'past_preferences': '과거 선호했던 음식 카테고리',
						'positive_reviews': '긍정적으로 평가한 식당들',
						'visit_patterns': '방문 패턴 분석',
						'location_preference': '선호 지역'
				}
				
				return jsonify({
						'success': True,
						'personalized_restaurants': [restaurant.to_dict() for restaurant in personalized_restaurants],
						'recommendation_basis': recommendation_basis,
						'user_preferences': user.food_preferences or {},
						'user_location': user.location
				}), 200
				
		except Exception as e:
				logger.error(f"개인화된 추천 생성 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '개인화된 추천 생성 중 오류가 발생했습니다.'
				}), 500

@recommendations_bp.route('/trending', methods=['GET'])
def get_trending_recommendations():
		"""
		최근 인기 상승 중인 식당들을 추천합니다.
		
		Query Parameters:
				limit: int (optional, default: 10) - 추천할 식당 수
				period: str (optional, default: '30d') - 분석 기간
		
		Returns:
				{
						"success": bool,
						"trending_restaurants": list,
						"period": str,
						"trend_factors": list,
						"error": str (if error)
				}
		"""
		try:
				limit = min(request.args.get('limit', 10, type=int), 20)
				period = request.args.get('period', '30d')
				
				# 트렌딩 식당 조회
				trending_restaurants = recommendation_engine.get_trending_restaurants(limit)
				
				# 트렌드 요소 설명
				trend_factors = [
						"최근 추천 빈도 증가",
						"새로운 긍정적 리뷰",
						"사용자 방문 증가",
						"평점 상승",
						"SNS 언급 증가"
				]
				
				return jsonify({
						'success': True,
						'trending_restaurants': [
								{
										**restaurant.to_dict(),
										'trending_score': getattr(restaurant, 'trending_score', 0)
								}
								for restaurant in trending_restaurants
						],
						'period': f'최근 {period}',
						'trend_factors': trend_factors,
						'generated_at': db.func.now()
				}), 200
				
		except Exception as e:
				logger.error(f"트렌딩 추천 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '트렌딩 추천 조회 중 오류가 발생했습니다.'
				}), 500

@recommendations_bp.route('/statistics', methods=['GET'])
def get_recommendation_statistics():
		"""
		추천 시스템의 전체 통계를 조회합니다.
		
		Returns:
				{
						"success": bool,
						"system_stats": dict,
						"performance_metrics": dict,
						"error": str (if error)
				}
		"""
		try:
				# 추천 엔진 통계 조회
				engine_stats = recommendation_engine.get_recommendation_statistics()
				
				# 전체 추천 수
				total_recommendations = Recommendation.query.count()
				
				# 성공적인 방문 수
				successful_visits = Recommendation.query.filter_by(was_visited=True).count()
				
				# 사용자 만족도 평균
				avg_satisfaction = db.session.query(
						db.func.avg(Recommendation.satisfaction_rating)
				).filter(
						Recommendation.satisfaction_rating.isnot(None)
				).scalar() or 0
				
				# 시스템 통계
				system_stats = {
						'total_recommendations': total_recommendations,
						'successful_visits': successful_visits,
						'visit_conversion_rate': (successful_visits / total_recommendations * 100) 
																		if total_recommendations > 0 else 0,
						'average_satisfaction': round(avg_satisfaction, 2),
						'active_users': User.query.filter_by(is_active=True).count(),
						'active_restaurants': Restaurant.query.filter_by(is_active=True).count()
				}
				
				return jsonify({
						'success': True,
						'system_stats': system_stats,
						'performance_metrics': engine_stats,
						'generated_at': db.func.now()
				}), 200
				
		except Exception as e:
				logger.error(f"추천 통계 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '통계 조회 중 오류가 발생했습니다.'
				}), 500

@recommendations_bp.route('/<int:recommendation_id>/click', methods=['POST'])
def record_recommendation_click(recommendation_id):
		"""
		추천 결과 클릭을 기록합니다.
		
		Returns:
				{
						"success": bool,
						"message": str,
						"error": str (if error)
				}
		"""
		try:
				# 추천 존재 확인
				recommendation = Recommendation.query.get(recommendation_id)
				if not recommendation:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 추천입니다.'
						}), 404
				
				# 클릭 기록
				recommendation.record_click()
				
				logger.info(f"추천 클릭 기록: 추천 {recommendation_id}")
				
				return jsonify({
						'success': True,
						'message': '클릭이 기록되었습니다.'
				}), 200
				
		except Exception as e:
				logger.error(f"추천 클릭 기록 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '클릭 기록 중 오류가 발생했습니다.'
				}), 500

# 에러 핸들러
@recommendations_bp.errorhandler(400)
def bad_request(error):
		"""잘못된 요청 에러 핸들러"""
		return jsonify({
				'success': False,
				'error': '잘못된 요청입니다.',
				'status_code': 400
		}), 400

@recommendations_bp.errorhandler(404)
def not_found(error):
		"""리소스를 찾을 수 없음 에러 핸들러"""
		return jsonify({
				'success': False,
				'error': '요청한 추천 정보를 찾을 수 없습니다.',
				'status_code': 404
		}), 404