# -*- coding: utf-8 -*-
"""
식당 API 엔드포인트
식당 정보 조회, 검색, 관리를 위한 REST API입니다.
"""

import logging
from flask import Blueprint, request, jsonify
from sqlalchemy import and_, or_
from app.models.restaurant import Restaurant
from app.models.review import Review
from app.services.database_manager import DatabaseManager
from app.services.map_renderer import MapRenderer
from app import db

logger = logging.getLogger(__name__)

# 블루프린트 생성
restaurants_bp = Blueprint('restaurants', __name__)

# 서비스 인스턴스 생성
db_manager = DatabaseManager()
map_renderer = MapRenderer()

@restaurants_bp.route('/', methods=['GET'])
def get_restaurants():
		"""
		식당 목록을 조회합니다.
		
		Query Parameters:
				page: int (optional, default: 1) - 페이지 번호
				per_page: int (optional, default: 20) - 페이지당 결과 수
				category: str (optional) - 카테고리 필터
				district: str (optional) - 지역 필터
				min_rating: float (optional) - 최소 평점
				max_price: int (optional) - 최대 가격
				sort_by: str (optional) - 정렬 기준
				search: str (optional) - 검색 키워드
		
		Returns:
				{
						"success": bool,
						"restaurants": list,
						"pagination": dict,
						"filters_applied": dict,
						"error": str (if error)
				}
		"""
		try:
				# 쿼리 파라미터 파싱
				page = request.args.get('page', 1, type=int)
				per_page = min(request.args.get('per_page', 20, type=int), 50)  # 최대 50개로 제한
				category = request.args.get('category')
				district = request.args.get('district')
				min_rating = request.args.get('min_rating', type=float)
				max_price = request.args.get('max_price', type=int)
				sort_by = request.args.get('sort_by', 'rating')
				search = request.args.get('search')
				
				# 검색 조건 구성
				search_params = {}
				if category:
						search_params['category'] = category
				if district:
						search_params['district'] = district
				if min_rating:
						search_params['min_rating'] = min_rating
				if max_price:
						search_params['max_price'] = max_price
				if sort_by:
						search_params['sort_by'] = sort_by
				if search:
						search_params['name'] = search
				
				# 데이터베이스 검색
				result = db_manager.search_restaurants(search_params, page, per_page)
				
				if result['success']:
						return jsonify({
								'success': True,
								'restaurants': result['restaurants'],
								'pagination': result['pagination'],
								'filters_applied': search_params
						}), 200
				else:
						return jsonify({
								'success': False,
								'error': result.get('error', '검색 중 오류가 발생했습니다.'),
								'restaurants': []
						}), 500
				
		except ValueError as e:
				return jsonify({
						'success': False,
						'error': f'잘못된 파라미터: {str(e)}'
				}), 400
		except Exception as e:
				logger.error(f"식당 목록 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '식당 목록 조회 중 오류가 발생했습니다.'
				}), 500

@restaurants_bp.route('/<int:restaurant_id>', methods=['GET'])
def get_restaurant_detail(restaurant_id):
		"""
		특정 식당의 상세 정보를 조회합니다.
		
		Query Parameters:
				include_reviews: bool (optional, default: true) - 리뷰 포함 여부
				include_map: bool (optional, default: true) - 지도 정보 포함 여부
				user_lat: float (optional) - 사용자 위도 (경로 계산용)
				user_lng: float (optional) - 사용자 경도 (경로 계산용)
		
		Returns:
				{
						"success": bool,
						"restaurant": dict,
						"recent_reviews": list,
						"map_info": dict,
						"directions": dict,
						"error": str (if error)
				}
		"""
		try:
				include_reviews = request.args.get('include_reviews', 'true').lower() == 'true'
				include_map = request.args.get('include_map', 'true').lower() == 'true'
				user_lat = request.args.get('user_lat', type=float)
				user_lng = request.args.get('user_lng', type=float)
				
				# 식당 조회
				restaurant = Restaurant.query.get(restaurant_id)
				if not restaurant or not restaurant.is_active:
						return jsonify({
								'success': False,
								'error': '식당을 찾을 수 없습니다.'
						}), 404
				
				# 기본 식당 정보
				result = {
						'success': True,
						'restaurant': restaurant.to_dict(include_reviews=False)
				}
				
				# 최근 리뷰 포함
				if include_reviews:
						recent_reviews = Review.query.filter(
								Review.restaurant_id == restaurant_id,
								Review.is_active == True
						).order_by(Review.created_at.desc()).limit(5).all()
						
						result['recent_reviews'] = [
								review.to_dict(include_user=True) for review in recent_reviews
						]
				
				# 지도 및 경로 정보 포함
				if include_map:
						user_location = None
						if user_lat and user_lng:
								user_location = (user_lat, user_lng)
						
						map_info = map_renderer.get_restaurant_directions_info(
								restaurant.to_dict(), user_location
						)
						
						result['map_info'] = {
								'map_url': map_info.get('map_url'),
								'nearby_landmarks': map_info.get('nearby_landmarks', [])
						}
						
						if map_info.get('directions'):
								result['directions'] = map_info['directions']
				
				# 거리 계산 (사용자 위치가 있는 경우)
				if user_lat and user_lng:
						distance = restaurant.calculate_distance(user_lat, user_lng)
						if distance:
								result['restaurant']['distance_km'] = distance
				
				return jsonify(result), 200
				
		except Exception as e:
				logger.error(f"식당 상세 정보 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '식당 정보 조회 중 오류가 발생했습니다.'
				}), 500

@restaurants_bp.route('/<int:restaurant_id>/menu', methods=['GET'])
def get_restaurant_menu(restaurant_id):
		"""
		식당의 메뉴 정보를 조회합니다.
		
		Returns:
				{
						"success": bool,
						"menu": dict,
						"menu_categories": list,
						"price_range": dict,
						"error": str (if error)
				}
		"""
		try:
				restaurant = Restaurant.query.get(restaurant_id)
				if not restaurant or not restaurant.is_active:
						return jsonify({
								'success': False,
								'error': '식당을 찾을 수 없습니다.'
						}), 404
				
				# 카테고리별 메뉴 정리
				categorized_menu = restaurant.get_menu_by_category()
				
				# 메뉴 카테고리 목록
				categories = list(categorized_menu.keys())
				
				# 가격 범위 계산
				prices = []
				for items in categorized_menu.values():
						for item in items:
								if item.get('price'):
										prices.append(item['price'])
				
				price_range = {}
				if prices:
						price_range = {
								'min': min(prices),
								'max': max(prices),
								'average': restaurant.average_price
						}
				
				return jsonify({
						'success': True,
						'menu': categorized_menu,
						'menu_categories': categories,
						'price_range': price_range,
						'restaurant_name': restaurant.name
				}), 200
				
		except Exception as e:
				logger.error(f"메뉴 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '메뉴 조회 중 오류가 발생했습니다.'
				}), 500

@restaurants_bp.route('/<int:restaurant_id>/hours', methods=['GET'])
def get_restaurant_hours(restaurant_id):
		"""
		식당의 운영시간 정보를 조회합니다.
		
		Returns:
				{
						"success": bool,
						"business_hours": dict,
						"is_open_now": bool,
						"today_hours": str,
						"next_opening": str,
						"error": str (if error)
				}
		"""
		try:
				restaurant = Restaurant.query.get(restaurant_id)
				if not restaurant or not restaurant.is_active:
						return jsonify({
								'success': False,
								'error': '식당을 찾을 수 없습니다.'
						}), 404
				
				# 현재 영업 상태
				is_open_now = restaurant.is_open_now()
				
				# 오늘 운영시간
				today_hours = restaurant.get_today_hours()
				
				# 다음 영업 시간 계산 (간단한 버전)
				next_opening = "정보 없음"
				if not is_open_now and restaurant.business_hours:
						# 실제 구현에서는 더 정교한 로직 필요
						next_opening = "내일 영업시간을 확인해주세요"
				
				return jsonify({
						'success': True,
						'business_hours': restaurant.business_hours or {},
						'closed_days': restaurant.closed_days or [],
						'is_open_now': is_open_now,
						'today_hours': today_hours,
						'next_opening': next_opening,
						'restaurant_name': restaurant.name
				}), 200
				
		except Exception as e:
				logger.error(f"운영시간 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '운영시간 조회 중 오류가 발생했습니다.'
				}), 500

@restaurants_bp.route('/categories', methods=['GET'])
def get_restaurant_categories():
		"""
		식당 카테고리 목록을 조회합니다.
		
		Returns:
				{
						"success": bool,
						"categories": list,
						"category_counts": dict,
						"error": str (if error)
				}
		"""
		try:
				# 활성 식당들의 카테고리 조회
				categories_query = db.session.query(
						Restaurant.category,
						db.func.count(Restaurant.id).label('count')
				).filter(
						Restaurant.is_active == True
				).group_by(Restaurant.category).order_by(
						db.func.count(Restaurant.id).desc()
				).all()
				
				categories = [cat[0] for cat in categories_query if cat[0]]
				category_counts = {cat[0]: cat[1] for cat in categories_query if cat[0]}
				
				return jsonify({
						'success': True,
						'categories': categories,
						'category_counts': category_counts
				}), 200
				
		except Exception as e:
				logger.error(f"카테고리 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '카테고리 조회 중 오류가 발생했습니다.'
				}), 500

@restaurants_bp.route('/districts', methods=['GET'])
def get_restaurant_districts():
		"""
		식당이 위치한 지역 목록을 조회합니다.
		
		Returns:
				{
						"success": bool,
						"districts": list,
						"district_counts": dict,
						"error": str (if error)
				}
		"""
		try:
				# 활성 식당들의 지역 조회
				districts_query = db.session.query(
						Restaurant.district,
						db.func.count(Restaurant.id).label('count')
				).filter(
						Restaurant.is_active == True,
						Restaurant.district.isnot(None)
				).group_by(Restaurant.district).order_by(
						db.func.count(Restaurant.id).desc()
				).all()
				
				districts = [dist[0] for dist in districts_query if dist[0]]
				district_counts = {dist[0]: dist[1] for dist in districts_query if dist[0]}
				
				return jsonify({
						'success': True,
						'districts': districts,
						'district_counts': district_counts
				}), 200
				
		except Exception as e:
				logger.error(f"지역 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '지역 조회 중 오류가 발생했습니다.'
				}), 500

@restaurants_bp.route('/search/suggestions', methods=['GET'])
def get_search_suggestions():
		"""
		검색 자동완성을 위한 제안을 제공합니다.
		
		Query Parameters:
				q: str (required) - 검색 키워드
				limit: int (optional, default: 10) - 최대 제안 수
		
		Returns:
				{
						"success": bool,
						"suggestions": list,
						"suggestion_types": dict,
						"error": str (if error)
				}
		"""
		try:
				query = request.args.get('q', '').strip()
				limit = min(request.args.get('limit', 10, type=int), 20)
				
				if not query or len(query) < 2:
						return jsonify({
								'success': False,
								'error': '검색어는 최소 2자 이상이어야 합니다.'
						}), 400
				
				suggestions = []
				suggestion_types = {
						'restaurants': [],
						'categories': [],
						'districts': []
				}
				
				# 식당명 검색
				restaurant_matches = Restaurant.query.filter(
						Restaurant.is_active == True,
						Restaurant.name.contains(query)
				).limit(limit // 2).all()
				
				for restaurant in restaurant_matches:
						suggestion = {
								'text': restaurant.name,
								'type': 'restaurant',
								'id': restaurant.id,
								'category': restaurant.category,
								'rating': restaurant.rating_average
						}
						suggestions.append(suggestion)
						suggestion_types['restaurants'].append(suggestion)
				
				# 카테고리 검색
				category_matches = db.session.query(Restaurant.category).filter(
						Restaurant.is_active == True,
						Restaurant.category.contains(query)
				).distinct().limit(3).all()
				
				for category_tuple in category_matches:
						category = category_tuple[0]
						if category:
								suggestion = {
										'text': category,
										'type': 'category'
								}
								suggestions.append(suggestion)
								suggestion_types['categories'].append(suggestion)
				
				# 지역 검색
				district_matches = db.session.query(Restaurant.district).filter(
						Restaurant.is_active == True,
						Restaurant.district.contains(query)
				).distinct().limit(3).all()
				
				for district_tuple in district_matches:
						district = district_tuple[0]
						if district:
								suggestion = {
										'text': district,
										'type': 'district'
								}
								suggestions.append(suggestion)
								suggestion_types['districts'].append(suggestion)
				
				return jsonify({
						'success': True,
						'suggestions': suggestions[:limit],
						'suggestion_types': suggestion_types,
						'query': query
				}), 200
				
		except Exception as e:
				logger.error(f"검색 제안 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '검색 제안 조회 중 오류가 발생했습니다.'
				}), 500

@restaurants_bp.route('/trending', methods=['GET'])
def get_trending_restaurants():
		"""
		최근 인기 상승 중인 식당들을 조회합니다.
		
		Query Parameters:
				limit: int (optional, default: 10) - 조회할 식당 수
		
		Returns:
				{
						"success": bool,
						"trending_restaurants": list,
						"period": str,
						"error": str (if error)
				}
		"""
		try:
				limit = min(request.args.get('limit', 10, type=int), 20)
				
				# 추천 엔진에서 트렌딩 식당 조회
				from app.services.recommendation_engine import RecommendationEngine
				recommendation_engine = RecommendationEngine()
				
				trending_restaurants = recommendation_engine.get_trending_restaurants(limit)
				
				# 결과 포맷팅
				restaurants_data = []
				for restaurant in trending_restaurants:
						restaurant_dict = restaurant.to_dict()
						restaurant_dict['trending_score'] = getattr(restaurant, 'trending_score', 0)
						restaurants_data.append(restaurant_dict)
				
				return jsonify({
						'success': True,
						'trending_restaurants': restaurants_data,
						'period': '최근 30일',
						'generated_at': db.func.now()
				}), 200
				
		except Exception as e:
				logger.error(f"트렌딩 식당 조회 중 오류 발생: {e}")
				return jsonify({
						'success': False,
						'error': '트렌딩 식당 조회 중 오류가 발생했습니다.'
				}), 500

# 에러 핸들러
@restaurants_bp.errorhandler(400)
def bad_request(error):
		"""잘못된 요청 에러 핸들러"""
		return jsonify({
				'success': False,
				'error': '잘못된 요청입니다.',
				'status_code': 400
		}), 400

@restaurants_bp.errorhandler(404)
def not_found(error):
		"""리소스를 찾을 수 없음 에러 핸들러"""
		return jsonify({
				'success': False,
				'error': '요청한 식당을 찾을 수 없습니다.',
				'status_code': 404
		}), 404