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
        self._bootstrap()

        self.type = win_type

        # Class var
        self.img_groups = {}
        self.imgs_with_keywords = {}
        self.img_paths = []

        # GUI
        self.scrolled_win = self._scrolled_win()
        self.grid = self._grid()
        self.progress_bar = self._progress_bar()
        self.group_names_input = self._group_names_input()
        self.search_bar = self._search_bar()
        self.done_bar = self._done_bar()

        self.scrolled_win.add(self.grid)

        if self.type == 'picro':
            self.vbox = self.picro_window()
        else:
            # self.type == 'viewer'
            self.vbox = self.viewer_window()

        self.add(self.vbox)
        self.show_all()

        # hide stuff
        self.search_bar.hide()

        # separate thread to fetch images
        self.img_fetch_thread = None

    def picro_window(self):
        """Window initialized on picro mode"""
        vbox = Gtk.Box.new(Gtk.Orientation(1), 0)
        vbox.pack_start(self.progress_bar, False, False, 10)
        vbox.pack_start(self.scrolled_win, True, True, 0)
        vbox.pack_start(self.group_names_input, False, False, 0)
        vbox.pack_start(self.done_bar, False, False, 0)
        return vbox

    def viewer_window(self):
        """Window initialized on viewer mode"""
        vbox = Gtk.Box.new(Gtk.Orientation(1), 0)
        vbox.pack_start(self.progress_bar, False, False, 10)
        vbox.pack_start(self.search_bar, False, False, 10)
        vbox.pack_start(self.scrolled_win, True, True, 0)
        return vbox

    def _bootstrap(self):
        """ Initialize the main window"""
        self.connect("destroy", Gtk.main_quit)
        self.connect("key_press_event", self._core_func)

        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        if not monitor:
            # Arbitrarily decide that the first monitor is the primary one as a fallback
            monitor = display.get_monitor(0)
        geometry = monitor.get_geometry()
        scale_factor = monitor.get_scale_factor()
        width = scale_factor * geometry.width
        height = scale_factor * geometry.height
        self.resize(width, height)

    def _scrolled_win(self):
        return Gtk.ScrolledWindow.new()

    def _grid(self):
        grid = Gtk.FlowBox.new()
        grid.set_sort_func(self._picro_sort)
        return grid

    def _search_bar(self):
        search_bar = Gtk.Entry.new()
        search_bar.set_placeholder_text('Search for images by keywords')
        search_bar.connect('changed', self._filter_search)
        icon_search = Gio.ThemedIcon(name="edit-find-symbolic")
        search_bar.set_icon_from_gicon(
            Gtk.EntryIconPosition.SECONDARY, icon_search)
        return search_bar

    def _progress_bar(self):
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
        """Reset the progress bar, add a new label to it and show it"""
        def _reset_progress():
            self.add_progress(0)

        _reset_progress()
        self.progress_bar.get_children()[0].set_label(label)
        self.progress_bar.show_all()

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

    def _get_entered_groups_names(self):
        """Get inputted group names and corresponding label"""
        names_list = []
        names_boxes = self.group_names_input.get_child().get_child()
        for box in names_boxes:
            names_list.append(
                (box.get_children()[0].get_text(), box.get_children()[1].get_text()))
        return names_list

    # Hack? to avoid modifying pictures when writing the group name
    def _groups_names_input_is_focused(self):
        """Returns True if at least one of the input menus is focused"""
        return any(child for child in self.group_names_input.get_child(
        ).get_child().get_children() if child.get_children()[1].has_focus())

    def _done_bar(self):
        label = Gtk.Label.new(
            "Name your groups than click 'Done' when you're finished")
        button = Gtk.Button.new_with_label("Done")
        button.connect('clicked', self._on_done_pressed)
        hbox = Gtk.Box.new(Gtk.Orientation(0), 0)
        hbox.pack_start(label, True, True, 0)
        hbox.pack_start(button, True, True, 0)

        return hbox

    def _on_done_pressed(self, _widget):
        """Callback -> Add keywords to images"""
        def translate(i):
            # 65457 corresponds to KEY_PAD_1
            return i - 65456

        def add_keywords():
            current_progress = 0
            for key, image_list in self.img_groups.items():
                index = translate(key)
                for label_index, inputted_name in grp_names_list:
                    if index == int(label_index):
                        group_name = inputted_name
                for _, image_file in image_list:
                    if group_name:
                        keyword = '-keywords=%s' % group_name

                        subprocess.call(
                            ['exiftool', '-overwrite_original', image_file, keyword], stdout=FNULL)
                        progress = current_progress / (img_count - 1)
                        GLib.idle_add(self.add_progress, progress)
                        current_progress += 1

            os._exit(0)

        grp_names_list = self._get_entered_groups_names()
        # delete untagged pic from dict
        del self.img_groups[65466]

        img_count = sum(len(v) for v in self.img_groups.values())

        self.progress_label('Adding keywords to images')
        Thread(target=add_keywords).start()

    def _add_icons(self):
        """Create icons from current dir images"""
        files = os.listdir(os.path.curdir)
        files_num = len(files)
        tmp_list = []

        def add_to_grid():
            self.grid.add(img[0])

        def image_to_flowbox_child():
            if img[1] in self.imgs_with_keywords:
                self.imgs_with_keywords[img[0]
                                        ] = self.imgs_with_keywords.pop(img[1])

        def read_keywords():
            current_progress = 0
            for img in img_list:
                out = subprocess.check_output(
                    ['exiftool', img]).decode('UTF-8')
                keyword_line = [l for l in out.splitlines() if 'Keywords' in l]
                if keyword_line:
                    keyword = keyword_line[0].split(':')[1].strip()
                    self.imgs_with_keywords[img] = keyword

                progress = current_progress / (img_num - 1)
                GLib.idle_add(self.add_progress, progress)
                current_progress += 1

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

        # Find images step
        img_list = filter_images()
        if not img_list:
            print("No images found in current directory")
            quit()
        img_num = len(img_list)

        # In case of viewer: Read image keywords step
        if self.type == 'viewer':
            def manual_sort():
                out = []
                for img in self.imgs_with_keywords:
                    idx = img_list.index(img)
                    if idx != -1:
                        del img_list[idx]
                sorted_list = sorted(
                    self.imgs_with_keywords.items(), key=lambda x: x[1])
                for v, _ in sorted_list:
                    out.append(v)
                out += img_list
                return out

            self.progress_label('Reading images keywords')
            read_keywords()

            img_list = manual_sort()

        # Create icons step
        self.progress_label("Creating icons")

        for idx, img_file in enumerate(img_list):
            img = self._create_images(img_file)
            GLib.idle_add(add_to_grid)

            if self.type == 'viewer':
                GLib.idle_add(image_to_flowbox_child)

            progress = idx/(img_num - 1)
            GLib.idle_add(self.add_progress, progress)

            tmp_list.append(img[1])

        # workaround race condition
        self.img_paths = tmp_list

        self.progress_bar.hide()
        self.search_bar.show()

    def _create_images(self, f):
        icn = GdkPixbuf.Pixbuf.new_from_file_at_size(f, 420, 420)
        img = Gtk.Image.new_from_pixbuf(icn)
        flow_box_child = Gtk.FlowBoxChild.new()
        flow_box_child.add(img)
        flow_box_child.show_all()
        return (flow_box_child, f)

    def _core_func(self, _, key):
        """Callback to key press event -> Sort pictures"""
        if self.type == 'viewer':
            return

        if self._groups_names_input_is_focused():
            self.grid.unselect_all()
            return

        if self.img_fetch_thread.is_alive():
            return

        # fill self.img_groups in main thread to avoid race condition
        if self.img_paths and not self.img_groups:
            self.img_groups[65466] = list(
                zip(self.grid.get_children(), self.img_paths))

        # KEY_PAD_1: 65457, KEY_PAD_9: 65465
        key_val = key.get_keyval()[1]
        if key_val not in range(65457, 65466):
            return

        if not self.grid.get_selected_children():
            return

        active_img = self.grid.get_selected_children()[0]
        active_img = self._search_dict_for_img(active_img)
        self._add_img_to_grp(key_val, active_img)

        # signal sort fn
        active_img[0].changed()

    def _search_dict_for_img(self, active_img):
        for img_list in self.img_groups.values():
            if img_list:
                active_img_list = [
                    img for img in img_list if active_img in img]
                if active_img_list:
                    return active_img_list[0]
        return None

    def _add_img_to_grp(self, key_val, active_img):
        for list_img in self.img_groups.values():
            if active_img in list_img:
                idx = list_img.index(active_img)
                del list_img[idx]
                break

        if key_val not in self.img_groups:
            self.img_groups[key_val] = [active_img]
        else:
            self.img_groups[key_val].append(active_img)

    def _filter_search(self, entry):
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

    def _picro_sort(self, child1, child2):

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

    def start(self):
        """Cooler name for self._add_icons + different thread"""
        self.img_fetch_thread = Thread(target=self._add_icons)
        self.img_fetch_thread.start()


if len(sys.argv) == 1:
    win = MainWindow('picro')
else:
    if sys.argv[1] == '-v' or sys.argv[1] == '--viewer':
        win = MainWindow('viewer')


Gtk.init()
win.start()
Gtk.main()
