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

        #self.grid = Gtk.Grid.new()
        self.grid = Gtk.FlowBox.new()
        self.grid.set_sort_func(self.rearrange)
        self.scrolled_win = Gtk.ScrolledWindow.new()
        self.scrolled_win.add(self.grid)

        self.vbox = Gtk.Box.new(Gtk.Orientation(1), 0)
        self.vbox.pack_start(self.scrolled_win, True, True, 0)
        self.vbox.pack_start(self.group_names_input(), False, False, 0)
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
        width = scale_factor * geometry.width
        height = scale_factor * geometry.height
        self.resize(width, height)

    def group_names_input(self):

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

    def finish_btn(self):
        label = Gtk.Label.new(
            "Name your groups than click Done when you're finished")
        button = Gtk.Button.new_with_label("Done")
        button.connect('clicked', self.on_done_pressed)
        hbox = Gtk.Box.new(Gtk.Orientation(0), 0)
        hbox.pack_start(label, True, True, 0)
        hbox.pack_start(button, True, True, 0)

        return hbox

    def on_done_pressed(self, _widget):
        def translate(i):
            return i - 65456
        grp_names_list = self.get_entred_groups_names()
        # order pic
        self.img_groups = collections.OrderedDict(
            sorted(self.img_groups.items()))
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

    def get_entred_groups_names(self):
        names_list = []
        # cool fn
        names_boxes = self.vbox.get_children()[1].get_children()[
            0].get_children()[0].get_children()
        for box in names_boxes:
            names_list.append(
                (box.get_children()[0].get_text(), box.get_children()[1].get_text()))
        return names_list

    def add_icons(self):
        files = os.listdir(os.path.curdir)
        tmp_list = []
        for f in files:
            out = subprocess.check_output(["file", f]).decode("UTF-8")
            if "JPEG" in out or "PNG" in out:
                img = self.create_images(f)
                tmp_list.append(img[1])
                self.grid.add(img[0])
        self.img_groups[65466] = list(zip(self.grid.get_children(), tmp_list))

    def create_images(self, f):
        icn = GdkPixbuf.Pixbuf.new_from_file_at_size(f, 420, 420)
        img = Gtk.Image.new_from_pixbuf(icn)
        return (img, f)

    def core_game(self, _, key):
        key_val = key.get_keyval()[1]
        if key_val not in range(65457, 65466):
            return

        if not self.grid.get_selected_children():
            return
        active_img = self.grid.get_selected_children()[0]
        active_img = self.search_dict_for_img(active_img)
        self.add_img_to_grp(key_val, active_img)
        # signal sort fn
        active_img[0].changed()

    def search_dict_for_img(self, active_img):
        for img_list in self.img_groups.values():
            if img_list:
                active_img_list = [
                    img for img in img_list if active_img in img]
                if active_img_list:
                    return active_img_list[0]

    def add_img_to_grp(self, key_val, active_img):
        for list_img in self.img_groups.values():
            if active_img in list_img:
                idx = list_img.index(active_img)
                del list_img[idx]
                break

        if key_val not in self.img_groups.keys():
            self.img_groups[key_val] = [active_img]
        else:
            self.img_groups[key_val].append(active_img)

    def rearrange(self, child1, child2):

        def search_keys():
            key1 = None
            key2 = None
            for key, value in self.img_groups.items():
                for img, _ in value:
                    if child1 == img:
                        key1 = key
                    if child2 == img:
                        key2 = key
                    if key1 and key2:
                        return key1, key2

        keys = search_keys()
        if keys:
            key1, key2 = keys
            if key1 > key2:
                return 1
            elif key2 > key1:
                return -1
            else:
                return 0
        else:
            return 0


Gtk.init()
win = MainWindow()
win.show_all()
Gtk.main()
