#!/usr/bin/env python3
"""
OpenAI 라이브러리 완전 재설치 스크립트
proxies 오류를 완전히 해결합니다.
"""

import subprocess
import sys
import os
import shutil

def run_command(command, description):
    """명령어 실행 및 결과 출력"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} 완료")
            return True
        else:
            print(f"❌ {description} 실패: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} 오류: {e}")
        return False

def clear_pip_cache():
    """pip 캐시 완전 정리"""
    print("\n🧹 pip 캐시 정리 중...")
    
    # pip 캐시 디렉토리 찾기
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'cache', 'dir'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            cache_dir = result.stdout.strip()
            print(f"   캐시 디렉토리: {cache_dir}")
            
            # 캐시 정리
            run_command(f"{sys.executable} -m pip cache purge", "pip 캐시 정리")
        else:
            print("   pip 캐시 디렉토리를 찾을 수 없습니다.")
    except Exception as e:
        print(f"   캐시 정리 중 오류: {e}")

def uninstall_openai_completely():
    """OpenAI 라이브러리 완전 제거"""
    print("\n🗑️  OpenAI 라이브러리 완전 제거 중...")
    
    # 여러 버전의 openai 제거 시도
    packages_to_remove = ['openai', 'openai-python', 'openai-api']
    
    for package in packages_to_remove:
        run_command(f"{sys.executable} -m pip uninstall {package} -y", f"{package} 제거")
    
    # 강제 제거 시도
    run_command(f"{sys.executable} -m pip uninstall openai -y --break-system-packages", "OpenAI 강제 제거")

def install_compatible_openai():
    """호환되는 OpenAI 라이브러리 설치"""
    print("\n📦 호환되는 OpenAI 라이브러리 설치 중...")
    
    # 안정적인 버전부터 시도
    versions_to_try = [
        "openai==1.3.7",  # 안정적인 버전
        "openai==1.3.0",  # 더 안정적인 버전
        "openai==0.28.1", # 구 버전 (API 방식 다름)
    ]
    
    for version in versions_to_try:
        print(f"\n   {version} 설치 시도 중...")
        if run_command(f"{sys.executable} -m pip install {version}", f"{version} 설치"):
            print(f"✅ {version} 설치 성공!")
            return version
        else:
            print(f"❌ {version} 설치 실패, 다음 버전 시도...")
    
    print("❌ 모든 OpenAI 버전 설치 실패")
    return None

def test_openai_installation():
    """OpenAI 설치 테스트"""
    print("\n🧪 OpenAI 설치 테스트 중...")
    
    try:
        import openai
        print(f"✅ OpenAI 버전: {openai.__version__}")
        
        # 클라이언트 초기화 테스트
        try:
            if hasattr(openai, 'OpenAI'):
                # v1.x 방식
                client = openai.OpenAI(api_key="test-key")
                print("✅ OpenAI v1.x 클라이언트 생성 성공")
                return "v1"
            else:
                # v0.x 방식
                openai.api_key = "test-key"
                print("✅ OpenAI v0.x 설정 성공")
                return "v0"
        except Exception as e:
            if "proxies" in str(e):
                print("❌ 여전히 proxies 오류 발생")
                return None
            else:
                print(f"✅ 다른 오류이지만 proxies 문제는 해결됨: {e}")
                return "unknown"
    
    except ImportError as e:
        print(f"❌ OpenAI 임포트 실패: {e}")
        return None

def main():
    """메인 수정 함수"""
    print("🔧 OpenAI 라이브러리 proxies 오류 수정 시작")
    print("=" * 60)
    
    # 1. 현재 상태 확인
    print("📋 현재 환경 확인")
    print(f"   Python 경로: {sys.executable}")
    print(f"   작업 디렉토리: {os.getcwd()}")
    
    # 2. pip 캐시 정리
    clear_pip_cache()
    
    # 3. OpenAI 완전 제거
    uninstall_openai_completely()
    
    # 4. 호환되는 버전 설치
    installed_version = install_compatible_openai()
    
    if not installed_version:
        print("\n❌ OpenAI 라이브러리 설치에 실패했습니다.")
        print("수동으로 다음 명령어를 시도해보세요:")
        print("   pip install openai==1.3.7")
        return False
    
    # 5. 설치 테스트
    api_version = test_openai_installation()
    
    if api_version:
        print(f"\n🎉 OpenAI 라이브러리 수정 완료! (API 버전: {api_version})")
        print("\n다음 단계:")
        print("1. python test_openai.py 재실행")
        print("2. .env 파일에 OPENAI_API_KEY 설정 확인")
        return True
    else:
        print("\n❌ 여전히 문제가 있습니다. 수동 해결이 필요합니다.")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)