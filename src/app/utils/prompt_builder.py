# -*- coding: utf-8 -*-
"""
프롬프트 빌더 유틸리티 (PromptBuilder)
OpenAI API를 위한 프롬프트 생성 및 전처리를 담당하는 도구입니다.
"""

import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

class PromptBuilder:
		"""
		맛집 추천을 위한 AI 프롬프트를 구성하고 최적화하는 클래스
		다양한 상황과 목적에 맞는 프롬프트 템플릿을 제공합니다.
		"""
		
		def __init__(self):
				"""
				프롬프트 빌더 초기화
				기본 템플릿과 설정을 로드합니다.
				"""
				# 기본 시스템 프롬프트
				self.base_system_prompt = """
당신은 대구 달서구 지역의 맛집 전문가 'FOODI'입니다.
다음과 같은 특성을 가지고 있습니다:

1. 친근하고 따뜻한 말투로 대화합니다
2. 대구 달서구 지역의 맛집에 대해 해박한 지식을 가지고 있습니다
3. 사용자의 취향과 상황을 세심하게 고려합니다
4. 구체적이고 실용적인 정보를 제공합니다
5. 이모지를 적절히 사용하여 친밀감을 표현합니다
6. 항상 도움이 되고 긍정적인 태도를 유지합니다

응답할 때는 다음을 포함해야 합니다:
- 식당 이름과 위치
- 추천 이유
- 가격대 정보
- 영업시간
- 특별한 특징이나 메뉴
- 개인적인 의견이나 팁
"""
				
				# 프롬프트 템플릿들
				self.templates = {
						"recommendation": self._load_recommendation_template(),
						"analysis": self._load_analysis_template(),
						"response": self._load_response_template(),
						"feedback": self._load_feedback_template()
				}
				
				# 컨텍스트 키워드
				self.context_keywords = {
						"urgency": ["급해", "빨리", "지금", "당장", "서둘러"],
						"special_occasion": ["데이트", "기념일", "생일", "회식", "모임"],
						"budget_concern": ["저렴", "싸", "가성비", "비싸", "돈"],
						"dietary": ["채식", "비건", "할랄", "글루텐프리", "알레르기"],
						"group_size": ["혼자", "둘이", "가족", "친구", "단체"]
				}
		
		def build_recommendation_prompt(self, 
																	user_query: str,
																	user_context: Dict[str, Any],
																	restaurants: List[Dict[str, Any]]) -> str:
				"""
				맛집 추천을 위한 프롬프트를 생성합니다.
				
				Args:
						user_query (str): 사용자 질문
						user_context (Dict[str, Any]): 사용자 컨텍스트
						restaurants (List[Dict[str, Any]]): 추천할 식당 목록
						
				Returns:
						str: 구성된 프롬프트
				"""
				# 사용자 컨텍스트 분석
				context_analysis = self._analyze_user_context(user_query, user_context)
				
				# 식당 정보 포맷팅
				restaurant_info = self._format_restaurant_info(restaurants)
				
				# 특별 상황 감지
				special_instructions = self._detect_special_instructions(user_query, context_analysis)
				
				prompt = f"""
사용자 질문: "{user_query}"

사용자 컨텍스트:
{self._format_user_context(user_context, context_analysis)}

추천할 식당 정보:
{restaurant_info}

{special_instructions}

위 정보를 바탕으로 다음 조건에 맞는 자연스럽고 친근한 추천 응답을 작성해주세요:

1. 따뜻한 인사말로 시작
2. 사용자의 질문에 대한 이해도 표현
3. 각 식당의 추천 이유를 명확히 설명
4. 가격, 평점, 특징 등 핵심 정보 포함
5. 이모지를 적절히 사용하여 친근함 표현
6. 추가 질문이나 도움이 필요한지 마무리

응답은 한국어로 작성하고, 대구 달서구 지역의 맛집 전문가답게 작성해주세요.
"""
				
				return prompt.strip()
		
		def build_query_analysis_prompt(self, user_query: str, user_context: Dict[str, Any] = None) -> str:
				"""
				사용자 질문 분석을 위한 프롬프트를 생성합니다.
				
				Args:
						user_query (str): 사용자 질문
						user_context (Dict[str, Any], optional): 사용자 컨텍스트
						
				Returns:
						str: 구성된 프롬프트
				"""
				context_info = ""
				if user_context:
						context_info = f"""
사용자 컨텍스트:
- 위치: {user_context.get('location', '대구 달서구')}
- 예산 범위: {user_context.get('budget_range', '정보 없음')}
- 이전 선호도: {user_context.get('food_preferences', {})}
- 식단 제한사항: {user_context.get('dietary_restrictions', [])}
"""
				
				prompt = f"""
다음 사용자 질문을 분석하여 JSON 형식으로 결과를 반환해주세요.

사용자 질문: "{user_query}"
{context_info}

분석해야 할 요소들:
1. 질문 의도 (meal_recommendation, restaurant_info, review_inquiry, help_request 등)
2. 선호하는 음식 종류 (한식, 중식, 일식, 양식, 치킨, 피자 등)
3. 예산 범위 (저렴함, 보통, 비싼, 구체적 금액)
4. 인원 수 (혼밥, 커플, 가족, 친구들, 회식 등)
5. 분위기 선호도 (캐주얼, 고급스러운, 조용한, 활기찬 등)
6. 특별 요구사항 (주차, 배달, 포장, 예약 등)
7. 위치 정보 (특정 동네, 거리, 접근성 등)
8. 시간 관련 (지금 당장, 저녁, 점심, 주말 등)
9. 특별 상황 (데이트, 기념일, 회식, 가족 모임 등)

JSON 형식:
{{
		"intent": "질문 의도",
		"cuisine_types": ["음식 종류들"],
		"budget": "예산 정보",
		"party_size": "인원 정보", 
		"atmosphere": "분위기 선호도",
		"special_requirements": ["특별 요구사항들"],
		"location_preference": "위치 선호도",
		"time_context": "시간 관련 정보",
		"special_occasion": "특별 상황",
		"keywords": ["추출된 키워드들"],
		"urgency": "긴급도 (high, medium, low)",
		"confidence": "분석 신뢰도 (0.0-1.0)"
}}
"""
				
				return prompt.strip()
		
		def build_feedback_analysis_prompt(self, 
																			user_feedback: str,
																			restaurant_info: Dict[str, Any]) -> str:
				"""
				사용자 피드백 분석을 위한 프롬프트를 생성합니다.
				
				Args:
						user_feedback (str): 사용자 피드백
						restaurant_info (Dict[str, Any]): 식당 정보
						
				Returns:
						str: 구성된 프롬프트
				"""
				prompt = f"""
다음 사용자 피드백을 분석하여 JSON 형식으로 결과를 반환해주세요.

사용자 피드백: "{user_feedback}"

관련 식당 정보:
- 이름: {restaurant_info.get('name', '알 수 없음')}
- 카테고리: {restaurant_info.get('category', '알 수 없음')}
- 평균 가격: {restaurant_info.get('average_price', '알 수 없음')}원

분석 요소:
1. 전반적인 만족도 (1-5 점수)
2. 감정 분석 (positive, negative, neutral)
3. 구체적인 긍정 요소들
4. 구체적인 부정 요소들
5. 개선 제안사항
6. 재방문 의사
7. 추천 의사

JSON 형식:
{{
		"satisfaction_score": "1-5 점수",
		"sentiment": "감정 분석 결과",
		"positive_aspects": ["긍정적 요소들"],
		"negative_aspects": ["부정적 요소들"],
		"improvement_suggestions": ["개선 제안들"],
		"would_revisit": "재방문 의사 (true/false)",
		"would_recommend": "추천 의사 (true/false)",
		"key_insights": ["주요 인사이트들"],
		"feedback_type": "피드백 타입 (experience, complaint, praise 등)"
}}
"""
				
				return prompt.strip()
		
		def build_preference_extraction_prompt(self, conversation_history: List[str]) -> str:
				"""
				대화 히스토리에서 사용자 선호도를 추출하는 프롬프트를 생성합니다.
				
				Args:
						conversation_history (List[str]): 대화 기록
						
				Returns:
						str: 구성된 프롬프트
				"""
				conversation_text = "\n".join([
						f"- {msg}" for msg in conversation_history[-20:]  # 최근 20개 메시지
				])
				
				prompt = f"""
다음 대화 기록에서 사용자의 음식 선호도를 추출하여 JSON 형식으로 반환해주세요.

대화 기록:
{conversation_text}

추출할 선호도 정보:
1. 선호하는 음식 종류와 강도 (1-5)
2. 싫어하는 음식 종류
3. 가격대 선호도
4. 분위기 선호도
5. 매운맛 선호도
6. 식당 특징 선호도 (주차, 배달 등)
7. 식단 제한사항

JSON 형식:
{{
		"favorite_cuisines": [
				{{"type": "음식종류", "preference_level": 1-5, "reason": "이유"}}
		],
		"disliked_cuisines": ["싫어하는 음식들"],
		"price_sensitivity": "high/medium/low",
		"atmosphere_preference": "선호 분위기",
		"spice_level": "mild/medium/hot",
		"preferred_features": ["선호 특징들"],
		"dietary_restrictions": ["식단 제한사항들"],
		"confidence": "추출 신뢰도 (0.0-1.0)"
}}
"""
				
				return prompt.strip()
		
		def optimize_prompt_length(self, prompt: str, max_tokens: int = 3000) -> str:
				"""
				프롬프트 길이를 최적화합니다.
				
				Args:
						prompt (str): 원본 프롬프트
						max_tokens (int): 최대 토큰 수
						
				Returns:
						str: 최적화된 프롬프트
				"""
				# 대략적인 토큰 계산 (한국어 기준)
				estimated_tokens = len(prompt) / 2  # 한국어는 대략 2글자당 1토큰
				
				if estimated_tokens <= max_tokens:
						return prompt
				
				# 프롬프트 압축
				lines = prompt.split('\n')
				
				# 중요도에 따라 라인 유지/제거
				essential_lines = []
				optional_lines = []
				
				for line in lines:
						line = line.strip()
						if not line:
								continue
						
						# 필수 라인 판별
						if any(keyword in line for keyword in 
										['사용자 질문:', 'JSON 형식:', '응답할 때는', '분석해야 할']):
								essential_lines.append(line)
						else:
								optional_lines.append(line)
				
				# 필수 라인 먼저 추가
				optimized_lines = essential_lines.copy()
				
				# 선택적 라인들을 길이 제한 내에서 추가
				current_length = sum(len(line) for line in optimized_lines)
				max_length = max_tokens * 2  # 토큰 추정치 역산
				
				for line in optional_lines:
						if current_length + len(line) < max_length:
								optimized_lines.append(line)
								current_length += len(line)
						else:
								break
				
				return '\n'.join(optimized_lines)
		
		def _analyze_user_context(self, user_query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
				"""사용자 컨텍스트를 분석하여 추가 정보를 추출합니다."""
				analysis = {
						"query_urgency": "medium",
						"detected_occasion": None,
						"budget_signals": [],
						"group_signals": [],
						"time_signals": []
				}
				
				query_lower = user_query.lower()
				
				# 긴급도 분석
				if any(word in query_lower for word in self.context_keywords["urgency"]):
						analysis["query_urgency"] = "high"
				
				# 특별 상황 감지
				for occasion in self.context_keywords["special_occasion"]:
						if occasion in query_lower:
								analysis["detected_occasion"] = occasion
								break
				
				# 예산 관련 신호 감지
				for budget_word in self.context_keywords["budget_concern"]:
						if budget_word in query_lower:
								analysis["budget_signals"].append(budget_word)
				
				# 인원 관련 신호 감지
				for group_word in self.context_keywords["group_size"]:
						if group_word in query_lower:
								analysis["group_signals"].append(group_word)
				
				return analysis
		
		def _format_restaurant_info(self, restaurants: List[Dict[str, Any]]) -> str:
				"""식당 정보를 프롬프트에 적합한 형태로 포맷팅합니다."""
				formatted_info = ""
				
				for i, restaurant in enumerate(restaurants, 1):
						formatted_info += f"""
{i}. {restaurant.get('name', '알 수 없음')}
		- 카테고리: {restaurant.get('category', '정보 없음')}
		- 위치: {restaurant.get('address', '정보 없음')}
		- 평점: {restaurant.get('rating_average', 0)}/5.0 ({restaurant.get('rating_count', 0)}개 리뷰)
		- 평균 가격: {restaurant.get('average_price', '정보 없음')}원
		- 운영시간: {restaurant.get('business_hours', '정보 없음')}
		- 특징: {', '.join(restaurant.get('special_features', []))}
		- 거리: {restaurant.get('distance', '정보 없음')}
"""
				
				return formatted_info.strip()
		
		def _format_user_context(self, user_context: Dict[str, Any], analysis: Dict[str, Any]) -> str:
				"""사용자 컨텍스트를 포맷팅합니다."""
				formatted_context = f"""
- 위치: {user_context.get('location', '대구 달서구')}
- 예산 범위: {user_context.get('budget_range', '정보 없음')}
- 선호 음식: {user_context.get('food_preferences', {})}
- 식단 제한: {user_context.get('dietary_restrictions', [])}
- 감지된 긴급도: {analysis.get('query_urgency', 'medium')}
- 특별 상황: {analysis.get('detected_occasion', '없음')}
"""
				
				return formatted_context.strip()
		
		def _detect_special_instructions(self, user_query: str, context_analysis: Dict[str, Any]) -> str:
				"""특별한 상황에 대한 추가 지시사항을 생성합니다."""
				instructions = []
				
				# 긴급도에 따른 지시사항
				if context_analysis.get("query_urgency") == "high":
						instructions.append("- 현재 영업 중인 식당을 우선 추천해주세요")
						instructions.append("- 빠른 서비스를 제공하는 곳을 언급해주세요")
				
				# 특별 상황에 따른 지시사항
				occasion = context_analysis.get("detected_occasion")
				if occasion == "데이트":
						instructions.append("- 분위기 좋고 조용한 곳을 우선 추천해주세요")
						instructions.append("- 커플석이나 프라이버시가 보장되는 곳을 언급해주세요")
				elif occasion == "회식":
						instructions.append("- 단체 수용이 가능한 곳을 우선 추천해주세요")
						instructions.append("- 예약 가능 여부를 언급해주세요")
				
				# 예산 관련 지시사항
				budget_signals = context_analysis.get("budget_signals", [])
				if any(word in budget_signals for word in ["저렴", "싸", "가성비"]):
						instructions.append("- 가격 대비 만족도가 높은 곳을 강조해주세요")
						instructions.append("- 구체적인 가격 정보를 명시해주세요")
				
				if instructions:
						return "특별 지시사항:\n" + "\n".join(instructions)
				else:
						return ""
		
		def _load_recommendation_template(self) -> str:
				"""추천 템플릿을 로드합니다."""
				return """
{user_greeting}

{understanding_statement}

{recommendations_list}

{additional_tips}

{closing_message}
"""
		
		def _load_analysis_template(self) -> str:
				"""분석 템플릿을 로드합니다."""
				return """
사용자 질문: "{user_query}"
분석 결과: {analysis_result}
신뢰도: {confidence}
"""
		
		def _load_response_template(self) -> str:
				"""응답 템플릿을 로드합니다."""
				return """
{introduction}
{main_content}
{conclusion}
"""
		
		def _load_feedback_template(self) -> str:
				"""피드백 템플릿을 로드합니다."""
				return """
피드백: "{feedback}"
분석: {analysis}
액션 아이템: {action_items}
"""