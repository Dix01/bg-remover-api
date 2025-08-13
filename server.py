from flask import Flask, request, send_file
from rembg import new_session, remove
from PIL import Image
import io
import os

app = Flask(__name__)

# Path to your local small model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "u2netp.onnx")

# Method 1: Create a rembg session with u2net_custom model and specify model_path
# This is the correct way according to rembg documentation
try:
    session = new_session('u2net_custom', {'model_path': MODEL_PATH})
    print(f"Successfully loaded local model from: {MODEL_PATH}")
except Exception as e:
    print(f"Failed to load local model: {e}")
    print("Falling back to default u2netp model")
    session = new_session('u2netp')

@app.route('/remove-bg', methods=['POST'])
def remove_bg():
    if 'file' not in request.files:
        return "No file uploaded", 400

    input_file = request.files['file']
    input_bytes = input_file.read()

    # Remove background using the session with your local model
    output_bytes = remove(input_bytes, session=session)

    # Return the result as a PNG image file
    return send_file(
        io.BytesIO(output_bytes),
        mimetype='image/png',
        as_attachment=True,
        download_name='output.png'
    )

@app.route('/health', methods=['GET'])
def health_check():
    return "OK", 200

if __name__ == '__main__':
    # Use PORT from env for hosting platforms, fallback to 5000 locally
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
