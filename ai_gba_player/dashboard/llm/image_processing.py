"""
Image Processing Module for LLM Client

Handles image enhancement, validation, and file operations.
Provides clean encapsulation of image-related functionality.
"""

import os
import time
from pathlib import Path
from typing import Optional

try:
    import PIL.Image
    import PIL.ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ImageProcessor:
    """
    Handles image processing operations for LLM analysis.
    
    Provides methods for:
    - Image enhancement (scaling, contrast, saturation)  
    - File validation and waiting
    - Image format conversion
    """
    
    def __init__(self):
        """Initialize image processor"""
        self.pil_available = PIL_AVAILABLE
        if not self.pil_available:
            print("⚠️ PIL not available - image enhancement disabled")
    
    def wait_for_screenshot(self, screenshot_path: str, max_wait_seconds: int = 5, 
                           check_interval: float = 0.2) -> bool:
        """
        Wait for screenshot file to become available with proper size validation.
        
        Args:
            screenshot_path: Path to screenshot file
            max_wait_seconds: Maximum time to wait in seconds
            check_interval: How often to check file status
            
        Returns:
            bool: True if file becomes available, False if timeout
        """
        total_waited = 0.0
        min_file_size = 1000  # Minimum file size in bytes for valid screenshot
        
        while total_waited < max_wait_seconds:
            if os.path.exists(screenshot_path):
                try:
                    file_size = os.path.getsize(screenshot_path)
                    if file_size >= min_file_size:
                        print(f"✅ Screenshot ready: {os.path.basename(screenshot_path)} ({file_size} bytes)")
                        return True
                    else:
                        print(f"⏳ Screenshot file too small ({file_size} bytes), waiting...")
                except OSError:
                    # File exists but couldn't get size - might be in process of writing
                    pass
            else:
                print(f"⏳ Screenshot file doesn't exist yet, waiting...")
            
            time.sleep(check_interval)
            total_waited += check_interval
        
        print(f"⚠️ Screenshot not ready after {max_wait_seconds}s: {os.path.basename(screenshot_path)}")
        return False
    
    def enhance_image(self, image_path: str) -> Optional[PIL.Image.Image]:
        """
        Enhance image for better LLM analysis.
        
        Applies scaling, contrast, and saturation improvements to make
        screenshots clearer for LLM vision models.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            PIL.Image.Image: Enhanced image, or original if enhancement fails
            
        Raises:
            FileNotFoundError: If image file doesn't exist
            PIL.UnidentifiedImageError: If image format is invalid
        """
        if not self.pil_available:
            # Return None to indicate no enhancement possible
            return None
        
        try:
            # Load original image
            original_image = PIL.Image.open(image_path)
            print(f"📸 Original image: {original_image.size[0]}x{original_image.size[1]}")
            
            # Enhancement parameters optimized for retro game screenshots
            scale_factor = 3.0
            contrast_factor = 1.5
            saturation_factor = 1.8
            brightness_factor = 1.1
            
            # Scale up the image for better detail visibility
            new_size = (
                int(original_image.size[0] * scale_factor),
                int(original_image.size[1] * scale_factor)
            )
            enhanced_image = original_image.resize(new_size, PIL.Image.LANCZOS)
            
            # Apply contrast enhancement
            enhancer = PIL.ImageEnhance.Contrast(enhanced_image)
            enhanced_image = enhancer.enhance(contrast_factor)
            
            # Apply saturation enhancement (for color images)
            if enhanced_image.mode in ('RGB', 'RGBA'):
                enhancer = PIL.ImageEnhance.Color(enhanced_image)
                enhanced_image = enhancer.enhance(saturation_factor)
            
            # Apply brightness adjustment
            enhancer = PIL.ImageEnhance.Brightness(enhanced_image)
            enhanced_image = enhancer.enhance(brightness_factor)
            
            print(f"✨ Enhanced image: {enhanced_image.size[0]}x{enhanced_image.size[1]} "
                  f"(scale: {scale_factor}x, contrast: {contrast_factor}x)")
            
            return enhanced_image
            
        except Exception as e:
            print(f"⚠️ Image enhancement failed: {e}")
            # Try to return original image as fallback
            try:
                return PIL.Image.open(image_path)
            except Exception as fallback_error:
                print(f"❌ Could not load image: {fallback_error}")
                raise fallback_error
    
    def validate_image_file(self, image_path: str) -> bool:
        """
        Validate that an image file exists and is readable.
        
        Args:
            image_path: Path to image file
            
        Returns:
            bool: True if valid image file, False otherwise
        """
        if not os.path.exists(image_path):
            return False
        
        try:
            file_size = os.path.getsize(image_path)
            if file_size < 1000:  # Too small to be a valid screenshot
                return False
        except OSError:
            return False
        
        if self.pil_available:
            try:
                with PIL.Image.open(image_path) as img:
                    img.verify()  # Verify image integrity
                return True
            except Exception:
                return False
        else:
            # Without PIL, just check file existence and size
            return True
    
    def get_image_info(self, image_path: str) -> dict:
        """
        Get information about an image file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            dict: Image information including size, format, mode
        """
        info = {
            'exists': os.path.exists(image_path),
            'size': None,
            'file_size': None,
            'format': None,
            'mode': None
        }
        
        if not info['exists']:
            return info
        
        try:
            info['file_size'] = os.path.getsize(image_path)
        except OSError:
            pass
        
        if self.pil_available:
            try:
                with PIL.Image.open(image_path) as img:
                    info['size'] = img.size
                    info['format'] = img.format
                    info['mode'] = img.mode
            except Exception:
                pass
        
        return info
    
    def save_enhanced_image(self, enhanced_image: PIL.Image.Image, 
                           output_path: str, quality: int = 95) -> bool:
        """
        Save enhanced image to file.
        
        Args:
            enhanced_image: PIL Image to save
            output_path: Where to save the image
            quality: JPEG quality (if saving as JPEG)
            
        Returns:
            bool: True if saved successfully
        """
        if not self.pil_available or enhanced_image is None:
            return False
        
        try:
            # Create output directory if needed
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save image with appropriate format
            if output_path.lower().endswith(('.jpg', '.jpeg')):
                enhanced_image.save(output_path, 'JPEG', quality=quality)
            elif output_path.lower().endswith('.png'):
                enhanced_image.save(output_path, 'PNG')
            else:
                # Default to PNG for unknown extensions
                enhanced_image.save(output_path, 'PNG')
            
            print(f"💾 Enhanced image saved to: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save enhanced image: {e}")
            return False