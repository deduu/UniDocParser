# backend/file_ingestion/handlers/excel_handler.py
from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import logging
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import base64

from backend.schemas.ingest import PageMetadata
from backend.utils.helpers import save_jpeg
from backend.utils.trackers import log_processing_time
from backend.utils.storage_paths import page_image_key, ensure_parent_dir

logger = logging.getLogger(__name__)


def _sanitize(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)


class ExcelRenderer:
    """Cross-platform Excel sheet renderer that supports charts, images, and complex formatting."""

    def __init__(self, max_width: int = 1600, max_height: int = 1200, cell_width: int = 100, cell_height: int = 30):
        self.max_width = max_width
        self.max_height = max_height
        self.cell_width = cell_width
        self.cell_height = cell_height
        self._font_cache: Dict[int, ImageFont.FreeTypeFont] = {}

    def _get_font(self, size: int = 12) -> ImageFont.FreeTypeFont:
        """Get or create a font with caching."""
        if size not in self._font_cache:
            try:
                # Try to load a system font
                self._font_cache[size] = ImageFont.truetype("arial.ttf", size)
            except (OSError, IOError):
                try:
                    self._font_cache[size] = ImageFont.truetype(
                        "DejaVuSans.ttf", size)
                except (OSError, IOError):
                    # Fallback to default font
                    self._font_cache[size] = ImageFont.load_default()
        return self._font_cache[size]

    def _parse_cell_range(self, range_str: str) -> Tuple[int, int, int, int]:
        """Parse Excel range string like 'A1:C10' into (min_col, min_row, max_col, max_row)."""
        try:
            if ':' not in range_str:
                # Single cell
                col, row = self._parse_cell_coordinate(range_str)
                return col, row, col, row

            start_cell, end_cell = range_str.split(':')
            min_col, min_row = self._parse_cell_coordinate(start_cell)
            max_col, max_row = self._parse_cell_coordinate(end_cell)
            return min_col, min_row, max_col, max_row
        except Exception as e:
            logger.debug(f"Error parsing range {range_str}: {e}")
            return 1, 1, 10, 20  # Default range

    def _parse_cell_coordinate(self, cell_str: str) -> Tuple[int, int]:
        """Parse cell coordinate like 'A1' into (column_index, row_index)."""
        try:
            # Split letters and numbers
            col_str = ""
            row_str = ""
            for char in cell_str:
                if char.isalpha():
                    col_str += char
                elif char.isdigit():
                    row_str += char

            # Convert column letters to index (A=1, B=2, etc.)
            col_index = 0
            for char in col_str.upper():
                col_index = col_index * 26 + (ord(char) - ord('A') + 1)

            row_index = int(row_str) if row_str else 1
            return col_index, row_index
        except Exception as e:
            logger.debug(f"Error parsing coordinate {cell_str}: {e}")
            return 1, 1

    def _column_index_to_letter(self, col_index: int) -> str:
        """Convert column index to Excel column letter (1->A, 2->B, etc.)."""
        result = ""
        while col_index > 0:
            col_index -= 1
            result = chr(col_index % 26 + ord('A')) + result
            col_index //= 26
        return result or 'A'

    def _get_cell_dimensions(self, worksheet) -> Tuple[int, int, Dict[int, int], Dict[int, int]]:
        """Calculate actual cell dimensions based on content and formatting."""
        try:
            # Get column widths by index
            col_widths = {}
            for col_letter, col_dim in worksheet.column_dimensions.items():
                try:
                    col_index = self._parse_cell_coordinate(
                        col_letter + "1")[0]
                    if col_dim.width:
                        col_widths[col_index] = max(int(col_dim.width * 8), 50)
                    else:
                        col_widths[col_index] = self.cell_width
                except Exception:
                    pass

            # Get row heights
            row_heights = {}
            for row_num, row_dim in worksheet.row_dimensions.items():
                if row_dim.height:
                    row_heights[row_num] = max(int(row_dim.height * 1.3), 20)
                else:
                    row_heights[row_num] = self.cell_height

            # Calculate total dimensions using our own range parsing
            used_range = worksheet.calculate_dimension()
            if used_range == 'A1:A1':
                return 800, 600, row_heights, col_widths

            min_col, min_row, max_col, max_row = self._parse_cell_range(
                used_range)

            total_width = sum(col_widths.get(i, self.cell_width)
                              for i in range(min_col, max_col + 1))
            total_height = sum(row_heights.get(i, self.cell_height)
                               for i in range(min_row, max_row + 1))

            # Add padding
            total_width = min(total_width + 100, self.max_width)
            total_height = min(total_height + 100, self.max_height)

            return total_width, total_height, row_heights, col_widths

        except Exception as e:
            logger.warning(f"Error calculating cell dimensions: {e}")
            return 800, 600, {}, {}

    def _draw_cell_borders(self, draw: ImageDraw.Draw, x: int, y: int, width: int, height: int,
                           cell_style=None) -> None:
        """Draw cell borders based on style."""
        try:
            border_color = (200, 200, 200)  # Light gray default

            if cell_style and hasattr(cell_style, 'border') and cell_style.border:
                # Draw borders if they exist
                if hasattr(cell_style.border, 'top') and cell_style.border.top.style:
                    draw.line([(x, y), (x + width, y)],
                              fill=border_color, width=1)
                if hasattr(cell_style.border, 'bottom') and cell_style.border.bottom.style:
                    draw.line([(x, y + height), (x + width, y + height)],
                              fill=border_color, width=1)
                if hasattr(cell_style.border, 'left') and cell_style.border.left.style:
                    draw.line([(x, y), (x, y + height)],
                              fill=border_color, width=1)
                if hasattr(cell_style.border, 'right') and cell_style.border.right.style:
                    draw.line([(x + width, y), (x + width, y + height)],
                              fill=border_color, width=1)
            else:
                # Default light border
                draw.rectangle([x, y, x + width, y + height],
                               outline=border_color, width=1)

        except Exception as e:
            logger.debug(f"Error drawing borders: {e}")
            # Fallback to simple border
            draw.rectangle([x, y, x + width, y + height],
                           outline=(200, 200, 200), width=1)

    def _get_cell_background_color(self, cell) -> Tuple[int, int, int]:
        """Extract cell background color."""
        try:
            if hasattr(cell, 'fill') and cell.fill and hasattr(cell.fill, 'fgColor'):
                color = cell.fill.fgColor
                if hasattr(color, 'rgb') and color.rgb and color.rgb != '00000000':
                    rgb_hex = color.rgb
                    if len(rgb_hex) == 8:  # ARGB format
                        rgb_hex = rgb_hex[2:]  # Remove alpha
                    if len(rgb_hex) == 6:
                        return tuple(int(rgb_hex[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            pass
        return (255, 255, 255)  # White background

    def _extract_and_draw_images(self, worksheet, image: Image.Image) -> None:
        """Extract and draw embedded images from the worksheet."""
        try:
            if not hasattr(worksheet, '_images') or not worksheet._images:
                return

            for img_obj in worksheet._images:
                try:
                    # Get image data
                    if hasattr(img_obj, '_data') and img_obj._data:
                        img_data = BytesIO(img_obj._data())
                        embedded_img = Image.open(img_data)

                        # Get position (approximate)
                        anchor = getattr(img_obj, 'anchor', None)
                        if anchor and hasattr(anchor, '_from'):
                            col = anchor._from.col * self.cell_width
                            row = anchor._from.row * self.cell_height

                            # Resize if too large
                            img_width, img_height = embedded_img.size
                            max_embed_size = 300
                            if img_width > max_embed_size or img_height > max_embed_size:
                                embedded_img.thumbnail(
                                    (max_embed_size, max_embed_size))

                            # Paste the image
                            if col < image.width and row < image.height:
                                image.paste(embedded_img, (int(col), int(row)))

                except Exception as e:
                    logger.debug(f"Error processing embedded image: {e}")

        except Exception as e:
            logger.debug(f"Error extracting images: {e}")

    def _extract_and_draw_charts(self, worksheet, image: Image.Image) -> None:
        """Extract and draw charts from the worksheet."""
        try:
            if not hasattr(worksheet, '_charts') or not worksheet._charts:
                return

            draw = ImageDraw.Draw(image)

            for chart in worksheet._charts:
                try:
                    # Get chart position
                    anchor = getattr(chart, 'anchor', None)
                    if anchor and hasattr(anchor, '_from'):
                        x = int(anchor._from.col * self.cell_width)
                        y = int(anchor._from.row * self.cell_height)
                        width = min(400, image.width - x)
                        height = min(300, image.height - y)

                        if x < image.width and y < image.height:
                            # Draw a placeholder for the chart
                            chart_color = (240, 248, 255)  # Light blue
                            draw.rectangle([x, y, x + width, y + height],
                                           fill=chart_color, outline=(100, 149, 237), width=2)

                            # Add chart label
                            font = self._get_font(14)
                            chart_title = getattr(chart, 'title', 'Chart')
                            if hasattr(chart_title, 'tx') and hasattr(chart_title.tx, 'rich'):
                                try:
                                    title_text = str(
                                        chart_title.tx.rich.p[0].r[0].t)
                                except:
                                    title_text = "Chart"
                            else:
                                title_text = f"{chart.__class__.__name__}"

                            text_x = x + 10
                            text_y = y + 10
                            draw.text((text_x, text_y), title_text,
                                      fill=(0, 0, 0), font=font)

                except Exception as e:
                    logger.debug(f"Error processing chart: {e}")

        except Exception as e:
            logger.debug(f"Error extracting charts: {e}")

    def render_worksheet(self, worksheet, sheet_name: str) -> Image.Image:
        """Render a worksheet to a PIL Image."""
        try:
            # Calculate dimensions
            width, height, row_heights, col_widths = self._get_cell_dimensions(
                worksheet)

            # Create image
            image = Image.new('RGB', (width, height), (255, 255, 255))
            draw = ImageDraw.Draw(image)

            # Get used range
            used_range = worksheet.calculate_dimension()
            if used_range == 'A1:A1':
                # Empty sheet, just add title
                font = self._get_font(16)
                draw.text((20, 20), f"Sheet: {sheet_name}", fill=(
                    0, 0, 0), font=font)
                return image

            # Parse the range to get boundaries
            min_col, min_row, max_col, max_row = self._parse_cell_range(
                used_range)

            # Limit the range for performance
            max_col = min(max_col, min_col + 50)  # Limit columns
            max_row = min(max_row, min_row + 100)  # Limit rows

            # Draw cells using direct cell access to avoid MergedCell issues
            current_y = 20  # Start with some padding

            for row_idx in range(min_row, max_row + 1):
                current_x = 20
                row_height = row_heights.get(row_idx, self.cell_height)

                for col_idx in range(min_col, max_col + 1):
                    if current_x >= width - 50:
                        break

                    try:
                        # Get cell value using direct access to avoid MergedCell
                        cell_value = None
                        cell_obj = None

                        # Try to get the cell safely
                        try:
                            cell_obj = worksheet.cell(
                                row=row_idx, column=col_idx)
                            # Check if this is actually a merged cell by checking if it has a value attribute
                            if hasattr(cell_obj, 'value'):
                                cell_value = cell_obj.value
                        except Exception:
                            # Skip problematic cells
                            pass

                        cell_width = col_widths.get(col_idx, self.cell_width)

                        # Draw cell background
                        bg_color = (255, 255, 255)  # Default white
                        if cell_obj:
                            bg_color = self._get_cell_background_color(
                                cell_obj)

                        draw.rectangle([current_x, current_y, current_x + cell_width,
                                        current_y + row_height], fill=bg_color)

                        # Draw borders
                        self._draw_cell_borders(draw, current_x, current_y,
                                                cell_width, row_height, cell_obj)

                        # Draw cell content if it exists
                        if cell_value is not None:
                            cell_text = str(cell_value)
                            if len(cell_text) > 25:  # Truncate long text
                                cell_text = cell_text[:25] + "..."

                            font_size = 10
                            try:
                                if (cell_obj and hasattr(cell_obj, 'font') and cell_obj.font and
                                        hasattr(cell_obj.font, 'size') and cell_obj.font.size):
                                    font_size = min(cell_obj.font.size, 14)
                            except Exception:
                                pass

                            font = self._get_font(font_size)
                            text_color = (0, 0, 0)

                            # Try to get font color
                            try:
                                if (cell_obj and hasattr(cell_obj, 'font') and cell_obj.font and
                                    hasattr(cell_obj.font, 'color') and cell_obj.font.color and
                                        hasattr(cell_obj.font.color, 'rgb') and cell_obj.font.color.rgb):
                                    rgb_hex = cell_obj.font.color.rgb
                                    if len(rgb_hex) == 8:
                                        rgb_hex = rgb_hex[2:]
                                    if len(rgb_hex) == 6:
                                        text_color = tuple(
                                            int(rgb_hex[i:i+2], 16) for i in (0, 2, 4))
                            except Exception:
                                pass

                            # Position text with some padding
                            text_x = current_x + 5
                            text_y = current_y + 5

                            try:
                                draw.text((text_x, text_y), cell_text,
                                          fill=text_color, font=font)
                            except Exception as e:
                                logger.debug(
                                    f"Error drawing text '{cell_text}': {e}")

                    except Exception as e:
                        logger.debug(
                            f"Error processing cell ({row_idx}, {col_idx}): {e}")

                    current_x += cell_width

                current_y += row_height
                if current_y >= height - 50:  # Leave some margin
                    break

            # Draw embedded images and charts
            self._extract_and_draw_images(worksheet, image)
            self._extract_and_draw_charts(worksheet, image)

            return image

        except Exception as e:
            logger.error(f"Error rendering worksheet '{sheet_name}': {e}")
            # Return a simple placeholder
            placeholder = Image.new('RGB', (800, 600), (245, 245, 245))
            draw = ImageDraw.Draw(placeholder)
            font = self._get_font(16)
            draw.text((50, 50), f"Error rendering sheet: {sheet_name}", fill=(
                255, 0, 0), font=font)
            draw.text((50, 80), f"Error: {str(e)[:100]}", fill=(
                100, 100, 100), font=self._get_font(12))
            return placeholder


class ExcelHandler:
    """High-performance, cross-platform Excel handler with chart and image support."""

    def __init__(self, img_pages_dir: Path, max_side: int, jpeg_quality: int):
        self.img_pages_dir = img_pages_dir
        self.max_side = max_side
        self.jpeg_quality = jpeg_quality
        self.renderer = ExcelRenderer(max_width=max_side, max_height=max_side)

    def _save_as_png_and_jpeg(self, image: Image.Image, base_path: Path) -> Path:
        """Save image as PNG first, then convert to JPEG for storage."""
        png_path = base_path.with_suffix(".png")
        jpeg_path = base_path.with_suffix(".jpeg")

        try:
            # Save as PNG (lossless, good for viewing)
            image.save(png_path, "PNG", optimize=True)

            # Also save as JPEG for storage efficiency
            if image.mode in ('RGBA', 'LA', 'P'):
                # Convert to RGB for JPEG
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                rgb_image.paste(image, mask=image.split()
                                [-1] if image.mode in ('RGBA', 'LA') else None)
                save_jpeg(rgb_image, jpeg_path, quality=self.jpeg_quality)
            else:
                save_jpeg(image, jpeg_path, quality=self.jpeg_quality)

            return png_path  # Return PNG path for better quality viewing

        except Exception as e:
            logger.error(f"Error saving image: {e}")
            # Fallback to JPEG only
            if image.mode in ('RGBA', 'LA', 'P'):
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                rgb_image.paste(image, mask=image.split()
                                [-1] if image.mode in ('RGBA', 'LA') else None)
                save_jpeg(rgb_image, jpeg_path, quality=self.jpeg_quality)
            else:
                save_jpeg(image, jpeg_path, quality=self.jpeg_quality)
            return jpeg_path

    @log_processing_time
    def handle(self, xls_path: Path, job_id: str) -> List[PageMetadata]:
        """Process Excel file and generate page images."""
        pages: List[PageMetadata] = []

        # Check for openpyxl
        try:
            import openpyxl
        except ImportError as e:
            logger.error("openpyxl required for Excel parsing: %s", e)
            return []

        # Load workbook
        try:
            # Load with data_only=False to preserve formulas, charts, etc.
            wb = openpyxl.load_workbook(
                xls_path, read_only=False, data_only=True)
        except Exception as e:
            logger.error("Failed to load workbook %s: %s", xls_path, e)
            return []

        # Process each worksheet
        for i, sheet_name in enumerate(wb.sheetnames):
            try:
                logger.info(
                    f"Processing sheet {i + 1}/{len(wb.sheetnames)}: '{sheet_name}'")

                # Get worksheet
                worksheet = wb[sheet_name]

                # Render worksheet to image
                sheet_image = self.renderer.render_worksheet(
                    worksheet, sheet_name)

                # Resize if needed
                if sheet_image.size[0] > self.max_side or sheet_image.size[1] > self.max_side:
                    sheet_image.thumbnail(
                        (self.max_side, self.max_side), Image.Resampling.LANCZOS)

                # Save image
                # Use PNG for better quality
                storage_key = page_image_key(job_id, i, ext="png")
                out_path = ensure_parent_dir(storage_key)

                saved_path = self._save_as_png_and_jpeg(sheet_image, out_path)

                # Update storage key to match saved format
                if saved_path.suffix == '.png':
                    storage_key = page_image_key(job_id, i, ext="png")

                pages.append(PageMetadata(
                    index=i, image=storage_key, elements=[]))

            except Exception as e:
                logger.warning(f"Failed to process sheet '{sheet_name}': {e}")
                # Create error placeholder
                try:
                    placeholder = Image.new('RGB', (800, 600), (245, 245, 245))
                    draw = ImageDraw.Draw(placeholder)
                    font = self.renderer._get_font(16)
                    draw.text((50, 50), f"Error processing sheet: {sheet_name}",
                              fill=(255, 0, 0), font=font)

                    storage_key = page_image_key(job_id, i, ext="png")
                    out_path = ensure_parent_dir(storage_key)
                    self._save_as_png_and_jpeg(placeholder, out_path)
                    pages.append(PageMetadata(
                        index=i, image=storage_key, elements=[]))

                except Exception as placeholder_error:
                    logger.error(
                        f"Failed to create placeholder for sheet '{sheet_name}': {placeholder_error}")

        try:
            wb.close()
        except Exception:
            pass

        logger.info(
            f"Excel processing complete: {len(pages)} sheets processed")
        return pages
# # backend/file_ingestion/handlers/excel_handler.py
# from __future__ import annotations
# from pathlib import Path
# from typing import List
# import logging
# from PIL import Image

# from backend.schemas.ingest import PageMetadata
# from backend.utils.helpers import save_jpeg
# from backend.utils.trackers import log_processing_time
# from backend.utils.storage_paths import page_image_key, ensure_parent_dir

# logger = logging.getLogger(__name__)


# def _sanitize(name: str) -> str:
#     return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)


# class ExcelHandler:
#     def __init__(self, img_pages_dir: Path, max_side: int, jpeg_quality: int):
#         self.img_pages_dir = img_pages_dir
#         self.max_side = max_side
#         self.jpeg_quality = jpeg_quality

#     @log_processing_time
#     def handle(self, xls_path: Path, job_id: str) -> List[PageMetadata]:
#         pages: List[PageMetadata] = []
#         try:
#             import openpyxl
#         except Exception as e:
#             logger.error("openpyxl required for Excel parsing: %s", e)
#             return []

#         try:
#             wb = openpyxl.load_workbook(
#                 xls_path, read_only=True, data_only=True)
#         except Exception as e:
#             logger.error("Failed to load workbook: %s", e)
#             return []

#         excel_to_img_ok = True
#         try:
#             import excel2img  # type: ignore
#         except Exception:
#             excel_to_img_ok = False
#             logger.warning(
#                 "excel2img not installed — will create placeholders.")

#         for i, sheet_name in enumerate(wb.sheetnames):
#             # Use PNG then save JPEG, or placeholder
#             storage_key = page_image_key(job_id, i, ext="jpeg")
#             out_path = ensure_parent_dir(storage_key)

#             if excel_to_img_ok:
#                 try:
#                     tmp_png = out_path.with_suffix(".png")
#                     excel2img.export_img(
#                         xls_path.as_posix(), tmp_png.as_posix(), sheet_name)
#                     img = Image.open(tmp_png)
#                     img.thumbnail((self.max_side, self.max_side))
#                     save_jpeg(img, out_path, quality=self.jpeg_quality)
#                     try:
#                         tmp_png.unlink(missing_ok=True)
#                     except Exception:
#                         pass
#                 except Exception as e:
#                     logger.warning(
#                         "excel2img failed for %s: %s", sheet_name, e)
#                     with Image.new("RGB", (1200, 675), (245, 245, 245)) as ph:
#                         save_jpeg(ph, out_path, quality=70)
#             else:
#                 with Image.new("RGB", (1200, 675), (245, 245, 245)) as ph:
#                     save_jpeg(ph, out_path, quality=70)

#             pages.append(PageMetadata(index=i, image=storage_key, elements=[]))
#         logger.info("Excel sheets processed: %d", len(pages))
#         return pages
