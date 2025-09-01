"""
Example of decoding UART data from a UART signal captured
using run_simple_block_capture() in the main pypicosdk package.

The data is captured in volts (V) and seconds (s).
"""
import os
import numpy as np
from matplotlib import pyplot as plt
from pypicosdk.decoder.uart import decode_uart

FILENAME = 'uart_data.npy'
BAUD = 9600


def get_data():
    """Extract the data from uart_data.npy file"""
    # Find and open the uart_data.npy file
    filepath = os.path.dirname(__file__)
    numpy_data = np.load(os.path.join(filepath, FILENAME))

    # Get the buffer from saved data
    buffer: np.ndarray = numpy_data[1]

    # Calculate the sample_interval from time_axis
    time_axis: np.ndarray = numpy_data[0]
    sample_interval = time_axis[1] - time_axis[0]
    return buffer, sample_interval


def plot_data(uart_data, buffer):
    """Plot data to pyplot"""
    # Plot upper and lower thresholds
    plt.axhline(uart_data.lower_thr, c='red', ls=':')
    plt.axhline(uart_data.upper_thr, c='red', ls=':')

    # Plot packet start and stop lines
    for x, y in zip(uart_data.packet_start_index, uart_data.packet_end_index):
        plt.axvline(x, c='green', ls=':')
        plt.axvline(y, c='turquoise', ls=':')

    # Plot buffer data
    plt.plot(buffer)
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude (V)")
    plt.grid(True)
    plt.show()


def main():
    """Main function"""
    buffer, sample_interval = get_data()
    uart_data = decode_uart(buffer, BAUD, sample_interval)
    plot_data(uart_data, buffer)


if __name__ == '__main__':
    main()
