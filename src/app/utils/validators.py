# -*- coding: utf-8 -*-
"""
FOODI 프로젝트 입력 데이터 검증 함수들
사용자 입력, API 요청 데이터 등의 유효성을 검증합니다.
"""

import re
import logging
from typing import Dict, List, Any, Tuple, Optional, Union

logger = logging.getLogger(__name__)

# =============================================================================
# 기본 검증 함수들
# =============================================================================

def validate_email(email: str) -> bool:
    """
    이메일 주소 형식을 검증하는 함수
    
    Args:
        email (str): 검증할 이메일 주소
    
    Returns:
        bool: 유효한 이메일 주소인지 여부
    """
    if not email or not isinstance(email, str):
        return False
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def validate_phone_number(phone: str) -> bool:
    """
    전화번호 형식을 검증하는 함수 (한국 전화번호 형식)
    
    Args:
        phone (str): 검증할 전화번호
    
    Returns:
        bool: 유효한 전화번호인지 여부
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # 한국 전화번호 패턴 (예: 010-1234-5678, 053-123-4567)
    phone_clean = phone.replace('-', '').replace(' ', '')
    phone_pattern = r'^(01[016789]|02|0[3-9][0-9]?)[0-9]{3,4}[0-9]{4}$'
    return re.match(phone_pattern, phone_clean) is not None

def validate_price_range(price_range: Union[str, int]) -> bool:
    """
    가격 범위 형식을 검증하는 함수
    
    Args:
        price_range (str|int): 검증할 가격 범위 (예: "10000-20000" 또는 10000)
    
    Returns:
        bool: 유효한 가격 범위인지 여부
    """
    if not price_range:
        return False
    
    try:
        if isinstance(price_range, int):
            return price_range >= 0
        
        if isinstance(price_range, str):
            if '-' in price_range:
                min_price, max_price = price_range.split('-')
                min_val = int(min_price.strip())
                max_val = int(max_price.strip())
                return min_val >= 0 and max_val >= min_val
            else:
                return int(price_range) >= 0
        
        return False
    except (ValueError, TypeError):
        return False

def validate_latitude(latitude: Union[float, str]) -> bool:
    """
    위도 값을 검증하는 함수
    
    Args:
        latitude (float|str): 검증할 위도 값
    
    Returns:
        bool: 유효한 위도인지 여부 (-90.0 ~ 90.0)
    """
    try:
        lat = float(latitude)
        return -90.0 <= lat <= 90.0
    except (ValueError, TypeError):
        return False

def validate_longitude(longitude: Union[float, str]) -> bool:
    """
    경도 값을 검증하는 함수
    
    Args:
        longitude (float|str): 검증할 경도 값
    
    Returns:
        bool: 유효한 경도인지 여부 (-180.0 ~ 180.0)
    """
    try:
        lng = float(longitude)
        return -180.0 <= lng <= 180.0
    except (ValueError, TypeError):
        return False

def validate_rating(rating: Union[float, str, int]) -> bool:
    """
    평점 값을 검증하는 함수
    
    Args:
        rating (float|str|int): 검증할 평점 값
    
    Returns:
        bool: 유효한 평점인지 여부 (0.0 ~ 5.0)
    """
    try:
        r = float(rating)
        return 0.0 <= r <= 5.0
    except (ValueError, TypeError):
        return False

def validate_string_length(text: str, min_len: int = 1, max_len: int = 255) -> bool:
    """
    문자열 길이를 검증하는 함수
    
    Args:
        text (str): 검증할 문자열
        min_len (int): 최소 길이
        max_len (int): 최대 길이
    
    Returns:
        bool: 유효한 길이인지 여부
    """
    if not isinstance(text, str):
        return False
    return min_len <= len(text.strip()) <= max_len

def validate_positive_integer(value: Union[int, str]) -> bool:
    """
    양의 정수를 검증하는 함수
    
    Args:
        value (int|str): 검증할 값
    
    Returns:
        bool: 양의 정수인지 여부
    """
    try:
        num = int(value)
        return num > 0
    except (ValueError, TypeError):
        return False

# =============================================================================
# 사용자 관련 검증 함수들
# =============================================================================

def validate_user_params(user_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    사용자 데이터를 검증하는 함수
    
    Args:
        user_data (dict): 검증할 사용자 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(user_data, dict):
        return False, ["사용자 데이터는 딕셔너리 형태여야 합니다."]
    
    # 필수 필드 검증
    required_fields = ['username', 'email']
    for field in required_fields:
        if field not in user_data or not user_data[field]:
            errors.append(f"{field}는 필수 입력 항목입니다.")
    
    # 사용자명 검증
    if 'username' in user_data and user_data['username']:
        username = user_data['username']
        if not validate_string_length(username, 2, 50):
            errors.append("사용자명은 2-50자 사이여야 합니다.")
        elif not re.match(r'^[a-zA-Z0-9가-힣_-]+$', username):
            errors.append("사용자명은 영문, 한글, 숫자, 언더스코어, 하이픈만 사용 가능합니다.")
    
    # 이메일 검증
    if 'email' in user_data and user_data['email']:
        if not validate_email(user_data['email']):
            errors.append("유효하지 않은 이메일 주소입니다.")
    
    # 예산 범위 검증
    if 'budget_range' in user_data and user_data['budget_range']:
        if not validate_price_range(user_data['budget_range']):
            errors.append("유효하지 않은 예산 범위입니다.")
    
    # 위치 검증
    if 'location' in user_data and user_data['location']:
        if not validate_string_length(user_data['location'], 2, 100):
            errors.append("위치는 2-100자 사이여야 합니다.")
    
    # 음식 선호도 검증
    if 'food_preferences' in user_data and user_data['food_preferences']:
        if not isinstance(user_data['food_preferences'], dict):
            errors.append("음식 선호도는 딕셔너리 형태여야 합니다.")
    
    return len(errors) == 0, errors

def validate_user_data(user_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    사용자 데이터를 검증하는 함수 (validate_user_params의 별칭)
    
    Args:
        user_data (dict): 검증할 사용자 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    return validate_user_params(user_data)

# =============================================================================
# 식당 관련 검증 함수들
# =============================================================================

def validate_restaurant_params(restaurant_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    식당 데이터를 검증하는 함수
    
    Args:
        restaurant_data (dict): 검증할 식당 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(restaurant_data, dict):
        return False, ["식당 데이터는 딕셔너리 형태여야 합니다."]
    
    # 필수 필드 검증
    required_fields = ['name', 'address', 'category']
    for field in required_fields:
        if field not in restaurant_data or not restaurant_data[field]:
            errors.append(f"{field}는 필수 입력 항목입니다.")
    
    # 식당명 검증
    if 'name' in restaurant_data and restaurant_data['name']:
        if not validate_string_length(restaurant_data['name'], 1, 100):
            errors.append("식당명은 1-100자 사이여야 합니다.")
    
    # 주소 검증
    if 'address' in restaurant_data and restaurant_data['address']:
        if not validate_string_length(restaurant_data['address'], 5, 200):
            errors.append("주소는 5-200자 사이여야 합니다.")
    
    # 전화번호 검증
    if 'phone' in restaurant_data and restaurant_data['phone']:
        if not validate_phone_number(restaurant_data['phone']):
            errors.append("유효하지 않은 전화번호입니다.")
    
    # 위도 검증
    if 'latitude' in restaurant_data and restaurant_data['latitude'] is not None:
        if not validate_latitude(restaurant_data['latitude']):
            errors.append("유효하지 않은 위도 값입니다.")
    
    # 경도 검증
    if 'longitude' in restaurant_data and restaurant_data['longitude'] is not None:
        if not validate_longitude(restaurant_data['longitude']):
            errors.append("유효하지 않은 경도 값입니다.")
    
    # 평균 가격 검증
    if 'average_price' in restaurant_data and restaurant_data['average_price'] is not None:
        try:
            price = int(restaurant_data['average_price'])
            if price < 0:
                errors.append("평균 가격은 0 이상이어야 합니다.")
        except (ValueError, TypeError):
            errors.append("유효하지 않은 평균 가격입니다.")
    
    # 카테고리 검증
    valid_categories = [
        '한식', '중식', '일식', '양식', '치킨', '피자', '햄버거', 
        '분식', '카페', '디저트', '술집', '베이커리', '패스트푸드', '기타'
    ]
    if 'category' in restaurant_data and restaurant_data['category']:
        if restaurant_data['category'] not in valid_categories:
            errors.append(f"유효하지 않은 카테고리입니다. 사용 가능한 카테고리: {', '.join(valid_categories)}")
    
    # 요리 타입 검증
    if 'cuisine_type' in restaurant_data and restaurant_data['cuisine_type']:
        if not validate_string_length(restaurant_data['cuisine_type'], 1, 50):
            errors.append("요리 타입은 1-50자 사이여야 합니다.")
    
    # 설명 검증
    if 'description' in restaurant_data and restaurant_data['description']:
        if not validate_string_length(restaurant_data['description'], 1, 500):
            errors.append("설명은 1-500자 사이여야 합니다.")
    
    # 메뉴 아이템 검증
    if 'menu_items' in restaurant_data and restaurant_data['menu_items']:
        if isinstance(restaurant_data['menu_items'], list):
            for i, menu_item in enumerate(restaurant_data['menu_items']):
                is_valid, menu_errors = validate_menu_data(menu_item)
                if not is_valid:
                    for error in menu_errors:
                        errors.append(f"메뉴 항목 {i+1}: {error}")
        else:
            errors.append("메뉴 아이템은 리스트 형태여야 합니다.")
    
    # 특별 기능 검증
    if 'special_features' in restaurant_data and restaurant_data['special_features']:
        if not isinstance(restaurant_data['special_features'], list):
            errors.append("특별 기능은 리스트 형태여야 합니다.")
    
    # 분위기 태그 검증
    if 'atmosphere_tags' in restaurant_data and restaurant_data['atmosphere_tags']:
        if not isinstance(restaurant_data['atmosphere_tags'], list):
            errors.append("분위기 태그는 리스트 형태여야 합니다.")
    
    return len(errors) == 0, errors

def validate_restaurant_data(restaurant_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    식당 데이터를 검증하는 함수 (validate_restaurant_params의 별칭)
    
    Args:
        restaurant_data (dict): 검증할 식당 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    return validate_restaurant_params(restaurant_data)

# =============================================================================
# 리뷰 관련 검증 함수들
# =============================================================================

def validate_review_params(review_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    리뷰 데이터를 검증하는 함수
    
    Args:
        review_data (dict): 검증할 리뷰 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(review_data, dict):
        return False, ["리뷰 데이터는 딕셔너리 형태여야 합니다."]
    
    # 필수 필드 검증
    required_fields = ['user_id', 'restaurant_id', 'rating']
    for field in required_fields:
        if field not in review_data or review_data[field] is None:
            errors.append(f"{field}는 필수 입력 항목입니다.")
    
    # 사용자 ID 검증
    if 'user_id' in review_data and review_data['user_id'] is not None:
        if not validate_positive_integer(review_data['user_id']):
            errors.append("사용자 ID는 양의 정수여야 합니다.")
    
    # 식당 ID 검증
    if 'restaurant_id' in review_data and review_data['restaurant_id'] is not None:
        if not validate_positive_integer(review_data['restaurant_id']):
            errors.append("식당 ID는 양의 정수여야 합니다.")
    
    # 평점 검증
    if 'rating' in review_data and review_data['rating'] is not None:
        if not validate_rating(review_data['rating']):
            errors.append("평점은 0.0에서 5.0 사이의 값이어야 합니다.")
    
    # 리뷰 내용 검증
    if 'content' in review_data and review_data['content']:
        if not validate_string_length(review_data['content'], 1, 1000):
            errors.append("리뷰 내용은 1-1000자 사이여야 합니다.")
    
    # 방문 날짜 검증 (있는 경우)
    if 'visit_date' in review_data and review_data['visit_date']:
        # 날짜 형식 검증은 필요에 따라 추가 가능
        pass
    
    # 추천 여부 검증
    if 'is_recommended' in review_data and review_data['is_recommended'] is not None:
        if not isinstance(review_data['is_recommended'], bool):
            errors.append("추천 여부는 불리언 값이어야 합니다.")
    
    return len(errors) == 0, errors

def validate_review_data(review_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    리뷰 데이터를 검증하는 함수 (validate_review_params의 별칭)
    
    Args:
        review_data (dict): 검증할 리뷰 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    return validate_review_params(review_data)

# =============================================================================
# 추천 관련 검증 함수들
# =============================================================================

def validate_recommendation_params(rec_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    추천 데이터를 검증하는 함수
    
    Args:
        rec_data (dict): 검증할 추천 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(rec_data, dict):
        return False, ["추천 데이터는 딕셔너리 형태여야 합니다."]
    
    # 필수 필드 검증
    required_fields = ['user_id', 'restaurant_id']
    for field in required_fields:
        if field not in rec_data or rec_data[field] is None:
            errors.append(f"{field}는 필수 입력 항목입니다.")
    
    # 사용자 ID 검증
    if 'user_id' in rec_data and rec_data['user_id'] is not None:
        if not validate_positive_integer(rec_data['user_id']):
            errors.append("사용자 ID는 양의 정수여야 합니다.")
    
    # 식당 ID 검증
    if 'restaurant_id' in rec_data and rec_data['restaurant_id'] is not None:
        if not validate_positive_integer(rec_data['restaurant_id']):
            errors.append("식당 ID는 양의 정수여야 합니다.")
    
    # 신뢰도 점수 검증
    if 'confidence_score' in rec_data and rec_data['confidence_score'] is not None:
        try:
            score = float(rec_data['confidence_score'])
            if not (0.0 <= score <= 1.0):
                errors.append("신뢰도 점수는 0.0에서 1.0 사이의 값이어야 합니다.")
        except (ValueError, TypeError):
            errors.append("유효하지 않은 신뢰도 점수입니다.")
    
    # 추천 이유 검증
    if 'reason' in rec_data and rec_data['reason']:
        if not validate_string_length(rec_data['reason'], 1, 500):
            errors.append("추천 이유는 1-500자 사이여야 합니다.")
    
    # 추천 타입 검증
    if 'recommendation_type' in rec_data and rec_data['recommendation_type']:
        valid_types = ['preference_based', 'location_based', 'collaborative', 'content_based', 'hybrid']
        if rec_data['recommendation_type'] not in valid_types:
            errors.append(f"유효하지 않은 추천 타입입니다. 사용 가능한 타입: {', '.join(valid_types)}")
    
    return len(errors) == 0, errors

def validate_recommendation_data(rec_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    추천 데이터를 검증하는 함수 (validate_recommendation_params의 별칭)
    
    Args:
        rec_data (dict): 검증할 추천 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    return validate_recommendation_params(rec_data)

# =============================================================================
# 메뉴 관련 검증 함수들
# =============================================================================

def validate_menu_data(menu_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    메뉴 데이터를 검증하는 함수
    
    Args:
        menu_data (dict): 검증할 메뉴 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(menu_data, dict):
        return False, ["메뉴 데이터는 딕셔너리 형태여야 합니다."]
    
    # 필수 필드 검증
    required_fields = ['name', 'price']
    for field in required_fields:
        if field not in menu_data or not menu_data[field]:
            errors.append(f"{field}는 필수 입력 항목입니다.")
    
    # 메뉴명 검증
    if 'name' in menu_data and menu_data['name']:
        if not validate_string_length(menu_data['name'], 1, 50):
            errors.append("메뉴명은 1-50자 사이여야 합니다.")
    
    # 가격 검증
    if 'price' in menu_data and menu_data['price'] is not None:
        try:
            price = int(menu_data['price'])
            if price < 0:
                errors.append("가격은 0 이상이어야 합니다.")
        except (ValueError, TypeError):
            errors.append("유효하지 않은 가격입니다.")
    
    # 카테고리 검증
    if 'category' in menu_data and menu_data['category']:
        valid_categories = ['메인', '사이드', '음료', '디저트', '주류', '기타']
        if menu_data['category'] not in valid_categories:
            errors.append(f"유효하지 않은 메뉴 카테고리입니다. 사용 가능한 카테고리: {', '.join(valid_categories)}")
    
    # 설명 검증
    if 'description' in menu_data and menu_data['description']:
        if not validate_string_length(menu_data['description'], 1, 200):
            errors.append("메뉴 설명은 1-200자 사이여야 합니다.")
    
    # 인기도 검증
    if 'is_popular' in menu_data and menu_data['is_popular'] is not None:
        if not isinstance(menu_data['is_popular'], bool):
            errors.append("인기 메뉴 여부는 불리언 값이어야 합니다.")
    
    return len(errors) == 0, errors

# =============================================================================
# 채팅 관련 검증 함수들
# =============================================================================

def validate_chat_message(message: str) -> Tuple[bool, str]:
    """
    채팅 메시지를 검증하는 함수
    
    Args:
        message (str): 검증할 메시지
    
    Returns:
        tuple: (유효성 여부, 오류 메시지)
    """
    if not message or not isinstance(message, str):
        return False, "메시지는 필수입니다."
    
    message = message.strip()
    
    if len(message) == 0:
        return False, "빈 메시지는 전송할 수 없습니다."
    
    if len(message) > 1000:
        return False, "메시지는 1000자를 초과할 수 없습니다."
    
    # 금지된 단어나 패턴 검사 (XSS 방지)
    forbidden_patterns = [
        r'<script.*?>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe',
        r'<object',
        r'<embed'
    ]
    
    for pattern in forbidden_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            return False, "허용되지 않는 내용이 포함되어 있습니다."
    
    return True, ""

def validate_chat_data(chat_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    채팅 데이터를 검증하는 함수
    
    Args:
        chat_data (dict): 검증할 채팅 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(chat_data, dict):
        return False, ["채팅 데이터는 딕셔너리 형태여야 합니다."]
    
    # 메시지 검증
    if 'message' in chat_data and chat_data['message']:
        is_valid, error_msg = validate_chat_message(chat_data['message'])
        if not is_valid:
            errors.append(error_msg)
    
    # 사용자 ID 검증
    if 'user_id' in chat_data and chat_data['user_id'] is not None:
        if not validate_positive_integer(chat_data['user_id']):
            errors.append("사용자 ID는 양의 정수여야 합니다.")
    
    # 세션 ID 검증
    if 'session_id' in chat_data and chat_data['session_id']:
        if not validate_string_length(chat_data['session_id'], 1, 100):
            errors.append("세션 ID는 1-100자 사이여야 합니다.")
    
    return len(errors) == 0, errors

# =============================================================================
# 위치 및 검색 관련 검증 함수들
# =============================================================================

def validate_location_data(location_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    위치 데이터를 검증하는 함수
    
    Args:
        location_data (dict): 검증할 위치 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(location_data, dict):
        return False, ["위치 데이터는 딕셔너리 형태여야 합니다."]
    
    # 위도 검증
    if 'latitude' in location_data and location_data['latitude'] is not None:
        if not validate_latitude(location_data['latitude']):
            errors.append("유효하지 않은 위도 값입니다.")
    
    # 경도 검증
    if 'longitude' in location_data and location_data['longitude'] is not None:
        if not validate_longitude(location_data['longitude']):
            errors.append("유효하지 않은 경도 값입니다.")
    
    # 주소 검증
    if 'address' in location_data and location_data['address']:
        if not validate_string_length(location_data['address'], 5, 200):
            errors.append("주소는 5-200자 사이여야 합니다.")
    
    # 거리 검증
    if 'distance' in location_data and location_data['distance'] is not None:
        try:
            distance = float(location_data['distance'])
            if distance < 0 or distance > 100:  # 최대 100km
                errors.append("거리는 0-100km 사이여야 합니다.")
        except (ValueError, TypeError):
            errors.append("유효하지 않은 거리 값입니다.")
    
    return len(errors) == 0, errors

def validate_search_params(search_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    검색 파라미터를 검증하는 함수
    
    Args:
        search_data (dict): 검증할 검색 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(search_data, dict):
        return False, ["검색 데이터는 딕셔너리 형태여야 합니다."]
    
    # 검색어 검증
    if 'query' in search_data and search_data['query']:
        if not validate_string_length(search_data['query'], 1, 100):
            errors.append("검색어는 1-100자 사이여야 합니다.")
    
    # 카테고리 필터 검증
    if 'category' in search_data and search_data['category']:
        valid_categories = [
            '한식', '중식', '일식', '양식', '치킨', '피자', '햄버거', 
            '분식', '카페', '디저트', '술집', '베이커리', '패스트푸드', '기타'
        ]
        if search_data['category'] not in valid_categories:
            errors.append(f"유효하지 않은 카테고리입니다.")
    
    # 가격 범위 검증
    if 'price_range' in search_data and search_data['price_range']:
        if not validate_price_range(search_data['price_range']):
            errors.append("유효하지 않은 가격 범위입니다.")
    
    # 거리 범위 검증
    if 'distance' in search_data and search_data['distance'] is not None:
        try:
            distance = float(search_data['distance'])
            if distance < 0 or distance > 50:  # 최대 50km
                errors.append("거리는 0-50km 사이여야 합니다.")
        except (ValueError, TypeError):
            errors.append("유효하지 않은 거리 값입니다.")
    
    # 정렬 기준 검증
    if 'sort_by' in search_data and search_data['sort_by']:
        valid_sorts = ['distance', 'rating', 'price', 'name', 'created_at', 'popularity']
        if search_data['sort_by'] not in valid_sorts:
            errors.append(f"유효하지 않은 정렬 기준입니다.")
    
    # 평점 필터 검증
    if 'min_rating' in search_data and search_data['min_rating'] is not None:
        if not validate_rating(search_data['min_rating']):
            errors.append("최소 평점은 0.0-5.0 사이여야 합니다.")
    
    return len(errors) == 0, errors

# =============================================================================
# 선호도 및 설정 관련 검증 함수들
# =============================================================================

def validate_preference_data(preference_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    사용자 선호도 데이터를 검증하는 함수
    
    Args:
        preference_data (dict): 검증할 선호도 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(preference_data, dict):
        return False, ["선호도 데이터는 딕셔너리 형태여야 합니다."]
    
    # 선호 요리 타입 검증
    if 'favorite_cuisines' in preference_data and preference_data['favorite_cuisines']:
        cuisines = preference_data['favorite_cuisines']
        if not isinstance(cuisines, list):
            errors.append("선호 요리 타입은 리스트 형태여야 합니다.")
        else:
            for i, cuisine in enumerate(cuisines):
                if not isinstance(cuisine, dict):
                    errors.append(f"요리 타입 {i+1}은 딕셔너리 형태여야 합니다.")
                    continue
                
                if 'type' not in cuisine or 'level' not in cuisine:
                    errors.append(f"요리 타입 {i+1}: 타입과 선호도 레벨은 필수입니다.")
                
                if 'level' in cuisine:
                    try:
                        level = int(cuisine['level'])
                        if not (1 <= level <= 5):
                            errors.append(f"요리 타입 {i+1}: 선호도 레벨은 1-5 사이여야 합니다.")
                    except (ValueError, TypeError):
                        errors.append(f"요리 타입 {i+1}: 유효하지 않은 선호도 레벨입니다.")
    
    # 매운맛 레벨 검증
    if 'spice_level' in preference_data and preference_data['spice_level']:
        valid_levels = ['mild', 'medium', 'hot', 'very_hot']
        if preference_data['spice_level'] not in valid_levels:
            errors.append(f"유효하지 않은 매운맛 레벨입니다. 사용 가능한 레벨: {', '.join(valid_levels)}")
    
    # 가격 민감도 검증
    if 'price_sensitivity' in preference_data and preference_data['price_sensitivity']:
        valid_levels = ['low', 'medium', 'high']
        if preference_data['price_sensitivity'] not in valid_levels:
            errors.append(f"유효하지 않은 가격 민감도입니다. 사용 가능한 레벨: {', '.join(valid_levels)}")
    
    # 분위기 선호도 검증
    if 'atmosphere_preference' in preference_data and preference_data['atmosphere_preference']:
        valid_atmospheres = ['casual', 'formal', 'romantic', 'family', 'business', 'quiet', 'lively']
        if preference_data['atmosphere_preference'] not in valid_atmospheres:
            errors.append(f"유효하지 않은 분위기 선호도입니다.")
    
    return len(errors) == 0, errors

# =============================================================================
# API 및 일반 검증 함수들
# =============================================================================

def validate_api_request_params(params: Dict[str, Any], required_params: List[str]) -> Tuple[bool, List[str]]:
    """
    API 요청 파라미터를 검증하는 함수
    
    Args:
        params (dict): 검증할 파라미터
        required_params (list): 필수 파라미터 목록
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(params, dict):
        return False, ["파라미터는 딕셔너리 형태여야 합니다."]
    
    # 필수 파라미터 검증
    for param in required_params:
        if param not in params or params[param] is None:
            errors.append(f"'{param}' 파라미터는 필수입니다.")
    
    return len(errors) == 0, errors

def validate_pagination_params(page_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    페이지네이션 파라미터를 검증하는 함수
    
    Args:
        page_data (dict): 검증할 페이지네이션 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(page_data, dict):
        return False, ["페이지네이션 데이터는 딕셔너리 형태여야 합니다."]
    
    # 페이지 번호 검증
    if 'page' in page_data and page_data['page'] is not None:
        if not validate_positive_integer(page_data['page']):
            errors.append("페이지 번호는 양의 정수여야 합니다.")
    
    # 페이지 크기 검증
    if 'page_size' in page_data and page_data['page_size'] is not None:
        try:
            page_size = int(page_data['page_size'])
            if not (1 <= page_size <= 100):
                errors.append("페이지 크기는 1-100 사이여야 합니다.")
        except (ValueError, TypeError):
            errors.append("유효하지 않은 페이지 크기입니다.")
    
    return len(errors) == 0, errors

def validate_file_upload(file_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    파일 업로드 데이터를 검증하는 함수
    
    Args:
        file_data (dict): 검증할 파일 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(file_data, dict):
        return False, ["파일 데이터는 딕셔너리 형태여야 합니다."]
    
    # 파일 크기 검증 (최대 5MB)
    if 'size' in file_data and file_data['size']:
        try:
            size = int(file_data['size'])
            if size > 5 * 1024 * 1024:  # 5MB
                errors.append("파일 크기는 5MB 이하여야 합니다.")
        except (ValueError, TypeError):
            errors.append("유효하지 않은 파일 크기입니다.")
    
    # 파일 타입 검증
    if 'type' in file_data and file_data['type']:
        valid_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        if file_data['type'] not in valid_types:
            errors.append(f"지원하지 않는 파일 타입입니다. 지원 타입: {', '.join(valid_types)}")
    
    # 파일명 검증
    if 'filename' in file_data and file_data['filename']:
        if not validate_string_length(file_data['filename'], 1, 255):
            errors.append("파일명은 1-255자 사이여야 합니다.")
    
    return len(errors) == 0, errors

# =============================================================================
# 유틸리티 함수들
# =============================================================================

def sanitize_input(input_str: str) -> str:
    """
    입력 문자열을 안전하게 정리하는 함수
    
    Args:
        input_str (str): 정리할 입력 문자열
    
    Returns:
        str: 정리된 문자열
    """
    if not isinstance(input_str, str):
        return ""
    
    # HTML 태그 제거
    input_str = re.sub(r'<[^>]+>', '', input_str)
    
    # 특수 문자 이스케이프
    input_str = input_str.replace('<', '&lt;').replace('>', '&gt;')
    input_str = input_str.replace('"', '&quot;').replace("'", '&#x27;')
    
    # 앞뒤 공백 제거
    input_str = input_str.strip()
    
    return input_str

def validate_all_params(data_type: str, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    데이터 타입에 따라 적절한 검증 함수를 호출하는 통합 함수
    
    Args:
        data_type (str): 데이터 타입
        data (dict): 검증할 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    validation_functions = {
        'user': validate_user_params,
        'restaurant': validate_restaurant_params,
        'review': validate_review_params,
        'recommendation': validate_recommendation_params,
        'location': validate_location_data,
        'menu': validate_menu_data,
        'search': validate_search_params,
        'preference': validate_preference_data,
        'pagination': validate_pagination_params,
        'chat': validate_chat_data,
        'file': validate_file_upload,
        'session': validate_session_data,
        'context': validate_context_data,
        'prompt': validate_prompt_data,
        'response': validate_response_data,
        'openai': validate_openai_request,
        'cache': validate_cache_data,
        'config': validate_config_data,
        'analytics': validate_analytics_data
    }
    
    if data_type not in validation_functions:
        return False, [f"지원하지 않는 데이터 타입입니다: {data_type}"]
    
    try:
        return validation_functions[data_type](data)
    except Exception as e:
        logger.error(f"검증 함수 실행 중 오류 발생: {e}")
        return False, [f"검증 중 오류가 발생했습니다: {str(e)}"]

# =============================================================================
# 추가 검증 함수들 (누락된 함수들)
# =============================================================================

def validate_chat_input(input_text: str) -> Tuple[bool, str]:
    """
    채팅 입력을 검증하는 함수 (validate_chat_message의 별칭)
    
    Args:
        input_text (str): 검증할 채팅 입력
    
    Returns:
        tuple: (유효성 여부, 오류 메시지)
    """
    return validate_chat_message(input_text)

def validate_session_data(session_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    세션 데이터를 검증하는 함수
    
    Args:
        session_data (dict): 검증할 세션 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(session_data, dict):
        return False, ["세션 데이터는 딕셔너리 형태여야 합니다."]
    
    # 세션 ID 검증
    if 'session_id' in session_data and session_data['session_id']:
        if not validate_string_length(session_data['session_id'], 1, 100):
            errors.append("세션 ID는 1-100자 사이여야 합니다.")
    
    # 사용자 ID 검증
    if 'user_id' in session_data and session_data['user_id'] is not None:
        if not validate_positive_integer(session_data['user_id']):
            errors.append("사용자 ID는 양의 정수여야 합니다.")
    
    return len(errors) == 0, errors

def validate_context_data(context_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    컨텍스트 데이터를 검증하는 함수
    
    Args:
        context_data (dict): 검증할 컨텍스트 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(context_data, dict):
        return False, ["컨텍스트 데이터는 딕셔너리 형태여야 합니다."]
    
    # 컨텍스트 타입 검증
    if 'context_type' in context_data and context_data['context_type']:
        valid_types = ['chat', 'recommendation', 'search', 'review', 'preference']
        if context_data['context_type'] not in valid_types:
            errors.append(f"유효하지 않은 컨텍스트 타입입니다. 사용 가능한 타입: {', '.join(valid_types)}")
    
    return len(errors) == 0, errors

def validate_prompt_data(prompt_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    프롬프트 데이터를 검증하는 함수
    
    Args:
        prompt_data (dict): 검증할 프롬프트 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(prompt_data, dict):
        return False, ["프롬프트 데이터는 딕셔너리 형태여야 합니다."]
    
    # 프롬프트 내용 검증
    if 'content' in prompt_data and prompt_data['content']:
        if not validate_string_length(prompt_data['content'], 1, 2000):
            errors.append("프롬프트 내용은 1-2000자 사이여야 합니다.")
    
    # 프롬프트 타입 검증
    if 'type' in prompt_data and prompt_data['type']:
        valid_types = ['system', 'user', 'assistant', 'function']
        if prompt_data['type'] not in valid_types:
            errors.append(f"유효하지 않은 프롬프트 타입입니다.")
    
    return len(errors) == 0, errors

def validate_response_data(response_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    응답 데이터를 검증하는 함수
    
    Args:
        response_data (dict): 검증할 응답 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(response_data, dict):
        return False, ["응답 데이터는 딕셔너리 형태여야 합니다."]
    
    # 응답 내용 검증
    if 'content' in response_data and response_data['content']:
        if not validate_string_length(response_data['content'], 1, 5000):
            errors.append("응답 내용은 1-5000자 사이여야 합니다.")
    
    # 응답 타입 검증
    if 'type' in response_data and response_data['type']:
        valid_types = ['text', 'recommendation', 'error', 'system']
        if response_data['type'] not in valid_types:
            errors.append(f"유효하지 않은 응답 타입입니다.")
    
    return len(errors) == 0, errors

def validate_openai_request(request_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    OpenAI API 요청 데이터를 검증하는 함수
    
    Args:
        request_data (dict): 검증할 요청 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(request_data, dict):
        return False, ["요청 데이터는 딕셔너리 형태여야 합니다."]
    
    # 모델 검증
    if 'model' in request_data and request_data['model']:
        valid_models = ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-4o']
        if request_data['model'] not in valid_models:
            errors.append(f"지원하지 않는 모델입니다.")
    
    # 메시지 검증
    if 'messages' in request_data and request_data['messages']:
        if not isinstance(request_data['messages'], list):
            errors.append("메시지는 리스트 형태여야 합니다.")
    
    # 온도 검증
    if 'temperature' in request_data and request_data['temperature'] is not None:
        try:
            temp = float(request_data['temperature'])
            if not (0.0 <= temp <= 2.0):
                errors.append("온도는 0.0-2.0 사이여야 합니다.")
        except (ValueError, TypeError):
            errors.append("유효하지 않은 온도 값입니다.")
    
    return len(errors) == 0, errors

def validate_cache_data(cache_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    캐시 데이터를 검증하는 함수
    
    Args:
        cache_data (dict): 검증할 캐시 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(cache_data, dict):
        return False, ["캐시 데이터는 딕셔너리 형태여야 합니다."]
    
    # 캐시 키 검증
    if 'key' in cache_data and cache_data['key']:
        if not validate_string_length(cache_data['key'], 1, 255):
            errors.append("캐시 키는 1-255자 사이여야 합니다.")
    
    # TTL 검증
    if 'ttl' in cache_data and cache_data['ttl'] is not None:
        try:
            ttl = int(cache_data['ttl'])
            if ttl < 0:
                errors.append("TTL은 0 이상이어야 합니다.")
        except (ValueError, TypeError):
            errors.append("유효하지 않은 TTL 값입니다.")
    
    return len(errors) == 0, errors

def validate_config_data(config_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    설정 데이터를 검증하는 함수
    
    Args:
        config_data (dict): 검증할 설정 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(config_data, dict):
        return False, ["설정 데이터는 딕셔너리 형태여야 합니다."]
    
    # API 키 검증
    if 'api_key' in config_data and config_data['api_key']:
        if not validate_string_length(config_data['api_key'], 10, 200):
            errors.append("API 키는 10-200자 사이여야 합니다.")
    
    # 환경 설정 검증
    if 'environment' in config_data and config_data['environment']:
        valid_envs = ['development', 'staging', 'production', 'testing']
        if config_data['environment'] not in valid_envs:
            errors.append(f"유효하지 않은 환경 설정입니다.")
    
    return len(errors) == 0, errors

def validate_analytics_data(analytics_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    분석 데이터를 검증하는 함수
    
    Args:
        analytics_data (dict): 검증할 분석 데이터
    
    Returns:
        tuple: (유효성 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if not isinstance(analytics_data, dict):
        return False, ["분석 데이터는 딕셔너리 형태여야 합니다."]
    
    # 이벤트 타입 검증
    if 'event_type' in analytics_data and analytics_data['event_type']:
        valid_events = ['page_view', 'search', 'recommendation', 'review', 'click']
        if analytics_data['event_type'] not in valid_events:
            errors.append(f"유효하지 않은 이벤트 타입입니다.")
    
    # 타임스탬프 검증
    if 'timestamp' in analytics_data and analytics_data['timestamp'] is not None:
        try:
            timestamp = int(analytics_data['timestamp'])
            if timestamp < 0:
                errors.append("타임스탬프는 0 이상이어야 합니다.")
        except (ValueError, TypeError):
            errors.append("유효하지 않은 타임스탬프입니다.")
    
    return len(errors) == 0, errors

# =============================================================================
# 빠른 검증 함수들 (자주 사용되는 간단한 검증)
# =============================================================================

def is_valid_id(value: Any) -> bool:
    """ID 값이 유효한지 빠르게 검증"""
    return validate_positive_integer(value)

def is_valid_email(email: str) -> bool:
    """이메일이 유효한지 빠르게 검증"""
    return validate_email(email)

def is_valid_phone(phone: str) -> bool:
    """전화번호가 유효한지 빠르게 검증"""
    return validate_phone_number(phone)

def is_valid_rating(rating: Any) -> bool:
    """평점이 유효한지 빠르게 검증"""
    return validate_rating(rating)

def is_valid_coordinates(lat: Any, lng: Any) -> bool:
    """좌표가 유효한지 빠르게 검증"""
    return validate_latitude(lat) and validate_longitude(lng)

def is_valid_text_length(text: str, max_length: int = 255) -> bool:
    """텍스트 길이가 유효한지 빠르게 검증"""
    return validate_string_length(text, 1, max_length)

def is_valid_price(price: Any) -> bool:
    """가격이 유효한지 빠르게 검증"""
    try:
        return int(price) >= 0
    except (ValueError, TypeError):
        return False