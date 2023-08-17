""" 
    Python GUI that communicates over bluetooth/serial connection to the C++ program on the arduino 

    Communicates through strings of 32 bits

    Format: [id]_[int]_[dir]_n
    s_90_1_n = Move shoulder forward 90 degrees
"""

import gi, serial, time

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gio, Gdk

MODULE_ADDRESS = "98:D3:71:FD:42:23"

class Window(Gtk.Window):
    def __init__(self):
        # Window initialisation
        super().__init__(title="S.A.M Interface")
        self.set_default_size(800, 600)

        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        provider.load_from_path("./gui/style/main.css")
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        main_box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        top_bar = Gtk.ActionBar()
        main_box.pack_start(top_bar, False, True, 0)

        self.bt_icon = Gtk.Image.new_from_icon_name("network-bluetooth", Gtk.IconSize.BUTTON)
        self.usb_icon = Gtk.Image.new_from_icon_name("drive-removable-media", Gtk.IconSize.BUTTON)
        self.bt_icon.set_opacity(0.5)
        self.usb_icon.set_opacity(0.5)

        bt_button = Gtk.Button()
        bt_button.set_image(self.bt_icon)
        top_bar.pack_start(bt_button)

        usb_button = Gtk.Button()
        usb_button.set_image(self.usb_icon)
        top_bar.pack_start(usb_button)

        bt_button.connect("clicked", self.get_bt_connection)
        usb_button.connect("clicked", self.get_usb_connection)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        lcol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        rcol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row.pack_start(lcol, True, True, 20)
        row.pack_end(rcol, True, True, 20)

        main_box.pack_start(row, True, True, 0)

        self.create_arrow_block(lcol, "<big>Shoulder Controls</big>", "s")
        self.create_arrow_block(lcol, "<big>Elbow Controls</big>", "e", invert=True)
        self.create_arrow_block(lcol, "<big>Base Controls</big>", "b")

        #self.create_input_block(rcol, "<big>Wrist Control</big>", "w")
        self.create_slider_block(rcol, "<big>Wrist Pitch</big>", "w", 0, 180)
        self.create_slider_block(rcol, "<big>Wrist Yaw</big>", "r", 0, 180)

        self.ser = self.get_serial_connection()
        self.limits = {'s': False, 'e': False, 'b': False}
        #GLib.idle_add(self.read_limits)

    def send_command(self, button, *data):
        #ser = get_serial_connection()
        if self.ser is not None:
            if data[0] in "wr":
                processed_data = (data[0], int(data[1].get_value()), 0)
                #data[1].set_text("")
            else:
                processed_data = data
            command = "%s_%s_%s_n" % processed_data
            self.ser.write(command.encode())
        else:
            print("Failed to send command, please check usb/bluetooth connection and try again")

    def read_limits(self):
        c = self.ser.read(1).decode('ascii')
        if c in self.limits.keys():
            self.limits[c] = True
            print(self.limits)

    def get_serial_connection(self):
        """ Fetches the serial connection through bluetooth or USB """

        ser = None
        try:
            ser = serial.Serial("/dev/rfcomm0")
            self.bt_icon.set_opacity(1)
        except serial.serialutil.SerialException:
            print("Bluetooth connection failed, falling back to USB")
            self.bt_icon.set_opacity(0.5)
            try:
                ser = serial.Serial('/dev/ttyACM1')
                self.usb_icon.set_opacity(1)
            except serial.serialutil.SerialException as e:
                print("USB connection failed.")
                self.usb_icon.set_opacity(0.5)
        return ser

    def get_bt_connection(self, button):
        try:
            self.ser = serial.Serial("/dev/rfcomm0")
            self.bt_icon.set_opacity(1)
        except serial.serialutil.SerialException:
            print("Bluetooth connection failed. Please check connection and try again. ")

    def get_usb_connection(self, button):
        for n in range(0, 5):
            try: 
                self.ser = serial.Serial("/dev/ttyACM%s" % n)
                self.usb_icon.set_opacity(1)
                return 1
            except serial.serialutil.SerialException:
                pass
        print("USB connection failed.")
        self.usb_icon.set_opacity(0.5)

    def create_arrow_block(self, col, label_text, id, invert=False):
        col.pack_start(Gtk.Label(label=label_text, use_markup=True), False, True, 10)

        control_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        col.pack_start(control_box, False, True, 10)

        left_button = Gtk.Button(label="<")
        right_button = Gtk.Button(label=">")
        control_box.pack_start(left_button, True, True, 0)
        control_box.pack_end(right_button, True, True, 0)

        if not invert: n1, n2 = 1, 0
        else: n1, n2 = 0, 1

        left_button.connect("clicked", self.send_command, id, 10, n1)
        right_button.connect("clicked", self.send_command, id, 10, n2)

    def create_input_block(self, col, label_text, id):
        col.pack_start(Gtk.Label(label=label_text, use_markup=True), False, True, 10)

        control_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        col.pack_start(control_box, False, True, 10)

        input_box = Gtk.Entry()
        control_box.pack_start(input_box, True, True, 0)

        go_button = Gtk.Button(label="Go!")
        control_box.pack_start(go_button, True, True, 0)

        go_button.connect("clicked", self.send_command, id, input_box, 0)

    def create_slider_block(self, col, label_text, id, min, max):
        col.pack_start(Gtk.Label(label=label_text, use_markup=True), False, True, 10)

        control_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        col.pack_start(control_box, False, True, 10)

        adj = Gtk.Adjustment(value=90, lower=0, upper=180, step_increment=5, page_increment=0)
        slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        slider.set_digits(0)
        slider.set_hexpand(True)
        slider.connect("value_changed", self.send_command, id, slider)

        control_box.pack_start(slider, False, True, 0)


win = Window()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()