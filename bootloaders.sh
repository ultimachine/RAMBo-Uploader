#! /bin/bash      
/usr/bin/avrdude -D -v -v -c avrispmkII -P usb:0200158420 -patmega32u2 -Uflash:w:/home/ultimachine/workspace/RAMBo/bootloaders/RAMBo-usbserial-DFU-combined-32u2.HEX:i -Uefuse:w:0xF4:m -Uhfuse:w:0xD9:m -Ulfuse:w:0xEF:m -Ulock:w:0x0F:m &
/usr/bin/avrdude -D -v -v -c avrispmkII -P usb:0200158597 -pm2560 -Uflash:w:/home/ultimachine/workspace/RAMBo/bootloaders/stk500boot_v2_mega2560.hex:i -Uefuse:w:0xFD:m -Uhfuse:w:0xD0:m -Ulfuse:w:0xFF:m -Ulock:w:0x0F:m &

