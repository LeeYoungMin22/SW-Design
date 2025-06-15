# -*- coding: utf-8 -*-
"""
맛집 추천 엔진 (Part 1)
AI 기반 맛집 추천 시스템의 핵심 로직을 담당합니다.
이 파일은 메인 클래스와 기본 추천 메소드들을 포함합니다.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func
from app import db
from app.models.restaurant import Restaurant
from app.models.user import User
from app.models.review import Review
from app.models.recommendation import Recommendation
from app.services.openai_service import OpenAIService
from app.utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class RecommendationEngine:
		"""
		AI 기반 맛집 추천 엔진
		사용자 질문을 분석하고 최적의 식당을 추천하는 핵심 서비스입니다.
		"""
		
		def __init__(self):
				"""
				추천 엔진 초기화
				OpenAI 서비스와 캐시 매니저를 설정합니다.
				"""
				self.openai_service = OpenAIService()
				self.cache_manager = CacheManager()
				self.algorithm_version = "1.0"
				
				# 추천 가중치 설정
				self.weights = {
						'rating': 0.25,          # 평점 가중치
						'distance': 0.20,        # 거리 가중치
						'price_match': 0.15,     # 가격 매칭 가중치
						'cuisine_match': 0.15,   # 요리 타입 매칭 가중치
						'user_preference': 0.15, # 사용자 선호도 가중치
						'freshness': 0.10        # 정보 신선도 가중치
				}
				
				# 성능 통계
				self.stats = {
						'total_recommendations': 0,
						'cache_hits': 0,
						'api_calls': 0,
						'average_response_time': 0.0
				}
		
		def get_recommendations(self, 
													user_id: int, 
													user_query: str,
													session_id: str = None,
													max_results: int = 5) -> Dict[str, Any]:
				"""
				사용자 질문에 대한 맛집 추천을 생성합니다.
				
				Args:
						user_id (int): 사용자 ID
						user_query (str): 사용자 질문
						session_id (str, optional): 채팅 세션 ID
						max_results (int): 최대 추천 결과 수
						
				Returns:
						Dict[str, Any]: 추천 결과와 메타데이터
				"""
				start_time = time.time()
				
				try:
						logger.info(f"추천 요청 시작: 사용자 {user_id}, 질문: {user_query[:50]}...")
						
						# 1. 사용자 정보 로드
						user = self._get_user(user_id)
						if not user:
								raise ValueError(f"사용자를 찾을 수 없습니다: {user_id}")
						
						# 2. 캐시 확인
						cache_key = self._generate_cache_key(user_id, user_query)
						cached_result = self.cache_manager.get(cache_key)
						if cached_result:
								self.stats['cache_hits'] += 1
								logger.info("캐시된 추천 결과 반환")
								return cached_result
						
						# 3. 사용자 질문 분석
						query_analysis = self._analyze_user_query(user_query, user)
						
						# 4. 후보 식당 필터링
						candidate_restaurants = self._filter_candidate_restaurants(
								query_analysis, user, max_results * 3  # 더 많은 후보에서 선별
						)
						
						# 5. 추천 점수 계산 및 순위 결정
						scored_restaurants = self._calculate_recommendation_scores(
								candidate_restaurants, query_analysis, user
						)
						
						# 6. 최종 추천 결과 선택
						final_recommendations = scored_restaurants[:max_results]
						
						# 7. 추천 이유 생성
						recommendation_reasons = self._generate_recommendation_reasons(
								final_recommendations, query_analysis
						)
						
						# 8. AI 응답 생성
						ai_response = self._generate_ai_response(
								final_recommendations, user_query, user
						)
						
						# 9. 추천 기록 저장
						recommendation_records = self._save_recommendation_records(
								user_id, final_recommendations, user_query, 
								query_analysis, session_id
						)
						
						# 10. 결과 구성
						result = {
								'success': True,
								'recommendations': [
										{
												**restaurant.to_dict(),
												'recommendation_score': restaurant.recommendation_score,
												'recommendation_reason': recommendation_reasons.get(restaurant.id, ''),
												'distance': getattr(restaurant, 'distance', None),
												'recommendation_id': recommendation_records.get(restaurant.id)
										}
										for restaurant in final_recommendations
								],
								'ai_response': ai_response,
								'query_analysis': query_analysis,
								'metadata': {
										'processing_time': time.time() - start_time,
										'algorithm_version': self.algorithm_version,
										'total_candidates': len(candidate_restaurants),
										'session_id': session_id
								}
						}
						
						# 11. 결과 캐싱
						self.cache_manager.set(cache_key, result, ttl=3600)  # 1시간 캐시
						
						# 12. 통계 업데이트
						self._update_stats(time.time() - start_time)
						
						logger.info(f"추천 완료: {len(final_recommendations)}개 식당, "
												f"소요시간: {time.time() - start_time:.2f}초")
						
						return result
						
				except Exception as e:
						logger.error(f"추천 생성 중 오류 발생: {e}")
						return {
								'success': False,
								'error': str(e),
								'recommendations': [],
								'ai_response': '죄송합니다. 추천을 생성하는 중에 오류가 발생했습니다. 다시 시도해주세요.',
								'metadata': {
										'processing_time': time.time() - start_time,
										'error_occurred': True
								}
						}
		
		def get_similar_restaurants(self, 
															restaurant_id: int, 
															limit: int = 5) -> List[Restaurant]:
				"""
				특정 식당과 유사한 식당들을 추천합니다.
				
				Args:
						restaurant_id (int): 기준 식당 ID
						limit (int): 추천할 식당 수
						
				Returns:
						List[Restaurant]: 유사한 식당 리스트
				"""
				try:
						# 기준 식당 정보 로드
						base_restaurant = Restaurant.query.get(restaurant_id)
						if not base_restaurant:
								return []
						
						# 유사도 기준 설정
						similar_restaurants = Restaurant.query.filter(
								and_(
										Restaurant.id != restaurant_id,
										Restaurant.is_active == True,
										or_(
												Restaurant.category == base_restaurant.category,
												Restaurant.cuisine_type == base_restaurant.cuisine_type
										)
								)
						).all()
						
						# 유사도 점수 계산
						for restaurant in similar_restaurants:
								restaurant.similarity_score = self._calculate_similarity_score(
										base_restaurant, restaurant
								)
						
						# 유사도 순으로 정렬하여 반환
						similar_restaurants.sort(
								key=lambda x: x.similarity_score, reverse=True
						)
						
						return similar_restaurants[:limit]
						
				except Exception as e:
						logger.error(f"유사 식당 추천 중 오류 발생: {e}")
						return []
		
		def update_user_preferences(self, 
															user_id: int, 
															feedback_data: Dict[str, Any]):
				"""
				사용자 피드백을 기반으로 선호도를 업데이트합니다.
				
				Args:
						user_id (int): 사용자 ID
						feedback_data (Dict[str, Any]): 피드백 데이터
				"""
				try:
						user = User.query.get(user_id)
						if not user:
								return
						
						# 선호도 업데이트 로직
						if feedback_data.get('liked_restaurant'):
								restaurant = Restaurant.query.get(feedback_data['liked_restaurant'])
								if restaurant:
										user.add_food_preference(restaurant.cuisine_type, 5)
						
						if feedback_data.get('disliked_aspects'):
								# 부정적 피드백 처리
								for aspect in feedback_data['disliked_aspects']:
										self._process_negative_feedback(user, aspect)
						
						# 예산 선호도 업데이트
						if feedback_data.get('preferred_price_range'):
								user.budget_range = feedback_data['preferred_price_range']
						
						db.session.commit()
						logger.info(f"사용자 {user_id} 선호도 업데이트 완료")
						
				except Exception as e:
						logger.error(f"사용자 선호도 업데이트 중 오류 발생: {e}")
		
		def get_recommendation_statistics(self) -> Dict[str, Any]:
				"""
				추천 엔진의 성능 통계를 반환합니다.
				
				Returns:
						Dict[str, Any]: 성능 통계 정보
				"""
				return {
						'engine_stats': self.stats.copy(),
						'openai_stats': self.openai_service.get_usage_stats(),
						'cache_stats': self.cache_manager.get_stats(),
						'weights': self.weights.copy(),
						'algorithm_version': self.algorithm_version
				}
		
		def _get_user(self, user_id: int) -> Optional[User]:
				"""사용자 정보를 조회합니다."""
				return User.query.get(user_id)
		
		def _analyze_user_query(self, user_query: str, user: User) -> Dict[str, Any]:
				"""
				사용자 질문을 분석하여 의도와 선호도를 추출합니다.
				
				Args:
						user_query (str): 사용자 질문
						user (User): 사용자 객체
						
				Returns:
						Dict[str, Any]: 분석된 질문 정보
				"""
				try:
						# 사용자 컨텍스트 정보 구성
						user_context = {
								'location': user.location,
								'budget_range': user.budget_range,
								'food_preferences': user.food_preferences
						}
						
						# OpenAI를 통한 질문 분석
						analysis = self.openai_service.analyze_user_query(
								user_query, user_context
						)
						
						# 분석 결과 보완
						analysis['user_location'] = user.location
						analysis['user_preferences'] = user.food_preferences
						
						return analysis
						
				except Exception as e:
						logger.error(f"질문 분석 중 오류 발생: {e}")
						return {
								'intent': 'meal_recommendation',
								'cuisine_types': [],
								'budget': 'medium',
								'keywords': user_query.split()[:5]
						}
		
		def _generate_cache_key(self, user_id: int, user_query: str) -> str:
				"""캐시 키를 생성합니다."""
				import hashlib
				
				# 질문과 사용자 ID를 조합하여 고유한 캐시 키 생성
				content = f"{user_id}:{user_query}:{datetime.now().strftime('%Y-%m-%d-%H')}"
				return f"recommendation:{hashlib.md5(content.encode()).hexdigest()}"
		
		def _update_stats(self, processing_time: float):
				"""성능 통계를 업데이트합니다."""
				self.stats['total_recommendations'] += 1
				
				# 평균 응답 시간 계산
				total_time = (self.stats['average_response_time'] * 
											(self.stats['total_recommendations'] - 1) + processing_time)
				self.stats['average_response_time'] = total_time / self.stats['total_recommendations']
		
		def _save_recommendation_records(self, 
																		user_id: int,
																		restaurants: List[Restaurant],
																		user_query: str,
																		query_analysis: Dict[str, Any],
																		session_id: str = None) -> Dict[int, int]:
				"""
				추천 기록을 데이터베이스에 저장합니다.
				
				Args:
						user_id (int): 사용자 ID
						restaurants (List[Restaurant]): 추천된 식당들
						user_query (str): 사용자 질문
						query_analysis (Dict[str, Any]): 질문 분석 결과
						session_id (str, optional): 세션 ID
						
				Returns:
						Dict[int, int]: 식당 ID별 추천 레코드 ID 매핑
				"""
				record_mapping = {}
				
				try:
						for i, restaurant in enumerate(restaurants):
								recommendation = Recommendation(
										user_id=user_id,
										restaurant_id=restaurant.id,
										user_query=user_query,
										session_id=session_id,
										algorithm_version=self.algorithm_version,
										confidence_score=getattr(restaurant, 'recommendation_score', 0.0),
										ranking_score=float(i + 1),  # 순위 점수
										recommendation_reason=getattr(restaurant, 'recommendation_reason', ''),
										extracted_preferences=query_analysis,
										ai_model_used=self.openai_service.model
								)
								
								db.session.add(recommendation)
								db.session.flush()  # ID 생성을 위해 flush
								
								record_mapping[restaurant.id] = recommendation.id
						
						db.session.commit()
						logger.info(f"추천 기록 저장 완료: {len(restaurants)}개")
						
				except Exception as e:
						logger.error(f"추천 기록 저장 중 오류 발생: {e}")
						db.session.rollback()
				
				return record_mapping
				
				
		# -*- coding: utf-8 -*-
		"""
		맛집 추천 엔진 (Part 2)
		추천 알고리즘의 핵심 계산 메소드들을 포함합니다.
		이 파일은 Part 1과 함께 사용되어야 합니다.
		"""

		def _filter_candidate_restaurants(self, 
																		query_analysis: Dict[str, Any], 
																		user: User,
																		limit: int = 15) -> List[Restaurant]:
				"""
				사용자 질문 분석 결과를 바탕으로 후보 식당들을 필터링합니다.
				
				Args:
						query_analysis (Dict[str, Any]): 질문 분석 결과
						user (User): 사용자 객체
						limit (int): 최대 후보 수
						
				Returns:
						List[Restaurant]: 필터링된 후보 식당 리스트
				"""
				try:
						# 기본 쿼리 구성 (활성 상태인 식당만)
						query = Restaurant.query.filter(Restaurant.is_active == True)
						
						# 1. 지역 필터링
						if user.location:
								query = query.filter(Restaurant.district.contains(user.location.split()[-1]))
						
						# 2. 요리 타입 필터링
						cuisine_types = query_analysis.get('cuisine_types', [])
						if cuisine_types:
								cuisine_filters = []
								for cuisine in cuisine_types:
										cuisine_filters.append(Restaurant.category.contains(cuisine))
										cuisine_filters.append(Restaurant.cuisine_type.contains(cuisine))
								query = query.filter(or_(*cuisine_filters))
						
						# 3. 예산 필터링
						budget_info = query_analysis.get('budget', 'medium')
						price_filter = self._get_price_filter(budget_info)
						if price_filter is not None:
								query = query.filter(price_filter)
						
						# 4. 특별 요구사항 필터링
						special_requirements = query_analysis.get('special_requirements', [])
						for requirement in special_requirements:
								if requirement == '주차':
										query = query.filter(Restaurant.parking_available == True)
								elif requirement == '배달':
										query = query.filter(Restaurant.delivery_available == True)
								elif requirement == '포장':
										query = query.filter(Restaurant.takeout_available == True)
						
						# 5. 평점 기준 필터링 (최소 평점 3.0 이상)
						query = query.filter(Restaurant.rating_average >= 3.0)
						
						# 6. 정렬 및 제한
						candidates = query.order_by(
								Restaurant.rating_average.desc(),
								Restaurant.rating_count.desc()
						).limit(limit * 2).all()  # 여유분 확보
						
						# 7. 거리 계산 (사용자 위치가 있는 경우)
						if user.latitude and user.longitude:
								for restaurant in candidates:
										restaurant.distance = restaurant.calculate_distance(
												user.latitude, user.longitude
										)
								
								# 거리 순으로 재정렬 (10km 이내 우선)
								candidates = [r for r in candidates if getattr(r, 'distance', 999) <= 10]
								candidates.sort(key=lambda x: getattr(x, 'distance', 999))
						
						logger.info(f"후보 식당 필터링 완료: {len(candidates)}개")
						return candidates[:limit]
						
				except Exception as e:
						logger.error(f"후보 식당 필터링 중 오류 발생: {e}")
						# 오류 시 기본 추천 (평점 높은 순)
						return Restaurant.query.filter(
								Restaurant.is_active == True,
								Restaurant.rating_average >= 3.0
						).order_by(Restaurant.rating_average.desc()).limit(limit).all()
		
		def _calculate_recommendation_scores(self, 
																				restaurants: List[Restaurant],
																				query_analysis: Dict[str, Any],
																				user: User) -> List[Restaurant]:
				"""
				각 식당에 대한 추천 점수를 계산하고 순위를 매깁니다.
				
				Args:
						restaurants (List[Restaurant]): 후보 식당들
						query_analysis (Dict[str, Any]): 질문 분석 결과
						user (User): 사용자 객체
						
				Returns:
						List[Restaurant]: 점수순으로 정렬된 식당 리스트
				"""
				try:
						for restaurant in restaurants:
								# 각 요소별 점수 계산
								rating_score = self._calculate_rating_score(restaurant)
								distance_score = self._calculate_distance_score(restaurant, user)
								price_score = self._calculate_price_score(restaurant, query_analysis)
								cuisine_score = self._calculate_cuisine_score(restaurant, query_analysis)
								preference_score = self._calculate_user_preference_score(restaurant, user)
								freshness_score = self._calculate_freshness_score(restaurant)
								
								# 가중 평균으로 최종 점수 계산
								final_score = (
										rating_score * self.weights['rating'] +
										distance_score * self.weights['distance'] +
										price_score * self.weights['price_match'] +
										cuisine_score * self.weights['cuisine_match'] +
										preference_score * self.weights['user_preference'] +
										freshness_score * self.weights['freshness']
								)
								
								# 점수를 0-1 범위로 정규화
								restaurant.recommendation_score = max(0.0, min(1.0, final_score))
								
								# 디버깅용 점수 세부사항 저장
								restaurant.score_breakdown = {
										'rating': rating_score,
										'distance': distance_score,
										'price': price_score,
										'cuisine': cuisine_score,
										'preference': preference_score,
										'freshness': freshness_score,
										'final': restaurant.recommendation_score
								}
						
						# 점수순으로 정렬
						restaurants.sort(key=lambda x: x.recommendation_score, reverse=True)
						
						logger.info("추천 점수 계산 완료")
						return restaurants
						
				except Exception as e:
						logger.error(f"추천 점수 계산 중 오류 발생: {e}")
						# 오류 시 평점순으로 정렬
						restaurants.sort(key=lambda x: x.rating_average, reverse=True)
						for i, restaurant in enumerate(restaurants):
								restaurant.recommendation_score = 1.0 - (i * 0.1)
						return restaurants
		
		def _calculate_rating_score(self, restaurant: Restaurant) -> float:
				"""
				평점 기반 점수를 계산합니다.
				
				Args:
						restaurant (Restaurant): 식당 객체
						
				Returns:
						float: 평점 점수 (0.0 - 1.0)
				"""
				# 평점과 리뷰 수를 모두 고려
				rating = restaurant.rating_average or 0.0
				review_count = restaurant.rating_count or 0
				
				# 평점 점수 (0-5 → 0-1)
				rating_normalized = rating / 5.0
				
				# 리뷰 수 보정 (더 많은 리뷰가 있으면 신뢰도 증가)
				review_bonus = min(review_count / 50.0, 0.2)  # 최대 0.2 보너스
				
				return min(1.0, rating_normalized + review_bonus)
		
		def _calculate_distance_score(self, restaurant: Restaurant, user: User) -> float:
				"""
				거리 기반 점수를 계산합니다.
				
				Args:
						restaurant (Restaurant): 식당 객체
						user (User): 사용자 객체
						
				Returns:
						float: 거리 점수 (0.0 - 1.0)
				"""
				if not hasattr(restaurant, 'distance') or restaurant.distance is None:
						return 0.7  # 거리 정보가 없으면 중간 점수
				
				distance = restaurant.distance
				
				# 거리에 따른 점수 계산 (가까울수록 높은 점수)
				if distance <= 1.0:        # 1km 이내
						return 1.0
				elif distance <= 3.0:      # 3km 이내
						return 0.8
				elif distance <= 5.0:      # 5km 이내
						return 0.6
				elif distance <= 10.0:     # 10km 이내
						return 0.4
				else:                      # 10km 초과
						return 0.2
		
		def _calculate_price_score(self, 
															restaurant: Restaurant, 
															query_analysis: Dict[str, Any]) -> float:
				"""
				가격 매칭 점수를 계산합니다.
				
				Args:
						restaurant (Restaurant): 식당 객체
						query_analysis (Dict[str, Any]): 질문 분석 결과
						
				Returns:
						float: 가격 매칭 점수 (0.0 - 1.0)
				"""
				budget_info = query_analysis.get('budget', 'medium')
				restaurant_price = restaurant.average_price or 20000
				
				# 예산별 적정 가격 범위 설정
				budget_ranges = {
						'low': (0, 15000),
						'medium': (10000, 30000),
						'high': (25000, 100000),
						'very_high': (50000, 200000)
				}
				
				# 구체적인 금액이 언급된 경우 처리
				if isinstance(budget_info, str) and '원' in budget_info:
						try:
								amount = int(''.join(filter(str.isdigit, budget_info)))
								budget_ranges['custom'] = (amount * 0.7, amount * 1.3)
								budget_info = 'custom'
						except:
								budget_info = 'medium'
				
				# 예산 범위 가져오기
				if budget_info not in budget_ranges:
						budget_info = 'medium'
				
				min_budget, max_budget = budget_ranges[budget_info]
				
				# 가격이 예산 범위 내에 있는지 확인
				if min_budget <= restaurant_price <= max_budget:
						return 1.0
				
				# 범위를 벗어난 경우 거리에 따라 점수 감소
				if restaurant_price < min_budget:
						# 너무 저렴한 경우
						diff_ratio = (min_budget - restaurant_price) / min_budget
						return max(0.3, 1.0 - diff_ratio)
				else:
						# 너무 비싼 경우
						diff_ratio = (restaurant_price - max_budget) / max_budget
						return max(0.1, 1.0 - diff_ratio)
		
		def _calculate_cuisine_score(self, 
																restaurant: Restaurant, 
																query_analysis: Dict[str, Any]) -> float:
				"""
				요리 타입 매칭 점수를 계산합니다.
				
				Args:
						restaurant (Restaurant): 식당 객체
						query_analysis (Dict[str, Any]): 질문 분석 결과
						
				Returns:
						float: 요리 타입 매칭 점수 (0.0 - 1.0)
				"""
				requested_cuisines = query_analysis.get('cuisine_types', [])
				
				if not requested_cuisines:
						return 0.5  # 특별한 요청이 없으면 중간 점수
				
				restaurant_category = restaurant.category or ''
				restaurant_cuisine = restaurant.cuisine_type or ''
				
				# 정확한 매칭 확인
				for cuisine in requested_cuisines:
						if (cuisine in restaurant_category or 
								cuisine in restaurant_cuisine or
								self._is_similar_cuisine(cuisine, restaurant_category)):
								return 1.0
				
				# 부분 매칭 확인
				for cuisine in requested_cuisines:
						if (self._partial_cuisine_match(cuisine, restaurant_category) or
								self._partial_cuisine_match(cuisine, restaurant_cuisine)):
								return 0.7
				
				return 0.2  # 매칭되지 않는 경우
		
		def _calculate_user_preference_score(self, 
																				restaurant: Restaurant, 
																				user: User) -> float:
				"""
				사용자 개인 선호도 기반 점수를 계산합니다.
				
				Args:
						restaurant (Restaurant): 식당 객체
						user (User): 사용자 객체
						
				Returns:
						float: 개인 선호도 점수 (0.0 - 1.0)
				"""
				if not user.food_preferences:
						return 0.5  # 선호도 정보가 없으면 중간 점수
				
				score = 0.5  # 기본 점수
				preferences = user.food_preferences
				
				# 선호하는 요리 타입 확인
				favorite_cuisines = preferences.get('favorite_cuisines', [])
				for cuisine_info in favorite_cuisines:
						if isinstance(cuisine_info, dict):
								cuisine_type = cuisine_info.get('type', '')
								preference_level = cuisine_info.get('level', 3)
								
								if (cuisine_type in restaurant.category or 
										cuisine_type in restaurant.cuisine_type):
										score += (preference_level / 5.0) * 0.3
				
				# 분위기 선호도 확인
				atmosphere_pref = preferences.get('atmosphere_preference', 'casual')
				restaurant_atmosphere = restaurant.atmosphere_tags or []
				
				if atmosphere_pref in restaurant_atmosphere:
						score += 0.2
				
				# 매운맛 선호도 확인
				spice_level = preferences.get('spice_level', 'medium')
				if '매운' in restaurant.name or '불' in restaurant.name:
						if spice_level == 'hot':
								score += 0.2
						elif spice_level == 'mild':
								score -= 0.2
				
				return min(1.0, max(0.0, score))
		
		def _calculate_freshness_score(self, restaurant: Restaurant) -> float:
				"""
				정보의 신선도 점수를 계산합니다.
				
				Args:
						restaurant (Restaurant): 식당 객체
						
				Returns:
						float: 신선도 점수 (0.0 - 1.0)
				"""
				if not restaurant.updated_at:
						return 0.3  # 업데이트 정보가 없으면 낮은 점수
				
				# 마지막 업데이트로부터 경과된 시간 계산
				time_diff = datetime.utcnow() - restaurant.updated_at
				days_old = time_diff.days
				
				# 신선도 점수 계산
				if days_old <= 7:        # 1주일 이내
						return 1.0
				elif days_old <= 30:     # 1개월 이내
						return 0.8
				elif days_old <= 90:     # 3개월 이내
						return 0.6
				elif days_old <= 180:    # 6개월 이내
						return 0.4
				else:                    # 6개월 초과
						return 0.2
		
		def _calculate_similarity_score(self, 
																	base_restaurant: Restaurant, 
																	target_restaurant: Restaurant) -> float:
				"""
				두 식당 간의 유사도 점수를 계산합니다.
				
				Args:
						base_restaurant (Restaurant): 기준 식당
						target_restaurant (Restaurant): 비교 대상 식당
						
				Returns:
						float: 유사도 점수 (0.0 - 1.0)
				"""
				score = 0.0
				
				# 카테고리 유사도 (30%)
				if base_restaurant.category == target_restaurant.category:
						score += 0.3
				elif (base_restaurant.cuisine_type and target_restaurant.cuisine_type and
							base_restaurant.cuisine_type == target_restaurant.cuisine_type):
						score += 0.2
				
				# 가격대 유사도 (25%)
				base_price = base_restaurant.average_price or 20000
				target_price = target_restaurant.average_price or 20000
				price_diff_ratio = abs(base_price - target_price) / max(base_price, target_price)
				price_similarity = max(0, 1 - price_diff_ratio)
				score += price_similarity * 0.25
				
				# 평점 유사도 (20%)
				base_rating = base_restaurant.rating_average or 3.0
				target_rating = target_restaurant.rating_average or 3.0
				rating_diff = abs(base_rating - target_rating)
				rating_similarity = max(0, 1 - rating_diff / 5.0)
				score += rating_similarity * 0.2
				
				# 위치 유사도 (15%)
				if base_restaurant.district == target_restaurant.district:
						score += 0.15
				elif base_restaurant.neighborhood == target_restaurant.neighborhood:
						score += 0.1
				
				# 특징 유사도 (10%)
				base_features = set(base_restaurant.special_features or [])
				target_features = set(target_restaurant.special_features or [])
				if base_features and target_features:
						common_features = base_features.intersection(target_features)
						feature_similarity = len(common_features) / len(base_features.union(target_features))
						score += feature_similarity * 0.1
				
				return min(1.0, score)
		
		def _get_price_filter(self, budget_info: str):
				"""예산 정보를 바탕으로 SQLAlchemy 필터를 생성합니다."""
				if budget_info == 'low':
						return Restaurant.average_price <= 15000
				elif budget_info == 'medium':
						return and_(Restaurant.average_price >= 10000, Restaurant.average_price <= 30000)
				elif budget_info == 'high':
						return Restaurant.average_price >= 25000
				else:
						return None  # 필터링하지 않음
		
		def _is_similar_cuisine(self, requested: str, restaurant_cuisine: str) -> bool:
				"""요리 타입이 유사한지 확인합니다."""
				similarity_map = {
						'한식': ['한국', '전통', '국물', '찌개', '불고기'],
						'중식': ['중국', '짜장', '짬뽕', '탕수육'],
						'일식': ['일본', '초밥', '라멘', '우동', '돈카츠'],
						'양식': ['서양', '스테이크', '파스타', '피자'],
						'치킨': ['닭', '후라이드', '양념'],
						'고기': ['소고기', '돼지고기', '갈비', '삼겹살']
				}
				
				similar_terms = similarity_map.get(requested, [])
				return any(term in restaurant_cuisine for term in similar_terms)
		
		def _partial_cuisine_match(self, requested: str, restaurant_cuisine: str) -> bool:
				"""부분적인 요리 타입 매칭을 확인합니다."""
				return any(char in restaurant_cuisine for char in requested if len(char) > 1)				
				
		# -*- coding: utf-8 -*-
		"""
		맛집 추천 엔진 (Part 3)
		AI 응답 생성 및 추천 이유 설명 메소드들을 포함합니다.
		이 파일은 Part 1, 2와 함께 사용되어야 합니다.
		"""

		def _generate_recommendation_reasons(self, 
																				restaurants: List[Restaurant],
																				query_analysis: Dict[str, Any]) -> Dict[int, str]:
				"""
				각 추천 식당에 대한 추천 이유를 생성합니다.
				
				Args:
						restaurants (List[Restaurant]): 추천된 식당들
						query_analysis (Dict[str, Any]): 질문 분석 결과
						
				Returns:
						Dict[int, str]: 식당 ID별 추천 이유 매핑
				"""
				reasons = {}
				
				try:
						for i, restaurant in enumerate(restaurants):
								reason_parts = []
								
								# 1. 순위 기반 이유
								if i == 0:
										reason_parts.append("가장 적합한 추천")
								elif i == 1:
										reason_parts.append("두 번째 추천")
								else:
										reason_parts.append(f"{i+1}번째 추천")
								
								# 2. 평점 기반 이유
								if restaurant.rating_average >= 4.5:
										reason_parts.append("매우 높은 평점")
								elif restaurant.rating_average >= 4.0:
										reason_parts.append("높은 평점")
								
								# 3. 거리 기반 이유
								if hasattr(restaurant, 'distance') and restaurant.distance:
										if restaurant.distance <= 1.0:
												reason_parts.append("가까운 거리")
										elif restaurant.distance <= 3.0:
												reason_parts.append("적당한 거리")
								
								# 4. 가격 기반 이유
								budget = query_analysis.get('budget', 'medium')
								if budget == 'low' and restaurant.average_price <= 15000:
										reason_parts.append("합리적인 가격")
								elif budget == 'high' and restaurant.average_price >= 30000:
										reason_parts.append("프리미엄 경험")
								
								# 5. 요리 타입 기반 이유
								requested_cuisines = query_analysis.get('cuisine_types', [])
								for cuisine in requested_cuisines:
										if (cuisine in restaurant.category or 
												cuisine in (restaurant.cuisine_type or '')):
												reason_parts.append(f"{cuisine} 전문점")
												break
								
								# 6. 특별 기능 기반 이유
								special_requirements = query_analysis.get('special_requirements', [])
								for req in special_requirements:
										if req == '주차' and restaurant.parking_available:
												reason_parts.append("주차 가능")
										elif req == '배달' and restaurant.delivery_available:
												reason_parts.append("배달 가능")
								
								# 7. 시간대 기반 이유
								if restaurant.is_open_now():
										reason_parts.append("현재 영업 중")
								
								# 추천 이유 조합
								if len(reason_parts) > 1:
										main_reason = reason_parts[0]
										sub_reasons = ", ".join(reason_parts[1:3])  # 최대 3개까지
										reasons[restaurant.id] = f"{main_reason} - {sub_reasons}"
								else:
										reasons[restaurant.id] = reason_parts[0] if reason_parts else "맞춤 추천"
						
				except Exception as e:
						logger.error(f"추천 이유 생성 중 오류 발생: {e}")
						# 오류 시 기본 이유 제공
						for i, restaurant in enumerate(restaurants):
								reasons[restaurant.id] = f"{i+1}번째 추천 - 평점 {restaurant.rating_average}/5.0"
				
				return reasons
		
		def _generate_ai_response(self, 
														restaurants: List[Restaurant],
														user_query: str,
														user: User) -> str:
				"""
				AI를 통해 자연스러운 추천 응답을 생성합니다.
				
				Args:
						restaurants (List[Restaurant]): 추천된 식당들
						user_query (str): 사용자 질문
						user (User): 사용자 객체
						
				Returns:
						str: 생성된 AI 응답
				"""
				try:
						# 식당 정보를 AI가 이해할 수 있는 형태로 변환
						restaurant_data = []
						for restaurant in restaurants:
								data = {
										'name': restaurant.name,
										'category': restaurant.category,
										'address': restaurant.address,
										'rating_average': restaurant.rating_average,
										'rating_count': restaurant.rating_count,
										'average_price': restaurant.average_price,
										'today_hours': restaurant.get_today_hours(),
										'special_features': restaurant.special_features or [],
										'distance': getattr(restaurant, 'distance', None),
										'recommendation_score': getattr(restaurant, 'recommendation_score', 0)
								}
								restaurant_data.append(data)
						
						# 사용자 선호도 정보
						user_preferences = {
								'location': user.location,
								'budget_range': user.budget_range,
								'food_preferences': user.food_preferences
						}
						
						# OpenAI를 통한 응답 생성
						ai_response = self.openai_service.generate_recommendation_response(
								restaurant_data, user_query, user_preferences
						)
						
						return ai_response
						
				except Exception as e:
						logger.error(f"AI 응답 생성 중 오류 발생: {e}")
						return self._generate_fallback_response(restaurants, user_query)
		
		def _generate_fallback_response(self, 
																	restaurants: List[Restaurant],
																	user_query: str) -> str:
				"""
				AI 응답 생성에 실패했을 때 사용할 대체 응답을 생성합니다.
				
				Args:
						restaurants (List[Restaurant]): 추천된 식당들
						user_query (str): 사용자 질문
						
				Returns:
						str: 대체 응답 텍스트
				"""
				if not restaurants:
						return ("죄송합니다. 조건에 맞는 식당을 찾지 못했습니다. 😅\n"
										"조건을 조금 바꿔서 다시 질문해주시면 더 좋은 추천을 드릴 수 있을 것 같아요!")
				
				response = f"'{user_query}'에 대한 추천 결과입니다! 🍽️\n\n"
				
				for i, restaurant in enumerate(restaurants[:3], 1):  # 최대 3개까지
						response += f"{i}. **{restaurant.name}**\n"
						response += f"   📍 {restaurant.address}\n"
						response += f"   ⭐ {restaurant.rating_average}/5.0 ({restaurant.rating_count}개 리뷰)\n"
						
						if restaurant.average_price:
								response += f"   💰 평균 {restaurant.average_price:,}원\n"
						
						if hasattr(restaurant, 'distance') and restaurant.distance:
								response += f"   🚶 약 {restaurant.distance}km\n"
						
						response += f"   ⏰ {restaurant.get_today_hours()}\n\n"
				
				response += "더 자세한 정보가 필요하시면 언제든 물어보세요! 😊"
				
				return response
		
		def _post_process_response(self, 
															ai_response: str, 
															restaurants: List[Restaurant]) -> str:
				"""
				AI 응답을 후처리하여 최종 응답을 생성합니다.
				
				Args:
						ai_response (str): AI가 생성한 응답
						restaurants (List[Restaurant]): 추천된 식당들
						
				Returns:
						str: 후처리된 최종 응답
				"""
				try:
						# 응답 길이 체크 및 조정
						if len(ai_response) > 2000:  # 너무 긴 응답은 줄임
								ai_response = ai_response[:1800] + "...\n\n더 자세한 정보는 개별 식당을 선택해주세요!"
						
						# 이모지가 없으면 추가
						if '🍽️' not in ai_response and '😊' not in ai_response:
								ai_response = ai_response.rstrip() + " 🍽️"
						
						# 식당 이름 볼드 처리 (마크다운 형식)
						for restaurant in restaurants:
								restaurant_name = restaurant.name
								if restaurant_name in ai_response and f"**{restaurant_name}**" not in ai_response:
										ai_response = ai_response.replace(restaurant_name, f"**{restaurant_name}**")
						
						# 마무리 멘트 추가 (없는 경우)
						if not any(ending in ai_response.lower() for ending in 
											['도움', '질문', '문의', '추천', '궁금', '언제든']):
								ai_response += "\n\n더 궁금한 점이 있으시면 언제든 말씀해주세요!"
						
						return ai_response
						
				except Exception as e:
						logger.error(f"응답 후처리 중 오류 발생: {e}")
						return ai_response  # 오류 시 원본 반환
		
		def _process_negative_feedback(self, user: User, negative_aspect: str):
				"""
				사용자의 부정적 피드백을 처리하여 선호도를 조정합니다.
				
				Args:
						user (User): 사용자 객체
						negative_aspect (str): 부정적 요소
				"""
				try:
						current_preferences = user.food_preferences or {}
						
						# 부정적 피드백에 따른 선호도 조정
						if '매운' in negative_aspect:
								current_preferences['spice_level'] = 'mild'
						elif '비싸' in negative_aspect or '가격' in negative_aspect:
								current_preferences['price_sensitivity'] = 'high'
						elif '시끄' in negative_aspect or '시간' in negative_aspect:
								current_preferences['atmosphere_preference'] = 'quiet'
						elif '서비스' in negative_aspect:
								# 서비스가 좋은 식당 위주로 추천하도록 가중치 조정
								pass
						
						user.food_preferences = current_preferences
						
				except Exception as e:
						logger.error(f"부정적 피드백 처리 중 오류 발생: {e}")
		
		def get_trending_restaurants(self, limit: int = 10) -> List[Restaurant]:
				"""
				최근 인기 상승 중인 식당들을 반환합니다.
				
				Args:
						limit (int): 반환할 식당 수
						
				Returns:
						List[Restaurant]: 인기 상승 식당 리스트
				"""
				try:
						# 최근 30일간의 추천 및 리뷰 데이터를 기반으로 트렌딩 계산
						recent_date = datetime.utcnow() - timedelta(days=30)
						
						# 서브쿼리: 최근 추천 수
						recent_recommendations = db.session.query(
								Recommendation.restaurant_id,
								func.count(Recommendation.id).label('recent_rec_count')
						).filter(
								Recommendation.created_at >= recent_date
						).group_by(Recommendation.restaurant_id).subquery()
						
						# 서브쿼리: 최근 리뷰 수
						recent_reviews = db.session.query(
								Review.restaurant_id,
								func.count(Review.id).label('recent_review_count'),
								func.avg(Review.rating).label('recent_avg_rating')
						).filter(
								Review.created_at >= recent_date
						).group_by(Review.restaurant_id).subquery()
						
						# 메인 쿼리: 트렌딩 식당 조회
						trending_query = db.session.query(Restaurant).outerjoin(
								recent_recommendations, 
								Restaurant.id == recent_recommendations.c.restaurant_id
						).outerjoin(
								recent_reviews,
								Restaurant.id == recent_reviews.c.restaurant_id
						).filter(
								Restaurant.is_active == True
						)
						
						restaurants = trending_query.all()
						
						# 트렌딩 점수 계산
						for restaurant in restaurants:
								rec_count = getattr(restaurant, 'recent_rec_count', 0) or 0
								review_count = getattr(restaurant, 'recent_review_count', 0) or 0
								recent_rating = getattr(restaurant, 'recent_avg_rating', 0) or 0
								
								# 트렌딩 점수 = (최근 추천 수 * 2 + 최근 리뷰 수) * 최근 평점
								trending_score = (rec_count * 2 + review_count) * (recent_rating / 5.0)
								restaurant.trending_score = trending_score
						
						# 트렌딩 점수 순으로 정렬
						restaurants.sort(key=lambda x: getattr(x, 'trending_score', 0), reverse=True)
						
						return restaurants[:limit]
						
				except Exception as e:
						logger.error(f"트렌딩 식당 조회 중 오류 발생: {e}")
						# 오류 시 최근 평점이 높은 식당들 반환
						return Restaurant.query.filter(
								Restaurant.is_active == True,
								Restaurant.rating_average >= 4.0
						).order_by(Restaurant.rating_average.desc()).limit(limit).all()
		
		def get_personalized_suggestions(self, user_id: int, limit: int = 5) -> List[Restaurant]:
				"""
				사용자의 과거 선호도를 기반으로 개인화된 추천을 제공합니다.
				
				Args:
						user_id (int): 사용자 ID
						limit (int): 추천할 식당 수
						
				Returns:
						List[Restaurant]: 개인화된 추천 식당 리스트
				"""
				try:
						user = User.query.get(user_id)
						if not user:
								return []
						
						# 사용자의 과거 추천 및 리뷰 이력 분석
						past_recommendations = Recommendation.query.filter_by(
								user_id=user_id
						).order_by(Recommendation.created_at.desc()).limit(50).all()
						
						# 선호 카테고리 추출
						preferred_categories = {}
						for rec in past_recommendations:
								if rec.restaurant and rec.user_feedback == 'visited':
										category = rec.restaurant.category
										preferred_categories[category] = preferred_categories.get(category, 0) + 1
						
						# 가장 선호하는 카테고리들
						top_categories = sorted(preferred_categories.items(), 
																	key=lambda x: x[1], reverse=True)[:3]
						
						if not top_categories:
								# 선호도 데이터가 없으면 일반적인 고평점 식당 추천
								return Restaurant.query.filter(
										Restaurant.is_active == True,
										Restaurant.rating_average >= 4.0
								).order_by(Restaurant.rating_average.desc()).limit(limit).all()
						
						# 선호 카테고리의 식당들 중에서 아직 추천받지 않은 곳들
						recommended_restaurant_ids = [rec.restaurant_id for rec in past_recommendations]
						
						suggestions = []
						for category, _ in top_categories:
								category_restaurants = Restaurant.query.filter(
										Restaurant.category.contains(category),
										Restaurant.is_active == True,
										Restaurant.rating_average >= 3.5,
										~Restaurant.id.in_(recommended_restaurant_ids)
								).order_by(Restaurant.rating_average.desc()).limit(3).all()
								
								suggestions.extend(category_restaurants)
						
						# 중복 제거 및 순서 조정
						unique_suggestions = []
						seen_ids = set()
						for restaurant in suggestions:
								if restaurant.id not in seen_ids:
										unique_suggestions.append(restaurant)
										seen_ids.add(restaurant.id)
						
						return unique_suggestions[:limit]
						
				except Exception as e:
						logger.error(f"개인화된 추천 생성 중 오류 발생: {e}")
						return []