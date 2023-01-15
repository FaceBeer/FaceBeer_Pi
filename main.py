from enum import Enum
import time
from argparse import ArgumentParser

from picamera import PiCamera
from multiprocessing import Process
from model import Model
from sensors import Camera, Button, MQ3
from client import Client
from display import Display


class State(Enum):
    INITIAL = 0
    SELFIE = 1
    ML = 2
    IDENTIFIED = 3
    BLOW = 4
    DONE = 5


class Session:
    def __init__(self, threshold=0.75):
        self.state = State.INITIAL
        self.displayed_text = ""
        self.image = None
        self.name = None
        self.confidence = None
        self.guest_threshold = threshold
        self.reset_start_time = None
        self.bac_readings = []
        self.reading_bac_start_time = None
        self.bac = None
        self.process = None

    def set_state(self, state):
        self.state = state
        print("Set state to", state.name)
        if self.process is not None and self.process.is_alive():
            self.process.kill()


class Controller:
    def __init__(self, session: Session):
        self.sess = session
        self.button = Button()
        self.camera = Camera()
        self.mqp3 = MQ3()
        self.model = Model()
        self.client = Client()
        self.display = Display()
        time.sleep(2)

    def display_text(self, text):
        if self.sess.displayed_text != text:
            # text not yet displayed
            self.display.clear_display()
            self.sess.process = Process(target=self.display.display_write, args=[text])
            self.sess.process.start()
            self.sess.displayed_text = text

    def run(self):
        print("Starting main loop")
        while True:  # main loop for state machine
            if self.sess.state == State.INITIAL:
                text = "FaceBeer Press for selfie"
                self.display_text(text)
                if self.button.get():
                    print("Selfie button pressed")
                    # pressed, time to take the selfie
                    self.sess.set_state(State.SELFIE)
            elif self.sess.state == State.SELFIE:
                text = "Say Cheese!"
                self.display_text(text)
                print("Taking picture")
                self.sess.image = self.camera.get_frame()
                # image grabbed, time to process
                print("Picture taken")
                self.sess.set_state(State.ML)
            elif self.sess.state == State.ML:
                text = "..."
                self.display_text(text)
                print("Beginning ML")
                self.sess.name, self.sess.confidence = self.model.predict(self.sess.image)
                self.sess.name = self.sess.name.title()
                print(f"Original name: {self.sess.name}, confidence: {self.sess.confidence:.3f}")
                if self.sess.confidence < self.sess.guest_threshold:
                    # uncertain about who this is, assume it's a "guest"
                    self.sess.name = "Guest"
                    self.sess.confidence = 1.0 - self.sess.confidence  # if it's 60% emre, then it's 40% guest
                print(f"Final name: {self.sess.name}, confidence: {self.sess.confidence:.3f}. You have 10s to confirm.")
                self.sess.reset_start_time = time.time()
                self.sess.set_state(State.IDENTIFIED)
            elif self.sess.state == State.IDENTIFIED:
                text = f"{self.sess.name}? Hold button and blow Resetting in 10s"
                self.display_text(text)
                if time.time() - self.sess.reset_start_time > 10:
                    # user didn't press button in 10 seconds, assume model was wrong
                    print("Wrong name, resetting")
                    self.sess.set_state(State.INITIAL)
                    self.sess = Session()
                elif self.button.get():
                    # button pressed, assume user is blowing
                    print("Blow button pressed")
                    self.sess.reading_bac_start_time = time.time()
                    self.sess.set_state(State.BLOW)
            elif self.sess.state == State.BLOW:
                text = "Blow for 10s"
                self.display_text(text)
                if time.time() - self.sess.reading_bac_start_time < 10:
                    self.sess.bac_readings.append(self.mqp3.read())
                else:
                    self.sess.bac = round(max(self.sess.bac_readings), 3)
                    self.client.add_row(self.sess.name, self.sess.bac)
                    self.sess.set_state(State.DONE)
                    print("Max BAC found", self.sess.bac)
            elif self.sess.state == State.DONE:
                text = f"BAC: {self.sess.bac} Press to reset"
                self.display_text(text)
                if self.button.get():
                    print("Done button pressed, resetting")
                    self.sess.set_state(State.INITIAL)
                    self.sess = Session()
                    time.sleep(2)
            else:
                print("ERROR OCCURRED")


def main():
    parser = ArgumentParser()
    parser.add_argument("-t", "--threshold", default=0.75)
    args = parser.parse_args()
    threshold = args.threshold
    session = Session(threshold)
    controller = Controller(session)
    controller.run()


if __name__ == "__main__":
    main()
