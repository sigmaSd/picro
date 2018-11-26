import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GLib, GdkPixbuf, GObject


def handle_key(_, key):
    print(key.get_event_type())


win = Gtk.Window.new(0)
win.connect("key_press_event", handle_key)
win.show_all()
Gtk.init()

Gtk.main()
