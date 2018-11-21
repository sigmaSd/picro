#!/bin/python

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gdk, Gio, GLib, GdkPixbuf, GObject

import os
import sys
import subprocess
from threading import Thread

# Needed to remove stdout
FNULL = open(os.devnull, 'w')


class MainWindow(Gtk.Window):
    def __init__(self, win_type='picro'):
        Gtk.Window.__init__(self, title="Pic Organizer")
        self.bootstrap()

        self.type = win_type

        self.img_groups = {}
        self.imgs_with_keywords = {}
        self.img_paths = None

        self.grid = self._grid()

        self.main_win = Gtk.ScrolledWindow.new()
        self.main_win.add(self.grid)

        self.progress_bar = self.create_progress_bar()
        self.group_names_input = self._group_names_input()
        self.search_bar = self._search_bar()

        if self.type == 'picro':
            self.vbox = self.picro_window()
        else:
            # self.type == 'viewer'
            self.vbox = self.viewer_window()

        self.add(self.vbox)
        self.show_all()

        # hide stuff
        self.search_bar.hide()

        self.img_fetch_thread = None

    def picro_window(self):
        vbox = Gtk.Box.new(Gtk.Orientation(1), 0)
        vbox.pack_start(self.progress_bar, False, False, 10)
        vbox.pack_start(self.main_win, True, True, 0)
        vbox.pack_start(self.group_names_input, False, False, 0)
        vbox.pack_start(self.finish_btn(), False, False, 0)
        return vbox

    def viewer_window(self):
        vbox = Gtk.Box.new(Gtk.Orientation(1), 0)
        vbox.pack_start(self.progress_bar, False, False, 10)
        vbox.pack_start(self.search_bar, False, False, 10)
        vbox.pack_start(self.main_win, True, True, 0)
        return vbox

    def bootstrap(self):
        self.connect("destroy", Gtk.main_quit)
        self.connect("key_press_event", self.core_game)

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

    def _grid(self):
        grid = Gtk.FlowBox.new()
        if self.type == 'picro':
            grid.set_sort_func(self.picro_sort)
        else:
            pass
            #self.type == 'viewer'
            # grid.set_sort_func(self.viewer_sort)

        return grid

    def _search_bar(self):
        search_bar = Gtk.Entry.new()
        search_bar.set_placeholder_text('Search for images by keywords')
        search_bar.connect('changed', self.filter_search)
        icon_search = Gio.ThemedIcon(name="edit-find-symbolic")
        search_bar.set_icon_from_gicon(
            Gtk.EntryIconPosition.SECONDARY, icon_search)
        return search_bar

    def create_progress_bar(self):
        label = Gtk.Label.new()
        label.props.margin_left = 10
        progress = Gtk.ProgressBar.new()
        hbox = Gtk.Box.new(Gtk.Orientation(0), 0)
        hbox.pack_start(label, False, False, 10)
        hbox.pack_start(progress, True, True, 0)
        return hbox

    def add_progress(self, progress):
        self.progress_bar.get_children()[1].set_fraction(progress)

    def progress_label(self, label):
        self.reset_progress()
        self.progress_bar.get_children()[0].set_label(label)
        self.progress_bar.show_all()

    def reset_progress(self):
        self.add_progress(0)

    def _group_names_input(self):

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

    def groups_names_input_is_focused(self):
        """Returns True if atleast one of the input menus is focused"""
        return any(child for child in self.group_names_input.get_child(
        ).get_child().get_children() if child.get_children()[1].has_focus())

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

        def add_keywords():
            current_prgoress = 0
            for key, value in self.img_groups.items():
                index = translate(key)
                for ref_idx, name in grp_names_list:
                    if index == int(ref_idx):
                        group_name = name
                for v in value:
                    img_file = v[1]
                    if group_name:
                        keyword = '-keywords=%s' % group_name

                        subprocess.call(
                            ['exiftool', '-overwrite_original', img_file, keyword], stdout=FNULL)
                        progress = current_prgoress / (img_count - 1)
                        GLib.idle_add(self.add_progress, progress)
                        current_prgoress += 1

            os._exit(0)

        grp_names_list = self.get_entred_groups_names()
        # delete untagged pic from dict, order pic
        del self.img_groups[65466]

        img_count = sum(len(v) for v in self.img_groups.values())
        self.progress_label('Adding keywords to images')

        Thread(target=add_keywords).start()

    def get_entred_groups_names(self):
        names_list = []
        # cool fn
        # need to make a wrapper around the internals!
        names_boxes = self.vbox.get_children()[2].get_children()[
            0].get_children()[0].get_children()
        for box in names_boxes:
            names_list.append(
                (box.get_children()[0].get_text(), box.get_children()[1].get_text()))
        return names_list

    def start(self):
        self.img_fetch_thread = Thread(target=self.add_icons)
        self.img_fetch_thread.start()

    def add_icons(self):
        files = os.listdir(os.path.curdir)
        files_num = len(files)
        tmp_list = []

        def add_to_grid():
            self.grid.add(img[0])

        def image_to_flowbox():
            if img[1] in self.imgs_with_keywords.keys():
                self.imgs_with_keywords[img[0]
                                        ] = self.imgs_with_keywords.pop(img[1])

        def read_keywords():
            current_prgoress = 0
            for img in img_list:
                out = subprocess.check_output(
                    ['exiftool', img]).decode('UTF-8')
                keyword_line = [l for l in out.splitlines() if 'Keywords' in l]
                if keyword_line:
                    keyword = keyword_line[0].split(':')[1].strip()
                    self.imgs_with_keywords[img] = keyword

                progress = current_prgoress / (img_num - 1)
                GLib.idle_add(self.add_progress, progress)
                current_prgoress += 1

        def filter_images():
            self.progress_label("Looking for images")
            img_list = []
            for idx, f in enumerate(files):
                progress = idx / (files_num - 1)
                out = subprocess.check_output(["file", f]).decode("UTF-8")
                if "JPEG" in out or "PNG" in out:
                    img_list.append(f)
                GLib.idle_add(self.add_progress, progress)
            return img_list

        img_list = filter_images()
        if not img_list:
            print("No images found in current directory")
            quit()
        img_num = len(img_list)

        if self.type == 'viewer':
            self.progress_label('Reading images keywords')
            read_keywords()

        self.progress_label("Creating icons")
        if self.type == 'viewer':
            def manual_sort():
                out = []
                for img in self.imgs_with_keywords.keys():
                    idx = img_list.index(img)
                    if idx != -1:
                        del img_list[idx]
                sorted_list = sorted(
                    self.imgs_with_keywords.items(), key=lambda x: x[1])
                for v, _ in sorted_list:
                    out.append(v)
                out += img_list
                return out

            img_list = manual_sort()
        for idx, img_file in enumerate(img_list):
            img = self.create_images(img_file)
            GLib.idle_add(add_to_grid)

            if self.type == 'viewer':
                GLib.idle_add(image_to_flowbox)

            progress = idx/(img_num - 1)
            GLib.idle_add(self.add_progress, progress)

            tmp_list.append(img[1])

        # workaround race condition
        self.img_paths = tmp_list

        self.progress_bar.hide()
        self.search_bar.show()

    def create_images(self, f):
        icn = GdkPixbuf.Pixbuf.new_from_file_at_size(f, 420, 420)
        img = Gtk.Image.new_from_pixbuf(icn)
        flow_box_child = Gtk.FlowBoxChild.new()
        flow_box_child.add(img)
        flow_box_child.show_all()
        return (flow_box_child, f)

    def core_game(self, _, key):
        if self.type == 'viewer':
            return

        if self.groups_names_input_is_focused():
            self.grid.unselect_all()
            return

        if self.img_fetch_thread.is_alive():
            return

        # fill self.img_groups in main thread to avoid race condition
        if self.img_paths and not self.img_groups:
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

    def filter_search(self, entry):
        self.grid.set_filter_func(self._sort, entry)

    def _sort(self, child, entry):
        if not entry.get_text():
            return True
        if child not in self.imgs_with_keywords and entry.get_text():
            return False

        key = self.imgs_with_keywords[child]

        if entry.get_text() in key:
            return True
        return False

    # def viewer_sort(self, child1, child2):
    #    key1 = self.imgs_with_keywords.get(child1, '')
    #    key2 = self.imgs_with_keywords.get(child2, '')
    #    print(key1, key2)
    #    if key1 > key2:
    #        return 1
    #    elif key2 > key1:
    #        return -1
    #    else:
    #        return 0

    def picro_sort(self, child1, child2):

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


if len(sys.argv) == 1:
    win = MainWindow('picro')
else:
    if sys.argv[1] == '-v' or sys.argv[1] == '--viewer':
        win = MainWindow('viewer')


Gtk.init()
win.start()
Gtk.main()
