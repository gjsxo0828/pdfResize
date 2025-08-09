# 📚 PDF 분할 책 편집기 - 개발 로그

## 🎯 프로젝트 개요

125×175mm 책 출판을 위한 PDF 편집 프로그램 개발 프로젝트입니다. 가로 PDF를 분할하여 책의 올바른 페이지 순서로 변환하는 기능을 제공합니다.

## 📋 요구사항 분석

### 초기 요구사항
- 125×170mm 사이즈로 책 출판
- PDF 여백을 고려한 편집
- 웹 기반 인터페이스

### 수정된 요구사항
- 125×175mm 책 크기로 변경
- 가로 PDF를 가운데를 기준으로 분할
- 첫 페이지의 좌측은 마지막 페이지, 우측은 첫 페이지
- 양면 인쇄에 최적화된 페이지 순서

## 🛠️ 기술 스택 선택

### 선택된 기술
- **Python 3.8+**: 메인 프로그래밍 언어
- **Streamlit**: 웹 인터페이스 프레임워크
- **PyMuPDF (fitz)**: PDF 처리 및 분석
- **ReportLab**: PDF 생성
- **Pillow**: 이미지 처리
- **PyPDF2**: PDF 읽기/쓰기

### 기술 선택 이유
- **Streamlit**: 빠른 웹 인터페이스 개발 가능
- **PyMuPDF**: 고성능 PDF 처리 및 이미지 변환
- **ReportLab**: 정확한 PDF 생성 및 크기 조정

## 📁 파일 구조

```
pdfResize/
├── split_pdf_editor.py    # 메인 애플리케이션
├── requirements.txt       # 의존성 패키지
├── run.py                # 실행 스크립트
├── README.md             # 사용자 가이드
├── DEVELOPMENT_LOG.md    # 개발 로그 (이 파일)
└── venv/                 # 가상환경
```

## 🔄 개발 과정

### Phase 1: 기본 구조 설계
- **기간**: 초기 개발
- **내용**: 
  - 기본 PDF 편집기 구조 설계
  - 여백 설정 기능 구현
  - 웹 인터페이스 기본 구조

### Phase 2: 고급 기능 추가
- **기간**: 중간 개발
- **내용**:
  - PDF 분석 기능 추가
  - 크기 조정 모드 구현
  - 이미지 처리 최적화

### Phase 3: 분할 기능 구현
- **기간**: 최종 개발
- **내용**:
  - 가로 PDF 자동 분할 기능
  - 올바른 페이지 순서 구현
  - 양면 인쇄 최적화

## 🎨 핵심 기능 구현

### 1. PDF 분할 기능
```python
def split_landscape_page(self, page, split_direction='vertical'):
    """가로 페이지를 세로로 분할"""
    rect = page.rect
    
    if split_direction == 'vertical':
        # 세로로 분할 (좌우 분할)
        left_rect = fitz.Rect(0, 0, rect.width/2, rect.height)
        right_rect = fitz.Rect(rect.width/2, 0, rect.width, rect.height)
        
        left_page = page.get_pixmap(clip=left_rect)
        right_page = page.get_pixmap(clip=right_rect)
        
        return left_page, right_page
```

### 2. 페이지 순서 로직
```python
# 책 순서에 맞게 저장 (우측이 첫 페이지, 좌측이 마지막 페이지)
book_pages.append({
    'type': 'split_right',
    'pixmap': right_pix,
    'original_page': page_num
})
book_pages.append({
    'type': 'split_left', 
    'pixmap': left_pix,
    'original_page': page_num
})
```

### 3. 양면 인쇄 최적화
```python
# 4의 배수로 맞추어 양면 인쇄 순서 생성
if total_book_pages % 4 != 0:
    # 4의 배수가 되도록 빈 페이지 추가
    padding_pages = 4 - (total_book_pages % 4)
    for i in range(padding_pages):
        book_pages.append({
            'type': 'blank',
            'pixmap': None,
            'original_page': -1
        })
```

## 🐛 해결된 문제들

### 1. PyPDF2 모듈 오류
- **문제**: `ModuleNotFoundError: No module named 'PyPDF2'`
- **해결**: 가상환경에서 패키지 재설치
- **명령어**: `pip install PyPDF2==3.0.1`

### 2. 페이지 순서 문제
- **문제**: 분할된 페이지가 올바른 순서로 배치되지 않음
- **해결**: 책 인쇄 순서에 맞는 페이지 재배열 로직 구현
- **결과**: 첫 페이지 우측이 첫 페이지, 좌측이 마지막 페이지

### 3. 중복 파일 정리
- **문제**: 여러 버전의 편집기 파일이 존재
- **해결**: 기본 버전과 고급 버전 제거, 분할 버전만 유지
- **결과**: 코드베이스 단순화 및 유지보수성 향상

## 📊 성능 최적화

### 1. 이미지 처리 최적화
- 고해상도 렌더링: `fitz.Matrix(2, 2)`
- 이미지 리사이징: `Image.Resampling.LANCZOS`
- 임시 파일 자동 정리

### 2. 메모리 관리
- Pixmap을 이미지로 변환 후 즉시 메모리 해제
- 임시 파일 사용 후 자동 삭제
- 가비지 컬렉션 최적화

### 3. 사용자 경험 개선
- 실시간 PDF 분석 결과 표시
- 예상 페이지 수 계산
- 진행 상황 표시

## 🔧 설정 및 환경

### 개발 환경
- **OS**: Windows 10
- **Python**: 3.10
- **가상환경**: venv
- **패키지 관리**: pip

### 의존성 패키지
```
PyPDF2==3.0.1
reportlab==4.0.4
Pillow==10.0.1
streamlit==1.28.1
pdf2image==1.16.3
PyMuPDF==1.23.8
numpy==1.24.3
```

## 🚀 배포 및 실행

### 로컬 실행
```bash
# 가상환경 활성화
venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# 실행
python run.py
# 또는
streamlit run split_pdf_editor.py
```

### 웹 접속
- **로컬**: http://localhost:8501
- **네트워크**: http://192.168.35.16:8501

## 📈 향후 개선 계획

### 1. 기능 개선
- [ ] 페이지 번호 자동 추가 기능
- [ ] 다양한 책 크기 지원
- [ ] 배경색 설정 기능
- [ ] 이미지 품질 조정 옵션

### 2. 성능 최적화
- [ ] 대용량 PDF 처리 최적화
- [ ] 병렬 처리 구현
- [ ] 캐싱 시스템 추가

### 3. 사용자 경험 개선
- [ ] 드래그 앤 드롭 파일 업로드
- [ ] 실시간 미리보기
- [ ] 배치 처리 기능

### 4. 기술적 개선
- [ ] 단위 테스트 추가
- [ ] 에러 처리 강화
- [ ] 로깅 시스템 구현

## 🐛 알려진 이슈

### 1. PyPDF2 모듈 오류
- **상태**: 해결됨
- **해결책**: 가상환경에서 패키지 재설치

### 2. 대용량 PDF 처리
- **상태**: 모니터링 중
- **영향**: 메모리 사용량 증가 가능성

### 3. 특수 문자 처리
- **상태**: 테스트 필요
- **영향**: 한글 텍스트 처리 시 문제 가능성

## 📝 개발 팁

### 1. 가상환경 관리
```bash
# 가상환경 생성
python -m venv venv

# 활성화 (Windows)
venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 디버깅
```python
# PDF 분석 결과 확인
analysis = editor.analyze_pdf_content(pdf_path)
print(f"총 페이지: {analysis['total_pages']}")
print(f"가로 페이지: {analysis['is_landscape']}")
```

### 3. 성능 모니터링
```python
import time

start_time = time.time()
# 처리 로직
end_time = time.time()
print(f"처리 시간: {end_time - start_time:.2f}초")
```

## 📞 참고 자료

### 기술 문서
- [Streamlit 공식 문서](https://docs.streamlit.io/)
- [PyMuPDF 문서](https://pymupdf.readthedocs.io/)
- [ReportLab 문서](https://www.reportlab.com/docs/reportlab-userguide.pdf)

### 관련 프로젝트
- [PDF 처리 라이브러리 비교](https://github.com/topics/pdf-processing)
- [책 인쇄 표준](https://www.iso.org/standard/74528.html)

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

---

**마지막 업데이트**: 2025년 8월 8일
**개발자**: AI Assistant
**버전**: 1.0.0 