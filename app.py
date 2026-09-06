import os
import urllib.parse
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

@app.route('/')
def index():
    # Flask sẽ tự động tìm file index.html trong thư mục "templates"
    return render_template('index.html')

@app.route('/api/scan-models', methods=['POST'])
def scan_models():
    data = request.get_json()
    user_api_key = data.get('api_key')
    
    # Dùng API Key của user nếu có, ngược lại dùng key mặc định của máy chủ Vercel
    active_key = user_api_key if (user_api_key and user_api_key.strip() != "") else os.environ.get("GEMINI_API_KEY")

    if not active_key:
        return jsonify({"error": "Không tìm thấy API Key nào để kết nối!"}), 400

    try:
        # Cấu hình API Key để dò
        genai.configure(api_key=active_key)
        
        available_models = []
        # Quét và lọc các mô hình hỗ trợ sinh văn bản
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

    if not math_problem:
        return jsonify({"error": "Máy chủ chưa nhận được chữ. Hãy nhập đề toán!"}), 400

    # Dùng API Key của user nếu có, ngược lại dùng key mặc định
    active_key = user_api_key if (user_api_key and user_api_key.strip() != "") else os.environ.get("GEMINI_API_KEY")
    
    if not active_key:
        return jsonify({"error": "Không có API Key hợp lệ. Hãy kiểm tra biến môi trường hoặc nhập key thủ công!"}), 400
        
    try:
        # Cấu hình API Key để bắt đầu tạo ảnh
        genai.configure(api_key=active_key)

        system_instruction = """Bạn là một chuyên gia chuyển đổi đề toán hình học không gian thành câu lệnh (prompt) tạo ảnh 3D bằng tiếng Anh. 
        QUY TẮC QUAN TRỌNG VỀ TỶ LỆ KÍCH THƯỚC:
        1. Phân tích số liệu tự động: Nếu phát hiện sự chênh lệch lớn về đơn vị đo (ví dụ: mét và centimet), BẮT BUỘC dùng tính từ cường điệu để phân biệt.
        2. Tính từ cường điệu: Dùng "massive", "giant" cho khối hình lớn và "tiny", "miniature" cho khối nhỏ.
        3. Tương tác vật lý: Mô tả vật thể nhỏ nằm lọt thỏm bên cạnh vật thể lớn (ví dụ: "The tiny ladle is dwarfed by the massive tank").
        4. Góc máy: Thêm các cụm từ "wide-angle shot, clear size comparison, educational STEM visualization".
        Chỉ trả về nội dung câu lệnh prompt bằng tiếng Anh, không giải thích thêm."""

        model = genai.GenerativeModel(
            model_name=selected_model,
            system_instruction=system_instruction
        )
        
        response = model.generate_content(math_problem)
        prompt = response.text.strip()
        
        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=400&nologo=true"
        
        return jsonify({"prompt": prompt, "image_url": image_url})
    except Exception as e:
        print(f"LỖI HỆ THỐNG GEMINI: {str(e)}") 
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
