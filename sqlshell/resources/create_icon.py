import os
import sys
from PIL import Image, ImageDraw, ImageFont

def create_sql_icon(output_path, size=256):
    """Create a professional SQL icon with improved readability"""
    # Create a new image with a transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Define colors
    primary_color = (44, 62, 80, 255)      # Dark blue-gray
    secondary_color = (52, 152, 219, 255)  # Bright blue
    text_color = (236, 240, 241, 255)      # Light gray for better readability
    accent_color = (26, 188, 156, 255)     # Teal
    
    # Draw a rounded rectangle background
    radius = size // 8
    rect = [(size//12, size//12), (size - size//12, size - size//12)]
    draw.rounded_rectangle(rect, radius, fill=primary_color)
    
    # Try to load fonts in order of preference
    font_size = size // 4  # Slightly smaller for better readability
    font = None
    
    # Common fonts list to try
    font_options = [
        "Arial Bold", "Arial", "Helvetica Bold", "Helvetica",
        "DejaVuSans-Bold.ttf", "DejaVuSans.ttf", 
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    
    for font_name in font_options:
        try:
            font = ImageFont.truetype(font_name, font_size)
            break
        except IOError:
            continue
    
    if font is None:
        font = ImageFont.load_default()
        font_size = size // 5  # Adjust size for default font
    
    # Draw "SQL" text with improved visibility
    text = "SQL"
    
    # Handle different PIL versions for text size calculation
    if hasattr(draw, 'textsize'):
        text_width, text_height = draw.textsize(text, font=font)
    elif hasattr(font, 'getsize'):
        text_width, text_height = font.getsize(text)
    else:
        # Fallback for newer PIL versions
        try:
            text_width, text_height = font.getbbox(text)[2:]
        except:
            text_width, text_height = font_size * 3, font_size
    
    # Position text slightly higher
    position = ((size - text_width) // 2, (size - text_height) // 2 - size//12)
    
    # Draw text with subtle shadow for better readability
    shadow_offset = max(1, size // 64)
    draw.text((position[0] + shadow_offset, position[1] + shadow_offset), 
              text, fill=(0, 0, 0, 100), font=font)
    draw.text(position, text, fill=text_color, font=font)
    
    # Draw a small database icon
    db_size = size // 3
    db_x = size // 2 - db_size // 2
    db_y = size // 2 + text_height // 2 + db_size // 4
    
    # Draw database cylinder with improved shape
    # Top ellipse
    draw.ellipse([(db_x, db_y - db_size//4), (db_x + db_size, db_y)], 
                fill=secondary_color)
    # Bottom ellipse
    draw.ellipse([(db_x, db_y + db_size//2), (db_x + db_size, db_y + db_size//1.5)], 
                fill=secondary_color)
    # Rectangle body
    draw.rectangle([(db_x, db_y), (db_x + db_size, db_y + db_size//2)], 
                  fill=secondary_color)
    
    # Add subtle details to database
    highlight_color = (72, 172, 240, 150)  # Lighter blue for highlight
    # Database line details
    line_y1 = db_y + db_size//6
    line_y2 = db_y + db_size//3
    draw.line([(db_x + db_size//6, line_y1), (db_x + db_size - db_size//6, line_y1)], 
             fill=highlight_color, width=max(1, size//128))
    draw.line([(db_x + db_size//6, line_y2), (db_x + db_size - db_size//6, line_y2)], 
             fill=highlight_color, width=max(1, size//128))
    
    # Save the image with compression
    img.save(output_path, optimize=True)
    print(f"Professional SQL icon created at {output_path}")
    return img

def create_logo(size=512):
    """Create a properly sized logo for different uses"""
    output_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.abspath(os.path.join(output_dir, '..', '..'))
    
    # Create different sizes
    sizes = {
        'icon': 128,           # For app icon
        'logo_small': 256,     # For UI elements
        'logo_medium': 512,    # For documentation
        'logo_large': 1024     # For high-res displays
    }
    
    for name, icon_size in sizes.items():
        output_path = os.path.join(output_dir, f"{name}.png")
        create_sql_icon(output_path, icon_size)
    
    # Create the main logo file at the root directory
    main_logo_path = os.path.join(project_dir, "sqlshell_logo.png")
    logo = create_sql_icon(main_logo_path, size)
    print(f"Main logo created at {main_logo_path}")

if __name__ == "__main__":
    # Default size is 512 if no argument provided
    size = 512
    if len(sys.argv) > 1:
        try:
            size = int(sys.argv[1])
        except ValueError:
            print(f"Invalid size argument: {sys.argv[1]}. Using default size {size}.")
    
    create_logo(size) 