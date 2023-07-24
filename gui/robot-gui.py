""" 
    Python GUI that communicates over bluetooth/serial connection to the C++ program on the arduino 

    Communicates through strings of 32 bits

    Format: [id]_[int]n
    s_90_1_n = Move shoulder forward 90 degrees
    e_45n = Move elbow 45 degrees
    w_0n = Move wrist to 0 degrees
    r_30n = Move secondary wrist servo to 30 degrees
"""

import gi, serial

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class Window(Gtk.Window):
    def __init__(self):

        # Window initialisation
        super().__init__(title="S.A.M Interface")
        self.set_default_size(800, 600)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(self.main_box)

        self.test_button = Gtk.Button()
        self.main_box.pack_start(self.test_button, True, False, 0)

win = Window()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()