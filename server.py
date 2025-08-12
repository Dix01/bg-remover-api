from flask import Flask, request, send_file, jsonify
import os
import io
from PIL import Image
from rembg import remove
import tempfile
import logging
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure maximum file size (16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Background removal service is running"})

@app.route('/remove-bg', methods=['POST'])
def remove_background():
    """
    Remove background from uploaded image
    Expects: multipart/form-data with 'image' file
    Returns: PNG image with transparent background
    """
    try:
        # Check if image file is present
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff'}
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            return jsonify({"error": f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"}), 400
        
        logger.info(f"Processing image: {file.filename}")
        
        # Read the image file
        input_image = file.read()
        
        # Remove background using rembg
        output_image = remove(input_image)
        
        # Create a temporary file to store the result
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            temp_file.write(output_image)
            temp_file_path = temp_file.name
        
        logger.info("Background removal completed successfully")
        
        # Send the processed image back
        def remove_temp_file():
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
        
        return send_file(
            temp_file_path,
            mimetype='image/png',
            as_attachment=True,
            download_name=f"no_bg_{file.filename.rsplit('.', 1)[0]}.png"
        )
    
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return jsonify({"error": f"Failed to process image: {str(e)}"}), 500

@app.route('/remove-bg-base64', methods=['POST'])
def remove_background_base64():
    """
    Alternative endpoint that accepts base64 encoded images
    Expects JSON: {"image": "base64_encoded_image_data"}
    Returns JSON: {"image": "base64_encoded_result"}
    """
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"error": "No base64 image data provided"}), 400
        
        # Decode base64 image
        try:
            image_data = base64.b64decode(data['image'])
        except Exception as e:
            return jsonify({"error": "Invalid base64 image data"}), 400
        
        logger.info("Processing base64 image")
        
        # Remove background
        output_image = remove(image_data)
        
        # Encode result back to base64
        output_base64 = base64.b64encode(output_image).decode('utf-8')
        
        logger.info("Base64 background removal completed successfully")
        
        return jsonify({
            "success": True,
            "image": output_base64,
            "format": "png"
        })
    
    except Exception as e:
        logger.error(f"Error processing base64 image: {str(e)}")
        return jsonify({"error": f"Failed to process image: {str(e)}"}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum size is 16MB"}), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    print("🚀 Starting Background Removal Server for ngrok...")
    print("📱 This server is optimized for iOS app integration via ngrok")
    print("\nAvailable endpoints:")
    print("  GET  /health - Health check")
    print("  POST /remove-bg - Upload image file (multipart/form-data)")
    print("  POST /remove-bg-base64 - Send base64 encoded image (JSON)")
    print("\n" + "="*60)
    print("🔗 SETUP INSTRUCTIONS:")
    print("1. Install ngrok: https://ngrok.com/download")
    print("2. Run this server: python server.py")
    print("3. In another terminal, run: ngrok http 5000")
    print("4. Copy the ngrok HTTPS URL (e.g., https://abc123.ngrok.io)")
    print("5. Use that URL in your iOS app")
    print("="*60)
    print("\n🌐 Starting server on localhost:5000 (ready for ngrok)")
    
    # Run the server - optimized for ngrok
    app.run(
        host='127.0.0.1',  # localhost for ngrok
        port=5000,
        debug=False,
        threaded=True,
        use_reloader=False  # Prevent issues with ngrok
    )
