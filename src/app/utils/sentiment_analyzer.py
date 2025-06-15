# -*- coding: utf-8 -*-
"""
감정 분석 유틸리티 (SentimentAnalyzer)
리뷰 텍스트의 감정을 분석하고 키워드를 추출하는 도구입니다.
"""

import re
import logging
from typing import Dict, List, Any, Tuple
from collections import Counter

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
		"""
		한국어 텍스트의 감정 분석을 수행하는 클래스
		간단한 규칙 기반 분석과 키워드 추출을 제공합니다.
		"""
		
		def __init__(self):
				"""
				감정 분석기 초기화
				긍정/부정 키워드와 감정 사전을 설정합니다.
				"""
				# 긍정적 키워드들
				self.positive_keywords = {
						'맛': ['맛있다', '맛있어', '맛좋다', '맛나다', '맛집', '맛짱', '존맛', '꿀맛'],
						'서비스': ['친절하다', '친절해', '서비스좋다', '친절', '정중', '상냥', '배려'],
						'분위기': ['좋다', '괜찮다', '멋지다', '예쁘다', '깔끔하다', '아늑하다', '편안하다'],
						'가성비': ['저렴하다', '싸다', '가성비', '합리적', '착하다', '적당하다'],
						'품질': ['신선하다', '질좋다', '고급스럽다', '깨끗하다', '위생적'],
						'기타': ['추천', '재방문', '또가고싶다', '만족', '좋아', '최고', '대박', '굿']
				}
				
				# 부정적 키워드들
				self.negative_keywords = {
						'맛': ['맛없다', '맛없어', '별로', '싱겁다', '짜다', '느끼하다', '비리다'],
						'서비스': ['불친절', '서비스나쁘다', '무시', '불쾌', '시끄럽다'],
						'분위기': ['더럽다', '지저분하다', '낡았다', '어둡다', '좁다'],
						'가성비': ['비싸다', '가격대비', '아깝다', '돈아까워', '바가지'],
						'품질': ['상했다', '오래됐다', '질나쁘다', '신선하지않다'],
						'기타': ['실망', '후회', '최악', '비추천', '안가', '다시안가']
				}
				
				# 감정 강도 수식어
				self.intensity_modifiers = {
						'매우': 1.5, '너무': 1.4, '정말': 1.3, '진짜': 1.3, '완전': 1.4,
						'조금': 0.7, '약간': 0.7, '살짝': 0.6, '그럭저럭': 0.5,
						'엄청': 1.6, '완전히': 1.5, '극도로': 1.7, '최고로': 1.8
				}
				
				# 부정 표현
				self.negation_words = ['안', '못', '없다', '아니다', '절대', '전혀', '결코']
				
				# 음식 관련 키워드
				self.food_keywords = [
						'맛', '음식', '요리', '메뉴', '반찬', '국물', '소스', '양념',
						'고기', '야채', '밥', '면', '국', '찌개', '볶음', '구이'
				]
				
				# 서비스 관련 키워드
				self.service_keywords = [
						'서비스', '직원', '사장', '알바', '웨이터', '응대', '주문', '계산'
				]
				
				# 분위기 관련 키워드
				self.atmosphere_keywords = [
						'분위기', '인테리어', '장소', '공간', '자리', '테이블', '화장실', '주차'
				]
		
		def analyze_text(self, text: str) -> Dict[str, Any]:
				"""
				텍스트를 분석하여 감정 점수와 관련 정보를 반환합니다.
				
				Args:
						text (str): 분석할 텍스트
						
				Returns:
						Dict[str, Any]: 감정 분석 결과
				"""
				try:
						if not text or len(text.strip()) < 3:
								return self._get_neutral_result()
						
						# 텍스트 전처리
						processed_text = self._preprocess_text(text)
						
						# 문장 분할
						sentences = self._split_sentences(processed_text)
						
						# 각 문장별 감정 분석
						sentence_scores = []
						positive_aspects = []
						negative_aspects = []
						
						for sentence in sentences:
								score, pos_aspects, neg_aspects = self._analyze_sentence(sentence)
								sentence_scores.append(score)
								positive_aspects.extend(pos_aspects)
								negative_aspects.extend(neg_aspects)
						
						# 전체 감정 점수 계산
						if sentence_scores:
								overall_score = sum(sentence_scores) / len(sentence_scores)
						else:
								overall_score = 0.0
						
						# 감정 라벨 결정
						sentiment_label = self._determine_sentiment_label(overall_score)
						
						# 키워드 추출
						keywords = self._extract_keywords(processed_text)
						
						# 감정 태그 생성
						emotion_tags = self._generate_emotion_tags(overall_score, positive_aspects, negative_aspects)
						
						return {
								'score': round(overall_score, 2),
								'label': sentiment_label,
								'confidence': abs(overall_score),
								'emotions': emotion_tags,
								'keywords': keywords[:10],  # 상위 10개 키워드
								'positive_aspects': list(set(positive_aspects)),
								'negative_aspects': list(set(negative_aspects)),
								'sentence_count': len(sentences),
								'analysis_details': {
										'sentence_scores': sentence_scores,
										'text_length': len(text)
								}
						}
						
				except Exception as e:
						logger.error(f"감정 분석 중 오류 발생: {e}")
						return self._get_neutral_result()
		
		def _preprocess_text(self, text: str) -> str:
				"""
				텍스트를 전처리합니다.
				
				Args:
						text (str): 원본 텍스트
						
				Returns:
						str: 전처리된 텍스트
				"""
				# 소문자 변환은 한글에서는 불필요
				processed = text.strip()
				
				# 반복되는 문자 정리 (ㅋㅋㅋ -> ㅋ, !!!!! -> !)
				processed = re.sub(r'([ㅋㅎ])\1{2,}', r'\1', processed)
				processed = re.sub(r'([!?])\1{2,}', r'\1', processed)
				
				# 이모티콘 처리 (간단한 텍스트 이모티콘)
				emoticon_map = {
						'^^': '기쁨',
						'^_^': '기쁨',
						':)': '기쁨',
						':(': '슬픔',
						'ㅠㅠ': '슬픔',
						'ㅜㅜ': '슬픔'
				}
				
				for emoticon, emotion in emoticon_map.items():
						if emoticon in processed:
								processed = processed.replace(emoticon, f' {emotion} ')
				
				return processed
		
		def _split_sentences(self, text: str) -> List[str]:
				"""
				텍스트를 문장으로 분할합니다.
				
				Args:
						text (str): 입력 텍스트
						
				Returns:
						List[str]: 문장 리스트
				"""
				# 한국어 문장 분할 패턴
				sentence_endings = r'[.!?。！？]+'
				sentences = re.split(sentence_endings, text)
				
				# 빈 문장 제거 및 정리
				cleaned_sentences = []
				for sentence in sentences:
						sentence = sentence.strip()
						if len(sentence) > 2:  # 너무 짧은 문장 제외
								cleaned_sentences.append(sentence)
				
				return cleaned_sentences
		
		def _analyze_sentence(self, sentence: str) -> Tuple[float, List[str], List[str]]:
				"""
				개별 문장의 감정을 분석합니다.
				
				Args:
						sentence (str): 분석할 문장
						
				Returns:
						Tuple[float, List[str], List[str]]: (감정점수, 긍정요소, 부정요소)
				"""
				sentence_lower = sentence.lower()
				
				positive_score = 0.0
				negative_score = 0.0
				positive_aspects = []
				negative_aspects = []
				
				# 부정어 확인
				has_negation = any(neg in sentence for neg in self.negation_words)
				
				# 긍정 키워드 검사
				for category, keywords in self.positive_keywords.items():
						for keyword in keywords:
								if keyword in sentence:
										score = 1.0
										
										# 강도 수식어 적용
										for modifier, multiplier in self.intensity_modifiers.items():
												if modifier in sentence:
														score *= multiplier
														break
										
										# 부정어가 있으면 점수 반전
										if has_negation:
												negative_score += score
												negative_aspects.append(f"{category}: {keyword}")
										else:
												positive_score += score
												positive_aspects.append(f"{category}: {keyword}")
				
				# 부정 키워드 검사
				for category, keywords in self.negative_keywords.items():
						for keyword in keywords:
								if keyword in sentence:
										score = 1.0
										
										# 강도 수식어 적용
										for modifier, multiplier in self.intensity_modifiers.items():
												if modifier in sentence:
														score *= multiplier
														break
										
										# 부정어가 있으면 점수 반전
										if has_negation:
												positive_score += score
												positive_aspects.append(f"{category}: {keyword}")
										else:
												negative_score += score
												negative_aspects.append(f"{category}: {keyword}")
				
				# 최종 점수 계산 (-1.0 ~ 1.0)
				total_score = positive_score - negative_score
				
				# 정규화
				if total_score > 0:
						final_score = min(total_score / 3.0, 1.0)  # 최대 3점으로 정규화
				else:
						final_score = max(total_score / 3.0, -1.0)
				
				return final_score, positive_aspects, negative_aspects
		
		def _determine_sentiment_label(self, score: float) -> str:
				"""
				감정 점수를 바탕으로 라벨을 결정합니다.
				
				Args:
						score (float): 감정 점수
						
				Returns:
						str: 감정 라벨
				"""
				if score > 0.3:
						return 'positive'
				elif score < -0.3:
						return 'negative'
				else:
						return 'neutral'
		
		def _extract_keywords(self, text: str) -> List[str]:
				"""
				텍스트에서 중요한 키워드를 추출합니다.
				
				Args:
						text (str): 텍스트
						
				Returns:
						List[str]: 키워드 리스트
				"""
				# 단어 분할 (간단한 공백 기반)
				words = re.findall(r'[가-힣]{2,}', text)
				
				# 불용어 제거
				stopwords = {
						'이것', '그것', '저것', '여기', '거기', '저기',
						'이거', '그거', '저거', '때문', '정도', '이런', '그런', '저런'
				}
				
				filtered_words = [word for word in words if word not in stopwords and len(word) >= 2]
				
				# 빈도 계산
				word_counts = Counter(filtered_words)
				
				# 음식/서비스/분위기 관련 키워드 우선순위 부여
				prioritized_keywords = []
				
				for word, count in word_counts.most_common():
						if (any(keyword in word for keyword in self.food_keywords) or
								any(keyword in word for keyword in self.service_keywords) or
								any(keyword in word for keyword in self.atmosphere_keywords)):
								prioritized_keywords.insert(0, word)
						else:
								prioritized_keywords.append(word)
				
				return prioritized_keywords
		
		def _generate_emotion_tags(self, 
															score: float, 
															positive_aspects: List[str], 
															negative_aspects: List[str]) -> List[str]:
				"""
				감정 태그를 생성합니다.
				
				Args:
						score (float): 감정 점수
						positive_aspects (List[str]): 긍정적 요소
						negative_aspects (List[str]): 부정적 요소
						
				Returns:
						List[str]: 감정 태그 리스트
				"""
				tags = []
				
				# 기본 감정 태그
				if score > 0.7:
						tags.append('매우_만족')
				elif score > 0.3:
						tags.append('만족')
				elif score > 0.1:
						tags.append('약간_만족')
				elif score < -0.7:
						tags.append('매우_불만')
				elif score < -0.3:
						tags.append('불만')
				elif score < -0.1:
						tags.append('약간_불만')
				else:
						tags.append('보통')
				
				# 세부 감정 태그
				if positive_aspects:
						if any('맛' in aspect for aspect in positive_aspects):
								tags.append('맛_만족')
						if any('서비스' in aspect for aspect in positive_aspects):
								tags.append('서비스_만족')
						if any('분위기' in aspect for aspect in positive_aspects):
								tags.append('분위기_만족')
				
				if negative_aspects:
						if any('맛' in aspect for aspect in negative_aspects):
								tags.append('맛_불만')
						if any('서비스' in aspect for aspect in negative_aspects):
								tags.append('서비스_불만')
						if any('분위기' in aspect for aspect in negative_aspects):
								tags.append('분위기_불만')
				
				return tags
		
		def _get_neutral_result(self) -> Dict[str, Any]:
				"""중립적인 기본 분석 결과를 반환합니다."""
				return {
						'score': 0.0,
						'label': 'neutral',
						'confidence': 0.0,
						'emotions': ['보통'],
						'keywords': [],
						'positive_aspects': [],
						'negative_aspects': [],
						'sentence_count': 0,
						'analysis_details': {
								'sentence_scores': [],
								'text_length': 0
						}
				}
		
		def batch_analyze(self, texts: List[str]) -> List[Dict[str, Any]]:
				"""
				여러 텍스트를 일괄 분석합니다.
				
				Args:
						texts (List[str]): 분석할 텍스트 리스트
						
				Returns:
						List[Dict[str, Any]]: 분석 결과 리스트
				"""
				results = []
				
				for text in texts:
						try:
								result = self.analyze_text(text)
								results.append(result)
						except Exception as e:
								logger.error(f"배치 분석 중 오류 발생: {e}")
								results.append(self._get_neutral_result())
				
				return results
		
		def get_sentiment_summary(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
				"""
				여러 분석 결과의 요약을 생성합니다.
				
				Args:
						analyses (List[Dict[str, Any]]): 분석 결과 리스트
						
				Returns:
						Dict[str, Any]: 요약 정보
				"""
				if not analyses:
						return {}
				
				# 평균 점수 계산
				scores = [analysis['score'] for analysis in analyses]
				avg_score = sum(scores) / len(scores)
				
				# 감정 라벨 분포
				labels = [analysis['label'] for analysis in analyses]
				label_counts = Counter(labels)
				
				# 공통 키워드
				all_keywords = []
				for analysis in analyses:
						all_keywords.extend(analysis.get('keywords', []))
				
				common_keywords = [keyword for keyword, count in Counter(all_keywords).most_common(10)]
				
				return {
						'total_analyses': len(analyses),
						'average_score': round(avg_score, 2),
						'dominant_sentiment': label_counts.most_common(1)[0][0],
						'sentiment_distribution': dict(label_counts),
						'common_keywords': common_keywords,
						'score_range': {
								'min': min(scores),
								'max': max(scores)
						}
				}