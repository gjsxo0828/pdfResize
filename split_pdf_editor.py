import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import RectangleObject
try:
    from PyPDF2 import Transformation
except ImportError:
    # PyPDF2 3.0+ 버전 호환성
    try:
        from PyPDF2.generic import Transformation
    except ImportError:
        # 수동으로 변환 매트릭스 구현
        class Transformation:
            def __init__(self):
                self.matrix = [1, 0, 0, 1, 0, 0]  # 기본 단위 행렬
            
            def scale(self, sx, sy):
                # 스케일링 변환
                new_transform = Transformation()
                new_transform.matrix = [sx, 0, 0, sy, 0, 0]
                return new_transform
            
            def translate(self, tx, ty):
                # 이동 변환 추가
                self.matrix[4] = tx
                self.matrix[5] = ty
                return self

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import red, blue
import io
import os
import tempfile
import copy

class BookPublishingEditor:
    """A4 가로 레이아웃 PDF를 책 출판용으로 분할하고 편집하는 클래스"""
    
    def __init__(self, book_width_mm=125, book_height_mm=175):
        self.book_width_mm = book_width_mm
        self.book_height_mm = book_height_mm
        self.book_width_pt = book_width_mm * mm
        self.book_height_pt = book_height_mm * mm
    
    def analyze_pdf(self, pdf_path):
        """PDF 파일 분석"""
        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            
            # 첫 페이지 크기 확인
            first_page = reader.pages[0]
            width = float(first_page.mediabox.width)
            height = float(first_page.mediabox.height)
            
            is_landscape = width > height
            
            return {
                'total_pages': total_pages,
                'is_landscape': is_landscape,
                'page_width': width,
                'page_height': height,
                'estimated_split_pages': total_pages * 2 if is_landscape else total_pages
            }
        except Exception as e:
            return {'error': str(e)}
    
    def split_landscape_pages(self, pdf_path, use_first_page=True, progress_callback=None):
        """A4 가로 페이지를 좌우로 분할"""
        reader = PdfReader(pdf_path)
        split_pages = []
        
        total_pages = len(reader.pages)
        
        for page_num, page in enumerate(reader.pages):
            if progress_callback:
                progress_callback(page_num + 1, total_pages, f"페이지 {page_num + 1} 분할 중...")
            
            # 페이지 크기 확인
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            
            if width > height:  # 가로 페이지
                # 좌측 페이지 생성
                left_page = copy.deepcopy(page)
                left_mediabox = RectangleObject([0, 0, width / 2, height])
                left_page.mediabox = left_mediabox
                split_pages.append({
                    'page': left_page,
                    'original_page': page_num + 1,
                    'side': 'left',
                    'description': f"원본 {page_num + 1}페이지 좌측"
                })
                
                # 우측 페이지 생성
                right_page = copy.deepcopy(page)
                right_mediabox = RectangleObject([width / 2, 0, width, height])
                right_page.mediabox = right_mediabox
                split_pages.append({
                    'page': right_page,
                    'original_page': page_num + 1,
                    'side': 'right',
                    'description': f"원본 {page_num + 1}페이지 우측"
                })
            else:  # 세로 페이지
                split_pages.append({
                    'page': page,
                    'original_page': page_num + 1,
                    'side': 'single',
                    'description': f"원본 {page_num + 1}페이지"
                })
        
        # 첫 페이지 사용 여부 적용
        if not use_first_page and len(split_pages) > 0:
            split_pages = split_pages[1:]
        
        return split_pages
    
    def apply_page_order(self, split_pages, page_order="1234"):
        """페이지 순서 재배열"""
        if page_order == "2341":
            reordered_pages = []
            for i in range(0, len(split_pages), 4):
                block = split_pages[i:i+4]
                if len(block) >= 4:
                    # 2,3,4,1 순서로 재배열
                    reordered_block = [block[1], block[2], block[3], block[0]]
                    reordered_pages.extend(reordered_block)
                else:
                    # 4개 미만인 경우 그대로
                    reordered_pages.extend(block)
            return reordered_pages
        else:
            # 1234 순서 (기본)
            return split_pages
    
    def calculate_page_margins(self, page_number, margin_top, margin_bottom, margin_outer, margin_inner):
        """페이지 번호에 따른 여백 계산"""
        if page_number % 2 == 1:  # 홀수 페이지
            margin_left = margin_outer   # 바깥쪽
            margin_right = margin_inner  # 안쪽
        else:  # 짝수 페이지
            margin_left = margin_inner   # 안쪽
            margin_right = margin_outer  # 바깥쪽
        
        return {
            'top': margin_top,
            'bottom': margin_bottom,
            'left': margin_left,
            'right': margin_right
        }
    
    def create_book_pdf(self, split_pages, margins, scaling_settings, show_margin_guides=False, progress_callback=None):
        """최종 책 PDF 생성"""
        writer = PdfWriter()
        total_pages = len(split_pages)
        
        for idx, page_info in enumerate(split_pages):
            if progress_callback:
                progress_callback(idx + 1, total_pages, f"페이지 {idx + 1} 처리 중...")
            
            page_number = idx + 1
            
            # 페이지별 여백 계산
            page_margins = self.calculate_page_margins(
                page_number, margins['top'], margins['bottom'], 
                margins['outer'], margins['inner']
            )
            
            # 페이지별 스케일링 설정 선택
            if page_number % 2 == 1:  # 홀수 페이지
                scale_factor = scaling_settings['odd']['scale']
                offset_x = scaling_settings['odd']['offset_x']
                offset_y = scaling_settings['odd']['offset_y']
            else:  # 짝수 페이지
                scale_factor = scaling_settings['even']['scale']
                offset_x = scaling_settings['even']['offset_x']
                offset_y = scaling_settings['even']['offset_y']
            
            # 페이지 변환 적용
            transformed_page = self.transform_page_to_book_size(
                page_info['page'], page_margins, scale_factor, offset_x, offset_y
            )
            
            # 여백 가이드 추가 (옵션)
            if show_margin_guides:
                transformed_page = self.add_margin_guides_to_page(
                    transformed_page, page_margins, page_number
                )
            
            writer.add_page(transformed_page)
        
        # PDF 데이터 반환
        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)
        return output_buffer.getvalue()
    
    def transform_page_to_book_size(self, page, margins, scale_factor, offset_x, offset_y):
        """페이지를 책 크기로 변환 (PyPDF2 3.0.1 호환)"""
        # 여백을 포인트로 변환
        margin_left_pt = margins['left'] * mm
        margin_right_pt = margins['right'] * mm
        margin_top_pt = margins['top'] * mm
        margin_bottom_pt = margins['bottom'] * mm
        
        # 콘텐츠 영역 계산
        content_width = self.book_width_pt - margin_left_pt - margin_right_pt
        content_height = self.book_height_pt - margin_top_pt - margin_bottom_pt
        
        # 원본 페이지 크기
        original_width = float(page.mediabox.width)
        original_height = float(page.mediabox.height)
        
        # 안전장치
        if original_width <= 0 or original_height <= 0 or content_width <= 0 or content_height <= 0:
            # 기본 변환만 적용
            page.mediabox = RectangleObject([0, 0, self.book_width_pt, self.book_height_pt])
            return page
        
        # 스케일 계산 (비율 유지)
        scale_x = (content_width * scale_factor) / original_width
        scale_y = (content_height * scale_factor) / original_height
        scale = min(scale_x, scale_y)
        
        # 중앙 정렬을 위한 오프셋 계산
        scaled_width = original_width * scale
        scaled_height = original_height * scale
        
        center_x = margin_left_pt + (content_width - scaled_width) / 2
        center_y = margin_bottom_pt + (content_height - scaled_height) / 2
        
        # 사용자 오프셋 추가 (mm를 포인트로 변환)
        final_x = center_x + (offset_x * mm)
        final_y = center_y + (offset_y * mm)
        
        # PyPDF2 3.0.1 호환 - 기본 스케일링만 적용
        try:
            # 스케일링 적용 (PyPDF2 3.0.1 방식)
            if hasattr(page, 'scale'):
                page.scale(scale, scale)
            elif hasattr(page, 'scaleBy'):
                page.scaleBy(scale)
            
            # 이동 적용
            if hasattr(page, 'translate'):
                page.translate(final_x / scale, final_y / scale)
            elif hasattr(page, 'translateBy'):
                page.translateBy(final_x / scale, final_y / scale)
                
        except Exception as e:
            # 변환 실패 시에도 계속 진행
            print(f"페이지 변환 경고: {e}")
        
        # 새 페이지 크기 설정
        page.mediabox = RectangleObject([0, 0, self.book_width_pt, self.book_height_pt])
        
        return page
    
    def add_margin_guides_to_page(self, page, margins, page_number):
        """페이지에 여백 가이드 선 추가"""
        # ReportLab으로 가이드 선이 있는 오버레이 생성
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(self.book_width_pt, self.book_height_pt))
        
        # 여백을 포인트로 변환
        margin_left_pt = margins['left'] * mm
        margin_right_pt = margins['right'] * mm
        margin_top_pt = margins['top'] * mm
        margin_bottom_pt = margins['bottom'] * mm
        
        # 선 색상 설정 (홀수: 빨간색, 짝수: 파란색)
        line_color = red if page_number % 2 == 1 else blue
        c.setStrokeColor(line_color)
        c.setLineWidth(0.5)
        
        # 여백 가이드 선 그리기
        # 상단
        c.line(0, self.book_height_pt - margin_top_pt, self.book_width_pt, self.book_height_pt - margin_top_pt)
        # 하단
        c.line(0, margin_bottom_pt, self.book_width_pt, margin_bottom_pt)
        # 좌측
        c.line(margin_left_pt, 0, margin_left_pt, self.book_height_pt)
        # 우측
        c.line(self.book_width_pt - margin_right_pt, 0, self.book_width_pt - margin_right_pt, self.book_height_pt)
        
        c.save()
        buffer.seek(0)
        
        # 오버레이를 원본 페이지에 합성
        overlay_reader = PdfReader(buffer)
        overlay_page = overlay_reader.pages[0]
        page.merge_page(overlay_page)
        
        return page

def main():
    st.set_page_config(
        page_title="📚 책 출판용 PDF 편집기",
        page_icon="📚",
        layout="wide"
    )
    
    st.title("📚 책 출판용 PDF 편집기")
    st.markdown("A4 가로 레이아웃 PDF를 책 출판용으로 분할하고 편집합니다.")
    
    # 사이드바 설정
    with st.sidebar:
        st.header("📋 설정")
        
        # 파일 업로드
        uploaded_file = st.file_uploader(
            "PDF 파일 선택", 
            type=['pdf'],
            help="A4 가로 레이아웃으로 작성된 PDF 파일을 업로드하세요."
        )
        
        if not uploaded_file:
            st.info("👆 PDF 파일을 업로드해주세요.")
            return
        
        # 임시 파일 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_file_path = tmp_file.name
        
        # PDF 편집기 초기화
        editor = BookPublishingEditor()
        
        # PDF 분석
        with st.spinner("PDF 분석 중..."):
            analysis = editor.analyze_pdf(tmp_file_path)
        
        if 'error' in analysis:
            st.error(f"PDF 분석 실패: {analysis['error']}")
            return
        
        # 분석 결과 표시
        with st.expander("📊 PDF 분석 결과", expanded=False):
            st.write(f"**총 페이지:** {analysis['total_pages']}")
            st.write(f"**레이아웃:** {'가로' if analysis['is_landscape'] else '세로'}")
            st.write(f"**예상 분할 페이지:** {analysis['estimated_split_pages']}")
        
        if not analysis['is_landscape']:
            st.warning("⚠️ 가로 레이아웃이 아닙니다. 분할 효과가 제한적일 수 있습니다.")
        
        st.divider()
        
        # 기본 설정
        st.subheader("⚙️ 기본 설정")
        
        use_first_page = st.checkbox(
            "첫 페이지 사용", 
            value=True,
            help="체크 해제시 좌측 첫 페이지를 제외하고 우측부터 1페이지로 시작"
        )
        
        page_order = st.selectbox(
            "페이지 순서",
            options=["1234", "2341"],
            help="1234: 일반 순서 / 2341: 제본용 순서 (용지 절단 후 연속 페이지)"
        )
        
        st.divider()
        
        # 여백 설정
        st.subheader("📏 여백 설정")
        
        col1, col2 = st.columns(2)
        with col1:
            margin_top = st.number_input("위쪽 (mm)", min_value=0, max_value=50, value=15, step=1)
            margin_outer = st.number_input("바깥쪽 (mm)", min_value=0, max_value=50, value=15, step=1)
        
        with col2:
            margin_bottom = st.number_input("아래쪽 (mm)", min_value=0, max_value=50, value=15, step=1)
            margin_inner = st.number_input("안쪽 (mm)", min_value=0, max_value=50, value=15, step=1)
        
        st.info("💡 홀수 페이지: 왼쪽=바깥쪽, 오른쪽=안쪽 / 짝수 페이지: 왼쪽=안쪽, 오른쪽=바깥쪽")
        
        st.divider()
        
        # 스케일링 및 위치 조정
        st.subheader("🔧 크기 및 위치 조정")
        
        # 홀수 페이지 설정
        st.write("**홀수 페이지 (1,3,5...)**")
        col1, col2, col3 = st.columns(3)
        with col1:
            scale_odd = st.number_input("축소 비율", min_value=0.10, max_value=2.00, value=1.00, step=0.01, key="scale_odd")
        with col2:
            offset_x_odd = st.number_input("좌우 이동 (mm)", min_value=-50.0, max_value=50.0, value=0.0, step=0.1, key="offset_x_odd")
        with col3:
            offset_y_odd = st.number_input("상하 이동 (mm)", min_value=-50.0, max_value=50.0, value=0.0, step=0.1, key="offset_y_odd")
        
        # 짝수 페이지 설정
        st.write("**짝수 페이지 (2,4,6...)**")
        col1, col2, col3 = st.columns(3)
        with col1:
            scale_even = st.number_input("축소 비율", min_value=0.10, max_value=2.00, value=1.00, step=0.01, key="scale_even")
        with col2:
            offset_x_even = st.number_input("좌우 이동 (mm)", min_value=-50.0, max_value=50.0, value=0.0, step=0.1, key="offset_x_even")
        with col3:
            offset_y_even = st.number_input("상하 이동 (mm)", min_value=-50.0, max_value=50.0, value=0.0, step=0.1, key="offset_y_even")
        
        st.divider()
        
        # 출력 설정
        st.subheader("📖 출력 설정")
        show_margin_guides = st.checkbox(
            "여백 가이드 선 포함", 
            value=False,
            help="PDF에 여백 경계선 포함 (홀수: 빨간색, 짝수: 파란색)"
        )
    
    # 메인 영역
    try:
        # PDF 분할
        with st.spinner("PDF 분할 중..."):
            split_pages = editor.split_landscape_pages(tmp_file_path, use_first_page)
        
        # 페이지 순서 적용
        ordered_pages = editor.apply_page_order(split_pages, page_order)
        
        st.success(f"✅ 총 {len(ordered_pages)}개 페이지 준비 완료")
        
        # 미리보기 (첫 4페이지)
        st.subheader("👀 미리보기 (처음 4페이지)")
        
        if len(ordered_pages) > 0:
            preview_pages = ordered_pages[:4]
            cols = st.columns(min(4, len(preview_pages)))
            
            for i, page_info in enumerate(preview_pages):
                with cols[i]:
                    st.write(f"**페이지 {i+1}**")
                    st.write(f"*{page_info['description']}*")
                    
                    # 간단한 페이지 정보 표시
                    if (i+1) % 2 == 1:
                        st.write("🔴 홀수 페이지")
                    else:
                        st.write("🔵 짝수 페이지")
        
        # PDF 생성 버튼
        st.divider()
        
        if st.button("📖 최종 PDF 생성", type="primary"):
            # 설정 정리
            margins = {
                'top': margin_top,
                'bottom': margin_bottom,
                'outer': margin_outer,
                'inner': margin_inner
            }
            
            scaling_settings = {
                'odd': {
                    'scale': scale_odd,
                    'offset_x': offset_x_odd,
                    'offset_y': offset_y_odd
                },
                'even': {
                    'scale': scale_even,
                    'offset_x': offset_x_even,
                    'offset_y': offset_y_even
                }
            }
            
            # 프로그래스바와 상태 표시
            progress_container = st.empty()
            status_container = st.empty()
            
            def update_progress(current, total, description):
                progress_value = current / total if total > 0 else 0
                progress_container.progress(progress_value)
                status_container.info(f"📊 {description}")
            
            try:
                # PDF 생성
                pdf_data = editor.create_book_pdf(
                    ordered_pages, margins, scaling_settings, 
                    show_margin_guides, update_progress
                )
                
                # 프로그래스바 제거
                progress_container.empty()
                status_container.empty()
                
                st.success("✅ PDF 생성 완료!")
                
                # 다운로드 버튼
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📥 완성된 PDF 다운로드",
                        data=pdf_data,
                        file_name=f"book_{uploaded_file.name}",
                        mime="application/pdf"
                    )
                
                with col2:
                    st.info("💡 출판업체에 전달 준비 완료!")
                
            except Exception as e:
                progress_container.empty()
                status_container.empty()
                st.error(f"❌ PDF 생성 중 오류: {str(e)}")
                st.code(str(e))
        
    except Exception as e:
        st.error(f"처리 중 오류 발생: {str(e)}")
    
    finally:
        # 임시 파일 정리
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
    
    # 사용법 안내
    with st.expander("📖 사용법 안내"):
        st.markdown("""
        ### 🎯 프로세스
        1. **A4 가로 PDF 업로드**: 좌우에 책 내용이 배치된 PDF
        2. **첫 페이지 설정**: 왼쪽부터 시작할지, 오른쪽부터 시작할지 선택
        3. **페이지 순서**: 일반 순서(1234) 또는 제본용 순서(2341) 선택
        4. **여백 설정**: 책 제본을 위한 여백 조정
        5. **크기/위치 조정**: 홀수/짝수 페이지별 독립 조정
        6. **PDF 생성**: 출판업체 전달용 최종 PDF 생성
        
        ### 📏 여백 설명
        - **바깥쪽**: 홀수 페이지의 왼쪽, 짝수 페이지의 오른쪽 여백
        - **안쪽**: 홀수 페이지의 오른쪽, 짝수 페이지의 왼쪽 여백 (제본 부분)
        
        ### 🔄 페이지 순서
        - **1234**: 1,2,3,4,5,6,7,8... (일반 순서)
        - **2341**: 2,3,4,1,6,7,8,5... (용지 절단 후 연속 페이지용)
        """)

if __name__ == "__main__":
    main() 