■ 프로젝트 소개 및 주요 기능 설명
■ 설치 방법 및 환경 설정 가이드
■ 사용법과 예제
■ 아키텍처 및 기술 스택 설명

# FOODI - 대구 달서구 맛집 추천 AI 챗봇

FOODI는 OpenAI GPT를 활용하여 대구 달서구 일대의 맛집을 개인 맞춤형으로 추천해주는 인공지능 챗봇 서비스입니다. 
사용자의 예산, 메뉴 선호도, 인원수 등을 고려하여 최적의 식당을 추천하고, 지도와 함께 상세 정보를 제공합니다.

## 주요 기능

### AI 기반 맞춤 추천
- OpenAI GPT를 활용한 자연어 처리로 사용자 의도 파악
- 예산, 메뉴, 분위기, 인원수 등 다양한 조건 고려
- 개인화된 추천 결과 제공

### 자연스러운 대화형 인터페이스
- 실시간 채팅 방식의 직관적인 UI
- 질문 예제 자동 제공으로 쉬운 사용법
- 대화 맥락을 유지하는 세션 메모리

### 지도 연동 위치 서비스
- NAVER 지역 검색 API, Kakao 로컬 API를 통한 식당 위치 시각화
- 실시간 운영시간 및 연락처 정보 제공
- 경로 안내 연동

### 리뷰 및 평점 시스템
- 사용자 리뷰 작성 및 관리
- AI 기반 감정 분석으로 자동 평점 조정
- 실시간 추천 알고리즘 업데이트

### 추천 이력 관리
- 개인별 추천 기록 저장 및 조회
- 선호도 학습을 통한 추천 정확도 향상
- 즐겨찾기 및 재방문 의사 추적

## 빠른 시작

### 사전 요구사항
- Python 3.8 이상
- OpenAI API 키
- Kakao 로컬 API 키(1. https://developers.kakao.com 에서 로그인 후 2. 내 애플리케이션 에서 애플리케이션 추가후 만든 애플리케이션에 진입(카테고리는 여행/지역정보)
 3. 허용 IP 주소에 현재 연결중인 IP주소 입력 4.앱설정부분의 앱키 진입 후 REST API 키 부분을 복사 5. .env 파일에서서 KAKAO_API_KEY 부분을 복사한 키로 수정)

### 설치 방법

1. **가상환경 생성 및 활성화**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. **패키지 설치**
```bash
pip install -r requirements.txt
```

3. **애플리케이션 실행**
```bash
python3 src/app.py
```

웹 브라우저에서 `http://localhost:5000` 접속

## 환경 설정

`.env` 파일에 다음 값들을 설정해주세요(현재 채워져 있음):

```bash
# OpenAI 설정
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo

# 데이터베이스 설정
DATABASE_URL=sqlite:///data/database/foodi.db

# Flask 설정
FLASK_ENV=development
SECRET_KEY=your_secret_key_here

# 서비스 설정
DEFAULT_LOCATION=대구 달서구
MAX_RECOMMENDATIONS=5
CACHE_TIMEOUT=3600
```

## 사용법

### 1. 맛집 추천받기
```
사용자: "2만원 이하로 고기 먹을 수 있는 곳 알려줘"
FOODI: "예산과 메뉴를 고려해서 추천드리겠습니다!
				
				1. 대구 본점 돼지갈비 - ⭐4.5
						📍 달서구 성당로 123
						💰 1인당 15,000원
						⏰ 11:00-22:00
				
				2. 황소곱창 - ⭐4.3
						📍 달서구 월성로 456
						💰 1인당 18,000원
						⏰ 17:00-24:00"
```

### 2. 리뷰 작성하기
추천받은 식당 방문 후 간단한 리뷰를 작성하면 AI가 감정을 분석하여 평점에 반영합니다.


## 아키텍처

### 주요 컴포넌트
- **ChatManager**: 사용자와의 대화 흐름 관리
- **RecommendationEngine**: AI 기반 맛집 추천 로직
- **ReviewManager**: 리뷰 수집 및 감정 분석
- **DatabaseManager**: 데이터 저장 및 관리
- **MapRenderer**: 지도 시각화 및 위치 서비스

### 기술 스택
- **Backend**: Flask, SQLite, OpenAI API
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap
- **Maps**: Naver Maps JavaScript API
- **AI**: OpenAI GPT-3.5/4, 자연어 처리
- **Database**: SQLite


## 데이터베이스 스키마

### 주요 테이블
- **users**: 사용자 정보 및 세션 데이터
- **restaurants**: 식당 기본 정보 (이름, 주소, 카테고리 등)
- **reviews**: 사용자 리뷰 및 평점
- **recommendations**: 추천 이력 및 결과
- **sessions**: 채팅 세션 관리

자세한 스키마는 `docs/database_schema.md`를 참조하세요.

## 배포

### Docker를 이용한 배포
```bash
docker build -t foodi-chatbot .
docker run -p 5000:5000 --env-file .env foodi-chatbot
```