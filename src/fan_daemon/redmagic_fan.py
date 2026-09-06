#!/usr/bin/env python3
'''
Red Magic 8 Pro Centrifugal Fan Daemon for Linux / postmarketOS.
Monitors CPU & GPU thermal zones and adjusts the internal turbofan speed.
'''
import time
import os
import glob
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

THERMAL_ZONES = "/sys/class/thermal/thermal_zone*/temp"
FAN_PWM_PATHS = [
    "/sys/class/pwm/pwmchip0/pwm0/duty_cycle",
    "/sys/devices/platform/soc/*.fan/fan_speed",
    "/sys/class/hwmon/hwmon*/pwm1"
]

def get_max_temperature():
    temps = []
    for tz in glob.glob(THERMAL_ZONES):
        try:
            with open(tz, 'r') as f:
                val = int(f.read().strip())
                if val > 1000:
                    val = val / 1000.0
                temps.append(val)
        except Exception:
            pass
    return max(temps) if temps else 40.0

def set_fan_speed(percent):
    logging.info(f"Thermal controller: Setting fan to {percent}%")
    for path in FAN_PWM_PATHS:
        for match in glob.glob(path):
            try:
                with open(match, 'w') as f:
                    f.write(str(int(percent * 255 / 100)))
            except Exception:
                pass

def main():
    logging.info("Starting Red Magic 8 Pro Fan Thermal Daemon...")
    while True:
        temp = get_max_temperature()
        if temp < 45.0:
            speed = 0
        elif temp < 55.0:
            speed = 35
        elif temp < 65.0:
            speed = 70
        else:
            speed = 100
        set_fan_speed(speed)
        time.sleep(3)

if __name__ == '__main__':
    main()
