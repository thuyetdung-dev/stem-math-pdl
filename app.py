from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types
import urllib.parse
import os  # Bổ sung thư viện os

app = Flask(__name__)

# Lấy API Key từ cài đặt bảo mật của máy chủ (Vercel)
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate_image():
    try:
        data = request.json
        math_problem = data.get('math_problem', '')
        
        # 1. Gọi Gemini phân tích
        system_instruction = (
            "Bạn là chuyên gia thiết kế giáo cụ trực quan STEM. "
            "Hãy đọc đề toán và viết ra MỘT CÂU LỆNH NGẮN GỌN (dưới 40 từ tiếng Anh) để vẽ ảnh minh họa. "
            "Chỉ trả về tiếng Anh, không giải thích."
        )
        
        response = client.models.generate_content(
            model='gemini-3.6-flash', # Dùng bản này cho ổn định
            contents=f"Đề toán: {math_problem}\n\nPrompt vẽ ảnh:",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            )
        )
        prompt_ve_anh = response.text.strip()
        
        # 2. Tạo link ảnh trực tiếp
        encoded_prompt = urllib.parse.quote(prompt_ve_anh)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true"
        
        return jsonify({
            "success": True, 
            "image_url": image_url,
            "prompt": prompt_ve_anh
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    # Khởi chạy máy chủ web
    print("🚀 TRANG WEB ĐÃ SẴN SÀNG! Mở trình duyệt và truy cập: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)