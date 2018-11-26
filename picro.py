#!/usr/bin/python

from threading import Thread
import signal
import subprocess
import sys
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GLib, GdkPixbuf, GObject


# Needed to remove stdout
FNULL = open(os.devnull, 'w')
# Blacklist some file types
BLACKLIST = ['vnd.fpx']


# Exit properly when Ctrl-c is hit
def signal_handler(sig, frame):
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


# Core
class MainWindow(Gtk.Window):
    def __init__(self, win_type='picro'):
        Gtk.Window.__init__(self, title="Pic Organizer")
        self._bootstrap()

        self.type = win_type

        # Class var
        self.img_groups = {}
        self.imgs_with_keywords = {}
        self.img_paths = []
        self.event_type = None
        self.key_holder = []
        # var used to signal operation end
        self.operation_done = None

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

    def progress_pulse(self):
        def pulse():
            if not self.operation_done:
                self.progress_bar.get_children()[1].pulse()
                return True
            else:
                return False
        self.operation_done = False
        GLib.timeout_add(1000, pulse)

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

        def add_keywords():
            current_progress = 0
            for key, image_list in self.img_groups.items():
                index = key
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
            FNULL.close()
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
        img_list = []
        tmp_list = []

        def discover_images():
            self.progress_label('Discovering images')
            self.progress_pulse()

            exiftool_cmd = ['exiftool', '-fast2'] + files
            out = subprocess.run(exiftool_cmd, errors='ignore',
                                 check=False, stdout=subprocess.PIPE).stdout
            tmp_file_name = ''

            for line in out.splitlines():
                if 'Error' in line:
                    # file type can't be read
                    pass

                elif '========' in line:
                    filename = line.split()[1]
                    tmp_file_name = filename

                elif 'MIME Type' in line:
                    if any(filetype for filetype in BLACKLIST if filetype in line) or 'image' not in line:
                        # not an image or file type is blacklisted
                        tmp_file_name = ''
                    else:
                        # 'image' in line:
                        img_list.append(tmp_file_name)

                elif 'Keywords' in line:
                    if tmp_file_name:
                        keywords = line.split(':')[1].strip()
                        self.imgs_with_keywords[tmp_file_name] = keywords
                        tmp_file_name = ''

            self.operation_done = True

        def sort_by_keywords():
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

        def create_icons(image_files):
            def add_to_grid(image):
                self.grid.add(image[0])

            def image_to_flowbox_child():
                if img[1] in self.imgs_with_keywords:
                    self.imgs_with_keywords[img[0]
                                            ] = self.imgs_with_keywords.pop(img[1])

            self.progress_label("Creating icons")

            img_num = len(image_files)
            for idx, img_file in enumerate(image_files):
                img = self._create_images(img_file)
                if img:
                    GLib.idle_add(add_to_grid, img)

                    if self.type == 'viewer':
                        GLib.idle_add(image_to_flowbox_child)

                    progress = idx/(img_num - 1)
                    GLib.idle_add(self.add_progress, progress)

                    tmp_list.append(img[1])

        if self.type == 'viewer':
            # Discover images step
            discover_images()
            # Sort images by keywords step
            img_list = sort_by_keywords()
        else:
            # self.type = 'picro':
            img_list = files

        # Create icons step
        create_icons(img_list)

        # workaround race condition
        self.img_paths = tmp_list

        # GUI stuff
        self.progress_bar.hide()
        self.search_bar.show()

    def _create_images(self, f):
        try:
            icn = GdkPixbuf.Pixbuf.new_from_file_at_size(f, 420, 420)
        except:
            # Not an image
            return None
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

        def add_to_primary_group(key_val):
            print('fst')
            if not self.grid.get_selected_children():
                return

            active_img = self.grid.get_selected_children()[0]
            active_img = self._search_dict_for_img(active_img)
            self._add_img_to_grp(key_val, active_img)

            # signal sort fn
            active_img[0].changed()

        def add_to_secondary_group(key_val1, key_val2):
            print('sec')
            if key_val1 in self.img_groups:
                print('do stuff')

        def handle_key():
            try:
                key_val = int(key.string)
            except ValueError:
                # not a number key
                return

            self.key_holder.append(key_val)
            # idle
            print(key.get_event_type())
            if not self.event_type:
                if key.get_event_type() == Gdk.EventType.KEY_PRESS:
                    self.event_type = 'press'
                    # we ignore the first press
                    return
                elif key.get_event_type() == Gdk.EventType.KEY_RELEASE:
                    self.event_type = 'release'
            print(self.event_type)
            # One key held and another one pressed
            if self.event_type == 'press':
                key_val1 = self.key_holder[0]
                key_val2 = key_val
                add_to_secondary_group(key_val1, key_val2)
                self.key_holder = []
            # one key pressed and released
            if self.event_type == 'release':
                # Ignore key relases after multiple key hit
                if len(self.key_holder) == 1:
                    add_to_primary_group(key_val)
                    self.key_holder = []

        handle_key()

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
