from flask import Flask, request, send_file
from rembg import new_session, remove
import io
import os
from pathlib import Path

# --- Start of Fix ---
# The issue likely stems from a version mismatch in the 'rembg' library.
# Your code uses an argument 'model_path' which existed in older versions.
# Newer versions of 'rembg' expect a 'model_name' and handle model
# downloading and caching automatically using another library called 'pooch'.
#
# The fix below updates your code to work with modern 'rembg' versions
# by telling it to use your local model file instead of downloading one.
# We do this by overriding the download URL for the 'u2netp' model
# with the path to your local file.

# 1. Import the necessary dictionary that stores model information
from rembg.u2net import MODELS

# 2. Define the model name and the path to your local .onnx file
model_name = "u2netp"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", f"{model_name}.onnx")

# 3. Check if the model file actually exists to prevent errors at startup
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Local model file not found at {MODEL_PATH}. "
        f"Please make sure the 'models/u2netp.onnx' file is in the correct location."
    )

# 4. Override the model's URL to point to the local file path.
#    The 'file://' prefix is essential for the underlying library to
#    recognize it as a local path. We also clear the hash check, as
#    your local file won't match the original download hash.
MODELS[model_name]["url"] = f"file://{Path(MODEL_PATH).resolve()}"
MODELS[model_name]["hash"] = None
# --- End of Fix ---


app = Flask(__name__)

# Now, create the rembg session. It will use the local model specified above.
# We explicitly pass the model_name to ensure the correct one is loaded.
print(f"Loading rembg session for '{model_name}' from local file...")
try:
    session = new_session(model_name)
    print("Session loaded successfully.")
except Exception as e:
    # Provide a more helpful error message if session creation fails
    raise RuntimeError(
        f"Failed to create rembg session. This might be due to an issue with "
        f"the onnxruntime or the model file itself. Original error: {e}"
    )


@app.route('/remove-bg', methods=['POST'])
def remove_bg_endpoint():
    # Check if a file was uploaded
    if 'file' not in request.files or request.files['file'].filename == '':
        return "No file selected or file part is missing.", 400

    input_file = request.files['file']

    # Ensure the file is valid
    if input_file:
        input_bytes = input_file.read()

        # Remove background using the pre-loaded session
        output_bytes = remove(input_bytes, session=session)

        # Create a more descriptive output filename
        output_filename = f"{Path(input_file.filename).stem}_bg_removed.png"

        # Return the result as a PNG image file for download
        return send_file(
            io.BytesIO(output_bytes),
            mimetype='image/png',
            as_attachment=True,
            download_name=output_filename
        )

    return "Invalid file uploaded.", 400

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to confirm the server is running."""
    return "OK", 200

if __name__ == '__main__':
    # Use PORT from environment variable for hosting platforms, fallback to 10000 locally
    port = int(os.environ.get('PORT', 10000))
    # Running on 0.0.0.0 makes it accessible from your local network
    app.run(host='0.0.0.0', port=port)
