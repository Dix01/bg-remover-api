from flask import Flask, request, send_file, jsonify
from rembg import new_session, remove
from PIL import Image
import io
import os
import logging
import tempfile

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure maximum file size (16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Path to your local small model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "u2netp.onnx")

# Create a rembg session with your local model (loads once at startup)
try:
    session = new_session('u2net_custom', {'model_path': MODEL_PATH})
    logger.info(f"Successfully loaded local model from: {MODEL_PATH}")
except Exception as e:
    logger.error(f"Failed to load local model: {e}")
    logger.info("Falling back to default u2netp model")
    session = new_session('u2netp')

@app.route('/remove-bg', methods=['POST'])
def remove_bg():
    """
    Remove background from uploaded image
    Expects: multipart/form-data with 'image' file (matches iOS app)
    Returns: PNG image with transparent background
    """
    try:
        # Debug: Log request details
        logger.info("=== Incoming /remove-bg Request ===")
        logger.info(f"Method: {request.method}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Files: {list(request.files.keys())}")
        logger.info(f"Form keys: {list(request.form.keys())}")
        try:
            raw_data = request.get_data()
            logger.info(f"Raw body length: {len(raw_data)} bytes")
        except Exception as e:
            logger.warning(f"Could not read raw body: {e}")

        # Check if image file is present
        if 'image' not in request.files:
            logger.error("No 'image' field found in request.files")
            return jsonify({"error": "No image file provided"}), 400

        file = request.files['image']

        if file.filename == '':
            logger.error("Empty filename received")
            return jsonify({"error": "No file selected"}), 400

        logger.info(f"Processing image: {file.filename}")

        # Read the image file
        input_image = file.read()
        
        if not input_image or len(input_image) == 0:
            logger.error("Empty image data received")
            return jsonify({"error": "Empty image data"}), 400

        logger.info(f"Image data size: {len(input_image)} bytes")

        # Validate that we received actual image data
        try:
            Image.open(io.BytesIO(input_image))
            logger.info("Image data validation successful")
        except Exception as validation_error:
            logger.error(f"Invalid image data: {validation_error}")
            return jsonify({"error": "Invalid image data received"}), 400

        # Remove background using the session
        logger.info("Starting background removal...")
        output_image = remove(input_image, session=session)
        logger.info("Background removal completed successfully")

        # --- MODIFIED SECTION ---
        # Return the result as a PNG image file directly in the response body.
        # This is the correct method for a programmatic API client like an iOS app.
        return send_file(
            io.BytesIO(output_image),
            mimetype='image/png'
        )
        # --- END MODIFIED SECTION ---

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return jsonify({"error": f"Failed to process image: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Background removal service is running"})

@app.route('/', methods=['GET'])
def home():
    return """
    <h1>Background Removal API</h1>
    <h2>Test Upload (matches iOS app format)</h2>
    <form action="/remove-bg" method="post" enctype="multipart/form-data">
        <input type="file" name="image" accept="image/*" required>
        <button type="submit">Remove Background</button>
    </form>
    <h2>Available Endpoints:</h2>
    <ul>
        <li>POST /remove-bg - Upload image for background removal (field name: 'image')</li>
        <li>GET /health - Health check</li>
    </ul>
    """

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum size is 16MB"}), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Use PORT from env for hosting platforms, fallback for local
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
