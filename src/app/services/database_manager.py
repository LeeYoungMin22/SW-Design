# -*- coding: utf-8 -*-
"""
데이터베이스 관리 서비스 (DatabaseManager)
SQLite 기반 추천 이력, 식당 데이터 CRUD 담당 및 데이터 정합성 관리를 수행합니다.
"""

import logging
import json
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from sqlalchemy import and_, or_, func, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app import db
from app.models.user import User
from app.models.restaurant import Restaurant
from app.models.review import Review
from app.models.recommendation import Recommendation

logger = logging.getLogger(__name__)

class DatabaseManager:
		"""
		데이터베이스 CRUD 작업과 데이터 정합성을 관리하는 서비스 클래스
		효율적인 쿼리 실행과 데이터 무결성을 보장합니다.
		"""
		
		def __init__(self):
				"""
				데이터베이스 매니저 초기화
				트랜잭션 관리와 성능 모니터링을 설정합니다.
				"""
				self.transaction_timeout = 30  # 초 단위
				self.batch_size = 1000         # 일괄 처리 크기
				
				# 성능 통계
				self.stats = {
						'total_queries': 0,
						'successful_transactions': 0,
						'failed_transactions': 0,
						'average_query_time': 0.0
				}
		
		# ============ 사용자 관리 메소드들 ============
		
		def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
				"""
				새로운 사용자를 생성합니다.
				
				Args:
						user_data (Dict[str, Any]): 사용자 정보
						
				Returns:
						Dict[str, Any]: 생성 결과
				"""
				try:
						# 중복 사용자 확인
						existing_user = User.query.filter(
								or_(
										User.username == user_data.get('username'),
										User.email == user_data.get('email')
								)
						).first()
						
						if existing_user:
								return {
										'success': False,
										'error': '이미 존재하는 사용자명 또는 이메일입니다.'
								}
						
						# 새 사용자 생성
						user = User(
								username=user_data['username'],
								email=user_data.get('email'),
								location=user_data.get('location', '대구 달서구'),
								budget_range=user_data.get('budget_range', '20000-30000'),
								preferred_radius=user_data.get('preferred_radius', 5)
						)
						
						# 추가 속성 설정
						if 'food_preferences' in user_data:
								user.food_preferences = user_data['food_preferences']
						
						if 'dietary_restrictions' in user_data:
								user.dietary_restrictions = user_data['dietary_restrictions']
						
						db.session.add(user)
						db.session.commit()
						
						self.stats['successful_transactions'] += 1
						logger.info(f"새 사용자 생성 완료: {user.username}")
						
						return {
								'success': True,
								'user_id': user.id,
								'message': '사용자가 성공적으로 생성되었습니다.'
						}
						
				except IntegrityError as e:
						db.session.rollback()
						self.stats['failed_transactions'] += 1
						logger.error(f"사용자 생성 중 무결성 오류: {e}")
						return {
								'success': False,
								'error': '데이터 무결성 오류가 발생했습니다.'
						}
				except Exception as e:
						db.session.rollback()
						self.stats['failed_transactions'] += 1
						logger.error(f"사용자 생성 중 오류 발생: {e}")
						return {
								'success': False,
								'error': str(e)
						}
		
		def get_user_by_id(self, user_id: int) -> Optional[User]:
				"""
				사용자 ID로 사용자 정보를 조회합니다.
				
				Args:
						user_id (int): 사용자 ID
						
				Returns:
						Optional[User]: 사용자 객체 또는 None
				"""
				try:
						self.stats['total_queries'] += 1
						return User.query.get(user_id)
				except Exception as e:
						logger.error(f"사용자 조회 중 오류 발생: {e}")
						return None
		
		def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
				"""
				사용자 정보를 업데이트합니다.
				
				Args:
						user_id (int): 사용자 ID
						update_data (Dict[str, Any]): 업데이트할 데이터
						
				Returns:
						Dict[str, Any]: 업데이트 결과
				"""
				try:
						user = User.query.get(user_id)
						if not user:
								return {
										'success': False,
										'error': '사용자를 찾을 수 없습니다.'
								}
						
						# 업데이트 가능한 필드들
						updateable_fields = [
								'username', 'email', 'location', 'preferred_radius',
								'budget_range', 'food_preferences', 'dietary_restrictions'
						]
						
						for field, value in update_data.items():
								if field in updateable_fields and hasattr(user, field):
										setattr(user, field, value)
						
						db.session.commit()
						self.stats['successful_transactions'] += 1
						
						return {
								'success': True,
								'message': '사용자 정보가 업데이트되었습니다.'
						}
						
				except Exception as e:
						db.session.rollback()
						self.stats['failed_transactions'] += 1
						logger.error(f"사용자 업데이트 중 오류 발생: {e}")
						return {
								'success': False,
								'error': str(e)
						}
		
		# ============ 식당 관리 메소드들 ============
		
		def bulk_insert_restaurants(self, restaurants_data: List[Dict[str, Any]]) -> Dict[str, Any]:
				"""
				여러 식당 데이터를 일괄 삽입합니다.
				
				Args:
						restaurants_data (List[Dict[str, Any]]): 식당 정보 리스트
						
				Returns:
						Dict[str, Any]: 삽입 결과
				"""
				try:
						inserted_count = 0
						skipped_count = 0
						errors = []
						
						# 배치 단위로 처리
						for i in range(0, len(restaurants_data), self.batch_size):
								batch = restaurants_data[i:i + self.batch_size]
								
								for restaurant_data in batch:
										try:
												# 중복 체크 (이름과 주소로)
												existing = Restaurant.query.filter(
														Restaurant.name == restaurant_data['name'],
														Restaurant.address == restaurant_data['address']
												).first()
												
												if existing:
														skipped_count += 1
														continue
												
												# 새 식당 생성
												restaurant = Restaurant(
														name=restaurant_data['name'],
														address=restaurant_data['address'],
														category=restaurant_data['category'],
														description=restaurant_data.get('description'),
														phone=restaurant_data.get('phone'),
														website=restaurant_data.get('website'),
														cuisine_type=restaurant_data.get('cuisine_type'),
														average_price=restaurant_data.get('average_price'),
														latitude=restaurant_data.get('latitude'),
														longitude=restaurant_data.get('longitude')
												)
												
												# 선택적 필드들
												if 'menu_items' in restaurant_data:
														restaurant.menu_items = restaurant_data['menu_items']
												
												if 'business_hours' in restaurant_data:
														restaurant.business_hours = restaurant_data['business_hours']
												
												if 'special_features' in restaurant_data:
														restaurant.special_features = restaurant_data['special_features']
												
												db.session.add(restaurant)
												inserted_count += 1
												
										except Exception as e:
												errors.append(f"식당 '{restaurant_data.get('name', 'Unknown')}': {str(e)}")
												continue
								
								# 배치마다 커밋
								try:
										db.session.commit()
								except Exception as e:
										db.session.rollback()
										errors.append(f"배치 커밋 실패: {str(e)}")
						
						self.stats['successful_transactions'] += 1
						logger.info(f"식당 일괄 삽입 완료: {inserted_count}개 삽입, {skipped_count}개 건너뜀")
						
						return {
								'success': True,
								'inserted_count': inserted_count,
								'skipped_count': skipped_count,
								'errors': errors,
								'message': f'{inserted_count}개 식당이 성공적으로 등록되었습니다.'
						}
						
				except Exception as e:
						db.session.rollback()
						self.stats['failed_transactions'] += 1
						logger.error(f"식당 일괄 삽입 중 오류 발생: {e}")
						return {
								'success': False,
								'error': str(e),
								'inserted_count': 0
						}
		
		def search_restaurants(self, 
													search_params: Dict[str, Any],
													page: int = 1,
													per_page: int = 20) -> Dict[str, Any]:
				"""
				다양한 조건으로 식당을 검색합니다.
				
				Args:
						search_params (Dict[str, Any]): 검색 조건
						page (int): 페이지 번호
						per_page (int): 페이지당 결과 수
						
				Returns:
						Dict[str, Any]: 검색 결과
				"""
				try:
						# 기본 쿼리 (활성 식당만)
						query = Restaurant.query.filter(Restaurant.is_active == True)
						
						# 이름으로 검색
						if 'name' in search_params:
								query = query.filter(Restaurant.name.contains(search_params['name']))
						
						# 카테고리로 검색
						if 'category' in search_params:
								query = query.filter(Restaurant.category.contains(search_params['category']))
						
						# 지역으로 검색
						if 'district' in search_params:
								query = query.filter(Restaurant.district == search_params['district'])
						
						# 가격 범위로 검색
						if 'min_price' in search_params:
								query = query.filter(Restaurant.average_price >= search_params['min_price'])
						
						if 'max_price' in search_params:
								query = query.filter(Restaurant.average_price <= search_params['max_price'])
						
						# 평점 범위로 검색
						if 'min_rating' in search_params:
								query = query.filter(Restaurant.rating_average >= search_params['min_rating'])
						
						# 특별 기능으로 검색
						if 'parking' in search_params and search_params['parking']:
								query = query.filter(Restaurant.parking_available == True)
						
						if 'delivery' in search_params and search_params['delivery']:
								query = query.filter(Restaurant.delivery_available == True)
						
						# 정렬 옵션
						sort_by = search_params.get('sort_by', 'rating')
						if sort_by == 'rating':
								query = query.order_by(Restaurant.rating_average.desc())
						elif sort_by == 'name':
								query = query.order_by(Restaurant.name)
						elif sort_by == 'price_low':
								query = query.order_by(Restaurant.average_price.asc())
						elif sort_by == 'price_high':
								query = query.order_by(Restaurant.average_price.desc())
						
						# 페이지네이션 적용
						paginated_results = query.paginate(
								page=page, per_page=per_page, error_out=False
						)
						
						# 결과 변환
						restaurants = [restaurant.to_dict() for restaurant in paginated_results.items]
						
						self.stats['total_queries'] += 1
						
						return {
								'success': True,
								'restaurants': restaurants,
								'pagination': {
										'current_page': page,
										'total_pages': paginated_results.pages,
										'per_page': per_page,
										'total_results': paginated_results.total,
										'has_next': paginated_results.has_next,
										'has_prev': paginated_results.has_prev
								}
						}
						
				except Exception as e:
						logger.error(f"식당 검색 중 오류 발생: {e}")
						return {
								'success': False,
								'error': str(e),
								'restaurants': []
						}
		
		def update_restaurant_status(self, restaurant_id: int, status_data: Dict[str, Any]) -> Dict[str, Any]:
				"""
				식당의 상태 정보를 업데이트합니다.
				
				Args:
						restaurant_id (int): 식당 ID
						status_data (Dict[str, Any]): 상태 정보
						
				Returns:
						Dict[str, Any]: 업데이트 결과
				"""
				try:
						restaurant = Restaurant.query.get(restaurant_id)
						if not restaurant:
								return {
										'success': False,
										'error': '식당을 찾을 수 없습니다.'
								}
						
						# 업데이트 가능한 상태 필드들
						status_fields = [
								'is_active', 'is_verified', 'business_hours',
								'parking_available', 'delivery_available', 'takeout_available'
						]
						
						for field, value in status_data.items():
								if field in status_fields and hasattr(restaurant, field):
										setattr(restaurant, field, value)
						
						restaurant.updated_at = datetime.utcnow()
						db.session.commit()
						
						return {
								'success': True,
								'message': '식당 상태가 업데이트되었습니다.'
						}
						
				except Exception as e:
						db.session.rollback()
						logger.error(f"식당 상태 업데이트 중 오류 발생: {e}")
						return {
								'success': False,
								'error': str(e)
						}
		
		# ============ 추천 이력 관리 메소드들 ============
		
		def get_user_recommendation_history(self, 
																			user_id: int,
																			limit: int = 50,
																			include_restaurants: bool = True) -> List[Dict[str, Any]]:
				"""
				사용자의 추천 이력을 조회합니다.
				
				Args:
						user_id (int): 사용자 ID
						limit (int): 조회할 최대 개수
						include_restaurants (bool): 식당 정보 포함 여부
						
				Returns:
						List[Dict[str, Any]]: 추천 이력 리스트
				"""
				try:
						query = Recommendation.query.filter(
								Recommendation.user_id == user_id
						).order_by(Recommendation.created_at.desc()).limit(limit)
						
						recommendations = query.all()
						
						result = []
						for rec in recommendations:
								rec_dict = rec.to_dict(include_restaurant=include_restaurants)
								result.append(rec_dict)
						
						self.stats['total_queries'] += 1
						return result
						
				except Exception as e:
						logger.error(f"추천 이력 조회 중 오류 발생: {e}")
						return []
		
		def update_recommendation_feedback(self, 
																			recommendation_id: int,
																			feedback_data: Dict[str, Any]) -> Dict[str, Any]:
				"""
				추천에 대한 사용자 피드백을 업데이트합니다.
				
				Args:
						recommendation_id (int): 추천 ID
						feedback_data (Dict[str, Any]): 피드백 데이터
						
				Returns:
						Dict[str, Any]: 업데이트 결과
				"""
				try:
						recommendation = Recommendation.query.get(recommendation_id)
						if not recommendation:
								return {
										'success': False,
										'error': '추천 기록을 찾을 수 없습니다.'
								}
						
						# 피드백 업데이트
						if 'feedback_type' in feedback_data:
								recommendation.record_feedback(
										feedback_data['feedback_type'],
										feedback_data.get('rating'),
										feedback_data.get('comment')
								)
						
						if 'was_visited' in feedback_data:
								recommendation.record_visit(feedback_data['was_visited'])
						
						return {
								'success': True,
								'message': '피드백이 업데이트되었습니다.'
						}
						
				except Exception as e:
						db.session.rollback()
						logger.error(f"추천 피드백 업데이트 중 오류 발생: {e}")
						return {
								'success': False,
								'error': str(e)
						}
		
		# ============ 데이터 분석 및 통계 메소드들 ============
		
		def get_system_statistics(self) -> Dict[str, Any]:
				"""
				시스템 전체 통계를 조회합니다.
				
				Returns:
						Dict[str, Any]: 시스템 통계
				"""
				try:
						# 기본 카운트 통계
						user_count = User.query.filter(User.is_active == True).count()
						restaurant_count = Restaurant.query.filter(Restaurant.is_active == True).count()
						review_count = Review.query.filter(Review.is_active == True).count()
						recommendation_count = Recommendation.query.count()
						
						# 최근 30일 활동 통계
						thirty_days_ago = datetime.utcnow() - timedelta(days=30)
						
						recent_users = User.query.filter(User.last_login >= thirty_days_ago).count()
						recent_reviews = Review.query.filter(Review.created_at >= thirty_days_ago).count()
						recent_recommendations = Recommendation.query.filter(
								Recommendation.created_at >= thirty_days_ago
						).count()
						
						# 평점 통계
						avg_restaurant_rating = db.session.query(
								func.avg(Restaurant.rating_average)
						).filter(Restaurant.is_active == True).scalar() or 0
						
						# 가장 인기 있는 카테고리
						popular_categories = db.session.query(
								Restaurant.category,
								func.count(Restaurant.id).label('count')
						).filter(
								Restaurant.is_active == True
						).group_by(Restaurant.category).order_by(
								func.count(Restaurant.id).desc()
						).limit(5).all()
						
						return {
								'counts': {
										'total_users': user_count,
										'total_restaurants': restaurant_count,
										'total_reviews': review_count,
										'total_recommendations': recommendation_count
								},
								'recent_activity': {
										'active_users_30d': recent_users,
										'new_reviews_30d': recent_reviews,
										'recommendations_30d': recent_recommendations
								},
								'averages': {
										'restaurant_rating': round(avg_restaurant_rating, 2)
								},
								'popular_categories': [
										{'category': cat, 'count': count} 
										for cat, count in popular_categories
								],
								'database_stats': self.stats.copy()
						}
						
				except Exception as e:
						logger.error(f"시스템 통계 조회 중 오류 발생: {e}")
						return {}
		
		def cleanup_old_data(self, days_to_keep: int = 365) -> Dict[str, Any]:
				"""
				오래된 데이터를 정리합니다.
				
				Args:
						days_to_keep (int): 보관할 일수
						
				Returns:
						Dict[str, Any]: 정리 결과
				"""
				try:
						cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
						
						# 오래된 추천 기록 삭제 (피드백이 없는 것들만)
						old_recommendations = Recommendation.query.filter(
								Recommendation.created_at < cutoff_date,
								Recommendation.user_feedback.is_(None)
						).delete()
						
						# 비활성 사용자의 오래된 세션 데이터 정리
						inactive_users = User.query.filter(
								User.last_login < cutoff_date,
								User.is_active == False
						).all()
						
						cleaned_sessions = 0
						for user in inactive_users:
								user.session_data = {}
								cleaned_sessions += 1
						
						db.session.commit()
						
						return {
								'success': True,
								'deleted_recommendations': old_recommendations,
								'cleaned_sessions': cleaned_sessions,
								'message': f'{old_recommendations}개의 오래된 추천 기록과 {cleaned_sessions}개의 세션이 정리되었습니다.'
						}
						
				except Exception as e:
						db.session.rollback()
						logger.error(f"데이터 정리 중 오류 발생: {e}")
						return {
								'success': False,
								'error': str(e)
						}