# tests/test_review_manager.py
"""
ReviewManager 클래스에 대한 단위 테스트
리뷰 수집 및 감정 분석 기능 테스트
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.review_manager import ReviewManager
from app.utils.sentiment_analyzer import SentimentAnalyzer

class TestReviewManager(unittest.TestCase):
		"""ReviewManager 테스트 클래스"""
		
		def setUp(self):
				"""테스트 환경 설정"""
				self.review_manager = ReviewManager()
				self.sample_review_data = {
						'restaurant_id': 1,
						'user_session': 'test_session',
						'rating': 5,
						'content': '정말 맛있었어요! 직원들도 친절하고 분위기도 좋았습니다.',
						'purpose': '데이트'
				}
		
		@patch('app.services.review_manager.DatabaseManager')
		@patch('app.services.review_manager.SentimentAnalyzer')
		def test_create_review(self, mock_sentiment, mock_db):
				"""리뷰 생성 테스트"""
				# Mock 설정
				mock_sentiment_instance = Mock()
				mock_sentiment.return_value = mock_sentiment_instance
				mock_sentiment_instance.analyze.return_value = {
						'score': 0.8,
						'label': 'positive',
						'confidence': 0.9
				}
				
				mock_db_instance = Mock()
				mock_db.return_value = mock_db_instance
				mock_db_instance.create_review.return_value = 123
				
				# 테스트 실행
				review_id = self.review_manager.create_review(self.sample_review_data)
				
				# 검증
				self.assertEqual(review_id, 123)
				mock_sentiment_instance.analyze.assert_called_once_with(
						self.sample_review_data['content']
				)
				mock_db_instance.create_review.assert_called_once()
		
		def test_validate_review_data(self):
				"""리뷰 데이터 유효성 검증 테스트"""
				# 유효한 데이터
				validation_result = self.review_manager.validate_review_data(self.sample_review_data)
				self.assertTrue(validation_result['valid'])
				
				# 필수 필드 누락
				invalid_data = self.sample_review_data.copy()
				del invalid_data['restaurant_id']
				
				validation_result = self.review_manager.validate_review_data(invalid_data)
				self.assertFalse(validation_result['valid'])
				self.assertIn('restaurant_id', validation_result['errors'])
				
				# 평점 범위 오류
				invalid_data = self.sample_review_data.copy()
				invalid_data['rating'] = 6
				
				validation_result = self.review_manager.validate_review_data(invalid_data)
				self.assertFalse(validation_result['valid'])
				self.assertIn('rating', validation_result['errors'])
		
		@patch('app.services.review_manager.DatabaseManager')
		def test_get_reviews_by_restaurant(self, mock_db):
				"""식당별 리뷰 조회 테스트"""
				mock_db_instance = Mock()
				mock_db.return_value = mock_db_instance
				mock_db_instance.get_reviews_by_restaurant_id.return_value = [
						{
								'id': 1,
								'rating': 5,
								'content': '맛있어요',
								'sentiment_score': 0.8,
								'created_at': '2024-01-01'
						}
				]
				
				reviews = self.review_manager.get_reviews_by_restaurant(
						restaurant_id=1,
						page=1,
						per_page=10
				)
				
				self.assertIsInstance(reviews, list)
				self.assertEqual(len(reviews), 1)
				self.assertEqual(reviews[0]['rating'], 5)
		
		@patch('app.services.review_manager.DatabaseManager')
		def test_calculate_review_statistics(self, mock_db):
				"""리뷰 통계 계산 테스트"""
				mock_db_instance = Mock()
				mock_db.return_value = mock_db_instance
				mock_db_instance.get_reviews_by_restaurant_id.return_value = [
						{'rating': 5, 'sentiment_score': 0.8},
						{'rating': 4, 'sentiment_score': 0.6},
						{'rating': 5, 'sentiment_score': 0.9}
				]
				
				stats = self.review_manager.calculate_review_statistics(restaurant_id=1)
				
				self.assertEqual(stats['total_reviews'], 3)
				self.assertAlmostEqual(stats['average_rating'], 4.67, places=1)
				self.assertAlmostEqual(stats['average_sentiment'], 0.77, places=1)
				self.assertEqual(stats['positive_reviews'], 3)
		
		def test_filter_inappropriate_content(self):
				"""부적절한 내용 필터링 테스트"""
				inappropriate_content = "이 식당은 정말 @@@@하고 ####한 곳이다"
				
				filtered_content = self.review_manager.filter_inappropriate_content(
						inappropriate_content
				)
				
				self.assertNotIn('@@@@', filtered_content)
				self.assertNotIn('####', filtered_content)
		
		@patch('app.services.review_manager.SentimentAnalyzer')
		def test_sentiment_analysis_integration(self, mock_sentiment):
				"""감정 분석 통합 테스트"""
				mock_sentiment_instance = Mock()
				mock_sentiment.return_value = mock_sentiment_instance
				
				# 긍정적 리뷰
				mock_sentiment_instance.analyze.return_value = {
						'score': 0.9,
						'label': 'positive',
						'confidence': 0.95
				}
				
				result = self.review_manager.analyze_review_sentiment(
						"정말 맛있고 서비스도 훌륭했습니다!"
				)
				
				self.assertEqual(result['label'], 'positive')
				self.assertGreater(result['score'], 0.8)
				
				# 부정적 리뷰
				mock_sentiment_instance.analyze.return_value = {
						'score': -0.7,
						'label': 'negative',
						'confidence': 0.85
				}
				
				result = self.review_manager.analyze_review_sentiment(
						"음식이 너무 짜고 서비스가 별로였어요"
				)
				
				self.assertEqual(result['label'], 'negative')
				self.assertLess(result['score'], -0.5)
		
		def test_review_keyword_extraction(self):
				"""리뷰 키워드 추출 테스트"""
				review_content = "음식이 정말 맛있고 직원들이 친절해요. 분위기도 좋고 가격도 합리적입니다."
				
				keywords = self.review_manager.extract_keywords(review_content)
				
				expected_keywords = ['맛있', '친절', '분위기', '가격', '합리적']
				
				for keyword in expected_keywords:
						self.assertTrue(any(keyword in k for k in keywords))
		
		@patch('app.services.review_manager.DatabaseManager')
		def test_update_restaurant_rating(self, mock_db):
				"""식당 평점 업데이트 테스트"""
				mock_db_instance = Mock()
				mock_db.return_value = mock_db_instance
				
				# 새 리뷰로 인한 평점 업데이트
				self.review_manager.update_restaurant_rating(
						restaurant_id=1,
						new_rating=5,
						review_count=10
				)
				
				mock_db_instance.update_restaurant_rating.assert_called_once()
		
		def test_review_spam_detection(self):
				"""리뷰 스팸 감지 테스트"""
				# 반복적인 내용
				spam_review = "좋아요 " * 20
				is_spam = self.review_manager.detect_spam(spam_review)
				self.assertTrue(is_spam)
				
				# 정상적인 리뷰
				normal_review = "음식이 맛있고 서비스가 좋았습니다. 다시 방문하고 싶어요."
				is_spam = self.review_manager.detect_spam(normal_review)
				self.assertFalse(is_spam)
		
		def test_review_moderation(self):
				"""리뷰 검토 테스트"""
				review_data = self.sample_review_data.copy()
				
				# 정상적인 리뷰
				moderation_result = self.review_manager.moderate_review(review_data)
				self.assertTrue(moderation_result['approved'])
				
				# 부적절한 내용 포함
				review_data['content'] = "이 식당은 정말 최악이고 @@@@합니다"
				moderation_result = self.review_manager.moderate_review(review_data)
				self.assertFalse(moderation_result['approved'])

if __name__ == '__main__':
		unittest.main()