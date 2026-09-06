import os
import re
import json
import base64
import random
import urllib.parse

import requests
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

import renderer

app = Flask(__name__)

MODEL_PREFERENCE = [
    "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash",
    "gemini-2.0-flash-exp", "gemini-1.5-flash-latest", "gemini-1.5-pro-latest",
]
POLLINATIONS_TOKEN = os.environ.get("POLLINATIONS_TOKEN", "").strip()

ANALYZER_INSTRUCTION = """Bạn là chuyên gia thiết kế hình minh họa sách giáo khoa Toán Việt Nam.
Đọc đề toán (chữ hoặc ảnh) rồi mô tả cảnh minh họa. Chỉ trả về DUY NHẤT một object JSON hợp lệ:

{
  "topic": "chủ đề ngắn gọn",
  "figures": [
    {"type": "box", "label": "Bể nước hình hộp chữ nhật",
     "dims": {"length": "3m", "width": "2m", "height": "2m"}},
    {"type": "cylinder", "label": "Gáo hình trụ",
     "dims": {"radius": "r = 10cm", "height": "h = 15cm"}}
  ],
  "character": {"enabled": true, "caption": "Bạn Đạt"},
  "badge": {"text": "× 30", "caption": "30 gáo/ngày"},
  "note": "π ≈ 3,14",
  "question": "SỐ NGÀY = ?"
}

QUY TẮC:
1. "type" chỉ được chọn trong: box, cube, cylinder, cone, sphere, pyramid, prism, rectangle, square, circle.
2. "dims" chỉ dùng các khoá: length, width, height, radius, diameter, base. Giá trị là chuỗi hiển thị,
   giữ nguyên số và đơn vị như trong đề (ví dụ "3m", "15cm", "r = 10cm"). Không bịa số, không đổi đơn vị.
3. figures[0] là khối hình lớn nhất của đề. figures[1] (nếu có) là vật thể nhỏ đi kèm, sẽ được vẽ phóng to
   trong khung tròn. Tối đa 2 phần tử.
4. "character": bật khi đề có nhân vật thao tác (múc nước, xếp gạch, đổ cát...). "caption" là tên nhân vật
   trong đề, ví dụ "Bạn Đạt". Nếu đề không có người, đặt enabled = false.
5. "badge": chỉ dùng khi đề có số lần lặp lại. "text" viết dạng "× 30", "caption" là chú thích ngắn.
   Không có thì bỏ trống.
6. "note": hằng số hoặc lưu ý của đề, ví dụ "π ≈ 3,14". Không có thì để null.
7. "question": câu hỏi rút gọn tối đa 4 chữ, VIẾT HOA, kết thúc bằng "= ?".
8. Toàn bộ chữ hiển thị viết bằng tiếng Việt có dấu."""

DIM_TO_SLOT_MAIN = {"length": "main_length", "width": "main_width",
                    "height": "main_height", "radius": "main_extra", "diameter": "main_extra"}
DIM_TO_SLOT_SUB = {"radius": "sub_radius", "diameter": "sub_radius",
                   "height": "sub_height", "length": "sub_extra"}


REVISE_INSTRUCTION = """Bạn đang chỉnh sửa spec JSON của một hình minh họa Toán.
Người dùng là giáo viên, họ sẽ mô tả bằng tiếng Việt điều cần sửa.

Trả về DUY NHẤT spec JSON hoàn chỉnh sau khi sửa, giữ nguyên mọi trường không liên quan đến yêu cầu.

Ngoài các trường sẵn có (topic, figures, character, badge, note, question), spec còn khoá "style":
{
  "theme": "yard" | "classroom" | "blank",   // sân vườn / lớp học / nền giấy kẻ ô để in
  "palette": "color" | "print",              // in màu / in đen trắng
  "angle": số từ 12 đến 50,                  // độ nghiêng góc nhìn, mặc định 30
  "mirror": true | false,                    // đổi khối hình sang bên kia
  "decor": true | false,                     // bật tắt cây cối trang trí
  "character": "boy" | "girl"
}

Ví dụ cách hiểu yêu cầu:
- "bỏ cây cối cho gọn" -> style.decor = false
- "cho in đen trắng" -> style.palette = "print", style.theme = "blank"
- "đổi thành bạn nữ" -> style.character = "girl"
- "nhìn từ góc thấp hơn" -> style.angle = 20
- "chuyển bể sang phải" -> style.mirror = true
- "chiều cao phải là 1,5m" -> sửa figures[0].dims.height = "1,5m"
- "bỏ nhân vật đi" -> character.enabled = false

Không bịa thêm số đo mà giáo viên không nói. Không thêm lời giải thích ngoài JSON."""


def resolve_key(payload):
    return (payload.get("api_key") or "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()


def parse_data_url(data_url):
    match = re.match(r"^data:(?P<mime>[\w/\-\.\+]+);base64,(?P<data>.+)$", data_url, re.S)
    if match:
        return match.group("mime"), base64.b64decode(match.group("data"))
    return "image/png", base64.b64decode(data_url)


def extract_json(raw):
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    start, depth = cleaned.find("{"), 0
    if start == -1:
        raise ValueError("Model không trả về JSON hợp lệ.")
    for i in range(start, len(cleaned)):
        if cleaned[i] == "{":
            depth += 1
        elif cleaned[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(cleaned[start:i + 1])
    raise ValueError("JSON bị cắt giữa chừng.")


def pick_model(requested):
    if requested:
        return requested
    try:
        available = {m.name.replace("models/", "") for m in genai.list_models()
                     if "generateContent" in m.supported_generation_methods}
        for candidate in MODEL_PREFERENCE:
            if candidate in available:
                return candidate
    except Exception:
        pass
    return "gemini-2.0-flash"


def analyze(payload):
    """Gọi Gemini để chuyển đề toán thành spec hình vẽ."""
    genai.configure(api_key=resolve_key(payload))
    model_name = pick_model((payload.get("model") or "").strip())
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=ANALYZER_INSTRUCTION,
        generation_config={"temperature": 0.2, "response_mime_type": "application/json"},
    )

    contents = []
    text = (payload.get("text") or "").strip()
    if text:
        contents.append("Đề bài:\n" + text)
    if payload.get("image_base64"):
        mime, blob = parse_data_url(payload["image_base64"])
        contents.append({"mime_type": mime, "data": blob})
    if not text:
        contents.append("Đọc đề trong ảnh rồi trả về spec JSON.")

    return extract_json(model.generate_content(contents).text), model_name


# --- nhánh ảnh AI (tuỳ chọn) ------------------------------------------------

SHAPE_WORDS = {"box": "rectangular prism tank", "cube": "cube", "cylinder": "cylinder",
               "cone": "cone", "sphere": "sphere", "pyramid": "square pyramid",
               "prism": "triangular prism", "rectangle": "flat rectangle",
               "square": "flat square", "circle": "flat circle"}


def ai_prompt(spec):
    figures = spec.get("figures") or [{}]
    main = figures[0]
    sub = figures[1] if len(figures) > 1 else None
    parts = [
        "Vietnamese primary school textbook math illustration, clean 2D technical line art, "
        "flat cartoon vector colors, soft pastel palette, isometric perspective, educational infographic layout.",
        f"LEFT HALF: one large transparent {SHAPE_WORDS.get(main.get('type'), 'geometric solid')} "
        f"resting on the ground, with plain dimension arrows along its edges.",
    ]
    if (spec.get("character") or {}).get("enabled", True):
        parts.append("RIGHT HALF: a cheerful Vietnamese schoolboy standing on the ground entirely "
                     "outside the solid, full body visible, correct proportions.")
    if sub:
        parts.append(f"A small {SHAPE_WORDS.get(sub.get('type'), 'object')} in his hand, plus a round "
                     f"magnifier callout in the top right corner showing that object in cutaway view.")
    parts.append("Sunny garden yard background with potted plants.")
    parts.append("CRITICAL: absolutely no text, no letters, no numbers, no watermark anywhere; "
                 "leave clean empty space around every arrow.")
    return " ".join(parts)[:1800]


def ai_annotations(spec):
    """Chuyển spec thành các nhãn số đo để dán đè lên ảnh AI."""
    figures = spec.get("figures") or []
    out, used = [], set()

    def push(slot, text):
        if slot and text and slot not in used:
            used.add(slot)
            out.append({"slot": slot, "text": str(text)})

    if figures:
        for key, value in (figures[0].get("dims") or {}).items():
            push(DIM_TO_SLOT_MAIN.get(key), value)
    if len(figures) > 1:
        for key, value in (figures[1].get("dims") or {}).items():
            push(DIM_TO_SLOT_SUB.get(key), value)
    badge = spec.get("badge") or {}
    push("badge", badge.get("text"))
    push("badge_caption", badge.get("caption"))
    push("note", spec.get("note"))
    push("banner", spec.get("question"))
    return out


def ai_image_url(prompt, seed):
    params = {"width": 1280, "height": 720, "model": "flux", "seed": seed,
              "nologo": "true", "enhance": "false", "private": "true"}
    if POLLINATIONS_TOKEN:
        params["token"] = POLLINATIONS_TOKEN
    return ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt, safe="")
            + "?" + urllib.parse.urlencode(params))


# --- routes -----------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", has_server_key=bool(os.environ.get("GEMINI_API_KEY")))


@app.route("/api/scan-models", methods=["POST"])
def scan_models():
    payload = request.get_json(silent=True) or {}
    if not resolve_key(payload):
        return jsonify({"error": "Chưa có API Key. Nhập key hoặc đặt biến môi trường GEMINI_API_KEY."}), 400
    try:
        genai.configure(api_key=resolve_key(payload))
        models = sorted(m.name.replace("models/", "") for m in genai.list_models()
                        if "generateContent" in m.supported_generation_methods)
        models.sort(key=lambda n: (MODEL_PREFERENCE.index(n) if n in MODEL_PREFERENCE else 99, n))
        return jsonify({"models": models})
    except Exception as exc:
        return jsonify({"error": f"Không kết nối được tới Gemini: {exc}"}), 403


@app.route("/api/generate", methods=["POST"])
def generate():
    payload = request.get_json(silent=True) or {}
    if not (payload.get("text") or "").strip() and not payload.get("image_base64"):
        return jsonify({"error": "Nhập nội dung bài toán hoặc tải ảnh đề lên trước đã."}), 400
    if not resolve_key(payload):
        return jsonify({"error": "Chưa có API Key. Nhập key hoặc đặt biến môi trường GEMINI_API_KEY."}), 400

    try:
        spec, model_name = analyze(payload)
    except Exception as exc:
        print("LỖI PHÂN TÍCH ĐỀ:", exc)
        return jsonify({"error": f"Không đọc được đề: {exc}"}), 500

    result = {"spec": spec, "model_used": model_name, "topic": spec.get("topic", "")}

    if payload.get("mode") == "ai":
        seed = payload.get("seed") or random.randint(1, 10_000_000)
        prompt = ai_prompt(spec)
        result.update({"mode": "ai", "prompt": prompt, "seed": seed,
                       "image_url": ai_image_url(prompt, seed),
                       "annotations": ai_annotations(spec)})
    else:
        try:
            result.update({"mode": "svg", "svg": renderer.render_scene(spec)})
        except Exception as exc:
            print("LỖI DỰNG HÌNH:", exc)
            return jsonify({"error": f"Không dựng được hình: {exc}"}), 500

    return jsonify(result)


@app.route("/api/rerender", methods=["POST"])
def rerender():
    """Vẽ lại từ spec đã có: đổi biến thể trình bày hoặc sửa số đo. Không gọi Gemini."""
    payload = request.get_json(silent=True) or {}
    spec = payload.get("spec") or {}

    if payload.get("variant_index") is not None:
        spec["style"] = renderer.variant(int(payload["variant_index"]))
    if payload.get("style_override"):
        spec["style"] = {**(spec.get("style") or {}), **payload["style_override"]}

    try:
        return jsonify({"svg": renderer.render_scene(spec), "spec": spec,
                        "variant_count": len(renderer.VARIANTS)})
    except Exception as exc:
        return jsonify({"error": f"Spec không hợp lệ: {exc}"}), 400


@app.route("/api/revise", methods=["POST"])
def revise():
    """Giáo viên mô tả bằng lời điều cần sửa, Gemini cập nhật spec rồi vẽ lại."""
    payload = request.get_json(silent=True) or {}
    instruction = (payload.get("instruction") or "").strip()
    spec = payload.get("spec")

    if not instruction:
        return jsonify({"error": "Hãy mô tả điều bạn muốn sửa, ví dụ: bỏ cây cối, đổi sang bạn nữ."}), 400
    if not spec:
        return jsonify({"error": "Chưa có hình nào để sửa. Tạo hình trước đã."}), 400
    if not resolve_key(payload):
        return jsonify({"error": "Chưa có API Key. Nhập key hoặc đặt biến môi trường GEMINI_API_KEY."}), 400

    try:
        genai.configure(api_key=resolve_key(payload))
        model = genai.GenerativeModel(
            model_name=pick_model((payload.get("model") or "").strip()),
            system_instruction=REVISE_INSTRUCTION,
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"},
        )
        prompt = ("Spec hiện tại:\n" + json.dumps(spec, ensure_ascii=False)
                  + "\n\nYêu cầu của giáo viên:\n" + instruction)
        new_spec = extract_json(model.generate_content(prompt).text)
        return jsonify({"svg": renderer.render_scene(new_spec), "spec": new_spec})
    except Exception as exc:
        print("LỖI SỬA HÌNH:", exc)
        return jsonify({"error": f"Không sửa được: {exc}"}), 500


@app.route("/api/proxy-image", methods=["POST"])
def proxy_image():
    url = (request.get_json(silent=True) or {}).get("url", "")
    if not url.startswith("https://image.pollinations.ai/"):
        return jsonify({"error": "Đường dẫn ảnh không hợp lệ."}), 400
    try:
        resp = requests.get(url, timeout=180)
        resp.raise_for_status()
        mime = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
        return jsonify({"data_url": f"data:{mime};base64,{base64.b64encode(resp.content).decode()}"})
    except Exception as exc:
        return jsonify({"error": f"Không tải được ảnh: {exc}"}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
