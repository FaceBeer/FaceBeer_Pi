import io
import time

from PIL import Image
from picamera import PiCamera
import numpy as np

import RPi.GPIO as GPIO
import Adafruit_ADS1x15


class Camera:
    def __init__(self):
        self.camera = PiCamera
        self.img_width = 1920
        self.img_height = 1080

    def get_frame(self):
        stream = io.BytesIO()
        with self.camera() as camera:
            camera.resolution = (self.img_width, self.img_height)
            camera.start_preview()
            time.sleep(2)
            camera.capture(stream, format='jpeg')

        stream.seek(0)
        img = Image.open(stream)
        return img
 

class Button:
    def __init__(self):
        self.button_pin = 23
        GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def get(self):
        """
        Gets the state of the button
        :return: True if pressed
        """
        return not GPIO.input(self.button_pin)

class MQ3:
    def __init__(self):
        # Setup MQ-3 Sensor
        self.adc = Adafruit_ADS1x15.ADS1115()
        self.GAIN = 1

    def read(self):
        raw = self.adc.read_adc(0, gain=self.GAIN)
        bac = self.raw_to_bac(raw)
        return bac

    def raw_to_bac(self, x):
        # don't wanna return a negative, apply ReLu
        return max(7E-06*x - 0.037, 0)
