import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

with open('video_text.json') as f:
    config = json.load(f)

# Fonts
fonts = {
    'greatvibes_130': ImageFont.truetype('fonts/GreatVibes-Regular.ttf', 130),
    'greatvibes_120': ImageFont.truetype('fonts/GreatVibes-Regular.ttf', 120),
    'greatvibes_110': ImageFont.truetype('fonts/GreatVibes-Regular.ttf', 110),
    'greatvibes_95': ImageFont.truetype('fonts/GreatVibes-Regular.ttf', 95),
    'cinzel_38': ImageFont.truetype('fonts/Cinzel.ttf', 38),
    'cinzel_36': ImageFont.truetype('fonts/Cinzel.ttf', 36),
    'dancing_75': ImageFont.truetype('fonts/DancingScript.ttf', 75),
    'alex_80': ImageFont.truetype('fonts/AlexBrush-Regular.ttf', 80),
    'rozha_140': ImageFont.truetype('fonts/RozhaOne-Regular.ttf', 140),
    'rozha_42': ImageFont.truetype('fonts/RozhaOne-Regular.ttf', 42),
    'georgia_36': ImageFont.truetype('fonts/Georgia.ttf', 36),
    'georgia_38': ImageFont.truetype('fonts/Georgia.ttf', 38),
    'georgia_42': ImageFont.truetype('fonts/Georgia.ttf', 42),
    'georgia_italic_40': ImageFont.truetype('fonts/Georgia Italic.ttf', 40),
    'georgia_italic_44': ImageFont.truetype('fonts/Georgia Italic.ttf', 44),
    'georgia_bold_italic_42': ImageFont.truetype('fonts/Georgia Bold.ttf', 42),
    'georgia_bold_italic_46': ImageFont.truetype('fonts/Georgia Bold.ttf', 46),
    'georgia_bold_italic_50': ImageFont.truetype('fonts/Georgia Bold.ttf', 50),
    'georgia_bold_52': ImageFont.truetype('fonts/Georgia Bold.ttf', 52),
}

def draw_centered(draw, text, cy, font, fill_rgba, stroke_rgba=None, stroke_width=0):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (1080 - w) // 2
    y = cy - h // 2
    draw.text((x, y), text, font=font, fill=fill_rgba, stroke_fill=stroke_rgba, stroke_width=stroke_width)

def render_frame_text(base_bgr, frame_idx):
    overlay = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Scene 2 (frames 170..240)
    if 170 <= frame_idx < 240:
        alpha = min(1.0, max(0.0, (frame_idx - 170) / 25.0))
        a_val = int(alpha * 255)
        c2 = config['scene_2_monogram']
        draw_centered(draw, c2['initials'], 430, fonts['georgia_bold_52'], (58, 72, 60, a_val))

    # Scene 3 (frames 300..410)
    elif 300 <= frame_idx < 410:
        c3 = config['scene_3_announcement']
        # Monogram
        a_logo = int(min(1.0, max(0.0, (frame_idx - 300) / 20.0)) * 255)
        draw_centered(draw, c3['monogram'], 150, fonts['georgia_bold_52'], (30, 63, 120, a_logo))
        # Names
        a_names = int(min(1.0, max(0.0, (frame_idx - 305) / 25.0)) * 255)
        draw_centered(draw, c3['couple_names'], 340, fonts['greatvibes_120'], (195, 34, 106, a_names), stroke_rgba=(255, 255, 255, a_names), stroke_width=2)
        # Subtext
        a_sub = int(min(1.0, max(0.0, (frame_idx - 330) / 25.0)) * 255)
        draw_centered(draw, c3['subtext'], 490, fonts['dancing_75'], (30, 80, 148, a_sub))
        # Date
        a_date = int(min(1.0, max(0.0, (frame_idx - 350) / 25.0)) * 255)
        draw_centered(draw, c3['date'], 630, fonts['georgia_bold_italic_50'], (30, 80, 148, a_date))

    # Scene 4 (frames 415..760)
    elif 415 <= frame_idx < 760:
        c4 = config['scene_4_invitation']
        # Shloka & headers
        a1 = int(min(1.0, max(0.0, (frame_idx - 415) / 25.0)) * 255)
        draw_centered(draw, c4['shloka'], 200, fonts['rozha_42'], (214, 123, 39, a1))
        draw_centered(draw, c4['header_line1'], 270, fonts['georgia_italic_40'], (44, 94, 84, a1))
        draw_centered(draw, c4['header_line2'], 335, fonts['georgia_italic_40'], (44, 94, 84, a1))
        
        # Groom
        if frame_idx >= 480:
            a_groom = int(min(1.0, max(0.0, (frame_idx - 480) / 25.0)) * 255)
            draw_centered(draw, c4['groom_name'], 480, fonts['greatvibes_130'], (216, 38, 114, a_groom))
        # Groom parents
        if frame_idx >= 530:
            a_gp = int(min(1.0, max(0.0, (frame_idx - 530) / 25.0)) * 255)
            draw_centered(draw, c4['groom_parents_relation'], 595, fonts['georgia_italic_40'], (44, 94, 84, a_gp))
            draw_centered(draw, c4['groom_parents_line1'], 655, fonts['georgia_bold_italic_42'], (44, 94, 84, a_gp))
            draw_centered(draw, c4['groom_parents_line2'], 710, fonts['georgia_bold_italic_42'], (44, 94, 84, a_gp))
        # With
        if frame_idx >= 570:
            a_with = int(min(1.0, max(0.0, (frame_idx - 570) / 20.0)) * 255)
            draw_centered(draw, c4['conjunction'], 800, fonts['georgia_italic_44'], (30, 60, 52, a_with))
        # Bride
        if frame_idx >= 600:
            a_bride = int(min(1.0, max(0.0, (frame_idx - 600) / 25.0)) * 255)
            draw_centered(draw, c4['bride_name'], 950, fonts['greatvibes_130'], (216, 38, 114, a_bride))
        # Bride parents
        if frame_idx >= 640:
            a_bp = int(min(1.0, max(0.0, (frame_idx - 640) / 25.0)) * 255)
            draw_centered(draw, c4['bride_parents_relation'], 1070, fonts['georgia_italic_40'], (44, 94, 84, a_bp))
            draw_centered(draw, c4['bride_parents_line1'], 1130, fonts['georgia_bold_italic_42'], (44, 94, 84, a_bp))
            draw_centered(draw, c4['bride_parents_line2'], 1185, fonts['georgia_bold_italic_42'], (44, 94, 84, a_bp))

    # Scene 5 (Haldi: frames 780..935)
    elif 780 <= frame_idx < 935:
        c5 = config['scene_5_haldi']
        a5 = int(min(1.0, max(0.0, (frame_idx - 780) / 25.0)) * 255)
        draw_centered(draw, c5['header'], 310, fonts['georgia_38'], (255, 255, 255, a5))
        # Haldi Title with warm golden glow
        draw_centered(draw, c5['title'], 470, fonts['greatvibes_120'], (255, 241, 118, a5), stroke_rgba=(245, 166, 35, a5), stroke_width=4)
        draw_centered(draw, c5['on_text'], 600, fonts['georgia_italic_40'], (255, 255, 255, a5))
        draw_centered(draw, c5['date'], 690, fonts['alex_80'], (255, 255, 255, a5))
        draw_centered(draw, c5['time'], 800, fonts['georgia_42'], (255, 255, 255, a5))
        draw_centered(draw, c5['venue_label'], 890, fonts['georgia_38'], (255, 255, 255, a5))
        draw_centered(draw, c5['venue_name'], 960, fonts['georgia_bold_italic_42'], (255, 255, 255, a5))
        draw_centered(draw, c5['address_line1'], 1020, fonts['georgia_36'], (255, 255, 255, a5))
        draw_centered(draw, c5['address_line2'], 1065, fonts['georgia_36'], (255, 255, 255, a5))

    # Scene 6 (Mehendi: frames 965..1085)
    elif 965 <= frame_idx < 1085:
        c6 = config['scene_6_mehendi']
        a6 = int(min(1.0, max(0.0, (frame_idx - 965) / 25.0)) * 255)
        draw_centered(draw, c6['header'], 520, fonts['georgia_36'], (34, 56, 40, a6))
        draw_centered(draw, c6['title_line1'], 640, fonts['greatvibes_110'], (46, 90, 54, a6))
        draw_centered(draw, c6['title_line2'], 750, fonts['greatvibes_110'], (46, 90, 54, a6))
        draw_centered(draw, c6['of_text'], 845, fonts['georgia_italic_40'], (34, 56, 40, a6))
        draw_centered(draw, c6['bride_name'], 935, fonts['greatvibes_110'], (46, 90, 54, a6))
        draw_centered(draw, c6['on_text'], 1020, fonts['georgia_italic_40'], (34, 56, 40, a6))
        draw_centered(draw, c6['date'], 1100, fonts['alex_80'], (46, 90, 54, a6))
        draw_centered(draw, c6['time'], 1200, fonts['georgia_bold_italic_42'], (34, 56, 40, a6))
        draw_centered(draw, c6['venue_name'], 1310, fonts['georgia_bold_italic_42'], (34, 56, 40, a6))
        draw_centered(draw, c6['address_line1'], 1365, fonts['georgia_38'], (34, 56, 40, a6))
        draw_centered(draw, c6['address_line2'], 1415, fonts['georgia_38'], (34, 56, 40, a6))

    # Scene 7 (Sangeet: frames 1115..1230)
    elif 1115 <= frame_idx < 1230:
        c7 = config['scene_7_sangeet']
        a7 = int(min(1.0, max(0.0, (frame_idx - 1115) / 25.0)) * 255)
        draw_centered(draw, c7['header_line1'], 510, fonts['cinzel_38'], (255, 255, 255, a7))
        draw_centered(draw, c7['header_line2'], 560, fonts['cinzel_38'], (255, 255, 255, a7))
        # Devanagari संगीत in gold with drop shadow
        draw_centered(draw, c7['event_name_hindi'], 735, fonts['rozha_140'], (30, 15, 20, int(a7 * 0.4)))
        draw_centered(draw, c7['event_name_hindi'], 730, fonts['rozha_140'], (248, 202, 63, a7))
        draw_centered(draw, c7['sub_header'], 915, fonts['cinzel_36'], (255, 255, 255, a7))
        draw_centered(draw, c7['bride_name'], 1020, fonts['greatvibes_120'], (248, 202, 63, a7))
        draw_centered(draw, c7['date'], 1150, fonts['cinzel_38'], (255, 255, 255, a7))
        draw_centered(draw, c7['venue_label'], 1220, fonts['cinzel_36'], (255, 255, 255, a7))
        draw_centered(draw, c7['venue_name'], 1280, fonts['cinzel_38'], (255, 255, 255, a7))

    # Scene 8 (Wedding: frames 1270..1425)
    elif 1270 <= frame_idx < 1425:
        c8 = config['scene_8_wedding']
        a8 = int(min(1.0, max(0.0, (frame_idx - 1270) / 25.0)) * 255)
        draw_centered(draw, c8['title'], 310, fonts['greatvibes_130'], (164, 30, 86, a8), stroke_rgba=(255, 255, 255, a8), stroke_width=2)
        draw_centered(draw, c8['on_text'], 460, fonts['georgia_italic_44'], (50, 75, 49, a8))
        draw_centered(draw, c8['date'], 560, fonts['greatvibes_110'], (164, 30, 86, a8), stroke_rgba=(255, 255, 255, a8), stroke_width=1)
        draw_centered(draw, "✦ ──── ✦ ──── ✦", 640, fonts['georgia_36'], (43, 68, 42, a8))
        draw_centered(draw, c8['time'], 700, fonts['georgia_bold_italic_46'], (43, 68, 42, a8))
        draw_centered(draw, "✦ ──── ✦ ──── ✦", 780, fonts['georgia_36'], (43, 68, 42, a8))
        draw_centered(draw, c8['venue_label'], 860, fonts['greatvibes_95'], (164, 30, 86, a8), stroke_rgba=(255, 255, 255, a8), stroke_width=1)
        draw_centered(draw, c8['venue_name'], 960, fonts['georgia_bold_italic_50'], (43, 68, 42, a8))

    # Scene 9 (Save the Date: frames 1455..1560)
    elif 1455 <= frame_idx < 1560:
        c9 = config['scene_9_closing']
        a9 = int(min(1.0, max(0.0, (frame_idx - 1455) / 25.0)) * 255)
        draw_centered(draw, c9['title'], 690, fonts['greatvibes_130'], (19, 75, 142, a9))
        draw_centered(draw, c9['date'], 830, fonts['georgia_bold_52'], (19, 75, 142, a9))

    base_pil = Image.fromarray(cv2.cvtColor(base_bgr, cv2.COLOR_BGR2RGB))
    base_pil.paste(overlay, (0, 0), overlay)
    return cv2.cvtColor(np.array(base_pil), cv2.COLOR_RGB2BGR)

# Test rendering a frame from each scene
cap = cv2.VideoCapture('clean_base.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)

sample_times = [7.0, 12.0, 23.0, 29.0, 35.0, 39.0, 45.0, 50.0]
for st in sample_times:
    idx = int(st * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    _, f = cap.read()
    rendered = render_frame_text(f, idx)
    cv2.imwrite(f'debug_frames/final_render_sec_{int(st)}.jpg', rendered)

cap.release()
print("Saved final render tests for all scenes!")
