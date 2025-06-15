FOODI API 문서
개요
FOODI API는 대구 달서구 지역의 맛집 추천 서비스를 위한 RESTful API입니다. 
이 문서는 API의 모든 엔드포인트와 사용법을 상세히 설명합니다.
기본 정보

Base URL: http://localhost:5000/api
API 버전: v1
인증: 현재 버전에서는 인증이 필요하지 않습니다.
데이터 형식: JSON
문자 인코딩: UTF-8

응답 형식
모든 API 응답은 다음과 같은 일관된 형식을 따릅니다:
json{
		"success": true|false,
		"data": { ... },
		"error": "오류 메시지 (오류 시에만)",
		"timestamp": "2024-01-01T12:00:00Z"
}
HTTP 상태 코드

200 OK: 요청 성공
201 Created: 리소스 생성 성공
400 Bad Request: 잘못된 요청
404 Not Found: 리소스를 찾을 수 없음
500 Internal Server Error: 서버 내부 오류


📱 채팅 API
POST /api/chat/message
사용자 메시지를 처리하고 AI 응답을 반환합니다.
요청 본문:
json{
		"message": "2만원 이하 고기집 추천해줘",
		"session_id": "chat_1234567890",
		"timestamp": "2024-01-01T12:00:00Z"
}
응답:
json{
		"success": true,
		"data": {
				"message": "좋은 고기집들을 찾아봤습니다!",
				"restaurants": [
						{
								"id": 1,
								"name": "대박삼겹살",
								"category": "고기",
								"rating": 4.3,
								"price_range": "15000-25000",
								"description": "신선한 국내산 삼겹살 전문점"
						}
				],
				"session_id": "chat_1234567890"
		}
}
GET /api/chat/examples
예제 질문 목록을 반환합니다.
응답:
json{
		"success": true,
		"data": {
				"examples": [
						{
								"text": "2만원 이하 고기집 추천해줘",
								"category": "budget"
						},
						{
								"text": "혼밥하기 좋은 곳 알려줘",
								"category": "purpose"
						}
				]
		}
}

🍽️ 식당 API
GET /api/restaurants
식당 목록을 조회합니다.
쿼리 파라미터:

category (string): 카테고리 필터
price_min (integer): 최소 가격
price_max (integer): 최대 가격
rating_min (float): 최소 평점
search (string): 검색 키워드
page (integer): 페이지 번호 (기본값: 1)
per_page (integer): 페이지당 항목 수 (기본값: 10)

예시 요청:
GET /api/restaurants?category=korean&price_max=20000&page=1&per_page=5
응답:
json{
		"success": true,
		"data": {
				"restaurants": [
						{
								"id": 1,
								"name": "할매국수",
								"category": "korean",
								"address": "대구 달서구 월배로 123",
								"latitude": 35.8562,
								"longitude": 128.5327,
								"rating": 4.5,
								"price_range": "5000-10000",
								"phone": "053-111-1111",
								"hours": "09:00-21:00",
								"description": "50년 전통의 손칼국수 전문점",
								"district": "월배동"
						}
				],
				"pagination": {
						"page": 1,
						"per_page": 5,
						"total": 25,
						"pages": 5
				}
		}
}
GET /api/restaurants/{id}
특정 식당의 상세 정보를 조회합니다.
응답:
json{
		"success": true,
		"data": {
				"restaurant": {
						"id": 1,
						"name": "할매국수",
						"category": "korean",
						"address": "대구 달서구 월배로 123",
						"latitude": 35.8562,
						"longitude": 128.5327,
						"rating": 4.5,
						"price_range": "5000-10000",
						"phone": "053-111-1111",
						"hours": "09:00-21:00",
						"description": "50년 전통의 손칼국수 전문점",
						"district": "월배동",
						"created_at": "2024-01-01T12:00:00Z",
						"updated_at": "2024-01-01T12:00:00Z"
				},
				"reviews": [
						{
								"id": 1,
								"rating": 5,
								"content": "정말 맛있어요!",
								"sentiment_score": 0.9,
								"sentiment_label": "positive",
								"created_at": "2024-01-01T12:00:00Z"
						}
				],
				"location": {
						"latitude": 35.8562,
						"longitude": 128.5327,
						"district": "월배동"
				}
		}
}
GET /api/restaurants/categories
사용 가능한 식당 카테고리 목록을 반환합니다.
응답:
json{
		"success": true,
		"data": {
				"categories": [
						{
								"id": "korean",
								"name": "한식",
								"icon": "🍚",
								"description": "한국 전통 음식"
						},
						{
								"id": "chinese",
								"name": "중식",
								"icon": "🥢",
								"description": "중국 음식"
						}
				]
		}
}
POST /api/restaurants/nearby
주변 식당을 검색합니다.
요청 본문:
json{
		"latitude": 35.8562,
		"longitude": 128.5327,
		"radius": 1000
}
응답:
json{
		"success": true,
		"data": {
				"restaurants": [
						{
								"id": 1,
								"name": "할매국수",
								"distance": 150.5
						}
				],
				"search_center": {
						"latitude": 35.8562,
						"longitude": 128.5327,
						"radius": 1000
				}
		}
}

⭐ 리뷰 API
POST /api/reviews
새 리뷰를 작성합니다.
요청 본문:
json{
		"restaurant_id": 1,
		"user_session": "user_123",
		"rating": 5,
		"content": "정말 맛있었어요! 직원들도 친절하고 분위기도 좋았습니다.",
		"purpose": "데이트"
}
응답:
json{
		"success": true,
		"data": {
				"review_id": 123,
				"message": "리뷰가 성공적으로 작성되었습니다.",
				"sentiment_analysis": {
						"score": 0.9,
						"label": "positive",
						"confidence": 0.95
				}
		}
}
GET /api/reviews/restaurant/{restaurant_id}
특정 식당의 리뷰 목록을 조회합니다.
쿼리 파라미터:

page (integer): 페이지 번호
per_page (integer): 페이지당 항목 수
sort_by (string): 정렬 기준 (created_at, rating)
order (string): 정렬 순서 (asc, desc)

응답:
json{
		"success": true,
		"data": {
				"reviews": [
						{
								"id": 1,
								"rating": 5,
								"content": "정말 맛있어요!",
								"sentiment_score": 0.9,
								"sentiment_label": "positive",
								"purpose": "데이트",
								"created_at": "2024-01-01T12:00:00Z"
						}
				],
				"statistics": {
						"total_reviews": 10,
						"average_rating": 4.5,
						"rating_distribution": {
								"5": 6,
								"4": 3,
								"3": 1,
								"2": 0,
								"1": 0
						}
				}
		}
}
PUT /api/reviews/{id}
기존 리뷰를 수정합니다.
요청 본문:
json{
		"rating": 4,
		"content": "수정된 리뷰 내용입니다."
}
DELETE /api/reviews/{id}
리뷰를 삭제합니다.
응답:
json{
		"success": true,
		"data": {
				"message": "리뷰가 성공적으로 삭제되었습니다."
		}
}

📊 추천 이력 API
GET /api/recommendations
사용자의 추천 이력을 조회합니다.
쿼리 파라미터:

session_id (string): 세션 ID
page (integer): 페이지 번호
per_page (integer): 페이지당 항목 수

응답:
json{
		"success": true,
		"data": {
				"recommendations": [
						{
								"id": 1,
								"session_id": "chat_123",
								"user_query": "2만원 이하 고기집 추천해줘",
								"recommended_restaurants": [
										{
												"id": 1,
												"name": "대박삼겹살",
												"reason": "가격대가 적절하고 평점이 높습니다."
										}
								],
								"user_feedback": 5,
								"created_at": "2024-01-01T12:00:00Z"
						}
				]
		}
}
POST /api/recommendations/feedback
추천에 대한 사용자 피드백을 저장합니다.
요청 본문:
json{
		"recommendation_id": 1,
		"feedback_score": 5,
		"feedback_comment": "추천이 정말 좋았어요!"
}

🔍 검색 API
GET /api/search
통합 검색을 수행합니다.
쿼리 파라미터:

q (string): 검색어
type (string): 검색 타입 (restaurants, reviews, all)
filters (object): 추가 필터

응답:
json{
		"success": true,
		"data": {
				"query": "삼겹살",
				"results": {
						"restaurants": [
								{
										"id": 1,
										"name": "대박삼겹살",
										"relevance_score": 0.95
								}
						],
						"total_count": 1
				}
		}
}

❌ 오류 처리
일반적인 오류 응답
json{
		"success": false,
		"error": "요청한 리소스를 찾을 수 없습니다.",
		"error_code": "RESOURCE_NOT_FOUND",
		"timestamp": "2024-01-01T12:00:00Z"
}
검증 오류 응답
json{
		"success": false,
		"error": "입력 데이터 검증 실패",
		"validation_errors": {
				"rating": ["평점은 1-5 사이의 값이어야 합니다."],
				"content": ["리뷰 내용은 필수입니다."]
		},
		"timestamp": "2024-01-01T12:00:00Z"
}

📝 사용 예시
JavaScript로 API 호출
javascript// 식당 목록 조회
async function getRestaurants() {
		const response = await fetch('/api/restaurants?category=korean&price_max=20000');
		const data = await response.json();
		
		if (data.success) {
				console.log('식당 목록:', data.data.restaurants);
		} else {
				console.error('오류:', data.error);
		}
}

// 리뷰 작성
async function createReview(restaurantId, rating, content) {
		const response = await fetch('/api/reviews', {
				method: 'POST',
				headers: {
						'Content-Type': 'application/json'
				},
				body: JSON.stringify({
						restaurant_id: restaurantId,
						rating: rating,
						content: content,
						user_session: 'user_123'
				})
		});
		
		const data = await response.json();
		
		if (data.success) {
				console.log('리뷰 작성 완료:', data.data.review_id);
		} else {
				console.error('리뷰 작성 실패:', data.error);
		}
}
Python으로 API 호출
pythonimport requests

# 채팅 메시지 전송
def send_chat_message(message, session_id):
		url = 'http://localhost:5000/api/chat/message'
		payload = {
				'message': message,
				'session_id': session_id,
				'timestamp': '2024-01-01T12:00:00Z'
		}
		
		response = requests.post(url, json=payload)
		data = response.json()
		
		if data['success']:
				return data['data']
		else:
				raise Exception(data['error'])

# 사용 예시
result = send_chat_message('파스타 맛집 추천해줘', 'chat_123')
print(f"AI 응답: {result['message']}")

🔧 개발자 도구
API 테스트
API를 테스트하기 위해 다음 도구들을 사용할 수 있습니다:

Postman: GUI 기반 API 테스트 도구
curl: 명령줄 기반 HTTP 클라이언트
Insomnia: 또 다른 GUI 기반 API 테스트 도구

curl 예시
bash# 식당 목록 조회
curl -X GET "http://localhost:5000/api/restaurants?category=korean" \
			-H "Content-Type: application/json"

# 리뷰 작성
curl -X POST "http://localhost:5000/api/reviews" \
			-H "Content-Type: application/json" \
			-d '{
				"restaurant_id": 1,
				"rating": 5,
				"content": "정말 맛있어요!",
				"user_session": "test_user"
			}'

📊 API 제한 사항
현재 제한 사항

인증이 구현되지 않아 모든 요청이 익명으로 처리됩니다.
요청 속도 제한이 없습니다.
파일 업로드 기능이 지원되지 않습니다.

향후 개선 계획

JWT 기반 인증 시스템 도입
API 키 기반 접근 제어
요청 속도 제한 (Rate Limiting)
이미지 업로드 지원
실시간 알림 기능