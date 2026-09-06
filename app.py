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

        system_instruction = """Bạn là một chuyên gia chuyển đổi đề toán hình học không gian thành câu lệnh (prompt) tạo ảnh 3D bằng tiếng Anh.
        QUY TẮC TỐI QUAN TRỌNG ĐỂ AI VẼ ĐÚNG:
        1. LOẠI BỎ HOÀN TOÀN CON SỐ: Tuyệt đối không đưa các số đo (2m, 3m, 15cm...) vào prompt vì AI vẽ ảnh không hiểu kích thước thực.
        2. Dùng tính từ thay thế: Biến số đo lớn thành "massive", "giant" và số đo nhỏ thành "tiny", "miniature".
        3. Tên hình khối chuẩn: Dùng "rectangular prism" (hình hộp chữ nhật), "cylinder" (hình trụ), "sphere" (hình cầu).
        4. Phong cách ép buộc: Bắt buộc chèn cụm từ này vào cuối mỗi prompt: "minimalist 3D geometric diagram, pure white background, clear size comparison, educational STEM illustration, isometric view, soft studio lighting, matte plastic materials".
        
        Ví dụ đề: "Bể 2m x 3m chứa nước, múc bằng gáo trụ 15cm"
        Prompt chuẩn: "A massive transparent rectangular prism water tank filled with blue water. Next to it on the ground is an extremely tiny cylindrical ladle. Minimalist 3D geometric diagram, pure white background, clear size comparison, educational STEM illustration, isometric view, soft studio lighting, matte plastic materials."
        
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