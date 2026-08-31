"""
Image Preprocessing Service for Part 4C: OCR & Image Preprocessing
Provides computer vision pipelines using OpenCV and PyMuPDF rendering:
- High-fidelity PDF page rendering (200-300 DPI)
- Grayscale conversion, adaptive contrast enhancement (CLAHE)
- Bilateral denoising to preserve fine alphanumeric strokes (PAN, GSTIN, Udyam)
- Deskewing & orientation detection
- Laplacian sharpness & blur detection
"""

import logging
from typing import Optional, Tuple
import cv2
import numpy as np
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class ImagePreprocessingError(Exception):
    """Exception raised during image preprocessing failures."""
    def __init__(self, error_code: str, error_message: str):
        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message


def render_pdf_page_to_image(
    pdf_bytes: bytes,
    page_number: int,
    dpi: int = 200,
) -> np.ndarray:
    """
    Renders a single PDF page into a high-resolution BGR OpenCV image matrix.
    Uses PyMuPDF Pixmap rendering with calculated zoom scaling.
    """
    if not pdf_bytes or len(pdf_bytes) == 0:
        raise ImagePreprocessingError("EMPTY_PDF_BYTES", "Cannot render page from empty PDF binary.")

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.error("Failed to open PDF stream for rendering: %s", e)
        raise ImagePreprocessingError("PDF_OPEN_FAILED", "Failed to open PDF stream for rendering.")

    try:
        if page_number < 1 or page_number > doc.page_count:
            raise ImagePreprocessingError(
                "PAGE_OUT_OF_BOUNDS",
                f"Requested page {page_number} is out of bounds (1..{doc.page_count}).",
            )

        page = doc.load_page(page_number - 1)
        zoom = dpi / 72.0  # 72 points per inch standard PDF coordinate system
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        # Convert pixmap samples to numpy ndarray and then BGR OpenCV matrix
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, 3))
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        return img_bgr
    finally:
        doc.close()


def load_image_bytes_to_cv2(image_bytes: bytes) -> np.ndarray:
    """Decodes raw image bytes (PNG, JPG, JPEG) into an OpenCV BGR matrix."""
    if not image_bytes or len(image_bytes) == 0:
        raise ImagePreprocessingError("EMPTY_IMAGE_BYTES", "Uploaded image binary contains 0 bytes.")

    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ImagePreprocessingError(
            "IMAGE_DECODE_FAILED",
            "The image file is corrupted or formatted invalidly and could not be decoded.",
        )
    return img


def calculate_image_sharpness(img_bgr_or_gray: np.ndarray) -> float:
    """Calculates focus/sharpness score using variance of the Laplacian operator."""
    if len(img_bgr_or_gray.shape) == 3:
        gray = cv2.cvtColor(img_bgr_or_gray, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_bgr_or_gray
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def deskew_image(img_gray: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Detects skew angle in document image and rotates to horizontal alignment.
    Preserves document boundary.
    """
    coords = np.column_stack(np.where(img_gray < 240))
    if len(coords) < 100:
        return img_gray, 0.0

    angle = 0.0
    try:
        # MinAreaRect returns angle in range [-90, 0)
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # If angle is negligible (< 0.5 degrees), return original
        if abs(angle) < 0.5 or abs(angle) > 45:
            return img_gray, 0.0

        (h, w) = img_gray.shape[:2]
        center = (w // 2, h // 2)
        m = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            img_gray,
            m,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated, angle
    except Exception as e:
        logger.debug("Deskew calculation skipped: %s", e)
        return img_gray, 0.0


def preprocess_document_image(
    img_bgr: np.ndarray,
    enhance_contrast: bool = True,
    denoise: bool = True,
    apply_deskew: bool = False,
) -> np.ndarray:
    """
    Applies conservative OpenCV preprocessing pipeline tailored for procurement documents:
    1. Grayscale conversion
    2. Optional deskewing
    3. Bilateral filter (smooths paper texture while keeping crisp text edges)
    4. CLAHE contrast enhancement for faded stamps / light print
    """
    if img_bgr is None or img_bgr.size == 0:
        raise ImagePreprocessingError("INVALID_IMAGE_MATRIX", "Cannot preprocess empty image matrix.")

    # 1. Grayscale conversion
    if len(img_bgr.shape) == 3:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_bgr.copy()

    # 2. Deskew if enabled
    if apply_deskew:
        gray, _ = deskew_image(gray)

    # 3. Bilateral filter for noise reduction without blurring characters
    if denoise:
        gray = cv2.bilateralFilter(gray, d=5, sigmaColor=50, sigmaSpace=50)

    # 4. Adaptive Contrast Enhancement (CLAHE)
    if enhance_contrast:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

    return gray
