import traceback
from math import sin, pi
import socketserver
from random import Random
from threading import Thread


HOST, PORT = "localhost", 5003


class PWM:

    def __init__(self, frequency, duty):
        self.frequency = float(frequency)
        self.duty = float(duty)

        self._random = Random()

    def get_sample(self, period, sampling_frequency):
        loop = int(sampling_frequency / self.frequency)
        if loop == 0:
            return [1] * int(period * sampling_frequency)
        offset = self._random.randint(0, loop)
        width_1 = int(loop * self.duty)
        width_0 = loop - width_1

        data = ([1] * width_1 + [0] * width_0) * (int(period * sampling_frequency / loop) + 2)
        return data[offset: offset + int(period * sampling_frequency)]


class Wave:

    def __init__(self, signal_frequency):
        self.signal_frequency = float(signal_frequency)
        self._random = Random()

    def get_sample(self, period, sampling_frequency):
        offset = self._random.random() * 2 * pi
        for i in range(int(period * sampling_frequency)):
            yield sin(offset + 2 * pi * i * self.signal_frequency / sampling_frequency) * 0.5 + 0.5


class Direct:

    def get_sample(self, period, sampling_frequency):
        for _ in range(int(period * sampling_frequency)):
            yield 0.5


signal_generator = Direct()


def decoder_8_bit(sample):
    for value in sample:
        if value < 0:
            yield b'\x00'
        elif value >= 1:
            yield b'\xff'
        else:
            yield int(value * 255).to_bytes(1, 'big')


def decoder_comma(sample):
    for value in sample:
        yield f"{value},".encode()


class SamplesHandler(socketserver.BaseRequestHandler):

    def __init__(self, request, client_address, server):
        self.data = None

        super().__init__(request, client_address, server)

    def handle(self):
        while True:
            method, period, frequency = self.request.recv(1024).decode().split(",")
            period = float(period)
            frequency = float(frequency)
            print(f"data request. period: {period}, frequency: {frequency}. "
                  f"Signal: {signal_generator.__class__.__name__}")

            data = b''.join(decoder_8_bit(signal_generator.get_sample(period, frequency)))
            data_size = len(data).to_bytes(4, 'big')
            self.request.sendall(data_size + data)


class Server(Thread):

    daemon = True

    def run(self):
        with socketserver.TCPServer((HOST, PORT), SamplesHandler) as server:
            server.serve_forever()


signals = {
    "wave": Wave,
    "pwm": PWM,
    "direct": Direct,
}


def listen_configurator():
    global signal_generator

    while True:
        print('listen')
        signal_params = input()

        print('got')
        try:
            shape, *params = signal_params.split(",")
            signal_generator = signals[shape](*params)

        except Exception():
            traceback.print_exc()


if __name__ == "__main__":
    Server().start()
    listen_configurator()
