# app.py

from flask import Flask, request, send_file, jsonify
from rembg import new_session, remove
from PIL import Image, ImageFile
import io
import os
import logging
import gc

# Allow PIL to load truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

# --- CORE OPTIMIZATIONS ---
# 1. Define a max dimension for images to prevent memory spikes from large uploads.
#    A 12MP image (4000x3000) can use >50MB RAM when opened. Resizing is crucial.
MAX_IMAGE_DIMENSION = 1200 

# 2. Use a much lighter, faster model. 'isnet-general-use' is excellent for performance.
#    It's significantly smaller than u2netp.
MODEL_NAME = 'isnet-general-use'
# ---

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure maximum file size (10MB). A smaller limit is safer on a free tier.
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# Create a rembg session (loads model once at startup)
try:
    session = new_session(MODEL_NAME)
    logger.info(f"Successfully loaded model: {MODEL_NAME}")
except Exception as e:
    logger.error(f"Failed to load model '{MODEL_NAME}': {e}. Check model name and dependencies.")
    # Exit if the core component can't load.
    exit()

@app.route('/remove-bg', methods=['POST'])
def remove_bg():
    """
    Remove background from an uploaded image, optimized for low-memory environments.
    """
    file = None
    input_image_bytes = None
    try:
        if 'image' not in request.files:
            logger.error("No 'image' field in request.files")
            return jsonify({"error": "No image file provided"}), 400

        file = request.files['image']

        if file.filename == '':
            logger.error("Empty filename submitted")
            return jsonify({"error": "No file selected"}), 400

        logger.info(f"Processing image: {file.filename}")
        input_image_bytes = file.read()

        if not input_image_bytes:
            logger.error("Received empty image data")
            return jsonify({"error": "Empty image data"}), 400
        
        # --- MEMORY OPTIMIZATION: RESIZE BEFORE PROCESSING ---
        # Open image with Pillow to check dimensions and resize if necessary
        try:
            img = Image.open(io.BytesIO(input_image_bytes))
            
            # Ensure the image is in a mode rembg can handle (RGBA)
            img = img.convert("RGBA")

            if max(img.size) > MAX_IMAGE_DIMENSION:
                logger.info(f"Image is large ({img.size}), resizing to max {MAX_IMAGE_DIMENSION}px")
                img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
            
            # Save the potentially resized image back to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            input_image_bytes = img_byte_arr.getvalue()
            logger.info(f"Image pre-processed for removal. New size: {img.size}")
            
        except Exception as e:
            logger.error(f"Could not validate or resize image: {e}")
            return jsonify({"error": "Invalid or corrupt image file"}), 400
        # ---

        # Remove background using the pre-loaded session
        logger.info("Starting background removal...")
        output_image_bytes = remove(input_image_bytes, session=session)
        logger.info("Background removal completed.")

        # Return the resulting PNG image
        return send_file(
            io.BytesIO(output_image_bytes),
            mimetype='image/png',
            as_attachment=False # Send inline
        )

    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    
    finally:
        # --- MEMORY OPTIMIZATION: EXPLICIT GARBAGE COLLECTION ---
        # Explicitly free up memory after the request is complete.
        # This is vital on low-RAM servers.
        del file
        del input_image_bytes
        gc.collect()
        logger.info("Garbage collection triggered.")


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Service is running"})

@app.route('/')
def home():
    """Simple home page with upload form for testing."""
    return """
    <h1>Background Removal API (Optimized)</h1>
    <p>Using <b>isnet-general-use</b> model for low memory usage.</p>
    <form action="/remove-bg" method="post" enctype="multipart/form-data">
        <input type="file" name="image" accept="image/*" required>
        <button type="submit">Remove Background</button>
    </form>
    """

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum size is 10MB"}), 413

if __name__ == '__main__':
    # Gunicorn is recommended for production instead of app.run()
    # The host and port are typically handled by the deployment platform (e.g., Render)
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
