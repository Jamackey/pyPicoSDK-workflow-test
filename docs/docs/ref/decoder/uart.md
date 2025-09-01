# UART Decoding

This page displays how to decode UART data from a single channel buffer.

!!! Important
    The data must be in or converted to volts (V) and seconds (s) to correctly process

## Example
Below is an example of how to decode the UART buffer.
This assume that `ch_a_buffer` is a numpy array containing a **single** channel of data from
either `run_simple_block_capture(...)` or `set_data_buffer(...)`. This will not work with a
channel buffer `dict` that hasn't been split into channels.

```python
from pypicosdk.decoder.uart import decode_uart

...

ch_a_buffer = ...  # single 1d numpy array of samples
baud = 9600
sample_interval_s = 0.5e-6 # (0.5 us)
data = decode_uart(ch_a_buffer, baud, sample_interval_s)
print(data)
```

## Reference

::: uart.decode_uart
    options:
        show_bases: false
        show_symbol_type_toc: true
        summary: true
        show_root_heading: true


::: uart.UARTData
    options:
        show_symbol_type_toc: true
        show_root_heading: true
