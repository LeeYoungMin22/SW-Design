#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
식당 데이터 로드 스크립트
JSON 파일이나 CSV 파일에서 식당 데이터를 읽어와 데이터베이스에 저장하는 스크립트입니다.
"""

import sys
import os
import json
import csv
import logging
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.restaurant import Restaurant
from app.services.database_manager import DatabaseManager
from app.services.map_renderer import MapRenderer

# 로깅 설정
logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RestaurantDataLoader:
		"""
		식당 데이터를 로드하고 처리하는 클래스
		"""
		
		def __init__(self):
				"""데이터 로더 초기화"""
				self.db_manager = DatabaseManager()
				self.map_renderer = MapRenderer()
				self.app = create_app()
				
				# 통계
				self.stats = {
						'total_processed': 0,
						'successful_inserts': 0,
						'skipped_duplicates': 0,
						'geocoding_success': 0,
						'geocoding_failed': 0,
						'errors': []
				}
		
		def load_from_json(self, file_path: str) -> None:
				"""
				JSON 파일에서 식당 데이터를 로드합니다.
				
				Args:
						file_path (str): JSON 파일 경로
				"""
				try:
						logger.info(f"📄 JSON 파일에서 데이터를 로드합니다: {file_path}")
						
						if not os.path.exists(file_path):
								raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
						
						with open(file_path, 'r', encoding='utf-8') as file:
								data = json.load(file)
						
						if isinstance(data, dict) and 'restaurants' in data:
								restaurants_data = data['restaurants']
						elif isinstance(data, list):
								restaurants_data = data
						else:
								raise ValueError("JSON 형식이 올바르지 않습니다. 'restaurants' 키가 있는 객체이거나 배열이어야 합니다.")
						
						logger.info(f"📊 총 {len(restaurants_data)}개의 식당 데이터를 발견했습니다.")
						
						# 데이터 처리
						self._process_restaurants_data(restaurants_data)
						
				except Exception as e:
						logger.error(f"❌ JSON 파일 로드 중 오류: {e}")
						raise
		
		def load_from_csv(self, file_path: str) -> None:
				"""
				CSV 파일에서 식당 데이터를 로드합니다.
				
				Args:
						file_path (str): CSV 파일 경로
				"""
				try:
						logger.info(f"📄 CSV 파일에서 데이터를 로드합니다: {file_path}")
						
						if not os.path.exists(file_path):
								raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
						
						restaurants_data = []
						
						with open(file_path, 'r', encoding='utf-8') as file:
								reader = csv.DictReader(file)
								
								for row in reader:
										# CSV 데이터를 식당 객체 형태로 변환
										restaurant_data = self._convert_csv_row_to_restaurant(row)
										if restaurant_data:
												restaurants_data.append(restaurant_data)
						
						logger.info(f"📊 총 {len(restaurants_data)}개의 식당 데이터를 변환했습니다.")
						
						# 데이터 처리
						self._process_restaurants_data(restaurants_data)
						
				except Exception as e:
						logger.error(f"❌ CSV 파일 로드 중 오류: {e}")
						raise
		
		def load_sample_data(self) -> None:
				"""
				샘플 식당 데이터를 생성하고 로드합니다.
				"""
				logger.info("🧪 샘플 식당 데이터를 생성합니다...")
				
				sample_restaurants = [
						{
								'name': '봉산찜갈비',
								'address': '대구 달서구 달구벌대로 1234',
								'category': '한식',
								'cuisine_type': '갈비찜',
								'description': '부드러운 찜갈비로 유명한 50년 전통 맛집',
								'phone': '053-111-2222',
								'average_price': 35000,
								'menu_items': [
										{'name': '찜갈비(소)', 'price': 35000, 'category': '메인'},
										{'name': '찜갈비(중)', 'price': 45000, 'category': '메인'},
										{'name': '찜갈비(대)', 'price': 55000, 'category': '메인'},
										{'name': '갈비탕', 'price': 12000, 'category': '국물'}
								],
								'special_features': ['주차가능', '단체석', '포장가능'],
								'atmosphere_tags': ['전통적인', '가족모임', '특별한날']
						},
						{
								'name': '대구 10미 칼국수',
								'address': '대구 달서구 월배로 567',
								'category': '한식',
								'cuisine_type': '칼국수',
								'description': '진한 육수의 칼국수 전문점',
								'phone': '053-222-3333',
								'average_price': 8000,
								'menu_items': [
										{'name': '칼국수', 'price': 8000, 'category': '메인'},
										{'name': '만두', 'price': 6000, 'category': '사이드'},
										{'name': '칼만두', 'price': 10000, 'category': '메인'}
								],
								'special_features': ['24시간', '주차가능', '포장가능'],
								'atmosphere_tags': ['서민적인', '친근한', '든든한']
						},
						{
								'name': '미스터피자 성서점',
								'address': '대구 달서구 성서로 890',
								'category': '양식',
								'cuisine_type': '피자',
								'description': '다양한 토핑의 피자 전문점',
								'phone': '053-333-4444',
								'average_price': 25000,
								'menu_items': [
										{'name': '페퍼로니 피자', 'price': 24000, 'category': '피자'},
										{'name': '콤비네이션 피자', 'price': 26000, 'category': '피자'},
										{'name': '치즈크러스트', 'price': 28000, 'category': '피자'}
								],
								'special_features': ['배달가능', '주차가능', '와이파이'],
								'atmosphere_tags': ['캐주얼', '가족친화적', '모던']
						},
						{
								'name': '교촌치킨 월성점',
								'address': '대구 달서구 월성로 123',
								'category': '치킨',
								'cuisine_type': '프라이드치킨',
								'description': '바삭한 허니콤보 치킨으로 유명',
								'phone': '053-444-5555',
								'average_price': 20000,
								'menu_items': [
										{'name': '허니콤보', 'price': 20000, 'category': '치킨'},
										{'name': '레드콤보', 'price': 21000, 'category': '치킨'},
										{'name': '오리지널', 'price': 18000, 'category': '치킨'}
								],
								'special_features': ['배달가능', '포장가능', '주차가능'],
								'atmosphere_tags': ['캐주얼', '배달맛집', '간편한']
						},
						{
								'name': '스시로 성서점',
								'address': '대구 달서구 성서중앙로 456',
								'category': '일식',
								'cuisine_type': '초밥',
								'description': '회전초밥 전문점, 신선한 회와 초밥',
								'phone': '053-555-6666',
								'average_price': 15000,
								'menu_items': [
										{'name': '연어초밥', 'price': 200, 'category': '초밥'},
										{'name': '참치초밥', 'price': 300, 'category': '초밥'},
										{'name': '우동', 'price': 3000, 'category': '면'}
								],
								'special_features': ['회전초밥', '주차가능', '가족석'],
								'atmosphere_tags': ['깔끔한', '신선한', '일본식']
						}
				]
				
				self._process_restaurants_data(sample_restaurants)
		
		def _process_restaurants_data(self, restaurants_data: list) -> None:
				"""
				식당 데이터 리스트를 처리하여 데이터베이스에 저장합니다.
				
				Args:
						restaurants_data (list): 식당 데이터 리스트
				"""
				with self.app.app_context():
						logger.info("🔄 식당 데이터 처리를 시작합니다...")
						
						for i, restaurant_data in enumerate(restaurants_data, 1):
								try:
										self.stats['total_processed'] += 1
										
										# 진행 상황 표시
										if i % 10 == 0 or i == 1:
												logger.info(f"📍 처리 중... {i}/{len(restaurants_data)}")
										
										# 중복 확인
										if self._is_duplicate_restaurant(restaurant_data):
												self.stats['skipped_duplicates'] += 1
												logger.debug(f"⏭️  중복 건너뜀: {restaurant_data.get('name', 'Unknown')}")
												continue
										
										# 위치 정보 보완 (위도/경도가 없는 경우)
										if not restaurant_data.get('latitude') or not restaurant_data.get('longitude'):
												self._add_geocoding_info(restaurant_data)
										
										# 식당 객체 생성 및 저장
										restaurant = self._create_restaurant_object(restaurant_data)
										db.session.add(restaurant)
										
										self.stats['successful_inserts'] += 1
										logger.debug(f"✅ 저장 완료: {restaurant.name}")
										
								except Exception as e:
										error_msg = f"식당 '{restaurant_data.get('name', 'Unknown')}' 처리 중 오류: {e}"
										logger.warning(error_msg)
										self.stats['errors'].append(error_msg)
										continue
						
						# 일괄 커밋
						try:
								db.session.commit()
								logger.info("💾 모든 변경사항이 데이터베이스에 저장되었습니다.")
						except Exception as e:
								db.session.rollback()
								logger.error(f"❌ 데이터베이스 저장 중 오류: {e}")
								raise
		
		def _convert_csv_row_to_restaurant(self, row: dict) -> dict:
				"""
				CSV 행을 식당 데이터 딕셔너리로 변환합니다.
				
				Args:
						row (dict): CSV 행 데이터
						
				Returns:
						dict: 변환된 식당 데이터
				"""
				try:
						# 필수 필드 확인
						if not row.get('name') or not row.get('address'):
								logger.warning(f"필수 필드 누락: {row}")
								return None
						
						# 기본 데이터 변환
						restaurant_data = {
								'name': row['name'].strip(),
								'address': row['address'].strip(),
								'category': row.get('category', '기타').strip(),
								'cuisine_type': row.get('cuisine_type', '').strip(),
								'description': row.get('description', '').strip(),
								'phone': row.get('phone', '').strip(),
								'website': row.get('website', '').strip()
						}
						
						# 숫자 필드 변환
						try:
								if row.get('average_price'):
										restaurant_data['average_price'] = int(row['average_price'])
								if row.get('latitude'):
										restaurant_data['latitude'] = float(row['latitude'])
								if row.get('longitude'):
										restaurant_data['longitude'] = float(row['longitude'])
						except (ValueError, TypeError) as e:
								logger.warning(f"숫자 변환 오류 ({row.get('name')}): {e}")
						
						# JSON 필드 변환
						try:
								if row.get('menu_items'):
										restaurant_data['menu_items'] = json.loads(row['menu_items'])
								if row.get('special_features'):
										restaurant_data['special_features'] = json.loads(row['special_features'])
								if row.get('atmosphere_tags'):
										restaurant_data['atmosphere_tags'] = json.loads(row['atmosphere_tags'])
						except json.JSONDecodeError as e:
								logger.warning(f"JSON 변환 오류 ({row.get('name')}): {e}")
						
						return restaurant_data
						
				except Exception as e:
						logger.error(f"CSV 행 변환 중 오류: {e}")
						return None
		
		def _is_duplicate_restaurant(self, restaurant_data: dict) -> bool:
				"""
				중복 식당인지 확인합니다.
				
				Args:
						restaurant_data (dict): 식당 데이터
						
				Returns:
						bool: 중복 여부
				"""
				existing = Restaurant.query.filter_by(
						name=restaurant_data['name'],
						address=restaurant_data['address']
				).first()
				
				return existing is not None
		
		def _add_geocoding_info(self, restaurant_data: dict) -> None:
				"""
				주소를 위도/경도로 변환하여 추가합니다.
				
				Args:
						restaurant_data (dict): 식당 데이터
				"""
				if not restaurant_data.get('address'):
						return
				
				# Google Maps API 키 확인
				if not self.map_renderer or not hasattr(self.map_renderer, 'api_key') or not self.map_renderer.api_key:
						logger.debug(f"⏭️  지오코딩 건너뜀 (API 키 미설정): {restaurant_data.get('name')}")
						self.stats['geocoding_failed'] += 1
						
						# 기본 좌표 설정 (대구 달서구 중심)
						restaurant_data['latitude'] = 35.8714
						restaurant_data['longitude'] = 128.6014
						return
				
				try:
						coords = self.map_renderer.geocode_address(restaurant_data['address'])
						if coords:
								restaurant_data['latitude'], restaurant_data['longitude'] = coords
								self.stats['geocoding_success'] += 1
								logger.debug(f"🗺️  지오코딩 성공: {restaurant_data['name']}")
						else:
								self.stats['geocoding_failed'] += 1
								logger.debug(f"🗺️  지오코딩 실패: {restaurant_data['name']}")
								
								# 기본 좌표 설정 (대구 달서구 중심)
								restaurant_data['latitude'] = 35.8714
								restaurant_data['longitude'] = 128.6014
								
				except Exception as e:
						self.stats['geocoding_failed'] += 1
						logger.debug(f"🗺️  지오코딩 오류 ({restaurant_data['name']}): {e}")
						
						# 기본 좌표 설정 (대구 달서구 중심)
						restaurant_data['latitude'] = 35.8714
						restaurant_data['longitude'] = 128.6014
		
		def _create_restaurant_object(self, restaurant_data: dict) -> Restaurant:
				"""
				식당 데이터에서 Restaurant 객체를 생성합니다.
				
				Args:
						restaurant_data (dict): 식당 데이터
						
				Returns:
						Restaurant: 생성된 식당 객체
				"""
				# 기본 운영시간 설정 (데이터에 없는 경우)
				if 'business_hours' not in restaurant_data:
						restaurant_data['business_hours'] = {
								'monday': {'open': '11:00', 'close': '22:00'},
								'tuesday': {'open': '11:00', 'close': '22:00'},
								'wednesday': {'open': '11:00', 'close': '22:00'},
								'thursday': {'open': '11:00', 'close': '22:00'},
								'friday': {'open': '11:00', 'close': '22:00'},
								'saturday': {'open': '11:00', 'close': '22:00'},
								'sunday': {'open': '11:00', 'close': '22:00'}
						}
				
				# 지역 정보 추출 (주소에서)
				if 'district' not in restaurant_data and restaurant_data.get('address'):
						address_parts = restaurant_data['address'].split()
						for part in address_parts:
								if '구' in part:
										restaurant_data['district'] = part.replace('구', '') + '구'
										break
				
				return Restaurant(**restaurant_data)
		
		def print_statistics(self) -> None:
				"""처리 통계를 출력합니다."""
				logger.info("📊 데이터 로드 통계:")
				logger.info(f"   • 총 처리: {self.stats['total_processed']}개")
				logger.info(f"   • 성공적 삽입: {self.stats['successful_inserts']}개")
				logger.info(f"   • 중복 건너뜀: {self.stats['skipped_duplicates']}개")
				logger.info(f"   • 지오코딩 성공: {self.stats['geocoding_success']}개")
				logger.info(f"   • 지오코딩 실패: {self.stats['geocoding_failed']}개")
				
				if self.stats['errors']:
						logger.warning(f"   • 오류: {len(self.stats['errors'])}개")
						for error in self.stats['errors'][:5]:  # 처음 5개만 표시
								logger.warning(f"     - {error}")

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='FOODI 식당 데이터 로더')
    parser.add_argument('--json', type=str, help='JSON 파일 경로')
    parser.add_argument('--csv', type=str, help='CSV 파일 경로')
    parser.add_argument('--sample', action='store_true', help='샘플 데이터 로드')
    
    args = parser.parse_args()
    
    # 옵션이 하나도 제공되지 않은 경우 샘플 데이터를 기본으로 로드
    if not any([args.json, args.csv, args.sample]):
        print("🍽️  FOODI 식당 데이터 로더")
        print("=" * 50)
        print("옵션이 제공되지 않아 샘플 데이터를 로드합니다.")
        print("다른 옵션을 사용하려면 --help를 확인하세요.")
        print("=" * 50)
        
        # 자동으로 샘플 데이터 로드
        args.sample = True
    
    try:
        loader = RestaurantDataLoader()
        
        if args.sample:
            print("📝 샘플 데이터를 로드합니다...")
            loader.load_sample_data()
        elif args.json:
            print(f"📄 JSON 파일에서 데이터를 로드합니다: {args.json}")
            loader.load_from_json(args.json)
        elif args.csv:
            print(f"📊 CSV 파일에서 데이터를 로드합니다: {args.csv}")
            loader.load_from_csv(args.csv)
        
        loader.print_statistics()
        
        print("\n✅ 식당 데이터 로드가 완료되었습니다!")
        
    except Exception as e:
        logger.error(f"❌ 데이터 로드 실패: {e}")
        sys.exit(1)

if __name__ == '__main__':
		main()