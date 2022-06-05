from machine import Pin, SPI
import array

# Holtek HT16D35
CMD_SOFT_RESET = 0xCC
CMD_GLOBAL_BRIGHTNESS = 0x37
CMD_COM_PIN_CTRL = 0x41
CMD_ROW_PIN_CTRL = 0x42
CMD_WRITE_DISPLAY = 0x80
CMD_READ_DISPLAY = 0x81
CMD_SYSTEM_CTRL = 0x35
CMD_SCROLL_CTRL = 0x20

_COLS = 17
_ROWS = 7
_PIXELS = _COLS * _ROWS
_BYTES_IN_MATRIX = 28 * 8

BUTTON_A = Pin(10, Pin.IN, Pin.PULL_UP)
BUTTON_B = Pin(11, Pin.IN, Pin.PULL_UP)
BUTTON_X = Pin(12, Pin.IN, Pin.PULL_UP)
BUTTON_Y = Pin(13, Pin.IN, Pin.PULL_UP)

SPI_SCK = Pin(18)
SPI_MOSI = Pin(19)
SPI_MISO = Pin(16)
SPI_CS0 = Pin(17, Pin.OUT, value=1)
SPI_CS1 = Pin(14, Pin.OUT, value=1)

class UnicornHATMini():
    lut = b'\x8b\x8a\x89\xdf\xde\xdd\xa7\xa6\xa5\xc3\xc2\xc1onm765SRQ\x88\x87\x86\xdc\xdb\xda\xa4\xa3\xa2\xc0\xbf\xbelkj432PONqsr\xc5\xc7\xc6\x8d\x8f\x8e\xa9\xab\xaaUWV\x1d\x1f\x1e9;:tvu\xc8\xca\xc9\x90\x92\x91\xac\xae\xadXZY "!<>=wyx\xcb\xcd\xcc\x93\x95\x94\xaf\xb1\xb0[]\\#%$?A@z|{\xce\xd0\xcf\x96\x98\x97\xb2\xb4\xb3^`_&(\'BDC}\x7f~\xd1\xd3\xd2\x99\x9b\x9a\xb5\xb7\xb6acb)+*EGF\x80\x82\x81\xd4\xd6\xd5\x9c\x9e\x9d\xb8\xba\xb9dfe,.-HJI\x83\x85\x84\xd7\xd9\xd8\x9f\xa1\xa0\xbb\xbd\xbcgih/10KML'

    def __init__(self, spi_max_speed_hz=5_000_000):
        """Initialise unicornhatmini
        :param spi_max_speed_hz: SPI speed in Hz
        """
        self.disp = array.array('L', 0 for _ in range(_PIXELS))
        self.spi = SPI(0, baudrate=spi_max_speed_hz, mosi=SPI_MOSI, sck=SPI_SCK)
        self.left_matrix = (SPI_CS0, 0)
        self.right_matrix = (SPI_CS1, 0 + _BYTES_IN_MATRIX)

        self.buf = bytearray(_BYTES_IN_MATRIX * 2)
        self._rotation = 0
        self.set_pixel = self._set_pixel_0

        for cs, _ in self.left_matrix, self.right_matrix:
            self.xfer(cs, CMD_SOFT_RESET)
            self.xfer(cs, CMD_GLOBAL_BRIGHTNESS, b'\x01')
            self.xfer(cs, CMD_SCROLL_CTRL, b'\x00')
            self.xfer(cs, CMD_SYSTEM_CTRL, b'\x00')
            self.xfer(cs, CMD_WRITE_DISPLAY, b'\0x00', bytes(_BYTES_IN_MATRIX))
            self.xfer(cs, CMD_COM_PIN_CTRL, b'\xff')
            self.xfer(cs, CMD_ROW_PIN_CTRL, b'\xff\xff\xff\xff')
            self.xfer(cs, CMD_SYSTEM_CTRL, b'\x03')

    def shutdown(self):
        for cs, _ in self.left_matrix, self.right_matrix:
            self.xfer(cs, CMD_COM_PIN_CTRL, b'\x00')
            self.xfer(cs, CMD_ROW_PIN_CTRL, b'\x00\x00\x00\x00')
            self.xfer(cs, CMD_SYSTEM_CTRL, b'\x00')

    def xfer(self, cs, command, *data):
        self.buf[0] = command
        ln = 1
        for d in data:
            ld = len(d)
            self.buf[ln:ln+ld] = d
            ln += ld     

        cs.value(0)       
        self.spi.write(self.buf[0:ln])
        cs.value(1)

    def xfer_write_display(self, cs, buf):
        cs.value(0)
        self.spi.write(b'\x80\x00')
        self.spi.write(buf[:_BYTES_IN_MATRIX])
        cs.value(1)

    def _set_pixel_0(self, x, y, r, g, b):
        offset = (x * _ROWS) + y
        self.disp[offset] = (r >> 2 << 16) | (g >> 2 << 8) | (b >> 2)

    def _set_pixel_90(self, x, y, r, g, b):
        y = _COLS - 1 - y
        offset = (y * _ROWS) + x
        self.disp[offset] = (r >> 2 << 16) | (g >> 2 << 8) | (b >> 2)

    def _set_pixel_180(self, x, y, r, g, b):
        x = _COLS - 1 - x
        y = _ROWS - 1 - y
        offset = (x * _ROWS) + y
        self.disp[offset] = (r >> 2 << 16) | (g >> 2 << 8) | (b >> 2)

    def _set_pixel_270(self, x, y, r, g, b):
        x = _ROWS - 1 - x
        offset = (y * _ROWS) + x
        self.disp[offset] = (r >> 2 << 16) | (g >> 2 << 8) | (b >> 2)

    def set_all(self, r, g, b):
        """Set all pixels."""
        self.disp[:] = (r >> 2 << 16) | (g >> 2 << 8) | (b >> 2)

    def set_image(self, image, offset_x=0, offset_y=0, wrap=False, bg_color=(0, 0, 0)):
        """Set a PIL image to the display buffer."""
        image_width, image_height = image.size

        if image.mode != "RGB":
            image = image.convert('RGB')

        display_width, display_height = self.get_shape()

        for y in range(display_height):
            for x in range(display_width):
                r, g, b = bg_color
                i_x = x + offset_x
                i_y = y + offset_y
                if wrap:
                    while i_x >= image_width:
                        i_x -= image_width
                    while i_y >= image_height:
                        i_y -= image_height
                if i_x < image_width and i_y < image_height:
                    r, g, b = image.getpixel((i_x, i_y))
                self.set_pixel(x, y, r, g, b)

    def clear(self):
        """Set all pixels to 0."""
        self.set_all(0, 0, 0)

    def set_brightness(self, b=0.2):        
        for cs, _ in self.left_matrix, self.right_matrix:
            self.xfer(cs, CMD_GLOBAL_BRIGHTNESS, (int(63 * b),))

    def set_rotation(self, rotation=0):
        if rotation not in [0, 90, 180, 270]:
            raise ValueError("Rotation must be one of 0, 90, 180, 270")
        self._rotation = rotation
        if rotation == 0:
            self.set_pixel = self._set_pixel_0
        elif rotation == 90:
            self.set_pixel = self._set_pixel_90
        elif rotation == 180:
            self.set_pixel = self._set_pixel_180
        else:
            self.set_pixel = self._set_pixel_270

    def _show_part(self, cs, disp_offset, count):
        disp = self.disp[disp_offset:]
        for i in range(0, count):
            i3 = i*3
            ir, ig, ib = UnicornHATMini.lut[i3:i3+3]
            rgb = disp[i]
            self.buf[ir] = rgb >> 16
            self.buf[ig] = rgb >> 8
            self.buf[ib] = rgb
        self.xfer_write_display(cs, self.buf)

    def show(self):
        _PIXELS_IN_FIRST_HALF = len(UnicornHATMini.lut)//3
        self._show_part(self.left_matrix[0],  0,                     _PIXELS_IN_FIRST_HALF)
        self._show_part(self.right_matrix[0], _PIXELS_IN_FIRST_HALF, _PIXELS-_PIXELS_IN_FIRST_HALF)

    def get_shape(self):
        if self._rotation in [90, 270]:
            return _ROWS, _COLS
        else:
            return _COLS, _ROWS
