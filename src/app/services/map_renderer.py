# -*- coding: utf-8 -*-
"""
지도 렌더링 서비스 (MapRenderer)
Google Maps API를 활용해 식당 위치 시각화와 경로 안내를 제공합니다.
"""

import logging
import json
import requests
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlencode
from app.config.settings import Config

logger = logging.getLogger(__name__)

class MapRenderer:
		"""
		Google Maps API를 통한 지도 시각화와 위치 서비스를 제공하는 클래스
		식당 위치 표시, 경로 계산, 주변 정보 검색을 담당합니다.
		"""
		
		def __init__(self):
				"""
				지도 렌더러 초기화
				Google Maps API 키와 기본 설정을 구성합니다.
				"""
				self.api_key = Config.GOOGLE_MAPS_API_KEY
				self.default_location = Config.DEFAULT_LOCATION
				
				# API 엔드포인트들
				self.endpoints = {
						'geocoding': 'https://maps.googleapis.com/maps/api/geocode/json',
						'places': 'https://maps.googleapis.com/maps/api/place/nearbysearch/json',
						'directions': 'https://maps.googleapis.com/maps/api/directions/json',
						'static_map': 'https://maps.googleapis.com/maps/api/staticmap'
				}
				
				# 기본 지도 설정
				self.default_map_config = {
						'zoom': 15,
						'size': '600x400',
						'maptype': 'roadmap',
						'language': 'ko',
						'region': 'KR'
				}
				
				# 마커 색상 설정
				self.marker_colors = {
						'restaurant': 'red',
						'user': 'blue',
						'recommended': 'green',
						'alternative': 'orange'
				}
				
				# API 사용량 통계
				self.stats = {
						'geocoding_calls': 0,
						'places_calls': 0,
						'directions_calls': 0,
						'static_map_calls': 0,
						'errors': 0
				}
		
		def get_restaurant_map_url(self, 
															restaurants: List[Dict[str, Any]],
															user_location: Optional[Tuple[float, float]] = None,
															map_config: Optional[Dict[str, str]] = None) -> str:
				"""
				여러 식당의 위치를 표시하는 정적 지도 URL을 생성합니다.
				
				Args:
						restaurants (List[Dict[str, Any]]): 식당 정보 리스트
						user_location (Optional[Tuple[float, float]]): 사용자 위치 (위도, 경도)
						map_config (Optional[Dict[str, str]]): 지도 설정
						
				Returns:
						str: Google Static Maps URL
				"""
				try:
						# 지도 설정 병합
						config = {**self.default_map_config}
						if map_config:
								config.update(map_config)
						
						# 기본 파라미터
						params = {
								'key': self.api_key,
								'size': config['size'],
								'zoom': config['zoom'],
								'maptype': config['maptype'],
								'language': config['language'],
								'region': config['region']
						}
						
						markers = []
						
						# 사용자 위치 마커 추가
						if user_location:
								lat, lng = user_location
								user_marker = f"color:{self.marker_colors['user']}|label:U|{lat},{lng}"
								markers.append(user_marker)
								
								# 사용자 위치를 중심으로 설정
								params['center'] = f"{lat},{lng}"
						
						# 식당 마커 추가
						for i, restaurant in enumerate(restaurants[:10]):  # 최대 10개까지
								if restaurant.get('latitude') and restaurant.get('longitude'):
										lat = restaurant['latitude']
										lng = restaurant['longitude']
										
										# 추천 순서에 따라 마커 색상 결정
										if i == 0:
												color = self.marker_colors['recommended']
												label = '1'
										elif i < 3:
												color = self.marker_colors['restaurant']
												label = str(i + 1)
										else:
												color = self.marker_colors['alternative']
												label = str(i + 1)
										
										marker = f"color:{color}|label:{label}|{lat},{lng}"
										markers.append(marker)
						
						# 마커가 있는 경우에만 추가
						if markers:
								params['markers'] = markers
						
						# 중심점이 설정되지 않은 경우 첫 번째 식당으로 설정
						if 'center' not in params and restaurants:
								first_restaurant = restaurants[0]
								if first_restaurant.get('latitude') and first_restaurant.get('longitude'):
										params['center'] = f"{first_restaurant['latitude']},{first_restaurant['longitude']}"
								else:
										# 위치 정보가 없으면 기본 위치 사용
										params['center'] = '35.8714,128.6014'  # 대구 달서구 중심
						
						# URL 생성
						url = f"{self.endpoints['static_map']}?{urlencode(params, doseq=True)}"
						
						self.stats['static_map_calls'] += 1
						logger.info(f"정적 지도 URL 생성 완료: {len(restaurants)}개 식당")
						
						return url
						
				except Exception as e:
						logger.error(f"지도 URL 생성 중 오류 발생: {e}")
						self.stats['errors'] += 1
						return self._get_default_map_url()
		
		def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
				"""
				주소를 위도, 경도 좌표로 변환합니다.
				
				Args:
						address (str): 변환할 주소
						
				Returns:
						Optional[Tuple[float, float]]: (위도, 경도) 또는 None
				"""
				try:
						params = {
								'address': address,
								'key': self.api_key,
								'language': 'ko',
								'region': 'KR'
						}
						
						response = requests.get(self.endpoints['geocoding'], params=params, timeout=10)
						response.raise_for_status()
						
						data = response.json()
						
						if data['status'] == 'OK' and data['results']:
								location = data['results'][0]['geometry']['location']
								lat = location['lat']
								lng = location['lng']
								
								self.stats['geocoding_calls'] += 1
								logger.debug(f"주소 지오코딩 성공: {address} -> ({lat}, {lng})")
								
								return (lat, lng)
						else:
								logger.warning(f"지오코딩 실패: {address}, 상태: {data['status']}")
								return None
								
				except requests.RequestException as e:
						logger.error(f"지오코딩 API 요청 오류: {e}")
						self.stats['errors'] += 1
						return None
				except Exception as e:
						logger.error(f"지오코딩 중 오류 발생: {e}")
						self.stats['errors'] += 1
						return None
		
		def get_directions(self, 
											origin: Tuple[float, float],
											destination: Tuple[float, float],
											mode: str = 'driving') -> Optional[Dict[str, Any]]:
				"""
				두 지점 간의 경로 정보를 조회합니다.
				
				Args:
						origin (Tuple[float, float]): 출발지 (위도, 경도)
						destination (Tuple[float, float]): 목적지 (위도, 경도)
						mode (str): 이동 수단 ('driving', 'walking', 'transit')
						
				Returns:
						Optional[Dict[str, Any]]: 경로 정보 또는 None
				"""
				try:
						origin_str = f"{origin[0]},{origin[1]}"
						destination_str = f"{destination[0]},{destination[1]}"
						
						params = {
								'origin': origin_str,
								'destination': destination_str,
								'mode': mode,
								'key': self.api_key,
								'language': 'ko',
								'region': 'KR',
								'units': 'metric'
						}
						
						response = requests.get(self.endpoints['directions'], params=params, timeout=15)
						response.raise_for_status()
						
						data = response.json()
						
						if data['status'] == 'OK' and data['routes']:
								route = data['routes'][0]
								leg = route['legs'][0]
								
								directions_info = {
										'distance': leg['distance']['text'],
										'duration': leg['duration']['text'],
										'distance_value': leg['distance']['value'],  # 미터 단위
										'duration_value': leg['duration']['value'],  # 초 단위
										'start_address': leg['start_address'],
										'end_address': leg['end_address'],
										'steps': self._format_directions_steps(leg['steps']),
										'polyline': route['overview_polyline']['points']
								}
								
								self.stats['directions_calls'] += 1
								logger.debug(f"경로 조회 성공: {leg['distance']['text']}, {leg['duration']['text']}")
								
								return directions_info
						else:
								logger.warning(f"경로 조회 실패: {data['status']}")
								return None
								
				except requests.RequestException as e:
						logger.error(f"경로 API 요청 오류: {e}")
						self.stats['errors'] += 1
						return None
				except Exception as e:
						logger.error(f"경로 조회 중 오류 발생: {e}")
						self.stats['errors'] += 1
						return None
		
		def find_nearby_places(self, 
													location: Tuple[float, float],
													place_type: str = 'restaurant',
													radius: int = 1000,
													keyword: str = None) -> List[Dict[str, Any]]:
				"""
				특정 위치 주변의 장소들을 검색합니다.
				
				Args:
						location (Tuple[float, float]): 검색 중심 위치
						place_type (str): 장소 타입
						radius (int): 검색 반경 (미터)
						keyword (str, optional): 검색 키워드
						
				Returns:
						List[Dict[str, Any]]: 검색된 장소 리스트
				"""
				try:
						location_str = f"{location[0]},{location[1]}"
						
						params = {
								'location': location_str,
								'radius': radius,
								'type': place_type,
								'key': self.api_key,
								'language': 'ko'
						}
						
						if keyword:
								params['keyword'] = keyword
						
						response = requests.get(self.endpoints['places'], params=params, timeout=15)
						response.raise_for_status()
						
						data = response.json()
						
						places = []
						if data['status'] == 'OK':
								for place in data['results'][:20]:  # 최대 20개
										place_info = {
												'place_id': place.get('place_id'),
												'name': place.get('name'),
												'address': place.get('vicinity'),
												'rating': place.get('rating'),
												'price_level': place.get('price_level'),
												'types': place.get('types', []),
												'latitude': place['geometry']['location']['lat'],
												'longitude': place['geometry']['location']['lng'],
												'photos': [photo.get('photo_reference') for photo in place.get('photos', [])]
										}
										places.append(place_info)
								
								self.stats['places_calls'] += 1
								logger.debug(f"주변 장소 검색 완료: {len(places)}개 발견")
						
						return places
						
				except requests.RequestException as e:
						logger.error(f"장소 검색 API 요청 오류: {e}")
						self.stats['errors'] += 1
						return []
				except Exception as e:
						logger.error(f"장소 검색 중 오류 발생: {e}")
						self.stats['errors'] += 1
						return []
		
		def get_restaurant_directions_info(self, 
																			restaurant: Dict[str, Any],
																			user_location: Optional[Tuple[float, float]] = None) -> Dict[str, Any]:
				"""
				식당까지의 경로 정보를 포함한 종합 정보를 반환합니다.
				
				Args:
						restaurant (Dict[str, Any]): 식당 정보
						user_location (Optional[Tuple[float, float]]): 사용자 위치
						
				Returns:
						Dict[str, Any]: 식당 및 경로 정보
				"""
				try:
						result = {
								'restaurant': restaurant,
								'map_url': None,
								'directions': None,
								'nearby_landmarks': []
						}
						
						# 식당 위치 확인
						if not (restaurant.get('latitude') and restaurant.get('longitude')):
								# 주소로 지오코딩 시도
								if restaurant.get('address'):
										coords = self.geocode_address(restaurant['address'])
										if coords:
												restaurant['latitude'], restaurant['longitude'] = coords
										else:
												logger.warning(f"식당 위치를 찾을 수 없음: {restaurant.get('name')}")
												return result
						
						restaurant_location = (restaurant['latitude'], restaurant['longitude'])
						
						# 지도 URL 생성
						result['map_url'] = self.get_restaurant_map_url(
								[restaurant], user_location
						)
						
						# 사용자 위치가 있으면 경로 정보 조회
						if user_location:
								# 도보 경로
								walking_directions = self.get_directions(
										user_location, restaurant_location, 'walking'
								)
								
								# 자동차 경로  
								driving_directions = self.get_directions(
										user_location, restaurant_location, 'driving'
								)
								
								result['directions'] = {
										'walking': walking_directions,
										'driving': driving_directions
								}
						
						# 주변 랜드마크 검색
						nearby_landmarks = self.find_nearby_places(
								restaurant_location, 'point_of_interest', 500
						)
						
						result['nearby_landmarks'] = nearby_landmarks[:5]  # 상위 5개만
						
						return result
						
				except Exception as e:
						logger.error(f"식당 경로 정보 생성 중 오류 발생: {e}")
						return {
								'restaurant': restaurant,
								'map_url': self._get_default_map_url(),
								'directions': None,
								'nearby_landmarks': []
						}
		
		def generate_directions_text(self, directions: Dict[str, Any]) -> str:
				"""
				경로 정보를 사람이 읽기 쉬운 텍스트로 변환합니다.
				
				Args:
						directions (Dict[str, Any]): 경로 정보
						
				Returns:
						str: 경로 안내 텍스트
				"""
				try:
						if not directions:
								return "경로 정보를 찾을 수 없습니다."
						
						text = f"📍 거리: {directions['distance']}\n"
						text += f"⏱️ 소요시간: {directions['duration']}\n\n"
						
						if directions.get('steps'):
								text += "🗺️ 상세 경로:\n"
								for i, step in enumerate(directions['steps'][:5], 1):  # 최대 5단계
										text += f"{i}. {step}\n"
						
						return text.strip()
						
				except Exception as e:
						logger.error(f"경로 텍스트 생성 중 오류 발생: {e}")
						return "경로 정보 처리 중 오류가 발생했습니다."
		
		def get_map_stats(self) -> Dict[str, Any]:
				"""
				지도 서비스 사용 통계를 반환합니다.
				
				Returns:
						Dict[str, Any]: 사용 통계
				"""
				total_calls = sum([
						self.stats['geocoding_calls'],
						self.stats['places_calls'], 
						self.stats['directions_calls'],
						self.stats['static_map_calls']
				])
				
				return {
						**self.stats,
						'total_api_calls': total_calls,
						'success_rate': ((total_calls - self.stats['errors']) / total_calls * 100) 
														if total_calls > 0 else 0,
						'api_key_configured': bool(self.api_key)
				}
		
		def _format_directions_steps(self, steps: List[Dict[str, Any]]) -> List[str]:
				"""
				경로 단계를 사람이 읽기 쉬운 형태로 포맷팅합니다.
				
				Args:
						steps (List[Dict[str, Any]]): Google API 경로 단계
						
				Returns:
						List[str]: 포맷팅된 단계 설명
				"""
				formatted_steps = []
				
				for step in steps:
						# HTML 태그 제거
						instruction = step['html_instructions']
						instruction = re.sub(r'<[^>]+>', '', instruction)
						
						# 거리 정보 추가
						distance = step['distance']['text']
						instruction += f" ({distance})"
						
						formatted_steps.append(instruction)
				
				return formatted_steps
		
		def _get_default_map_url(self) -> str:
				"""
				기본 지도 URL을 반환합니다.
				
				Returns:
						str: 기본 지도 URL
				"""
				params = {
						'center': '35.8714,128.6014',  # 대구 달서구
						'zoom': '12',
						'size': '600x400',
						'maptype': 'roadmap',
						'key': self.api_key
				}
				
				return f"{self.endpoints['static_map']}?{urlencode(params)}"