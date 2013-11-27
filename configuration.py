# Configuration file for Rambo-Uploader

# Path to avrdude
avrdude_path="C:/avrdude-5.11-w32-libusb/avrdude.exe"
# Type of ICSP programmer for Atmega32u2.
m32u2_icsp_programmer="jtag2isp"
# Type of ICSP programmer for Atmega2560
m2560_icsp_programmer="jtag2isp"
# Type of programming through serial
serial_programmer="wiring"
# Port (USB serial number) of ICSP Programmer connected to Atmega32u2
m32u2_icsp_port="usb:402671"
# Port (USB serial number) of ICSP Programmer connected to Atmega2560
m2560_icsp_port="usb:402903"
# Path to Atmega32u2 bootloader
m32u2_bootloader_path="C:/RAMBo/bootloaders/RAMBo-usbserial-DFU-combined-32u2.HEX"
# Path to Atmega2560 bootloader
m2560_bootloader_path="C:/RAMbo/bootloaders/stk500boot_v2_mega2560.hex"
# Serial port for Test Jig Controller. Set to None to use serial number
#controller_port="COM24"
controller_port=None
# Serial number for Test Jig controller
controller_snr="6403635343035130E0E0"
# Serial port for Device Under Test. Set to None to auto-detect
#target_port="COM25"
target_port=None
# List of RAMBo board serial numbers to ignore if auto-detecting target. Useful if you have printers connected to the same PC.
ignore_rambo_snr=("64033353730351A0D1C0", )
# Program the Atmega32u2 and Atmega2560 through ICSP (required if the fuses are not yet set or bootloader not flashed yet)
icsp_program=True
# Verify flash after ICSP programming
icsp_verify=True
# Delay before testing after we power on the power supply. Some power supply require a bit of time before they provide power.
powering_delay=1

# Path to the test firmware
test_firmware_path="C:/RAMBo/bootloaders/test_firmware.hex"
# Path to the final retail firmware
vendor_firmware_path="C:/RAMBo/bootloaders/vendor_firmware.hex"
