import numpy as np
from PIL import Image
import tflite_runtime.interpreter as tflite


class Model:
    def __init__(self):
        self.model_path = "/home/facebeer/model.tflite"
        self.labels_path = "/home/facebeer/labels.txt"
        self.labels = self.read_label_file()
        self.interpreter = tflite.Interpreter(self.model_path)
        self.interpreter.allocate_tensors()
        self.input_img_shape = (256, 256)

    def read_label_file(self):
        labels = {}
        with open(self.labels_path, 'r') as file:
            for i, e in enumerate(file.readlines()):
                labels.update({i: e.replace('\n', '')})
        return labels

    def predict(self, img):
        input_details = self.interpreter.get_input_details()[0]
        img = img.resize(self.input_img_shape, Image.LANCZOS)
        img = np.array(img, dtype=np.float32)
        img /= 256.0
        img = np.expand_dims(img, axis=0)
        self.interpreter.set_tensor(input_details['index'], img)
        self.interpreter.invoke()
        output_details = self.interpreter.get_output_details()[0]
        output = self.interpreter.get_tensor(output_details['index'])
        output = np.squeeze(output)
        prediction = np.argmax(output)
        return self.labels[int(prediction)], output[int(prediction)]
