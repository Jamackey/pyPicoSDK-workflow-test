"""
This is a module that provides decoding for a UART serial protocol
"""
from dataclasses import dataclass
from typing import Literal, TypedDict, Unpack
import numpy as np
from skimage.filters import apply_hysteresis_threshold as hyst  # pylint: disable=E0611


@dataclass
class UARTData:
    """UART data class for storing and recieving UART data.

    Attributes:
        packet_start_index (list[int]): Indices where packets start.
        packet_end_index (list[int]): Indices where packets end.
        packet_data (list[int]): Raw packet data as a list of bytes.
        parity_bits (list[int]): Extracted parity bits for each packet.
        hyst_buffer (np.ndarray): Buffer after hysteresis processing.

        lower_thr (float): Lower threshold used in decoding. Defaults to 1.0.
        upper_thr (float): Upper threshold used in decoding. Defaults to 2.5.
        order (str): Bit order for decoding. Defaults to ``'lsb'``.
        parity (bool): Whether parity is enabled. Defaults to ``False``.
        packet_len (int): Expected packet length. Defaults to 10.

    Examples:
        >>> print(data.str)
        >>> # or
        >>> for i in data:
        >>>     print(i)
    """

    packet_start_index = []
    packet_end_index = []
    packet_data = []
    parity_bits = []
    hyst_buffer = np.empty(0)

    # Extra keyword arguments
    lower_thr: float = 1
    upper_thr: float = 2.5
    order: Literal['lsb', 'msb'] = 'lsb'
    parity: bool = False
    packet_len: int = 10

    class _Kwargs(TypedDict, total=False):
        "Kwargs typehint"
        lower_thr: float
        upper_thr: float
        order: Literal['lsb', 'msb']
        parity: bool
        packet_len: int

    @property
    def dec(self) -> list:
        """`list[int]`: Return data as decimal list"""
        return self.packet_data

    @property
    def ascii(self):
        """`List[str]`: Return data as ascii list"""
        return [chr(byte) for byte in self.packet_data]

    @property
    def str(self):
        """`list[str]`: Return data as ascii string"""
        return bytes(self.packet_data).decode()

    @property
    def bin(self):
        """`list[byte]`: Return data as binary list"""
        return [bin(byte) for byte in self.packet_data]

    @property
    def hexi(self):
        "`list[hex]`: Return data as hexidecimal list"
        return [hex(byte) for byte in self.packet_data]

    def __str__(self):
        return self.str

    def __iter__(self):
        return iter(self.dec)


def decode_uart(
    buffer: np.ndarray,
    baud: int,
    interval: float,
    **kwargs: Unpack[UARTData._Kwargs]
) -> UARTData:
    """
    Decode UART data from an oscilloscope data buffer.
    The data must converted into voltage (V) and seconds (s)

    Args:
        buffer (np.ndarray): Captured oscilloscope voltage (V) data in a numpy array.
        baud (int): Baud of the UART signal.
        interval (float): Interval between each sample in seconds (s).

    Other Parameters:
        lower_thr (float, optional): Lower threshold to apply hysteresis. Defaults to 1.
        upper_thr (float, optional): Upper threshold to apply hysteresis. Defaults to 2.5.
        order (str, optional): Bit order 'lsb' or 'msb'. Defaults to 'lsb'.
        parity (bool, optional): Parity bit included. Defaults to False.
        packet_len (int, optional): Length of the packet (including parity). Defaults to 10.

    Returns:
        UARTData: UARTData class containing data and packet start and end indexes.
    """
    # Create data class to return
    uart = UARTData(**kwargs)

    # Get data word length
    data_len = uart.packet_len - (3 if uart.parity else 2)

    # Apply hysteresis to the buffer
    uart.hyst_buffer = hyst(buffer, uart.lower_thr, uart.upper_thr)

    # Get sample bit width
    baud_interval = int((1/baud) // interval)
    half_baud_interval = int(baud_interval // 2)

    # Get edges from data
    edge_buffer = np.diff(uart.hyst_buffer)
    edge_index_arr = np.where(edge_buffer)[0]

    # Find each start/stop bit and get data
    for edge_index in edge_index_arr:

        # Ignore edges before last stop bit
        try:
            if edge_index < uart.packet_end_index[-1]:
                continue
        except IndexError:
            pass

        # Get value at start bit
        start_half_index = edge_index + half_baud_interval
        start_bit_val = uart.hyst_buffer[start_half_index]

        # Check value at stop bit
        stop_half_index = start_half_index + (9 * baud_interval)
        stop_bit_val = uart.hyst_buffer[stop_half_index]

        # Check if start and stop value are correct
        if bool(start_bit_val) is False and bool(stop_bit_val) is True:
            uart.packet_start_index.append(edge_index)
            uart.packet_end_index.append(stop_half_index)

        # Retrieve the data
        data_packet = []
        for d_index in range(data_len):
            bit_index = start_half_index + baud_interval + (d_index * baud_interval)
            bit_value = uart.hyst_buffer[bit_index]
            data_packet.append(bit_value)

        # Flip order if LSB order is set
        if uart.order.lower() == 'lsb':
            data_packet = np.flip(data_packet)

        # Convert the data from true/false array to an int
        data_packet = int("".join(map(str, np.where(data_packet, 1, 0))), 2)

        # Add data to uart class
        uart.packet_data.append(data_packet)

        # Check parity bits
        if uart.parity:
            uart.parity_bits.append(uart.hyst_buffer[stop_half_index - baud_interval])

    return uart
