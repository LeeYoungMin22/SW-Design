# tests/test_chat_manager.py
"""
ChatManager 클래스에 대한 단위 테스트
채팅 흐름 제어 및 예제 출력 기능 테스트
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

from app.services.chat_manager import ChatManager
from app.services.openai_service import OpenAIService
from app.services.database_manager import DatabaseManager

class TestChatManager(unittest.TestCase):
		"""ChatManager 테스트 클래스"""
		
		def setUp(self):
				"""테스트 환경 설정"""
				self.chat_manager = ChatManager()
				self.test_session_id = 'test_session_123'
				self.test_user_message = '2만원 이하 고기집 추천해줘'
		
		def tearDown(self):
				"""테스트 후 정리"""
				pass
		
		def test_session_initialization(self):
				"""세션 초기화 테스트"""
				session_id = self.chat_manager.create_session()
				self.assertIsNotNone(session_id)
				self.assertTrue(session_id.startswith('chat_'))
				self.assertIn(session_id, self.chat_manager.active_sessions)
		
		def test_example_questions_generation(self):
				"""예제 질문 생성 테스트"""
				examples = self.chat_manager.get_example_questions()
				
				self.assertIsInstance(examples, list)
				self.assertGreater(len(examples), 0)
				
				for example in examples:
						self.assertIn('text', example)
						self.assertIn('category', example)
						self.assertIsInstance(example['text'], str)
						self.assertGreater(len(example['text']), 0)
		
		@patch('app.services.chat_manager.OpenAIService')
		@patch('app.services.chat_manager.DatabaseManager')
		def test_process_user_message(self, mock_db, mock_openai):
				"""사용자 메시지 처리 테스트"""
				# Mock 설정
				mock_openai_instance = Mock()
				mock_openai.return_value = mock_openai_instance
				mock_openai_instance.generate_response.return_value = {
						'text': '좋은 고기집들을 찾아봤습니다!',
						'restaurants': [
								{'id': 1, 'name': '대박삼겹살', 'rating': 4.5}
						]
				}
				
				mock_db_instance = Mock()
				mock_db.return_value = mock_db_instance
				mock_db_instance.search_restaurants.return_value = [
						{'id': 1, 'name': '대박삼겹살', 'price_range': '15000-25000'}
				]
				
				# 테스트 실행
				response = self.chat_manager.process_message(
						self.test_session_id,
						self.test_user_message
				)
				
				# 검증
				self.assertIsInstance(response, dict)
				self.assertIn('message', response)
				self.assertIn('restaurants', response)
				self.assertIsInstance(response['restaurants'], list)
		
		def test_message_history_management(self):
				"""메시지 히스토리 관리 테스트"""
				session_id = self.chat_manager.create_session()
				
				# 메시지 추가
				self.chat_manager.add_message_to_history(
						session_id, 'user', self.test_user_message
				)
				self.chat_manager.add_message_to_history(
						session_id, 'assistant', '좋은 식당들을 찾아봤습니다.'
				)
				
				# 히스토리 조회
				history = self.chat_manager.get_message_history(session_id)
				
				self.assertEqual(len(history), 2)
				self.assertEqual(history[0]['role'], 'user')
				self.assertEqual(history[1]['role'], 'assistant')
				self.assertEqual(history[0]['content'], self.test_user_message)
		
		def test_session_cleanup(self):
				"""세션 정리 테스트"""
				session_id = self.chat_manager.create_session()
				self.assertIn(session_id, self.chat_manager.active_sessions)
				
				self.chat_manager.cleanup_session(session_id)
				self.assertNotIn(session_id, self.chat_manager.active_sessions)
		
		def test_context_preservation(self):
				"""대화 문맥 보존 테스트"""
				session_id = self.chat_manager.create_session()
				
				# 첫 번째 대화
				self.chat_manager.add_message_to_history(
						session_id, 'user', '한식 맛집 추천해줘'
				)
				self.chat_manager.add_message_to_history(
						session_id, 'assistant', '좋은 한식 맛집들을 추천드릴게요.'
				)
				
				# 두 번째 대화 (문맥 참조)
				self.chat_manager.add_message_to_history(
						session_id, 'user', '그 중에서 가장 가까운 곳은?'
				)
				
				context = self.chat_manager.build_context(session_id)
				
				self.assertGreater(len(context), 0)
				self.assertTrue(any('한식' in msg['content'] for msg in context))
		
		@patch('app.services.chat_manager.datetime')
		def test_session_timeout_handling(self, mock_datetime):
				"""세션 타임아웃 처리 테스트"""
				# 현재 시간 Mock
				mock_now = datetime(2024, 1, 1, 12, 0, 0)
				mock_datetime.now.return_value = mock_now
				
				session_id = self.chat_manager.create_session()
				
				# 30분 후 시간으로 변경
				mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 31, 0)
				
				# 타임아웃된 세션 정리
				self.chat_manager.cleanup_expired_sessions()
				
				self.assertNotIn(session_id, self.chat_manager.active_sessions)
		
		def test_error_handling(self):
				"""에러 처리 테스트"""
				# 존재하지 않는 세션에 대한 처리
				non_existent_session = 'non_existent_session'
				
				with self.assertRaises(ValueError):
						self.chat_manager.get_message_history(non_existent_session)
				
				# 빈 메시지에 대한 처리
				session_id = self.chat_manager.create_session()
				response = self.chat_manager.process_message(session_id, '')
				
				self.assertIn('error', response)
		
		def test_special_commands(self):
				"""특수 명령어 처리 테스트"""
				session_id = self.chat_manager.create_session()
				
				# 도움말 명령
				response = self.chat_manager.process_message(session_id, '/help')
				self.assertIn('도움말', response['message'])
				
				# 초기화 명령
				self.chat_manager.add_message_to_history(session_id, 'user', '테스트 메시지')
				response = self.chat_manager.process_message(session_id, '/clear')
				
				history = self.chat_manager.get_message_history(session_id)
				self.assertEqual(len(history), 0)

if __name__ == '__main__':
		unittest.main()