#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터베이스 초기화 스크립트
FOODI 프로젝트의 데이터베이스를 처음 설정할 때 실행하는 스크립트입니다.
"""

import sys
import os
import logging
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.config.settings import Config
from app.models.user import User
from app.models.restaurant import Restaurant
from app.models.review import Review
from app.models.recommendation import Recommendation

# 로깅 설정
logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_database():
		"""
		데이터베이스를 초기화하고 기본 테이블을 생성합니다.
		"""
		try:
				logger.info("🚀 FOODI 데이터베이스 초기화를 시작합니다...")
				
				# Flask 앱 생성
				app = create_app()
				
				with app.app_context():
						# 기존 테이블 삭제 (개발 환경에서만)
						if Config.FLASK_ENV == 'development':
								logger.info("⚠️  개발 환경: 기존 테이블을 삭제합니다...")
								db.drop_all()
						
						# 모든 테이블 생성
						logger.info("📋 데이터베이스 테이블을 생성합니다...")
						db.create_all()
						
						# 기본 데이터 삽입
						logger.info("📝 기본 데이터를 삽입합니다...")
						create_default_data()
						
						logger.info("✅ 데이터베이스 초기화가 완료되었습니다!")
						
						# 생성된 테이블 정보 출력
						print_table_info()
				
		except Exception as e:
				logger.error(f"❌ 데이터베이스 초기화 중 오류 발생: {e}")
				sys.exit(1)

def create_default_data():
		"""
		시스템 운영에 필요한 기본 데이터를 생성합니다.
		"""
		try:
				# 관리자 사용자 생성
				admin_user = User.query.filter_by(username='admin').first()
				if not admin_user:
						admin_user = User(
								username='admin',
								email='admin@foodi.com',
								location='대구 달서구',
								is_admin=True,
								food_preferences={
										'favorite_cuisines': [
												{'type': '한식', 'level': 5, 'added_at': datetime.utcnow().isoformat()},
												{'type': '중식', 'level': 4, 'added_at': datetime.utcnow().isoformat()}
										],
										'spice_level': 'medium',
										'price_sensitivity': 'medium',
										'atmosphere_preference': 'casual'
								}
						)
						db.session.add(admin_user)
						logger.info("👤 관리자 계정이 생성되었습니다 (admin@foodi.com)")
				
				# 테스트 사용자 생성 (개발 환경에서만)
				if Config.FLASK_ENV == 'development':
						test_user = User.query.filter_by(username='testuser').first()
						if not test_user:
								test_user = User(
										username='testuser',
										email='test@foodi.com',
										location='대구 달서구',
										budget_range='15000-25000',
										food_preferences={
												'favorite_cuisines': [
														{'type': '일식', 'level': 5, 'added_at': datetime.utcnow().isoformat()},
														{'type': '양식', 'level': 3, 'added_at': datetime.utcnow().isoformat()}
												],
												'spice_level': 'mild',
												'atmosphere_preference': 'quiet'
										}
								)
								db.session.add(test_user)
								logger.info("🧪 테스트 사용자가 생성되었습니다 (test@foodi.com)")
				
				# 샘플 식당 데이터 생성 (개발 환경에서만)
				if Config.FLASK_ENV == 'development':
						create_sample_restaurants()
				
				# 변경사항 저장
				db.session.commit()
				logger.info("💾 기본 데이터 저장이 완료되었습니다")
				
		except Exception as e:
				logger.error(f"❌ 기본 데이터 생성 중 오류 발생: {e}")
				db.session.rollback()
				raise

def create_sample_restaurants():
		"""
		개발 및 테스트를 위한 샘플 식당 데이터를 생성합니다.
		"""
		sample_restaurants = [
				{
						'name': '대구할매순대국',
						'address': '대구 달서구 월배로 123',
						'category': '한식',
						'cuisine_type': '국물요리',
						'description': '40년 전통의 순대국 전문점',
						'phone': '053-123-4567',
						'average_price': 8000,
						'latitude': 35.8714,
						'longitude': 128.6014,
						'menu_items': [
								{'name': '순대국', 'price': 8000, 'category': '메인'},
								{'name': '순대국밥', 'price': 9000, 'category': '메인'},
								{'name': '머리고기국밥', 'price': 10000, 'category': '메인'}
						],
						'special_features': ['주차가능', '포장가능', '24시간'],
						'atmosphere_tags': ['전통적인', '서민적인', '푸근한']
				},
				{
						'name': '월성동 맛집 치킨',
						'address': '대구 달서구 월성로 456',
						'category': '치킨',
						'cuisine_type': '양념치킨',
						'description': '바삭한 양념치킨 전문점',
						'phone': '053-234-5678',
						'average_price': 18000,
						'latitude': 35.8650,
						'longitude': 128.5950,
						'menu_items': [
								{'name': '양념치킨', 'price': 18000, 'category': '메인'},
								{'name': '후라이드치킨', 'price': 17000, 'category': '메인'},
								{'name': '반반치킨', 'price': 19000, 'category': '메인'}
						],
						'special_features': ['배달가능', '포장가능', '주차가능'],
						'atmosphere_tags': ['캐주얼', '가족친화적']
				},
				{
						'name': '성서 이탈리안 파스타',
						'address': '대구 달서구 성서로 789',
						'category': '양식',
						'cuisine_type': '이탈리안',
						'description': '정통 이탈리안 파스타 전문점',
						'phone': '053-345-6789',
						'average_price': 15000,
						'latitude': 35.8500,
						'longitude': 128.5800,
						'menu_items': [
								{'name': '까르보나라', 'price': 14000, 'category': '파스타'},
								{'name': '토마토파스타', 'price': 13000, 'category': '파스타'},
								{'name': '알리오올리오', 'price': 12000, 'category': '파스타'}
						],
						'special_features': ['데이트코스', '와인', '분위기좋음'],
						'atmosphere_tags': ['로맨틱', '모던', '세련된']
				}
		]
		
		for restaurant_data in sample_restaurants:
				existing = Restaurant.query.filter_by(name=restaurant_data['name']).first()
				if not existing:
						restaurant = Restaurant(**restaurant_data)
						db.session.add(restaurant)
						logger.info(f"🍽️  샘플 식당 추가: {restaurant_data['name']}")

def print_table_info():
		"""
		생성된 테이블 정보를 출력합니다.
		"""
		try:
				logger.info("📊 생성된 테이블 정보:")
				
				# 각 테이블의 레코드 수 조회
				tables_info = [
						('Users', User.query.count()),
						('Restaurants', Restaurant.query.count()),
						('Reviews', Review.query.count()),
						('Recommendations', Recommendation.query.count())
				]
				
				for table_name, count in tables_info:
						logger.info(f"   • {table_name}: {count}개 레코드")
				
				# 데이터베이스 파일 위치 (SQLite인 경우)
				if 'sqlite' in Config.SQLALCHEMY_DATABASE_URI:
						db_path = Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
						logger.info(f"💾 데이터베이스 파일: {db_path}")
				
		except Exception as e:
				logger.warning(f"테이블 정보 조회 중 오류: {e}")

def check_prerequisites():
		"""
		초기화 전 필수 조건들을 확인합니다.
		"""
		logger.info("🔍 필수 조건을 확인합니다...")
		
		# 환경 변수 확인
		if not Config.OPENAI_API_KEY:
				logger.warning("⚠️  OPENAI_API_KEY가 설정되지 않았습니다.")
		
		if not Config.GOOGLE_MAPS_API_KEY:
				logger.warning("⚠️  GOOGLE_MAPS_API_KEY가 설정되지 않았습니다.")
		
		# 데이터베이스 디렉토리 확인 및 생성
		if 'sqlite' in Config.SQLALCHEMY_DATABASE_URI:
				db_path = Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
				db_dir = os.path.dirname(db_path)
				
				if db_dir and not os.path.exists(db_dir):
						os.makedirs(db_dir, exist_ok=True)
						logger.info(f"📁 데이터베이스 디렉토리 생성: {db_dir}")
		
		logger.info("✅ 필수 조건 확인 완료")

def create_admin_user_interactive():
		"""
		대화형으로 관리자 사용자를 생성합니다.
		"""
		if Config.FLASK_ENV != 'development':
				return
		
		print("\n" + "="*50)
		print("🔧 관리자 계정 설정")
		print("="*50)
		
		try:
				# 기존 관리자 확인
				existing_admin = User.query.filter_by(is_admin=True).first()
				if existing_admin:
						print(f"✅ 기존 관리자 계정이 있습니다: {existing_admin.username}")
						return
				
				# 새 관리자 정보 입력
				username = input("관리자 사용자명 (기본: admin): ").strip() or 'admin'
				email = input("관리자 이메일 (기본: admin@foodi.com): ").strip() or 'admin@foodi.com'
				location = input("기본 위치 (기본: 대구 달서구): ").strip() or '대구 달서구'
				
				# 관리자 계정 생성
				admin_user = User(
						username=username,
						email=email,
						location=location,
						is_admin=True
				)
				
				db.session.add(admin_user)
				db.session.commit()
				
				print(f"✅ 관리자 계정이 생성되었습니다: {username}")
				
		except KeyboardInterrupt:
				print("\n❌ 관리자 계정 생성이 취소되었습니다.")
		except Exception as e:
				print(f"❌ 관리자 계정 생성 중 오류: {e}")
				db.session.rollback()

def main():
		"""메인 함수"""
		print("🍽️  FOODI 맛집 추천 챗봇")
		print("=" * 50)
		print("데이터베이스 초기화를 시작합니다...\n")
		
		try:
				# 필수 조건 확인
				check_prerequisites()
				
				# 데이터베이스 초기화
				init_database()
				
				print("\n" + "="*50)
				print("🎉 FOODI 데이터베이스 초기화가 완료되었습니다!")
				print("="*50)
				print("이제 다음 명령으로 서버를 시작할 수 있습니다:")
				print("python run.py")
				print("="*50)
				
		except KeyboardInterrupt:
				print("\n❌ 초기화가 사용자에 의해 중단되었습니다.")
				sys.exit(1)
		except Exception as e:
				logger.error(f"❌ 초기화 실패: {e}")
				sys.exit(1)

if __name__ == '__main__':
		main()