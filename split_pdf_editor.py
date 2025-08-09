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
from PIL import Image, ImageDraw
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
        # 홀수 페이지(1,3,5...): 왼쪽이 바깥쪽, 오른쪽이 안쪽
        # 짝수 페이지(2,4,6...): 왼쪽이 안쪽, 오른쪽이 바깥쪽
        
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
    
    def add_margin_borders_to_image(self, image_data, page_number, margin_top, margin_bottom, 
                                   margin_outer, margin_inner, 
                                   scale_factor_odd=1.0, offset_x_odd=0, offset_y_odd=0,
                                   scale_factor_even=1.0, offset_x_even=0, offset_y_even=0):
        """이미지에 여백 경계선을 추가하고 축소/이동 효과 적용 (홀수/짝수 페이지별)"""
        
        # 홀수/짝수 페이지에 따라 다른 설정 사용
        if page_number % 2 == 1:  # 홀수 페이지
            scale_factor = scale_factor_odd
            offset_x = offset_x_odd
            offset_y = offset_y_odd
        else:  # 짝수 페이지
            scale_factor = scale_factor_even
            offset_x = offset_x_even
            offset_y = offset_y_even
        
        # PIL Image로 변환
        original_image = Image.open(io.BytesIO(image_data))
        
        # 이미지 크기
        img_width, img_height = original_image.size
        
        # 여백 계산 (픽셀 단위로 변환)
        margins = self.calculate_margins_for_page(page_number, margin_top, margin_bottom, margin_outer, margin_inner)
        
        # 125x175mm 비율로 여백을 픽셀로 변환
        margin_left_px = int((margins['left'] / 125) * img_width)
        margin_right_px = int((margins['right'] / 125) * img_width)
        margin_top_px = int((margins['top'] / 175) * img_height)
        margin_bottom_px = int((margins['bottom'] / 175) * img_height)
        
        # 컨텐츠 영역 계산
        content_width_px = img_width - margin_left_px - margin_right_px
        content_height_px = img_height - margin_top_px - margin_bottom_px
        
        # 축소된 컨텐츠 크기 계산
        scaled_content_width_px = int(content_width_px * scale_factor)
        scaled_content_height_px = int(content_height_px * scale_factor)
        
        # 여유 공간 계산 (축소로 인한)
        extra_space_x_px = content_width_px - scaled_content_width_px
        extra_space_y_px = content_height_px - scaled_content_height_px
        
        # 중앙 정렬 + 사용자 오프셋
        offset_x_px = int((offset_x / 125) * img_width)  # mm를 픽셀로 변환
        offset_y_px = int((offset_y / 175) * img_height)
        
        content_start_x = margin_left_px + (extra_space_x_px // 2) + offset_x_px
        content_start_y = margin_top_px + (extra_space_y_px // 2) + offset_y_px
        
        # 새로운 이미지 생성 (흰색 배경)
        result_image = Image.new('RGB', (img_width, img_height), 'white')
        
        # 축소된 원본 이미지를 새 위치에 붙여넣기
        if scale_factor < 1.0:
            # 원본 이미지를 축소
            resized_original = original_image.resize((scaled_content_width_px, scaled_content_height_px), Image.Resampling.LANCZOS)
            
            # 경계 체크
            paste_x = max(margin_left_px, min(content_start_x, margin_left_px + content_width_px - scaled_content_width_px))
            paste_y = max(margin_top_px, min(content_start_y, margin_top_px + content_height_px - scaled_content_height_px))
            
            result_image.paste(resized_original, (paste_x, paste_y))
        else:
            # 축소 없이 이동만 적용
            paste_x = max(margin_left_px, min(content_start_x, margin_left_px + content_width_px - content_width_px))
            paste_y = max(margin_top_px, min(content_start_y, margin_top_px + content_height_px - content_height_px))
            
            # 컨텐츠 영역만 잘라서 붙여넣기
            content_crop = original_image.crop((0, 0, content_width_px, content_height_px))
            result_image.paste(content_crop, (paste_x, paste_y))
        
        # 경계선 그리기
        draw = ImageDraw.Draw(result_image)
        
        # 홀수/짝수 페이지에 따라 다른 색상의 경계선
        if page_number % 2 == 1:  # 홀수 페이지
            border_color = (255, 0, 0)  # 빨간색
        else:  # 짝수 페이지
            border_color = (0, 0, 255)  # 파란색
        
        border_width = 2
        
        # 상단 경계선
        draw.rectangle([0, margin_top_px-border_width, img_width, margin_top_px+border_width], 
                      fill=border_color)
        
        # 하단 경계선
        draw.rectangle([0, img_height-margin_bottom_px-border_width, img_width, img_height-margin_bottom_px+border_width], 
                      fill=border_color)
        
        # 좌측 경계선
        draw.rectangle([margin_left_px-border_width, 0, margin_left_px+border_width, img_height], 
                      fill=border_color)
        
        # 우측 경계선
        draw.rectangle([img_width-margin_right_px-border_width, 0, img_width-margin_right_px+border_width, img_height], 
                      fill=border_color)
        
        # 이미지를 바이트로 변환하여 반환
        output = io.BytesIO()
        result_image.save(output, format='PNG')
        return output.getvalue()
    
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
                              margin_top=15, margin_bottom=15, margin_outer=15, margin_inner=15,
                              scale_factor_odd=1.0, offset_x_odd=0, offset_y_odd=0,
                              scale_factor_even=1.0, offset_x_even=0, offset_y_even=0):
        """미리보기용 이미지 생성 (홀수/짝수 페이지별 설정 포함)"""
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
        
        # 최종 미리보기 이미지 생성 (홀수/짝수별 여백 정보 및 경계선 포함)
        preview_images = []
        for i, page_info in enumerate(reordered_pages[:max_pages]):
            page_number = i + 1
            margins = self.calculate_margins_for_page(page_number, margin_top, margin_bottom, margin_outer, margin_inner)
            
            # 홀수/짝수별 설정 정보
            if page_number % 2 == 1:  # 홀수 페이지
                current_scale = scale_factor_odd
                current_offset_x = offset_x_odd
                current_offset_y = offset_y_odd
                page_type = "홀수"
            else:  # 짝수 페이지
                current_scale = scale_factor_even
                current_offset_x = offset_x_even
                current_offset_y = offset_y_even
                page_type = "짝수"
            
            # 여백 경계선이 추가된 이미지 생성 (홀수/짝수별 축소/이동 효과 포함)
            bordered_image_data = self.add_margin_borders_to_image(
                page_info['image_data'], page_number, margin_top, margin_bottom, margin_outer, margin_inner,
                scale_factor_odd, offset_x_odd, offset_y_odd,
                scale_factor_even, offset_x_even, offset_y_even
            )
            
            preview_images.append({
                'page_number': page_number,
                'image_data': bordered_image_data,
                'description': f"페이지 {page_number} ({page_info['description']})",
                'margins': margins,
                'margin_info': f"위{margins['top']}mm, 아래{margins['bottom']}mm, 왼쪽{margins['left']}mm, 오른쪽{margins['right']}mm",
                'page_type': page_type,
                'scale_info': f"축소{int(current_scale*100)}%, 이동({current_offset_x:+.0f},{current_offset_y:+.0f}mm)"
            })
        
        return preview_images
    
    def create_book_pages(self, content_pdf_path, margin_top=15, margin_bottom=15, 
                         margin_outer=15, margin_inner=15, split_direction='vertical',
                         use_first_page=True, page_order="1234", 
                         scale_factor_odd=1.0, offset_x_odd=0, offset_y_odd=0,
                         scale_factor_even=1.0, offset_x_even=0, offset_y_even=0):
        """PDF 내용을 책 페이지 크기로 변환 - 홀수/짝수별 설정 적용"""
        
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
        
        # 페이지 순서에 따라 재배열 (모든 페이지에 적용)
        order_map = {
            "1234": lambda pages: pages,  # 순서 그대로
            "2341": lambda pages: pages[1:] + [pages[0]] if len(pages) > 0 else pages  # 첫 페이지를 마지막으로
        }
        
        if page_order in order_map:
            reordered_pages = order_map[page_order](all_pages)
        else:
            reordered_pages = all_pages
        
        total_pages = 0
        
        # 모든 페이지를 PDF에 추가 (홀수/짝수별 여백 및 조정 적용)
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
                
                # 이미지를 페이지에 추가 (홀수/짝수별 축소 및 이동 적용)
                self.add_page_to_book(
                    c, img_path, content_width, content_height, 
                    margin_left_pt, margin_bottom_pt, page_number,
                    scale_factor_odd, offset_x_odd, offset_y_odd,
                    scale_factor_even, offset_x_even, offset_y_even
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
                        margin_left_pt, margin_bottom_pt, page_number,
                        scale_factor_odd=1.0, offset_x_odd=0, offset_y_odd=0,
                        scale_factor_even=1.0, offset_x_even=0, offset_y_even=0):
        """이미지를 책 페이지에 추가 (홀수/짝수 페이지별 축소 및 이동 기능)"""
        
        # 홀수/짝수 페이지에 따라 다른 설정 사용
        if page_number % 2 == 1:  # 홀수 페이지
            scale_factor = scale_factor_odd
            offset_x = offset_x_odd
            offset_y = offset_y_odd
        else:  # 짝수 페이지
            scale_factor = scale_factor_even
            offset_x = offset_x_even
            offset_y = offset_y_even
        
        # 원본 이미지 크기 확인
        with Image.open(image_path) as img:
            original_width, original_height = img.size
        
        # 축소된 크기 계산 (실제 컨텐츠 영역 내에서)
        scaled_content_width = content_width * scale_factor
        scaled_content_height = content_height * scale_factor
        
        # 이미지를 축소된 크기에 맞게 조정
        adjusted_img_path = self.adjust_image_for_book(
            image_path, scaled_content_width, scaled_content_height, 'fit_both'
        )
        
        # 조정된 이미지의 실제 크기 확인
        with Image.open(adjusted_img_path) as adjusted_img:
            actual_img_width, actual_img_height = adjusted_img.size
        
        # PIL 이미지 크기를 포인트로 변환 (72 DPI 기준)
        actual_width_pt = actual_img_width * 72 / 72  # 1:1 비율
        actual_height_pt = actual_img_height * 72 / 72
        
        # 축소로 인한 여유 공간 계산
        extra_space_x = content_width - actual_width_pt
        extra_space_y = content_height - actual_height_pt
        
        # 중앙 정렬을 위한 기본 오프셋
        center_offset_x = extra_space_x / 2
        center_offset_y = extra_space_y / 2
        
        # 사용자 지정 오프셋 (mm를 포인트로 변환)
        user_offset_x = self.convert_mm_to_points(offset_x)
        user_offset_y = self.convert_mm_to_points(offset_y)
        
        # 최종 위치 계산
        final_x = margin_left_pt + center_offset_x + user_offset_x
        final_y = margin_bottom_pt + center_offset_y + user_offset_y
        
        # 경계 체크 (이미지가 페이지를 벗어나지 않도록)
        max_x = margin_left_pt + content_width - actual_width_pt
        max_y = margin_bottom_pt + content_height - actual_height_pt
        
        final_x = max(margin_left_pt, min(final_x, max_x))
        final_y = max(margin_bottom_pt, min(final_y, max_y))
        
        # 조정된 이미지를 새 페이지에 그리기
        canvas_obj.drawImage(adjusted_img_path, final_x, final_y, 
                           width=actual_width_pt, height=actual_height_pt)
        
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
                margin_inner = st.slider("안쪽", 5, 40, 15, help="홀수 페이지 왼쪽, 짝수 페이지 오른쪽 여백 (제본 부분)")
            
            # 여백 설명
            st.markdown("""
            **여백 설명:**
            - **위/아래**: 모든 페이지의 상단/하단 여백
            - **바깥쪽**: 홀수 페이지(1,3,5...)의 왼쪽, 짝수 페이지(2,4,6...)의 오른쪽 여백
            - **안쪽**: 홀수 페이지(1,3,5...)의 오른쪽, 짝수 페이지(2,4,6...)의 왼쪽 여백 (제본 부분)
            """)
            
            # 페이지 조정 설정
            st.subheader("🎛️ 페이지 조정")
            st.markdown("**홀수/짝수 페이지별 축소 및 위치 조정**")
            
            # 홀수 페이지 설정
            st.markdown("#### 📄 홀수 페이지 (1, 3, 5...) - 빨간색 경계선")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                scale_factor_odd = st.slider("홀수 축소 비율", 0.5, 1.0, 1.0, 0.05, help="홀수 페이지 축소 비율 (1.0 = 원본 크기)")
            
            with col2:
                offset_x_odd = st.slider("홀수 좌우 이동", -20, 20, 0, 1, help="홀수 페이지를 좌우로 이동 (mm)")
            
            with col3:
                offset_y_odd = st.slider("홀수 상하 이동", -20, 20, 0, 1, help="홀수 페이지를 상하로 이동 (mm)")
            
            with col4:
                st.markdown("**홀수 페이지 상태**")
                st.write(f"축소: {int(scale_factor_odd*100)}%")
                direction_odd = ""
                if offset_x_odd > 0:
                    direction_odd += "→"
                elif offset_x_odd < 0:
                    direction_odd += "←"
                if offset_y_odd > 0:
                    direction_odd += "↑"
                elif offset_y_odd < 0:
                    direction_odd += "↓"
                st.write(f"이동: {direction_odd if direction_odd else '중앙'}")
            
            # 짝수 페이지 설정
            st.markdown("#### 📄 짝수 페이지 (2, 4, 6...) - 파란색 경계선")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                scale_factor_even = st.slider("짝수 축소 비율", 0.5, 1.0, 1.0, 0.05, help="짝수 페이지 축소 비율 (1.0 = 원본 크기)")
            
            with col2:
                offset_x_even = st.slider("짝수 좌우 이동", -20, 20, 0, 1, help="짝수 페이지를 좌우로 이동 (mm)")
            
            with col3:
                offset_y_even = st.slider("짝수 상하 이동", -20, 20, 0, 1, help="짝수 페이지를 상하로 이동 (mm)")
            
            with col4:
                st.markdown("**짝수 페이지 상태**")
                st.write(f"축소: {int(scale_factor_even*100)}%")
                direction_even = ""
                if offset_x_even > 0:
                    direction_even += "→"
                elif offset_x_even < 0:
                    direction_even += "←"
                if offset_y_even > 0:
                    direction_even += "↑"
                elif offset_y_even < 0:
                    direction_even += "↓"
                st.write(f"이동: {direction_even if direction_even else '중앙'}")
            
            # 페이지 조정 설명
            st.markdown("""
            **페이지 조정 설명:**
            - **축소 비율**: 페이지 내용의 크기를 조절합니다 (여백은 그대로 유지)
            - **좌우 이동**: 양수는 오른쪽, 음수는 왼쪽으로 이동
            - **상하 이동**: 양수는 위쪽, 음수는 아래쪽으로 이동
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
                            margin_inner=margin_inner,
                            scale_factor_odd=scale_factor_odd,
                            offset_x_odd=offset_x_odd,
                            offset_y_odd=offset_y_odd,
                            scale_factor_even=scale_factor_even,
                            offset_x_even=offset_x_even,
                            offset_y_even=offset_y_even
                        )
                        
                        if preview_images:
                            # 2열로 미리보기 표시
                            cols = st.columns(2)
                            for i, img_info in enumerate(preview_images):
                                col_idx = i % 2
                                with cols[col_idx]:
                                    st.write(f"**{img_info['description']}**")
                                    st.write(f"*여백: {img_info['margin_info']}*")
                                    st.write(f"*조정: {img_info['scale_info']}*")
                                    
                                    # 홀수/짝수에 따른 색상 표시
                                    if img_info['page_type'] == '홀수':
                                        border_info = "🔴 홀수 페이지 (빨간 경계선)"
                                    else:
                                        border_info = "🔵 짝수 페이지 (파란 경계선)"
                                    
                                    st.image(
                                        img_info['image_data'], 
                                        caption=f"최종 페이지 {img_info['page_number']} - {border_info}",
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
                            page_order=page_order,
                            scale_factor_odd=scale_factor_odd,
                            offset_x_odd=offset_x_odd,
                            offset_y_odd=offset_y_odd,
                            scale_factor_even=scale_factor_even,
                            offset_x_even=offset_x_even,
                            offset_y_even=offset_y_even
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