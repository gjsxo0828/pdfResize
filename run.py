#!/usr/bin/env python3
"""
PDF 분할 편집기 실행 스크립트
"""

import subprocess
import sys
import os

def check_dependencies():
    """필요한 패키지가 설치되어 있는지 확인"""
    try:
        import streamlit
        import PyPDF2
        import reportlab
        import PIL
        import fitz
        return True
    except ImportError as e:
        print(f"❌ 필요한 패키지가 설치되지 않았습니다: {e}")
        print("다음 명령어로 패키지를 설치하세요:")
        print("pip install -r requirements.txt")
        return False

def main():
    print("📚 PDF 분할 편집기")
    print("=" * 50)
    
    # 의존성 확인
    if not check_dependencies():
        return
    
    print("🚀 PDF 분할 편집기를 실행합니다...")
    print("웹 브라우저에서 http://localhost:8501 로 접속하세요.")
    print("종료하려면 Ctrl+C를 누르세요.")
    print("-" * 50)
    
    try:
        # Streamlit 실행
        subprocess.run([sys.executable, "-m", "streamlit", "run", "split_pdf_editor.py"])
    except KeyboardInterrupt:
        print("\n👋 프로그램을 종료합니다.")
    except Exception as e:
        print(f"❌ 실행 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main() 