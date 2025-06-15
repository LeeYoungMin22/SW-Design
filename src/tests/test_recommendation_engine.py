# tests/test_recommendation_engine.py
"""
RecommendationEngine 클래스에 대한 단위 테스트
AI 기반 맛집 추천 기능 테스트
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json

from app.services.recommendation_engine import RecommendationEngine
from app.models.restaurant import Restaurant

class TestRecommendationEngine(unittest.TestCase):
		"""RecommendationEngine 테스트 클래스"""
		
		def setUp(self):
				"""테스트 환경 설정"""
				self.recommendation_engine = RecommendationEngine()
				self.sample_restaurants = [
						{
								'id': 1,
								'name': '할매국수',
								'category': '한식',
								'rating': 4.5,
								'price_range': '5000-10000',
								'description': '전통 칼국수 전문점'
						},
						{
								'id': 2,
								'name': '대박삼겹살',
								'category': '고기',
								'rating': 4.3,
								'price_range': '15000-25000',
								'description': '신선한 국내산 삼겹살'
						}
				]
		
		def test_filter_by_category(self):
				"""카테고리별 필터링 테스트"""
				result = self.recommendation_engine.filter_restaurants(
						self.sample_restaurants,
						category='한식'
				)
				
				self.assertEqual(len(result), 1)
				self.assertEqual(result[0]['name'], '할매국수')
		
		def test_filter_by_price_range(self):
				"""가격대별 필터링 테스트"""
				result = self.recommendation_engine.filter_restaurants(
						self.sample_restaurants,
						max_price=12000
				)
				
				self.assertEqual(len(result), 1)
				self.assertEqual(result[0]['name'], '할매국수')
		
		def test_filter_by_rating(self):
				"""평점별 필터링 테스트"""
				result = self.recommendation_engine.filter_restaurants(
						self.sample_restaurants,
						min_rating=4.4
				)
				
				self.assertEqual(len(result), 1)
				self.assertEqual(result[0]['name'], '할매국수')
		
		@patch('app.services.recommendation_engine.OpenAIService')
		def test_analyze_user_intent(self, mock_openai):
				"""사용자 의도 분석 테스트"""
				mock_openai_instance = Mock()
				mock_openai.return_value = mock_openai_instance
				mock_openai_instance.analyze_intent.return_value = {
						'category': '고기',
						'max_price': 20000,
						'purpose': '회식',
						'keywords': ['삼겹살', '회식']
				}
				
				user_message = '2만원 이하로 회식하기 좋은 고기집 추천해줘'
				intent = self.recommendation_engine.analyze_user_intent(user_message)
				
				self.assertEqual(intent['category'], '고기')
				self.assertEqual(intent['max_price'], 20000)
				self.assertEqual(intent['purpose'], '회식')
		
		def test_score_restaurants(self):
				"""식당 점수 계산 테스트"""
				user_preferences = {
						'category': '한식',
						'max_price': 15000,
						'min_rating': 4.0
				}
				
				scored_restaurants = self.recommendation_engine.score_restaurants(
						self.sample_restaurants,
						user_preferences
				)
				
				self.assertEqual(len(scored_restaurants), 2)
				# 한식 식당이 더 높은 점수를 받아야 함
				self.assertGreater(scored_restaurants[0]['score'], scored_restaurants[1]['score'])
		
		def test_generate_explanation(self):
				"""추천 이유 생성 테스트"""
				restaurant = self.sample_restaurants[0]
				user_intent = {
						'category': '한식',
						'max_price': 15000,
						'keywords': ['전통', '국수']
				}
				
				explanation = self.recommendation_engine.generate_explanation(
						restaurant, user_intent
				)
				
				self.assertIsInstance(explanation, str)
				self.assertGreater(len(explanation), 10)
				self.assertIn('전통', explanation.lower())
		
		@patch('app.services.recommendation_engine.DatabaseManager')
		def test_get_similar_restaurants(self, mock_db):
				"""유사한 식당 찾기 테스트"""
				mock_db_instance = Mock()
				mock_db.return_value = mock_db_instance
				mock_db_instance.find_similar_restaurants.return_value = [
						self.sample_restaurants[1]
				]
				
				similar = self.recommendation_engine.get_similar_restaurants(
						restaurant_id=1,
						limit=3
				)
				
				self.assertIsInstance(similar, list)
				self.assertEqual(len(similar), 1)
		
		def test_personalize_recommendations(self):
				"""개인화 추천 테스트"""
				user_history = [
						{'restaurant_id': 1, 'rating': 5, 'category': '한식'},
						{'restaurant_id': 2, 'rating': 4, 'category': '고기'}
				]
				
				personalized = self.recommendation_engine.personalize_recommendations(
						self.sample_restaurants,
						user_history
				)
				
				self.assertIsInstance(personalized, list)
				# 사용자가 선호하는 카테고리가 우선순위에 있어야 함
				self.assertEqual(personalized[0]['category'], '한식')
		
		def test_handle_complex_query(self):
				"""복합 조건 쿼리 처리 테스트"""
				complex_query = "가족과 함께 갈 만한 2만원 이하 한식당 중에서 주차 가능한 곳"
				
				parsed_conditions = self.recommendation_engine.parse_complex_query(complex_query)
				
				expected_conditions = {
						'category': '한식',
						'max_price': 20000,
						'purpose': '가족식사',
						'amenities': ['주차']
				}
				
				for key, value in expected_conditions.items():
						self.assertIn(key, parsed_conditions)
		
		def test_location_based_filtering(self):
				"""위치 기반 필터링 테스트"""
				user_location = {'lat': 35.8562, 'lng': 128.5327}
				
				# 거리 계산 테스트
				restaurant_location = {'lat': 35.8570, 'lng': 128.5330}
				distance = self.recommendation_engine.calculate_distance(
						user_location, restaurant_location
				)
				
				self.assertIsInstance(distance, float)
				self.assertLess(distance, 1.0)  # 1km 이내
		
		def test_time_based_filtering(self):
				"""시간 기반 필터링 테스트"""
				from datetime import datetime, time
				
				current_time = time(14, 30)  # 오후 2시 30분
				
				restaurants_with_hours = [
						{**self.sample_restaurants[0], 'hours': '09:00-21:00'},
						{**self.sample_restaurants[1], 'hours': '17:00-02:00'}
				]
				
				open_restaurants = self.recommendation_engine.filter_by_operating_hours(
						restaurants_with_hours, current_time
				)
				
				self.assertEqual(len(open_restaurants), 1)
				self.assertEqual(open_restaurants[0]['name'], '할매국수')

if __name__ == '__main__':
		unittest.main()