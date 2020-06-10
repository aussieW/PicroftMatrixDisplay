# PicroftMatrixDisplay
Code to interface an RGD LED Matrix with a Picroft

To start:
nohup sudo python3 ./Display.py --led-pixel-mapper=U-mapper --led-rows=32 --led-cols=64 --led-chain=2 --led-brightness=37 --led-rgb-sequence=RBG --led-slowdown-gpio 2 &
