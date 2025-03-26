from PIL import Image, ImageDraw, ImageFont
import os
import math

def create_frame(size, progress, text=None):
    # Create a new image with a dark background
    img = Image.new('RGBA', size, (44, 62, 80, 255))  # Dark blue-gray background
    draw = ImageDraw.Draw(img)
    
    # Calculate dimensions
    width, height = size
    center_x = width // 2
    center_y = height // 2
    
    # Create a more visible circular pattern
    radius = 80  # Larger radius
    num_dots = 12
    dot_size = 6  # Larger dots
    trail_length = 8  # Longer trail
    
    # Add a subtle gradient background
    for y in range(height):
        # Create a vertical gradient
        gradient_factor = y / height
        r = int(44 + (52 - 44) * gradient_factor)
        g = int(62 + (152 - 62) * gradient_factor)
        b = int(80 + (219 - 80) * gradient_factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    
    # Draw a pulsing circle
    pulse_size = 40 + 15 * math.sin(progress * 2 * math.pi)
    draw.ellipse(
        (center_x - pulse_size, center_y - pulse_size,
         center_x + pulse_size, center_y + pulse_size),
        outline=(52, 152, 219, 100),
        width=2
    )
    
    # Draw orbiting dots with trails
    for i in range(num_dots):
        # Calculate dot position
        angle = (progress * 360 - i * (360 / num_dots)) % 360
        x = center_x + radius * math.cos(math.radians(angle))
        y = center_y + radius * math.sin(math.radians(angle))
        
        # Calculate dot opacity based on position in trail
        opacity = int(255 * (1 - (i / trail_length))) if i < trail_length else 0
        
        if opacity > 0:
            # Draw dot with gradient effect
            for size_mult in [1.0, 0.8, 0.6]:
                current_size = int(dot_size * size_mult)
                current_opacity = int(opacity * size_mult)
                
                # Use more vibrant color for dots
                draw.ellipse(
                    (x - current_size, y - current_size,
                     x + current_size, y + current_size),
                    fill=(41, 128, 185, current_opacity)  # Brighter blue with fading opacity
                )
    
    # Add a subtle glow effect in the center
    glow_radius = 60 + 10 * math.sin(progress * 4 * math.pi)
    for r in range(int(glow_radius), 0, -5):
        opacity = int(100 * (r / glow_radius))
        draw.ellipse(
            (center_x - r, center_y - r, center_x + r, center_y + r),
            fill=(52, 152, 219, opacity // 8)  # Very transparent blue
        )
    
    return img

def create_splash_gif():
    size = (400, 300)
    frames = []
    
    # Create 30 frames for smooth animation (reduced from 60 for smaller file size)
    for i in range(30):
        progress = i / 30
        frame = create_frame(size, progress)
        frames.append(frame)
    
    # Save the animated GIF
    output_path = os.path.join(os.path.dirname(__file__), "splash_screen.gif")
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=66,  # 66ms per frame = ~15fps (reduced from 20fps for smaller file size)
        loop=0,
        optimize=True  # Enable optimization
    )
    print(f"Created splash screen GIF at: {output_path}")

if __name__ == "__main__":
    create_splash_gif() 