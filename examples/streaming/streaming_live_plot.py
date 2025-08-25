"""
Note: RACE CONDITION!
The data retrieved from get_streaming data *NEEDS* to be
    larger than the captured data.
    If it's smaller, the live plot will lag behind the data.
    If it's larger, the streaming will ignore the empty buffers.

Threading:
    The main streaming is handled in a thread while loop.
    This is so that the matplotlib animation can be the main loop,
    so the frame update interval doesn't control the retrieval of data
    removing any race condition from the animation.
"""


import threading
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
import pypicosdk as psdk
from pypicosdk.streaming import StreamingScope

# Capture configuration
channel = psdk.CHANNEL.A
SAMPLES = int(1E9)  # Samples to store in PicoScope
STREAMING_SAMPLES = 1000  # Samples to populate buffer in PicoScope
INTERVAL = 1
pico_unit = psdk.PICO_TIME_UNIT.US
MAX_SAMPLES = 10000000  # Samples to store in python buffer
DISPLAY_SAMPLES = 10000  # Samples to display in graph
DISPLAY_RATIO = MAX_SAMPLES//DISPLAY_SAMPLES

sps_list = np.zeros(100, dtype=np.int64)
sps_index = [0]


class TimeAxis:
    """None"""
    timebase: int
    time_axis: np.ndarray
    time_axis_ratio: np.ndarray


time_class = TimeAxis()

fig = plt.figure()
axis = plt.axes(xlim=(0, DISPLAY_RATIO),
                ylim=(-32000, 32000))
x = np.arange(DISPLAY_SAMPLES)  # Predefined x-data of length 10
line, = axis.plot(x, np.zeros_like(x), lw=2)  # Initialize with zeros
axis.set_xlabel("Time (ns)")
axis.set_ylabel("ADC Count")


def setup_scope():
    """None"""
    scope = psdk.psospa()
    scope.open_unit()
    scope.set_siggen(frequency=1_000_000, pk2pk=1.6,
                     wave_type=psdk.WAVEFORM.TRIANGLE)
    scope.set_channel(channel=psdk.CHANNEL.A, range=psdk.RANGE.V1)
    time_class.timebase = \
        scope.interval_to_timebase(INTERVAL, psdk.TIME_UNIT.MS)
    time_class.time_axis, _ = \
        psdk.convert_time_axis(
            scope.get_time_axis(time_class.timebase, MAX_SAMPLES), 'ns', 's')
    time_class.time_axis_ratio = time_class.time_axis[::DISPLAY_RATIO]
    # scope.set_simple_trigger(channel=psdk.CHANNEL.A, threshold_mv=0)
    return scope


def streaming_thread(stream: StreamingScope):
    """None"""
    stream.run_streaming_while()


def animate(_, stream: StreamingScope):
    """None"""
    # print(f"{stream.current_sps / 1e6:.2f} MS/s")
    sps_list[sps_index] = stream.current_sps
    sps_index[0] = (sps_index[0] + 1) % sps_list.shape[0]
    # print(f"{sps_list.mean() / 1e6:.2f} MS/s")

    # data = stream.buffer_array[::DISPLAY_RATIO]
    # time_axis = time_class.time_axis[::DISPLAY_RATIO]
    # line.set_data(time_axis, data)
    if len(stream.buffer_array) >= MAX_SAMPLES:
        data = stream.buffer_array[-MAX_SAMPLES::DISPLAY_RATIO]
        line.set_ydata(data)
    return [line]


def main():
    """None"""
    scope = setup_scope()
    stream = StreamingScope(scope)
    stream.config_streaming(channel, SAMPLES, INTERVAL, pico_unit,
                            MAX_SAMPLES)

    th = threading.Thread(target=streaming_thread, args=[stream])
    th.start()

    _ = FuncAnimation(fig, animate, frames=500, fargs=(stream, ), interval=20,
                      blit=True)
    plt.show()

    stream.stop()
    th.join()

    scope.close_unit()


if __name__ == '__main__':
    main()
