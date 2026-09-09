import os
import sys
import time
import json
import argparse
import subprocess
import multiprocessing as mp
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# -------------------------------------------------------------
# Fonts loader
# -------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(SCRIPT_DIR, 'fonts')

def load_fonts():
    return {
        'greatvibes_130': ImageFont.truetype(os.path.join(FONTS_DIR, 'GreatVibes-Regular.ttf'), 130),
        'greatvibes_120': ImageFont.truetype(os.path.join(FONTS_DIR, 'GreatVibes-Regular.ttf'), 120),
        'greatvibes_110': ImageFont.truetype(os.path.join(FONTS_DIR, 'GreatVibes-Regular.ttf'), 110),
        'greatvibes_105': ImageFont.truetype(os.path.join(FONTS_DIR, 'GreatVibes-Regular.ttf'), 105),
        'greatvibes_95':  ImageFont.truetype(os.path.join(FONTS_DIR, 'GreatVibes-Regular.ttf'), 95),
        'cinzel_160':     ImageFont.truetype(os.path.join(FONTS_DIR, 'Cinzel.ttf'), 160),
        'cinzel_38':      ImageFont.truetype(os.path.join(FONTS_DIR, 'Cinzel.ttf'), 38),
        'cinzel_36':      ImageFont.truetype(os.path.join(FONTS_DIR, 'Cinzel.ttf'), 36),
        'cinzel_34':      ImageFont.truetype(os.path.join(FONTS_DIR, 'Cinzel.ttf'), 34),
        'dancing_75':     ImageFont.truetype(os.path.join(FONTS_DIR, 'DancingScript.ttf'), 75),
        'alex_80':        ImageFont.truetype(os.path.join(FONTS_DIR, 'AlexBrush-Regular.ttf'), 80),
        'rozha_140':      ImageFont.truetype(os.path.join(FONTS_DIR, 'RozhaOne-Regular.ttf'), 140),
        'rozha_42':       ImageFont.truetype(os.path.join(FONTS_DIR, 'RozhaOne-Regular.ttf'), 42),
        'georgia_32':     ImageFont.truetype(os.path.join(FONTS_DIR, 'Georgia.ttf'), 32),
        'georgia_36':     ImageFont.truetype(os.path.join(FONTS_DIR, 'Georgia.ttf'), 36),
        'georgia_38':     ImageFont.truetype(os.path.join(FONTS_DIR, 'Georgia.ttf'), 38),
        'georgia_42':     ImageFont.truetype(os.path.join(FONTS_DIR, 'Georgia.ttf'), 42),
        'georgia_italic_40': ImageFont.truetype(os.path.join(FONTS_DIR, 'Georgia Italic.ttf'), 40),
        'georgia_italic_44': ImageFont.truetype(os.path.join(FONTS_DIR, 'Georgia Italic.ttf'), 44),
        'georgia_bold_38': ImageFont.truetype(os.path.join(FONTS_DIR, 'Georgia Bold.ttf'), 38),
        'georgia_bold_italic_42': ImageFont.truetype(os.path.join(FONTS_DIR, 'Georgia Bold.ttf'), 42),
        'georgia_bold_italic_46': ImageFont.truetype(os.path.join(FONTS_DIR, 'Georgia Bold.ttf'), 46),
        'georgia_bold_italic_50': ImageFont.truetype(os.path.join(FONTS_DIR, 'Georgia Bold.ttf'), 50),
        'georgia_bold_52': ImageFont.truetype(os.path.join(FONTS_DIR, 'Georgia Bold.ttf'), 52),
    }

def draw_centered(draw, text, cy, font, fill_rgba, stroke_rgba=None, stroke_width=0, max_width=940):
    if not text:
        return
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    if max_width and w > max_width:
        scale = max_width / w
        new_size = max(18, int(font.size * scale))
        try:
            font = ImageFont.truetype(font.path, new_size)
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        except Exception:
            pass
    x = (1080 - w) // 2
    y = cy - h // 2
    draw.text((x, y), text, font=font, fill=fill_rgba, stroke_fill=stroke_rgba, stroke_width=stroke_width)

def draw_ornament_divider(draw, cy, color_rgba):
    # Elegant vector divider with diamonds and lines
    d_size = 8
    draw.polygon([(540, cy - d_size), (540 + d_size, cy), (540, cy + d_size), (540 - d_size, cy)], fill=color_rgba)
    draw.polygon([(390, cy - 6), (390 + 6, cy), (390, cy + 6), (390 - 6, cy)], fill=color_rgba)
    draw.polygon([(690, cy - 6), (690 + 6, cy), (690, cy + 6), (690 - 6, cy)], fill=color_rgba)
    draw.line([(405, cy), (525, cy)], fill=color_rgba, width=2)
    draw.line([(555, cy), (675, cy)], fill=color_rgba, width=2)

def render_frame_text(base_bgr, frame_idx, config, fonts, shloka_img=None):
    # If no text in this scene, return quickly
    if frame_idx < 170:
        return base_bgr
    if 240 <= frame_idx < 300:
        return base_bgr

    overlay = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Scene 2 (frames 170..240)
    if 170 <= frame_idx < 240:
        alpha = min(1.0, max(0.0, (frame_idx - 170) / 25.0))
        a_val = int(alpha * 255)
        c2 = config['scene_2_monogram']
        draw_centered(draw, c2['initials'], 380, fonts['cinzel_160'], (75, 95, 75, a_val))

    # Scene 3 (frames 300..410)
    elif 300 <= frame_idx < 410:
        c3 = config['scene_3_announcement']
        a_logo = int(min(1.0, max(0.0, (frame_idx - 300) / 20.0)) * 255)
        draw_centered(draw, c3['monogram'], 150, fonts['georgia_bold_52'], (30, 63, 120, a_logo))
        
        a_names = int(min(1.0, max(0.0, (frame_idx - 305) / 25.0)) * 255)
        draw_centered(draw, c3['couple_names'], 340, fonts['greatvibes_120'], (195, 34, 106, a_names), stroke_rgba=(255, 255, 255, a_names), stroke_width=2)
        
        a_sub = int(min(1.0, max(0.0, (frame_idx - 330) / 25.0)) * 255)
        draw_centered(draw, c3['subtext'], 490, fonts['dancing_75'], (30, 80, 148, a_sub))
        
        a_date = int(min(1.0, max(0.0, (frame_idx - 350) / 25.0)) * 255)
        draw_centered(draw, c3['date'], 630, fonts['georgia_bold_italic_50'], (30, 80, 148, a_date))


    # Scene 4 (frames 415..760)
    elif 415 <= frame_idx < 760:
        c4 = config['scene_4_invitation']
        a1 = int(min(1.0, max(0.0, (frame_idx - 415) / 25.0)) * 255)
        if shloka_img is not None:
            sw, sh = shloka_img.size
            sh_alpha = shloka_img.copy()
            r, g, b, a = sh_alpha.split()
            a = a.point(lambda p: int(p * a1 / 255.0))
            sh_alpha.putalpha(a)
            overlay.paste(sh_alpha, ((1080 - sw) // 2, 160), sh_alpha)
        else:
            draw_centered(draw, c4.get('shloka', '॥ श्री गणेशाय नमः ॥'), 180, fonts['rozha_42'], (214, 123, 39, a1))
        draw_centered(draw, c4.get('header_line1', ''), 255, fonts['georgia_italic_40'], (44, 94, 84, a1))
        draw_centered(draw, c4.get('header_line2', ''), 305, fonts['georgia_italic_40'], (44, 94, 84, a1), max_width=960)
        
        has_parents = (
            c4.get('bride_parents_line1') or c4.get('groom_parents_line1')
        )

        if has_parents:
            # Bride details
            if frame_idx >= 465:
                a_bride = int(min(1.0, max(0.0, (frame_idx - 465) / 20.0)) * 255)
                draw_centered(draw, c4.get('bride_name', 'Muskan'), 445, fonts['greatvibes_130'], (216, 38, 114, a_bride))
            if frame_idx >= 505:
                a_bp = int(min(1.0, max(0.0, (frame_idx - 505) / 20.0)) * 255)
                if c4.get('bride_parents_relation'):
                    draw_centered(draw, c4['bride_parents_relation'], 540, fonts['georgia_italic_40'], (44, 94, 84, a_bp))
                if c4.get('bride_parents_line1'):
                    draw_centered(draw, c4['bride_parents_line1'], 600, fonts['georgia_bold_italic_42'], (44, 94, 84, a_bp))
                if c4.get('bride_parents_line2'):
                    draw_centered(draw, c4['bride_parents_line2'], 655, fonts['georgia_bold_italic_42'], (44, 94, 84, a_bp))
            if frame_idx >= 545:
                a_with = int(min(1.0, max(0.0, (frame_idx - 545) / 15.0)) * 255)
                draw_centered(draw, c4.get('conjunction', 'With'), 740, fonts['georgia_italic_44'], (30, 60, 52, a_with))
            if frame_idx >= 575:
                a_groom = int(min(1.0, max(0.0, (frame_idx - 575) / 20.0)) * 255)
                draw_centered(draw, c4.get('groom_name', 'Shubham'), 880, fonts['greatvibes_130'], (216, 38, 114, a_groom))
            if frame_idx >= 615:
                a_gp = int(min(1.0, max(0.0, (frame_idx - 615) / 20.0)) * 255)
                if c4.get('groom_parents_relation'):
                    draw_centered(draw, c4['groom_parents_relation'], 975, fonts['georgia_italic_40'], (44, 94, 84, a_gp))
                if c4.get('groom_parents_line1'):
                    draw_centered(draw, c4['groom_parents_line1'], 1035, fonts['georgia_bold_italic_42'], (44, 94, 84, a_gp))
                if c4.get('groom_parents_line2'):
                    draw_centered(draw, c4['groom_parents_line2'], 1090, fonts['georgia_bold_italic_42'], (44, 94, 84, a_gp))
        else:
            if frame_idx >= 445:
                a_groom = int(min(1.0, max(0.0, (frame_idx - 445) / 20.0)) * 255)
                draw_centered(draw, c4.get('groom_name', ''), 510, fonts['greatvibes_130'], (216, 38, 114, a_groom))
            if frame_idx >= 485:
                a_with = int(min(1.0, max(0.0, (frame_idx - 485) / 15.0)) * 255)
                draw_centered(draw, c4.get('conjunction', 'With'), 630, fonts['georgia_italic_44'], (30, 60, 52, a_with))
            if frame_idx >= 510:
                a_bride = int(min(1.0, max(0.0, (frame_idx - 510) / 20.0)) * 255)
                draw_centered(draw, c4.get('bride_name', ''), 760, fonts['greatvibes_130'], (216, 38, 114, a_bride))
            if frame_idx >= 545 and c4.get('address_line1'):
                a_res = int(min(1.0, max(0.0, (frame_idx - 545) / 20.0)) * 255)
                if c4.get('residence_label'):
                    draw_centered(draw, c4['residence_label'], 930, fonts['georgia_bold_38'], (44, 94, 84, a_res))
                draw_centered(draw, c4['address_line1'], 990, fonts['georgia_36'], (44, 94, 84, a_res))
                if c4.get('address_line2'):
                    draw_centered(draw, c4['address_line2'], 1045, fonts['georgia_36'], (44, 94, 84, a_res))

    # Scene 5 (Haldi: frames 780..935)
    elif 780 <= frame_idx < 935:
        c5 = config['scene_5_haldi']
        a5 = int(min(1.0, max(0.0, (frame_idx - 780) / 25.0)) * 255)
        draw_centered(draw, c5['header'], 310, fonts['georgia_38'], (255, 255, 255, a5))
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
        draw_centered(draw, c6.get('header', 'You are invited to be a part of'), 520, fonts['georgia_36'], (34, 56, 40, a6))
        if c6.get('title_line2'):
            draw_centered(draw, c6['title_line1'], 640, fonts['greatvibes_110'], (46, 90, 54, a6))
            draw_centered(draw, c6['title_line2'], 750, fonts['greatvibes_110'], (46, 90, 54, a6))
            draw_centered(draw, c6.get('of_text', 'of'), 845, fonts['georgia_italic_40'], (34, 56, 40, a6))
            draw_centered(draw, c6.get('bride_name', ''), 935, fonts['greatvibes_110'], (46, 90, 54, a6))
        else:
            draw_centered(draw, c6.get('title_line1', 'Mehandi Ceremony'), 680, fonts['greatvibes_120'], (46, 90, 54, a6))
            draw_centered(draw, c6.get('of_text', 'of'), 790, fonts['georgia_italic_40'], (34, 56, 40, a6))
            draw_centered(draw, c6.get('bride_name', ''), 890, fonts['greatvibes_110'], (46, 90, 54, a6))
        draw_centered(draw, c6.get('on_text', 'on'), 980 if not c6.get('title_line2') else 1020, fonts['georgia_italic_40'], (34, 56, 40, a6))
        draw_centered(draw, c6.get('date', ''), 1070 if not c6.get('title_line2') else 1100, fonts['alex_80'], (46, 90, 54, a6))
        draw_centered(draw, c6.get('time', ''), 1170 if not c6.get('title_line2') else 1200, fonts['georgia_bold_italic_42'], (34, 56, 40, a6))
        draw_centered(draw, c6.get('venue_name', ''), 1270 if not c6.get('title_line2') else 1310, fonts['georgia_bold_italic_42'], (34, 56, 40, a6))
        if c6.get('address_line1'):
            draw_centered(draw, c6['address_line1'], 1335 if not c6.get('title_line2') else 1365, fonts['georgia_38'], (34, 56, 40, a6))
        if c6.get('address_line2'):
            draw_centered(draw, c6['address_line2'], 1385 if not c6.get('title_line2') else 1415, fonts['georgia_38'], (34, 56, 40, a6))

    # Scene 7 (Sangeet: frames 1115..1230)
    elif 1115 <= frame_idx < 1230:
        c7 = config['scene_7_sangeet']
        a7 = int(min(1.0, max(0.0, (frame_idx - 1115) / 25.0)) * 255)
        draw_centered(draw, c7.get('header_line1', ''), 510, fonts['cinzel_38'], (255, 255, 255, a7))
        draw_centered(draw, c7.get('header_line2', ''), 560, fonts['cinzel_38'], (255, 255, 255, a7))
        draw_centered(draw, c7.get('event_name_hindi', 'संगीत'), 735, fonts['rozha_140'], (30, 15, 20, int(a7 * 0.4)))
        draw_centered(draw, c7.get('event_name_hindi', 'संगीत'), 730, fonts['rozha_140'], (248, 202, 63, a7))
        draw_centered(draw, c7.get('sub_header', ''), 915, fonts['cinzel_36'], (255, 255, 255, a7))
        draw_centered(draw, c7.get('bride_name', ''), 1020, fonts['greatvibes_120'], (248, 202, 63, a7))
        draw_centered(draw, c7.get('date', ''), 1150, fonts['cinzel_36'], (255, 255, 255, a7))
        draw_centered(draw, c7.get('venue_label', ''), 1220, fonts['cinzel_36'], (255, 255, 255, a7))
        draw_centered(draw, c7.get('venue_name', ''), 1275, fonts['cinzel_34'], (255, 255, 255, a7))

    # Scene 8 (Mandha Ceremony: frames 1270..1425)
    elif 1270 <= frame_idx < 1425:
        c8 = config.get('scene_8_mandha') or config.get('scene_8_wedding', {})
        a8 = int(min(1.0, max(0.0, (frame_idx - 1270) / 25.0)) * 255)
        green = (43, 68, 42, a8)
        red = (164, 30, 86, a8)
        draw_centered(draw, c8.get('title', 'Mandha Ceremony'), 500, fonts['greatvibes_120'], red, stroke_rgba=(255, 255, 255, a8), stroke_width=2)
        if c8.get('on_text'):
            draw_centered(draw, c8['on_text'], 600, fonts['georgia_italic_40'], green)
        draw_centered(draw, c8.get('date', 'Monday, 21 September 2026'), 670, fonts['georgia_bold_38'], green)
        draw_ornament_divider(draw, 730, green)
        draw_centered(draw, c8.get('time', 'Lunch 11:30 AM'), 790, fonts['georgia_bold_italic_46'], green)
        draw_ornament_divider(draw, 850, green)
        draw_centered(draw, c8.get('venue_label', 'Venue:'), 910, fonts['greatvibes_95'], red, stroke_rgba=(255, 255, 255, a8), stroke_width=1)
        draw_centered(draw, c8.get('venue_name', 'Kali Mata Mandir Auditorium'), 990, fonts['georgia_bold_italic_46'], green, max_width=920)
        addr = c8.get('address') or c8.get('address_line1') or ''
        if addr:
            draw_centered(draw, addr, 1055, fonts['georgia_36'], green, max_width=920)

    # Scene 9 (Wedding Ceremony: frames 1464..1619)
    elif 1464 <= frame_idx < 1619:
        c9 = config.get('scene_9_wedding') or config.get('scene_8_wedding', {})
        a9 = int(min(1.0, max(0.0, (frame_idx - 1464) / 25.0)) * 255)
        green = (43, 68, 42, a9)
        red = (164, 30, 86, a9)
        draw_centered(draw, c9.get('title', 'Wedding Ceremony'), 500, fonts['greatvibes_120'], red, stroke_rgba=(255, 255, 255, a9), stroke_width=2)
        if c9.get('on_text'):
            draw_centered(draw, c9['on_text'], 600, fonts['georgia_italic_40'], green)
        draw_centered(draw, c9.get('date', 'Monday, 21 September 2026'), 670, fonts['georgia_bold_38'], green)
        draw_ornament_divider(draw, 730, green)
        draw_centered(draw, c9.get('time', '7:00 PM Onwards'), 790, fonts['georgia_bold_italic_46'], green)
        draw_ornament_divider(draw, 850, green)
        draw_centered(draw, c9.get('venue_label', 'Venue:'), 910, fonts['greatvibes_95'], red, stroke_rgba=(255, 255, 255, a9), stroke_width=1)
        draw_centered(draw, c9.get('venue_name', 'The Divine'), 990, fonts['georgia_bold_italic_46'], green, max_width=920)
        addr = c9.get('address') or c9.get('address_line1') or ''
        if addr:
            draw_centered(draw, addr, 1055, fonts['georgia_36'], green, max_width=920)

    # Scene 10 (Save the Date + RSVP: frames 1649..1755)
    elif 1649 <= frame_idx < 1755:
        c10 = config.get('scene_10_closing') or config.get('scene_9_closing', {})
        a10 = int(min(1.0, max(0.0, (frame_idx - 1649) / 25.0)) * 255)
        blue = (19, 75, 142, a10)
        maroon = (164, 30, 86, a10)
        green = (43, 68, 42, a10)
        draw_centered(draw, c10.get('title', 'Save The Date'), 550, fonts['greatvibes_130'], blue)
        draw_centered(draw, c10.get('date', '21st September 2026'), 680, fonts['georgia_bold_52'], blue)
        draw_ornament_divider(draw, 755, blue)
        if c10.get('rsvp_label') or c10.get('rsvp_text'):
            draw_centered(draw, c10.get('rsvp_label', 'RSVP'), 825, fonts['cinzel_38'], maroon)
            draw_centered(draw, c10.get('rsvp_text', 'From Mittal Family & Friends'), 900, fonts['greatvibes_95'], green, max_width=860)

    base_pil = Image.fromarray(cv2.cvtColor(base_bgr, cv2.COLOR_BGR2RGB))
    base_pil.paste(overlay, (0, 0), overlay)
    return cv2.cvtColor(np.array(base_pil), cv2.COLOR_RGB2BGR)

# Parallel worker
def render_worker(task):
    part_id, start_frame, end_frame, config_path, clean_video_path = task
    with open(config_path) as f:
        cfg = json.load(f)
    fonts = load_fonts()

    shloka_img = None
    shloka_png = os.path.join(SCRIPT_DIR, 'tmp_render', 'shloka.png')
    if os.path.exists(shloka_png):
        try:
            shloka_img = Image.open(shloka_png).convert('RGBA')
        except Exception:
            shloka_img = None

    cap = cv2.VideoCapture(clean_video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    fps = cap.get(cv2.CAP_PROP_FPS)

    os.makedirs(os.path.join(SCRIPT_DIR, 'tmp_render'), exist_ok=True)
    part_file = os.path.join(SCRIPT_DIR, 'tmp_render', f'part_{part_id:02d}.mp4')
    out = cv2.VideoWriter(part_file, cv2.VideoWriter_fourcc(*'mp4v'), fps, (1080, 1920))

    for idx in range(start_frame, end_frame):
        ret, frame = cap.read()
        if not ret:
            break
        rendered = render_frame_text(frame, idx, cfg, fonts, shloka_img=shloka_img)
        out.write(rendered)

    out.release()
    cap.release()
    return part_file

def main():
    parser = argparse.ArgumentParser(description="Render customizable wedding invitation video.")
    parser.add_argument('--config', default='video_text.json', help='Path to configuration JSON file')
    parser.add_argument('--output', default='custom_invitation.mp4', help='Output video file path')
    parser.add_argument('--clean-video', default='clean_base.mp4', help='Clean background video path')
    parser.add_argument('--template', help='Path to template.json file')
    args = parser.parse_args()

    clean_video = args.clean_video if os.path.isabs(args.clean_video) else os.path.join(SCRIPT_DIR, args.clean_video)
    config_file = args.config if os.path.isabs(args.config) else os.path.join(SCRIPT_DIR, args.config)
    output_file = args.output if os.path.isabs(args.output) else os.path.join(SCRIPT_DIR, args.output)

    if args.template:
        template_file = args.template if os.path.isabs(args.template) else os.path.join(SCRIPT_DIR, args.template)
        with open(template_file, 'r', encoding='utf-8') as f:
            t_data = json.load(f)
        cfg = template_to_wedding_config(t_data)
        config_file = os.path.join(SCRIPT_DIR, 'tmp_render', 'active_wedding_config.json')
        os.makedirs(os.path.join(SCRIPT_DIR, 'tmp_render'), exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    if not os.path.exists(clean_video):
        print(f"Error: Base video '{clean_video}' not found!", flush=True)
        sys.exit(1)
    if not os.path.exists(config_file):
        print(f"Error: Config file '{config_file}' not found!", flush=True)
        sys.exit(1)

    t0 = time.time()
    print(f"=== Rendering Wedding Invitation Video ===", flush=True)
    print(f"Config: {config_file}", flush=True)
    print(f"Output: {output_file}", flush=True)
    print("[PROGRESS] 10", flush=True)

    os.makedirs(os.path.join(SCRIPT_DIR, 'tmp_render'), exist_ok=True)
    with open(config_file, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    shloka_text = cfg.get('scene_4_invitation', {}).get('shloka', '')
    get_shloka_image(shloka_text)
    print("[PROGRESS] 25", flush=True)

    cap = cv2.VideoCapture(clean_video)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()

    num_workers = min(8, mp.cpu_count() or 4)
    chunk_size = (total_frames + num_workers - 1) // num_workers

    tasks = []
    for i in range(num_workers):
        s = i * chunk_size
        e = min((i + 1) * chunk_size, total_frames)
        if s < total_frames:
            tasks.append((i, s, e, config_file, clean_video))

    print(f"[*] Rendering {total_frames} frames across {len(tasks)} parallel workers...", flush=True)
    print("[PROGRESS] 40", flush=True)
    with mp.Pool(len(tasks)) as pool:
        part_files = pool.map(render_worker, tasks)

    print("[PROGRESS] 82", flush=True)
    print("Frames rendered! Assembling final MP4 with audio...", flush=True)
    concat_list = os.path.join(SCRIPT_DIR, 'tmp_render', 'concat_list.txt')
    with open(concat_list, 'w') as f:
        for p in part_files:
            f.write(f"file '{os.path.abspath(p)}'\n")

    print("[PROGRESS] 88", flush=True)
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0',
        '-i', concat_list,
        '-i', clean_video,
        '-map', '0:v:0',
        '-map', '1:a:0?',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-preset', 'veryfast',
        '-crf', '18',
        '-c:a', 'copy',
        output_file
    ]
    subprocess.run(cmd, check=True)
    print("[PROGRESS] 98", flush=True)

    # Clean up temp parts
    for p in part_files:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    if os.path.exists(concat_list):
        try:
            os.remove(concat_list)
        except Exception:
            pass

    elapsed = time.time() - t0
    print(f"\nSUCCESS! Video saved to '{output_file}' in {elapsed:.2f} seconds.", flush=True)
    print("[PROGRESS] 100", flush=True)

# -------------------------------------------------------------
# Web Studio Integration
# -------------------------------------------------------------
CACHED_FONTS = None

def get_cached_fonts():
    global CACHED_FONTS
    if CACHED_FONTS is None:
        CACHED_FONTS = load_fonts()
    return CACHED_FONTS

def template_to_wedding_config(template_data):
    cfg_file = os.path.join(SCRIPT_DIR, 'video_text.json')
    if os.path.exists(cfg_file):
        with open(cfg_file, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    else:
        cfg = {}

    if not template_data or not template_data.get('scenes'):
        return cfg

    field_map = {}
    for sc in template_data.get('scenes', []):
        for f in sc.get('fields', []):
            field_map[f['id']] = f.get('value', '')

    if 's2_initials' in field_map:
        cfg.setdefault('scene_2_monogram', {})['initials'] = field_map['s2_initials']

    if 's3_names' in field_map:
        s3 = cfg.setdefault('scene_3_announcement', {})
        s3['monogram'] = field_map.get('s3_monogram', s3.get('monogram', 'SM'))
        s3['couple_names'] = field_map['s3_names']
        s3['subtext'] = field_map.get('s3_subtext', s3.get('subtext', 'are getting married on ..'))
        s3['date'] = field_map.get('s3_date', s3.get('date', '21st September 2026'))

    if 's4_bride' in field_map or 's4_groom' in field_map:
        s4 = cfg.setdefault('scene_4_invitation', {})
        if 's4_shloka' in field_map: s4['shloka'] = field_map['s4_shloka']
        if 's4_header1' in field_map: s4['header_line1'] = field_map['s4_header1']
        if 's4_header2' in field_map: s4['header_line2'] = field_map['s4_header2']
        if 's4_bride' in field_map: s4['bride_name'] = field_map['s4_bride']
        if 's4_bride_parents_rel' in field_map: s4['bride_parents_relation'] = field_map['s4_bride_parents_rel']
        if 's4_bride_parents1' in field_map: s4['bride_parents_line1'] = field_map['s4_bride_parents1']
        if 's4_bride_parents2' in field_map: s4['bride_parents_line2'] = field_map['s4_bride_parents2']
        if 's4_with' in field_map: s4['conjunction'] = field_map['s4_with']
        if 's4_groom' in field_map: s4['groom_name'] = field_map['s4_groom']
        if 's4_groom_parents_rel' in field_map: s4['groom_parents_relation'] = field_map['s4_groom_parents_rel']
        if 's4_groom_parents1' in field_map: s4['groom_parents_line1'] = field_map['s4_groom_parents1']
        if 's4_groom_parents2' in field_map: s4['groom_parents_line2'] = field_map['s4_groom_parents2']
        if 's4_res_label' in field_map: s4['residence_label'] = field_map['s4_res_label']
        if 's4_addr1' in field_map: s4['address_line1'] = field_map['s4_addr1']
        if 's4_addr2' in field_map: s4['address_line2'] = field_map['s4_addr2']

    if 's5_title' in field_map or 's5_date' in field_map:
        s5 = cfg.setdefault('scene_5_haldi', {})
        if 's5_header' in field_map: s5['header'] = field_map['s5_header']
        if 's5_title' in field_map: s5['title'] = field_map['s5_title']
        if 's5_date' in field_map: s5['date'] = field_map['s5_date']
        if 's5_time' in field_map: s5['time'] = field_map['s5_time']
        if 's5_venue_label' in field_map: s5['venue_label'] = field_map['s5_venue_label']
        if 's5_venue_name' in field_map: s5['venue_name'] = field_map['s5_venue_name']
        if 's5_addr1' in field_map: s5['address_line1'] = field_map['s5_addr1']
        if 's5_addr2' in field_map: s5['address_line2'] = field_map['s5_addr2']

    if 's6_bride' in field_map or 's6_date' in field_map:
        s6 = cfg.setdefault('scene_6_mehendi', {})
        if 's6_header' in field_map: s6['header'] = field_map['s6_header']
        if 's6_title' in field_map: s6['title_line1'] = field_map['s6_title']
        if 's6_bride' in field_map: s6['bride_name'] = field_map['s6_bride']
        if 's6_date' in field_map: s6['date'] = field_map['s6_date']
        if 's6_time' in field_map: s6['time'] = field_map['s6_time']
        if 's6_venue' in field_map: s6['venue_name'] = field_map['s6_venue']
        if 's6_addr1' in field_map: s6['address_line1'] = field_map['s6_addr1']
        if 's6_addr2' in field_map: s6['address_line2'] = field_map['s6_addr2']

    if 's7_hindi' in field_map or 's7_date_time' in field_map:
        s7 = cfg.setdefault('scene_7_sangeet', {})
        if 's7_header1' in field_map: s7['header_line1'] = field_map['s7_header1']
        if 's7_header2' in field_map: s7['header_line2'] = field_map['s7_header2']
        if 's7_hindi' in field_map: s7['event_name_hindi'] = field_map['s7_hindi']
        if 's7_sub' in field_map: s7['sub_header'] = field_map['s7_sub']
        if 's7_bride' in field_map: s7['bride_name'] = field_map['s7_bride']
        if 's7_date_time' in field_map: s7['date'] = field_map['s7_date_time']
        if 's7_venue1' in field_map: s7['venue_label'] = field_map['s7_venue1']
        if 's7_venue2' in field_map: s7['venue_name'] = field_map['s7_venue2']

    if 's8_mandha_title' in field_map or 's8_wedding_title' in field_map:
        s8 = cfg.setdefault('scene_8_mandha', {})
        if 's8_mandha_title' in field_map: s8['title'] = field_map['s8_mandha_title']
        if 's8_date_header' in field_map: s8['date'] = field_map['s8_date_header']
        if 's8_mandha_time' in field_map: s8['time'] = field_map['s8_mandha_time']
        if 's8_mandha_v1' in field_map: s8['venue_name'] = field_map['s8_mandha_v1']
        if 's8_mandha_v2' in field_map: s8['address'] = field_map['s8_mandha_v2']

        s9 = cfg.setdefault('scene_9_wedding', {})
        if 's8_wedding_title' in field_map: s9['title'] = field_map['s8_wedding_title']
        if 's9_wedding_date' in field_map: s9['date'] = field_map['s9_wedding_date']
        elif 's8_date_header' in field_map: s9['date'] = field_map['s8_date_header']
        if 's8_wedding_time' in field_map: s9['time'] = field_map['s8_wedding_time']
        if 's8_wedding_v1' in field_map: s9['venue_name'] = field_map['s8_wedding_v1']
        if 's8_wedding_v2' in field_map: s9['address'] = field_map['s8_wedding_v2']

    if 's9_title' in field_map or 's9_date' in field_map or 's10_rsvp_label' in field_map:
        s10 = cfg.setdefault('scene_10_closing', {})
        if 's9_title' in field_map: s10['title'] = field_map['s9_title']
        if 's9_date' in field_map: s10['date'] = field_map['s9_date']
        if 's10_rsvp_label' in field_map: s10['rsvp_label'] = field_map['s10_rsvp_label']
        if 's10_rsvp_text' in field_map: s10['rsvp_text'] = field_map['s10_rsvp_text']

    return cfg

_CURRENT_SHLOKA = None

def get_shloka_image(shloka_text):
    global _CURRENT_SHLOKA
    if not shloka_text:
        return None
    shloka_png = os.path.join(SCRIPT_DIR, 'tmp_render', 'shloka.png')
    render_text_bin = os.path.join(SCRIPT_DIR, 'bin', 'render_text')
    if os.path.exists(render_text_bin):
        if _CURRENT_SHLOKA != shloka_text or not os.path.exists(shloka_png):
            os.makedirs(os.path.join(SCRIPT_DIR, 'tmp_render'), exist_ok=True)
            try:
                subprocess.run([
                    render_text_bin,
                    shloka_text,
                    'Rozha One',
                    '42',
                    '214,123,39',
                    shloka_png
                ], check=True, timeout=3)
                _CURRENT_SHLOKA = shloka_text
            except Exception:
                pass
    if os.path.exists(shloka_png):
        try:
            return Image.open(shloka_png).convert('RGBA')
        except Exception:
            return None
    return None

def render_wedding_frame(base_bgr, frame_idx, template_data):
    cfg = template_to_wedding_config(template_data)
    fonts = get_cached_fonts()
    shloka_text = cfg.get('scene_4_invitation', {}).get('shloka', '')
    shloka_img = get_shloka_image(shloka_text)
    return render_frame_text(base_bgr, frame_idx, cfg, fonts, shloka_img=shloka_img)

def render_wedding_video_from_template(template_data, clean_video, output_file, num_workers=None):
    if num_workers is None:
        num_workers = min(8, mp.cpu_count() or 4)

    cfg = template_to_wedding_config(template_data)
    tmp_config_path = os.path.join(SCRIPT_DIR, 'tmp_render', 'active_wedding_config.json')
    os.makedirs(os.path.join(SCRIPT_DIR, 'tmp_render'), exist_ok=True)
    with open(tmp_config_path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def render_wedding_video_from_template(template_data, clean_video, output_file, num_workers=None, progress_callback=None):
    cfg = template_to_wedding_config(template_data)
    tmp_config_path = os.path.join(SCRIPT_DIR, 'tmp_render', 'active_wedding_config.json')
    os.makedirs(os.path.join(SCRIPT_DIR, 'tmp_render'), exist_ok=True)
    with open(tmp_config_path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    cmd = [
        sys.executable,
        os.path.join(SCRIPT_DIR, 'render_video.py'),
        '--config', tmp_config_path,
        '--clean-video', clean_video,
        '--output', output_file
    ]

    print(f"[*] Dispatching standalone multi-core render subprocess: {' '.join(cmd)}", flush=True)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in proc.stdout:
        line_str = line.strip()
        print(f"[RENDER_LOG] {line_str}", flush=True)
        if "[PROGRESS]" in line_str and progress_callback:
            try:
                pct = int(line_str.split("[PROGRESS]")[1].strip())
                progress_callback(pct)
            except Exception:
                pass

    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"render_video.py subprocess failed with exit code {proc.returncode}")
    return output_file

if __name__ == '__main__':
    main()
