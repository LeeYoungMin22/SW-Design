# -*- coding: utf-8 -*-
"""
세션 관리 유틸리티 (SessionManager)
사용자 채팅 세션과 대화 컨텍스트를 메모리에서 관리하는 도구입니다.
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from threading import Lock, Timer
from collections import defaultdict

logger = logging.getLogger(__name__)

class SessionManager:
		"""
		사용자 채팅 세션과 대화 메모리를 관리하는 클래스
		세션별 대화 상태와 컨텍스트 정보를 유지합니다.
		"""
		
		def __init__(self, 
									session_timeout: int = 3600,  # 1시간
									max_sessions: int = 1000,
									cleanup_interval: int = 300):  # 5분
				"""
				세션 매니저 초기화
				
				Args:
						session_timeout (int): 세션 타임아웃 (초)
						max_sessions (int): 최대 세션 수
						cleanup_interval (int): 정리 작업 간격 (초)
				"""
				self.session_timeout = session_timeout
				self.max_sessions = max_sessions
				self.cleanup_interval = cleanup_interval
				
				# 세션 데이터 저장소
				self.sessions = {}  # session_id -> session_data
				self.user_sessions = defaultdict(list)  # user_id -> [session_ids]
				self.session_locks = defaultdict(Lock)  # session_id -> Lock
				self.global_lock = Lock()
				
				# 세션 메타데이터
				self.session_metadata = {}  # session_id -> metadata
				
				# 통계
				self.stats = {
						'total_sessions_created': 0,
						'active_sessions': 0,
						'expired_sessions_cleaned': 0,
						'memory_usage_mb': 0
				}
				
				# 자동 정리 타이머 시작
				self._start_cleanup_timer()
		
		def create_session(self, session_id: str, initial_data: Dict[str, Any] = None) -> bool:
				"""
				새로운 세션을 생성합니다.
				
				Args:
						session_id (str): 세션 ID
						initial_data (Dict[str, Any], optional): 초기 세션 데이터
						
				Returns:
						bool: 생성 성공 여부
				"""
				with self.global_lock:
						try:
								# 세션 수 제한 확인
								if len(self.sessions) >= self.max_sessions:
										self._cleanup_oldest_session()
								
								# 초기 데이터 설정
								if initial_data is None:
										initial_data = {}
								
								# 세션 데이터 구성
								session_data = {
										'session_id': session_id,
										'created_at': datetime.utcnow().isoformat(),
										'last_activity': datetime.utcnow().isoformat(),
										'user_id': initial_data.get('user_id'),
										'state': 'active',
										'conversation_history': [],
										'context': {},
										'preferences': {},
										**initial_data
								}
								
								# 세션 저장
								self.sessions[session_id] = session_data
								
								# 메타데이터 저장
								self.session_metadata[session_id] = {
										'created_timestamp': time.time(),
										'last_access_timestamp': time.time(),
										'access_count': 1
								}
								
								# 사용자별 세션 매핑 업데이트
								if session_data.get('user_id'):
										self.user_sessions[session_data['user_id']].append(session_id)
								
								# 통계 업데이트
								self.stats['total_sessions_created'] += 1
								self.stats['active_sessions'] = len(self.sessions)
								
								logger.info(f"새 세션 생성: {session_id}")
								return True
								
						except Exception as e:
								logger.error(f"세션 생성 중 오류 발생: {e}")
								return False
		
		def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
				"""
				세션 데이터를 조회합니다.
				
				Args:
						session_id (str): 세션 ID
						
				Returns:
						Optional[Dict[str, Any]]: 세션 데이터 또는 None
				"""
				with self.session_locks[session_id]:
						try:
								if session_id not in self.sessions:
										return None
								
								# 세션 만료 확인
								if self._is_session_expired(session_id):
										self._delete_session(session_id)
										return None
								
								# 접근 시간 업데이트
								self._update_session_access(session_id)
								
								return self.sessions[session_id].copy()
								
						except Exception as e:
								logger.error(f"세션 조회 중 오류 발생: {e}")
								return None
		
		def update_session(self, session_id: str, update_data: Dict[str, Any]) -> bool:
				"""
				세션 데이터를 업데이트합니다.
				
				Args:
						session_id (str): 세션 ID
						update_data (Dict[str, Any]): 업데이트할 데이터
						
				Returns:
						bool: 업데이트 성공 여부
				"""
				with self.session_locks[session_id]:
						try:
								if session_id not in self.sessions:
										return False
								
								# 세션 만료 확인
								if self._is_session_expired(session_id):
										self._delete_session(session_id)
										return False
								
								# 데이터 업데이트
								self.sessions[session_id].update(update_data)
								self.sessions[session_id]['last_activity'] = datetime.utcnow().isoformat()
								
								# 접근 시간 업데이트
								self._update_session_access(session_id)
								
								return True
								
						except Exception as e:
								logger.error(f"세션 업데이트 중 오류 발생: {e}")
								return False
		
		def delete_session(self, session_id: str) -> bool:
				"""
				세션을 삭제합니다.
				
				Args:
						session_id (str): 세션 ID
						
				Returns:
						bool: 삭제 성공 여부
				"""
				with self.global_lock:
						return self._delete_session(session_id)
		
		def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
				"""
				특정 사용자의 모든 활성 세션을 조회합니다.
				
				Args:
						user_id (int): 사용자 ID
						
				Returns:
						List[Dict[str, Any]]: 사용자의 세션 리스트
				"""
				try:
						user_sessions = []
						session_ids = self.user_sessions.get(user_id, [])
						
						for session_id in session_ids.copy():  # 복사본으로 반복
								session_data = self.get_session(session_id)
								if session_data:
										user_sessions.append(session_data)
								else:
										# 만료된 세션은 목록에서 제거
										self.user_sessions[user_id].remove(session_id)
						
						return user_sessions
						
				except Exception as e:
						logger.error(f"사용자 세션 조회 중 오류 발생: {e}")
						return []
		
		def add_message_to_session(self, 
															session_id: str,
															role: str,
															content: str,
															metadata: Dict[str, Any] = None) -> bool:
				"""
				세션에 메시지를 추가합니다.
				
				Args:
						session_id (str): 세션 ID
						role (str): 메시지 역할 ('user', 'assistant', 'system')
						content (str): 메시지 내용
						metadata (Dict[str, Any], optional): 추가 메타데이터
						
				Returns:
						bool: 추가 성공 여부
				"""
				with self.session_locks[session_id]:
						try:
								session_data = self.get_session(session_id)
								if not session_data:
										return False
								
								# 메시지 객체 생성
								message = {
										'role': role,
										'content': content,
										'timestamp': datetime.utcnow().isoformat(),
										'metadata': metadata or {}
								}
								
								# 대화 히스토리에 추가
								if 'conversation_history' not in session_data:
										session_data['conversation_history'] = []
								
								session_data['conversation_history'].append(message)
								
								# 히스토리 길이 제한 (최대 100개 메시지)
								max_history = 100
								if len(session_data['conversation_history']) > max_history:
										session_data['conversation_history'] = session_data['conversation_history'][-max_history:]
								
								# 세션 업데이트
								return self.update_session(session_id, session_data)
								
						except Exception as e:
								logger.error(f"메시지 추가 중 오류 발생: {e}")
								return False
		
		def get_conversation_history(self, 
																session_id: str,
																limit: int = 20) -> List[Dict[str, Any]]:
				"""
				세션의 대화 히스토리를 조회합니다.
				
				Args:
						session_id (str): 세션 ID
						limit (int): 조회할 최대 메시지 수
						
				Returns:
						List[Dict[str, Any]]: 대화 히스토리
				"""
				try:
						session_data = self.get_session(session_id)
						if not session_data:
								return []
						
						history = session_data.get('conversation_history', [])
						
						# 최신 메시지부터 limit 개수만큼 반환
						return history[-limit:] if len(history) > limit else history
						
				except Exception as e:
						logger.error(f"대화 히스토리 조회 중 오류 발생: {e}")
						return []
		
		def update_session_context(self, 
															session_id: str,
															context_key: str,
															context_value: Any) -> bool:
				"""
				세션의 컨텍스트 정보를 업데이트합니다.
				
				Args:
						session_id (str): 세션 ID
						context_key (str): 컨텍스트 키
						context_value (Any): 컨텍스트 값
						
				Returns:
						bool: 업데이트 성공 여부
				"""
				try:
						session_data = self.get_session(session_id)
						if not session_data:
								return False
						
						if 'context' not in session_data:
								session_data['context'] = {}
						
						session_data['context'][context_key] = context_value
						
						return self.update_session(session_id, session_data)
						
				except Exception as e:
						logger.error(f"세션 컨텍스트 업데이트 중 오류 발생: {e}")
						return False
		
		def cleanup_expired_sessions(self) -> int:
				"""
				만료된 세션들을 정리합니다.
				
				Returns:
						int: 정리된 세션 수
				"""
				with self.global_lock:
						try:
								expired_sessions = []
								current_time = time.time()
								
								for session_id, metadata in self.session_metadata.items():
										if current_time - metadata['last_access_timestamp'] > self.session_timeout:
												expired_sessions.append(session_id)
								
								# 만료된 세션들 삭제
								for session_id in expired_sessions:
										self._delete_session(session_id)
								
								self.stats['expired_sessions_cleaned'] += len(expired_sessions)
								
								if expired_sessions:
										logger.info(f"만료된 세션 정리: {len(expired_sessions)}개")
								
								return len(expired_sessions)
								
						except Exception as e:
								logger.error(f"만료된 세션 정리 중 오류 발생: {e}")
								return 0
		
		def get_session_stats(self) -> Dict[str, Any]:
				"""
				세션 관리 통계를 반환합니다.
				
				Returns:
						Dict[str, Any]: 세션 통계
				"""
				with self.global_lock:
						# 메모리 사용량 추정 (대략적)
						memory_usage = 0
						for session_data in self.sessions.values():
								memory_usage += len(json.dumps(session_data, ensure_ascii=False).encode('utf-8'))
						
						self.stats['memory_usage_mb'] = round(memory_usage / (1024 * 1024), 2)
						self.stats['active_sessions'] = len(self.sessions)
						
						return {
								**self.stats,
								'session_timeout': self.session_timeout,
								'max_sessions': self.max_sessions,
								'current_timestamp': time.time()
						}
		
		def _is_session_expired(self, session_id: str) -> bool:
				"""
				세션이 만료되었는지 확인합니다.
				
				Args:
						session_id (str): 세션 ID
						
				Returns:
						bool: 만료 여부
				"""
				if session_id not in self.session_metadata:
						return True
				
				current_time = time.time()
				last_access = self.session_metadata[session_id]['last_access_timestamp']
				
				return current_time - last_access > self.session_timeout
		
		def _update_session_access(self, session_id: str) -> None:
				"""
				세션의 접근 시간을 업데이트합니다.
				
				Args:
						session_id (str): 세션 ID
				"""
				if session_id in self.session_metadata:
						self.session_metadata[session_id]['last_access_timestamp'] = time.time()
						self.session_metadata[session_id]['access_count'] += 1
		
		def _delete_session(self, session_id: str) -> bool:
				"""
				세션을 삭제합니다 (내부 메소드).
				
				Args:
						session_id (str): 세션 ID
						
				Returns:
						bool: 삭제 성공 여부
				"""
				try:
						# 세션 데이터에서 사용자 ID 추출
						session_data = self.sessions.get(session_id)
						user_id = session_data.get('user_id') if session_data else None
						
						# 세션 데이터 삭제
						self.sessions.pop(session_id, None)
						self.session_metadata.pop(session_id, None)
						
						# 사용자별 세션 매핑에서 제거
						if user_id and session_id in self.user_sessions[user_id]:
								self.user_sessions[user_id].remove(session_id)
								
								# 사용자의 세션이 모두 없어지면 매핑 삭제
								if not self.user_sessions[user_id]:
										del self.user_sessions[user_id]
						
						# 세션 락 정리
						if session_id in self.session_locks:
								del self.session_locks[session_id]
						
						# 통계 업데이트
						self.stats['active_sessions'] = len(self.sessions)
						
						logger.debug(f"세션 삭제 완료: {session_id}")
						return True
						
				except Exception as e:
						logger.error(f"세션 삭제 중 오류 발생: {e}")
						return False
		
		def _cleanup_oldest_session(self) -> None:
				"""
				가장 오래된 세션을 정리합니다.
				"""
				if not self.session_metadata:
						return
				
				# 가장 오래 전에 접근된 세션 찾기
				oldest_session_id = min(
						self.session_metadata.items(),
						key=lambda x: x[1]['last_access_timestamp']
				)[0]
				
				self._delete_session(oldest_session_id)
				logger.info(f"최대 세션 수 초과로 인한 정리: {oldest_session_id}")
		
		def _start_cleanup_timer(self) -> None:
				"""
				주기적인 정리 작업 타이머를 시작합니다.
				"""
				def cleanup_task():
						try:
								self.cleanup_expired_sessions()
						except Exception as e:
								logger.error(f"정기 정리 작업 중 오류 발생: {e}")
						finally:
								# 다음 정리 작업 예약
								self._start_cleanup_timer()
				
				timer = Timer(self.cleanup_interval, cleanup_task)
				timer.daemon = True
				timer.start()
		
		def __del__(self):
				"""소멸자에서 모든 세션 정리"""
				try:
						with self.global_lock:
								self.sessions.clear()
								self.session_metadata.clear()
								self.user_sessions.clear()
								self.session_locks.clear()
				except:
						pass  # 소멸자에서는 예외를 무시