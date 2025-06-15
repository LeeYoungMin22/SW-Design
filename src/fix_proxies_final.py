#!/usr/bin/env python3
"""
OpenAI Proxies 오류 완전 해결 스크립트
구 버전과 새 버전을 모두 시도합니다.
"""

import subprocess
import sys
import os
import json

def run_command(command, description, silent=False):
    """명령어 실행"""
    if not silent:
        print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            if not silent:
                print(f"✅ {description} 완료")
            return True, result.stdout
        else:
            if not silent:
                print(f"❌ {description} 실패: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        if not silent:
            print(f"❌ {description} 오류: {e}")
        return False, str(e)

def test_openai_version(version_info):
    """특정 OpenAI 버전 테스트"""
    print(f"\n🧪 OpenAI {version_info['version']} 테스트 중...")
    
    try:
        if version_info['api_style'] == 'v0':
            # v0.x 방식 테스트
            import openai
            openai.api_key = "test-key"
            print(f"✅ OpenAI {version_info['version']} (v0.x API) 초기화 성공")
            return True
        else:
            # v1.x 방식 테스트
            import openai
            try:
                client = openai.OpenAI(api_key="test-key")
                print(f"✅ OpenAI {version_info['version']} (v1.x API) 초기화 성공")
                return True
            except Exception as e:
                if "proxies" in str(e):
                    print(f"❌ OpenAI {version_info['version']} proxies 오류: {e}")
                    return False
                else:
                    print(f"✅ OpenAI {version_info['version']} 다른 오류 (proxies 아님): {e}")
                    return True
    except Exception as e:
        print(f"❌ OpenAI {version_info['version']} 테스트 실패: {e}")
        return False

def install_and_test_version(version_info):
    """특정 버전 설치 및 테스트"""
    print(f"\n📦 OpenAI {version_info['version']} 설치 시도 중...")
    
    # 기존 버전 제거
    run_command(f"{sys.executable} -m pip uninstall openai -y", "기존 OpenAI 제거", silent=True)
    
    # 새 버전 설치
    success, output = run_command(
        f"{sys.executable} -m pip install openai=={version_info['version']}", 
        f"OpenAI {version_info['version']} 설치"
    )
    
    if not success:
        return False
    
    # 설치된 버전 확인
    try:
        import importlib
        if 'openai' in sys.modules:
            importlib.reload(sys.modules['openai'])
        else:
            import openai
        
        actual_version = openai.__version__
        print(f"   설치된 버전: {actual_version}")
        
        # 테스트
        return test_openai_version(version_info)
        
    except Exception as e:
        print(f"❌ 버전 확인 실패: {e}")
        return False

def clear_python_cache():
    """Python 캐시 정리"""
    print("\n🧹 Python 캐시 정리 중...")
    
    # __pycache__ 폴더 삭제
    run_command("find . -type d -name '__pycache__' -exec rm -rf {} +", "pycache 정리", silent=True)
    
    # .pyc 파일 삭제
    run_command("find . -name '*.pyc' -delete", "pyc 파일 정리", silent=True)
    
    # pip 캐시 정리
    run_command(f"{sys.executable} -m pip cache purge", "pip 캐시 정리", silent=True)
    
    print("✅ 캐시 정리 완료")

def check_environment():
    """환경 확인"""
    print("🔍 환경 확인 중...")
    
    # Python 버전
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"   Python 버전: {python_version}")
    
    # 가상환경 확인
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("   가상환경: 활성화됨 ✅")
    else:
        print("   가상환경: 시스템 Python ⚠️")
    
    # 작업 디렉토리
    print(f"   작업 디렉토리: {os.getcwd()}")
    
    return True

def main():
    """메인 해결 함수"""
    print("🔧 OpenAI Proxies 오류 완전 해결 시작")
    print("=" * 60)
    
    # 환경 확인
    check_environment()
    
    # 캐시 정리
    clear_python_cache()
    
    # 테스트할 버전들 (안정적인 순서대로)
    versions_to_try = [
        {
            'version': '0.28.1',
            'api_style': 'v0',
            'description': '구 버전 (매우 안정적, proxies 문제 없음)'
        },
        {
            'version': '1.3.0', 
            'api_style': 'v1',
            'description': '새 버전 (안정적)'
        },
        {
            'version': '1.2.0',
            'api_style': 'v1', 
            'description': '더 안정적인 새 버전'
        },
        {
            'version': '1.1.0',
            'api_style': 'v1',
            'description': '초기 v1 버전'
        }
    ]
    
    successful_version = None
    
    for version_info in versions_to_try:
        print(f"\n{'='*50}")
        print(f"시도 중: OpenAI {version_info['version']}")
        print(f"설명: {version_info['description']}")
        print(f"{'='*50}")
        
        if install_and_test_version(version_info):
            successful_version = version_info
            print(f"\n🎉 성공! OpenAI {version_info['version']}이 정상 작동합니다!")
            break
        else:
            print(f"\n❌ OpenAI {version_info['version']} 실패, 다음 버전 시도...")
    
    if successful_version:
        print(f"\n{'='*60}")
        print(f"✅ 해결 완료!")
        print(f"   성공한 버전: OpenAI {successful_version['version']}")
        print(f"   API 스타일: {successful_version['api_style']}")
        print(f"   설명: {successful_version['description']}")
        
        # 성공한 버전 정보 저장
        config = {
            'openai_version': successful_version['version'],
            'api_style': successful_version['api_style'],
            'solved_at': str(os.times())
        }
        
        with open('.openai_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n다음 단계:")
        print(f"1. python test_openai.py 실행하여 테스트")
        print(f"2. .env 파일에 OPENAI_API_KEY 설정")
        print(f"3. python app.py 로 서버 시작")
        
        if successful_version['api_style'] == 'v0':
            print(f"\n💡 참고: v0.x API를 사용하므로 일부 기능이 다를 수 있습니다.")
        
        return True
    else:
        print(f"\n❌ 모든 버전에서 실패했습니다.")
        print(f"\n🔧 수동 해결 방법:")
        print(f"1. 가상환경 재생성:")
        print(f"   deactivate")
        print(f"   rm -rf foodi_chatbot")
        print(f"   python -m venv foodi_chatbot")
        print(f"   source foodi_chatbot/bin/activate")
        print(f"   pip install openai==0.28.1")
        print(f"")
        print(f"2. 시스템 Python 사용:")
        print(f"   pip install --user openai==0.28.1")
        print(f"")
        print(f"3. 다른 Python 버전 시도:")
        print(f"   python3.8 -m pip install openai==0.28.1")
        
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)