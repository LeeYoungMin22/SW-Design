# scripts/backup_database.py
"""
데이터베이스 백업 스크립트
정기적인 데이터베이스 백업과 복원을 위한 스크립트
"""

import os
import sys
import sqlite3
import shutil
import gzip
import json
from datetime import datetime
import argparse

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.config.settings import DevelopmentConfig

class DatabaseBackupManager:
    """데이터베이스 백업 관리자"""
    
    def __init__(self, db_path=None, backup_dir=None):
        self.db_path = db_path or DevelopmentConfig.DATABASE_PATH
        self.backup_dir = backup_dir or os.path.join(project_root, 'backups')
        
        # 백업 디렉토리 생성
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_backup(self, compress=True, include_data=True):
        """
        데이터베이스 백업 생성
        
        Args:
            compress (bool): 압축 여부
            include_data (bool): 데이터 포함 여부
            
        Returns:
            str: 백업 파일 경로
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"foodi_backup_{timestamp}.db"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        print(f"📦 데이터베이스 백업을 생성합니다: {backup_filename}")
        
        try:
            if include_data:
                # 전체 데이터베이스 복사
                shutil.copy2(self.db_path, backup_path)
            else:
                # 스키마만 백업
                self._backup_schema_only(backup_path)
            
            # 압축 옵션
            if compress:
                compressed_path = self._compress_backup(backup_path)
                os.remove(backup_path)  # 원본 삭제
                backup_path = compressed_path
            
            # 백업 메타데이터 생성
            self._create_backup_metadata(backup_path, include_data, compress)
            
            file_size = os.path.getsize(backup_path)
            print(f"✅ 백업 완료: {backup_path} ({file_size:,} bytes)")
            
            return backup_path
            
        except Exception as e:
            print(f"❌ 백업 생성 실패: {e}")
            if os.path.exists(backup_path):
                os.remove(backup_path)
            raise
    
    def restore_backup(self, backup_path, confirm=True):
        """
        백업에서 데이터베이스 복원
        
        Args:
            backup_path (str): 백업 파일 경로
            confirm (bool): 복원 확인 여부
            
        Returns:
            bool: 복원 성공 여부
        """
        if not os.path.exists(backup_path):
            print(f"❌ 백업 파일이 존재하지 않습니다: {backup_path}")
            return False
        
        if confirm:
            response = input(f"⚠️ 현재 데이터베이스를 '{backup_path}' 백업으로 복원하시겠습니까? (y/N): ")
            if response.lower() != 'y':
                print("복원이 취소되었습니다.")
                return False
        
        print(f"🔄 데이터베이스를 복원합니다: {backup_path}")
        
        try:
            # 현재 데이터베이스 백업 (복원 전)
            current_backup = self._create_emergency_backup()
            print(f"📋 현재 DB 임시 백업: {current_backup}")
            
            # 압축된 백업인지 확인
            if backup_path.endswith('.gz'):
                temp_path = self._decompress_backup(backup_path)
                restore_source = temp_path
            else:
                restore_source = backup_path
            
            # 데이터베이스 복원
            shutil.copy2(restore_source, self.db_path)
            
            # 임시 파일 정리
            if backup_path.endswith('.gz'):
                os.remove(temp_path)
            
            # 복원된 데이터베이스 검증
            if self._verify_database():
                print("✅ 데이터베이스 복원이 완료되었습니다.")
                return True
            else:
                # 복원 실패 시 원본 복구
                shutil.copy2(current_backup, self.db_path)
                print("❌ 복원 검증 실패. 원본 데이터베이스를 복구했습니다.")
                return False
                
        except Exception as e:
            print(f"❌ 복원 실패: {e}")
            # 오류 발생 시 원본 복구 시도
            try:
                if current_backup and os.path.exists(current_backup):
                    shutil.copy2(current_backup, self.db_path)
                    print("🔄 원본 데이터베이스를 복구했습니다.")
            except:
                print("⚠️ 원본 데이터베이스 복구에도 실패했습니다.")
            return False
        finally:
            # 임시 백업 파일 정리
            if current_backup and os.path.exists(current_backup):
                os.remove(current_backup)
    
    def list_backups(self):
        """
        백업 목록 조회
        
        Returns:
            list: 백업 파일 정보 리스트
        """
        backups = []
        
        for filename in os.listdir(self.backup_dir):
            if filename.startswith('foodi_backup_'):
                file_path = os.path.join(self.backup_dir, filename)
                
                backup_info = {
                    'filename': filename,
                    'path': file_path,
                    'size': os.path.getsize(file_path),
                    'created': datetime.fromtimestamp(os.path.getctime(file_path)),
                    'compressed': filename.endswith('.gz')
                }
                
                # 메타데이터 로드
                metadata = self._load_backup_metadata(file_path)
                if metadata:
                    backup_info.update(metadata)
                
                backups.append(backup_info)
        
        # 생성 시간 기준 내림차순 정렬
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        return backups
    
    def cleanup_old_backups(self, keep_count=10):
        """
        오래된 백업 파일 정리
        
        Args:
            keep_count (int): 보관할 백업 개수
        """
        backups = self.list_backups()
        
        if len(backups) <= keep_count:
            print(f"✅ 정리할 백업이 없습니다. (현재 {len(backups)}개)")
            return
        
        # 오래된 백업들 삭제
        to_delete = backups[keep_count:]
        deleted_count = 0
        
        for backup in to_delete:
            try:
                os.remove(backup['path'])
                
                # 메타데이터 파일도 삭제
                metadata_path = backup['path'] + '.meta'
                if os.path.exists(metadata_path):
                    os.remove(metadata_path)
                
                deleted_count += 1
                print(f"🗑️ 삭제됨: {backup['filename']}")
                
            except Exception as e:
                print(f"❌ 삭제 실패 ({backup['filename']}): {e}")
        
        print(f"✅ {deleted_count}개의 오래된 백업을 정리했습니다.")
    
    def _backup_schema_only(self, backup_path):
        """스키마만 백업"""
        source_conn = sqlite3.connect(self.db_path)
        backup_conn = sqlite3.connect(backup_path)
        
        try:
            # 스키마 덤프
            for line in source_conn.iterdump():
                if not line.startswith('INSERT'):
                    backup_conn.execute(line)
            
            backup_conn.commit()
            
        finally:
            source_conn.close()
            backup_conn.close()
    
    def _compress_backup(self, backup_path):
        """백업 파일 압축"""
        compressed_path = backup_path + '.gz'
        
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return compressed_path
    
    def _decompress_backup(self, compressed_path):
        """백업 파일 압축 해제"""
        temp_path = compressed_path.replace('.gz', '.temp')
        
        with gzip.open(compressed_path, 'rb') as f_in:
            with open(temp_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return temp_path
    
    def _create_backup_metadata(self, backup_path, include_data, compressed):
        """백업 메타데이터 생성"""
        metadata = {
            'created_at': datetime.now().isoformat(),
            'original_db_path': self.db_path,
            'include_data': include_data,
            'compressed': compressed,
            'file_size': os.path.getsize(backup_path),
            'version': '1.0'
        }
        
        # 데이터베이스 통계 추가
        if include_data:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM restaurants")
                metadata['restaurant_count'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM reviews")
                metadata['review_count'] = cursor.fetchone()[0]
                
                conn.close()
            except Exception:
                pass
        
        metadata_path = backup_path + '.meta'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def _load_backup_metadata(self, backup_path):
        """백업 메타데이터 로드"""
        metadata_path = backup_path + '.meta'
        
        if not os.path.exists(metadata_path):
            return None
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def _create_emergency_backup(self):
        """응급 백업 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        emergency_backup = os.path.join(self.backup_dir, f"emergency_{timestamp}.db")
        shutil.copy2(self.db_path, emergency_backup)
        return emergency_backup
    
    def _verify_database(self):
        """데이터베이스 무결성 검증"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 기본 테이블 존재 확인
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name IN ('restaurants', 'reviews')
            """)
            
            table_count = cursor.fetchone()[0]
            conn.close()
            
            return table_count >= 2
            
        except Exception:
            return False

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='FOODI 데이터베이스 백업 관리')
    parser.add_argument('action', choices=['backup', 'restore', 'list', 'cleanup'], 
                       help='수행할 작업')
    parser.add_argument('--file', '-f', help='백업 파일 경로 (restore 시 필요)')
    parser.add_argument('--no-compress', action='store_true', help='압축하지 않음')
    parser.add_argument('--schema-only', action='store_true', help='스키마만 백업')
    parser.add_argument('--keep', type=int, default=10, help='보관할 백업 개수')
    parser.add_argument('--yes', '-y', action='store_true', help='확인 없이 실행')
    
    args = parser.parse_args()
    
    backup_manager = DatabaseBackupManager()
    
    try:
        if args.action == 'backup':
            backup_path = backup_manager.create_backup(
                compress=not args.no_compress,
                include_data=not args.schema_only
            )
            print(f"백업이 생성되었습니다: {backup_path}")
            
        elif args.action == 'restore':
            if not args.file:
                print("❌ 복원할 백업 파일을 지정해주세요. (--file 옵션)")
                sys.exit(1)
            
            success = backup_manager.restore_backup(args.file, confirm=not args.yes)
            if not success:
                sys.exit(1)
                
        elif args.action == 'list':
            backups = backup_manager.list_backups()
            
            if not backups:
                print("백업 파일이 없습니다.")
            else:
                print("📋 백업 목록:")
                print("-" * 80)
                for backup in backups:
                    compressed_indicator = " (압축됨)" if backup.get('compressed') else ""
                    data_indicator = " (스키마만)" if not backup.get('include_data', True) else ""
                    
                    print(f"{backup['filename']}{compressed_indicator}{data_indicator}")
                    print(f"  생성일: {backup['created'].strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"  크기: {backup['size']:,} bytes")
                    
                    if backup.get('restaurant_count') is not None:
                        print(f"  식당: {backup['restaurant_count']:,}개, "
                              f"리뷰: {backup.get('review_count', 0):,}개")
                    print()
                    
        elif args.action == 'cleanup':
            backup_manager.cleanup_old_backups(keep_count=args.keep)
            
    except KeyboardInterrupt:
        print("\n⏹️ 작업이 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()