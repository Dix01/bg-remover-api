from flask import Flask, request, jsonify, send_file
from rembg import remove, new_session
from PIL import Image
import io
import os

app = Flask(__name__)

# Path to local small model (u2netp.onnx)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "u2netp.onnx")

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Local model file not found at {MODEL_PATH}")

print(f"Loading model from {MODEL_PATH}...")
# Load model without triggering auto-download
session = new_session(model_path=MODEL_PATH)
print("Model loaded successfully.")

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Background removal service is running"
    })

@app.route('/remove-bg', methods=['POST'])
def remove_background():
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        input_image = request.files['image']
        input_pil = Image.open(input_image.stream).convert("RGBA")

        # Remove background using preloaded local model session
        output = remove(input_pil, session=session)

        img_byte_arr = io.BytesIO()
        output.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)

        return send_file(
            img_byte_arr,
            mimetype='image/png',
            as_attachment=True,
            download_name='output.png'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )
