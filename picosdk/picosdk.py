import ctypes
import os

from .error_list import ERROR_STRING
from .constants import *
from .version import VERSION

# Exceptions
class PicoSDKNotFoundException(Exception):
    pass

class PicoSDKException(Exception):
    pass


# General Functions
def _legacy_get_lib_path() -> str:    
    """
    Checks for and returns the PicoSDK lib location from Program Files.

    Returns:
        str: File path to PicoSDK folder.

    Raises:
        PicoSDKNotFoundException: If the PicoSDK library is not found.
    """
    program_files = os.environ.get("ProgramFiles")
    lib_location = os.path.join(program_files, "Pico Technology/SDK/lib")
    if not os.path.exists(lib_location):
        raise PicoSDKNotFoundException("PicoSDK is not found at 'Program Files/Pico Technology/SDK/lib'")
    return lib_location

def _get_lib_path() -> str:
    package_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(package_dir, "lib")


# PicoScope Classes
class PicoScopeBase:
    """PicoScope base class including common SDK and python modules and functions"""
    # Class Functions
    def __init__(self):
        self.handle = ctypes.c_short()
        self.range = {}
        self.resolution = None
        self.max_adc_value = None
        self.min_adc_value = None
    
    def __exit__(self):
        self.close_unit()

    def __del__(self):
        self.close_unit()

    # General Functions
    def _get_attr_function(self, function_name: str) -> ctypes.CDLL:
        """
        Returns ctypes function based on sub-class prefix name.

        For example, `_get_attr_function("OpenUnit")` will return `self.dll.ps####aOpenUnit()`.

        Args:
            function_name (str): PicoSDK function name, e.g., "OpenUnit".

        Returns:
            ctypes.CDLL: CDLL function for the specified name.
        """
        return getattr(self.dll, self._unit_prefix_n + function_name)
    
    def _error_handler(self, status: int) -> None:
        """
        Checks status code against error list; raises an exception if not 0.

        Errors such as `SUPPLY_NOT_CONNECTED` are returned as warnings.

        Args:
            status (int): Returned status value from PicoSDK.

        Raises:
            PicoSDKException: Pythonic exception based on status value.
        """
        error_code = ERROR_STRING[status]
        if status != 0:
            if status in [POWER_SOURCE.SUPPLY_NOT_CONNECTED]:
                print('WARNING: Power supply not connected')
                return
            self.close_unit()
            raise PicoSDKException(error_code)
        return
    
    def _call_attr_function(self, function_name:str, *args) -> int:
        """
        Calls a specific attribute function with the provided arguments.

        Args:
            function_name (str): PicoSDK function suffix.

        Returns:
            int: Returns status integer of PicoSDK dll.
        """
        attr_function = self._get_attr_function(function_name)
        status = attr_function(*args)
        self._error_handler(status)
        return status

    # General PicoSDK functions    
    def _open_unit(self, serial_number:int=None, resolution:RESOLUTION=0) -> None:
        """
        Opens PicoScope unit.

        Args:
            serial_number (int, optional): Serial number of specific unit, e.g., JR628/0017.
            resolution (RESOLUTION, optional): Resolution of device. 
        """

        if serial_number is not None:
            serial_number = serial_number.encode()
        self._call_attr_function(
            'OpenUnit',
            ctypes.byref(self.handle),
            serial_number, 
            resolution
        )
        self.resolution = resolution
    
    def close_unit(self) -> int:
        """
        Closes the PicoScope device and releases the hardware handle.

        This calls the PicoSDK `CloseUnit` function to properly disconnect from the device.

        Returns:
                None
        """

        self._get_attr_function('CloseUnit')(self.handle)

    def is_ready(self) -> None:
        """
        Blocks execution until the PicoScope device is ready.

        Continuously calls the PicoSDK `IsReady` function in a loop, checking if
        the device is prepared to proceed with data acquisition.

        Returns:
                None
        """

        ready = ctypes.c_int16()
        attr_function = getattr(self.dll, self._unit_prefix_n + "IsReady")
        while True:
            status = attr_function(
                self.handle, 
                ctypes.byref(ready)
            )
            self._error_handler(status)
            if ready.value != 0:
                break
    
    # Get information from PicoScope
    def get_unit_info(self, unit_info: UNIT_INFO) -> str:
        """
        Get specified information from unit. Use UNIT_INFO.XXXX or integer.

        Args:
            unit_info (UNIT_INFO): Specify information from PicoScope unit i.e. UNIT_INFO.PICO_BATCH_AND_SERIAL.

        Returns:
            str: Returns data from device.
        """
        string = ctypes.create_string_buffer(16)
        string_length = ctypes.c_int16(32)
        required_size = ctypes.c_int16(32)
        status = self._call_attr_function(
            'GetUnitInfo',
            self.handle,
            string,
            string_length,
            ctypes.byref(required_size),
            ctypes.c_uint32(unit_info)
        )
        return string.value.decode()
    
    def get_unit_serial(self) -> str:
        """
        Get and return batch and serial of unit.

        Returns:
                str: Returns serial, e.g., "JR628/0017".
        """
        return self.get_unit_info(UNIT_INFO.PICO_BATCH_AND_SERIAL)
    
    def _get_timebase(self, timebase: int, samples: int, segment:int=0) -> dict:
        """
        This function calculates the sampling rate and maximum number of 
        samples for a given timebase under the specified conditions.

        Args:
                timebase (int): Selected timebase multiplier (refer to programmer's guide).
                samples (int): Number of samples.
                segment (int, optional): The index of the memory segment to use.

        Returns:
                dict: Returns interval (ns) and max samples as a dictionary.
        """
        time_interval_ns = ctypes.c_double()
        max_samples = ctypes.c_uint64()
        attr_function = getattr(self.dll, self._unit_prefix_n + 'GetTimebase')
        status = attr_function(
            self.handle,
            timebase,
            samples,
            ctypes.byref(time_interval_ns),
            ctypes.byref(max_samples),
            segment
        )
        self._error_handler(status)
        return {"Interval(ns)": time_interval_ns.value, 
                "Samples":          max_samples.value}
    
    def _get_timebase_2(self, timebase: int, samples: int, segment:int=0):
        """
        Calculates the sampling rate and maximum number of samples for a given
        timebase under the specified conditions.

        Args:
                timebase (int): Selected timebase multiplier (refer to programmer's guide).
                samples (int): Number of samples.
                segment (int, optional): Index of the memory segment to use.

        Returns:
                dict: Dictionary containing:
                        - 'interval' (ns): Time interval between samples.
                        - 'max_samples': Maximum number of samples.
        """
        time_interval_ns = ctypes.c_float()
        max_samples = ctypes.c_int32()
        attr_function = getattr(self.dll, self._unit_prefix_n + 'GetTimeBase2')
        status = attr_function(
            self.handle,
            timebase,
            samples,
            ctypes.byref(time_interval_ns),
            ctypes.byref(max_samples),
            segment
        )
        self._error_handler(status)
        return {"Interval(ns)": time_interval_ns.value, 
                "Samples":          max_samples.value}
    
    def _get_adc_limits(self) -> tuple:
        """
        Gets the ADC limits for specified devices.

        Currently tested on: 6000a.

        Returns:
                tuple: (minimum value, maximum value)

        Raises:
                PicoSDKException: If device hasn't been initialized.
        """
        if self.resolution is None:
            raise PicoSDKException("Device has not been initialized, use open_unit()")
        min_value = ctypes.c_int32()
        max_value = ctypes.c_int32()
        self._call_attr_function(
            'GetAdcLimits',
            self.handle,
            self.resolution,
            ctypes.byref(min_value),
            ctypes.byref(max_value)
        )
        return min_value.value, max_value.value
    
    def _get_maximum_adc_value(self) -> int:
        """
        Gets the ADC limits for specified devices.

        Currently tested on: 5000a.

        Returns:
                int: Maximum ADC value.
        """
        max_value = ctypes.c_int16()
        self._call_attr_function(
            'MaximumValue',
            self.handle,
            ctypes.byref(max_value)
        )
        return max_value.value
    
    # Data conversion ADC/mV & ctypes/int 
    def mv_to_adc(self, mv:float, channel_range:int) -> int:
        """
        Converts a millivolt (mV) value to an ADC value based on the device's
        maximum ADC range.

        Args:
                mv (float): Voltage in millivolts to be converted.
                channel_range (int): Range of channel in millivolts i.e. 500 mV.

        Returns:
                int: ADC value corresponding to the input millivolt value.
        """
        channel_range_mv = RANGE_LIST[channel_range]
        return int((mv / channel_range_mv) * self.max_adc_value)
    
    def adc_to_mv(self, adc: int, channel_range: int):
        "Converts ADC value to mV - based on maximum ADC value"
        channel_range_mv = float(RANGE_LIST[channel_range])
        return (float(adc) / float(self.max_adc_value)) * channel_range_mv
    
    def buffer_adc_to_mv(self, buffer: list, channel: str) -> list:
        """Converts an ADC buffer list to mV list"""
        return [self.adc_to_mv(sample, self.range[channel]) for sample in buffer]
    
    def buffer_adc_to_mv_multiple_channels(self, channels_buffer: dict) -> dict:
        "Converts dict of multiple channels adc values to millivolts (mV)"
        for channel in channels_buffer:
            channels_buffer[channel] = self.buffer_adc_to_mv(channels_buffer[channel], channel)
        return channels_buffer
    
    def buffer_ctypes_to_list(self, ctypes_list):
        "Converts a ctype dataset into a python list of samples"
        return [sample for sample in ctypes_list]
    
    def buffer_ctype_to_list_for_multiple_channels(self, channels_buffer):
        "Takes a ctypes channel dictionary buffer and converts into a integer array."
        for channel in channels_buffer:
            channels_buffer[channel] = self.buffer_ctypes_to_list(channels_buffer[channel])
        return channels_buffer

    # Set methods for PicoScope configuration    
    def _change_power_source(self, state: POWER_SOURCE) -> 0:
        """
        Change the power source of a device to/from USB only or DC + USB.

        Args:
                state (POWER_SOURCE): Power source variable (i.e. POWER_SOURCE.SUPPLY_NOT_CONNECTED).
        """
        self._call_attr_function(
            'ChangePowerSource',
            self.handle,
            state
        )

    def _set_channel_on(self, channel, range, coupling=COUPLING.DC, offset=0.0, bandwidth=BANDWIDTH_CH.FULL):
        """Sets a channel to ON at a specified range (6000E)"""
        self.range[channel] = range
        attr_function = getattr(self.dll, self._unit_prefix_n + 'SetChannelOn')
        status = attr_function(
            self.handle,
            channel,
            coupling,
            range,
            ctypes.c_double(offset),
            bandwidth
        )
        return self._error_handler(status)
    
    def _set_channel_off(self, channel):
        """Sets a channel to OFF (6000E)"""
        attr_function = getattr(self.dll, self._unit_prefix_n + 'SetChannelOff')
        status = attr_function(
            self.handle, 
            channel
        )
        return self._error_handler(status)
    
    def _set_channel(self, channel, range, enabled=True, coupling=COUPLING.DC, offset=0.0):
        """Set a channel ON with a specified range (5000D)"""
        self.range[channel] = range
        status = self.dll.ps5000aSetChannel(
            self.handle,
            channel,
            enabled,
            coupling,
            range,
            ctypes.c_float(offset)
        )
        return self._error_handler(status)
    
    def set_simple_trigger(self, channel, threshold_mv, enable=True, direction=TRIGGER_DIR.RISING, delay=0, auto_trigger_ms=3000):
        """Sets up a simple trigger from a specified channel and threshold in mV"""
        threshold_adc = self.mv_to_adc(threshold_mv, self.range[channel])
        attr_function = getattr(self.dll, self._unit_prefix_n + 'SetSimpleTrigger')
        status = attr_function(
            self.handle,
            enable,
            channel,
            threshold_adc,
            direction,
            delay,
            auto_trigger_ms
        )
        return self._error_handler(status)
    
    def set_data_buffer_for_enabled_channels():
        raise NotImplemented("Method not yet available for this oscilloscope")
    
    def _set_data_buffer_ps5000a(self, channel, samples, segment=0, ratio_mode=0):
        """Set data buffer (5000D)"""
        buffer = (ctypes.c_int16 * samples)
        buffer = buffer()
        self._call_attr_function(
            'SetDataBuffer',
            self.handle,
            channel,
            ctypes.byref(buffer),
            samples,
            segment,
            ratio_mode
        )
        return buffer
    
    def _set_data_buffer_ps6000a(self, channel, samples, segment=0, 
                                 datatype=DATA_TYPE.INT16_T, ratio_mode=RATIO_MODE.RAW, 
                                 action=ACTION.CLEAR_ALL | ACTION.ADD) -> ctypes.Array:
        """
        Allocates and assigns a data buffer for a specified channel on the 6000A series.

        Args:
            channel (int): The channel to associate the buffer with (e.g., CHANNEL.A).
            samples (int): Number of samples to allocate in the buffer.
            segment (int, optional): Memory segment to use. 
            datatype (DATA_TYPE, optional): C data type for the buffer (e.g., INT16_T). 
            ratio_mode (RATIO_MODE, optional): Downsampling mode. 
            action (ACTION, optional): Action to apply to the data buffer (e.g., CLEAR_ALL | ADD).

        Returns:
            ctypes.Array: A ctypes array that will be populated with data during capture.

        Raises:
            PicoSDKException: If an unsupported data type is provided.
        """
        if datatype == DATA_TYPE.INT8_T:     buffer = (ctypes.c_int8 * samples)
        elif datatype == DATA_TYPE.INT16_T:  buffer = (ctypes.c_int16 * samples)
        elif datatype == DATA_TYPE.INT32_T:  buffer = (ctypes.c_int32 * samples)
        elif datatype == DATA_TYPE.INT64_T:  buffer = (ctypes.c_int64 * samples)
        elif datatype == DATA_TYPE.UINT32_T: buffer = (ctypes.c_uint32 * samples)
        else: raise PicoSDKException("Invalid datatype selected for buffer")

        buffer = buffer()
        self._call_attr_function(
            'SetDataBuffer',
            self.handle,
            channel,
            ctypes.byref(buffer),
            samples,
            datatype,
            segment,
            ratio_mode,
            action
        )
        return buffer
    
    # Run functions
    def run_block_capture(self, timebase, samples, pre_trig_percent=50, segment=0) -> int:
        """
        Runs a block capture using the specified timebase and number of samples.

        This sets up the PicoScope to begin collecting a block of data, divided into
        pre-trigger and post-trigger samples. It uses the PicoSDK `RunBlock` function.

        Args:
                timebase (int): Timebase value determining sample interval (refer to PicoSDK guide).
                samples (int): Total number of samples to capture.
                pre_trig_percent (int, optional): Percentage of samples to capture before the trigger. 
                segment (int, optional): Memory segment index to use.

        Returns:
                int: Estimated time (in milliseconds) the device will be busy capturing data.
        """

        pre_samples = int((samples * pre_trig_percent) / 100)
        post_samples = int(samples - pre_samples)
        time_indisposed_ms = ctypes.c_int32()
        self._call_attr_function(
            'RunBlock',
            self.handle,
            pre_samples,
            post_samples,
            timebase,
            ctypes.byref(time_indisposed_ms),
            segment,
            None,
            None
        )
        return time_indisposed_ms.value
    
    def get_values(self, samples, start_index=0, segment=0, ratio=0, ratio_mode=RATIO_MODE.RAW) -> int:
        """
        Retrieves a block of captured samples from the device once it's ready.

        This function should be called after confirming the device is ready using `is_ready()`.
        It invokes the underlying PicoSDK `GetValues` function to read the data into memory.

        Args:
                samples (int): Number of samples to retrieve.
                start_index (int, optional): Starting index in the buffer.
                segment (int, optional): Memory segment index to retrieve data from.
                ratio (int, optional): Downsampling ratio.
                ratio_mode (RATIO_MODE, optional): Ratio mode for downsampling. 

        Returns:
                int: Actual number of samples retrieved.
        """

        self.is_ready()
        total_samples = ctypes.c_uint32(samples)
        overflow = ctypes.c_int16()
        self._call_attr_function(
            'GetValues',
            self.handle, 
            start_index,
            ctypes.byref(total_samples),
            ratio,
            ratio_mode,
            segment,
            ctypes.byref(overflow)
        )
        return total_samples.value
    
    def run_simple_block_capture(self, timebase, samples) -> dict:
        raise NotImplementedError("This method is not yet implimented in this PicoScope")
    
    # Siggen Functions
    def _siggen_apply(self, enabled=1, sweep_enabled=0, trigger_enabled=0, 
                     auto_clock_optimise_enabled=0, override_auto_clock_prescale=0) -> dict:
        """
        Sets the signal generator running using parameters previously configured.

        Args:
                enabled (int, optional): SigGen Enabled, 
                sweep_enabled (int, optional): Sweep Enabled,
                trigger_enabled (int, optional): SigGen trigger enabled,
                auto_clock_optimise_enabled (int, optional): Auto Clock Optimisation,
                override_auto_clock_prescale (int, optional): Override Clock Prescale,

        Returns:
                dict: Returns dictionary of the actual achieved values.
        """
        freq = ctypes.c_double()
        stop_freq = ctypes.c_double()
        freq_incr = ctypes.c_double()
        dwell_time = ctypes.c_double()
        self._call_attr_function(
            'SigGenApply',
            self.handle,
            enabled,
            sweep_enabled,
            trigger_enabled,
            auto_clock_optimise_enabled,
            override_auto_clock_prescale,
            ctypes.byref(freq),
            ctypes.byref(stop_freq),
            ctypes.byref(freq_incr),
            ctypes.byref(dwell_time)
        )
        return {'Freq': freq.value,
                'StopFreq': stop_freq.value,
                'FreqInc': freq_incr.value,
                'dwelltime': dwell_time.value}
    
    def _siggen_set_frequency(self, frequency:int) -> None:
        """
        Set frequency of SigGen in Hz.

        Args:
                frequency (int): Frequency in Hz.
        """   
        self._call_attr_function(
            'SigGenFrequency',
            self.handle,
            frequency
        )
    
    def _siggen_set_range(self, pk2pk:int, offset=0):
        """
        Set mV range of SigGen (6000A).

        Args:
                pk2pk (int): Peak to peak of signal in mV.
                offset (int, optional): Offset of signal in mV.
        """      
        self._call_attr_function(
            'SigGenRange',
            self.handle,
            pk2pk,
            offset
        )
    
    def _siggen_set_waveform(self, wavetype: WAVEFORM):
        """
        Set waveform type for SigGen (6000A).

        Args:
                wavetype (WAVEFORM): Waveform type i.e. WAVEFORM.SINE.
        """
        self._call_attr_function(
            'SigGenRange',
            self.handle,
            wavetype,
            0,
            0
        )


class ps6000a(PicoScopeBase):
    """PicoScope 6000 (A) API specific functions"""
    dll = ctypes.CDLL(os.path.join(_get_lib_path(), "ps6000a.dll"))
    _unit_prefix_n = "ps6000a"

    def open_unit(self, serial_number:str=None, resolution:RESOLUTION = 0) -> None:
        """
        Open PicoScope unit.

        Args:
                serial_number (str, optional): Serial number of device.
                resolution (RESOLUTION, optional): Resolution of device.
        """
        super()._open_unit(serial_number, resolution)
        self.min_adc_value, self.max_adc_value =super()._get_adc_limits()
    
    def set_channel(self, channel:CHANNEL, range:RANGE, enabled=True, coupling:COUPLING=COUPLING.DC, 
                    offset:float=0.0, bandwidth=BANDWIDTH_CH.FULL) -> None:
        """
        Enable/disable a channel and specify certain variables i.e. range, coupling, offset, etc.

        Args:
                channel (CHANNEL): Channel to setup.
                range (RANGE): Voltage range of channel.
                enabled (bool, optional): Enable or disable channel.
                coupling (COUPLING, optional): AC/DC/DC 50 Ohm coupling of selected channel.
                offset (int, optional): Analog offset in volts (V) of selected channel.
                bandwidth (BANDWIDTH_CH, optional): Bandwidth of channel (selected models).
        """
        if enabled:
            super()._set_channel_on(channel, range, coupling, offset, bandwidth)
        else:
            super()._set_channel_off(channel)
    
    def get_timebase(self, timebase:int, samples:int, segment:int=0) -> None:
        """
        This function calculates the sampling rate and maximum number of 
        samples for a given timebase under the specified conditions.

        Args:
                timebase (int): Selected timebase multiplier (refer to programmer's guide).
                samples (int): Number of samples.
                segment (int, optional): The index of the memory segment to use.

        Returns:
                dict: Returns interval (ns) and max samples as a dictionary.
        """

        return super()._get_timebase(timebase, samples, segment)
    
    def set_data_buffer(self, channel:CHANNEL, samples:int, segment:int=0, datatype:DATA_TYPE=DATA_TYPE.INT16_T, 
                        ratio_mode:RATIO_MODE=RATIO_MODE.RAW, action:ACTION=ACTION.CLEAR_ALL | ACTION.ADD) -> ctypes.Array:
        """
        Tells the driver where to store the data that will be populated when get_values() is called.
        This function works on a single buffer. For aggregation mode, call set_data_buffers instead.

        Args:
                channel (CHANNEL): Channel you want to use with the buffer.
                samples (int): Number of samples/length of the buffer.
                segment (int, optional): Location of the buffer.
                datatype (DATATYPE, optional): C datatype of the data.
                ratio_mode (RATIO_MODE, optional): Down-sampling mode.
                action (ACTION, optional): Method to use when creating a buffer.

        Returns:
                ctypes.Array: Array that will be populated when get_values() is called.
        """
        return super()._set_data_buffer_ps6000a(channel, samples, segment, datatype, ratio_mode, action)
    
    def set_data_buffer_for_enabled_channels(self, samples:int, segment:int=0, datatype=DATA_TYPE.INT16_T, 
                                             ratio_mode=RATIO_MODE.RAW, action=ACTION.CLEAR_ALL | ACTION.ADD) -> dict:
        """
        Sets data buffers for enabled channels set by picosdk.set_channel()

        Args:
            samples (int): The sample buffer or size to allocate.
            segment (int): The memory segment index.
            datatype (DATA_TYPE): The data type used for the buffer.
            ratio_mode (RATIO_MODE): The ratio mode (e.g., RAW, AVERAGE).
            action (ACTION): The action to perform (e.g., CLEAR_ALL | ADD).

        Returns:
            dict: A dictionary mapping each channel to its associated data buffer.
        """
        channels_buffer = {}
        for channel in self.range:
            channels_buffer[channel] = super()._set_data_buffer_ps6000a(channel, samples, segment, datatype, ratio_mode, action)
        return channels_buffer
    
    def run_simple_block_capture(self, timebase:int, samples:int, segment=0, start_index=0, datatype=DATA_TYPE.INT16_T, ratio=0, 
                         ratio_mode=RATIO_MODE.RAW, action=ACTION.CLEAR_ALL|ACTION.ADD, pre_trig_percent=50) -> dict:
        """
        Performs a complete single block capture using current channel and trigger configuration.

        This function sets up data buffers for all enabled channels, starts a block capture,
        and retrieves the values once the device is ready. It is a simplified interface 
        for common block capture use cases.

        Args:
            timebase (int): Timebase value determining the sample interval (refer to PicoSDK guide).
            samples (int): Total number of samples to capture.
            segment (int, optional): Memory segment index to use.
            start_index (int, optional): Starting index in the buffer.
            datatype (DATA_TYPE, optional): Data type to use for the capture buffer.
            ratio (int, optional): Downsampling ratio.
            ratio_mode (RATIO_MODE, optional): Downsampling mode.
            action (ACTION, optional): Action to take on the data buffer.
            pre_trig_percent (int, optional): Percentage of samples to capture before the trigger.

        Returns:
            dict: A dictionary mapping each enabled channel to its corresponding data buffer.

        Examples:
            >>> scope.set_channel(CHANNEL.A, RANGE.V1)
            >>> scope.set_simple_trigger(CHANNEL.A, threshold_mv=500)
            >>> buffers = scope.run_simple_block_capture(timebase=3, samples=1000)
        """
        channels_buffer = self.set_data_buffer_for_enabled_channels(samples, segment, datatype, ratio_mode, action)
        self.run_block_capture(timebase, samples, pre_trig_percent, segment)
        self.get_values(samples, start_index, segment, ratio, ratio_mode)
        return channels_buffer
    
class ps5000a(PicoScopeBase):
    dll = ctypes.CDLL(os.path.join(_get_lib_path(), "ps5000a.dll"))
    _unit_prefix_n = "ps5000a"

    def open_unit(self, serial_number=None, resolution=RESOLUTION):
        status = super()._open_unit(serial_number, resolution)
        self.max_adc_value = super()._get_maximum_adc_value()
        return status

    def set_channel(self, channel, range, enabled=True, coupling=COUPLING.DC, offset=0):
        return super()._set_channel(channel, range, enabled, coupling, offset)
    
    def get_timebase(self, timebase, samples, segment=0):
        return super()._get_timebase_2(timebase, samples, segment)
    
    def set_data_buffer(self, channel, samples, segment=0, ratio_mode=0):
        return super()._set_data_buffer_ps5000a(channel, samples, segment, ratio_mode)
    
    def set_data_buffer_for_enabled_channels(self, samples, segment=0, ratio_mode=0):
        channels_buffer = {}
        for channel in self.range:
            channels_buffer[channel] = super()._set_data_buffer_ps5000a(channel, samples, segment, ratio_mode)
        return channels_buffer
    
    def change_power_source(self, state):
        return super()._change_power_source(state)



# """Timebase calculation for external use WIP"""
# def timebase_calc_6000a(timebase: int):
#     """Hello World

#     :param int timebase: _description_
#     :return _type_: _description_
#     """
#     if timebase <= 4:
#         return print((pow(2, timebase))/5_000_000_000)
#     else:
#         return print((timebase - 4) / 156_250_000)

# def timebase_calc_6428E_D(timebase: int):
#     if timebase <= 5:
#         return to_engineering_notation((pow(2, timebase)) / 10_000_000_000)
#     else:
#         return to_engineering_notation((timebase - 5) / 156_250_000)
    
# def to_engineering_notation(value):
#     prefixes = {
#         -12: 'p',  # pico
#         -9: 'n',   # nano
#         -6: 'u',   # micro
#         -3: 'm',   # milli
#          0: '',    # unit
#          3: 'k',   # kilo
#          6: 'M',   # mega
#          9: 'G',   # giga
#         12: 'T',   # tera
#     }
    
#     if value == 0:
#         return "0"
    
#     exponent = 0
#     scaled_value = 0
#     exponent = value/10
#     print(exponent)
    
#     return 0
#     # return f"{scaled_value:.3f}{prefixes[exponent]}"
