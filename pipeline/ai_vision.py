import os
import sys
import json
import re
import base64
import urllib.request
import urllib.error

NVIDIA_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_MODEL = "meta/llama-3.2-11b-vision-instruct"

def load_nvidia_api_key():
    """Load NVIDIA API key from environment or .env file."""
    key = os.environ.get("NVIDIA_API_KEY")
    if key:
        return key.strip()
    
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(script_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("NVIDIA_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None

def sanitize_json_string(s):
    r"""
    Sanitize raw model JSON string by converting \u{XXXX} to actual unicode characters
    and escaping invalid backslashes.
    """
    # Replace \u{XXXX} with actual unicode character
    s = re.sub(r'\\u\{([0-9a-fA-F]+)\}', lambda m: chr(int(m.group(1), 16)), s)
    # Fix solitary backslashes that are not standard JSON escapes
    s = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', s)
    return s

def parse_ai_response(raw_text):
    """
    Robustly parse extracted text elements from model output.
    Handles pure JSON, markdown JSON, and structured bullet lists.
    """
    cleaned_text = sanitize_json_string(raw_text)

    # 1. Try JSON array match
    match = re.search(r"\[\s*\{.*?\}\s*\]", cleaned_text, re.DOTALL)
    if match:
        try:
            items = json.loads(match.group(0))
            if isinstance(items, list) and len(items) > 0:
                res = []
                for it in items:
                    t = str(it.get("text", "")).strip()
                    if t:
                        res.append({
                            "text": t,
                            "role": str(it.get("role", "general")).lower(),
                            "align": str(it.get("align", "center")).lower(),
                            "y_percent": float(it.get("y_percent", 50.0))
                        })
                if res:
                    return res
        except Exception:
            pass

    # 2. Try structured bullet items
    items_map = {}
    detailed_blocks = re.findall(r'[\*\-]\s*["“]([^"”]+)["”](.*?)(?=\n\s*[\*\-]|\Z)', cleaned_text, re.DOTALL)
    for text, details in detailed_blocks:
        t = text.strip()
        if not t:
            continue
        role_m = re.search(r'Role:\s*([^\n\r]+)', details, re.IGNORECASE)
        align_m = re.search(r'Align(?:ment)?:\s*([^\n\r]+)', details, re.IGNORECASE)
        y_m = re.search(r'Y-Percent:\s*([0-9.]+)', details, re.IGNORECASE)

        role = role_m.group(1).strip().lower() if role_m else "general"
        align = align_m.group(1).strip().lower() if align_m else "center"
        y_percent = float(y_m.group(1)) if y_m else 50.0

        k = t.lower()
        if k not in items_map or (role != "general" and items_map[k]["role"] == "general"):
            items_map[k] = {
                "text": t,
                "role": role,
                "align": align,
                "y_percent": y_percent
            }

    if items_map:
        return list(items_map.values())

    return []

def extract_text_with_nim(image_path, model=DEFAULT_MODEL, timeout=45):
    """
    Extract text from an image keyframe using NVIDIA NIM vision model.
    Accurately extracts Hindi/Devanagari and English text, classifies semantic roles,
    and returns clean structured fields.
    """
    api_key = load_nvidia_api_key()
    if not api_key:
        print("[-] Warning: NVIDIA_API_KEY not found in environment or .env file")
        return []

    if not os.path.exists(image_path):
        print(f"[-] Image file not found: {image_path}")
        return []

    with open(image_path, "rb") as f:
        img_bytes = f.read()
    b64_img = base64.b64encode(img_bytes).decode("utf-8")

    prompt = (
        "Extract all distinct text elements visible in this video frame in reading order (top to bottom).\n"
        "For each text element, provide:\n"
        "- text: exact text string (crucial: accurately transcribe Hindi / Devanagari characters like हुआ, शुभ विवाह, and English)\n"
        "- role: one of: title, names, date, time, venue, hashtag, general\n"
        "- align: center, left, or right\n"
        "- y_percent: approximate vertical center position (0.0 to 100.0)\n\n"
        "Return strictly a JSON array of objects:\n"
        "[\n"
        "  {\"text\": \"You Are Invited To\", \"role\": \"title\", \"align\": \"center\", \"y_percent\": 25.0},\n"
        "  {\"text\": \"Mansi & Ankush\", \"role\": \"names\", \"align\": \"center\", \"y_percent\": 40.0},\n"
        "  {\"text\": \"#KhushहुआMan\", \"role\": \"hashtag\", \"align\": \"center\", \"y_percent\": 50.0}\n"
        "]\n"
        "Output ONLY the JSON array. Do not include markdown codeblocks or conversational text."
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a specialized JSON-only vision OCR and text extraction system. You output valid JSON arrays containing extracted text elements with exact transcription of English and Devanagari/Indic scripts. No conversational commentary."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                ]
            }
        ],
        "temperature": 0.05,
        "max_tokens": 1024
    }

    req = urllib.request.Request(
        NVIDIA_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_text = data["choices"][0]["message"]["content"].strip()
            return parse_ai_response(raw_text)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
        print(f"[-] NVIDIA NIM HTTP Error ({e.code}): {err_msg}")
    except Exception as e:
        print(f"[-] NVIDIA NIM error: {e}")

    return []

if __name__ == "__main__":
    test_img = sys.argv[1] if len(sys.argv) > 1 else "test_source_sc2.jpg"
    print(f"[*] Testing NVIDIA NIM text extraction on: {test_img}")
    results = extract_text_with_nim(test_img)
    print(f"[+] Extracted {len(results)} items:")
    for r in results:
        print(f"    - [{r['role']}] {r['text']} (y: {r['y_percent']}%, align: {r['align']})")
