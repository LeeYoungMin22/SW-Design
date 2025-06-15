# tests/test_api_endpoints.py
"""
API 엔드포인트 통합 테스트
실제 HTTP 요청을 통한 API 기능 테스트
"""

import unittest
import json
import tempfile
import os
from unittest.mock import patch, Mock

from app import create_app
from app.config.settings import TestingConfig

class TestAPIEndpoints(unittest.TestCase):
		"""API 엔드포인트 테스트 클래스"""
		
		def setUp(self):
				"""테스트 환경 설정"""
				# 임시 데이터베이스 생성
				self.db_fd, self.db_path = tempfile.mkstemp()
				
				# 테스트용 설정
				TestingConfig.DATABASE_PATH = self.db_path
				
				# 테스트 앱 생성
				self.app = create_app('testing')
				self.app_context = self.app.app_context()
				self.app_context.push()
				
				self.client = self.app.test_client()
				
				# 테스트 데이터베이스 초기화
				from app.services.database_manager import DatabaseManager
				db_manager = DatabaseManager(db_path=self.db_path)
				db_manager.init_database()
				
				# 테스트 데이터 삽입
				self.test_restaurant_id = db_manager.create_restaurant({
						'name': '테스트 식당',
						'category': 'korean',
						'address': '대구 달서구 테스트로 123',
						'latitude': 35.8562,
						'longitude': 128.5327,
						'rating': 4.5,
						'price_range': '10000-20000',
						'phone': '053-123-4567',
						'hours': '11:00-22:00',
						'description': '테스트용 식당입니다.'
				})
		
		def tearDown(self):
				"""테스트 후 정리"""
				self.app_context.pop()
				os.close(self.db_fd)
				os.unlink(self.db_path)
		
		def test_health_check(self):
				"""헬스 체크 엔드포인트 테스트"""
				response = self.client.get('/api/health')
				
				self.assertEqual(response.status_code, 200)
				data = json.loads(response.data)
				self.assertTrue(data['success'])
				self.assertIn('status', data['data'])
		
		def test_get_restaurants(self):
				"""식당 목록 조회 API 테스트"""
				response = self.client.get('/api/restaurants')
				
				self.assertEqual(response.status_code, 200)
				data = json.loads(response.data)
				self.assertTrue(data['success'])
				self.assertIn('restaurants', data['data'])
				self.assertIn('pagination', data['data'])
		
		def test_get_restaurants_with_filters(self):
				"""필터를 적용한 식당 조회 테스트"""
				response = self.client.get('/api/restaurants?category=korean&price_max=25000')
				
				self.assertEqual(response.status_code, 200)
				data = json.loads(response.data)
				self.assertTrue(data['success'])
				
				# 필터링 결과 확인
				restaurants = data['data']['restaurants']
				for restaurant in restaurants:
						self.assertEqual(restaurant['category'], 'korean')
		
		def test_get_restaurant_by_id(self):
				"""특정 식당 상세 조회 테스트"""
				response = self.client.get(f'/api/restaurants/{self.test_restaurant_id}')
				
				self.assertEqual(response.status_code, 200)
				data = json.loads(response.data)
				self.assertTrue(data['success'])
				
				restaurant = data['data']['restaurant']
				self.assertEqual(restaurant['id'], self.test_restaurant_id)
				self.assertEqual(restaurant['name'], '테스트 식당')
		
		def test_get_nonexistent_restaurant(self):
				"""존재하지 않는 식당 조회 테스트"""
				response = self.client.get('/api/restaurants/99999')
				
				self.assertEqual(response.status_code, 404)
				data = json.loads(response.data)
				self.assertFalse(data['success'])
		
		def test_get_restaurant_categories(self):
				"""식당 카테고리 목록 조회 테스트"""
				response = self.client.get('/api/restaurants/categories')
				
				self.assertEqual(response.status_code, 200)
				data = json.loads(response.data)
				self.assertTrue(data['success'])
				self.assertIn('categories', data['data'])
		
		def test_search_nearby_restaurants(self):
				"""주변 식당 검색 테스트"""
				search_data = {
						'latitude': 35.8562,
						'longitude': 128.5327,
						'radius': 1000
				}
				
				response = self.client.post(
						'/api/restaurants/nearby',
						data=json.dumps(search_data),
						content_type='application/json'
				)
				
				self.assertEqual(response.status_code, 200)
				data = json.loads(response.data)
				self.assertTrue(data['success'])
				self.assertIn('restaurants', data['data'])
		
		def test_create_review(self):
				"""리뷰 작성 테스트"""
				review_data = {
						'restaurant_id': self.test_restaurant_id,
						'user_session': 'test_user',
						'rating': 5,
						'content': '정말 맛있었어요! 다시 방문하고 싶습니다.',
						'purpose': '데이트'
				}
				
				with patch('app.services.review_manager.SentimentAnalyzer') as mock_sentiment:
						mock_sentiment.return_value.analyze.return_value = {
								'score': 0.9,
								'label': 'positive',
								'confidence': 0.95
						}
						
						response = self.client.post(
								'/api/reviews',
								data=json.dumps(review_data),
								content_type='application/json'
						)
				
				self.assertEqual(response.status_code, 200)
				data = json.loads(response.data)
				self.assertTrue(data['success'])
				self.assertIn('review_id', data['data'])
		
		def test_create_review_invalid_data(self):
				"""잘못된 데이터로 리뷰 작성 테스트"""
				invalid_review_data = {
						'restaurant_id': self.test_restaurant_id,
						'rating': 6,  # 잘못된 평점 (1-5 범위 초과)
						'content': ''  # 빈 내용
				}
				
				response = self.client.post(
						'/api/reviews',
						data=json.dumps(invalid_review_data),
						content_type='application/json'
				)
				
				self.assertEqual(response.status_code, 400)
				data = json.loads(response.data)
				self.assertFalse(data['success'])
		
		def test_get_restaurant_reviews(self):
				"""식당 리뷰 목록 조회 테스트"""
				# 먼저 리뷰 생성
				from app.services.database_manager import DatabaseManager
				db_manager = DatabaseManager(db_path=self.db_path)
				
				review_data = {
						'restaurant_id': self.test_restaurant_id,
						'user_session': 'test_user',
						'rating': 5,
						'content': '테스트 리뷰입니다.',
						'sentiment_score': 0.8,
						'sentiment_label': 'positive'
				}
				db_manager.create_review(review_data)
				
				# 리뷰 조회
				response = self.client.get(f'/api/reviews/restaurant/{self.test_restaurant_id}')
				
				self.assertEqual(response.status_code, 200)
				data = json.loads(response.data)
				self.assertTrue(data['success'])
				self.assertIn('reviews', data['data'])
				self.assertIn('statistics', data['data'])
		
		@patch('app.services.chat_manager.OpenAIService')
		def test_chat_message(self, mock_openai):
				"""채팅 메시지 처리 테스트"""
				# OpenAI 응답 Mock
				mock_openai.return_value.generate_response.return_value = {
						'message': '좋은 한식 맛집들을 찾아봤습니다!',
						'restaurants': [
								{
										'id': self.test_restaurant_id,
										'name': '테스트 식당',
										'reason': '평점이 높고 가격이 적절합니다.'
								}
						]
				}
				
				chat_data = {
						'message': '한식 맛집 추천해줘',
						'session_id': 'test_session_123',
						'timestamp': '2024-01-01T12:00:00Z'
				}
				
				response = self.client.post(
						'/api/chat/message',
						data=json.dumps(chat_data),
						content_type='application/json'
				)
				
				self.assertEqual(response.status_code, 200)
				data = json.loads(response.data)
				self.assertTrue(data['success'])
				self.assertIn('message', data['data'])
		
		def test_chat_message_empty(self):
				"""빈 메시지 처리 테스트"""
				chat_data = {
						'message': '',
						'session_id': 'test_session_123'
				}
				
				response = self.client.post(
						'/api/chat/message',
						data=json.dumps(chat_data),
						content_type='application/json'
				)
				
				self.assertEqual(response.status_code, 400)
				data = json.loads(response.data)
				self.assertFalse(data['success'])
		
		def test_get_chat_examples(self):
				"""채팅 예제 질문 조회 테스트"""
				response = self.client.get('/api/chat/examples')
				
				self.assertEqual(response.status_code, 200)
				data = json.loads(response.data)
				self.assertTrue(data['success'])
				self.assertIn('examples', data['data'])
		
		def test_cors_headers(self):
				"""CORS 헤더 확인 테스트"""
				response = self.client.options('/api/restaurants')
				
				# CORS 헤더가 포함되어야 함
				self.assertIn('Access-Control-Allow-Origin', response.headers)
				self.assertIn('Access-Control-Allow-Methods', response.headers)
		
		def test_content_type_validation(self):
				"""Content-Type 검증 테스트"""
				# JSON이 아닌 데이터 전송
				response = self.client.post(
						'/api/reviews',
						data='invalid data',
						content_type='text/plain'
				)
				
				self.assertEqual(response.status_code, 400)
		
		def test_rate_limiting(self):
				"""API 요청 제한 테스트 (실제로는 설정에 따라)"""
				# 연속으로 많은 요청 보내기
				responses = []
				for i in range(10):
						response = self.client.get('/api/restaurants')
						responses.append(response.status_code)
				
				# 모든 요청이 성공해야 함 (실제 rate limiting은 설정에 따라)
				self.assertTrue(all(status == 200 for status in responses))
		
		def test_error_handling(self):
				"""오류 처리 테스트"""
				# 잘못된 JSON 형식
				response = self.client.post(
						'/api/reviews',
						data='{"invalid": json}',
						content_type='application/json'
				)
				
				self.assertEqual(response.status_code, 400)
				data = json.loads(response.data)
				self.assertFalse(data['success'])
				self.assertIn('error', data)

if __name__ == '__main__':
		unittest.main()