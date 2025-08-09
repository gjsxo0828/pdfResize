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
        """가로 페이지를 세로로 분할 (고해상도)"""
        rect = page.rect
        
        if split_direction == 'vertical':
            # 세로로 분할 (좌우 분할)
            left_rect = fitz.Rect(0, 0, rect.width/2, rect.height)
            right_rect = fitz.Rect(rect.width/2, 0, rect.width, rect.height)
            
            # 초고해상도 렌더링 (600 DPI 수준)
            high_res_matrix = fitz.Matrix(8.0, 8.0)  # 4.0에서 8.0으로 증가
            left_page = page.get_pixmap(clip=left_rect, matrix=high_res_matrix)
            right_page = page.get_pixmap(clip=right_rect, matrix=high_res_matrix)
            
            return left_page, right_page
        else:
            # 가로로 분할 (상하 분할)
            top_rect = fitz.Rect(0, 0, rect.width, rect.height/2)
            bottom_rect = fitz.Rect(0, rect.height/2, rect.width, rect.height)
            
            # 초고해상도 렌더링 (600 DPI 수준)
            high_res_matrix = fitz.Matrix(8.0, 8.0)  # 4.0에서 8.0으로 증가
            top_page = page.get_pixmap(clip=top_rect, matrix=high_res_matrix)
            bottom_page = page.get_pixmap(clip=bottom_rect, matrix=high_res_matrix)
            
            return top_page, bottom_page
    
    def split_landscape_page_preview(self, page, split_direction='vertical'):
        """가로 페이지를 세로로 분할 (미리보기용 - 빠른 로딩)"""
        rect = page.rect
        
        if split_direction == 'vertical':
            # 세로로 분할 (좌우 분할)
            left_rect = fitz.Rect(0, 0, rect.width/2, rect.height)
            right_rect = fitz.Rect(rect.width/2, 0, rect.width, rect.height)
            
            # 미리보기용 낮은 해상도 (75 DPI 수준 - 빠른 로딩)
            preview_matrix = fitz.Matrix(1.0, 1.0)  # 미리보기용으로 대폭 낮춤
            left_page = page.get_pixmap(clip=left_rect, matrix=preview_matrix)
            right_page = page.get_pixmap(clip=right_rect, matrix=preview_matrix)
            
            return left_page, right_page
        else:
            # 가로로 분할 (상하 분할)
            top_rect = fitz.Rect(0, 0, rect.width, rect.height/2)
            bottom_rect = fitz.Rect(0, rect.height/2, rect.width, rect.height)
            
            # 미리보기용 낮은 해상도 (빠른 로딩)
            preview_matrix = fitz.Matrix(1.0, 1.0)
            top_page = page.get_pixmap(clip=top_rect, matrix=preview_matrix)
            bottom_page = page.get_pixmap(clip=bottom_rect, matrix=preview_matrix)
            
            return top_page, bottom_page
    
    def generate_preview_images(self, content_pdf_path, split_direction='vertical', 
                              max_pages=4, use_first_page=True, page_order="1234",
                              margin_top=15, margin_bottom=15, margin_outer=15, margin_inner=15,
                              scale_factor_odd=1.0, offset_x_odd=0, offset_y_odd=0,
                              scale_factor_even=1.0, offset_x_even=0, offset_y_even=0,
                              show_page_numbers=True, progress_callback=None):
        """미리보기용 이미지 생성 (홀수/짝수 페이지별 설정 포함)"""
        doc = fitz.open(content_pdf_path)
        all_pages = []
        total_pages = len(doc)
        
        # 모든 분할된 페이지 생성 (고정 번호 부여)
        for page_num in range(total_pages):
            if progress_callback:
                progress_callback(page_num + 1, total_pages, f"페이지 {page_num + 1}/{total_pages} 분할 중...")
            
            page = doc[page_num]
            rect = page.rect
            
            # 가로 페이지인지 확인
            if rect.width > rect.height:
                # 가로 페이지를 분할 (미리보기용 해상도)
                left_pix, right_pix = self.split_landscape_page_preview(page, split_direction)
                
                # 좌측 페이지
                left_img_data = left_pix.tobytes("png")
                all_pages.append({
                    'image_data': left_img_data,
                    'description': f"원본 {page_num + 1}페이지 좌측",
                    'original_page': page_num,
                    'split_part': 'left',
                    'fixed_number': len(all_pages) + 1  # 고정 번호 부여
                })
                
                # 우측 페이지
                right_img_data = right_pix.tobytes("png")
                all_pages.append({
                    'image_data': right_img_data,
                    'description': f"원본 {page_num + 1}페이지 우측",
                    'original_page': page_num,
                    'split_part': 'right',
                    'fixed_number': len(all_pages) + 1  # 고정 번호 부여
                })
                    
            else:
                # 세로 페이지는 그대로 (미리보기용 낮은 해상도)
                preview_matrix = fitz.Matrix(1.0, 1.0)  # 미리보기용 낮은 해상도
                pix = page.get_pixmap(matrix=preview_matrix)
                img_data = pix.tobytes("png")
                all_pages.append({
                    'image_data': img_data,
                    'description': f"원본 {page_num + 1}페이지",
                    'original_page': page_num,
                    'split_part': 'single',
                    'fixed_number': len(all_pages) + 1  # 고정 번호 부여
                })
        
        doc.close()
        
        if progress_callback:
            progress_callback(total_pages, total_pages, "페이지 순서 정리 중...")
        
        # 첫 페이지 사용 여부에 따라 조정 (고정 번호 재계산)
        if not use_first_page and len(all_pages) > 0:
            removed_page = all_pages.pop(0)  # 첫 페이지 제거
            # 나머지 페이지들의 고정 번호를 1씩 앞당김
            for page_info in all_pages:
                page_info['fixed_number'] -= 1
        
        # 페이지 순서에 따라 재배열 (고정 번호는 그대로 유지)
        if page_order == "2341":
            # 2341 순서: 4페이지 단위로 2,3,4,1 패턴 적용
            reordered_pages = []
            for i in range(0, len(all_pages), 4):
                # 현재 4페이지 블록 가져오기
                current_block = all_pages[i:i+4]
                if len(current_block) >= 4:
                    # 2,3,4,1 순서로 재배열
                    reordered_block = [current_block[1], current_block[2], current_block[3], current_block[0]]
                    reordered_pages.extend(reordered_block)
                else:
                    # 4개 미만인 경우 그대로 추가
                    reordered_pages.extend(current_block)
        else:
            # 1234 순서: 순서 그대로
            reordered_pages = all_pages
        
        # 최종 미리보기 이미지 생성 (홀수/짝수별 여백 정보 및 경계선 포함)
        preview_images = []
        selected_pages = reordered_pages[:max_pages]
        
        for i, page_info in enumerate(selected_pages):
            if progress_callback:
                progress_callback(i + 1, len(selected_pages), f"미리보기 {i + 1}/{len(selected_pages)} 생성 중...")
            
            # 미리보기에서의 페이지 번호 (표시용)
            display_page_number = i + 1
            # 고정된 실제 페이지 번호
            fixed_page_number = page_info['fixed_number']
            
            margins = self.calculate_margins_for_page(display_page_number, margin_top, margin_bottom, margin_outer, margin_inner)
            
            # 홀수/짝수별 설정 정보 (미리보기 페이지 번호 기준)
            if display_page_number % 2 == 1:  # 홀수 페이지
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
                page_info['image_data'], display_page_number, margin_top, margin_bottom, margin_outer, margin_inner,
                scale_factor_odd, offset_x_odd, offset_y_odd,
                scale_factor_even, offset_x_even, offset_y_even
            )
            
            # 원본 페이지 번호 오버레이 추가 (고정 번호 사용)
            if show_page_numbers:
                bordered_image_data = self.add_page_number_overlay_with_fixed_number(
                    bordered_image_data, fixed_page_number
                )
            
            preview_images.append({
                'page_number': display_page_number,
                'fixed_page_number': fixed_page_number,
                'image_data': bordered_image_data,
                'description': f"페이지 {display_page_number} ({page_info['description']})",
                'margins': margins,
                'margin_info': f"위{margins['top']}mm, 아래{margins['bottom']}mm, 왼쪽{margins['left']}mm, 오른쪽{margins['right']}mm",
                'page_type': page_type,
                'scale_info': f"축소{int(current_scale*100)}%, 이동({current_offset_x:+.0f},{current_offset_y:+.0f}mm)"
            })
        
        if progress_callback:
            progress_callback(len(selected_pages), len(selected_pages), "미리보기 완료!")
        
        return preview_images
    
    def create_book_pages(self, content_pdf_path, book_width_mm=125, book_height_mm=175, 
                         split_direction='vertical', use_first_page=True, page_order="1234",
                         margin_top=15, margin_bottom=15, margin_outer=15, margin_inner=15,
                         scale_factor_odd=1.0, offset_x_odd=0, offset_y_odd=0,
                         scale_factor_even=1.0, offset_x_even=0, offset_y_even=0,
                         show_borders=False, progress_callback=None):
        """PDF를 분할하여 책 형태로 변환 (벡터 그래픽 보존)"""
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfutils
        from PyPDF2 import PdfReader, PdfWriter
        import tempfile
        import os
        
        # mm를 포인트로 변환 (1mm = 2.834645669 points)
        book_width_pt = book_width_mm * 2.834645669
        book_height_pt = book_height_mm * 2.834645669
        
        # 새 PDF 생성
        buffer = io.BytesIO()
        
        try:
            # PyPDF2로 원본 PDF 읽기
            reader = PdfReader(content_pdf_path)
            writer = PdfWriter()
            
            total_pages = len(reader.pages)
            all_split_pages = []
            
            if progress_callback:
                progress_callback(0, total_pages, "PDF 페이지 분할 시작...")
            
            # 각 페이지를 분할
            for page_num, page in enumerate(reader.pages):
                if progress_callback:
                    progress_callback(page_num + 1, total_pages, f"페이지 {page_num + 1}/{total_pages} 분할 중...")
                
                # 페이지 크기 확인
                media_box = page.mediabox
                page_width = float(media_box.width)
                page_height = float(media_box.height)
                
                # 가로 페이지인지 확인
                if page_width > page_height:
                    # 가로 페이지를 분할
                    if split_direction == 'vertical':
                        # 좌측 페이지
                        left_page = page
                        left_page.mediabox.upper_right = (page_width / 2, page_height)
                        all_split_pages.append(('split_left', left_page, page_num))
                        
                        # 우측 페이지 (새로운 페이지 객체 생성)
                        right_page = reader.pages[page_num]  # 원본 페이지 복사
                        right_page.mediabox.lower_left = (page_width / 2, 0)
                        all_split_pages.append(('split_right', right_page, page_num))
                    else:
                        # 상하 분할
                        # 상단 페이지
                        top_page = page
                        top_page.mediabox.lower_left = (0, page_height / 2)
                        all_split_pages.append(('split_top', top_page, page_num))
                        
                        # 하단 페이지
                        bottom_page = reader.pages[page_num]
                        bottom_page.mediabox.upper_right = (page_width, page_height / 2)
                        all_split_pages.append(('split_bottom', bottom_page, page_num))
                else:
                    # 세로 페이지는 그대로
                    all_split_pages.append(('single', page, page_num))
            
            if progress_callback:
                progress_callback(total_pages, total_pages, "페이지 순서 정리 중...")
            
            # 첫 페이지 사용 여부에 따라 조정
            if not use_first_page and len(all_split_pages) > 0:
                all_split_pages = all_split_pages[1:]
            
            # 페이지 순서에 따라 재배열
            if page_order == "2341":
                reordered_pages = []
                for i in range(0, len(all_split_pages), 4):
                    current_block = all_split_pages[i:i+4]
                    if len(current_block) >= 4:
                        reordered_block = [current_block[1], current_block[2], current_block[3], current_block[0]]
                        reordered_pages.extend(reordered_block)
                    else:
                        reordered_pages.extend(current_block)
            else:
                reordered_pages = all_split_pages
            
            pages_added = 0
            total_pages_to_process = len(reordered_pages)
            
            # 각 페이지를 새 PDF에 추가
            for page_idx, (split_type, page, original_page_num) in enumerate(reordered_pages):
                if progress_callback:
                    progress_callback(page_idx + 1, total_pages_to_process, f"PDF 생성 중... {page_idx + 1}/{total_pages_to_process}")
                
                # 페이지 번호 (1부터 시작)
                page_number = page_idx + 1
                
                # 해당 페이지의 여백 계산
                margins = self.calculate_margins_for_page(page_number, margin_top, margin_bottom, margin_outer, margin_inner)
                
                # 홀수/짝수별 스케일 팩터 선택
                if page_number % 2 == 1:
                    scale_factor = scale_factor_odd
                    offset_x = offset_x_odd
                    offset_y = offset_y_odd
                else:
                    scale_factor = scale_factor_even
                    offset_x = offset_x_even
                    offset_y = offset_y_even
                
                # 새 페이지 크기로 스케일링
                scaled_page = self.scale_page_to_book_size(
                    page, book_width_pt, book_height_pt, margins, 
                    scale_factor, offset_x, offset_y
                )
                
                writer.add_page(scaled_page)
                pages_added += 1
            
            if progress_callback:
                progress_callback(total_pages_to_process, total_pages_to_process, f"총 {pages_added}개 페이지 추가됨")
            
            # 페이지가 하나도 추가되지 않은 경우 빈 페이지 추가
            if pages_added == 0:
                from reportlab.pdfgen import canvas
                temp_buffer = io.BytesIO()
                temp_canvas = canvas.Canvas(temp_buffer, pagesize=(book_width_pt, book_height_pt))
                temp_canvas.showPage()
                temp_canvas.save()
                temp_buffer.seek(0)
                temp_reader = PdfReader(temp_buffer)
                writer.add_page(temp_reader.pages[0])
                pages_added = 1
            
            if progress_callback:
                progress_callback(total_pages_to_process, total_pages_to_process, "PDF 저장 중...")
            
            # PDF 저장
            writer.write(buffer)
            buffer.seek(0)
            
        except Exception as e:
            print(f"PDF 생성 중 오류: {e}")
            raise
        
        if progress_callback:
            progress_callback(total_pages_to_process, total_pages_to_process, "PDF 생성 완료!")
        
        # 전체 버퍼 내용 반환
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data
    
    def scale_page_to_book_size(self, page, book_width_pt, book_height_pt, margins, scale_factor, offset_x, offset_y):
        """페이지를 책 크기로 스케일링하고 여백 적용"""
        from PyPDF2 import Transformation
        
        # 여백을 포인트로 변환
        margin_left_pt = margins['left'] * 2.834645669
        margin_right_pt = margins['right'] * 2.834645669  
        margin_top_pt = margins['top'] * 2.834645669
        margin_bottom_pt = margins['bottom'] * 2.834645669
        
        # 사용 가능한 콘텐츠 영역
        content_width = book_width_pt - margin_left_pt - margin_right_pt
        content_height = book_height_pt - margin_top_pt - margin_bottom_pt
        
        # 페이지 크기
        media_box = page.mediabox
        page_width = float(media_box.width)
        page_height = float(media_box.height)
        
        # 스케일링 비율 계산 (콘텐츠 영역에 맞춤)
        scale_x = (content_width * scale_factor) / page_width
        scale_y = (content_height * scale_factor) / page_height
        scale = min(scale_x, scale_y)  # 비율 유지
        
        # 오프셋 계산 (mm를 포인트로 변환)
        offset_x_pt = offset_x * 2.834645669
        offset_y_pt = offset_y * 2.834645669
        
        # 중앙 정렬을 위한 오프셋
        scaled_width = page_width * scale
        scaled_height = page_height * scale
        center_x = margin_left_pt + (content_width - scaled_width) / 2 + offset_x_pt
        center_y = margin_bottom_pt + (content_height - scaled_height) / 2 + offset_y_pt
        
        # 변환 매트릭스 적용
        transformation = Transformation().scale(scale, scale).translate(center_x / scale, center_y / scale)
        page.add_transformation(transformation)
        
        # 새 페이지 크기 설정
        page.mediabox.lower_left = (0, 0)
        page.mediabox.upper_right = (book_width_pt, book_height_pt)
        
        return page
    
    def save_pixmap_to_image(self, pixmap, filename):
        """Pixmap을 최고품질 이미지 파일로 저장"""
        # PNG로 최고품질 저장
        img_data = pixmap.tobytes("png")
        
        # PIL을 통해 최고품질로 재저장
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as img_file:
            # 원본 PNG 데이터를 PIL로 열어서 최고품질로 재저장
            pil_img = Image.open(io.BytesIO(img_data))
            # 최고품질 PNG로 저장 (압축 완전 비활성화, 600 DPI 설정)
            pil_img.save(img_file.name, 'PNG', compress_level=0, optimize=False, dpi=(600, 600))
            return img_file.name
    
    def add_page_to_book(self, canvas_obj, image_path, content_width, content_height, 
                        margin_left_pt, margin_bottom_pt, page_number,
                        scale_factor_odd=1.0, offset_x_odd=0, offset_y_odd=0,
                        scale_factor_even=1.0, offset_x_even=0, offset_y_even=0,
                        show_borders=False, book_width=None, book_height=None):
        """이미지를 책 페이지에 추가 (홀수/짝수 페이지별 축소 및 이동 기능, 경계선 옵션)"""
        
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
        # 초고해상도를 위해 PIL Image 객체로 직접 그리기
        from reportlab.lib.utils import ImageReader
        
        # PIL Image 객체로 열어서 초고해상도 유지
        with Image.open(adjusted_img_path) as pil_img:
            # 이미지 해상도 정보 확인 및 설정
            if hasattr(pil_img, 'info') and 'dpi' in pil_img.info:
                pass  # DPI 정보 확인됨
            
            img_reader = ImageReader(pil_img)
            
            # 고품질 이미지 그리기 (mask 사용으로 투명도 처리)
            canvas_obj.drawImage(img_reader, final_x, final_y, 
                               width=actual_width_pt, height=actual_height_pt,
                               preserveAspectRatio=True, anchor='c', mask='auto')
        
        # 여백 경계선 그리기 (옵션)
        if show_borders and book_width and book_height:
            # 홀수/짝수에 따른 색상 선택
            if page_number % 2 == 1:  # 홀수 페이지
                border_color = (1, 0, 0)  # 빨간색 (RGB 0-1 범위)
            else:  # 짝수 페이지
                border_color = (0, 0, 1)  # 파란색
            
            canvas_obj.setStrokeColorRGB(*border_color)
            canvas_obj.setLineWidth(1)
            
            # 여백 경계선 그리기
            margin_right_pt = book_width - margin_left_pt - content_width
            margin_top_pt = book_height - margin_bottom_pt - content_height
            
            # 상단 경계선
            canvas_obj.line(0, book_height - margin_top_pt, book_width, book_height - margin_top_pt)
            # 하단 경계선  
            canvas_obj.line(0, margin_bottom_pt, book_width, margin_bottom_pt)
            # 좌측 경계선
            canvas_obj.line(margin_left_pt, 0, margin_left_pt, book_height)
            # 우측 경계선
            canvas_obj.line(book_width - margin_right_pt, 0, book_width - margin_right_pt, book_height)
        
        canvas_obj.showPage()
        
        # 임시 파일 정리 (예외 처리 추가)
        if adjusted_img_path != image_path:
            try:
                if os.path.exists(adjusted_img_path):
                    os.unlink(adjusted_img_path)
            except Exception as e:
                # 임시 파일 삭제 실패는 무시 (PDF 생성에는 영향 없음)
                pass
    
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
            
            # 최고품질 이미지 리사이즈 (LANCZOS보다 더 고품질인 알고리즘 사용)
            if hasattr(Image.Resampling, 'LANCZOS'):
                resample_filter = Image.Resampling.LANCZOS
            else:
                resample_filter = Image.LANCZOS
                
            resized_img = img.resize((int(new_width), int(new_height)), resample_filter)
            
            # 새 이미지 파일로 최고품질 저장 (DPI 정보 보존)
            output_path = image_path.replace('.png', '_resized.png')
            
            # 원본 DPI 정보 보존
            dpi_info = img.info.get('dpi', (600, 600))  # 기본값 600 DPI
            
            # PNG 압축을 완전히 비활성화하여 최고품질 보장 (0=무압축)
            resized_img.save(output_path, 'PNG', compress_level=0, optimize=False, dpi=dpi_info)
            
            return output_path

    def add_page_number_overlay(self, image_data, original_page, split_part):
        """이미지 하단에 원본 페이지 번호 오버레이 추가"""
        from PIL import ImageFont, ImageDraw
        
        # PIL Image로 변환
        image = Image.open(io.BytesIO(image_data))
        draw = ImageDraw.Draw(image)
        
        # 이미지 크기
        img_width, img_height = image.size
        
        # 페이지 번호 텍스트 생성
        if split_part == 'left':
            page_text = f"원본 {original_page + 1}페이지 (좌측)"
        elif split_part == 'right':
            page_text = f"원본 {original_page + 1}페이지 (우측)"
        else:
            page_text = f"원본 {original_page + 1}페이지"
        
        # 폰트 크기 계산 (이미지 크기에 비례)
        font_size = max(16, min(32, img_width // 25))
        
        try:
            # 시스템 기본 폰트 사용 시도
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                # Windows 기본 폰트
                font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", font_size)
            except:
                # 기본 폰트 사용
                font = ImageFont.load_default()
        
        # 텍스트 크기 계산
        bbox = draw.textbbox((0, 0), page_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 텍스트 위치 (하단 중앙)
        text_x = (img_width - text_width) // 2
        text_y = img_height - text_height - 10
        
        # 배경 박스 그리기 (반투명 검은색)
        padding = 5
        box_coords = [
            text_x - padding,
            text_y - padding,
            text_x + text_width + padding,
            text_y + text_height + padding
        ]
        
        # 반투명 배경을 위해 별도 이미지 생성
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # 반투명 검은색 배경
        overlay_draw.rectangle(box_coords, fill=(0, 0, 0, 180))
        
        # 원본 이미지가 RGB 모드가 아니면 변환
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # 오버레이 합성
        image = Image.alpha_composite(image, overlay)
        
        # 텍스트 그리기 (흰색)
        final_draw = ImageDraw.Draw(image)
        final_draw.text((text_x, text_y), page_text, fill=(255, 255, 255, 255), font=font)
        
        # RGB로 변환 (PNG 저장을 위해)
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])  # 알파 채널을 마스크로 사용
            image = background
        
        # 이미지를 바이트로 변환하여 반환
        output = io.BytesIO()
        image.save(output, format='PNG')
        return output.getvalue()

    def add_page_number_overlay_with_fixed_number(self, image_data, fixed_page_number):
        """이미지 하단에 고정된 페이지 번호 오버레이 추가"""
        from PIL import ImageFont, ImageDraw
        
        # PIL Image로 변환
        image = Image.open(io.BytesIO(image_data))
        draw = ImageDraw.Draw(image)
        
        # 이미지 크기
        img_width, img_height = image.size
        
        # 페이지 번호 텍스트 생성
        page_text = f"페이지 {fixed_page_number}"
        
        # 폰트 크기 계산 (이미지 크기에 비례)
        font_size = max(16, min(32, img_width // 25))
        
        try:
            # 시스템 기본 폰트 사용 시도
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                # Windows 기본 폰트
                font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", font_size)
            except:
                # 기본 폰트 사용
                font = ImageFont.load_default()
        
        # 텍스트 크기 계산
        bbox = draw.textbbox((0, 0), page_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 텍스트 위치 (하단 중앙)
        text_x = (img_width - text_width) // 2
        text_y = img_height - text_height - 10
        
        # 배경 박스 그리기 (반투명 검은색)
        padding = 5
        box_coords = [
            text_x - padding,
            text_y - padding,
            text_x + text_width + padding,
            text_y + text_height + padding
        ]
        
        # 반투명 배경을 위해 별도 이미지 생성
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # 반투명 검은색 배경
        overlay_draw.rectangle(box_coords, fill=(0, 0, 0, 180))
        
        # 원본 이미지가 RGB 모드가 아니면 변환
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # 오버레이 합성
        image = Image.alpha_composite(image, overlay)
        
        # 텍스트 그리기 (흰색)
        final_draw = ImageDraw.Draw(image)
        final_draw.text((text_x, text_y), page_text, fill=(255, 255, 255, 255), font=font)
        
        # RGB로 변환 (PNG 저장을 위해)
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])  # 알파 채널을 마스크로 사용
            image = background
        
        # 이미지를 바이트로 변환하여 반환
        output = io.BytesIO()
        image.save(output, format='PNG')
        return output.getvalue()

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
        help="최종 PDF의 페이지 순서를 선택 (처음 4페이지 기준으로 재배열)"
    )
    
    # 미리보기 설정
    st.sidebar.subheader("미리보기 설정")
    show_preview = st.sidebar.checkbox("분할 미리보기 표시", value=True)
    show_page_numbers = st.sidebar.checkbox("원본 페이지 번호 표시", value=True, 
                                          help="미리보기 이미지 하단에 원본 페이지 번호 표시")
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "PDF 파일을 선택하세요",
        type=['pdf'],
        help="편집할 PDF 파일을 업로드하세요"
    )
    
    if uploaded_file is not None:
        # 파일 정보 표시 (접힌 상태)
        with st.expander("📄 파일 정보", expanded=False):
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
            
            # PDF 분석 결과 (접힌 상태)
            with st.expander("📊 PDF 분석 결과", expanded=False):
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
            col1, col2 = st.columns(2)
            with col1:
                st.success("🎯 **PDF 저장**: 600 DPI 초고해상도")
            with col2:
                st.info("⚡ **미리보기**: 75 DPI (초고속 로딩)")
            
            # 여백 설정 (접힌 상태)
            with st.expander("📏 여백 설정", expanded=False):
                st.markdown("**책 제본을 위한 여백 설정**")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    margin_top = st.number_input(
                        "위 (상단 여백)", 
                        min_value=0, 
                        max_value=50, 
                        value=15, 
                        step=1,
                        help="모든 페이지의 상단 여백 (mm)"
                    )
                
                with col2:
                    margin_bottom = st.number_input(
                        "아래 (하단 여백)", 
                        min_value=0, 
                        max_value=50, 
                        value=15, 
                        step=1,
                        help="모든 페이지의 하단 여백 (mm)"
                    )
                
                with col3:
                    margin_outer = st.number_input(
                        "바깥쪽", 
                        min_value=0, 
                        max_value=50, 
                        value=20, 
                        step=1,
                        help="홀수 페이지 오른쪽, 짝수 페이지 왼쪽 여백 (mm)"
                    )
                
                with col4:
                    margin_inner = st.number_input(
                        "안쪽", 
                        min_value=0, 
                        max_value=50, 
                        value=15, 
                        step=1,
                        help="홀수 페이지 왼쪽, 짝수 페이지 오른쪽 여백 (mm, 제본 부분)"
                    )
                
                # 여백 설명
                st.markdown("""
                **여백 설명:**
                - **위/아래**: 모든 페이지의 상단/하단 여백
                - **바깥쪽**: 홀수 페이지(1,3,5...)의 왼쪽, 짝수 페이지(2,4,6...)의 오른쪽 여백
                - **안쪽**: 홀수 페이지(1,3,5...)의 오른쪽, 짝수 페이지(2,4,6...)의 왼쪽 여백 (제본 부분)
                """)
            
            # 페이지 조정 설정 (접힌 상태)
            with st.expander("🎛️ 페이지 조정", expanded=False):
                st.markdown("**홀수/짝수 페이지별 축소 및 위치 조정**")
                
                # 홀수 페이지 설정
                st.markdown("#### 📄 홀수 페이지 (1, 3, 5...) - 빨간색 경계선")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    scale_factor_odd = st.number_input(
                        "홀수 축소 비율", 
                        min_value=0.10, 
                        max_value=2.00, 
                        value=1.00, 
                        step=0.01,
                        format="%.2f",
                        help="홀수 페이지 축소 비율 (1.00 = 원본 크기, 소수점 2자리까지 입력 가능)"
                    )
                
                with col2:
                    offset_x_odd = st.number_input(
                        "홀수 좌우 이동", 
                        min_value=-50.0, 
                        max_value=50.0, 
                        value=0.0, 
                        step=0.1,
                        format="%.1f",
                        help="홀수 페이지를 좌우로 이동 (mm, 양수=오른쪽, 음수=왼쪽)"
                    )
                
                with col3:
                    offset_y_odd = st.number_input(
                        "홀수 상하 이동", 
                        min_value=-50.0, 
                        max_value=50.0, 
                        value=0.0, 
                        step=0.1,
                        format="%.1f",
                        help="홀수 페이지를 상하로 이동 (mm, 양수=위쪽, 음수=아래쪽)"
                    )
                
                with col4:
                    st.markdown("**홀수 페이지 상태**")
                    st.write(f"축소: {scale_factor_odd:.2f} ({int(scale_factor_odd*100)}%)")
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
                    
                    # 축소 비율 가이드
                    if scale_factor_odd < 0.5:
                        st.warning("⚠️ 매우 작음")
                    elif scale_factor_odd < 0.8:
                        st.info("ℹ️ 작음")
                    elif scale_factor_odd > 1.5:
                        st.warning("⚠️ 매우 큼")
                    elif scale_factor_odd > 1.2:
                        st.info("ℹ️ 큼")
                    else:
                        st.success("✅ 적당함")
                
                # 짝수 페이지 설정
                st.markdown("#### 📄 짝수 페이지 (2, 4, 6...) - 파란색 경계선")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    scale_factor_even = st.number_input(
                        "짝수 축소 비율", 
                        min_value=0.10, 
                        max_value=2.00, 
                        value=1.00, 
                        step=0.01,
                        format="%.2f",
                        help="짝수 페이지 축소 비율 (1.00 = 원본 크기, 소수점 2자리까지 입력 가능)"
                    )
                
                with col2:
                    offset_x_even = st.number_input(
                        "짝수 좌우 이동", 
                        min_value=-50.0, 
                        max_value=50.0, 
                        value=0.0, 
                        step=0.1,
                        format="%.1f",
                        help="짝수 페이지를 좌우로 이동 (mm, 양수=오른쪽, 음수=왼쪽)"
                    )
                
                with col3:
                    offset_y_even = st.number_input(
                        "짝수 상하 이동", 
                        min_value=-50.0, 
                        max_value=50.0, 
                        value=0.0, 
                        step=0.1,
                        format="%.1f",
                        help="짝수 페이지를 상하로 이동 (mm, 양수=위쪽, 음수=아래쪽)"
                    )
                
                with col4:
                    st.markdown("**짝수 페이지 상태**")
                    st.write(f"축소: {scale_factor_even:.2f} ({int(scale_factor_even*100)}%)")
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
                    
                    # 축소 비율 가이드
                    if scale_factor_even < 0.5:
                        st.warning("⚠️ 매우 작음")
                    elif scale_factor_even < 0.8:
                        st.info("ℹ️ 작음")
                    elif scale_factor_even > 1.5:
                        st.warning("⚠️ 매우 큼")
                    elif scale_factor_even > 1.2:
                        st.info("ℹ️ 큼")
                    else:
                        st.success("✅ 적당함")
                
                # 페이지 조정 설명
                st.markdown("""
                **페이지 조정 설명:**
                - **축소 비율**: 페이지 내용의 크기를 0.10~2.00 범위에서 소수점 2자리까지 정밀 조절 (여백은 그대로 유지)
                - **좌우 이동**: -50.0~50.0mm 범위에서 소수점 1자리까지 정밀 조절 (양수=오른쪽, 음수=왼쪽)
                - **상하 이동**: -50.0~50.0mm 범위에서 소수점 1자리까지 정밀 조절 (양수=위쪽, 음수=아래쪽)
                - **홀수/짝수**: 각각 독립적으로 설정 가능하며, 미리보기에서 빨간색/파란색 경계선으로 구분
                """)
            
            # 미리보기 표시
            if show_preview and analysis['is_landscape']:
                st.subheader("🔍 분할 미리보기")
                
                # 세션 상태에 현재 페이지 저장
                if 'preview_page_start' not in st.session_state:
                    st.session_state.preview_page_start = 0
                
                # 미리보기 설정 해시 생성 (설정 변경 감지용)
                current_settings = {
                    'split_direction': split_direction,
                    'use_first_page': use_first_page,
                    'page_order': page_order,
                    'margin_top': margin_top,
                    'margin_bottom': margin_bottom,
                    'margin_outer': margin_outer,
                    'margin_inner': margin_inner,
                    'scale_factor_odd': scale_factor_odd,
                    'offset_x_odd': offset_x_odd,
                    'offset_y_odd': offset_y_odd,
                    'scale_factor_even': scale_factor_even,
                    'offset_x_even': offset_x_even,
                    'offset_y_even': offset_y_even,
                    'show_page_numbers': show_page_numbers,
                    'file_hash': hash(uploaded_file.getvalue()) if uploaded_file else None
                }
                
                # 설정이 변경되었는지 확인
                settings_changed = (
                    'preview_settings' not in st.session_state or 
                    st.session_state.preview_settings != current_settings or
                    'cached_preview_images' not in st.session_state
                )
                
                # 설정이 변경된 경우에만 미리보기 재생성
                if settings_changed:
                    # 프로그래스바와 상태 메시지를 위한 컨테이너
                    progress_container = st.empty()
                    status_container = st.empty()
                    
                    try:
                        # 프로그래스 콜백 함수 정의
                        def update_progress(current, total, description):
                            progress_value = current / total if total > 0 else 0
                            progress_container.progress(progress_value)
                            status_container.info(f"📊 {description}")
                        
                        # 전체 미리보기 이미지 생성 (모든 페이지)
                        all_preview_images = editor.generate_preview_images(
                            tmp_file_path, 
                            split_direction=split_direction,
                            max_pages=999,  # 모든 페이지 가져오기
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
                            offset_y_even=offset_y_even,
                            show_page_numbers=show_page_numbers,
                            progress_callback=update_progress
                        )
                        
                        # 프로그래스바와 상태 메시지 제거
                        progress_container.empty()
                        status_container.empty()
                        
                        # 캐시에 저장
                        st.session_state.cached_preview_images = all_preview_images
                        st.session_state.preview_settings = current_settings
                        
                    except Exception as e:
                        # 프로그래스바와 상태 메시지 제거
                        progress_container.empty()
                        status_container.empty()
                        st.error(f"미리보기 생성 중 오류: {str(e)}")
                        all_preview_images = []
                else:
                    # 캐시된 미리보기 사용
                    all_preview_images = st.session_state.cached_preview_images
                    st.info("💾 캐시된 미리보기를 사용합니다.")
                    
                if all_preview_images:
                    total_pages = len(all_preview_images)
                    current_start = st.session_state.preview_page_start
                    current_end = min(current_start + 4, total_pages)
                    
                    # 페이지 네비게이션 컨트롤
                    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
                    
                    with col1:
                        if st.button("⏮️ 처음", disabled=(current_start == 0)):
                            st.session_state.preview_page_start = 0
                            st.rerun()
                    
                    with col2:
                        if st.button("◀️ 이전", disabled=(current_start == 0)):
                            st.session_state.preview_page_start = max(0, current_start - 4)
                            st.rerun()
                    
                    with col3:
                        st.write(f"**페이지 {current_start + 1}-{current_end} / 총 {total_pages}페이지**")
                    
                    with col4:
                        if st.button("다음 ▶️", disabled=(current_end >= total_pages)):
                            st.session_state.preview_page_start = min(current_start + 4, total_pages - 4)
                            st.rerun()
                    
                    with col5:
                        if st.button("마지막 ⏭️", disabled=(current_end >= total_pages)):
                            st.session_state.preview_page_start = max(0, total_pages - 4)
                            st.rerun()
                    
                    # 현재 페이지 범위의 미리보기 표시
                    current_preview_images = all_preview_images[current_start:current_end]
                    
                    if current_preview_images:
                        # 2열로 미리보기 표시
                        cols = st.columns(2)
                        for i, img_info in enumerate(current_preview_images):
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
                                    caption=f"미리보기 {img_info['page_number']} - {border_info} (고정번호: {img_info['fixed_page_number']})",
                                    use_column_width=True
                                )
                    else:
                        st.warning("미리보기 이미지를 생성할 수 없습니다.")
                else:
                    st.warning("미리보기 이미지를 생성할 수 없습니다.")
            
            # PDF 생성 옵션
            st.subheader("📖 PDF 생성")
            
            col1, col2 = st.columns(2)
            with col1:
                show_margin_borders = st.checkbox(
                    "여백 경계선 출력", 
                    value=False,
                    help="PDF에 여백 경계선을 포함하여 출력 (홀수 페이지: 빨간색, 짝수 페이지: 파란색)"
                )
            
            with col2:
                if show_margin_borders:
                    st.info("🔴 홀수 페이지 / 🔵 짝수 페이지")
                else:
                    st.write("경계선 없이 깔끔하게 출력")
            
            # 편집 버튼
            if st.button("📖 PDF 생성하기", type="primary"):
                st.info("🚀 PDF 생성을 시작합니다...")
                
                # 프로그래스바와 상태 메시지를 위한 컨테이너
                pdf_progress_container = st.empty()
                pdf_status_container = st.empty()
                
                try:
                    # 프로그래스 콜백 함수 정의
                    def update_pdf_progress(current, total, description):
                        progress_value = current / total if total > 0 else 0
                        pdf_progress_container.progress(progress_value)
                        pdf_status_container.info(f"📊 {description}")
                    
                    result_pdf = editor.create_book_pages(
                        tmp_file_path,
                        book_width_mm=125,
                        book_height_mm=175,
                        split_direction=split_direction,
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
                        offset_y_even=offset_y_even,
                        show_borders=show_margin_borders,
                        progress_callback=update_pdf_progress
                    )
                    
                    # 프로그래스바와 상태 메시지 제거
                    pdf_progress_container.empty()
                    pdf_status_container.empty()
                    
                    # 결과 다운로드
                    st.success(f"✅ PDF 생성 완료!")
                    
                    # 다운로드 버튼
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            label="📥 완성된 PDF 다운로드",
                            data=result_pdf,
                            file_name=f"book_{uploaded_file.name}",
                            mime="application/pdf"
                        )
                    
                    with col2:
                        st.info("💡 **팁:** 홀수/짝수 페이지별로 여백이 적용되었습니다.")
                    
                except Exception as e:
                    # 프로그래스바와 상태 메시지 제거
                    pdf_progress_container.empty()
                    pdf_status_container.empty()
                    st.error(f"❌ 생성 중 오류가 발생했습니다: {str(e)}")
                    
                    # 디버그용 상세 오류 정보
                    import traceback
                    st.error("상세 오류 정보:")
                    st.code(traceback.format_exc())
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
        
        - **페이지 네비게이션**: 4개 페이지 단위로 미리보기 탐색
        - **실시간 미리보기**: 설정 변경 시 자동으로 미리보기 업데이트
        - **여백 정보**: 각 페이지별 여백 정보 표시
        - **홀수/짝수 구분**: 빨간색(홀수)/파란색(짝수) 경계선으로 구분
        - **조정 정보**: 각 페이지별 축소 비율과 이동 정보 표시
        
        ### ⚠️ 주의사항
        
        - **안쪽 여백**: 제본을 위해 충분한 안쪽 여백을 확보하세요.
        - **바깥쪽 여백**: 독서 시 손가락이 닿는 부분이므로 적절한 여백을 두세요.
        - **페이지 순서**: 미리보기에서 페이지 순서를 확인한 후 생성하세요.
        """)

if __name__ == "__main__":
    main() 