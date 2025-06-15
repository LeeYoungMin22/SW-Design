# tests/test_database_manager.py
"""
DatabaseManager 클래스에 대한 단위 테스트
SQLite CRUD 관리 기능 테스트
"""

import unittest
import sqlite3
import tempfile
import os
from datetime import datetime

from app.services.database_manager import DatabaseManager
from app.models.restaurant import Restaurant
from app.models.review import Review

class TestDatabaseManager(unittest.TestCase):
		"""DatabaseManager 테스트 클래스"""
		
		def setUp(self):
				"""테스트 환경 설정"""
				# 임시 데이터베이스 파일 생성
				self.temp_db = tempfile.NamedTemporaryFile(delete=False)
				self.temp_db.close()
				self.db_path = self.temp_db.name
				
				self.db_manager = DatabaseManager(db_path=self.db_path)
				self.db_manager.init_database()
				
				# 테스트 데이터
				self.sample_restaurant = {
						'name': '테스트 식당',
						'category': '한식',
						'address': '대구 달서구 테스트로 123',
						'latitude': 35.8562,
						'longitude': 128.5327,
						'rating': 4.5,
						'price_range': '10000-20000',
						'phone': '053-123-4567',
						'hours': '11:00-22:00',
						'description': '테스트용 식당입니다.'
				}
		
		def tearDown(self):
				"""테스트 후 정리"""
				if os.path.exists(self.db_path):
						os.unlink(self.db_path)
		
		def test_database_initialization(self):
				"""데이터베이스 초기화 테스트"""
				# 테이블 존재 확인
				with sqlite3.connect(self.db_path) as conn:
						cursor = conn.cursor()
						
						# restaurants 테이블 확인
						cursor.execute("""
								SELECT name FROM sqlite_master 
								WHERE type='table' AND name='restaurants'
						""")
						self.assertIsNotNone(cursor.fetchone())
						
						# reviews 테이블 확인
						cursor.execute("""
								SELECT name FROM sqlite_master 
								WHERE type='table' AND name='reviews'
						""")
						self.assertIsNotNone(cursor.fetchone())
		
		def test_create_restaurant(self):
				"""식당 생성 테스트"""
				restaurant_id = self.db_manager.create_restaurant(self.sample_restaurant)
				
				self.assertIsNotNone(restaurant_id)
				self.assertIsInstance(restaurant_id, int)
				self.assertGreater(restaurant_id, 0)
		
		def test_get_restaurant_by_id(self):
				"""ID로 식당 조회 테스트"""
				# 식당 생성
				restaurant_id = self.db_manager.create_restaurant(self.sample_restaurant)
				
				# 조회
				retrieved_restaurant = self.db_manager.get_restaurant_by_id(restaurant_id)
				
				self.assertIsNotNone(retrieved_restaurant)
				self.assertEqual(retrieved_restaurant['name'], self.sample_restaurant['name'])
				self.assertEqual(retrieved_restaurant['category'], self.sample_restaurant['category'])
		
		def test_update_restaurant(self):
				"""식당 정보 업데이트 테스트"""
				# 식당 생성
				restaurant_id = self.db_manager.create_restaurant(self.sample_restaurant)
				
				# 업데이트
				update_data = {
						'rating': 4.8,
						'phone': '053-999-9999'
				}
				success = self.db_manager.update_restaurant(restaurant_id, update_data)
				
				self.assertTrue(success)
				
				# 확인
				updated_restaurant = self.db_manager.get_restaurant_by_id(restaurant_id)
				self.assertEqual(updated_restaurant['rating'], 4.8)
				self.assertEqual(updated_restaurant['phone'], '053-999-9999')
		
		def test_delete_restaurant(self):
				"""식당 삭제 테스트"""
				# 식당 생성
				restaurant_id = self.db_manager.create_restaurant(self.sample_restaurant)
				
				# 삭제
				success = self.db_manager.delete_restaurant(restaurant_id)
				self.assertTrue(success)
				
				# 확인
				deleted_restaurant = self.db_manager.get_restaurant_by_id(restaurant_id)
				self.assertIsNone(deleted_restaurant)
		
		def test_search_restaurants(self):
				"""식당 검색 테스트"""
				# 여러 식당 생성
				restaurants = [
						{**self.sample_restaurant, 'name': '한식당A', 'category': '한식'},
						{**self.sample_restaurant, 'name': '중식당B', 'category': '중식'},
						{**self.sample_restaurant, 'name': '한식당C', 'category': '한식'}
				]
				
				for restaurant in restaurants:
						self.db_manager.create_restaurant(restaurant)
				
				# 카테고리별 검색
				korean_restaurants = self.db_manager.search_restaurants(category='한식')
				self.assertEqual(len(korean_restaurants), 2)
				
				# 키워드 검색
				search_results = self.db_manager.search_restaurants(keyword='한식당')
				self.assertEqual(len(search_results), 2)
		
		def test_get_restaurants_with_filters(self):
				"""필터를 적용한 식당 조회 테스트"""
				# 다양한 가격대의 식당 생성
				restaurants = [
						{**self.sample_restaurant, 'name': '저렴한집', 'price_range': '5000-10000'},
						{**self.sample_restaurant, 'name': '보통집', 'price_range': '10000-20000'},
						{**self.sample_restaurant, 'name': '비싼집', 'price_range': '30000-50000'}
				]
				
				for restaurant in restaurants:
						self.db_manager.create_restaurant(restaurant)
				
				# 가격 필터 적용
				affordable_restaurants = self.db_manager.get_restaurants_with_filters(
						price_max=15000
				)
				self.assertEqual(len(affordable_restaurants), 2)
				
				# 평점 필터 적용
				high_rated = self.db_manager.get_restaurants_with_filters(
						rating_min=4.0
				)
				self.assertGreater(len(high_rated), 0)
		
		def test_create_review(self):
				"""리뷰 생성 테스트"""
				# 식당 먼저 생성
				restaurant_id = self.db_manager.create_restaurant(self.sample_restaurant)
				
				review_data = {
						'restaurant_id': restaurant_id,
						'user_session': 'test_user',
						'rating': 5,
						'content': '정말 맛있었어요!',
						'sentiment_score': 0.9,
						'sentiment_label': 'positive'
				}
				
				review_id = self.db_manager.create_review(review_data)
				
				self.assertIsNotNone(review_id)
				self.assertIsInstance(review_id, int)
				self.assertGreater(review_id, 0)
		
		def test_get_reviews_by_restaurant_id(self):
				"""식당별 리뷰 조회 테스트"""
				# 식당과 리뷰 생성
				restaurant_id = self.db_manager.create_restaurant(self.sample_restaurant)
				
				reviews_data = [
						{
								'restaurant_id': restaurant_id,
								'user_session': 'user1',
								'rating': 5,
								'content': '맛있어요',
								'sentiment_score': 0.8,
								'sentiment_label': 'positive'
						},
						{
								'restaurant_id': restaurant_id,
								'user_session': 'user2',
								'rating': 4,
								'content': '좋아요',
								'sentiment_score': 0.6,
								'sentiment_label': 'positive'
						}
				]
				
				for review_data in reviews_data:
						self.db_manager.create_review(review_data)
				
				# 리뷰 조회
				reviews = self.db_manager.get_reviews_by_restaurant_id(restaurant_id)
				
				self.assertEqual(len(reviews), 2)
				self.assertEqual(reviews[0]['restaurant_id'], restaurant_id)
		
		def test_get_review_statistics(self):
				"""리뷰 통계 조회 테스트"""
				# 식당과 리뷰 생성
				restaurant_id = self.db_manager.create_restaurant(self.sample_restaurant)
				
				ratings = [5, 4, 5, 3, 4]
				for i, rating in enumerate(ratings):
						review_data = {
								'restaurant_id': restaurant_id,
								'user_session': f'user{i}',
								'rating': rating,
								'content': f'리뷰 {i}',
								'sentiment_score': 0.5,
								'sentiment_label': 'neutral'
						}
						self.db_manager.create_review(review_data)
				
				# 통계 조회
				stats = self.db_manager.get_review_statistics(restaurant_id)
				
				self.assertEqual(stats['total_reviews'], 5)
				self.assertEqual(stats['average_rating'], 4.2)
				self.assertEqual(stats['rating_distribution']['5'], 2)
				self.assertEqual(stats['rating_distribution']['4'], 2)
		
		def test_get_nearby_restaurants(self):
				"""주변 식당 검색 테스트"""
				# 다양한 위치의 식당 생성
				restaurants = [
						{**self.sample_restaurant, 'name': '가까운집', 'latitude': 35.8562, 'longitude': 128.5327},
						{**self.sample_restaurant, 'name': '먼집', 'latitude': 35.9000, 'longitude': 128.6000}
				]
				
				for restaurant in restaurants:
						self.db_manager.create_restaurant(restaurant)
				
				# 주변 식당 검색 (반경 1km)
				center_lat, center_lng = 35.8562, 128.5327
				nearby = self.db_manager.get_nearby_restaurants(
						center_lat, center_lng, radius=1000
				)
				
				# 가까운 식당만 결과에 포함되어야 함
				self.assertEqual(len(nearby), 1)
				self.assertEqual(nearby[0]['name'], '가까운집')
		
		def test_database_transaction(self):
				"""데이터베이스 트랜잭션 테스트"""
				# 트랜잭션 내에서 여러 작업 수행
				try:
						with self.db_manager.get_connection() as conn:
								cursor = conn.cursor()
								
								# 여러 식당 동시 생성
								restaurants = [
										{**self.sample_restaurant, 'name': f'식당{i}'} 
										for i in range(3)
								]
								
								created_ids = []
								for restaurant in restaurants:
										restaurant_id = self.db_manager.create_restaurant(restaurant)
										created_ids.append(restaurant_id)
								
								# 모든 식당이 생성되었는지 확인
								self.assertEqual(len(created_ids), 3)
								
				except Exception as e:
						self.fail(f"트랜잭션 실행 중 오류 발생: {e}")

if __name__ == '__main__':
		unittest.main()