"""
Test script for ImagePickerField changes.
Tests:
1. Image path resolution for existing images
2. Image preview display when editing products
"""
import sys
import os
import tempfile
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import  QPixmap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui.widgets import ImagePickerField, PRODUCT_IMG_DIR

# Create a QApplication instance (required for Qt widgets)
app = QApplication([])

# Test 1: Path resolution
print("=" * 60)
print("Test 1: Image path resolution")
print("=" * 60)
test_filename = "test_image.jpg"
resolved_path = ImagePickerField._resolve_image_path(None, test_filename)
print(f"Input filename: {test_filename}")
print(f"Resolved path: {resolved_path}")
print(f"Is absolute path: {os.path.isabs(resolved_path)}")
print(f"PRODUCT_IMG_DIR: {PRODUCT_IMG_DIR}")
print()

# Test 2: Create temporary test image
print("=" * 60)
print("Test 2: Create test image and verify preview")
print("=" * 60)
# Create a simple test image
test_img_dir = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "public", "dist", "img")
os.makedirs(test_img_dir, exist_ok=True)

# Create a simple 100x100 red image for testing
test_img_path = os.path.join(test_img_dir, "test_product_img.png")
from PyQt6.QtGui import QImage, QColor
img = QImage(100, 100, QImage.Format.Format_RGB32)
img.fill(QColor("red"))
img.save(test_img_path)
print(f"Created test image: {test_img_path}")
print(f"Image exists: {os.path.exists(test_img_path)}")
print()

# Test 3: ImagePickerField with existing image
print("=" * 60)
print("Test 3: ImagePickerField with existing image (edit scenario)")
print("=" * 60)
field = ImagePickerField("test_product_img.png")
field.show()
app.processEvents()

# Check if preview is showing
pixmap = field.preview.pixmap()
print(f"Preview has pixmap: {not pixmap.isNull() if pixmap else False}")
print(f"Preview size: {field.preview.size()}")
print(f"Filename edit text: {field.name_edit.text()}")
print()

# Test 4: ImagePickerField with no image
print("=" * 60)
print("Test 4: ImagePickerField with no image")
print("=" * 60)
field2 = ImagePickerField("")
field2.show()
app.processEvents()
pixmap2 = field2.preview.pixmap()
print(f"Preview has pixmap (no image): {not pixmap2.isNull() if pixmap2 else False}")
print(f"Filename edit text (empty): '{field2.name_edit.text()}'")
print()

# Clean up
import shutil
try:
    os.remove(test_img_path)
    print(f"Cleaned up test image")
except:
    pass

print("=" * 60)
print("All tests completed!")
print("=" * 60)

# Keep the app running briefly to show widgets
import time
time.sleep(1)
