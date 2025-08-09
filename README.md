# 📚 책 출판용 PDF 편집기

A4 가로 레이아웃 PDF를 125x175mm 책 출판용으로 분할하고 편집하는 Streamlit 기반 웹 애플리케이션

## 🎯 프로젝트 목적

- A4 가로 페이지를 좌우로 분할하여 책 페이지로 변환
- 125x175mm 책 규격에 맞는 여백 및 레이아웃 조정
- 출판업체 전달용 고품질 PDF 생성

## ✨ 주요 기능

### 📄 PDF 처리
- **자동 분할**: A4 가로 페이지를 좌우 2개 페이지로 분할
- **페이지 순서**: 1234 순서 또는 2341 반복 패턴 지원
- **첫 페이지 제어**: 좌측/우측 페이지부터 시작 선택

### 📐 레이아웃 조정
- **여백 설정**: 위/아래/바깥쪽/안쪽 여백 독립 조정
- **크기 조정**: 홀수/짝수 페이지별 축소 비율 설정
- **위치 조정**: 좌우/상하 이동 오프셋 적용
- **여백 가이드**: 빨간색(홀수)/파란색(짝수) 가이드 선 표시

### 🔍 미리보기
- **실시간 미리보기**: 설정 변경 시 즉시 반영
- **페이지네이션**: 4페이지 단위 미리보기 탐색
- **원본 페이지 번호**: 선택적 페이지 번호 표시

### 📊 진행 상황
- **분할 진행률**: PDF 분할 과정 실시간 표시
- **생성 진행률**: 최종 PDF 생성 과정 추적

## 🛠 기술 스택

- **Python 3.8+**
- **Streamlit**: 웹 인터페이스
- **PyPDF2**: PDF 조작 및 생성
- **PyMuPDF (fitz)**: PDF 렌더링
- **ReportLab**: PDF 생성 및 그래픽
- **Pillow (PIL)**: 이미지 처리
- **NumPy**: 수치 연산

## 🚀 설치 및 실행

### 1. 저장소 클론
```bash
git clone https://github.com/gjsxo0828/pdfResize.git
cd pdfResize
```

### 2. 가상환경 생성 및 활성화
```bash
# Windows
python -m venv venv
venv\Scripts\activate.ps1

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 애플리케이션 실행
```bash
streamlit run split_pdf_editor.py
```

## 📋 사용법

### 1. PDF 업로드
- A4 가로 레이아웃으로 작성된 PDF 파일 업로드

### 2. 기본 설정
- **첫 페이지 사용**: 좌측부터 시작할지 우측부터 시작할지 선택
- **페이지 순서**: 1234 (일반) 또는 2341 (제본용) 선택

### 3. 여백 설정
- **위쪽/아래쪽**: 모든 페이지 공통 여백
- **바깥쪽**: 홀수 페이지 오른쪽, 짝수 페이지 왼쪽 여백
- **안쪽**: 홀수 페이지 왼쪽, 짝수 페이지 오른쪽 여백

### 4. 크기 및 위치 조정
- **홀수/짝수 페이지별 독립 설정**
- **축소 비율**: 0.10 ~ 2.00 (소수점 2자리)
- **좌우/상하 이동**: -50.0 ~ 50.0mm (소수점 1자리)

### 5. 미리보기 확인
- 4페이지 단위로 미리보기 확인
- 이전/다음 버튼으로 페이지 탐색
- 원본 페이지 번호 표시 옵션

### 6. PDF 생성
- **여백 가이드 선 포함** 옵션 선택
- **최종 PDF 생성** 버튼 클릭
- 생성된 PDF 다운로드

## 📁 파일 구조

```
pdfResize/
├── split_pdf_editor.py      # 메인 애플리케이션
├── requirements.txt         # Python 의존성
├── README.md               # 프로젝트 문서
├── PROJECT_STATUS.md       # 개발 현황
└── venv/                   # 가상환경 (생성됨)
```

## 🔧 주요 클래스 및 함수

### BookPublishingEditor 클래스
- `analyze_pdf()`: PDF 분석 및 메타데이터 추출
- `split_landscape_pages()`: A4 가로 페이지 분할
- `apply_page_order()`: 페이지 순서 재배열
- `calculate_page_margins()`: 홀수/짝수 페이지 여백 계산
- `transform_page_to_book_size()`: 페이지 크기 및 위치 변환
- `create_preview_image()`: 미리보기 이미지 생성
- `create_book_pdf()`: 최종 PDF 생성
- `add_margin_guides_to_page()`: 여백 가이드 선 추가

## 🎨 UI 구성

### 사이드바
- 파일 업로드
- 파일 정보 (접힌 상태)
- PDF 분석 결과 (접힌 상태)
- 기본 설정
- 여백 설정 (접힌 상태)
- 크기 및 위치 조정 (접힌 상태)
- 출력 설정

### 메인 영역
- 미리보기 (4페이지 단위)
- 페이지네이션 버튼
- PDF 생성 및 다운로드

## 🔍 품질 보증

### 오류 해결 완료
- ✅ Pickle 직렬화 오류 해결
- ✅ "sequence index out of range" 오류 해결
- ✅ "I/O operation on closed file" 오류 해결
- ✅ PDF 손상 문제 해결
- ✅ 버퍼 참조 문제 해결

### 품질 특징
- **고해상도 출력**: 300 DPI 품질
- **벡터 그래픽 보존**: 텍스트 및 도형 선명도 유지
- **안정적인 처리**: 다중 대안 경로 및 오류 처리
- **메모리 효율성**: 적절한 버퍼 관리
- **사용자 친화적**: 직관적인 인터페이스

## 📈 성능

- **미리보기**: 75 DPI로 빠른 렌더링
- **최종 출력**: 300 DPI 고품질
- **메모리 관리**: 임시 파일 자동 정리
- **진행률 표시**: 실시간 처리 상황 안내

## 🤝 기여

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 지원

문제가 발생하거나 기능 요청이 있으시면 GitHub Issues를 통해 연락해 주세요.

---
**개발자**: AI Assistant  
**최종 업데이트**: 2025-01-09  
**버전**: 1.0.0 