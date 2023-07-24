import bluetooth
import serial

MODULE_ADDRESS = "98:D3:71:FD:42:23"


port = 1

#sock=bluetooth.BluetoothSocket( bluetooth.RFCOMM )
#sock.connect((MODULE_ADDRESS, port))

ser = serial.Serial("/dev/rfcomm0")
while True:
    ser.write(input().encode())
    output = ser.read_until(b'\n')
    if output != b'':
        print(output)

#sock.close()