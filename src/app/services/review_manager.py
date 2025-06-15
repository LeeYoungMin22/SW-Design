# -*- coding: utf-8 -*-
"""
리뷰 관리 서비스 (ReviewManager)
사용자 리뷰 수집, 감정 분석, 식당 점수 조정을 담당합니다.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import and_, or_, func
from app import db
from app.models.review import Review
from app.models.restaurant import Restaurant
from app.models.user import User
from app.utils.sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)

class ReviewManager:
		"""
		리뷰 수집, 감정 분석, 평점 업데이트를 담당하는 서비스 클래스
		사용자 리뷰를 종합적으로 관리하고 식당 평점에 반영합니다.
		"""
		
		def __init__(self):
				"""
				리뷰 매니저 초기화
				감정 분석기와 검증 기준을 설정합니다.
				"""
				self.sentiment_analyzer = SentimentAnalyzer()
				
				# 리뷰 검증 기준
				self.validation_criteria = {
						'min_content_length': 10,      # 최소 내용 길이
						'max_content_length': 2000,    # 최대 내용 길이
						'min_rating': 1,               # 최소 평점
						'max_rating': 5,               # 최대 평점
						'spam_keywords': ['광고', '홍보', '스팸'],  # 스팸 키워드
						'required_fields': ['rating', 'content']   # 필수 필드
				}
				
				# 감정 분석 가중치
				self.sentiment_weights = {
						'positive': 1.2,    # 긍정적 리뷰 가중치
						'neutral': 1.0,     # 중립적 리뷰 가중치
						'negative': 0.8     # 부정적 리뷰 가중치
				}
		
		def create_review(self, 
											user_id: int,
											restaurant_id: int,
											review_data: Dict[str, Any]) -> Dict[str, Any]:
				"""
				새로운 리뷰를 생성하고 저장합니다.
				
				Args:
						user_id (int): 리뷰 작성자 ID
						restaurant_id (int): 리뷰 대상 식당 ID
						review_data (Dict[str, Any]): 리뷰 데이터
						
				Returns:
						Dict[str, Any]: 생성 결과
				"""
				try:
						# 1. 입력 데이터 검증
						validation_result = self._validate_review_data(review_data)
						if not validation_result['valid']:
								return {
										'success': False,
										'error': validation_result['message'],
										'validation_errors': validation_result.get('errors', [])
								}
						
						# 2. 중복 리뷰 확인
						existing_review = self._check_duplicate_review(user_id, restaurant_id)
						if existing_review:
								return {
										'success': False,
										'error': '이미 이 식당에 대한 리뷰를 작성하셨습니다.',
										'existing_review_id': existing_review.id
								}
						
						# 3. 사용자 및 식당 존재 확인
						user = User.query.get(user_id)
						restaurant = Restaurant.query.get(restaurant_id)
						
						if not user or not restaurant:
								return {
										'success': False,
										'error': '사용자 또는 식당 정보를 찾을 수 없습니다.'
								}
						
						# 4. 리뷰 객체 생성
						review = Review(
								user_id=user_id,
								restaurant_id=restaurant_id,
								rating=review_data['rating'],
								content=review_data['content'],
								title=review_data.get('title'),
								taste_rating=review_data.get('taste_rating'),
								service_rating=review_data.get('service_rating'),
								atmosphere_rating=review_data.get('atmosphere_rating'),
								value_rating=review_data.get('value_rating'),
								visit_date=review_data.get('visit_date'),
								visit_purpose=review_data.get('visit_purpose'),
								party_size=review_data.get('party_size'),
								total_cost=review_data.get('total_cost'),
								would_recommend=review_data.get('would_recommend'),
								would_revisit=review_data.get('would_revisit')
						)
						
						# 5. 주문 메뉴 정보 추가
						if review_data.get('ordered_items'):
								review.ordered_items = review_data['ordered_items']
						
						# 6. 감정 분석 수행
						sentiment_result = self._analyze_review_sentiment(review.content)
						review.sentiment_score = sentiment_result['score']
						review.sentiment_label = sentiment_result['label']
						review.emotion_tags = sentiment_result.get('emotions', [])
						review.keywords = sentiment_result.get('keywords', [])
						review.positive_aspects = sentiment_result.get('positive_aspects', [])
						review.negative_aspects = sentiment_result.get('negative_aspects', [])
						
						# 7. 데이터베이스에 저장
						db.session.add(review)
						db.session.commit()
						
						# 8. 식당 평점 업데이트
						self._update_restaurant_rating(restaurant)
						
						# 9. 사용자 선호도 업데이트
						self._update_user_preferences(user, restaurant, review)
						
						logger.info(f"새 리뷰 생성 완료: 사용자 {user_id}, 식당 {restaurant_id}")
						
						return {
								'success': True,
								'review_id': review.id,
								'sentiment_analysis': sentiment_result,
								'message': '리뷰가 성공적으로 등록되었습니다.'
						}
						
				except Exception as e:
						logger.error(f"리뷰 생성 중 오류 발생: {e}")
						db.session.rollback()
						return {
								'success': False,
								'error': '리뷰 저장 중 오류가 발생했습니다.',
								'details': str(e)
						}
		
		def get_restaurant_reviews(self, 
															restaurant_id: int,
															page: int = 1,
															per_page: int = 10,
															sort_by: str = 'latest') -> Dict[str, Any]:
				"""
				특정 식당의 리뷰들을 조회합니다.
				
				Args:
						restaurant_id (int): 식당 ID
						page (int): 페이지 번호
						per_page (int): 페이지당 리뷰 수
						sort_by (str): 정렬 기준 ('latest', 'rating_high', 'rating_low', 'helpful')
						
				Returns:
						Dict[str, Any]: 리뷰 목록과 통계
				"""
				try:
						# 기본 쿼리 (활성 리뷰만)
						query = Review.query.filter(
								Review.restaurant_id == restaurant_id,
								Review.is_active == True
						)
						
						# 정렬 기준 적용
						if sort_by == 'latest':
								query = query.order_by(Review.created_at.desc())
						elif sort_by == 'rating_high':
								query = query.order_by(Review.rating.desc(), Review.created_at.desc())
						elif sort_by == 'rating_low':
								query = query.order_by(Review.rating.asc(), Review.created_at.desc())
						elif sort_by == 'helpful':
								query = query.order_by(Review.helpful_count.desc(), Review.created_at.desc())
						
						# 페이지네이션 적용
						paginated_reviews = query.paginate(
								page=page, per_page=per_page, error_out=False
						)
						
						# 리뷰 데이터 변환
						reviews_data = []
						for review in paginated_reviews.items:
								review_dict = review.to_dict(include_user=True)
								review_dict['time_ago'] = review.get_time_ago()
								review_dict['helpfulness_ratio'] = review.get_helpfulness_ratio()
								reviews_data.append(review_dict)
						
						# 리뷰 통계 계산
						stats = self._calculate_review_statistics(restaurant_id)
						
						return {
								'success': True,
								'reviews': reviews_data,
								'pagination': {
										'current_page': page,
										'total_pages': paginated_reviews.pages,
										'per_page': per_page,
										'total_reviews': paginated_reviews.total,
										'has_next': paginated_reviews.has_next,
										'has_prev': paginated_reviews.has_prev
								},
								'statistics': stats
						}
						
				except Exception as e:
						logger.error(f"리뷰 조회 중 오류 발생: {e}")
						return {
								'success': False,
								'error': str(e),
								'reviews': [],
								'statistics': {}
						}
		
		def update_review_helpfulness(self, 
																review_id: int,
																user_id: int,
																is_helpful: bool) -> Dict[str, Any]:
				"""
				리뷰의 유용성 평가를 업데이트합니다.
				
				Args:
						review_id (int): 리뷰 ID
						user_id (int): 평가하는 사용자 ID
						is_helpful (bool): 도움이 되었는지 여부
						
				Returns:
						Dict[str, Any]: 업데이트 결과
				"""
				try:
						review = Review.query.get(review_id)
						if not review:
								return {
										'success': False,
										'error': '리뷰를 찾을 수 없습니다.'
								}
						
						# 자신의 리뷰에는 평가할 수 없음
						if review.user_id == user_id:
								return {
										'success': False,
										'error': '자신의 리뷰에는 평가할 수 없습니다.'
								}
						
						# 유용성 평가 업데이트
						review.mark_helpful(is_helpful)
						
						return {
								'success': True,
								'helpful_count': review.helpful_count,
								'not_helpful_count': review.not_helpful_count,
								'helpfulness_ratio': review.get_helpfulness_ratio()
						}
						
				except Exception as e:
						logger.error(f"리뷰 유용성 업데이트 중 오류 발생: {e}")
						return {
								'success': False,
								'error': str(e)
						}
		
		def get_user_reviews(self, 
												user_id: int,
												page: int = 1,
												per_page: int = 10) -> Dict[str, Any]:
				"""
				특정 사용자가 작성한 리뷰들을 조회합니다.
				
				Args:
						user_id (int): 사용자 ID
						page (int): 페이지 번호
						per_page (int): 페이지당 리뷰 수
						
				Returns:
						Dict[str, Any]: 사용자의 리뷰 목록
				"""
				try:
						# 사용자 리뷰 조회 (최신순)
						query = Review.query.filter(
								Review.user_id == user_id,
								Review.is_active == True
						).order_by(Review.created_at.desc())
						
						paginated_reviews = query.paginate(
								page=page, per_page=per_page, error_out=False
						)
						
						# 리뷰 데이터 변환 (식당 정보 포함)
						reviews_data = []
						for review in paginated_reviews.items:
								review_dict = review.to_dict(include_restaurant=True)
								review_dict['time_ago'] = review.get_time_ago()
								reviews_data.append(review_dict)
						
						# 사용자 리뷰 통계
						user_stats = self._calculate_user_review_statistics(user_id)
						
						return {
								'success': True,
								'reviews': reviews_data,
								'pagination': {
										'current_page': page,
										'total_pages': paginated_reviews.pages,
										'per_page': per_page,
										'total_reviews': paginated_reviews.total
								},
								'user_statistics': user_stats
						}
						
				except Exception as e:
						logger.error(f"사용자 리뷰 조회 중 오류 발생: {e}")
						return {
								'success': False,
								'error': str(e),
								'reviews': []
						}
		
		def analyze_review_trends(self, 
														restaurant_id: int,
														days: int = 30) -> Dict[str, Any]:
				"""
				특정 기간 동안의 리뷰 트렌드를 분석합니다.
				
				Args:
						restaurant_id (int): 식당 ID
						days (int): 분석 기간 (일 단위)
						
				Returns:
						Dict[str, Any]: 트렌드 분석 결과
				"""
				try:
						# 기간 설정
						end_date = datetime.utcnow()
						start_date = end_date - timedelta(days=days)
						
						# 기간 내 리뷰 조회
						reviews = Review.query.filter(
								Review.restaurant_id == restaurant_id,
								Review.created_at >= start_date,
								Review.is_active == True
						).all()
						
						if not reviews:
								return {
										'success': True,
										'message': '분석할 리뷰가 없습니다.',
										'trends': {}
								}
						
						# 트렌드 분석
						trends = {
								'period': {
										'start_date': start_date.isoformat(),
										'end_date': end_date.isoformat(),
										'days': days
								},
								'review_count': len(reviews),
								'average_rating': sum(r.rating for r in reviews) / len(reviews),
								'rating_distribution': self._calculate_rating_distribution(reviews),
								'sentiment_distribution': self._calculate_sentiment_distribution(reviews),
								'common_keywords': self._extract_common_keywords(reviews),
								'peak_review_days': self._find_peak_review_days(reviews),
								'improvement_suggestions': self._generate_improvement_suggestions(reviews)
						}
						
						return {
								'success': True,
								'trends': trends
						}
						
				except Exception as e:
						logger.error(f"리뷰 트렌드 분석 중 오류 발생: {e}")
						return {
								'success': False,
								'error': str(e)
						}
		
		def _validate_review_data(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
				"""
				리뷰 데이터의 유효성을 검증합니다.
				
				Args:
						review_data (Dict[str, Any]): 검증할 리뷰 데이터
						
				Returns:
						Dict[str, Any]: 검증 결과
				"""
				errors = []
				
				# 필수 필드 확인
				for field in self.validation_criteria['required_fields']:
						if field not in review_data or not review_data[field]:
								errors.append(f'{field} 필드는 필수입니다.')
				
				# 평점 범위 확인
				rating = review_data.get('rating')
				if rating is not None:
						if not (self.validation_criteria['min_rating'] <= rating <= self.validation_criteria['max_rating']):
								errors.append(f'평점은 {self.validation_criteria["min_rating"]}-{self.validation_criteria["max_rating"]} 사이여야 합니다.')
				
				# 내용 길이 확인
				content = review_data.get('content', '')
				if len(content) < self.validation_criteria['min_content_length']:
						errors.append(f'리뷰 내용은 최소 {self.validation_criteria["min_content_length"]}자 이상이어야 합니다.')
				elif len(content) > self.validation_criteria['max_content_length']:
						errors.append(f'리뷰 내용은 최대 {self.validation_criteria["max_content_length"]}자까지 가능합니다.')
				
				# 스팸 키워드 확인
				for keyword in self.validation_criteria['spam_keywords']:
						if keyword in content:
								errors.append('적절하지 않은 내용이 포함되어 있습니다.')
								break
				
				return {
						'valid': len(errors) == 0,
						'message': '검증 통과' if len(errors) == 0 else '검증 실패',
						'errors': errors
				}
		
		def _check_duplicate_review(self, user_id: int, restaurant_id: int) -> Optional[Review]:
				"""중복 리뷰가 있는지 확인합니다."""
				return Review.query.filter(
						Review.user_id == user_id,
						Review.restaurant_id == restaurant_id,
						Review.is_active == True
				).first()
		
		def _analyze_review_sentiment(self, content: str) -> Dict[str, Any]:
				"""
				리뷰 내용의 감정을 분석합니다.
				
				Args:
						content (str): 리뷰 내용
						
				Returns:
						Dict[str, Any]: 감정 분석 결과
				"""
				try:
						return self.sentiment_analyzer.analyze_text(content)
				except Exception as e:
						logger.error(f"감정 분석 중 오류 발생: {e}")
						return {
								'score': 0.0,
								'label': 'neutral',
								'emotions': [],
								'keywords': [],
								'positive_aspects': [],
								'negative_aspects': []
						}
		
		def _update_restaurant_rating(self, restaurant: Restaurant):
				"""식당의 평점을 업데이트합니다."""
				try:
						restaurant.update_rating()
						logger.info(f"식당 {restaurant.id} 평점 업데이트 완료")
				except Exception as e:
						logger.error(f"식당 평점 업데이트 중 오류 발생: {e}")
		
		def _update_user_preferences(self, user: User, restaurant: Restaurant, review: Review):
				"""리뷰를 바탕으로 사용자 선호도를 업데이트합니다."""
				try:
						# 긍정적인 리뷰인 경우 선호도 증가
						if review.rating >= 4:
								user.add_food_preference(restaurant.cuisine_type, review.rating)
						
						logger.info(f"사용자 {user.id} 선호도 업데이트 완료")
				except Exception as e:
						logger.error(f"사용자 선호도 업데이트 중 오류 발생: {e}")
		
		def _calculate_review_statistics(self, restaurant_id: int) -> Dict[str, Any]:
				"""식당의 리뷰 통계를 계산합니다."""
				try:
						reviews = Review.query.filter(
								Review.restaurant_id == restaurant_id,
								Review.is_active == True
						).all()
						
						if not reviews:
								return {'total_reviews': 0}
						
						# 기본 통계
						total_reviews = len(reviews)
						avg_rating = sum(r.rating for r in reviews) / total_reviews
						
						# 평점별 분포
						rating_counts = {}
						for i in range(1, 6):
								rating_counts[str(i)] = len([r for r in reviews if r.rating == i])
						
						# 감정 분포
						sentiment_counts = {
								'positive': len([r for r in reviews if r.sentiment_label == 'positive']),
								'neutral': len([r for r in reviews if r.sentiment_label == 'neutral']),
								'negative': len([r for r in reviews if r.sentiment_label == 'negative'])
						}
						
						return {
								'total_reviews': total_reviews,
								'average_rating': round(avg_rating, 1),
								'rating_distribution': rating_counts,
								'sentiment_distribution': sentiment_counts,
								'recent_reviews_count': len([r for r in reviews 
																						if r.created_at > datetime.utcnow() - timedelta(days=30)])
						}
						
				except Exception as e:
						logger.error(f"리뷰 통계 계산 중 오류 발생: {e}")
						return {'total_reviews': 0}