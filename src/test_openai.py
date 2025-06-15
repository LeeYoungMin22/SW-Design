#!/usr/bin/env python3
"""
FOODI OpenAI 연동 테스트 스크립트
환경 설정 및 API 연결을 확인합니다.
"""

import os
import sys
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

def test_environment():
    """환경변수 설정 테스트"""
    print("🔍 환경변수 확인 중...")
    
    # .env 파일 로드
    load_dotenv()
    
    # 필수 환경변수 확인 (키: 환경변수명, 값: 설명)
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API 키',
        'OPENAI_MODEL': 'OpenAI 모델'
    }
    
    missing_vars = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            if var == 'OPENAI_API_KEY':
                # API 키는 마스킹해서 표시
                masked = value[:8] + '*' * (len(value) - 12) + value[-4:] if len(value) > 12 else '****'
                print(f"✅ {description}: {masked}")
            else:
                print(f"✅ {description}: {value}")
        else:
            print(f"❌ {description}: 설정되지 않음")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  다음 환경변수를 .env 파일에 설정해주세요:")
        for var in missing_vars:
            print(f"   {var}=your_value_here")
        return False
    
    return True

def test_dependencies():
    """필수 패키지 설치 확인"""
    print("\n📦 패키지 의존성 확인 중...")
    
    required_packages = {
        'openai': 'OpenAI Python 클라이언트',
        'flask': 'Flask 웹 프레임워크',
        'dotenv': '환경변수 로더',
        'flask_cors': 'Flask CORS 확장'
    }
    
    missing_packages = []
    
    for package, description in required_packages.items():
        try:
            if package == 'dotenv':
                from dotenv import load_dotenv
            elif package == 'flask_cors':
                import flask_cors
            else:
                __import__(package)
            print(f"✅ {description}: 설치됨")
        except ImportError:
            print(f"❌ {description}: 미설치")
            if package == 'dotenv':
                missing_packages.append('python-dotenv')
            elif package == 'flask_cors':
                missing_packages.append('flask-cors')
            else:
                missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  다음 패키지를 설치해주세요:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True

def test_openai_connection():
    """OpenAI API 연결 테스트"""
    print("\n🤖 OpenAI API 연결 테스트 중...")
    
    try:
        from openai import OpenAI
        
        # OpenAI 클라이언트 초기화 (v1.x 방식)
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
            return False
        
        client = OpenAI(api_key=api_key)
        
        # 간단한 테스트 요청
        model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        
        print(f"   사용 모델: {model}")
        print("   테스트 요청 전송 중...")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "당신은 도움이 되는 AI 어시스턴트입니다."},
                {"role": "user", "content": "안녕하세요! 간단한 연결 테스트입니다."}
            ],
            max_tokens=30,
            temperature=0.1
        )
        
        content = response.choices[0].message.content
        print(f"✅ OpenAI API 연결 성공!")
        print(f"   응답: {content[:50]}{'...' if len(content) > 50 else ''}")
        
        # 토큰 사용량 확인
        usage = response.usage
        print(f"   토큰 사용량: {usage.total_tokens} (입력: {usage.prompt_tokens}, 출력: {usage.completion_tokens})")
        
        return True
        
    except ImportError as e:
        print(f"❌ OpenAI 라이브러리 임포트 실패: {str(e)}")
        print("   💡 다음 명령어로 설치해주세요: pip install openai==1.6.1")
        return False
        
    except Exception as e:
        print(f"❌ OpenAI API 연결 실패: {str(e)}")
        
        # 일반적인 오류 원인 안내
        error_str = str(e).lower()
        if "authentication" in error_str or "invalid api key" in error_str:
            print("   💡 API 키가 올바르지 않습니다. OPENAI_API_KEY를 확인해주세요.")
            print("   💡 https://platform.openai.com/api-keys 에서 새 API 키를 생성하세요.")
        elif "insufficient_quota" in error_str or "billing" in error_str:
            print("   💡 OpenAI 계정의 크레딧이 부족합니다.")
            print("   💡 https://platform.openai.com/account/billing 에서 결제 정보를 확인하세요.")
        elif "rate_limit" in error_str:
            print("   💡 API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
        elif "model" in error_str:
            print(f"   💡 모델 '{model}'에 접근할 수 없습니다. gpt-3.5-turbo를 시도해보세요.")
        else:
            print("   💡 네트워크 연결을 확인하고 다시 시도해주세요.")
        
        return False

def test_foodi_service():
    """FOODI 서비스 클래스 테스트"""
    print("\n🍽️  FOODI 서비스 클래스 테스트 중...")
    
    try:
        # 경로 설정
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # 먼저 모듈을 임포트해서 내용 확인
        try:
            import app.services.openai_service as openai_module
            print("✅ openai_service 모듈 임포트 성공")
            
            # 모듈에 있는 클래스들 확인
            available_classes = []
            for attr_name in dir(openai_module):
                attr = getattr(openai_module, attr_name)
                if isinstance(attr, type) and not attr_name.startswith('_'):
                    available_classes.append(attr_name)
            
            print(f"   사용 가능한 클래스들: {available_classes}")
            
            # OpenAIService 클래스 찾기
            if 'OpenAIService' in available_classes:
                from app.services.openai_service import OpenAIService
                print("✅ OpenAIService 클래스 임포트 성공")
            else:
                # 비슷한 이름의 클래스 찾기
                similar_classes = [cls for cls in available_classes if 'openai' in cls.lower() or 'service' in cls.lower()]
                if similar_classes:
                    print(f"❌ OpenAIService를 찾을 수 없습니다. 비슷한 클래스: {similar_classes}")
                    print(f"   💡 다음 중 하나를 사용해보세요:")
                    for cls in similar_classes:
                        print(f"      from app.services.openai_service import {cls}")
                else:
                    print(f"❌ OpenAIService 클래스가 정의되지 않았습니다.")
                    print(f"   💡 app/services/openai_service.py 파일에 다음과 같이 클래스를 정의하세요:")
                    print(f"      class OpenAIService:")
                    print(f"          def __init__(self):")
                    print(f"              pass")
                return False
                
        except ImportError as e:
            print(f"❌ openai_service 모듈 임포트 실패: {str(e)}")
            return False
        except SyntaxError as e:
            print(f"❌ openai_service.py 파일에 문법 오류: {str(e)}")
            print(f"   💡 파일의 {e.lineno}번째 줄을 확인해주세요: {e.text}")
            return False
        
        # 서비스 초기화 시도
        print("   OpenAI 서비스 초기화 중...")
        service = OpenAIService()
        print(f"✅ OpenAIService 초기화 성공")
        print(f"   등록된 맛집 수: {len(service.restaurant_database)}")
        
        # 샘플 맛집 정보 출력
        if service.restaurant_database:
            sample_restaurant = service.restaurant_database[0]
            print(f"   첫 번째 맛집: {sample_restaurant['name']} ({sample_restaurant['category']})")
        
        # 테스트 추천 요청
        test_message = "가족과 함께 갈 수 있는 한식당 추천해줘"
        print(f"\n🧪 테스트 질문: '{test_message}'")
        print("   추천 생성 중... (OpenAI API 호출)")
        
        result = service.get_restaurant_recommendation(test_message)
        
        if result['success']:
            print("✅ 추천 생성 성공!")
            print(f"   응답 길이: {len(result['response'])} 글자")
            print(f"   응답 미리보기: {result['response'][:100]}{'...' if len(result['response']) > 100 else ''}")
            print(f"   추천 맛집 수: {len(result['restaurants'])}")
            
            if result['restaurants']:
                first_restaurant = result['restaurants'][0]
                print(f"   첫 번째 추천: {first_restaurant['name']} ({first_restaurant.get('category', 'N/A')})")
                print(f"   평점: {first_restaurant.get('rating', 'N/A')}")
            
            # 분석 결과 출력
            analysis = result.get('analysis', {})
            print(f"   분석된 카테고리: {analysis.get('category', 'N/A')}")
            print(f"   분석된 상황: {analysis.get('situation', 'N/A')}")
            
        else:
            print(f"❌ 추천 생성 실패: {result.get('error', '알 수 없는 오류')}")
            if 'fallback' in str(result.get('error', '')).lower():
                print("   💡 OpenAI API 오류로 인해 기본 시스템이 작동했습니다.")
                print("   💡 .env 파일의 OPENAI_API_KEY를 확인해주세요.")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FOODI 서비스 테스트 실패: {str(e)}")
        
        # 구체적인 오류 원인 분석
        error_str = str(e).lower()
        if "no module named" in error_str:
            print("   💡 모듈 임포트 오류입니다. 프로젝트 구조를 확인해주세요.")
        elif "openai" in error_str:
            print("   💡 OpenAI 관련 오류입니다. API 키와 네트워크를 확인해주세요.")
        elif "file not found" in error_str or "no such file" in error_str:
            print("   💡 파일 경로 오류입니다. 프로젝트 구조를 확인해주세요.")
        
        print(f"   디버깅 정보: 현재 작업 디렉토리 = {os.getcwd()}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 FOODI OpenAI 연동 테스트 시작")
    print("=" * 50)
    
    tests = [
        ("환경변수 설정", test_environment),
        ("패키지 의존성", test_dependencies),
        ("OpenAI API 연결", test_openai_connection),
        ("FOODI 서비스", test_foodi_service)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name} 테스트")
        print("-" * 30)
        
        if test_func():
            passed += 1
        else:
            print(f"\n⚠️  {test_name} 테스트 실패. 설정을 확인해주세요.")
    
    print("\n" + "=" * 50)
    print(f"🏁 테스트 완료: {passed}/{total} 통과")
    
    if passed == total:
        print("🎉 모든 테스트 통과! FOODI 시스템이 준비되었습니다.")
        print("\n다음 명령어로 서버를 시작하세요:")
        print("   python app.py")
    else:
        print("❌ 일부 테스트 실패. 위의 오류를 해결하고 다시 시도해주세요.")
        sys.exit(1)

if __name__ == "__main__":
    main()