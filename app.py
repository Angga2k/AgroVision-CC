from flask import Flask, request, jsonify
import tensorflow as tf
import numpy as np
from PIL import Image
import io

app = Flask(__name__)

# Memuat model
model = tf.keras.models.load_model("model.h5")

# Fungsi preprocessing (disesuaikan dengan model Anda)
def preprocess_image(image):
    """
    Preprocessing untuk input gambar. Sesuaikan dengan model Anda.
    """
    # Ubah gambar ke RGB (jika perlu)
    if image.mode != "RGB":
        image = image.convert("RGB")
    
    # Ubah ukuran gambar ke ukuran yang diterima model
    target_size = (150, 150)  # Contoh ukuran (sesuaikan dengan model)
    image = image.resize(target_size)
    
    # Konversi ke array numpy dan normalisasi
    image_array = np.array(image) / 255.0  # Normalisasi ke [0,1]
    
    # Tambahkan dimensi batch
    image_array = np.expand_dims(image_array, axis=0)
    
    return image_array

# Endpoint untuk prediksi
@app.route("/predict", methods=["POST"])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Validasi ekstensi file
    allowed_extensions = {'jpg', 'jpeg', 'png'}
    if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return jsonify({'error': 'Invalid file extension'}), 400

    try:
        # Membaca file gambar
        image = Image.open(io.BytesIO(file.read()))
        
        # Preprocessing gambar
        processed_image = preprocess_image(image)
        
        # Prediksi menggunakan model
        predictions = model.predict(processed_image)
        
        # Ubah ke list agar bisa dijadikan JSON
        predictions = predictions.tolist()

        return jsonify({"predictions": predictions})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Jalankan aplikasi
if __name__ == "__main__":
    app.run(debug=True)
