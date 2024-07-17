# load libraries
import numpy as np
import tensorflow as tf
from tensorflow import keras


def create_model(input):
    inputs = keras.layers.Input(shape=(input[0], input[1]))
    x = keras.layers.LSTM(64, return_sequences=True)(inputs)
    x = keras.layers.LSTM(64)(x)
    x = keras.layers.Dropout(0.2)(x)
    output = keras.layers.Dense(1)(x)   

    model = keras.Model(inputs=inputs, outputs=output, name="hr_model")
    model.compile(
        optimizer=keras.optimizers.Adam(),
        metrics=["mae"],
        loss="mae",
    )
    return model

def load_model():
    model = create_model(input=(60, 4))
    # Load weight
    model.load_weights("./model_checkpoint.keras")
    return model

def predict(model, input):
    a = model.predict(input)
    print(a)
