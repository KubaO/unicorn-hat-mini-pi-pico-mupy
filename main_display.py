from colorsys import hsv_to_rgb
from machine import Pin, Timer
from unicornhatmini import UnicornHATMini
import time

if True:
    led = Pin(25, Pin.OUT)
    timer = Timer()

    def blink(timer):
        led.toggle()

    timer.init(freq=10, mode=Timer.PERIODIC, callback=blink)
        
    unicorn = UnicornHATMini()
    COLS, ROWS = unicorn.get_shape()

    #for i in range(10):
    while True:
        t = time.ticks_ms() / 4000.0
        #print(t)
        for y in range(ROWS):
            for x in range(COLS):
                hue = t + (x / float(COLS * 2)) + (y / float(ROWS))
                r, g, b = [int(c * 255) for c in hsv_to_rgb(hue, 1.0, 1.0)]
                unicorn.set_pixel(x, y, r, g, b)
        unicorn.show()
        time.sleep(1.0 / 60)
