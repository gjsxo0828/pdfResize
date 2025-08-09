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
    
    def calculate_margins_for_page(self, page_number, margin_top, margin_bottom, margin_outer, margin_inner):
        """페이지 번호에 따라 실제 여백 계산 (홀수/짝수 페이지 고려)"""
        # 홀수 페이지(1,3,5...): 왼쪽이 안쪽, 오른쪽이 바깥쪽
        # 짝수 페이지(2,4,6...): 왼쪽이 바깥쪽, 오른쪽이 안쪽
        
        if page_number % 2 == 1:  # 홀수 페이지
            margin_left = margin_inner   # 안쪽
            margin_right = margin_outer  # 바깥쪽
        else:  # 짝수 페이지
            margin_left = margin_outer   # 바깥쪽
            margin_right = margin_inner  # 안쪽
        
        return {
            'top': margin_top,
            'bottom': margin_bottom,
            'left': margin_left,
            'right': margin_right
        }
    
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
    
    def generate_preview_images(self, content_pdf_path, split_direction='vertical', 
                              max_pages=4, use_first_page=True, page_order="1234",
                              margin_top=15, margin_bottom=15, margin_outer=15, margin_inner=15):
        """미리보기용 이미지 생성 (여백 정보 포함)"""
        doc = fitz.open(content_pdf_path)
        all_pages = []
        
        # 모든 분할된 페이지 생성
        for page_num in range(len(doc)):
            page = doc[page_num]
            rect = page.rect
            
            # 가로 페이지인지 확인
            if rect.width > rect.height:
                # 가로 페이지를 분할
                left_pix, right_pix = self.split_landscape_page(page, split_direction)
                
                # 좌측 페이지
                left_img_data = left_pix.tobytes("png")
                all_pages.append({
                    'image_data': left_img_data,
                    'description': f"원본 {page_num + 1}페이지 좌측",
                    'original_page': page_num,
                    'split_part': 'left'
                })
                
                # 우측 페이지
                right_img_data = right_pix.tobytes("png")
                all_pages.append({
                    'image_data': right_img_data,
                    'description': f"원본 {page_num + 1}페이지 우측",
                    'original_page': page_num,
                    'split_part': 'right'
                })
                    
            else:
                # 세로 페이지는 그대로
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img_data = pix.tobytes("png")
                all_pages.append({
                    'image_data': img_data,
                    'description': f"원본 {page_num + 1}페이지",
                    'original_page': page_num,
                    'split_part': 'single'
                })
        
        doc.close()
        
        # 첫 페이지 사용 여부에 따라 조정
        if not use_first_page and len(all_pages) > 0:
            all_pages = all_pages[1:]  # 첫 페이지 제거
        
        # 페이지 순서에 따라 재배열
        if len(all_pages) >= 4:
            selected_pages = all_pages[:4]  # 처음 4페이지 선택
            
            # 페이지 순서 매핑
            order_map = {
                "1234": [0, 1, 2, 3],
                "2341": [1, 2, 3, 0]
            }
            
            if page_order in order_map:
                indices = order_map[page_order]
                reordered_pages = [selected_pages[i] for i in indices if i < len(selected_pages)]
            else:
                reordered_pages = selected_pages
        else:
            reordered_pages = all_pages
        
        # 최종 미리보기 이미지 생성 (여백 정보 포함)
        preview_images = []
        for i, page_info in enumerate(reordered_pages[:max_pages]):
            page_number = i + 1
            margins = self.calculate_margins_for_page(page_number, margin_top, margin_bottom, margin_outer, margin_inner)
            
            preview_images.append({
                'page_number': page_number,
                'image_data': page_info['image_data'],
                'description': f"페이지 {page_number} ({page_info['description']})",
                'margins': margins,
                'margin_info': f"위{margins['top']}mm, 아래{margins['bottom']}mm, 왼쪽{margins['left']}mm, 오른쪽{margins['right']}mm"
            })
        
        return preview_images
    
    def create_book_pages(self, content_pdf_path, margin_top=15, margin_bottom=15, 
                         margin_outer=15, margin_inner=15, split_direction='vertical',
                         use_first_page=True, page_order="1234"):
        """PDF 내용을 책 페이지 크기로 변환"""
        
        # 원본 PDF 읽기
        doc = fitz.open(content_pdf_path)
        
        # 새 PDF 생성
        output = io.BytesIO()
        c = canvas.Canvas(output, pagesize=(self.book_width, self.book_height))
        
        all_pages = []
        
        # 모든 페이지를 분할하여 저장
        for page_num in range(len(doc)):
            page = doc[page_num]
            rect = page.rect
            
            # 가로 페이지인지 확인
            if rect.width > rect.height:
                # 가로 페이지를 분할
                left_pix, right_pix = self.split_landscape_page(page, split_direction)
                
                # 좌측 페이지
                left_img_path = self.save_pixmap_to_image(left_pix, f"left_{page_num}")
                all_pages.append(left_img_path)
                
                # 우측 페이지
                right_img_path = self.save_pixmap_to_image(right_pix, f"right_{page_num}")
                all_pages.append(right_img_path)
                
            else:
                # 세로 페이지는 그대로 처리
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_path = self.save_pixmap_to_image(pix, f"page_{page_num}")
                all_pages.append(img_path)
        
        # 첫 페이지 사용 여부에 따라 조정
        if not use_first_page and len(all_pages) > 0:
            if os.path.exists(all_pages[0]):
                os.unlink(all_pages[0])  # 첫 페이지 파일 삭제
            all_pages = all_pages[1:]  # 첫 페이지 제거
        
        # 페이지 순서에 따라 재배열
        if len(all_pages) >= 4:
            selected_pages = all_pages[:4]  # 처음 4페이지 선택
            
            # 페이지 순서 매핑
            order_map = {
                "1234": [0, 1, 2, 3],
                "2341": [1, 2, 3, 0]
            }
            
            if page_order in order_map:
                indices = order_map[page_order]
                reordered_pages = [selected_pages[i] for i in indices if i < len(selected_pages)]
            else:
                reordered_pages = selected_pages
                
            # 사용하지 않는 페이지 파일 삭제
            unused_pages = [page for i, page in enumerate(selected_pages) if i not in order_map.get(page_order, [0, 1, 2, 3])]
            for unused_page in unused_pages:
                if os.path.exists(unused_page):
                    os.unlink(unused_page)
        else:
            reordered_pages = all_pages
        
        total_pages = 0
        
        # 재배열된 페이지들을 PDF에 추가 (각 페이지별 여백 적용)
        for i, img_path in enumerate(reordered_pages):
            if os.path.exists(img_path):
                page_number = i + 1
                margins = self.calculate_margins_for_page(page_number, margin_top, margin_bottom, margin_outer, margin_inner)
                
                # 여백을 포인트로 변환
                margin_top_pt = self.convert_mm_to_points(margins['top'])
                margin_bottom_pt = self.convert_mm_to_points(margins['bottom'])
                margin_left_pt = self.convert_mm_to_points(margins['left'])
                margin_right_pt = self.convert_mm_to_points(margins['right'])
                
                # 사용 가능한 내용 영역 계산
                content_width = self.book_width - margin_left_pt - margin_right_pt
                content_height = self.book_height - margin_top_pt - margin_bottom_pt
                
                # 이미지를 페이지에 추가
                self.add_page_to_book(
                    c, img_path, content_width, content_height, 
                    margin_left_pt, margin_bottom_pt
                )
                total_pages += 1
                os.unlink(img_path)  # 임시 파일 삭제
        
        c.save()
        output.seek(0)
        doc.close()
        
        # 남은 임시 파일들 정리
        for img_path in all_pages:
            if os.path.exists(img_path):
                os.unlink(img_path)
        
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
    st.markdown("가로 PDF를 분할하여 125×175mm 책 페이지로 변환")
    
    # 사이드바 설정
    st.sidebar.header("📐 기본 설정")
    
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
    
    # 페이지 순서 설정
    st.sidebar.subheader("페이지 설정")
    use_first_page = st.sidebar.checkbox("첫 페이지 사용", value=True,
                                        help="분할된 첫 페이지를 사용할지 선택")
    
    page_order = st.sidebar.selectbox(
        "페이지 순서",
        ["1234", "2341"],
        format_func=lambda x: {
            "1234": "1,2,3,4 순서",
            "2341": "2,3,4,1 순서"
        }[x],
        help="최종 PDF의 페이지 순서를 선택"
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
            st.write(f"**최종 크기:** 125×175mm")
            st.write(f"**첫 페이지:** {'사용' if use_first_page else '사용 안함'}")
            st.write(f"**페이지 순서:** {page_order}")
        
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
            
            # 첫 페이지 사용 여부에 따라 조정
            if not use_first_page and expected_pages > 0:
                expected_pages -= 1
            
            # 최대 4페이지까지만 사용
            final_pages = min(expected_pages, 4)
            
            st.info(f"📋 **최종 페이지 수:** {final_pages}페이지 ({page_order} 순서)")
            
            # 여백 설정 (미리보기 이후에 배치)
            st.subheader("📏 여백 설정")
            st.markdown("**책 제본을 위한 여백 설정**")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                margin_top = st.slider("위 (상단 여백)", 5, 40, 15, help="모든 페이지의 상단 여백")
            
            with col2:
                margin_bottom = st.slider("아래 (하단 여백)", 5, 40, 15, help="모든 페이지의 하단 여백")
            
            with col3:
                margin_outer = st.slider("바깥쪽", 5, 40, 20, help="홀수 페이지 오른쪽, 짝수 페이지 왼쪽 여백")
            
            with col4:
                margin_inner = st.slider("안쪽", 5, 40, 15, help="홀수 페이지 왼쪽, 짝수 페이지 오른쪽 여백")
            
            # 여백 설명
            st.markdown("""
            **여백 설명:**
            - **위/아래**: 모든 페이지의 상단/하단 여백
            - **바깥쪽**: 홀수 페이지(1,3,5...)의 오른쪽, 짝수 페이지(2,4,6...)의 왼쪽 여백
            - **안쪽**: 홀수 페이지(1,3,5...)의 왼쪽, 짝수 페이지(2,4,6...)의 오른쪽 여백 (제본 부분)
            """)
            
            # 미리보기 표시
            if show_preview and analysis['is_landscape']:
                st.subheader("🔍 분할 미리보기")
                
                with st.spinner("미리보기 이미지를 생성하는 중..."):
                    try:
                        preview_images = editor.generate_preview_images(
                            tmp_file_path, 
                            split_direction=split_direction,
                            max_pages=preview_pages,
                            use_first_page=use_first_page,
                            page_order=page_order,
                            margin_top=margin_top,
                            margin_bottom=margin_bottom,
                            margin_outer=margin_outer,
                            margin_inner=margin_inner
                        )
                        
                        if preview_images:
                            # 2열로 미리보기 표시
                            cols = st.columns(2)
                            for i, img_info in enumerate(preview_images):
                                col_idx = i % 2
                                with cols[col_idx]:
                                    st.write(f"**{img_info['description']}**")
                                    st.write(f"*여백: {img_info['margin_info']}*")
                                    st.image(
                                        img_info['image_data'], 
                                        caption=f"최종 페이지 {img_info['page_number']} ({'홀수' if img_info['page_number'] % 2 == 1 else '짝수'} 페이지)",
                                        use_column_width=True
                                    )
                        else:
                            st.warning("미리보기 이미지를 생성할 수 없습니다.")
                            
                    except Exception as e:
                        st.error(f"미리보기 생성 중 오류: {str(e)}")
            
            # 편집 버튼
            if st.button("📖 PDF 생성하기", type="primary"):
                with st.spinner("PDF를 생성하는 중..."):
                    try:
                        result_pdf, actual_pages = editor.create_book_pages(
                            tmp_file_path,
                            margin_top=margin_top,
                            margin_bottom=margin_bottom,
                            margin_outer=margin_outer,
                            margin_inner=margin_inner,
                            split_direction=split_direction,
                            use_first_page=use_first_page,
                            page_order=page_order
                        )
                        
                        # 결과 다운로드
                        st.success(f"✅ PDF 생성 완료! (총 {actual_pages}페이지)")
                        
                        # 다운로드 버튼
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="📥 완성된 PDF 다운로드",
                                data=result_pdf.getvalue(),
                                file_name=f"book_{uploaded_file.name}",
                                mime="application/pdf"
                            )
                        
                        with col2:
                            st.info("💡 **팁:** 홀수/짝수 페이지별로 여백이 적용되었습니다.")
                        
                    except Exception as e:
                        st.error(f"❌ 생성 중 오류가 발생했습니다: {str(e)}")
                    finally:
                        # 임시 파일 정리
                        if os.path.exists(tmp_file_path):
                            os.unlink(tmp_file_path)
        
        except Exception as e:
            st.error(f"PDF 분석 중 오류가 발생했습니다: {str(e)}")
    
    # 사용법 안내
    with st.expander("📖 상세 사용법"):
        st.markdown("""
        ### 🎯 사용 프로세스
        
        1. **PDF 파일 업로드**: 편집할 PDF 파일을 선택합니다.
        2. **기본 설정**: 분할 방향과 페이지 설정을 조정합니다.
        3. **미리보기 확인**: 분할된 페이지들을 미리 확인합니다.
        4. **여백 설정**: 책 제본에 맞는 여백을 설정합니다.
        5. **PDF 생성**: 'PDF 생성하기' 버튼을 클릭합니다.
        6. **다운로드**: 완성된 PDF를 다운로드합니다.
        
        ### 📏 여백 설정 가이드
        
        #### 여백의 의미
        - **위**: 모든 페이지의 상단 여백
        - **아래**: 모든 페이지의 하단 여백
        - **바깥쪽**: 페이지의 바깥쪽 여백 (홀수 페이지 오른쪽, 짝수 페이지 왼쪽)
        - **안쪽**: 페이지의 안쪽 여백 (홀수 페이지 왼쪽, 짝수 페이지 오른쪽) - 제본 부분
        
        #### 권장 여백 설정
        
        | 책 유형 | 위 | 아래 | 바깥쪽 | 안쪽 |
        |---------|----|----|--------|------|
        | 일반 소설 | 20mm | 15mm | 20mm | 15mm |
        | 참고서 | 15mm | 15mm | 20mm | 20mm |
        | 만화책 | 10mm | 10mm | 15mm | 12mm |
        | 잡지 | 12mm | 12mm | 18mm | 15mm |
        
        ### 📋 페이지 순서 설명
        
        - **1,2,3,4 순서**: 분할된 페이지를 순서대로 배치
        - **2,3,4,1 순서**: 첫 페이지를 마지막으로 이동하여 배치
        - **첫 페이지 제외**: 분할된 첫 페이지를 사용하지 않음
        
        ### 🔍 미리보기 기능
        
        - **실시간 미리보기**: 설정 변경 시 자동으로 미리보기 업데이트
        - **여백 정보**: 각 페이지별 여백 정보 표시
        - **홀수/짝수 구분**: 페이지 번호에 따른 여백 적용 확인
        
        ### ⚠️ 주의사항
        
        - **안쪽 여백**: 제본을 위해 충분한 안쪽 여백을 확보하세요.
        - **바깥쪽 여백**: 독서 시 손가락이 닿는 부분이므로 적절한 여백을 두세요.
        - **페이지 순서**: 미리보기에서 페이지 순서를 확인한 후 생성하세요.
        """)

if __name__ == "__main__":
    main() 