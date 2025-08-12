from flask import Flask, request, jsonify, send_file
from rembg import remove
from PIL import Image
import io
import os

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Background removal service is running"
    })

@app.route('/remove-bg', methods=['POST'])
def remove_background():
    try:
        # Ensure a file was uploaded
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        input_image = request.files['image']

        # Open the uploaded image
        input_pil = Image.open(input_image.stream).convert("RGBA")

        # Remove background
        output = remove(input_pil)

        # Save output to bytes
        img_byte_arr = io.BytesIO()
        output.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)

        # Return the image as a file
        return send_file(
            img_byte_arr,
            mimetype='image/png',
            as_attachment=True,
            download_name='output.png'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render provides PORT
    app.run(
        host='0.0.0.0',  # Listen on all interfaces
        port=port,
        debug=False,
        threaded=True
    )
