""" 
    Python GUI that communicates over bluetooth/serial connection to the C++ program on the arduino 

    Communicates through strings of 32 bits

    Format: [id]_[int]_[dir]_n
    s_90_1_n = Move shoulder forward 90 degrees
"""

import gi, serial, time

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

MODULE_ADDRESS = "98:D3:71:FD:42:23"

def get_serial_connection():
    """ Fetches the serial connection through bluetooth or USB """

    ser = None
    try:
        ser = serial.Serial("/dev/rfcomm0")
    except serial.serialutil.SerialException:
        print("Bluetooth connection failed, falling back to USB")
        try:
            ser = serial.Serial('/dev/ttyACM0')
        except serial.serialutil.SerialException as e:
            print("USB connection failed.")
    return ser

class Window(Gtk.Window):
    def __init__(self):
        # Window initialisation
        super().__init__(title="S.A.M Interface")
        self.set_default_size(800, 600)

        main_box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        lcol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        rcol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row.pack_start(lcol, True, True, 20)
        row.pack_end(rcol, True, True, 20)

        main_box.pack_start(row, True, True, 0)

        lcol.pack_start(Gtk.Label(label="<big>Shoulder Controls</big>", use_markup=True), False, True, 10)

        shoulder_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lcol.pack_start(shoulder_controls, False, True, 10)

        left_button = Gtk.Button(label="<")
        right_button = Gtk.Button(label=">")
        shoulder_controls.pack_start(left_button, True, True, 0)
        shoulder_controls.pack_end(right_button, True, True, 0)

        left_button.connect("clicked", self.send_command, "s", 100, 1)
        right_button.connect("clicked", self.send_command, "s", 100, 0)

        lcol.pack_start(Gtk.Label(label="Elbow Controls"), False, True, 10)

        control_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lcol.pack_start(control_box, False, True, 10)
        left_button = Gtk.Button(label="<")
        right_button = Gtk.Button(label=">")
        control_box.pack_start(left_button, True, True, 0)
        control_box.pack_end(right_button, True, True, 0)

        left_button.connect("clicked", self.send_command, "e", 100, 0)
        right_button.connect("clicked", self.send_command, "e", 100, 1)

        lcol.pack_start(Gtk.Label(label="Base Controls"), False, True, 10)

        control_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lcol.pack_start(control_box, False, True, 10)
        left_button = Gtk.Button(label="<")
        right_button = Gtk.Button(label=">")
        control_box.pack_start(left_button, True, True, 0)
        control_box.pack_end(right_button, True, True, 0)

        left_button.connect("clicked", self.send_command, "b", 100, 0)
        right_button.connect("clicked", self.send_command, "b", 100, 1)

    def send_command(self, button, *data):
        ser = get_serial_connection()
        if ser is not None:
            command = "%s_%s_%s_n" % (data[0], data[1], data[2])
            print(command)
            ser.write(command.encode())
        else:
            print("Failed to send command, please check usb/bluetooth connection and try again")

win = Window()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()