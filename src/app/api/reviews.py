# -*- coding: utf-8 -*-
"""
리뷰 API 엔드포인트
사용자 리뷰 작성, 조회, 관리를 위한 REST API입니다.
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.models.review import Review
from app.models.restaurant import Restaurant
from app.models.user import User
from app.services.review_manager import ReviewManager
from app import db

logger = logging.getLogger(__name__)

# 블루프린트 생성
reviews_bp = Blueprint('reviews', __name__)

# 서비스 인스턴스 생성
review_manager = ReviewManager()

@reviews_bp.route('/', methods=['POST'])
def create_review():
		"""
		새로운 리뷰를 작성합니다.
		
		Request Body:
				{
						"user_id": int (required),
						"restaurant_id": int (required),
						"rating": int (required, 1-5),
						"content": str (required),
						"title": str (optional),
						"taste_rating": int (optional, 1-5),
						"service_rating": int (optional, 1-5),
						"atmosphere_rating": int (optional, 1-5),
						"value_rating": int (optional, 1-5),
						"visit_date": str (optional, YYYY-MM-DD),
						"visit_purpose": str (optional),
						"party_size": int (optional),
						"ordered_items": list (optional),
						"total_cost": int (optional),
						"would_recommend": bool (optional),
						"would_revisit": bool (optional)
				}
		
		Returns:
				{
						"success": bool,
						"review_id": int,
						"sentiment_analysis": dict,
						"message": str,
						"error": str (if error)
				}
		"""
		try:
				data = request.get_json()
				
				# 필수 파라미터 검증
				required_fields = ['user_id', 'restaurant_id', 'rating', 'content']
				for field in required_fields:
						if not data or field not in data:
								return jsonify({
										'success': False,
										'error': f'{field}는 필수 파라미터입니다.'
								}), 400
				
				user_id = data['user_id']
				restaurant_id = data['restaurant_id']
				
				# 사용자 및 식당 존재 확인
				user = User.query.get(user_id)
				restaurant = Restaurant.query.get(restaurant_id)
				
				if not user:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 사용자입니다.'
						}), 404
				
				if not restaurant or not restaurant.is_active:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 식당입니다.'
						}), 404
				
				# 방문 날짜 형식 검증 (있는 경우)
				if 'visit_date' in data and data['visit_date']:
						try:
								datetime.strptime(data['visit_date'], '%Y-%m-%d')
						except ValueError:
								return jsonify({
										'success': False,
										'error': '방문 날짜는 YYYY-MM-DD 형식이어야 합니다.'
								}), 400
				
				# 리뷰 생성
				result = review_manager.create_review(user_id, restaurant_id, data)
				
				if result['success']:
						logger.info(f"새 리뷰 생성: 사용자 {user_id}, 식당 {restaurant_id}")
						return jsonify(result), 201
				else:
						return jsonify(result), 400
				
		except Exception as e:
				logger.error(f"리뷰 생성 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '리뷰 생성 중 오류가 발생했습니다.'
				}), 500

@reviews_bp.route('/restaurant/<int:restaurant_id>', methods=['GET'])
def get_restaurant_reviews(restaurant_id):
		"""
		특정 식당의 리뷰들을 조회합니다.
		
		Query Parameters:
				page: int (optional, default: 1) - 페이지 번호
				per_page: int (optional, default: 10) - 페이지당 리뷰 수
				sort_by: str (optional, default: 'latest') - 정렬 기준
		
		Returns:
				{
						"success": bool,
						"reviews": list,
						"pagination": dict,
						"statistics": dict,
						"error": str (if error)
				}
		"""
		try:
				page = request.args.get('page', 1, type=int)
				per_page = min(request.args.get('per_page', 10, type=int), 50)
				sort_by = request.args.get('sort_by', 'latest')
				
				# 정렬 기준 검증
				valid_sort_options = ['latest', 'rating_high', 'rating_low', 'helpful']
				if sort_by not in valid_sort_options:
						return jsonify({
								'success': False,
								'error': f'sort_by는 다음 중 하나여야 합니다: {valid_sort_options}'
						}), 400
				
				# 식당 존재 확인
				restaurant = Restaurant.query.get(restaurant_id)
				if not restaurant:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 식당입니다.'
						}), 404
				
				# 리뷰 조회
				result = review_manager.get_restaurant_reviews(
						restaurant_id, page, per_page, sort_by
				)
				
				return jsonify(result), 200 if result['success'] else 500
				
		except Exception as e:
				logger.error(f"식당 리뷰 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '리뷰 조회 중 오류가 발생했습니다.'
				}), 500

@reviews_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user_reviews(user_id):
		"""
		특정 사용자가 작성한 리뷰들을 조회합니다.
		
		Query Parameters:
				page: int (optional, default: 1) - 페이지 번호
				per_page: int (optional, default: 10) - 페이지당 리뷰 수
		
		Returns:
				{
						"success": bool,
						"reviews": list,
						"pagination": dict,
						"user_statistics": dict,
						"error": str (if error)
				}
		"""
		try:
				page = request.args.get('page', 1, type=int)
				per_page = min(request.args.get('per_page', 10, type=int), 50)
				
				# 사용자 존재 확인
				user = User.query.get(user_id)
				if not user:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 사용자입니다.'
						}), 404
				
				# 사용자 리뷰 조회
				result = review_manager.get_user_reviews(user_id, page, per_page)
				
				return jsonify(result), 200 if result['success'] else 500
				
		except Exception as e:
				logger.error(f"사용자 리뷰 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '리뷰 조회 중 오류가 발생했습니다.'
				}), 500

@reviews_bp.route('/<int:review_id>', methods=['GET'])
def get_review_detail(review_id):
		"""
		특정 리뷰의 상세 정보를 조회합니다.
		
		Returns:
				{
						"success": bool,
						"review": dict,
						"error": str (if error)
				}
		"""
		try:
				review = Review.query.get(review_id)
				
				if not review or not review.is_active:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 리뷰입니다.'
						}), 404
				
				# 상세 리뷰 정보 (사용자 및 식당 정보 포함)
				review_data = review.to_dict(include_user=True, include_restaurant=True)
				
				return jsonify({
						'success': True,
						'review': review_data
				}), 200
				
		except Exception as e:
				logger.error(f"리뷰 상세 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '리뷰 조회 중 오류가 발생했습니다.'
				}), 500

@reviews_bp.route('/<int:review_id>/helpful', methods=['POST'])
def mark_review_helpful(review_id):
		"""
		리뷰에 유용성 평가를 남깁니다.
		
		Request Body:
				{
						"user_id": int (required),
						"is_helpful": bool (required)
				}
		
		Returns:
				{
						"success": bool,
						"helpful_count": int,
						"not_helpful_count": int,
						"helpfulness_ratio": float,
						"error": str (if error)
				}
		"""
		try:
				data = request.get_json()
				
				# 필수 파라미터 검증
				if not data or 'user_id' not in data or 'is_helpful' not in data:
						return jsonify({
								'success': False,
								'error': 'user_id와 is_helpful은 필수 파라미터입니다.'
						}), 400
				
				user_id = data['user_id']
				is_helpful = data['is_helpful']
				
				# 사용자 존재 확인
				user = User.query.get(user_id)
				if not user:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 사용자입니다.'
						}), 404
				
				# 유용성 평가 업데이트
				result = review_manager.update_review_helpfulness(review_id, user_id, is_helpful)
				
				return jsonify(result), 200 if result['success'] else 400
				
		except Exception as e:
				logger.error(f"리뷰 유용성 평가 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '유용성 평가 중 오류가 발생했습니다.'
				}), 500

@reviews_bp.route('/<int:review_id>', methods=['PUT'])
def update_review(review_id):
		"""
		기존 리뷰를 수정합니다.
		
		Request Body:
				{
						"user_id": int (required),
						"rating": int (optional, 1-5),
						"content": str (optional),
						"title": str (optional),
						// 기타 수정 가능한 필드들
				}
		
		Returns:
				{
						"success": bool,
						"message": str,
						"updated_review": dict,
						"error": str (if error)
				}
		"""
		try:
				data = request.get_json()
				
				if not data or 'user_id' not in data:
						return jsonify({
								'success': False,
								'error': 'user_id는 필수 파라미터입니다.'
						}), 400
				
				user_id = data['user_id']
				
				# 리뷰 존재 및 권한 확인
				review = Review.query.get(review_id)
				if not review or not review.is_active:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 리뷰입니다.'
						}), 404
				
				if review.user_id != user_id:
						return jsonify({
								'success': False,
								'error': '리뷰를 수정할 권한이 없습니다.'
						}), 403
				
				# 수정 가능한 필드들
				updateable_fields = [
						'rating', 'content', 'title', 'taste_rating', 'service_rating',
						'atmosphere_rating', 'value_rating', 'would_recommend', 'would_revisit'
				]
				
				# 필드 업데이트
				updated = False
				for field in updateable_fields:
						if field in data:
								setattr(review, field, data[field])
								updated = True
				
				if not updated:
						return jsonify({
								'success': False,
								'error': '수정할 내용이 없습니다.'
						}), 400
				
				# 평점이 변경된 경우 감정 분석 재수행
				if 'rating' in data or 'content' in data:
						review.analyze_sentiment()
				
				# 수정 시간 업데이트
				review.updated_at = datetime.utcnow()
				
				# 데이터베이스 저장
				db.session.commit()
				
				# 식당 평점 재계산
				review.restaurant.update_rating()
				
				logger.info(f"리뷰 수정 완료: 리뷰 {review_id}")
				
				return jsonify({
						'success': True,
						'message': '리뷰가 성공적으로 수정되었습니다.',
						'updated_review': review.to_dict()
				}), 200
				
		except Exception as e:
				logger.error(f"리뷰 수정 중 오류 발생: {e}")
				db.session.rollback()
				return jsonify({
						'success': False,
						'error': '리뷰 수정 중 오류가 발생했습니다.'
				}), 500

@reviews_bp.route('/<int:review_id>', methods=['DELETE'])
def delete_review(review_id):
		"""
		리뷰를 삭제합니다 (비활성화).
		
		Request Body:
				{
						"user_id": int (required)
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
				
				if not data or 'user_id' not in data:
						return jsonify({
								'success': False,
								'error': 'user_id는 필수 파라미터입니다.'
						}), 400
				
				user_id = data['user_id']
				
				# 리뷰 존재 및 권한 확인
				review = Review.query.get(review_id)
				if not review or not review.is_active:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 리뷰입니다.'
						}), 404
				
				if review.user_id != user_id:
						return jsonify({
								'success': False,
								'error': '리뷰를 삭제할 권한이 없습니다.'
						}), 403
				
				# 리뷰 비활성화 (실제 삭제하지 않음)
				review.is_active = False
				review.updated_at = datetime.utcnow()
				
				db.session.commit()
				
				# 식당 평점 재계산
				review.restaurant.update_rating()
				
				logger.info(f"리뷰 삭제 완료: 리뷰 {review_id}")
				
				return jsonify({
						'success': True,
						'message': '리뷰가 성공적으로 삭제되었습니다.'
				}), 200
				
		except Exception as e:
				logger.error(f"리뷰 삭제 중 오류 발생: {e}")
				db.session.rollback()
				return jsonify({
						'success': False,
						'error': '리뷰 삭제 중 오류가 발생했습니다.'
				}), 500

@reviews_bp.route('/restaurant/<int:restaurant_id>/trends', methods=['GET'])
def get_review_trends(restaurant_id):
		"""
		특정 식당의 리뷰 트렌드를 분석합니다.
		
		Query Parameters:
				days: int (optional, default: 30) - 분석 기간 (일 단위)
		
		Returns:
				{
						"success": bool,
						"trends": dict,
						"error": str (if error)
				}
		"""
		try:
				days = request.args.get('days', 30, type=int)
				
				# 기간 제한 (최대 365일)
				if days < 1 or days > 365:
						return jsonify({
								'success': False,
								'error': '분석 기간은 1-365일 사이여야 합니다.'
						}), 400
				
				# 식당 존재 확인
				restaurant = Restaurant.query.get(restaurant_id)
				if not restaurant:
						return jsonify({
								'success': False,
								'error': '존재하지 않는 식당입니다.'
						}), 404
				
				# 트렌드 분석
				result = review_manager.analyze_review_trends(restaurant_id, days)
				
				return jsonify(result), 200 if result['success'] else 500
				
		except Exception as e:
				logger.error(f"리뷰 트렌드 분석 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '트렌드 분석 중 오류가 발생했습니다.'
				}), 500

@reviews_bp.route('/statistics', methods=['GET'])
def get_review_statistics():
		"""
		전체 리뷰 시스템의 통계를 조회합니다.
		
		Returns:
				{
						"success": bool,
						"statistics": dict,
						"error": str (if error)
				}
		"""
		try:
				# 전체 리뷰 통계
				total_reviews = Review.query.filter(Review.is_active == True).count()
				
				# 평점 분포
				rating_distribution = {}
				for rating in range(1, 6):
						count = Review.query.filter(
								Review.is_active == True,
								Review.rating == rating
						).count()
						rating_distribution[str(rating)] = count
				
				# 평균 평점
				avg_rating = db.session.query(db.func.avg(Review.rating)).filter(
						Review.is_active == True
				).scalar() or 0
				
				# 최근 30일 리뷰 수
				from datetime import datetime, timedelta
				thirty_days_ago = datetime.utcnow() - timedelta(days=30)
				recent_reviews = Review.query.filter(
						Review.is_active == True,
						Review.created_at >= thirty_days_ago
				).count()
				
				statistics = {
						'total_reviews': total_reviews,
						'average_rating': round(avg_rating, 2),
						'rating_distribution': rating_distribution,
						'recent_reviews_30d': recent_reviews,
						'generated_at': datetime.utcnow().isoformat()
				}
				
				return jsonify({
						'success': True,
						'statistics': statistics
				}), 200
				
		except Exception as e:
				logger.error(f"리뷰 통계 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '통계 조회 중 오류가 발생했습니다.'
				}), 500

# 에러 핸들러
@reviews_bp.errorhandler(403)
def forbidden(error):
		"""권한 없음 에러 핸들러"""
		return jsonify({
				'success': False,
				'error': '해당 작업을 수행할 권한이 없습니다.',
				'status_code': 403
		}), 403