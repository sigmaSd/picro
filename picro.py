import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, GdkPixbuf, Gdk, GObject, GLib

import os
import subprocess
import collections
from threading import Thread


class MainWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Pic Organizer")
        self.bootstrap()

        self.pos = (0, 0)
        self.radio_group = Gtk.RadioButton.new(None)
        self.radio_img_list = []
        self.connect("key_press_event", self.core_game)
        self.img_groups = {}

        self.grid = Gtk.FlowBox.new()
        self.grid.set_sort_func(self.rearrange)
        self.scrolled_win = Gtk.ScrolledWindow.new()
        self.scrolled_win.add(self.grid)

        self.img_paths = None
        self.progress_bar = self.create_progress_bar()

        self.vbox = Gtk.Box.new(Gtk.Orientation(1), 0)
        self.vbox.pack_start(self.progress_bar, False, False, 10)
        self.vbox.pack_start(self.scrolled_win, True, True, 0)
        self.vbox.pack_start(self.group_names_input(), False, False, 0)
        self.vbox.pack_start(self.finish_btn(), False, False, 0)

        self.add(self.vbox)
        self.show_all()
        self.img_fetch_thread = None

    def start(self):
        self.img_fetch_thread = Thread(target=self.add_icons)
        self.img_fetch_thread.start()

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

    def create_progress_bar(self):
        label = Gtk.Label.new()
        label.props.margin_left = 10
        progress = Gtk.ProgressBar.new()
        hbox = Gtk.Box.new(Gtk.Orientation(0), 0)
        hbox.pack_start(label, False, False, 10)
        hbox.pack_start(progress, True, True, 0)
        return hbox

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
            "Name your groups than click 'Done' when you're finished")
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
        # delete untagged pic from dict, order pic
        del self.img_groups[65466]
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

        quit()

    def get_entred_groups_names(self):
        names_list = []
        # cool fn
        names_boxes = self.vbox.get_children()[2].get_children()[
            0].get_children()[0].get_children()
        for box in names_boxes:
            names_list.append(
                (box.get_children()[0].get_text(), box.get_children()[1].get_text()))
        return names_list

    def add_icons(self):
        files = os.listdir(os.path.curdir)
        files_num = len(files)
        tmp_list = []

        def add_progress(progress):
            self.progress_bar.get_children()[1].set_fraction(progress)

        def progress_label(label):
            self.progress_bar.get_children()[0].set_label(label)

        def filter_images():
            progress_label("Looking for images")
            img_list = []
            for idx, f in enumerate(files):
                progress = idx / (files_num - 1)
                out = subprocess.check_output(["file", f]).decode("UTF-8")
                if "JPEG" in out or "PNG" in out:
                    img_list.append(f)
                GLib.idle_add(add_progress, progress)
            return img_list

        img_list = filter_images()
        if not img_list:
            print("No images found in current directory")
            quit()
        img_num = len(img_list)

        for idx, img in enumerate(img_list):
            progress_label("Creating icons")
            img = self.create_images(img)
            GLib.idle_add(self.grid.add, img[0])

            progress = idx/(img_num - 1)
            GLib.idle_add(add_progress, progress)

            tmp_list.append(img[1])
        # workaround race condition
        self.img_paths = tmp_list
        self.progress_bar.hide()

    def create_images(self, f):
        icn = GdkPixbuf.Pixbuf.new_from_file_at_size(f, 420, 420)
        img = Gtk.Image.new_from_pixbuf(icn)
        img.show()
        return (img, f)

    def core_game(self, _, key):

        if not self.img_paths:
            return

        # fill self.img_groups in main thread to avoid race condition
        if not self.img_groups:
            self.img_groups[65466] = list(
                zip(self.grid.get_children(), self.img_paths))

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
win.start()
Gtk.main()
