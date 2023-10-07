""" 
    Python GUI that communicates over bluetooth/serial connection to the C++ program on the arduino 

    Communicates through strings of 32 bits

    Format: [id]_[int]_[dir]_n
    s_90_1_n = Move shoulder forward 90 degrees
"""

import gi, serial, time, threading, random, sys, inspect

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gio, Gdk, GdkPixbuf

MODULE_ADDRESS = "98:D3:71:FD:42:23"

class ListBoxRowWithData(Gtk.ListBoxRow):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.add(Gtk.Label(label=data))

class DummySerial():
    """ Fake serial for debugging purposes """
    def __init__(self):
        pass

    def write(self, data):
        print(data)

    def read(self, length):
        if random.randint(1, 100000) == 1:
            return(b'0')
        else:
            return(b'1')

class Window(Gtk.Window):
    def __init__(self):
        # Window initialisation
        super().__init__(title="S.A.M Interface")
        self.set_default_size(800, 600)

        # Set icon
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale("./icon.svg", -1, 128, True)
        self.set_icon(pixbuf)

        main_box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        top_bar = Gtk.ActionBar()
        main_box.pack_start(top_bar, False, True, 0)

        bt_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale("./bt.svg", -1, 16, True)
        usb_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale("./usb.svg", -1, 16, True)
        
        self.bt_icon = Gtk.Image.new_from_pixbuf(bt_pixbuf)
        self.usb_icon = Gtk.Image.new_from_pixbuf(usb_pixbuf)
        self.bt_icon.set_opacity(0.5)
        self.usb_icon.set_opacity(0.5)

        bt_button = Gtk.Button()
        bt_button.set_image(self.bt_icon)
        top_bar.pack_start(bt_button)
        bt_button.set_tooltip_text("Connect to S.A.M through Bluetooth")

        usb_button = Gtk.Button()
        usb_button.set_image(self.usb_icon)
        top_bar.pack_start(usb_button)
        usb_button.set_tooltip_text("Connect to S.A.M through USB")

        self.debug_warning = Gtk.Label()
        self.debug_warning.set_markup("<span size='x-large' foreground='red'> !  </span>")
        self.display_warning(False)
        top_bar.pack_start(self.debug_warning)

        bt_button.connect("clicked", self.get_bt_connection)
        usb_button.connect("button-release-event", self.get_usb_connection)
        usb_button.connect("key-release-event", self.get_usb_connection)

        self.row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        lcol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        rcol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.row.pack_start(lcol, True, True, 20)
        self.row.pack_end(rcol, True, True, 20)

        main_box.pack_start(self.row, True, True, 0)

        sh_box = self.create_control_block(lcol, "Shoulder Controls")
        e_box = self.create_control_block(lcol, "Elbow Controls")
        b_box = self.create_control_block(lcol, "Base Controls")
        w_box = self.create_control_block(rcol, "Wrist Controls")

        self.create_arrow_block(sh_box, "s")
        self.create_arrow_block(e_box, "e", invert=True)
        self.create_arrow_block(b_box, "b")

        self.precise_movement_block(sh_box, "s", 180)
        self.precise_movement_block(e_box, "e", 180)
        self.precise_movement_block(b_box, "b", 180)

        #self.create_input_block(rcol, "<big>Wrist Control</big>", "w")
        servo_grid = Gtk.Grid()
        w_box.pack_start(servo_grid, True, True, 0)
        self.create_slider_block(servo_grid, "w", 0, 180, "<big>Pitch</big>", 0)
        self.create_slider_block(servo_grid, "r", 0, 180, "<big>Roll</big>", 1)

        claw_button = Gtk.ToggleButton(label="Grab", tooltip_text="Toggle the robotic claw. ")
        claw_button.connect("toggled", self.grab)
        rcol.pack_start(claw_button, False, False, 20)

        self.ser = self.get_serial_connection()
        self.limits = {'s': False, 'e': False, 'b': False}
        #GLib.idle_add(self.read_limits)

        history_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.history = Gtk.ListStore(str)
        self.scrollbox = Gtk.ScrolledWindow()
        self.history_list = Gtk.TreeView(model=self.history)
        self.history_list.set_headers_visible(False)

        # All of this is GTK treeview code, which is needlessly complicated but I have to use it because GTK3 is a buggy mess
        tr = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("main_column", tr, text=0) # This does not display
        self.history_list.append_column(col)
        sel = self.history_list.get_selection()
        sel.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.scrollbox.add(self.history_list)
        history_box.pack_start(self.scrollbox, True, True, 0)

        save_icon = Gtk.Image.new_from_icon_name("document-save", Gtk.IconSize.BUTTON)
        save_button = Gtk.Button()
        save_button.set_image(save_icon)
        save_button.connect("clicked", self.save_script)
        save_button.set_tooltip_text("Saves the selected actions to a .sams script file.")
        history_box.pack_start(save_button, False, False, 0)

        rcol.pack_start(history_box, True, True, 20)

        self.execute_button = Gtk.Button(label="Execute from file")
        self.execute_button.set_tooltip_text("Executes a script saved on the local system.")
        top_bar.pack_end(self.execute_button)

        self.execute_button.connect("clicked", self.execute_from_file)

        self.reset_button = Gtk.Button(label="RESET")
        self.reset_button.set_tooltip_text("Resets the robot back to it's default position. Keycode: Z")
        main_box.pack_end(self.reset_button, False, False, 0)
        self.reset_button.set_vexpand(False)
        self.reset_button.connect("clicked", self.reset)

        if self.ser is None:
            self.sensitivity(False)

        sys.excepthook = self.error_handler

    def grab(self, button):
        """ Sends a simple signal to toggle the claw """
        self.ser.write(b'gn')
        self.update_history('gn')

    def reset(self, button):
        """ Sends a simple signal to trigger the reset callibration process """
        self.ser.write(b'Zn')
        self.update_history('Zn')

    def display_warning(self, state):
        self.debug_warning.set_opacity(int(state))
        if state:
            self.debug_warning.set_tooltip_text("Currently using debug serial. This is a fake connection and does not indicate connectivity to the robot. No data will be sent.")
        else:
            self.debug_warning.set_tooltip_text(None)

    def sensitivity(self, state):
        """ Disables/Undisables the controls """
        self.execute_button.set_sensitive(state)
        self.row.set_sensitive(state)
        self.reset_button.set_sensitive(state)

    def execute_script(self, script, dialog, progress):
        """ Executes the script file in a seperate thread """

        global dialog_exists
        length = len(script)
        while script and dialog_exists:
            print((length - len(script))/length)
            GLib.idle_add(progress.set_fraction, (length - len(script))/length)
            if self.ser.read(1) == b'0':
                self.ser.write(script[0].encode())
                script.pop(0)
        if dialog_exists:
            GLib.idle_add(dialog.destroy)
            dialog_exists = False
    
    def execute_from_file(self, button, *data):
        """ Selects a file and starts the execution thread with a popup """

        global dialog_exists
        response, filename = self.filechooser_dialog(Gtk.FileChooserAction.OPEN)

        if filename != None:
            # Load file, split into seperate commands
            script = open(filename, "r").read().split("N")
            script = [x + 'N' for x in script[:-1]] + ['n']
            
            dialog = Gtk.Dialog(
                transient_for=self,
                flags=0,
                #message_type=Gtk.MessageType.INFO,
                #buttons=Gtk.ButtonsType.NONE,
                #text="Executing...",
            )
            dialog.set_default_size(250, 50)

            box = dialog.get_content_area()
            
            box.pack_start(Gtk.Label(label="<big>Executing...</big>", use_markup = True), False, True, 20)

            progress = Gtk.ProgressBar(text="Executing")
            box.pack_start(progress, True, True, 0)

            def close_dialog(button):
                global dialog_exists
                dialog_exists = False
                dialog.destroy()

            cancel_button = Gtk.Button()
            image = Gtk.Image.new_from_stock(Gtk.STOCK_CANCEL, Gtk.IconSize.BUTTON)
            cancel_button.set_image(image)
            cancel_button.connect("clicked", close_dialog)
            box.pack_start(cancel_button, False, True, 5)

            dialog.show_all()

            dialog_exists = True

            # Start execution in seperate thread
            thread = threading.Thread(target=self.execute_script, args=[script, dialog, progress])
            thread.daemon = True
            thread.start()

            # Display dialog
            dialog.run()
            #if response == 0:
            #    dialog_exists = False
            #    dialog.destroy()

    def update_history(self, command):
        self.history.append([command])

        self.history_list.show_all()

        # Supposed to scroll to bottom. Doesn't work. I want to die.
        adj = self.scrollbox.get_vadjustment()
        adj.set_value(adj.get_property('upper'))
        self.scrollbox.set_vadjustment(adj)

    def filechooser_dialog(self, action):
        """ Stock function that throws up a dialog to choose a file """

        dialog = Gtk.FileChooserDialog(parent=self, action=action)
        if action == Gtk.FileChooserAction.SAVE:
            dialog.set_current_name("Untitled.sams")
            dialog.set_title("Save selection as script file. ")
            confirm = Gtk.STOCK_SAVE
        else:
            dialog.set_title("Select script file to execute")
            confirm = Gtk.STOCK_OPEN
        dialog.set_current_folder("./scripts/")

        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            confirm,
            Gtk.ResponseType.OK,
        )

        # Custom file filter that only allows text files with the suffix .sams
        filter_sams = Gtk.FileFilter()
        filter_sams.set_name("SAMScript Files")
        filter_sams.add_mime_type("text/plain")
        filter_sams.add_pattern("*.sams")
        dialog.add_filter(filter_sams)

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
        else:
            filename = None

        dialog.destroy()

        return response, filename

    def save_script(self, button, *data):
        """ Converts selected history to text and saves it to a .sams file. """

        history = []

        # Adapted from StackOverflow. Gets the current selection. No idea why it has to be this complicated
        tree_selection = self.history_list.get_selection()
        model, pathlist = tree_selection.get_selected_rows()
        for path in pathlist :
            tree_iter = model.get_iter(path)
            value = model.get_value(tree_iter,0)
            history.append(value)

        if len(history) <= 1:
            # Haven't selected anything, or only selected a single action, so we save the whole history
            history = [x[0] for x in list(self.history)]

        response, filename = self.filechooser_dialog(Gtk.FileChooserAction.SAVE)    # Throw up the file chooser dialog
        if response == Gtk.ResponseType.OK:
            file = open(filename, "w")
            for command in history[:-1]:
                file.write(command.replace("n", "N"))
            file.write(history[-1])
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")

    def send_command(self, button, *data):
        """ Sends general commands over the serial connection """

        if self.ser is not None:
            if data[0] in "wr":
                processed_data = (data[0], int(data[1].get_value()), 0)
                #data[1].set_text("")
            else:
                processed_data = data
            command = "%s_%s_%s_n" % processed_data
            self.update_history(command)
            self.ser.write(command.encode())
        else:
            print("Failed to send command, please check usb/bluetooth connection and try again")

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
                ser = serial.Serial('/dev/COM1')
                self.usb_icon.set_opacity(1)
            except serial.serialutil.SerialException as e:
                print("USB connection failed.")
                self.usb_icon.set_opacity(0.5)
        
        if ser != None:
            self.sensitivity(True)

        return ser

    def get_bt_connection(self, button):
        """ BT Button function, attempts to create bluetooth connection """
        print("Bluetooth unsupported on Windows. ")

    def get_usb_connection(self, button, event):
        """ USB button function. Attempts to create a USB connection, or if button is shift clicked, create a fake debug connection"""

        if hasattr(event, 'keyval'):
            if Gdk.keyval_name(event.keyval) != "space":
                return 1

        if event.get_state() & Gdk.ModifierType.SHIFT_MASK:
            self.ser = DummySerial()
            self.usb_icon.set_opacity(1)
            self.bt_icon.set_opacity(0.5)
            self.sensitivity(True)
            self.display_warning(True)
            print("Using debug serial. THIS WILL NOT SEND DATA TO THE ROBOT! ")
        else:
            for n in range(0, 20):
                try: 
                    self.ser = serial.Serial("COM%s" % n)
                    self.usb_icon.set_opacity(1)
                    self.bt_icon.set_opacity(0.5)
                    self.sensitivity(True)
                    self.display_warning(False)
                    return 1
                except serial.serialutil.SerialException:
                    pass
            print("USB connection failed.")
            self.usb_icon.set_opacity(0.5)
            self.sensitivity(False)
            self.display_warning(False)

    def create_control_block(self, col, label_text):
        col.pack_start(Gtk.Label(label="<big>%s</big>" % label_text, use_markup=True), False, True, 10)

        control_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        col.pack_start(control_box, False, True, 10)

        return control_box

    def create_arrow_block(self, control_box, id, invert=False):
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        control_box.pack_start(container, False, True, 10)

        left_button = Gtk.Button(label="<", tooltip_text="Move 10 degrees towards the limit switch. ")
        right_button = Gtk.Button(label=">", tooltip_text="Move 10 degrees away from the limit switch. ")
        container.pack_start(left_button, True, True, 0)
        container.pack_end(right_button, True, True, 0)

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

    def create_slider_block(self, grid, id, min, max, label_text, n):
        label = Gtk.Label(label=label_text, use_markup=True)
        grid.attach(label, 0, n*2, 2, 2)

        adj = Gtk.Adjustment(value=90, lower=0, upper=180, step_increment=5, page_increment=0)
        slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        slider.set_digits(0)
        slider.set_hexpand(True)
        slider.connect("value_changed", self.send_command, id, slider)

        grid.attach_next_to(slider, label, Gtk.PositionType.RIGHT, 6, 2)

    def precise_movement_block(self, box, id, max):
        """ Creates a block with a slider and a button for precise movement """

        grid = Gtk.Grid()
        box.pack_start(grid, True, True, 0)

        adj = Gtk.Adjustment(value=0, lower=-max, upper=max, step_increment=5, page_increment=0)
        slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment = adj)
        slider.set_digits(0)
        slider.set_hexpand(True)
        
        grid.attach(slider, 0, 0, 8, 1)

        button = Gtk.Button(label="Go", tooltip_text="Move by the specified angle. ")
        grid.attach_next_to(button, slider, Gtk.PositionType.RIGHT, 2, 1)

        button.connect("clicked", self.precise_movement, id, slider)

    def precise_movement(self, button, *data):
        id, val = data[0], data[1].get_value()
        data[1].set_value(0)

        if val >= 0:
            dir = 1
        else:
            dir = 0

        self.send_command(button, id, abs(int(val)), dir)

    def error_handler(self, exception_type, value, traceback):
        if exception_type == serial.SerialException:
            self.get_serial_connection()
        else:
            print(value)

win = Window()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
