"""
FOODI OpenAI 서비스 (카카오 API 데이터 강화 버전)
GPT-3.5-turbo를 사용한 맛집 추천 서비스
카카오 API 데이터를 최대한 활용하여 GPT 프롬프트 생성
"""

import os
import json
import logging
import requests
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

class OpenAIService:
    """카카오 API 데이터를 강화 활용한 OpenAI 맛집 추천 서비스"""
    
    def __init__(self):
        """서비스 초기화"""
        # OpenAI 클라이언트 설정
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        
        # 키워드 분류 사전들
        self._init_keyword_dictionaries()
        
        # 맛집 데이터베이스 로드
        self.restaurant_database = self._load_restaurant_database()
        
        print(f"🤖 OpenAI 서비스 초기화 완료")
        print(f"   - 모델: {self.model}")
        print(f"   - 등록 맛집 수: {len(self.restaurant_database)}개")
        print(f"   - 키워드 카테고리: {len(self.categories)}개")
        print(f"   - 상황 분류: {len(self.situations)}개")
    
    def _init_keyword_dictionaries(self):
        """키워드 분류 사전 초기화"""
        self.categories = {
            '한식': [
                '한식', '한국', '한국음식', '한정식', '백반', '정식',
                '김치', '된장', '불고기', '갈비', '비빔밥', '냉면', '물냉면', '비빔냉면',
                '삼겹살', '목살', '항정살', '순두부', '김치찌개', '된장찌개', '부대찌개',
                '제육볶음', '돼지국밥', '순대국', '설렁탕', '곰탕', '갈비탕', '삼계탕',
                '떡볶이', '순대', '호떡', '붕어빵', '계란빵', '국밥', '찜닭', '닭갈비',
                '막창', '곱창', '대구탕', '찜갈비', '안동찜닭'
            ],
            '중식': [
                '중식', '중국', '중국음식', '중국집',
                '짜장면', '짬뽕', '탕수육', '볶음밥', '군만두', '물만두', '완자탕',
                '마라탕', '마라샹궈', '훠궈', '딤섬', '깐풍기', '양장피', '유산슬',
                '고추잡채', '울면', '쟁반짜장', '삼선짜장', '사천짜장', '해물짬뽕'
            ],
            '일식': [
                '일식', '일본', '일본음식', '이자카야', '스시', '사시미',
                '초밥', '회', '돈까스', '라멘', '우동', '소바', '튀김',
                '규동', '가츠동', '오야코동', '야키토리', '오코노미야키', '타코야키'
            ],
            '양식': [
                '양식', '서양', '서양음식', '이탈리안', '프렌치', '아메리칸',
                '스테이크', '파스타', '피자', '샐러드', '리조또', '햄버거', '치즈버거',
                '오믈렛', '팬케이크', '와플', '토스트', '샌드위치', '수프'
            ],
            '해산물': [
                '회', '해산물', '바다', '생선', '조개', '새우', '게', '랍스터', '전복',
                '광어', '연어', '참치', '우럭', '도미', '방어', '삼치', '고등어',
                '문어', '오징어', '쭈꾸미', '낙지', '해물탕', '매운탕', '지리'
            ],
            '치킨': [
                '치킨', '닭', '후라이드', '양념', '간장', '마늘', '허니', '불닭',
                '순살', '뼈', '윙', '다리', '닭강정', '닭발', '닭똥집'
            ],
            '카페': [
                '카페', '커피', '브런치', '디저트', '케이크', '빵', '베이커리',
                '아메리카노', '라떼', '카푸치노', '마키야또', '프라푸치노', '스무디'
            ],
            '분식': [
                '분식', '떡볶이', '순대', '튀김', '김밥', '라면', '우동', '어묵',
                '핫도그', '콘도그', '토스트', '계란빵', '호떡', '붕어빵'
            ]
        }
        
        self.situations = {
            '가족식사': ['가족', '부모', '어머니', '아버지', '엄마', '아빠', '아이', '아기'],
            '데이트': ['연인', '데이트', '남친', '여친', '남자친구', '여자친구', '애인', '기념일'],
            '친구모임': ['친구', '동료', '같이', '함께', '모임', '단체', '그룹'],
            '혼밥': ['혼자', '혼밥', '1인', '간단', '혼식'],
            '비즈니스': ['회식', '직장', '팀', '상사', '동료', '접대', '미팅']
        }
    
    def _load_restaurant_database(self):
        """맛집 데이터베이스 로드"""
        restaurants = [
            {
                "id": 1,
                "name": "한우마당",
                "category": "한식",
                "description": "고품질 한우와 다채로운 메뉴로 손님들을 매료시키는 곳",
                "rating": 4.2,
                "price_range": "중간",
                "location": "대구 중구",
                "specialties": ["한우갈비", "불고기", "된장찌개"],
                "atmosphere": "가족적인",
                "suitable_for": ["가족", "연인", "회식"]
            },
            {
                "id": 2,
                "name": "돈까스 천국",
                "category": "일식",
                "description": "바삭한 돈까스와 풍성한 사이드 메뉴가 인상적인 맛집",
                "rating": 4.5,
                "price_range": "저렴",
                "location": "대구 수성구",
                "specialties": ["등심돈까스", "치즈돈까스", "카레"],
                "atmosphere": "캐주얼",
                "suitable_for": ["친구", "혼밥", "가족"]
            }
        ]
        return restaurants
    
    def _extract_keywords_from_message(self, message):
        """사용자 메시지에서 키워드 추출"""
        print(f"🔍 키워드 추출 시작: '{message[:50]}...'")
        
        try:
            found_keywords = []
            detected_category = None
            detected_situation = None
            
            # 카테고리별 점수 계산
            category_scores = {}
            for category, keywords in self.categories.items():
                score = sum(1 for keyword in keywords if keyword in message)
                if score > 0:
                    category_scores[category] = score
                    found_keywords.extend([kw for kw in keywords if kw in message])
            
            # 가장 높은 점수의 카테고리 선택
            if category_scores:
                detected_category = max(category_scores, key=category_scores.get)
                print(f"   ✅ 최종 카테고리: {detected_category} ({category_scores[detected_category]}점)")
            
            # 상황 분석
            for situation, keywords in self.situations.items():
                situation_keywords = [kw for kw in keywords if kw in message]
                if situation_keywords:
                    detected_situation = situation
                    found_keywords.extend(situation_keywords)
                    print(f"   ✅ 감지된 상황: {situation}")
                    break
            
            return {
                'keywords': list(set(found_keywords))[:5],
                'category': detected_category,
                'situation': detected_situation,
                'category_scores': category_scores
            }
            
        except Exception as e:
            print(f"❌ 키워드 추출 오류: {e}")
            return {'keywords': [], 'category': None, 'situation': None}
    
    def _analyze_user_intent(self, user_message):
        """사용자 의도 종합 분석"""
        print(f"🧠 사용자 의도 종합 분석 시작")
        keyword_analysis = self._extract_keywords_from_message(user_message)
        
        analysis = {
            'category': keyword_analysis['category'],
            'situation': keyword_analysis['situation'],
            'keywords_found': keyword_analysis['keywords'],
            'original_message': user_message
        }
        
        print(f"   📊 종합 분석 결과:")
        print(f"      🍽️ 음식 카테고리: {analysis['category']}")
        print(f"      👥 식사 상황: {analysis['situation']}")
        print(f"      🔑 핵심 키워드: {analysis['keywords_found']}")
        
        return analysis
    
    def _get_kakao_restaurants(self, user_message):
        """카카오 API에서 맛집 정보 조회 (강화된 데이터 수집)"""
        print(f"🔍 카카오 API 맛집 검색 시작")
        
        try:
            KAKAO_API_KEY = os.getenv('KAKAO_API_KEY')
            if not KAKAO_API_KEY:
                print("❌ KAKAO_API_KEY 환경변수가 없습니다.")
                return None
            
            # 키워드 추출로 검색 쿼리 생성
            keyword_analysis = self._extract_keywords_from_message(user_message)
            extracted_keywords = keyword_analysis['keywords']
            detected_category = keyword_analysis['category']
            
            # 쿼리 생성
            base_query = "대구 달서구"
            if extracted_keywords:
                query = f"{base_query} {' '.join(extracted_keywords[:2])} 맛집"
            else:
                query = f"{base_query} 맛집"
            
            print(f"   🔎 최종 검색 쿼리: '{query}'")
            
            # API 호출
            headers = {
                "Authorization": f"KakaoAK {KAKAO_API_KEY}",
                "Content-Type": "application/json"
            }
            
            params = {
                "query": query,
                "category_group_code": "FD6",
                "size": "15",
                "sort": "accuracy"
            }
            
            response = requests.get(
                "https://dapi.kakao.com/v2/local/search/keyword.json", 
                headers=headers, 
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                kakao_data = response.json()
                restaurants_count = len(kakao_data.get('documents', []))
                print(f"   ✅ 검색 성공! 발견된 맛집: {restaurants_count}개")
                
                return {
                    'data': kakao_data,
                    'keywords': keyword_analysis,
                    'query_used': query
                }
            else:
                print(f"   ❌ API 오류 ({response.status_code})")
                return None
                
        except Exception as e:
            print(f"❌ 카카오 API 호출 실패: {e}")
            return None
    
    def _safe_get_value(self, data, key, default_value="정보 없음"):
        """안전한 값 추출 (undefined, null, 빈 값 처리)"""
        try:
            value = data.get(key, default_value)
            
            # None, undefined, null 처리
            if value is None or value == 'undefined' or value == 'null':
                return default_value
            
            # 빈 문자열 처리
            if isinstance(value, str):
                value = value.strip()
                if not value or value.lower() in ['', 'undefined', 'null', 'none']:
                    return default_value
            
            return value
            
        except Exception:
            return default_value
    
    def _format_category_name(self, category):
        """카테고리 이름 정리"""
        if not category or category == '정보 없음':
            return '음식점'
        
        # '>' 기준으로 분리하여 마지막 카테고리 반환
        category_parts = category.split(' > ')
        last_category = category_parts[-1].strip() if category_parts else '음식점'
        
        # 빈 값이면 기본값 반환
        return last_category if last_category else '음식점'
    
    def _format_phone_number(self, phone):
        """전화번호 포맷팅"""
        if not phone or phone in ['정보 없음', 'undefined', 'null', '']:
            return "전화번호 정보 없음"
        
        # 숫자만 추출
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # 전화번호 길이에 따른 포맷팅
        if len(clean_phone) >= 10:
            if clean_phone.startswith('02'):
                # 서울 지역번호 (02-xxxx-xxxx)
                return f"02-{clean_phone[2:6]}-{clean_phone[6:]}"
            elif len(clean_phone) == 10:
                # 지역번호 3자리 (0xx-xxx-xxxx)
                return f"{clean_phone[:3]}-{clean_phone[3:6]}-{clean_phone[6:]}"
            elif len(clean_phone) == 11:
                # 휴대폰 또는 지역번호 3자리 (0xx-xxxx-xxxx)
                return f"{clean_phone[:3]}-{clean_phone[3:7]}-{clean_phone[7:]}"
        elif len(clean_phone) >= 8:
            # 짧은 번호 (xxxx-xxxx)
            return f"{clean_phone[:4]}-{clean_phone[4:]}"
        
        # 포맷팅할 수 없는 경우 원본 반환
        return phone if phone else "전화번호 정보 없음"
    
    def _format_distance(self, distance):
        """거리 정보 포맷팅"""
        if not distance or distance in ['undefined', 'null', '']:
            return "거리 정보 없음"
        
        try:
            distance_m = int(float(distance))
            if distance_m < 1000:
                return f"{distance_m}m"
            else:
                return f"{distance_m/1000:.1f}km"
        except (ValueError, TypeError):
            return "거리 정보 없음"
    
    def _enrich_kakao_restaurant_data(self, restaurant):
        """카카오 맛집 데이터 풍부화 (undefined 처리 강화)"""
        try:
            # 안전한 기본 정보 추출
            name = self._safe_get_value(restaurant, 'place_name', '이름 없음')
            category = self._safe_get_value(restaurant, 'category_name', '')
            address = self._safe_get_value(restaurant, 'address_name', '')
            road_address = self._safe_get_value(restaurant, 'road_address_name', '')
            phone = self._safe_get_value(restaurant, 'phone', '')
            place_url = self._safe_get_value(restaurant, 'place_url', '')
            x = self._safe_get_value(restaurant, 'x', '')
            y = self._safe_get_value(restaurant, 'y', '')
            distance = self._safe_get_value(restaurant, 'distance', '')
            
            enriched = {
                'name': name,
                'category': category,
                'address': address,
                'road_address': road_address,
                'phone': phone,
                'place_url': place_url,
                'x': x,
                'y': y,
                'distance': distance,
                'source': 'kakao'
            }
            
            # 카테고리 정보 분석
            if category and category != '정보 없음':
                category_parts = [part.strip() for part in category.split(' > ') if part.strip()]
                enriched['main_category'] = category_parts[0] if category_parts else '음식점'
                enriched['sub_category'] = category_parts[1] if len(category_parts) > 1 else '정보 없음'
                enriched['detail_category'] = category_parts[-1] if category_parts else '음식점'
            else:
                enriched['main_category'] = '음식점'
                enriched['sub_category'] = '정보 없음'
                enriched['detail_category'] = '음식점'
            
            # 거리 정보 처리
            enriched['distance_text'] = self._format_distance(distance)
            
            # 주소 정보 처리 (도로명 주소 우선)
            if road_address and road_address != '정보 없음':
                enriched['display_address'] = road_address
            elif address and address != '정보 없음':
                enriched['display_address'] = address
            else:
                enriched['display_address'] = "주소 정보 없음"
            
            # 전화번호 포맷팅
            enriched['formatted_phone'] = self._format_phone_number(phone)
            
            # URL 처리
            if not place_url or place_url == '정보 없음':
                enriched['has_url'] = False
            else:
                enriched['has_url'] = True
            
            return enriched
            
        except Exception as e:
            print(f"   ⚠️ 개별 맛집 데이터 처리 오류: {e}")
            # 오류 발생 시에도 기본 구조 반환
            return {
                'name': '이름 없음',
                'category': '음식점',
                'display_address': '주소 정보 없음',
                'formatted_phone': '전화번호 정보 없음',
                'distance_text': '거리 정보 없음',
                'detail_category': '음식점',
                'has_url': False,
                'source': 'kakao'
            }
    
    def _filter_restaurants(self, analysis, kakao_data=None):
        """맛집 필터링 (카카오 데이터 우선 활용)"""
        print(f"🎯 맛집 필터링 시작")
        
        if kakao_data and kakao_data.get('documents'):
            print(f"   📊 카카오 데이터 기반 필터링")
            return self._filter_kakao_restaurants(analysis, kakao_data)
        else:
            print(f"   📊 기본 데이터베이스 기반 필터링")
            return self._filter_database_restaurants(analysis)
    
    def _filter_kakao_restaurants(self, analysis, kakao_data):
        """카카오 API 데이터 필터링 (풍부한 정보 보존)"""
        restaurants = kakao_data.get('documents', [])
        print(f"   📍 원본 데이터: {len(restaurants)}개")
        
        filtered = []
        
        for restaurant in restaurants:
            enriched_restaurant = self._enrich_kakao_restaurant_data(restaurant)
            if enriched_restaurant:
                # 카테고리 매칭 확인
                if self._matches_analysis(enriched_restaurant, analysis) or len(filtered) < 8:
                    filtered.append(enriched_restaurant)
        
        print(f"   ✅ 필터링 완료: {len(filtered)}개")
        return filtered[:10]  # 최대 10개까지
    
    def _filter_database_restaurants(self, analysis):
        """데이터베이스 기반 필터링"""
        filtered_restaurants = self.restaurant_database.copy()
        
        # 카테고리 필터링
        if analysis.get('category'):
            filtered_restaurants = [
                r for r in filtered_restaurants 
                if r['category'] == analysis['category']
            ]
        
        return filtered_restaurants
    
    def _matches_analysis(self, restaurant, analysis):
        """맛집이 분석 결과와 매칭되는지 확인"""
        category_name = restaurant.get('category', '').lower()
        detected_category = analysis.get('category')
        
        if not detected_category:
            return True
        
        category_mapping = {
            '한식': ['한식', '한정식', '국물', '찌개', '한국'],
            '중식': ['중국', '중식'],
            '일식': ['일식', '일본', '스시', '라멘'],
            '양식': ['양식', '이탈리안', '프렌치', '서양'],
            '치킨': ['치킨', '닭'],
            '카페': ['카페', '커피', '디저트', '베이커리'],
            '해산물': ['회', '해산물', '횟집'],
            '분식': ['분식']
        }
        
        keywords = category_mapping.get(detected_category, [])
        return any(keyword in category_name for keyword in keywords)
    
    def _create_enhanced_gpt_prompt(self, user_message, filtered_restaurants, analysis):
        """카카오 API 데이터를 최대한 활용한 GPT 프롬프트 생성"""
        print(f"📝 강화된 GPT 프롬프트 생성 시작")
        print(f"   📊 대상 맛집 수: {len(filtered_restaurants)}개")
        
        if not filtered_restaurants:
            prompt = f"""사용자가 '{user_message}'라고 요청했습니다. 
대구 달서구 지역의 맛집을 추천해주세요. 친근하고 도움이 되는 톤으로 답변해주세요."""
            print(f"   ⚠️ 맛집 정보 없음 - 기본 프롬프트 생성")
            return prompt
        
        # 카카오 데이터인지 확인
        is_kakao_data = filtered_restaurants[0].get('source') == 'kakao'
        
        if is_kakao_data:
            # 카카오 API 데이터 기반 상세 프롬프트
            restaurant_info = self._build_kakao_restaurant_info(filtered_restaurants)
            data_source_info = "실시간 카카오맵 데이터"
        else:
            # 데이터베이스 기반 프롬프트
            restaurant_info = self._build_database_restaurant_info(filtered_restaurants)
            data_source_info = "내부 맛집 데이터베이스"
        
        # 사용자 분석 정보
        analysis_info = self._build_analysis_info(analysis)
        
        # 최종 프롬프트 구성
        prompt = f"""당신은 대구 지역의 맛집 추천 전문가입니다.

**사용자 요청**: {user_message}

**사용자 선호도 분석**:
{analysis_info}

**추천 가능한 맛집 정보** (출처: {data_source_info}):
{restaurant_info}

**추천 요청사항**:
1. 사용자의 요청에 가장 적합한 맛집 3-5곳을 선별하여 추천해주세요
2. 각 맛집별로 추천 이유와 특징을 구체적으로 설명해주세요
3. 위치, 연락처, 특별한 장점 등 실용적인 정보를 포함해주세요
4. 사용자의 상황(가족식사, 데이트, 친구모임 등)에 맞는 조언을 해주세요
5. 친근하고 따뜻한 톤으로 작성해주세요
6. 한국어로 응답해주세요

맛있는 식사가 되도록 정성껏 추천해주세요! 🍽️"""

        print(f"   ✅ 강화된 프롬프트 생성 완료 (길이: {len(prompt)}자)")
        return prompt
    
    def _build_kakao_restaurant_info(self, restaurants):
        """카카오 API 데이터를 활용한 맛집 정보 구성 (undefined 처리 강화)"""
        restaurant_info = ""
        
        for i, restaurant in enumerate(restaurants[:8], 1):
            # 안전한 데이터 추출
            name = restaurant.get('name', '이름 없음')
            detail_category = restaurant.get('detail_category', '음식점')
            display_address = restaurant.get('display_address', '주소 정보 없음')
            formatted_phone = restaurant.get('formatted_phone', '전화번호 정보 없음')
            distance_text = restaurant.get('distance_text', '거리 정보 없음')
            place_url = restaurant.get('place_url', '')
            has_url = restaurant.get('has_url', False)
            main_category = restaurant.get('main_category', '음식점')
            
            # 맛집 정보 구성
            restaurant_info += f"{i}. **{name}**\n"
            restaurant_info += f"   📍 위치: {display_address}\n"
            restaurant_info += f"   🍽️ 카테고리: {detail_category}\n"
            restaurant_info += f"   📞 연락처: {formatted_phone}\n"
            restaurant_info += f"   📏 거리: {distance_text}\n"
            
            # 카카오맵 URL이 있는 경우에만 추가
            if has_url and place_url and place_url != '정보 없음':
                restaurant_info += f"   🔗 카카오맵: {place_url}\n"
            
            # 메인 카테고리 정보 (유의미한 경우에만)
            if main_category and main_category != '음식점' and main_category != detail_category:
                restaurant_info += f"   🏷️ 주카테고리: {main_category}\n"
            
            restaurant_info += "\n"
        
        return restaurant_info
    
    def _build_database_restaurant_info(self, restaurants):
        """데이터베이스 기반 맛집 정보 구성 (undefined 처리 강화)"""
        restaurant_info = ""
        
        for i, restaurant in enumerate(restaurants[:5], 1):
            # 안전한 값 추출
            name = restaurant.get('name', '이름 없음')
            description = restaurant.get('description', '맛있는 음식을 제공하는 곳')
            rating = restaurant.get('rating', 4.0)
            location = restaurant.get('location', '대구')
            price_range = restaurant.get('price_range', '보통')
            specialties = restaurant.get('specialties', [])
            
            # undefined, null 값 처리
            if not name or name in ['undefined', 'null']:
                name = '이름 없음'
            if not description or description in ['undefined', 'null']:
                description = '맛있는 음식을 제공하는 곳'
            if not location or location in ['undefined', 'null']:
                location = '대구'
            if not price_range or price_range in ['undefined', 'null']:
                price_range = '보통'
            
            # 평점 검증
            try:
                rating = float(rating) if rating and rating != 'undefined' else 4.0
                rating = max(0, min(5, rating))  # 0-5 사이 값으로 제한
            except (ValueError, TypeError):
                rating = 4.0
            
            restaurant_info += f"{i}. **{name}**\n"
            restaurant_info += f"   📍 위치: {location}\n"
            restaurant_info += f"   📝 설명: {description}\n"
            restaurant_info += f"   ⭐ 평점: {rating}점\n"
            restaurant_info += f"   💰 가격대: {price_range}\n"
            
            # 대표메뉴가 있는 경우에만 추가
            if specialties and isinstance(specialties, list) and len(specialties) > 0:
                # 빈 값이나 undefined 제거
                valid_specialties = [s for s in specialties 
                                   if s and s not in ['undefined', 'null', '']]
                if valid_specialties:
                    restaurant_info += f"   🍽️ 대표메뉴: {', '.join(valid_specialties)}\n"
            
            restaurant_info += "\n"
        
        return restaurant_info
    
    def _build_analysis_info(self, analysis):
        """사용자 분석 정보 구성 (undefined 처리 강화)"""
        analysis_info = ""
        
        # 안전한 값 추출 및 검증
        category = analysis.get('category')
        situation = analysis.get('situation') 
        keywords_found = analysis.get('keywords_found', [])
        
        if category and category not in ['undefined', 'null', '', None]:
            analysis_info += f"- 🍽️ 원하는 음식 종류: {category}\n"
            
        if situation and situation not in ['undefined', 'null', '', None]:
            analysis_info += f"- 👥 식사 상황: {situation}\n"
            
        if keywords_found and isinstance(keywords_found, list) and len(keywords_found) > 0:
            # 빈 값이나 undefined 제거
            valid_keywords = [kw for kw in keywords_found 
                            if kw and kw not in ['undefined', 'null', '', None]]
            if valid_keywords:
                analysis_info += f"- 🔑 핵심 키워드: {', '.join(valid_keywords)}\n"
        
        # 분석 정보가 없는 경우 기본 메시지
        if not analysis_info.strip():
            analysis_info = "- 일반적인 맛집 추천 요청\n"
        
        return analysis_info
    
    def _call_openai_api(self, prompt):
        """OpenAI API 호출"""
        print(f"\n🤖 OpenAI GPT API 호출 시작")
        print(f"   🎯 모델: {self.model}")
        
        try:
            api_start_time = datetime.now()
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "당신은 대구 지역의 친근한 맛집 추천 전문가입니다. 실제 맛집 데이터를 바탕으로 사용자에게 도움이 되는 구체적이고 실용적인 추천을 해주세요."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.7,
                top_p=1.0,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )
            
            api_duration = (datetime.now() - api_start_time).total_seconds()
            gpt_response = response.choices[0].message.content
            
            token_usage = {
                'prompt': response.usage.prompt_tokens,
                'completion': response.usage.completion_tokens,
                'total': response.usage.total_tokens
            }
            
            print(f"   ✅ API 호출 완료 ({api_duration:.2f}초)")
            print(f"   🎫 토큰 사용량: {token_usage['total']} tokens")
            print(f"   📏 응답 길이: {len(gpt_response)}자")
            
            return {
                'response': gpt_response,
                'token_usage': token_usage,
                'api_duration': api_duration,
                'success': True
            }
            
        except Exception as e:
            print(f"❌ OpenAI API 호출 실패: {str(e)}")
            return {
                'error': str(e),
                'success': False
            }
    
    def get_restaurant_recommendation(self, user_message):
        """메인 추천 함수 (카카오 API 데이터 강화 버전)"""
        print(f"\n🍽️" + "="*80)
        print(f"🍽️ FOODI 맛집 추천 서비스 시작 (카카오 API 강화)")
        print(f"🍽️" + "="*80)
        print(f"📝 사용자 요청: '{user_message}'")
        
        start_time = datetime.now()
        
        try:
            # 1. 사용자 의도 분석
            print(f"\n📊 1단계: 사용자 의도 분석")
            analysis = self._analyze_user_intent(user_message)
            
            # 2. 카카오 API에서 맛집 검색
            print(f"\n🔍 2단계: 카카오 API 맛집 데이터 수집")
            kakao_result = self._get_kakao_restaurants(user_message)
            
            # 3. 맛집 필터링
            print(f"\n🎯 3단계: 맛집 필터링 및 데이터 정제")
            if kakao_result and kakao_result['data']:
                filtered_restaurants = self._filter_restaurants(analysis, kakao_result['data'])
                kakao_available = True
                print(f"   ✅ 카카오 API 데이터 활용: {len(filtered_restaurants)}개 맛집")
            else:
                print(f"   ℹ️ 카카오 API 데이터 없음 - 내부 데이터베이스 사용")
                filtered_restaurants = self._filter_restaurants(analysis)
                kakao_available = False
            
            # 4. 강화된 GPT 프롬프트 생성
            print(f"\n📝 4단계: 강화된 AI 추천 프롬프트 생성")
            prompt = self._create_enhanced_gpt_prompt(user_message, filtered_restaurants, analysis)
            
            # 5. OpenAI API 호출
            print(f"\n🤖 5단계: AI 맛집 추천 생성")
            gpt_result = self._call_openai_api(prompt)
            
            # 6. 최종 결과 처리
            print(f"\n📋 6단계: 최종 결과 처리")
            total_time = (datetime.now() - start_time).total_seconds()
            
            if gpt_result.get('success'):
                result = {
                    'success': True,
                    'response': gpt_result['response'],
                    'restaurants': filtered_restaurants[:5],
                    'analysis': analysis,
                    'token_usage': gpt_result['token_usage'],
                    'processing_time': total_time,
                    'api_duration': gpt_result['api_duration'],
                    'kakao_available': kakao_available,
                    'restaurant_count': len(filtered_restaurants),
                    'data_source': 'kakao_api' if kakao_available else 'database'
                }
                
                print(f"✅ 강화된 추천 처리 완료!")
                print(f"   ⏱️ 총 처리 시간: {total_time:.2f}초")
                print(f"   🏪 추천 맛집 수: {len(filtered_restaurants)}개")
                print(f"   🌐 데이터 소스: {'카카오 API' if kakao_available else '내부 DB'}")
                print(f"   🎫 사용 토큰: {gpt_result['token_usage']['total']}")
                
            else:
                # GPT API 오류 시 폴백 응답
                print(f"   ⚠️ AI 추천 실패 - 기본 추천 생성")
                fallback_response = self._generate_fallback_response(filtered_restaurants)
                
                result = {
                    'success': True,
                    'response': fallback_response,
                    'restaurants': filtered_restaurants[:3],
                    'analysis': analysis,
                    'fallback': True,
                    'error': gpt_result.get('error'),
                    'processing_time': total_time,
                    'kakao_available': kakao_available,
                    'restaurant_count': len(filtered_restaurants)
                }
            
            print(f"🍽️" + "="*80 + "\n")
            return result
        
        except Exception as e:
            total_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"추천 처리 중 오류 발생: {str(e)}"
            
            print(f"❌ 시스템 오류 발생: {error_msg}")
            
            result = {
                'success': False,
                'error': error_msg,
                'restaurants': [],
                'analysis': {},
                'processing_time': total_time
            }
            
            return result
    
    def _generate_fallback_response(self, restaurants):
        """API 오류 시 기본 응답 생성 (undefined 처리 강화)"""
        if not restaurants:
            return "죄송합니다. 현재 조건에 맞는 맛집을 찾을 수 없습니다. 다른 조건으로 검색해보시겠어요?"
        
        restaurant = restaurants[0]
        
        if restaurant.get('source') == 'kakao':
            # 카카오 데이터 기반 - 안전한 값 추출
            name = restaurant.get('name', '맛집')
            display_address = restaurant.get('display_address', '대구 달서구')
            detail_category = restaurant.get('detail_category', '음식점')
            formatted_phone = restaurant.get('formatted_phone', '전화번호 정보 없음')
            distance_text = restaurant.get('distance_text', '거리 정보 없음')
            
            response = f"""안녕하세요! **{name}**을(를) 추천해드립니다.

📍 위치: {display_address}
🍽️ 종류: {detail_category}
📞 연락처: {formatted_phone}"""
            
            # 거리 정보가 있는 경우에만 추가
            if distance_text != '거리 정보 없음':
                response += f"\n📏 거리: {distance_text}"
            
            # 카카오맵 링크가 있는 경우에만 추가
            if restaurant.get('has_url') and restaurant.get('place_url'):
                response += f"\n🔗 카카오맵: {restaurant['place_url']}"
            
            response += "\n\n좋은 식사 되세요! 🍽️"
            
        else:
            # 데이터베이스 기반 - 안전한 값 추출
            name = restaurant.get('name', '맛집')
            description = restaurant.get('description', '맛있는 음식을 제공하는 곳입니다.')
            location = restaurant.get('location', '대구')
            rating = restaurant.get('rating', 4.0)
            price_range = restaurant.get('price_range', '보통')
            
            response = f"""안녕하세요! **{name}**을(를) 추천해드립니다.

{description}

📍 위치: {location}
⭐ 평점: {rating}점"""
            
            # 가격대 정보가 유의미한 경우에만 추가
            if price_range and price_range != '정보 없음':
                response += f"\n💰 가격대: {price_range}"
            
            response += "\n\n좋은 식사 되세요! 🍽️"
        
        return response

# 테스트용 코드
if __name__ == "__main__":
    try:
        service = OpenAIService()
        
        test_messages = [
            "가족과 함께 갈 수 있는 한식당 추천해줘",
            "친구들과 저렴하게 먹을 수 있는 곳이 어디 있나요?",
            "연인과 데이트하기 좋은 분위기 좋은 레스토랑 알려주세요"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n🧪 테스트 {i}/{len(test_messages)}")
            result = service.get_restaurant_recommendation(message)
            
            if result['success']:
                print(f"✅ 테스트 성공!")
                print(f"📊 데이터 소스: {result.get('data_source', 'unknown')}")
            else:
                print(f"❌ 테스트 실패: {result.get('error', '알 수 없는 오류')}")
                
    except Exception as e:
        print(f"❌ 테스트 실행 오류: {str(e)}")