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

        system_instruction = """Bạn là chuyên gia chuyển đổi bài toán thực tế thành câu lệnh prompt tạo ảnh minh họa sách giáo khoa bằng tiếng Anh.
QUY TẮC BỐ CỤC BẮT BUỘC:
1. Chia bố cục rõ ràng:
   - On the left: Một hình khối hình học lớn (ví dụ: massive transparent rectangular prism water tank filled with water, concrete edges, isometric perspective).
   - On the right: Một cậu bé đứng hoàn toàn bên ngoài trên mặt đất (schoolboy standing outside on the ground next to the tank, holding a tiny wooden ladle). Tuyệt đối không để người ở bên trong khối nước.
2. Phong cách vẽ: Bắt buộc dùng "Vietnamese textbook math illustration style, clear 2D technical line art, flat cartoon vector colors, educational infographic layout, outdoor yard setting".
3. Ký hiệu đo lường: Thêm "with measurement arrows and dimension lines along the edges, technical educational diagram".
4. Không đưa con số đo lường chi tiết vào prompt để tránh chữ bị méo mó vô nghĩa. Chỉ tập trung vào hình khối, tỷ lệ lớn/nhỏ và vị trí nhân vật.

Chỉ trả về duy nhất chuỗi prompt bằng tiếng Anh, không thêm văn bản giải thích."""

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
        # Nâng cấp lên model=flux để dựng hình khối và nhân vật sắc nét, đúng bố cục
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=576&model=flux&nologo=true"
        
        return jsonify({"prompt": prompt, "image_url": image_url})
    except Exception as e:
        print(f"LỖI HỆ THỐNG GEMINI: {str(e)}") 
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)