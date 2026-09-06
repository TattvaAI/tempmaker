import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

with open('video_text.json') as f:
    config = json.load(f)

# Load fonts
f_greatvibes = lambda s: ImageFont.truetype('fonts/GreatVibes-Regular.ttf', s)
f_cinzel = lambda s: ImageFont.truetype('fonts/Cinzel.ttf', s)
f_playfair = lambda s: ImageFont.truetype('fonts/PlayfairDisplay.ttf', s)
f_cormorant = lambda s: ImageFont.truetype('fonts/CormorantGaramond-Bold.ttf', s)
f_rozha = lambda s: ImageFont.truetype('fonts/RozhaOne-Regular.ttf', s)
f_alex = lambda s: ImageFont.truetype('fonts/AlexBrush-Regular.ttf', s)
f_dancing = lambda s: ImageFont.truetype('fonts/DancingScript.ttf', s)

def draw_text_centered(draw, text, cy, font, fill, stroke_fill=None, stroke_width=0):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (1080 - w) // 2
    y = cy - h // 2
    draw.text((x, y), text, font=font, fill=fill, stroke_fill=stroke_fill, stroke_width=stroke_width)

cap = cv2.VideoCapture('clean_base.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)

# Test Scene 3 (sec 12)
cap.set(cv2.CAP_PROP_POS_FRAMES, int(12.0 * fps))
_, f_sc3 = cap.read()
img = Image.fromarray(cv2.cvtColor(f_sc3, cv2.COLOR_BGR2RGB))
draw = ImageDraw.Draw(img)
c3 = config['scene_3_announcement']
draw_text_centered(draw, c3['monogram'], 150, f_cormorant(90), (30, 63, 120))
draw_text_centered(draw, c3['couple_names'], 340, f_greatvibes(120), (195, 34, 106), stroke_fill=(255, 255, 255), stroke_width=2)
draw_text_centered(draw, c3['subtext'], 490, f_dancing(75), (30, 80, 148))
draw_text_centered(draw, c3['date'], 630, f_playfair(65), (30, 80, 148))
img.save('debug_frames/render_test_sc3.png')

# Test Scene 8 (sec 45)
cap.set(cv2.CAP_PROP_POS_FRAMES, int(45.0 * fps))
_, f_sc8 = cap.read()
img = Image.fromarray(cv2.cvtColor(f_sc8, cv2.COLOR_BGR2RGB))
draw = ImageDraw.Draw(img)
c8 = config['scene_8_wedding']
draw_text_centered(draw, c8['title'], 310, f_greatvibes(130), (164, 30, 86), stroke_fill=(255, 255, 255), stroke_width=2)
draw_text_centered(draw, c8['on_text'], 460, f_playfair(44), (50, 75, 49))
draw_text_centered(draw, c8['date'], 560, f_greatvibes(100), (164, 30, 86), stroke_fill=(255, 255, 255), stroke_width=1)
draw_text_centered(draw, "✦ ──── ✦ ──── ✦", 640, f_playfair(32), (43, 68, 42))
draw_text_centered(draw, c8['time'], 700, f_playfair(46), (43, 68, 42))
draw_text_centered(draw, "✦ ──── ✦ ──── ✦", 780, f_playfair(32), (43, 68, 42))
draw_text_centered(draw, c8['venue_label'], 860, f_greatvibes(95), (164, 30, 86), stroke_fill=(255, 255, 255), stroke_width=1)
draw_text_centered(draw, c8['venue_name'], 960, f_playfair(52), (43, 68, 42))
img.save('debug_frames/render_test_sc8.png')

print("Test render frames saved successfully!")
