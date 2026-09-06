import os
import urllib.parse
import base64
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan-models', methods=['POST'])
def scan_models():
    data = request.get_json()
    user_api_key = data.get('api_key')
    
    active_key = user_api_key if (user_api_key and user_api_key.strip() != "") else os.environ.get("GEMINI_API_KEY")

    if not active_key:
        return jsonify({"error": "Không tìm thấy API Key nào để kết nối!"}), 400

    try:
        genai.configure(api_key=active_key)
        
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                clean_name = m.name.replace('models/', '')
                available_models.append(clean_name)
                
        return jsonify({"models": available_models})
    except Exception as e:
        return jsonify({"error": f"Lỗi API: {str(e)}"}), 403

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.get_json()
    math_problem = data.get('text') or ''
    selected_model = data.get('model') or 'gemini-1.5-flash-latest'
    user_api_key = data.get('api_key')
    image_b64 = data.get('image_base64')

    if not math_problem and not image_b64:
        return jsonify({"error": "Hãy nhập đề toán hoặc tải ảnh lên!"}), 400

    active_key = user_api_key if (user_api_key and user_api_key.strip() != "") else os.environ.get("GEMINI_API_KEY")
    
    if not active_key:
        return jsonify({"error": "Không có API Key hợp lệ. Hãy kiểm tra biến môi trường hoặc nhập key thủ công!"}), 400
        
    try:
        genai.configure(api_key=active_key)

       system_instruction = """Bạn là một chuyên gia chuyển đổi đề toán thành câu lệnh (prompt) tạo ảnh bằng tiếng Anh.
        QUY TẮC ĐỂ TẠO ẢNH GIỐNG SÁCH GIÁO KHOA (NHƯ ẢNH MẪU):
        1. Phong cách đồ họa: BẮT BUỘC thêm cụm từ "2D educational children's book illustration, bright colorful anime style, clear line art, flat colors". Tuyệt đối KHÔNG dùng "3D, photorealistic, render".
        2. Bối cảnh & Nhân vật: Luôn mô tả một nhân vật (ví dụ: "a cute young schoolboy") đang tương tác thực tế với vật thể trong một bối cảnh (ví dụ: "outdoor garden background with plants").
        3. Khung trích xuất chi tiết (Callout): Để thể hiện vật nhỏ cạnh vật lớn, hãy dùng cụm từ "a magnified circular inset showing a close-up of the small [tên vật thể]".
        4. Ký hiệu toán học: Thêm từ khóa "math educational diagram, drawing measurement arrows, mathematical annotations". (Lưu ý: Không ép AI viết tiếng Việt vì AI vẽ chữ rất kém, chỉ cần vẽ bối cảnh và mũi tên).
        
        Ví dụ đề: "Bể 2m x 3m chứa nước, múc bằng gáo trụ 15cm"
        Prompt chuẩn: "2D educational children's book illustration, bright colorful anime style. A cute young schoolboy standing in a garden, holding a tiny cylindrical wooden ladle to scoop water from a massive rectangular water tank. There is a magnified circular inset showing a detailed close-up of the wooden ladle. Math educational diagram, drawing measurement arrows, mathematical annotations, clear line art, cheerful atmosphere."
        
        Chỉ trả về nội dung prompt tiếng Anh, tuyệt đối không giải thích thêm."""

        model = genai.GenerativeModel(
            model_name=selected_model,
            system_instruction=system_instruction
        )
        
        prompt_contents = []
        if math_problem:
            prompt_contents.append(math_problem)
            
        if image_b64:
            mime_type, base64_data = image_b64.split(';base64,')
            mime_type = mime_type.replace('data:', '')
            prompt_contents.append({
                'mime_type': mime_type,
                'data': base64.b64decode(base64_data)
            })
        
        response = model.generate_content(prompt_contents)
        prompt = response.text.strip()
        
        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=400&nologo=true"
        
        return jsonify({"prompt": prompt, "image_url": image_url})
    except Exception as e:
        print(f"LỖI HỆ THỐNG GEMINI: {str(e)}") 
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
