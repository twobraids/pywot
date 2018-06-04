import RPi.GPIO as GPIO

WHITE = 17
ORANGE = 22
BLUE = 23
THERMOSTAT = 18

ON = GPIO.LOW
OFF = GPIO.HIGH

class StoveControllerImplementation:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(WHITE, GPIO.OUT)
        GPIO.setup(ORANGE, GPIO.OUT)
        GPIO.setup(BLUE, GPIO.OUT)
        GPIO.setup(THERMOSTAT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.set_off()

    def set_on_high(self):
        GPIO.output(WHITE, ON)
        GPIO.output(ORANGE, ON)
        GPIO.output(BLUE, OFF)

    def set_on_medium(self):
        GPIO.output(WHITE, ON)
        GPIO.output(ORANGE, OFF)
        GPIO.output(BLUE, OFF)

    def set_on_low(self):
        GPIO.output(WHITE, ON)
        GPIO.output(ORANGE, OFF)
        GPIO.output(BLUE, ON)

    def set_off(self):
        GPIO.output(WHITE, OFF)
        GPIO.output(ORANGE, OFF)
        GPIO.output(BLUE, OFF)

    def shutdown(self):
        GPIO.cleanup()

    def get_thermostat_state(self):
        return not GPIO.input(THERMOSTAT)


