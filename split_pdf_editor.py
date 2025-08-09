import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import RectangleObject
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import red, blue
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
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
        split_pages = []
        temp_files = []  # 임시 파일 추적
        
        # PyMuPDF로 PDF 열기
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        for page_num in range(total_pages):
            if progress_callback:
                progress_callback(page_num + 1, total_pages, f"페이지 {page_num + 1} 분할 중...")
            
            page = doc[page_num]
            page_rect = page.rect
            width = page_rect.width
            height = page_rect.height
            
            if width > height:  # 가로 페이지
                # 좌측 절반을 이미지로 렌더링
                left_rect = fitz.Rect(0, 0, width / 2, height)
                left_mat = fitz.Matrix(2.0, 2.0)  # 144 DPI
                left_pix = page.get_pixmap(matrix=left_mat, clip=left_rect)
                left_img_data = left_pix.tobytes("png")
                
                # 우측 절반을 이미지로 렌더링
                right_rect = fitz.Rect(width / 2, 0, width, height)
                right_mat = fitz.Matrix(2.0, 2.0)  # 144 DPI
                right_pix = page.get_pixmap(matrix=right_mat, clip=right_rect)
                right_img_data = right_pix.tobytes("png")
                
                # PIL 이미지로 변환하여 임시 PDF 생성
                left_img = Image.open(io.BytesIO(left_img_data))
                right_img = Image.open(io.BytesIO(right_img_data))
                
                # 좌측 페이지를 PDF로 변환
                left_pdf_buffer = io.BytesIO()
                left_img.save(left_pdf_buffer, format='PDF')
                left_pdf_buffer.seek(0)
                
                # 우측 페이지를 PDF로 변환
                right_pdf_buffer = io.BytesIO()
                right_img.save(right_pdf_buffer, format='PDF')
                right_pdf_buffer.seek(0)
                
                # PyPDF2로 페이지 객체 생성 (deepcopy 사용하지 않음)
                try:
                    left_reader = PdfReader(left_pdf_buffer)
                    right_reader = PdfReader(right_pdf_buffer)
                    
                    # 페이지 데이터를 저장 (페이지 객체 자체가 아닌 필요한 정보만)
                    split_pages.append({
                        'pdf_data': left_pdf_buffer.getvalue(),  # PDF 바이트 데이터 저장
                        'original_page': page_num + 1,
                        'side': 'left',
                        'description': f"원본 {page_num + 1}페이지 좌측",
                        'original_number': len(split_pages) + 1
                    })
                    
                    split_pages.append({
                        'pdf_data': right_pdf_buffer.getvalue(),  # PDF 바이트 데이터 저장
                        'original_page': page_num + 1,
                        'side': 'right',
                        'description': f"원본 {page_num + 1}페이지 우측",
                        'original_number': len(split_pages) + 1
                    })
                    
                finally:
                    left_pdf_buffer.close()
                    right_pdf_buffer.close()
                        
            else:  # 세로 페이지
                # 전체 페이지를 이미지로 렌더링
                mat = fitz.Matrix(2.0, 2.0)  # 144 DPI
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # PIL 이미지로 변환하여 PDF 생성
                img = Image.open(io.BytesIO(img_data))
                
                single_pdf_buffer = io.BytesIO()
                img.save(single_pdf_buffer, format='PDF')
                single_pdf_buffer.seek(0)
                
                try:
                    reader = PdfReader(single_pdf_buffer)
                    
                    split_pages.append({
                        'pdf_data': single_pdf_buffer.getvalue(),  # PDF 바이트 데이터 저장
                        'original_page': page_num + 1,
                        'side': 'single',
                        'description': f"원본 {page_num + 1}페이지",
                        'original_number': len(split_pages) + 1
                    })
                    
                finally:
                    single_pdf_buffer.close()
        
        doc.close()
        
        # 첫 페이지 사용 여부에 따른 처리
        if not use_first_page and len(split_pages) > 0:
            split_pages = split_pages[1:]
            # original_number 재정렬
            for i, page_info in enumerate(split_pages):
                page_info['original_number'] = i + 1
        
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
        
        for i, page_info in enumerate(split_pages):
            if progress_callback:
                progress_callback(i + 1, total_pages, f"페이지 {i + 1} 처리 중...")
            
            page_number = i + 1
            
            try:
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
                
                # PDF 데이터 확인
                if 'pdf_data' not in page_info or not page_info['pdf_data']:
                    continue
                
                # 페이지 변환 적용
                transformed_page = self.transform_page_to_book_size(
                    page_info['pdf_data'], page_margins, scale_factor, offset_x, offset_y
                )
                
                if transformed_page is None:
                    # 변환 실패 시 기본 페이지 생성
                    try:
                        buffer = io.BytesIO()
                        c = canvas.Canvas(buffer, pagesize=(self.book_width_pt, self.book_height_pt))
                        
                        # 빈 페이지에 작은 텍스트 추가
                        c.setFont("Helvetica", 8)
                        c.drawString(10, 10, f"Page {page_number}")
                        c.save()
                        
                        buffer.seek(0)
                        
                        # 페이지 데이터를 새로운 PDF로 복사
                        temp_reader = PdfReader(buffer)
                        if len(temp_reader.pages) > 0:
                            temp_writer = PdfWriter()
                            temp_writer.add_page(temp_reader.pages[0])
                            
                            # 새로운 버퍼에 복사
                            final_buffer = io.BytesIO()
                            temp_writer.write(final_buffer)
                            final_buffer.seek(0)
                            
                            # 원본 버퍼 닫기
                            buffer.close()
                            
                            # 새 버퍼에서 페이지 읽기
                            final_reader = PdfReader(final_buffer)
                            transformed_page = final_reader.pages[0]
                        else:
                            buffer.close()
                            transformed_page = None
                        
                        if transformed_page is None:
                            continue
                            
                    except Exception:
                        continue
                
                # 여백 가이드 추가 (옵션)
                if show_margin_guides:
                    transformed_page = self.add_margin_guides_to_page(transformed_page, page_margins, i + 1)
                
                writer.add_page(transformed_page)
                
            except Exception:
                # 실패한 페이지는 빈 페이지로 대체
                try:
                    buffer = io.BytesIO()
                    c = canvas.Canvas(buffer, pagesize=(self.book_width_pt, self.book_height_pt))
                    
                    # 빈 페이지에 오류 정보 추가
                    c.setFont("Helvetica", 8)
                    c.drawString(10, 10, f"Error on page {page_number}")
                    c.save()
                    
                    buffer.seek(0)
                    
                    # 페이지 데이터를 새로운 PDF로 복사
                    temp_reader = PdfReader(buffer)
                    if len(temp_reader.pages) > 0:
                        temp_writer = PdfWriter()
                        temp_writer.add_page(temp_reader.pages[0])
                        
                        # 새로운 버퍼에 복사
                        final_buffer = io.BytesIO()
                        temp_writer.write(final_buffer)
                        final_buffer.seek(0)
                        
                        # 원본 버퍼 닫기
                        buffer.close()
                        
                        # 새 버퍼에서 페이지 읽기
                        final_reader = PdfReader(final_buffer)
                        fallback_page = final_reader.pages[0]
                        
                        writer.add_page(fallback_page)
                    else:
                        buffer.close()
                        continue
                        
                except Exception:
                    # 완전 실패 시 건너뛰기
                    continue
        
        # PDF 데이터 반환
        try:
            output_buffer = io.BytesIO()
            
            # PDF 작성 전 페이지 수 확인
            if len(writer.pages) == 0:
                return None
            
            # PDF 작성
            writer.write(output_buffer)
            output_buffer.seek(0)
            
            # PDF 데이터 검증
            pdf_data = output_buffer.getvalue()
            if len(pdf_data) < 100:  # 너무 작은 PDF는 손상된 것으로 간주
                output_buffer.close()
                return None
            
            # PDF 유효성 검사
            try:
                test_reader = PdfReader(io.BytesIO(pdf_data))
                if len(test_reader.pages) == 0:
                    output_buffer.close()
                    return None
            except Exception:
                output_buffer.close()
                return None
            
            output_buffer.close()
            return pdf_data
            
        except Exception as e:
            import traceback
            st.error(f"PDF 생성 중 오류: {e}")
            st.error(f"상세 오류: {traceback.format_exc()}")
            raise
    
    def transform_page_to_book_size(self, pdf_data, margins, scale_factor, offset_x, offset_y):
        """PDF 데이터를 책 크기로 변환 - 이미지 기반 처리"""
        try:
            # 입력 데이터 검증
            if not pdf_data or len(pdf_data) == 0:
                return None
            
            # 1단계: PDF 데이터를 임시 파일로 저장
            temp_pdf_path = None
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf_file:
                temp_pdf_path = temp_pdf_file.name
                temp_pdf_file.write(pdf_data)
            
            # 2단계: PyMuPDF로 고해상도 이미지 변환
            doc = fitz.open(temp_pdf_path)
            if len(doc) == 0:
                doc.close()
                return None
            
            page = doc[0]
            mat = fitz.Matrix(4.17, 4.17)  # 300 DPI
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            doc.close()
            
            # 3단계: PIL로 이미지 처리
            original_img = Image.open(io.BytesIO(img_data))
            
            # 4단계: 책 크기 설정 (300 DPI 기준)
            dpi = 300
            book_width_px = int(self.book_width_mm * dpi / 25.4)
            book_height_px = int(self.book_height_mm * dpi / 25.4)
            
            # 5단계: 여백 계산 (픽셀 단위)
            margin_left_px = int(margins['left'] * dpi / 25.4)
            margin_right_px = int(margins['right'] * dpi / 25.4)
            margin_top_px = int(margins['top'] * dpi / 25.4)
            margin_bottom_px = int(margins['bottom'] * dpi / 25.4)
            
            # 콘텐츠 영역 크기
            content_width = max(10, book_width_px - margin_left_px - margin_right_px)
            content_height = max(10, book_height_px - margin_top_px - margin_bottom_px)
            
            # 6단계: 원본 이미지 크기 조정
            orig_w, orig_h = original_img.size
            
            if orig_w > 0 and orig_h > 0 and content_width > 0 and content_height > 0:
                # 스케일 계산 (비율 유지)
                scale_x = (content_width * scale_factor) / orig_w
                scale_y = (content_height * scale_factor) / orig_h
                scale = min(scale_x, scale_y)
                
                new_width = max(1, int(orig_w * scale))
                new_height = max(1, int(orig_h * scale))
                
                # 이미지 리사이즈
                resized_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 중앙 정렬 위치 계산
                center_x = margin_left_px + (content_width - new_width) // 2
                center_y = margin_top_px + (content_height - new_height) // 2
                
                # 오프셋 적용
                offset_x_px = int(offset_x * dpi / 25.4)
                offset_y_px = int(offset_y * dpi / 25.4)
                
                final_x = max(0, min(book_width_px - new_width, center_x + offset_x_px))
                final_y = max(0, min(book_height_px - new_height, center_y + offset_y_px))
                
            else:
                # 안전한 기본값
                resized_img = original_img.resize((100, 100), Image.Resampling.LANCZOS)
                final_x = (book_width_px - 100) // 2
                final_y = (book_height_px - 100) // 2
            
            # 7단계: 새 캔버스에 배치
            canvas_img = Image.new('RGB', (book_width_px, book_height_px), color='white')
            canvas_img.paste(resized_img, (final_x, final_y))
            
            # 8단계: ReportLab을 사용하여 안정적인 PDF 생성
            output_pdf_buffer = io.BytesIO()
            
            # 이미지를 임시 파일로 저장
            temp_img_path = None
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_img_file:
                temp_img_path = temp_img_file.name
                canvas_img.save(temp_img_path, format='PNG')
            
            # ReportLab으로 PDF 생성
            c = canvas.Canvas(output_pdf_buffer, pagesize=(self.book_width_pt, self.book_height_pt))
            
            # 이미지를 PDF에 삽입 (포인트 단위로 변환)
            img_width_pt = book_width_px * 72 / dpi
            img_height_pt = book_height_px * 72 / dpi
            
            try:
                # 파일 경로를 사용하여 이미지 삽입
                c.drawImage(temp_img_path, 0, 0, width=img_width_pt, height=img_height_pt)
                c.save()
                
            except Exception:
                # 대안: PIL로 PDF 생성
                try:
                    c.save()  # 빈 페이지라도 저장
                    output_pdf_buffer.seek(0)
                    output_pdf_buffer.truncate(0)  # 버퍼 초기화
                    
                    # PIL로 직접 PDF 생성
                    canvas_img_rgb = canvas_img.convert('RGB')
                    canvas_img_rgb.save(output_pdf_buffer, format='PDF', resolution=300.0)
                    
                except Exception:
                    return None
            
            # 임시 이미지 파일 정리
            try:
                if temp_img_path and os.path.exists(temp_img_path):
                    os.unlink(temp_img_path)
            except:
                pass
            
            output_pdf_buffer.seek(0)
            
            # 9단계: PyPDF2로 페이지 객체 생성
            reader = PdfReader(output_pdf_buffer)
            if len(reader.pages) == 0:
                output_pdf_buffer.close()
                return None
            
            # 페이지 데이터를 새로운 PDF로 복사
            new_writer = PdfWriter()
            new_writer.add_page(reader.pages[0])
            
            # 새로운 버퍼에 복사
            final_buffer = io.BytesIO()
            new_writer.write(final_buffer)
            final_buffer.seek(0)
            
            # 원본 버퍼 닫기
            output_pdf_buffer.close()
            
            # 새 버퍼에서 페이지 읽기
            final_reader = PdfReader(final_buffer)
            new_page = final_reader.pages[0]
            
            # 임시 파일 정리
            try:
                if temp_pdf_path and os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
            except:
                pass
            
            return new_page
            
        except Exception as e:
            # 실패 시 빈 페이지 생성
            try:
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=(self.book_width_pt, self.book_height_pt))
                c.save()
                buffer.seek(0)
                
                # 페이지 데이터를 새로운 PDF로 복사
                temp_reader = PdfReader(buffer)
                if len(temp_reader.pages) > 0:
                    temp_writer = PdfWriter()
                    temp_writer.add_page(temp_reader.pages[0])
                    
                    # 새로운 버퍼에 복사
                    final_buffer = io.BytesIO()
                    temp_writer.write(final_buffer)
                    final_buffer.seek(0)
                    
                    # 원본 버퍼 닫기
                    buffer.close()
                    
                    # 새 버퍼에서 페이지 읽기
                    final_reader = PdfReader(final_buffer)
                    empty_page = final_reader.pages[0]
                    return empty_page
                else:
                    buffer.close()
                    return None
                    
            except:
                # 최후의 수단: None 반환
                return None
    
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

    def create_preview_image(self, page_data, margins, scale_factor, offset_x, offset_y, page_number, show_page_numbers=True):
        """미리보기 이미지 생성 - 안전하고 간단한 방식"""
        try:
            # 1단계: 원본 페이지를 이미지로 변환
            temp_pdf_path = None
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf_file:
                temp_pdf_path = temp_pdf_file.name
                temp_writer = PdfWriter()
                temp_writer.add_page(PdfReader(io.BytesIO(page_data['pdf_data'])).pages[0]) # 페이지 객체 생성
                temp_writer.write(temp_pdf_file)
            
            # PyMuPDF로 이미지 렌더링
            doc = fitz.open(temp_pdf_path)
            page = doc[0]
            mat = fitz.Matrix(2.0, 2.0)  # 144 DPI (안전한 해상도)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            doc.close()
            
            # PIL 이미지로 변환
            original_img = Image.open(io.BytesIO(img_data))
            
            # 2단계: 미리보기 캔버스 설정 (고정 크기)
            canvas_width = 200
            canvas_height = 280  # 125:175 비율
            
            # 3단계: 여백 계산
            effective_margins = self.calculate_page_margins(
                page_number, margins['top'], margins['bottom'], 
                margins['outer'], margins['inner']
            )
            
            # 여백을 미리보기 픽셀로 변환 (간단한 비례 계산)
            margin_left_px = int(effective_margins['left'] * canvas_width / 125)
            margin_right_px = int(effective_margins['right'] * canvas_width / 125)
            margin_top_px = int(effective_margins['top'] * canvas_height / 175)
            margin_bottom_px = int(effective_margins['bottom'] * canvas_height / 175)
            
            # 콘텐츠 영역 크기
            content_width = max(10, canvas_width - margin_left_px - margin_right_px)
            content_height = max(10, canvas_height - margin_top_px - margin_bottom_px)
            
            # 4단계: 원본 이미지 크기 조정
            orig_w, orig_h = original_img.size
            
            if orig_w > 0 and orig_h > 0 and content_width > 0 and content_height > 0:
                # 스케일 계산 (비율 유지)
                scale_x = (content_width * scale_factor) / orig_w
                scale_y = (content_height * scale_factor) / orig_h
                scale = min(scale_x, scale_y)
                
                new_width = max(1, int(orig_w * scale))
                new_height = max(1, int(orig_h * scale))
                
                # 이미지 리사이즈
                resized_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 중앙 정렬 위치 계산
                center_x = margin_left_px + (content_width - new_width) // 2
                center_y = margin_top_px + (content_height - new_height) // 2
                
                # 오프셋 적용 (mm를 픽셀로 대략 변환)
                offset_x_px = int(offset_x * canvas_width / 125)
                offset_y_px = int(offset_y * canvas_height / 175)
                
                final_x = max(0, min(canvas_width - new_width, center_x + offset_x_px))
                final_y = max(0, min(canvas_height - new_height, center_y + offset_y_px))
            else:
                # 안전한 기본값
                resized_img = original_img.resize((50, 50), Image.Resampling.LANCZOS)
                final_x, final_y = 75, 115  # 중앙 근처
            
            # 5단계: 캔버스 생성 및 이미지 배치
            canvas = Image.new('RGB', (canvas_width, canvas_height), color='white')
            canvas.paste(resized_img, (final_x, final_y))
            
            # 6단계: 여백 가이드 선 그리기
            draw = ImageDraw.Draw(canvas)
            line_color = (255, 0, 0) if page_number % 2 == 1 else (0, 0, 255)
            
            # 여백 가이드 선
            x1 = max(0, margin_left_px)
            y1 = max(0, margin_top_px)
            x2 = min(canvas_width - 1, canvas_width - margin_right_px)
            y2 = min(canvas_height - 1, canvas_height - margin_bottom_px)
            
            if x2 > x1 and y2 > y1:
                draw.rectangle([x1, y1, x2, y2], outline=line_color, width=2)
            
            # 7단계: 페이지 번호 표시
            if show_page_numbers:
                try:
                    font = ImageFont.load_default()
                    text = str(page_data.get('original_number', page_number))
                    draw.rectangle([5, 5, 35, 25], fill=(255, 255, 255), outline=(0, 0, 0))
                    draw.text((10, 10), text, fill=(0, 0, 0), font=font)
                except:
                    pass
            
            # 임시 파일 정리
            try:
                if temp_pdf_path and os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
            except:
                pass
            
            return canvas
            
        except Exception as e:
            # 상세한 에러 정보를 포함한 이미지 생성
            error_img = Image.new('RGB', (200, 280), color=(250, 250, 250))
            draw = ImageDraw.Draw(error_img)
            draw.rectangle([0, 0, 199, 279], outline=(255, 0, 0), width=2)
            
            try:
                font = ImageFont.load_default()
                y = 10
                
                # 페이지 정보
                draw.text((10, y), f"Page {page_number}", fill=(0, 0, 0), font=font)
                y += 20
                
                # 설정 정보
                draw.text((10, y), f"Scale: {scale_factor:.2f}", fill=(100, 100, 100), font=font)
                y += 15
                draw.text((10, y), f"Offset: {offset_x:.1f},{offset_y:.1f}", fill=(100, 100, 100), font=font)
                y += 20
                
                # 에러 정보
                draw.text((10, y), "Preview Error:", fill=(255, 0, 0), font=font)
                y += 20
                
                # 에러 메시지 (짧게)
                error_msg = str(e)[:50]
                draw.text((10, y), error_msg, fill=(255, 0, 0), font=font)
                
            except:
                # 폰트 로딩 실패 시 기본 텍스트만
                draw.text((10, 10), f"Error on page {page_number}", fill=(255, 0, 0))
            
            return error_img


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
        
        # 임시 파일 저장 (안전한 방식)
        try:
            # 업로드된 파일을 바이트로 읽기
            file_bytes = uploaded_file.getvalue()
            
            # 임시 파일 생성
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(file_bytes)
                tmp_file_path = tmp_file.name
            
            # 파일 정보 표시
            with st.expander("📄 파일 정보", expanded=False):
                st.write(f"**파일명:** {uploaded_file.name}")
                st.write(f"**파일 크기:** {len(file_bytes):,} bytes")
        
        except Exception as e:
            st.error(f"파일 처리 중 오류 발생: {e}")
            return
        
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
            offset_x_odd = st.number_input("좌우 이동", min_value=-50.0, max_value=50.0, value=0.0, step=0.1, key="offset_x_odd")
        with col3:
            offset_y_odd = st.number_input("상하 이동", min_value=-50.0, max_value=50.0, value=0.0, step=0.1, key="offset_y_odd")
        
        # 짝수 페이지 설정
        st.write("**짝수 페이지 (2,4,6...)**")
        col1, col2, col3 = st.columns(3)
        with col1:
            scale_even = st.number_input("축소 비율", min_value=0.10, max_value=2.00, value=1.00, step=0.01, key="scale_even")
        with col2:
            offset_x_even = st.number_input("좌우 이동", min_value=-50.0, max_value=50.0, value=0.0, step=0.1, key="offset_x_even")
        with col3:
            offset_y_even = st.number_input("상하 이동", min_value=-50.0, max_value=50.0, value=0.0, step=0.1, key="offset_y_even")
        
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
        # PDF 분할 - 프로그래스바 추가
        split_progress_container = st.empty()
        split_status_container = st.empty()
        
        def split_progress_callback(current, total, description):
            progress_value = current / total if total > 0 else 0
            split_progress_container.progress(progress_value)
            split_status_container.info(f"📄 {description}")
        
        with st.spinner("PDF 분할 중..."):
            split_pages = editor.split_landscape_pages(tmp_file_path, use_first_page, split_progress_callback)
        
        # 프로그래스바 제거
        split_progress_container.empty()
        split_status_container.empty()
        
        if not split_pages:
            st.error("PDF 분할에 실패했습니다. 파일을 확인해주세요.")
            return
        
        # 페이지 순서 적용
        ordered_pages = editor.apply_page_order(split_pages, page_order)
        
        st.success(f"✅ 총 {len(ordered_pages)}개 페이지 준비 완료")
        
        # 미리보기
        st.subheader("👀 미리보기")
        
        # 미리보기 설정
        col1, col2 = st.columns(2)
        with col1:
            show_page_numbers = st.checkbox("원본 페이지 번호 표시", value=True)
        with col2:
            # 페이지네이션을 위한 세션 상태 초기화
            if 'preview_start' not in st.session_state:
                st.session_state.preview_start = 0
        
        if len(ordered_pages) > 0:
            # 현재 페이지 범위 계산
            start_idx = st.session_state.preview_start
            end_idx = min(start_idx + 4, len(ordered_pages))
            preview_pages = ordered_pages[start_idx:end_idx]
            
            # 페이지네이션 버튼
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button("◀ 이전", disabled=(start_idx == 0)):
                    st.session_state.preview_start = max(0, start_idx - 4)
                    st.rerun()
            
            with col2:
                st.write(f"페이지 {start_idx + 1}-{end_idx} / {len(ordered_pages)}")
            
            with col3:
                if st.button("다음 ▶", disabled=(end_idx >= len(ordered_pages))):
                    st.session_state.preview_start = min(len(ordered_pages) - 4, start_idx + 4)
                    st.rerun()
            
            # 미리보기 이미지 생성 및 표시
            cols = st.columns(min(4, len(preview_pages)))
            
            with st.spinner("미리보기 생성 중..."):
                for i, page_data in enumerate(preview_pages):
                    with cols[i]:
                        page_num = start_idx + i + 1
                        st.write(f"**페이지 {page_num}**")
                        st.write(f"*{page_data['description']}*")
                        
                        # 현재 페이지의 설정 가져오기
                        if page_num % 2 == 1:  # 홀수 페이지
                            current_scale = scale_odd
                            current_offset_x = offset_x_odd
                            current_offset_y = offset_y_odd
                            st.write("🔴 홀수 페이지")
                        else:  # 짝수 페이지
                            current_scale = scale_even
                            current_offset_x = offset_x_even
                            current_offset_y = offset_y_even
                            st.write("🔵 짝수 페이지")
                        
                        # 여백 설정
                        margins = {
                            'top': margin_top,
                            'bottom': margin_bottom,
                            'outer': margin_outer,
                            'inner': margin_inner
                        }
                        
                        # 미리보기 이미지 생성
                        try:
                            preview_img = editor.create_preview_image(
                                page_data, margins, current_scale, 
                                current_offset_x, current_offset_y, 
                                page_num, show_page_numbers
                            )
                            st.image(preview_img, use_column_width=True)
                        except Exception as e:
                            st.error(f"미리보기 생성 실패: {e}")
                            st.write("미리보기를 생성할 수 없습니다.")
        
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
                
                # PDF 생성 결과 검증
                if pdf_data is None:
                    st.error("❌ PDF 생성에 실패했습니다.")
                    return
                
                if len(pdf_data) < 1000:  # 최소 크기 검사
                    st.error("❌ 생성된 PDF가 너무 작습니다. 다시 시도해주세요.")
                    return
                
                # 최종 검증
                try:
                    final_reader = PdfReader(io.BytesIO(pdf_data))
                    page_count = len(final_reader.pages)
                    if page_count == 0:
                        st.error("❌ 생성된 PDF에 페이지가 없습니다.")
                        return
                    
                    st.success(f"✅ PDF 생성 완료! ({page_count}페이지)")
                    
                except Exception as validation_error:
                    st.error(f"❌ PDF 검증 실패: {validation_error}")
                    st.error("생성된 PDF가 손상되었을 수 있습니다.")
                    return
                
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
                st.error(f"❌ PDF 생성 중 오류: {e}")
                import traceback
                st.error(f"상세 오류: {traceback.format_exc()}")

    except Exception as e:
        st.error(f"처리 중 오류 발생: {e}")
        import traceback
        st.error(f"상세 오류: {traceback.format_exc()}")
        return
    
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