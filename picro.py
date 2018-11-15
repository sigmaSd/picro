import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, GdkPixbuf, Gdk, GObject

import os
import subprocess

import collections


class MainWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Pic Organizer")
        self.bootstrap()

        self.pos = (0, 0)
        self.radio_group = Gtk.RadioButton.new(None)
        self.radio_img_list = []
        self.connect("key_press_event", self.core_game)
        self.img_groups = {}

        self.grid = Gtk.Grid.new()
        self.scrolled_win = Gtk.ScrolledWindow.new()
        self.scrolled_win.add(self.grid)

        self.vbox = Gtk.Box.new(Gtk.Orientation(1), 0)
        self.vbox.pack_start(self.scrolled_win, True, True, 0)
        self.vbox.pack_start(self.group_names(), False, False, 0)
        self.vbox.pack_start(self.finish_btn(), False, False, 0)

        self.add(self.vbox)
        self.add_icons()

    def bootstrap(self):
        self.connect("destroy", Gtk.main_quit)
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        if not monitor:
            # Randomly decide that the first monitor is the primary one as a fallback
            monitor = display.get_monitor(0)
        geometry = monitor.get_geometry()
        scale_factor = monitor.get_scale_factor()
        # need it for magic stuff
        self.width = scale_factor * geometry.width
        height = scale_factor * geometry.height
        self.resize(self.width, height)

    def finish_btn(self):
        label = Gtk.Label.new(
            "Name your groups than click Done when you're finished")
        button = Gtk.Button.new_with_label("Done")
        button.connect('clicked', self.on_done_pressed)
        hbox = Gtk.Box.new(Gtk.Orientation(0), 0)
        hbox.pack_start(label, True, True, 0)
        hbox.pack_start(button, True, True, 0)

        return hbox

    def get_entred_groups_names(self):
        names_list = []
        # cool fn
        names_boxes = self.vbox.get_children()[1].get_children()[
            0].get_children()[0].get_children()
        for box in names_boxes:
            names_list.append(
                (box.get_children()[0].get_text(), box.get_children()[1].get_text()))
        return names_list

    def on_done_pressed(self, _widget):
        def translate(i):
            return i - 65456
        grp_names_list = self.get_entred_groups_names()
        for key, value in self.img_groups.items():
            index = translate(key)
            for ref_idx, name in grp_names_list:
                if index == int(ref_idx):
                    group_name = name
            for v in value:
                img_file = v[1]
                if group_name:
                    new_name = "%s-%s" % (group_name, img_file)
                    os.rename(img_file, new_name)

    def group_names(self):

        group_names = Gtk.Box.new(Gtk.Orientation(0), 0)
        for i in range(1, 10):
            label = Gtk.Label.new(str(i))
            entry = Gtk.Entry.new()
            hbox = Gtk.Box.new(Gtk.Orientation(0), 0)
            hbox.pack_start(label, True, True, 0)
            hbox.pack_start(entry, True, True, 0)
            group_names.pack_start(hbox, True, True, 0)

        grp_scrolled_win = Gtk.ScrolledWindow.new()
        grp_scrolled_win.add(group_names)

        return grp_scrolled_win

    def create_icons(self, f):
        icn = GdkPixbuf.Pixbuf.new_from_file_at_size(f, 420, 420)
        img = Gtk.Image.new_from_pixbuf(icn)
        rb = Gtk.RadioButton.new_from_widget(self.radio_group)
        rb.add(img)
        self.radio_img_list.append((rb, f))

    def core_game(self, _, key):
        key_val = key.get_keyval()[1]
        if key_val not in range(65457, 65466):
            return
        active_img = self.search_list_for_img()

        if not active_img:
            active_img = self.search_dict_for_img()

        self.add_img_to_grp(key_val, active_img)
        self.rearrange()

    def search_list_for_img(self):
        if len(self.radio_img_list) > 0:
            active_img = [
                img for img in self.radio_img_list if img[0].get_active() == True]

            if len(active_img) > 0:
                active_img = active_img[0]
                self.move_img(active_img)
                return active_img

            return None
        return None

    def search_dict_for_img(self):
        for img_list in self.img_groups.values():
            for img in img_list:
                if img[0].get_active():
                    return img

    def add_img_to_grp(self, key_val, active_img):
        for list_img in self.img_groups.values():
            list_img: list
            if active_img in list_img:
                idx = list_img.index(active_img)
                del list_img[idx]
                break

        if key_val not in self.img_groups.keys():
            self.img_groups[key_val] = [active_img]
        else:
            self.img_groups[key_val].append(active_img)

    def move_img(self, active_img):
        out_list = []
        for img in self.radio_img_list:
            if active_img != img:
                out_list.append(img)
        self.radio_img_list = out_list

    def clear_grid(self):
        self.pos = (0, 0)
        for child in self.grid.get_children():
            self.grid.remove(child)

    def rearrange(self):
        # perf !!!
        self.img_groups = collections.OrderedDict(
            sorted(self.img_groups.items()))
        out_list = []
        for list_img in self.img_groups.values():
            out_list += list_img
        # render non assigned images
        out_list += self.radio_img_list

        self.fill_grid(out_list)
        self.show_all()

    def add_icons(self):
        files = os.listdir(os.path.curdir)
        for f in files:
            out = subprocess.check_output(["file", f]).decode("UTF-8")
            if "JPEG" in out or "PNG" in out:
                self.create_icons(f)

        self.fill_grid(self.radio_img_list)

    def fill_grid(self, img_list):
        self.clear_grid()
        for img in img_list:
            col_n, row_n = self.pos
            self.grid.attach(img[0], col_n, row_n, 1, 1)
            self.advance()

    def advance(self):
        # Magic
        MAX_W = self.width / 500
        col_n, row_n = self.pos
        if col_n < MAX_W - 1:
            col_n += 1
        else:
            col_n = 0
            row_n += 1
        self.pos = (col_n, row_n)


Gtk.init()
win = MainWindow()
win.show_all()
Gtk.main()
