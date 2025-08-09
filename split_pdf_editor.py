import streamlit as st
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, white
import io
import os
import tempfile
from PIL import Image
import fitz  # PyMuPDF
import numpy as np
import base64

class SplitPDFEditor:
    def __init__(self):
        # 125x175mm 책 크기 (포인트 단위로 변환)
        self.book_width = 125 * mm
        self.book_height = 175 * mm
        
    def convert_mm_to_points(self, mm_value):
        """밀리미터를 포인트로 변환"""
        return mm_value * 2.83465
    
    def convert_points_to_mm(self, points_value):
        """포인트를 밀리미터로 변환"""
        return points_value / 2.83465
    
    def analyze_pdf_content(self, pdf_path):
        """PDF 내용 분석"""
        doc = fitz.open(pdf_path)
        analysis = {
            'total_pages': len(doc),
            'page_sizes': [],
            'text_content': [],
            'image_count': 0,
            'is_landscape': False
        }
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            rect = page.rect
            analysis['page_sizes'].append(rect)
            
            # 가로/세로 판단
            if rect.width > rect.height:
                analysis['is_landscape'] = True
            
            # 텍스트 추출
            text = page.get_text()
            analysis['text_content'].append(text)
            
            # 이미지 개수 확인
            image_list = page.get_images()
            analysis['image_count'] += len(image_list)
        
        doc.close()
        return analysis
    
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
        else:
            # 가로로 분할 (상하 분할)
            top_rect = fitz.Rect(0, 0, rect.width, rect.height/2)
            bottom_rect = fitz.Rect(0, rect.height/2, rect.width, rect.height)
            
            top_page = page.get_pixmap(clip=top_rect)
            bottom_page = page.get_pixmap(clip=bottom_rect)
            
            return top_page, bottom_page
    
    def generate_preview_images(self, content_pdf_path, split_direction='vertical', max_pages=4):
        """미리보기용 이미지 생성"""
        doc = fitz.open(content_pdf_path)
        preview_images = []
        
        pages_processed = 0
        
        for page_num in range(len(doc)):
            if pages_processed >= max_pages:
                break
                
            page = doc[page_num]
            rect = page.rect
            
            # 가로 페이지인지 확인
            if rect.width > rect.height:
                # 가로 페이지를 분할
                left_pix, right_pix = self.split_landscape_page(page, split_direction)
                
                # 좌측 페이지 이미지
                if pages_processed < max_pages:
                    left_img_data = left_pix.tobytes("png")
                    preview_images.append({
                        'page_number': pages_processed + 1,
                        'image_data': left_img_data,
                        'description': f"페이지 {pages_processed + 1} (원본 {page_num + 1}페이지 좌측)"
                    })
                    pages_processed += 1
                
                # 우측 페이지 이미지
                if pages_processed < max_pages:
                    right_img_data = right_pix.tobytes("png")
                    preview_images.append({
                        'page_number': pages_processed + 1,
                        'image_data': right_img_data,
                        'description': f"페이지 {pages_processed + 1} (원본 {page_num + 1}페이지 우측)"
                    })
                    pages_processed += 1
                    
            else:
                # 세로 페이지는 그대로
                if pages_processed < max_pages:
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                    img_data = pix.tobytes("png")
                    preview_images.append({
                        'page_number': pages_processed + 1,
                        'image_data': img_data,
                        'description': f"페이지 {pages_processed + 1} (원본 {page_num + 1}페이지)"
                    })
                    pages_processed += 1
        
        doc.close()
        return preview_images
    
    def create_book_pages(self, content_pdf_path, margin_top=15, margin_bottom=15, 
                         margin_left=15, margin_right=15, split_direction='vertical'):
        """PDF 내용을 책 페이지 크기로 변환 (순차적 분할)"""
        
        # 여백을 포인트로 변환
        margin_top_pt = self.convert_mm_to_points(margin_top)
        margin_bottom_pt = self.convert_mm_to_points(margin_bottom)
        margin_left_pt = self.convert_mm_to_points(margin_left)
        margin_right_pt = self.convert_mm_to_points(margin_right)
        
        # 사용 가능한 내용 영역 계산
        content_width = self.book_width - margin_left_pt - margin_right_pt
        content_height = self.book_height - margin_top_pt - margin_bottom_pt
        
        # 원본 PDF 읽기
        doc = fitz.open(content_pdf_path)
        
        # 새 PDF 생성
        output = io.BytesIO()
        c = canvas.Canvas(output, pagesize=(self.book_width, self.book_height))
        
        total_pages = 0
        
        # 순차적으로 페이지 처리 (1,2,3,4 순서)
        for page_num in range(len(doc)):
            page = doc[page_num]
            rect = page.rect
            
            # 가로 페이지인지 확인
            if rect.width > rect.height:
                # 가로 페이지를 분할 - 좌측이 먼저, 우측이 다음
                left_pix, right_pix = self.split_landscape_page(page, split_direction)
                
                # 좌측 페이지 먼저 추가 (페이지 1)
                left_img_path = self.save_pixmap_to_image(left_pix, f"left_{page_num}")
                self.add_page_to_book(c, left_img_path, content_width, content_height, 
                                    margin_left_pt, margin_bottom_pt)
                total_pages += 1
                os.unlink(left_img_path)
                
                # 우측 페이지 다음에 추가 (페이지 2)
                right_img_path = self.save_pixmap_to_image(right_pix, f"right_{page_num}")
                self.add_page_to_book(c, right_img_path, content_width, content_height, 
                                    margin_left_pt, margin_bottom_pt)
                total_pages += 1
                os.unlink(right_img_path)
                
            else:
                # 세로 페이지는 그대로 처리
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_path = self.save_pixmap_to_image(pix, f"page_{page_num}")
                self.add_page_to_book(c, img_path, content_width, content_height, 
                                    margin_left_pt, margin_bottom_pt)
                total_pages += 1
                os.unlink(img_path)
        
        c.save()
        output.seek(0)
        doc.close()
        return output, total_pages
    
    def save_pixmap_to_image(self, pixmap, filename):
        """Pixmap을 이미지 파일로 저장"""
        img_data = pixmap.tobytes("png")
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as img_file:
            img_file.write(img_data)
            return img_file.name
    
    def add_page_to_book(self, canvas_obj, image_path, content_width, content_height, 
                        margin_left_pt, margin_bottom_pt):
        """이미지를 책 페이지에 추가"""
        # 이미지 크기 조정
        adjusted_img_path = self.adjust_image_for_book(
            image_path, content_width, content_height, 'fit_both'
        )
        
        # 조정된 이미지를 새 페이지에 그리기
        canvas_obj.drawImage(adjusted_img_path, margin_left_pt, margin_bottom_pt, 
                           width=content_width, height=content_height)
        
        canvas_obj.showPage()
        
        # 임시 파일 정리
        if adjusted_img_path != image_path:
            os.unlink(adjusted_img_path)
    
    def adjust_image_for_book(self, image_path, target_width, target_height, scale_mode):
        """이미지를 책 크기에 맞게 조정"""
        with Image.open(image_path) as img:
            img_width, img_height = img.size
            
            if scale_mode == 'fit_width':
                # 너비에 맞춰 조정
                scale_factor = target_width / img_width
                new_width = target_width
                new_height = img_height * scale_factor
                
                if new_height > target_height:
                    # 높이가 넘치면 높이에 맞춰 조정
                    scale_factor = target_height / img_height
                    new_width = img_width * scale_factor
                    new_height = target_height
                    
            elif scale_mode == 'fit_height':
                # 높이에 맞춰 조정
                scale_factor = target_height / img_height
                new_width = img_width * scale_factor
                new_height = target_height
                
                if new_width > target_width:
                    # 너비가 넘치면 너비에 맞춰 조정
                    scale_factor = target_width / img_width
                    new_width = target_width
                    new_height = img_height * scale_factor
                    
            else:  # fit_both
                # 둘 다에 맞춰 조정 (비율 유지)
                width_scale = target_width / img_width
                height_scale = target_height / img_height
                scale_factor = min(width_scale, height_scale)
                new_width = img_width * scale_factor
                new_height = img_height * scale_factor
            
            # 이미지 리사이즈
            resized_img = img.resize((int(new_width), int(new_height)), Image.Resampling.LANCZOS)
            
            # 새 이미지 파일로 저장
            output_path = image_path.replace('.png', '_resized.png')
            resized_img.save(output_path, 'PNG')
            
            return output_path

def main():
    st.set_page_config(
        page_title="PDF 분할 편집기",
        page_icon="📚",
        layout="wide"
    )
    
    st.title("📚 PDF 분할 편집기")
    st.markdown("가로 PDF를 분할하여 125×175mm 책 페이지로 변환 (순차적 페이지 순서)")
    
    # 사이드바 설정
    st.sidebar.header("📐 편집 설정")
    
    # 여백 설정
    st.sidebar.subheader("여백 설정 (mm)")
    margin_top = st.sidebar.slider("상단 여백", 5, 40, 15)
    margin_bottom = st.sidebar.slider("하단 여백", 5, 40, 15)
    margin_left = st.sidebar.slider("좌측 여백", 5, 40, 15)
    margin_right = st.sidebar.slider("우측 여백", 5, 40, 15)
    
    # 분할 방향 설정
    st.sidebar.subheader("분할 설정")
    split_direction = st.sidebar.selectbox(
        "분할 방향",
        ["vertical", "horizontal"],
        format_func=lambda x: {
            "vertical": "세로 분할 (좌우 분할)",
            "horizontal": "가로 분할 (상하 분할)"
        }[x]
    )
    
    # 미리보기 설정
    st.sidebar.subheader("미리보기 설정")
    show_preview = st.sidebar.checkbox("분할 미리보기 표시", value=True)
    preview_pages = st.sidebar.slider("미리보기 페이지 수", 2, 8, 4)
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "PDF 파일을 선택하세요",
        type=['pdf'],
        help="편집할 PDF 파일을 업로드하세요"
    )
    
    if uploaded_file is not None:
        # 파일 정보 표시
        st.subheader("📄 파일 정보")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**파일명:** {uploaded_file.name}")
            st.write(f"**파일 크기:** {uploaded_file.size / 1024:.1f} KB")
        
        with col2:
            st.write(f"**목표 크기:** 125×175mm")
            st.write(f"**여백:** 상단{margin_top}mm, 하단{margin_bottom}mm, 좌측{margin_left}mm, 우측{margin_right}mm")
        
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        # PDF 분석
        try:
            editor = SplitPDFEditor()
            analysis = editor.analyze_pdf_content(tmp_file_path)
            
            st.subheader("📊 PDF 분석 결과")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("원본 페이지 수", analysis['total_pages'])
            
            with col2:
                st.metric("이미지 개수", analysis['image_count'])
            
            with col3:
                if analysis['is_landscape']:
                    st.metric("가로 페이지", "있음")
                else:
                    st.metric("가로 페이지", "없음")
            
            with col4:
                avg_text_length = sum(len(text) for text in analysis['text_content']) / len(analysis['text_content'])
                st.metric("평균 텍스트 길이", f"{avg_text_length:.0f}자")
            
            # 예상 결과 페이지 수 계산
            expected_pages = 0
            for page_size in analysis['page_sizes']:
                if page_size.width > page_size.height:
                    expected_pages += 2  # 가로 페이지는 2개로 분할
                else:
                    expected_pages += 1  # 세로 페이지는 그대로
            
            st.info(f"📋 **예상 결과 페이지 수:** {expected_pages}페이지 (순차적 순서)")
            
            # 미리보기 표시
            if show_preview and analysis['is_landscape']:
                st.subheader("🔍 분할 미리보기")
                
                with st.spinner("미리보기 이미지를 생성하는 중..."):
                    try:
                        preview_images = editor.generate_preview_images(
                            tmp_file_path, 
                            split_direction=split_direction,
                            max_pages=preview_pages
                        )
                        
                        if preview_images:
                            # 2열로 미리보기 표시
                            cols = st.columns(2)
                            for i, img_info in enumerate(preview_images):
                                col_idx = i % 2
                                with cols[col_idx]:
                                    st.write(f"**{img_info['description']}**")
                                    st.image(
                                        img_info['image_data'], 
                                        caption=f"페이지 {img_info['page_number']}",
                                        use_column_width=True
                                    )
                        else:
                            st.warning("미리보기 이미지를 생성할 수 없습니다.")
                            
                    except Exception as e:
                        st.error(f"미리보기 생성 중 오류: {str(e)}")
            
            # 편집 버튼
            if st.button("📖 PDF 분할하기", type="primary"):
                with st.spinner("PDF를 분할하는 중..."):
                    try:
                        result_pdf, actual_pages = editor.create_book_pages(
                            tmp_file_path,
                            margin_top=margin_top,
                            margin_bottom=margin_bottom,
                            margin_left=margin_left,
                            margin_right=margin_right,
                            split_direction=split_direction
                        )
                        
                        # 결과 다운로드
                        st.success(f"✅ 분할이 완료되었습니다! (총 {actual_pages}페이지)")
                        
                        # 다운로드 버튼
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="📥 분할된 PDF 다운로드",
                                data=result_pdf.getvalue(),
                                file_name=f"split_{uploaded_file.name}",
                                mime="application/pdf"
                            )
                        
                        with col2:
                            st.info("💡 **팁:** 분할된 페이지가 1,2,3,4 순서로 배치되었습니다.")
                        
                    except Exception as e:
                        st.error(f"❌ 분할 중 오류가 발생했습니다: {str(e)}")
                    finally:
                        # 임시 파일 정리
                        if os.path.exists(tmp_file_path):
                            os.unlink(tmp_file_path)
        
        except Exception as e:
            st.error(f"PDF 분석 중 오류가 발생했습니다: {str(e)}")
    
    # 사용법 안내
    with st.expander("📖 상세 사용법"):
        st.markdown("""
        ### 🎯 사용 방법
        
        1. **PDF 파일 업로드**: 편집할 PDF 파일을 선택합니다.
        2. **여백 설정**: 사이드바에서 상단, 하단, 좌측, 우측 여백을 조정합니다.
        3. **분할 방향 선택**: 
           - **세로 분할 (좌우 분할)**: 가로 페이지를 좌우로 나눕니다.
           - **가로 분할 (상하 분할)**: 가로 페이지를 상하로 나눕니다.
        4. **미리보기 확인**: 분할될 페이지들을 미리 확인합니다.
        5. **분할**: 'PDF 분할하기' 버튼을 클릭합니다.
        6. **다운로드**: 분할된 PDF를 다운로드합니다.
        
        ### 🔍 미리보기 기능
        
        - **분할 미리보기**: 실제 분할 전에 결과를 미리 확인할 수 있습니다.
        - **페이지 수 조정**: 미리보기할 페이지 수를 2-8페이지까지 설정 가능합니다.
        - **실시간 업데이트**: 분할 방향을 변경하면 미리보기도 자동 업데이트됩니다.
        
        ### 📏 권장 여백 설정
        
        | 책 유형 | 상단 | 하단 | 좌측 | 우측 |
        |---------|------|------|------|------|
        | 일반적인 책 | 15mm | 15mm | 15mm | 15mm |
        | 여백이 넓은 책 | 20mm | 20mm | 20mm | 20mm |
        | 여백이 좁은 책 | 10mm | 10mm | 10mm | 10mm |
        | 이미지 중심 책 | 10mm | 10mm | 10mm | 10mm |
        | 텍스트 중심 책 | 20mm | 20mm | 20mm | 20mm |
        
        ### ⚠️ 주의사항
        
        - **가로 페이지 분할**: 가로 형태의 페이지는 자동으로 2개 페이지로 분할됩니다.
        - **세로 페이지**: 세로 형태의 페이지는 그대로 1개 페이지로 처리됩니다.
        - **분할 기준**: 가로 페이지는 정확히 가운데를 기준으로 분할됩니다.
        - **페이지 순서**: 분할된 페이지는 1,2,3,4 순서로 배치됩니다.
        - **품질**: 원본 PDF의 품질이 좋을수록 결과물도 좋습니다.
        
        ### 🔄 분할 방식 설명
        
        - **세로 분할 (좌우 분할)**: 가로 페이지를 가운데를 기준으로 좌우로 나눕니다.
          - 좌측 → 페이지 1, 우측 → 페이지 2
        - **가로 분할 (상하 분할)**: 가로 페이지를 가운데를 기준으로 상하로 나눕니다.
          - 상단 → 페이지 1, 하단 → 페이지 2
        
        ### 📖 페이지 순서 설명
        
        - **순차적 순서**: 분할된 페이지가 1,2,3,4 순서로 배치됩니다.
        - **간단한 구조**: 복잡한 책 인쇄 순서 없이 단순한 순서로 처리됩니다.
        - **직관적**: 원본 페이지 순서를 그대로 유지합니다.
        """)

if __name__ == "__main__":
    main() 