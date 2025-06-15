# -*- coding: utf-8 -*-
"""
캐시 관리 유틸리티 (CacheManager)
API 응답과 계산 결과를 캐싱하여 성능을 향상시키는 도구입니다.
"""

import json
import time
import logging
import hashlib
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from threading import Lock

logger = logging.getLogger(__name__)

class CacheManager:
		"""
		메모리 기반 캐시 관리 클래스
		API 응답과 계산 결과를 임시 저장하여 성능을 향상시킵니다.
		"""
		
		def __init__(self, default_ttl: int = 3600, max_size: int = 1000):
				"""
				캐시 매니저 초기화
				
				Args:
						default_ttl (int): 기본 TTL (초 단위)
						max_size (int): 최대 캐시 항목 수
				"""
				self.default_ttl = default_ttl
				self.max_size = max_size
				self.cache_data = {}  # 캐시 데이터 저장소
				self.cache_metadata = {}  # 캐시 메타데이터 (생성시간, TTL 등)
				self.access_times = {}  # 접근 시간 (LRU 구현용)
				self.lock = Lock()  # 스레드 안전성을 위한 락
				
				# 캐시 통계
				self.stats = {
						'hits': 0,
						'misses': 0,
						'sets': 0,
						'deletes': 0,
						'evictions': 0,
						'cleanups': 0
				}
		
		def get(self, key: str) -> Optional[Any]:
				"""
				캐시에서 값을 조회합니다.
				
				Args:
						key (str): 캐시 키
						
				Returns:
						Optional[Any]: 캐시된 값 또는 None
				"""
				with self.lock:
						try:
								# 키 정규화
								normalized_key = self._normalize_key(key)
								
								# 캐시 존재 확인
								if normalized_key not in self.cache_data:
										self.stats['misses'] += 1
										return None
								
								# TTL 확인
								if self._is_expired(normalized_key):
										self._delete_key(normalized_key)
										self.stats['misses'] += 1
										return None
								
								# 접근 시간 업데이트 (LRU)
								self.access_times[normalized_key] = time.time()
								
								# 캐시 히트
								self.stats['hits'] += 1
								logger.debug(f"캐시 히트: {key}")
								
								return self.cache_data[normalized_key]
								
						except Exception as e:
								logger.error(f"캐시 조회 중 오류 발생: {e}")
								self.stats['misses'] += 1
								return None
		
		def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
				"""
				캐시에 값을 저장합니다.
				
				Args:
						key (str): 캐시 키
						value (Any): 저장할 값
						ttl (Optional[int]): TTL (초 단위), None이면 기본값 사용
						
				Returns:
						bool: 저장 성공 여부
				"""
				with self.lock:
						try:
								# TTL 설정
								if ttl is None:
										ttl = self.default_ttl
								
								# 키 정규화
								normalized_key = self._normalize_key(key)
								
								# 캐시 크기 확인 및 정리
								if len(self.cache_data) >= self.max_size:
										self._evict_lru()
								
								# 값 저장
								self.cache_data[normalized_key] = value
								
								# 메타데이터 저장
								current_time = time.time()
								self.cache_metadata[normalized_key] = {
										'created_at': current_time,
										'ttl': ttl,
										'expires_at': current_time + ttl,
										'access_count': 1
								}
								
								# 접근 시간 저장
								self.access_times[normalized_key] = current_time
								
								self.stats['sets'] += 1
								logger.debug(f"캐시 저장: {key} (TTL: {ttl}초)")
								
								return True
								
						except Exception as e:
								logger.error(f"캐시 저장 중 오류 발생: {e}")
								return False
		
		def delete(self, key: str) -> bool:
				"""
				캐시에서 특정 키를 삭제합니다.
				
				Args:
						key (str): 삭제할 캐시 키
						
				Returns:
						bool: 삭제 성공 여부
				"""
				with self.lock:
						try:
								normalized_key = self._normalize_key(key)
								
								if normalized_key in self.cache_data:
										self._delete_key(normalized_key)
										self.stats['deletes'] += 1
										logger.debug(f"캐시 삭제: {key}")
										return True
								
								return False
								
						except Exception as e:
								logger.error(f"캐시 삭제 중 오류 발생: {e}")
								return False
		
		def clear(self) -> None:
				"""
				모든 캐시를 삭제합니다.
				"""
				with self.lock:
						try:
								count = len(self.cache_data)
								self.cache_data.clear()
								self.cache_metadata.clear()
								self.access_times.clear()
								
								logger.info(f"전체 캐시 삭제: {count}개 항목")
								
						except Exception as e:
								logger.error(f"캐시 전체 삭제 중 오류 발생: {e}")
		
		def cleanup_expired(self) -> int:
				"""
				만료된 캐시 항목들을 정리합니다.
				
				Returns:
						int: 정리된 항목 수
				"""
				with self.lock:
						try:
								expired_keys = []
								current_time = time.time()
								
								for key, metadata in self.cache_metadata.items():
										if current_time > metadata['expires_at']:
												expired_keys.append(key)
								
								# 만료된 키들 삭제
								for key in expired_keys:
										self._delete_key(key)
								
								self.stats['cleanups'] += 1
								
								if expired_keys:
										logger.info(f"만료된 캐시 정리: {len(expired_keys)}개 항목")
								
								return len(expired_keys)
								
						except Exception as e:
								logger.error(f"만료된 캐시 정리 중 오류 발생: {e}")
								return 0
		
		def get_stats(self) -> Dict[str, Any]:
				"""
				캐시 통계 정보를 반환합니다.
				
				Returns:
						Dict[str, Any]: 캐시 통계
				"""
				with self.lock:
						total_requests = self.stats['hits'] + self.stats['misses']
						hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
						
						return {
								'cache_size': len(self.cache_data),
								'max_size': self.max_size,
								'hit_rate': round(hit_rate, 2),
								'total_requests': total_requests,
								**self.stats
						}
		
		def get_cache_info(self, key: str) -> Optional[Dict[str, Any]]:
				"""
				특정 캐시 키의 정보를 반환합니다.
				
				Args:
						key (str): 캐시 키
						
				Returns:
						Optional[Dict[str, Any]]: 캐시 정보 또는 None
				"""
				with self.lock:
						normalized_key = self._normalize_key(key)
						
						if normalized_key not in self.cache_metadata:
								return None
						
						metadata = self.cache_metadata[normalized_key]
						current_time = time.time()
						
						return {
								'key': key,
								'created_at': datetime.fromtimestamp(metadata['created_at']).isoformat(),
								'ttl': metadata['ttl'],
								'expires_at': datetime.fromtimestamp(metadata['expires_at']).isoformat(),
								'expires_in': max(0, metadata['expires_at'] - current_time),
								'access_count': metadata['access_count'],
								'is_expired': current_time > metadata['expires_at']
						}
		
		def invalidate_pattern(self, pattern: str) -> int:
				"""
				패턴에 맞는 캐시 키들을 무효화합니다.
				
				Args:
						pattern (str): 키 패턴 (단순 문자열 포함 검사)
						
				Returns:
						int: 무효화된 항목 수
				"""
				with self.lock:
						try:
								keys_to_delete = []
								
								for key in self.cache_data.keys():
										if pattern in key:
												keys_to_delete.append(key)
								
								# 매칭된 키들 삭제
								for key in keys_to_delete:
										self._delete_key(key)
								
								logger.info(f"패턴 '{pattern}'으로 {len(keys_to_delete)}개 캐시 무효화")
								return len(keys_to_delete)
								
						except Exception as e:
								logger.error(f"패턴 기반 캐시 무효화 중 오류 발생: {e}")
								return 0
		
		def _normalize_key(self, key: str) -> str:
				"""
				캐시 키를 정규화합니다.
				
				Args:
						key (str): 원본 키
						
				Returns:
						str: 정규화된 키
				"""
				# 문자열이 아닌 경우 문자열로 변환
				if not isinstance(key, str):
						key = str(key)
				
				# 너무 긴 키는 해시로 변환
				if len(key) > 250:
						return hashlib.md5(key.encode('utf-8')).hexdigest()
				
				return key
		
		def _is_expired(self, key: str) -> bool:
				"""
				캐시가 만료되었는지 확인합니다.
				
				Args:
						key (str): 캐시 키
						
				Returns:
						bool: 만료 여부
				"""
				if key not in self.cache_metadata:
						return True
				
				current_time = time.time()
				expires_at = self.cache_metadata[key]['expires_at']
				
				return current_time > expires_at
		
		def _delete_key(self, key: str) -> None:
				"""
				캐시 키와 관련된 모든 데이터를 삭제합니다.
				
				Args:
						key (str): 삭제할 키
				"""
				self.cache_data.pop(key, None)
				self.cache_metadata.pop(key, None)
				self.access_times.pop(key, None)
		
		def _evict_lru(self) -> None:
				"""
				LRU 알고리즘으로 가장 오래된 항목을 제거합니다.
				"""
				if not self.access_times:
						return
				
				# 가장 오래 전에 접근된 키 찾기
				lru_key = min(self.access_times.items(), key=lambda x: x[1])[0]
				
				# 해당 키 삭제
				self._delete_key(lru_key)
				self.stats['evictions'] += 1
				
				logger.debug(f"LRU 제거: {lru_key}")


class RestaurantCache:
		"""
		식당 관련 데이터를 위한 특화된 캐시 클래스
		식당 검색 결과와 추천 결과를 효율적으로 캐싱합니다.
		"""
		
		def __init__(self, cache_manager: CacheManager):
				"""
				식당 캐시 초기화
				
				Args:
						cache_manager (CacheManager): 기본 캐시 매니저
				"""
				self.cache = cache_manager
				self.restaurant_ttl = 3600  # 1시간
				self.search_ttl = 1800      # 30분
				self.recommendation_ttl = 1800  # 30분
		
		def cache_restaurant(self, restaurant_id: int, restaurant_data: Dict[str, Any]) -> bool:
				"""
				식당 정보를 캐싱합니다.
				
				Args:
						restaurant_id (int): 식당 ID
						restaurant_data (Dict[str, Any]): 식당 데이터
						
				Returns:
						bool: 캐싱 성공 여부
				"""
				key = f"restaurant:{restaurant_id}"
				return self.cache.set(key, restaurant_data, self.restaurant_ttl)
		
		def get_restaurant(self, restaurant_id: int) -> Optional[Dict[str, Any]]:
				"""
				캐시에서 식당 정보를 조회합니다.
				
				Args:
						restaurant_id (int): 식당 ID
						
				Returns:
						Optional[Dict[str, Any]]: 식당 데이터 또는 None
				"""
				key = f"restaurant:{restaurant_id}"
				return self.cache.get(key)
		
		def cache_search_results(self, 
														search_params: Dict[str, Any], 
														results: List[Dict[str, Any]]) -> bool:
				"""
				검색 결과를 캐싱합니다.
				
				Args:
						search_params (Dict[str, Any]): 검색 조건
						results (List[Dict[str, Any]]): 검색 결과
						
				Returns:
						bool: 캐싱 성공 여부
				"""
				# 검색 조건을 키로 변환
				search_key = self._generate_search_key(search_params)
				key = f"search:{search_key}"
				
				return self.cache.set(key, results, self.search_ttl)
		
		def get_search_results(self, search_params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
				"""
				캐시에서 검색 결과를 조회합니다.
				
				Args:
						search_params (Dict[str, Any]): 검색 조건
						
				Returns:
						Optional[List[Dict[str, Any]]]: 검색 결과 또는 None
				"""
				search_key = self._generate_search_key(search_params)
				key = f"search:{search_key}"
				
				return self.cache.get(key)
		
		def cache_recommendations(self, 
														user_id: int, 
														query_hash: str,
														recommendations: List[Dict[str, Any]]) -> bool:
				"""
				추천 결과를 캐싱합니다.
				
				Args:
						user_id (int): 사용자 ID
						query_hash (str): 질문 해시
						recommendations (List[Dict[str, Any]]): 추천 결과
						
				Returns:
						bool: 캐싱 성공 여부
				"""
				key = f"recommendation:{user_id}:{query_hash}"
				return self.cache.set(key, recommendations, self.recommendation_ttl)
		
		def get_recommendations(self, user_id: int, query_hash: str) -> Optional[List[Dict[str, Any]]]:
				"""
				캐시에서 추천 결과를 조회합니다.
				
				Args:
						user_id (int): 사용자 ID
						query_hash (str): 질문 해시
						
				Returns:
						Optional[List[Dict[str, Any]]]: 추천 결과 또는 None
				"""
				key = f"recommendation:{user_id}:{query_hash}"
				return self.cache.get(key)
		
		def invalidate_restaurant(self, restaurant_id: int) -> None:
				"""
				특정 식당의 모든 캐시를 무효화합니다.
				
				Args:
						restaurant_id (int): 식당 ID
				"""
				# 식당 정보 캐시 삭제
				self.cache.delete(f"restaurant:{restaurant_id}")
				
				# 해당 식당이 포함된 검색 결과 캐시들 무효화
				self.cache.invalidate_pattern(f"restaurant_id:{restaurant_id}")
				
				logger.info(f"식당 {restaurant_id} 관련 캐시 무효화 완료")
		
		def _generate_search_key(self, search_params: Dict[str, Any]) -> str:
				"""
				검색 조건을 기반으로 캐시 키를 생성합니다.
				
				Args:
						search_params (Dict[str, Any]): 검색 조건
						
				Returns:
						str: 생성된 키
				"""
				# 정렬하여 일관된 키 생성
				sorted_params = sorted(search_params.items())
				params_str = json.dumps(sorted_params, ensure_ascii=False, sort_keys=True)
				
				# 해시로 변환하여 길이 제한
				return hashlib.md5(params_str.encode('utf-8')).hexdigest()