from PIL import Image, ImageDraw, ImageFont
import os
import math

def create_frame(size, progress, text=None):  # We won't use text parameter anymore
    # Create a new image with a dark background
    img = Image.new('RGBA', size, (44, 62, 80, 255))  # Dark blue-gray background
    draw = ImageDraw.Draw(img)
    
    # Calculate dimensions
    width, height = size
    center_x = width // 2
    center_y = height // 2
    
    # Create a subtle circular pattern
    radius = 60
    num_dots = 12
    dot_size = 4
    trail_length = 6
    
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
                draw.ellipse(
                    (x - current_size, y - current_size,
                     x + current_size, y + current_size),
                    fill=(52, 152, 219, current_opacity)  # Bright blue with fading opacity
                )
    
    return img

def create_splash_gif():
    size = (400, 300)
    frames = []
    
    # Create 60 frames for smooth animation
    for i in range(60):
        progress = i / 60
        frame = create_frame(size, progress)
        frames.append(frame)
    
    # Save the animated GIF
    output_path = os.path.join(os.path.dirname(__file__), "splash_screen.gif")
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=50,  # 50ms per frame = 20fps
        loop=0,
        optimize=False
    )
    print(f"Created splash screen GIF at: {output_path}")

if __name__ == "__main__":
    create_splash_gif() 