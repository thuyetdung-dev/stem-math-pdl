from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types
import urllib.parse
import os

app = Flask(__name__)

# Lấy API Key từ hệ thống Vercel
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    math_problem = data.get('text', '')

    # Bộ quy tắc System Instruction ép AI nhận diện tỷ lệ hình học thực tế
    system_instruction = """Bạn là một chuyên gia chuyển đổi đề toán hình học không gian thành câu lệnh (prompt) tạo ảnh 3D bằng tiếng Anh. 
    Nhiệm vụ của bạn là đọc đề bài và tạo ra MỘT câu lệnh tiếng Anh duy nhất.

    QUY TẮC QUAN TRỌNG VỀ TỶ LỆ KÍCH THƯỚC:
    1. Phân tích số liệu tự động: Nếu phát hiện sự chênh lệch lớn về đơn vị đo (ví dụ: mét và centimet), BẮT BUỘC dùng tính từ cường điệu để phân biệt.
    2. Tính từ cường điệu: Dùng "massive", "giant", "enormous" cho khối hình lớn và "tiny", "miniature" cho khối hình nhỏ.
    3. Tương tác vật lý: Mô tả vật thể nhỏ nằm lọt thỏm bên cạnh vật thể lớn (ví dụ: "The tiny ladle is dwarfed by the massive tank").
    4. Góc máy nhiếp ảnh: Thêm các cụm từ "wide-angle shot, deep depth of field, clear size comparison, educational STEM visualization" để bối cảnh trực quan nhất.

    Chỉ trả về nội dung câu lệnh prompt bằng tiếng Anh, không giải thích thêm."""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=math_problem,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )
        prompt = response.text.strip()
        
        # Tạo đường dẫn ảnh từ Pollinations AI
        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=400&nologo=true"
        
        return jsonify({"prompt": prompt, "image_url": image_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)