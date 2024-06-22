import random
import string
from PIL import Image, ImageDraw, ImageFont


def generate_captcha_text(length=4):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def generate_captcha_image(text):
    # Define dimensions
    width, height = 120, 40
    # Create a new image with white background
    image = Image.new('RGB', (width, height), 'white')
    # Create a draw object
    draw = ImageDraw.Draw(image)

    # Load a font (ensure the path to your font file is correct)
    font = ImageFont.truetype('arial.ttf', 30)

    # Calculate the width of each character to be drawn
    char_width = width // len(text)

    # Draw each character separately with random rotation
    for i, char in enumerate(text):
        # Create an image for each character
        char_image = Image.new('RGBA', (char_width, height), (255, 255, 255, 0))
        char_draw = ImageDraw.Draw(char_image)
        char_draw.text((10, 5), char, font=font, fill=(0, 0, 0))

        # Rotate the character image
        angle = random.randint(-30, 30)
        char_image = char_image.rotate(angle, expand=1)

        # Paste the rotated character image onto the main image
        image.paste(char_image, (i * char_width, 0), char_image)

    # Add noise points
    for _ in range(100):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

    # Add some noise lines
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),
                  width=1)

    return image


def check_code():
    captcha_text = generate_captcha_text()
    captcha_image = generate_captcha_image(captcha_text)
    captcha_image.save('captcha.png')

    return captcha_image,captcha_text


