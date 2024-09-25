import struct
import os
import pyaudio

import struct
import inspect


def namestr(obj, namespace):
    return [name for name in namespace if namespace[name] is obj]

class WavInfo:
    """Class for storing wav parameters to pass to pyaudio"""
    frame_rate: int
    num_channels: int
    sample_width: int
    wav_size: int
    format_tag: int

    def __init__(self, frame, verbose=False) -> float:
        assert (len(frame) == 44)
        assert (frame[0:4] == b'RIFF')
        wav_size = struct.unpack('I', frame[4:8])[0]
        assert (frame[8:12] == b'WAVE')
        assert (frame[12:16] == b'fmt ')
        assert (struct.unpack('I', frame[16:20])[0] == 16)
        fmt_tag, num_channels = struct.unpack('2h', frame[20:24])
        sample_rate, byte_rate = struct.unpack('2I', frame[24:32])
        block_align, bits_per_sample = struct.unpack('2h', frame[32:36])
        assert (byte_rate == block_align * sample_rate)
        assert (frame[36:40] == b'data')
        data_size = struct.unpack('I', frame[40:44])[0]
        assert (wav_size == data_size + 36)

        self.frame_rate = sample_rate
        self.num_channels = num_channels
        self.format_tag = fmt_tag
        self.sample_width = bits_per_sample // 8
        self.wav_size = wav_size

        if verbose:
            f = inspect.currentframe()
            for item in [wav_size, fmt_tag, num_channels, sample_rate, byte_rate, block_align, bits_per_sample, data_size]:
                print(
                    f"{__class__.__name__}: {namestr(item, f.f_locals)[0]} = {item}")

class SavingBufferWithStreaming:
    def __init__(self, do_streaming=True):
        self.data = b""
        self.bytes_to_read = None
        if do_streaming:
            self.p = pyaudio.PyAudio()
            os.environ['SDL_AUDIODRIVER'] = 'dsp'
            self.stream = None
        else:
            self.p = None

    def push(self, frame):
        WAV_HEADER_SIZE = 44
        leftover = None

        self.data += frame
        if len(self.data) < WAV_HEADER_SIZE:
            return leftover

        if not self.bytes_to_read:  # first batch
            header = WavInfo(frame[:WAV_HEADER_SIZE])
            self.bytes_to_read = header.wav_size + 8
            if self.p:
                self.stream = self.p.open(
                    format=2 if header.sample_width == 4 else self.p.get_format_from_width(
                        header.sample_width),
                    channels=header.num_channels,
                    rate=header.frame_rate,
                    output=True)
                self.stream.start_stream()
                if self.stream.is_active():
                    self.stream.write(frame[WAV_HEADER_SIZE:])
        if self.p:
            if self.stream.is_active():
                self.stream.write(frame)
        if len(self.data) > self.bytes_to_read:
            self.data, leftover = self.data[:self.bytes_to_read], self.data[self.bytes_to_read:]
        return leftover

    def is_closed(self):
        return len(self.data) == 0

    def close(self, out_file="received.wav"):
        if self.p:
            if self.stream.is_active():
                self.stream.stop_stream()
                self.stream.close()
            self.stream = None  # prepare for the next transmission

        with open(out_file, "wb") as f:
            f.write(self.data)

        self.data = b""  # prepare for the next transmission
        self.bytes_to_read = None

    def __exit__(self):
        if self.p:
            self.p.terminate()
