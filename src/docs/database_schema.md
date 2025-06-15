FOODI 데이터베이스 스키마 문서
개요
FOODI 프로젝트는 SQLite 데이터베이스를 사용하여 맛집 정보, 리뷰, 추천 이력 등을 관리합니다. 
이 문서는 데이터베이스의 구조와 각 테이블의 상세 정보를 설명합니다.
데이터베이스 정보

DB 엔진: SQLite 3
파일 위치: data/database/foodi.db
문자 인코딩: UTF-8
외래 키 제약: 활성화됨


📊 테이블 구조
1. restaurants (식당 정보)
메인 식당 정보를 저장하는 테이블입니다.
sqlCREATE TABLE restaurants (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		name TEXT NOT NULL,
		category TEXT NOT NULL,
		address TEXT,
		latitude REAL,
		longitude REAL,
		rating REAL DEFAULT 0.0,
		price_range TEXT,
		phone TEXT,
		hours TEXT,
		description TEXT,
		image_url TEXT,
		district TEXT,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
필드 설명:

id: 식당 고유 ID (Primary Key)
name: 식당명 (필수)
category: 음식 카테고리 (korean, chinese, japanese, western, meat, snack, cafe, etc.)
address: 주소
latitude, longitude: 위도, 경도 (지도 표시용)
rating: 평균 평점 (0.0 ~ 5.0)
price_range: 가격대 (예: "10000-20000")
phone: 전화번호
hours: 영업시간
description: 식당 설명
image_url: 대표 이미지 URL
district: 행정구역 (예: "월배동", "성서동")
created_at, updated_at: 생성일, 수정일

인덱스:
sqlCREATE INDEX idx_restaurants_category ON restaurants(category);
CREATE INDEX idx_restaurants_rating ON restaurants(rating DESC);
CREATE INDEX idx_restaurants_location ON restaurants(latitude, longitude);
CREATE INDEX idx_restaurants_district ON restaurants(district);
2. reviews (리뷰 정보)
사용자 리뷰를 저장하는 테이블입니다.
sqlCREATE TABLE reviews (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		restaurant_id INTEGER NOT NULL,
		user_session TEXT,
		rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
		content TEXT NOT NULL,
		sentiment_score REAL,
		sentiment_label TEXT,
		purpose TEXT,
		is_verified BOOLEAN DEFAULT FALSE,
		is_spam BOOLEAN DEFAULT FALSE,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		FOREIGN KEY (restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE
);
필드 설명:

id: 리뷰 고유 ID (Primary Key)
restaurant_id: 식당 ID (Foreign Key → restaurants.id)
user_session: 사용자 세션 ID (익명 사용자 구분용)
rating: 평점 (1-5, 필수)
content: 리뷰 내용 (필수)
sentiment_score: AI 감정 분석 점수 (-1.0 ~ 1.0)
sentiment_label: 감정 레이블 (positive, negative, neutral)
purpose: 방문 목적 (혼밥, 데이트, 가족식사, 회식 등)
is_verified: 검증된 리뷰 여부
is_spam: 스팸 리뷰 여부
created_at, updated_at: 생성일, 수정일

인덱스:
sqlCREATE INDEX idx_reviews_restaurant_id ON reviews(restaurant_id);
CREATE INDEX idx_reviews_created_at ON reviews(created_at DESC);
CREATE INDEX idx_reviews_rating ON reviews(rating);
3. recommendations (추천 이력)
AI 추천 이력을 저장하는 테이블입니다.
sqlCREATE TABLE recommendations (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		session_id TEXT NOT NULL,
		user_query TEXT NOT NULL,
		recommended_restaurants TEXT,  -- JSON 형태로 저장
		user_feedback INTEGER,         -- 1-5 점수
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
필드 설명:

id: 추천 고유 ID (Primary Key)
session_id: 채팅 세션 ID
user_query: 사용자 질문/요청
recommended_restaurants: 추천된 식당 정보 (JSON 배열)
user_feedback: 사용자 피드백 점수 (1-5)
created_at: 추천 생성일

JSON 형태 예시:
json[
		{
				"id": 1,
				"name": "할매국수",
				"reason": "전통적인 맛과 저렴한 가격",
				"score": 0.95
		}
]
인덱스:
sqlCREATE INDEX idx_recommendations_session_id ON recommendations(session_id);
CREATE INDEX idx_recommendations_created_at ON recommendations(created_at DESC);
4. chat_sessions (채팅 세션)
사용자 채팅 세션 정보를 저장하는 테이블입니다.
sqlCREATE TABLE chat_sessions (
		id TEXT PRIMARY KEY,
		user_id TEXT,
		message_history TEXT,  -- JSON 형태로 저장
		last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
필드 설명:

id: 세션 ID (Primary Key)
user_id: 사용자 ID (현재는 익명)
message_history: 메시지 히스토리 (JSON 배열)
last_activity: 마지막 활동 시간
created_at: 세션 생성일

메시지 히스토리 JSON 예시:
json[
		{
				"role": "user",
				"content": "파스타 맛집 추천해줘",
				"timestamp": "2024-01-01T12:00:00Z"
		},
		{
				"role": "assistant",
				"content": "좋은 파스타 맛집을 찾아봤습니다!",
				"timestamp": "2024-01-01T12:00:05Z"
		}
]
인덱스:
sqlCREATE INDEX idx_chat_sessions_last_activity ON chat_sessions(last_activity DESC);
5. restaurant_categories (식당 카테고리)
식당 카테고리 정보를 저장하는 테이블입니다.
sqlCREATE TABLE restaurant_categories (
		id TEXT PRIMARY KEY,
		name TEXT NOT NULL,
		icon TEXT,
		description TEXT,
		sort_order INTEGER DEFAULT 0
);
필드 설명:

id: 카테고리 ID (Primary Key, 예: "korean", "chinese")
name: 카테고리 표시명 (예: "한식", "중식")
icon: 아이콘 (이모지 또는 아이콘 클래스)
description: 카테고리 설명
sort_order: 정렬 순서

기본 카테고리 데이터:
sqlINSERT INTO restaurant_categories VALUES
('korean', '한식', '🍚', '한국 전통 음식', 1),
('chinese', '중식', '🥢', '중국 음식', 2),
('japanese', '일식', '🍣', '일본 음식', 3),
('western', '양식', '🍝', '서양 음식', 4),
('meat', '고기', '🥩', '고기 전문점', 5),
('snack', '분식', '🍢', '분식 및 간식', 6),
('cafe', '카페', '☕', '카페 및 디저트', 7),
('etc', '기타', '🍽️', '기타 음식점', 10);

🔧 트리거 (Triggers)
1. 자동 타임스탬프 업데이트
sql-- restaurants 테이블 updated_at 자동 업데이트
CREATE TRIGGER update_restaurants_timestamp 
AFTER UPDATE ON restaurants
BEGIN
		UPDATE restaurants SET updated_at = CURRENT_TIMESTAMP 
		WHERE id = NEW.id;
END;

-- reviews 테이블 updated_at 자동 업데이트
CREATE TRIGGER update_reviews_timestamp 
AFTER UPDATE ON reviews
BEGIN
		UPDATE reviews SET updated_at = CURRENT_TIMESTAMP 
		WHERE id = NEW.id;
END;
2. 식당 평점 자동 계산
sql-- 리뷰 추가 시 식당 평점 자동 업데이트
CREATE TRIGGER update_restaurant_rating_on_review_insert
AFTER INSERT ON reviews
BEGIN
		UPDATE restaurants 
		SET rating = (
				SELECT AVG(CAST(rating AS REAL)) 
				FROM reviews 
				WHERE restaurant_id = NEW.restaurant_id 
				AND is_spam = FALSE
		)
		WHERE id = NEW.restaurant_id;
END;

-- 리뷰 수정 시 식당 평점 자동 업데이트
CREATE TRIGGER update_restaurant_rating_on_review_update
AFTER UPDATE ON reviews
BEGIN
		UPDATE restaurants 
		SET rating = (
				SELECT AVG(CAST(rating AS REAL)) 
				FROM reviews 
				WHERE restaurant_id = NEW.restaurant_id 
				AND is_spam = FALSE
		)
		WHERE id = NEW.restaurant_id;
END;

📊 뷰 (Views)
1. 식당 통계 뷰
sqlCREATE VIEW restaurant_stats AS
SELECT 
		r.id,
		r.name,
		r.category,
		r.rating,
		COUNT(rv.id) as review_count,
		AVG(CAST(rv.rating AS REAL)) as calculated_rating,
		COUNT(CASE WHEN rv.rating >= 4 THEN 1 END) as positive_reviews,
		COUNT(CASE WHEN rv.rating <= 2 THEN 1 END) as negative_reviews
FROM restaurants r
LEFT JOIN reviews rv ON r.id = rv.restaurant_id AND rv.is_spam = FALSE
GROUP BY r.id, r.name, r.category, r.rating;
2. 인기 식당 뷰
sqlCREATE VIEW popular_restaurants AS
SELECT 
		r.*,
		COUNT(rv.id) as review_count,
		AVG(CAST(rv.rating AS REAL)) as avg_rating
FROM restaurants r
LEFT JOIN reviews rv ON r.id = rv.restaurant_id AND rv.is_spam = FALSE
GROUP BY r.id
HAVING review_count >= 3 AND avg_rating >= 4.0
ORDER BY review_count DESC, avg_rating DESC;

🔍 자주 사용되는 쿼리
1. 카테고리별 식당 조회
sqlSELECT * FROM restaurants 
WHERE category = 'korean' 
ORDER BY rating DESC, name;
2. 가격대별 식당 검색
sqlSELECT * FROM restaurants 
WHERE price_range LIKE '%10000%' OR price_range LIKE '%15000%'
ORDER BY rating DESC;
3. 주변 식당 검색 (간단 버전)
sqlSELECT *, 
		ABS(latitude - 35.8562) + ABS(longitude - 128.5327) as distance
FROM restaurants 
WHERE distance < 0.01  -- 대략 1km 내외
ORDER BY distance;
4. 평점 높은 식당 TOP 10
sqlSELECT name, category, rating, 
		(SELECT COUNT(*) FROM reviews WHERE restaurant_id = restaurants.id) as review_count
FROM restaurants 
WHERE rating >= 4.0
ORDER BY rating DESC, review_count DESC
LIMIT 10;
5. 최근 리뷰가 있는 식당
sqlSELECT DISTINCT r.*, rv.created_at as last_review_date
FROM restaurants r
JOIN reviews rv ON r.id = rv.restaurant_id
WHERE rv.created_at >= datetime('now', '-30 days')
ORDER BY rv.created_at DESC;
6. 감정 분석 통계
sqlSELECT 
		sentiment_label,
		COUNT(*) as count,
		AVG(rating) as avg_rating,
		AVG(sentiment_score) as avg_sentiment_score
FROM reviews 
WHERE sentiment_label IS NOT NULL
GROUP BY sentiment_label;

🔧 데이터 무결성 제약
1. CHECK 제약

reviews.rating: 1 이상 5 이하의 정수
restaurants.rating: 0.0 이상 5.0 이하의 실수

2. 외래 키 제약

reviews.restaurant_id → restaurants.id (CASCADE DELETE)

3. NOT NULL 제약

restaurants.name: 식당명은 필수
restaurants.category: 카테고리는 필수
reviews.restaurant_id: 식당 ID는 필수
reviews.rating: 평점은 필수
reviews.content: 리뷰 내용은 필수


🚀 성능 최적화
1. 인덱스 활용

검색이 자주 일어나는 컬럼에 인덱스 생성
복합 인덱스로 다중 조건 검색 최적화

2. 쿼리 최적화

EXPLAIN QUERY PLAN을 통한 쿼리 실행 계획 분석
불필요한 JOIN 최소화
적절한 LIMIT 사용

3. 데이터 정리

오래된 세션 데이터 정기적 삭제
스팸 리뷰 정기적 정리
인덱스 리빌드 (REINDEX)


📋 백업 및 복원
백업 명령
bash# 전체 데이터베이스 백업
python scripts/backup_database.py backup

# 스키마만 백업
python scripts/backup_database.py backup --schema-only

# 압축 백업
python scripts/backup_database.py backup --compress
복원 명령
bash# 백업에서 복원
python scripts/backup_database.py restore --file backup_file.db

# 확인 없이 복원
python scripts/backup_database.py restore --file backup_file.db --yes

🔄 마이그레이션
스키마 변경 시 고려사항

기존 데이터 호환성 확인
인덱스 재생성 필요성 검토
트리거 및 뷰 업데이트
백업 후 변경 작업 수행

예시: 새 컬럼 추가
sql-- 1. 새 컬럼 추가
ALTER TABLE restaurants ADD COLUMN menu_info TEXT;

-- 2. 기본값 설정
UPDATE restaurants SET menu_info = '{}' WHERE menu_info IS NULL;

-- 3. 필요시 인덱스 추가
CREATE INDEX idx_restaurants_menu ON restaurants(menu_info);