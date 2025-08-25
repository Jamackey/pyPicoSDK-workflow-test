"""None"""
from threading import Thread, Event

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from pypicosdk import psospa, CHANNEL, SAMPLE_RATE

av_channel = CHANNEL.A
SAMPLES = 1000
MAX_RANGE_V = 1
LED_LIST = ['A', 'B', 'C', 'D', 'AUX', 'AWG']

scope = psospa()


def setup_scope():
    """Sets up scope and buffers"""
    scope.open_unit()
    scope.set_channel(av_channel, range='1V')
    scope.set_simple_trigger(av_channel, auto_trigger=int(1E6))
    timebase = scope.sample_rate_to_timebase(10, SAMPLE_RATE.MSPS)
    buffer = scope.set_data_buffer(av_channel, SAMPLES)
    adc = scope.max_adc_value, -scope.min_adc_value
    return buffer, timebase, adc


def run_block(timebase, buffer, adc, stop: Event):
    """Runs block capture"""
    max_adc = adc[0]
    led_colour_list = (['green'] * 4) + ['yellow'] + ['red']
    scope.set_led_colours(LED_LIST, led_colour_list, [100] * 6)
    while not stop.is_set():
        scope.run_block_capture(timebase, SAMPLES)
        scope.get_values(SAMPLES)
        update_leds(buffer, max_adc)


def update_leds(buffer: np.ndarray, max_adc: int):
    """Update PSOSPA LEDs"""
    level = int((buffer.max()/max_adc) * 6)
    led_state_list = ['off'] * 6
    for i in range(level):
        led_state_list[i] = 'on'
    scope.set_led_states(LED_LIST, led_state_list)


def create_plot(buffer, adc):
    """Create pyplot animation plot"""
    fig, ax = plt.subplots()
    x = range(SAMPLES)
    ax.set_ylim(adc[1], adc[0])
    line, = ax.plot(x, buffer)
    return fig, line


def update_plot(_, line, buffer):
    """Update pyplot"""
    line.set_ydata(buffer)
    return [line]


def main():
    """Main loop function"""
    buffer, timebase, adc = setup_scope()
    fig, line = create_plot(buffer, adc)

    stop = Event()
    run_block_thread = Thread(
        target=run_block, args=[timebase, buffer, adc, stop])
    run_block_thread.start()

    _ = FuncAnimation(fig, update_plot, interval=100, blit=True,
                      fargs=[line, buffer], cache_frame_data=False)
    plt.show()

    stop.set()
    run_block_thread.join()


if __name__ == '__main__':
    main()
