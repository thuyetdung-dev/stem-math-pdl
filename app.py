import os
import urllib.parse
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

# Sửa lỗi 3: Bổ sung template_folder='.' để Flask quét file index.html ở thư mục gốc
app = Flask(__name__, template_folder='.')

api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate(): # Sửa lỗi 1: Bổ sung định nghĩa hàm cho route này
    # Toàn bộ khối lệnh bên dưới đã được thụt lề (indent) đúng chuẩn Python
    data = request.get_json()
    math_problem = data.get('prompt') or data.get('text') or data.get('message') or ''

    if not math_problem:
        return jsonify({"error": "Máy chủ chưa nhận được chữ. Hãy kiểm tra biến gửi đi trong file HTML!"}), 400

    system_instruction = """Bạn là một chuyên gia chuyển đổi đề toán hình học không gian thành câu lệnh (prompt) tạo ảnh 3D bằng tiếng Anh. 
    QUY TẮC QUAN TRỌNG VỀ TỶ LỆ KÍCH THƯỚC:
    1. Phân tích số liệu tự động: Nếu phát hiện sự chênh lệch lớn về đơn vị đo (ví dụ: mét và centimet), BẮT BUỘC dùng tính từ cường điệu để phân biệt.
    2. Tính từ cường điệu: Dùng "massive", "giant" cho khối hình lớn và "tiny", "miniature" cho khối nhỏ.
    3. Tương tác vật lý: Mô tả vật thể nhỏ nằm lọt thỏm bên cạnh vật thể lớn (ví dụ: "The tiny ladle is dwarfed by the massive tank").
    4. Góc máy: Thêm các cụm từ "wide-angle shot, clear size comparison, educational STEM visualization".
    Chỉ trả về nội dung câu lệnh prompt bằng tiếng Anh, không giải thích thêm."""

    try:
        # Sửa lỗi 2: Chuyển sang model khả dụng gemini-1.5-flash
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
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