
from mcculw import ul
from mcculw.enums import InfoType, BoardInfo, DigitalPortType, DigitalInfo
from mcculw.enums import InterfaceType, DigitalIODirection, FunctionType

from bitstring import BitArray
import struct

from pdb import set_trace as bpt

### util.py 

def config_first_detected_device(board_num):
    """Adds the first available device to the UL.

    Parameters
    ----------
    board_num : int, optional
        The board number to assign to the board when configuring the device.

    Returns
    -------
    boolean
        True if a device was found and added, False if no devices were
        found. 
    """

    # Get the device inventory
    devices = ul.get_daq_device_inventory(InterfaceType.ANY)
    # Check if any devices were found
    if len(devices) > 0:
        device = devices[0]
        # Print a messsage describing the device found
        print("Found device: " + device.product_name +
              " (" + device.unique_id + ")\n")
        # Add the device to the UL.
        ul.create_daq_device(board_num, device)
        return True

    return False


def config_first_detected_device_of_type(board_num, types_list):
    """Adds the first available device to the UL.

    Parameters
    ----------
    board_num : int, optional
        The board number to assign to the board when configuring the device.

    Returns
    -------
    boolean
        True if a device was found and added, False if no devices were
        found. 
    """

    # Get the device inventory (optional parameter omitted)
    devices = ul.get_daq_device_inventory(InterfaceType.ANY)

    device = next((device for device in devices
                   if device.product_id in types_list), None)

    if device != None:
        # Print a messsage describing the device found
        print("Found device: " + device.product_name +
              " (" + device.unique_id + ")\n")
        # Add the device to the UL.
        ul.create_daq_device(board_num, device)
        return True

    return False

###

# copied this from examples.props.digital

class Props(object):
    """The base class for classes that provide hardware information for the
    library examples. Subclasses of this class may change hardware values.
    It is recommended that the values provided by these classes be
    hard-coded in production code.
    """

    def __init__(self, params): pass

    def get_config_array(self, info_type, board_num, count_item, value_item,
                         wrapper_type=None):
        result = []

        count = ul.get_config(info_type, board_num, 0, count_item)
        for item_num in range(count):
            config_value = ul.get_config(
                info_type, board_num, item_num, value_item)
            if wrapper_type == None:
                result.append(config_value)
            else:
                result.append(wrapper_type(config_value))

        return result

class PortInfo(object):
    def __init__(self, board_num, port_index):
        self._board_num = board_num
        self._port_index = port_index

        self.type = self._get_digital_dev_type()
        self.first_bit = self._get_first_bit(port_index, self.type)
        self.num_bits = self._get_num_bits()
        self.in_mask = self._get_in_mask()
        self.out_mask = self._get_out_mask()
        self.is_bit_configurable = self._get_is_bit_configurable(
            self.type, self.first_bit, self.in_mask, self.out_mask)
        self.is_port_configurable = self._get_is_port_configurable(
            self.type, self.in_mask, self.out_mask)
        self.supports_input = self._get_supports_input(
            self.in_mask, self.is_port_configurable)
        self.supports_input_scan = self._get_supports_input_scan()
        self.supports_output = self._get_supports_output(
            self.out_mask, self.is_port_configurable)
        self.supports_output_scan = self._get_supports_output_scan()

    def _get_num_bits(self):
        return ul.get_config(
            InfoType.DIGITALINFO, self._board_num, self._port_index,
            DigitalInfo.NUMBITS)

    def _get_supports_input(self, in_mask, is_port_programmable):
        return in_mask > 0 or is_port_programmable

    def _get_supports_input_scan(self):
        try:
            ul.get_status(self._board_num, FunctionType.DIFUNCTION)
        except ul.ULError:
            return False
        return True

    def _get_supports_output_scan(self):
        try:
            ul.get_status(self._board_num, FunctionType.DOFUNCTION)
        except ul.ULError:
            return False
        return True

    def _get_supports_output(self, out_mask, is_port_programmable):
        return out_mask > 0 or is_port_programmable

    def _get_first_bit(self, port_index, port_type):
        # A few devices (USB-SSR08 for example) start at FIRSTPORTCL and
        # number the bits as if FIRSTPORTA and FIRSTPORTB exist for
        # compatibility with older digital peripherals
        if port_index == 0 and port_type == DigitalPortType.FIRSTPORTCL:
            return 16
        return 0

    def _get_is_bit_configurable(self, port_type, first_bit, in_mask,
                                 out_mask):
        if in_mask & out_mask > 0:
            return False
        # AUXPORT type ports might be configurable, check if d_config_bit
        # completes without error
        if port_type == DigitalPortType.AUXPORT:
            try:
                ul.d_config_bit(
                    self._board_num, port_type, first_bit,
                    DigitalIODirection.OUT)
                ul.d_config_bit(
                    self._board_num, port_type, first_bit,
                    DigitalIODirection.IN)
            except ul.ULError:
                return False
            return True
        return False

    def _get_is_port_configurable(self, port_type, in_mask, out_mask):
        if in_mask & out_mask > 0:
            return False
        # Check if d_config_port completes without error
        try:
            ul.d_config_port(self._board_num, port_type,
                             DigitalIODirection.OUT)
            ul.d_config_port(self._board_num, port_type,
                             DigitalIODirection.IN)
        except ul.ULError:
            return False
        return True

    def _get_digital_dev_type(self):
        return DigitalPortType(ul.get_config(
            InfoType.DIGITALINFO, self._board_num, self._port_index,
            DigitalInfo.DEVTYPE))

    def _get_in_mask(self):
        return ul.get_config(
            InfoType.DIGITALINFO, self._board_num, self._port_index,
            DigitalInfo.INMASK)

    def _get_out_mask(self):
        return ul.get_config(
            InfoType.DIGITALINFO, self._board_num, self._port_index,
            DigitalInfo.OUTMASK)

class DigitalProps(Props):
    """Provides digital IO information on the hardware configured at the
    board number given.

    This class is used to provide hardware information for the library
    examples, and may change hardware values. It is recommended that the
    values provided by this class be hard-coded in production code. 
    """

    def __init__(self, board_num):
        self._board_num = board_num
        self.num_ports = self._get_num_digital_chans()

        self.port_info = []
        for port_index in range(self.num_ports):
            self.port_info.append(PortInfo(board_num, port_index))

    def _get_num_digital_chans(self):
        try:
            return ul.get_config(
                InfoType.BOARDINFO, self._board_num, 0,
                BoardInfo.DINUMDEVS)
        except ul.ULError:
            return 0

class PhaseShifter:

    def __init__(self, board_num=0):
        self.board_num = board_num
        self.state = BitArray(uint=0, length=11)

    def connect(self):
        ul.ignore_instacal()
        config_first_detected_device(self.board_num)
        
        self.dig_props = DigitalProps(self.board_num)

        self.pA = self.dig_props.port_info[0]
        self.pB = self.dig_props.port_info[1]

        ul.d_config_port(0, self.pA.type, DigitalIODirection.OUT)
        ul.d_config_port(0, self.pB.type, DigitalIODirection.OUT)


    def write(self, delay):

        if delay > (2 **10 - 1) * 5 or delay < 0:
            raise ValueError()

        self.ps_delay = delay // 5
        self.state = BitArray(uint=self.ps_delay, length=11)

        ul.d_out(self.board_num, self.pA.type, self.state[3:].uint)
        ul.d_out(self.board_num, self.pB.type, self.state[:3].uint)
        

    def flip_bit(self, n):
        if n > 10 or n < 0:
            raise ValueError()

        if self.state[n]:
            self.state.set(0, n)
        else:
            self.state.set(1, n)

        ul.d_out(self.board_num, self.pA.type, self.state[3:].uint)
        ul.d_out(self.board_num, self.pB.type, self.state[:3].uint)

        self.read()
        self.print()

    def write_state(self):
        ul.d_out(self.board_num, self.pA.type, self.state[3:].uint)
        ul.d_out(self.board_num, self.pB.type, self.state[:3].uint)

    def set_delay(self, delay):
        self.state.uint = (1 << 10) | delay
        self.write_state()
        self.state.uint = (0 << 10) | delay
        self.write_state()
        self.state.uint = (1 << 10) | delay
        self.write_state()



    def read(self):
        self.stA = BitArray(uint=ul.d_in(self.board_num, self.pA.type), length=8)
        self.stB = BitArray(uint=ul.d_in(self.board_num, self.pB.type), length=3)

        self.state = self.stB + self.stA

    def print(self):
        print('Phase shift is %4i ps (%s).' % (self.state.uint *5,
                                               self.state.bin), sep='' )

# ul.d_out(0, pA.type, 0xFF)
# ul.d_in(0, pA.type)
