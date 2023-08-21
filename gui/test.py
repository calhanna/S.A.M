import gi
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk

class TestWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        self.resize(400, 400)
        self.connect("delete-event", Gtk.main_quit)

        ls = Gtk.ListStore(str)
        ls.append(["Testrow 1"])
        ls.append(["Testrow 2"])
        ls.append(["Testrow 3"])
        tv = Gtk.TreeView(ls)
        tr = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("Testcolumn", tr, text=0)
        tv.append_column(col)
        sel = tv.get_selection()
        sel.set_mode(Gtk.SelectionMode.MULTIPLE)

        self.add(tv)
        self.show_all()

if __name__ == "__main__":
    app = TestWindow()
    Gtk.main()