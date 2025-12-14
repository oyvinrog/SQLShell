#!/usr/bin/env python3
"""
Script to split the christmas_theme_original.png into individual decoration images
with transparent backgrounds.
"""

from PIL import Image
import os

def remove_background(img, threshold=240):
    """Remove the cream/white background and make it transparent."""
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    data = img.getdata()
    new_data = []
    
    for item in data:
        r, g, b, a = item
        # Check if pixel is close to the cream background color (#F5F0E8 or similar light colors)
        # The background in the image appears to be a light cream color
        if r > threshold and g > threshold - 10 and b > threshold - 20:
            # Make it transparent
            new_data.append((r, g, b, 0))
        else:
            new_data.append(item)
    
    img.putdata(new_data)
    return img

def crop_to_content(img, padding=5):
    """Crop image to content, removing transparent borders."""
    # Get the bounding box of non-transparent pixels
    bbox = img.getbbox()
    if bbox:
        # Add padding
        left = max(0, bbox[0] - padding)
        top = max(0, bbox[1] - padding)
        right = min(img.width, bbox[2] + padding)
        bottom = min(img.height, bbox[3] + padding)
        return img.crop((left, top, right, bottom))
    return img

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    original_path = os.path.join(script_dir, 'christmas_theme_original.png')
    
    # Open the original image
    original = Image.open(original_path)
    
    # Convert to RGBA
    original = original.convert('RGBA')
    
    # Define approximate bounding boxes for each decoration (x, y, width, height)
    # Based on the 1024x1024 image layout
    decorations = {
        # Row 1
        'santa_hat': (0, 0, 340, 320),
        'pine_branch': (280, 0, 440, 360),
        'bow': (680, 0, 344, 340),
        
        # Row 2
        'holly_large': (0, 280, 200, 220),
        'star': (200, 320, 140, 140),
        'candy_cane': (300, 280, 200, 280),
        'stocking': (540, 260, 300, 340),
        
        # Row 3
        'holly_small': (0, 500, 180, 180),
        'gift_box': (80, 640, 340, 340),
        'snowman': (380, 580, 300, 400),
        'wreath': (680, 580, 344, 400),
    }
    
    for name, (x, y, w, h) in decorations.items():
        # Crop the region
        region = original.crop((x, y, x + w, y + h))
        
        # Remove background
        region = remove_background(region)
        
        # Crop to content
        region = crop_to_content(region)
        
        # Save the image
        output_path = os.path.join(script_dir, f'{name}.png')
        region.save(output_path, 'PNG')
        print(f'Saved: {name}.png ({region.width}x{region.height})')

if __name__ == '__main__':
    main()
