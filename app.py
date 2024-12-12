import os
from flask import Flask, request, jsonify
from google.cloud import firestore
import re
from predict import *
from google.cloud import storage
import os
import uuid
import firebase_admin
from firebase_admin import auth
from werkzeug.utils import secure_filename

model = load_models()

# Inisialisasi Flask
app = Flask(__name__)
db = firestore.Client()

# Koleksi Firestore
users_collection = db.collection('users')
predictions_collection = db.collection('predictions')

# Set your bucket name
BUCKET_NAME = 'image-agrovision'


# Fungsi untuk mengunggah gambar ke Google Cloud Storage
def upload_to_gcs(file, bucket_name):
    # Membuat nama file unik
    unique_filename = str(uuid.uuid4()) + secure_filename(file.filename)
    
    # Membuat client Google Cloud Storage
    client = storage.Client()

    # Mengakses bucket
    bucket = client.get_bucket(bucket_name)
    
    # Mengunggah file ke bucket
    blob = bucket.blob(unique_filename)
    blob.upload_from_file(file)

    # Menetapkan file sebagai dapat diakses publik
    blob.make_public()

    # Mengembalikan URL publik file
    return blob.public_url

# Fungsi validasi email
def is_valid_email(email):
    """Validate email format."""
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email) is not None

# Endpoint untuk Login Menggunakan Token Firebase (hapus jika tidak digunakan)
@app.route('/login', methods=['POST'])
def login():
    return jsonify({"message": "Login successful"}), 200

# Endpoint untuk Registrasi Pengguna
@app.route('/register', methods=['POST'])
def register_user():
    data = request.json

    if not data.get('email') or not is_valid_email(data['email']):
        return jsonify({"error": "Invalid or missing email"}), 400

    if not data.get('name'):
        return jsonify({"error": "Name is required"}), 400

    if not data.get('uid'):
        return jsonify({"error": "UID is required"}), 400

    try:
        existing_user = users_collection.document(data['uid']).get()

        if existing_user.exists:
            return jsonify({"error": "User already exists"}), 409

        users_collection.document(data['uid']).set({
            'name': data['name'],
            'phone': data['phone'],
            'email': data['email'],
            'address': data.get('address', '')  
        })
        return jsonify({"message": "User registered successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint untuk Menyimpan Riwayat Prediksi

@app.route("/prediction", methods=['POST'])
def predictions():
    # Cek apakah ada data form
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    imagefile = request.files['file']
    
    # Cek jika file tidak ada atau kosong
    if imagefile.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Cek ekstensi file yang diperbolehkan
    allowed_extensions = {'jpg', 'jpeg', 'png'}
    if '.' not in imagefile.filename or imagefile.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return jsonify({'error': 'Invalid file extension'}), 400
    
    class_prediction = ["Alternaria Alternata", "Cercospora Nicotianae", "Healthy"]

    # Proses file image langsung tanpa menyimpannya
    result, prediction = main(imagefile, model)
    response_data = {
        "accuracy": float(prediction), 
        "class": class_prediction[int(result)]
    }
    return jsonify(response_data), 200


@app.route('/save-prediction', methods=['POST'])
def save_prediction():
    try:
        # Memeriksa apakah file dikirim
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        # Mengambil file dari request
        imagefile = request.files['file']
        
        # Memeriksa apakah file kosong
        if imagefile.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        allowed_extensions = {'jpg', 'jpeg', 'png'}
        if '.' not in imagefile.filename or imagefile.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'error': 'Invalid file extension'}), 400
        
        # Mengunggah file ke Google Cloud Storage
        image_url = upload_to_gcs(imagefile, BUCKET_NAME)
        
        # Mendapatkan ID Token dari pengguna yang login
        user_uid = None
        if 'Authorization' in request.headers:
            id_token = request.headers['Authorization'].split('Bearer ')[1]
            user_uid = get_user_uid_from_id_token(id_token)  # Fungsi untuk mengambil user UID
        
        # Mengambil data lainnya dari form-data
        result = request.form.get('result')
        accuracy = request.form.get('accuracy')

        if not user_uid or not result:
            return jsonify({"error": "Missing user_id or result"}), 400
        
        # Menyimpan data ke Firestore
        prediction_id = predictions_collection.document().id
        predictions_collection.document(prediction_id).set({
            'user_id': user_uid,
            'result': result,
            'accuracy' : accuracy,
            'date': firestore.SERVER_TIMESTAMP,
            'image_url': image_url
        })

        return jsonify({"message": "Prediction saved successfully", "prediction_id": prediction_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_user_uid_from_id_token(id_token):
    # Inisialisasi Firebase Admin SDK

    # Jika Firebase Admin SDK belum diinisialisasi
    if not firebase_admin._apps:
        firebase_admin.initialize_app()

    # Ambil user ID dari ID Token
    decoded_token = auth.verify_id_token(id_token)
    return decoded_token['uid']


# Endpoint untuk Mendapatkan Riwayat Prediksi
@app.route('/get-predictions/', methods=['GET'])
def get_predictions():
    try:
        user_uid = None
        if 'Authorization' in request.headers:
            id_token = request.headers['Authorization'].split('Bearer ')[1]
            user_uid = get_user_uid_from_id_token(id_token)  # Fungsi untuk mengambil user UID
            
        if user_uid == None:
            return jsonify({"status" : "error",
                            "message" : "please login first"
                            })
            
        predictions = predictions_collection.where('user_id', '==', user_uid).stream()
        results = [
            {'prediction_id': pred.id, **pred.to_dict()} for pred in predictions
        ]
        
        if not results:
            return jsonify({
                "status": "success",
                "data": []
            }), 200
        
        return jsonify({
            "status": "success",
            "data": results
        }), 200
    except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)