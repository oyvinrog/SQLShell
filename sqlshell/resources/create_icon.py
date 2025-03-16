import os
from PIL import Image, ImageDraw, ImageFont

def create_sql_icon(output_path, size=256):
    """Create a simple SQL icon"""
    # Create a new image with a transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Define colors
    primary_color = (44, 62, 80, 255)  # Dark blue-gray
    secondary_color = (52, 152, 219, 255)  # Bright blue
    accent_color = (26, 188, 156, 255)  # Teal
    
    # Draw a rounded rectangle background
    radius = size // 10
    rect = [(size//8, size//8), (size - size//8, size - size//8)]
    draw.rounded_rectangle(rect, radius, fill=primary_color)
    
    # Try to load a font, fall back to default if not available
    try:
        font_size = size // 3
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()
    
    # Draw SQL text
    text = "SQL"
    text_width, text_height = draw.textsize(text, font=font) if hasattr(draw, 'textsize') else font.getsize(text)
    position = ((size - text_width) // 2, (size - text_height) // 2)
    draw.text(position, text, fill=accent_color, font=font)
    
    # Draw a small database icon
    db_size = size // 4
    db_x = size // 2 - db_size // 2
    db_y = size // 2 + text_height // 2 + db_size // 2
    
    # Draw database cylinder
    draw.ellipse([(db_x, db_y - db_size//3), (db_x + db_size, db_y)], fill=secondary_color)
    draw.ellipse([(db_x, db_y + db_size//3), (db_x + db_size, db_y + db_size//1.5)], fill=secondary_color)
    draw.rectangle([(db_x, db_y), (db_x + db_size, db_y + db_size//3)], fill=secondary_color)
    
    # Save the image
    img.save(output_path)
    print(f"Icon created at {output_path}")

if __name__ == "__main__":
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "icon.png")
    create_sql_icon(output_path) 