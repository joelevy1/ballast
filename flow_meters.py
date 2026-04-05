"""
Flow Meter Manager - GPIO and Pulse Counting
Version: 4-5-2026-v1.0
"""

from machine import Pin
from time import ticks_ms, ticks_diff

VERSION = "4-5-2026-v1.0"

class FlowMeterManager:
    def __init__(self):
        self.pins = []
        self.pulse_counts = [0] * 8
        self.last_trigger_time = [0] * 8
        self.debounce_ms = 50
        
        # Initialize GPIO pins GP0-GP7
        for i in range(8):
            pin = Pin(i, Pin.IN, Pin.PULL_UP)
            pin.irq(trigger=Pin.IRQ_FALLING, handler=self._make_handler(i))
            self.pins.append(pin)
        
        print(f"Flow meters initialized: 8 channels (v{VERSION})")
    
    def _make_handler(self, pin_index):
        def handler(pin):
            current_time = ticks_ms()
            if ticks_diff(current_time, self.last_trigger_time[pin_index]) > self.debounce_ms:
                self.pulse_counts[pin_index] += 1
                self.last_trigger_time[pin_index] = current_time
        return handler
    
    def get_pulse_count(self, pin_index):
        if 0 <= pin_index < 8:
            return self.pulse_counts[pin_index]
        return 0
    
    def get_all_pulse_counts(self):
        return self.pulse_counts.copy()
    
    def reset_counter(self, pin_index):
        if 0 <= pin_index < 8:
            self.pulse_counts[pin_index] = 0
    
    def reset_all_counters(self):
        self.pulse_counts = [0] * 8
    
    def get_pin_state(self, pin_index):
        if 0 <= pin_index < 8:
            return self.pins[pin_index].value()
        return None
    
    def get_all_pin_states(self):
        return [pin.value() for pin in self.pins]
