import os
import logging
import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np
import io

from efficientnet.keras import preprocess_input
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import load_img, img_to_array

def load_models():
    model1 = load_model("weights/model.h5")
    print('model1 loading complete')
    
    return model1

def show_predict(model, preprocessed_image):
    classes = model.predict(preprocessed_image)
    predicted_index = np.argmax(classes[0])
    confidence = max(100 * classes[0])
    return predicted_index, confidence

def main(img_path, model1):
    img = tf.keras.utils.load_img(
        io.BytesIO(img_path.read()), target_size=(150, 150)
    )
    x = tf.keras.utils.img_to_array(img)
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)
    
    index, confidence = show_predict(model1,x)
    return index, confidence

