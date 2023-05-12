import time
import dearpygui.dearpygui as dpg
import PIL.Image
import io
import numpy as np

from threading import Thread
from turing_machine import Tape, tm_to_diagraph, load_tm, BLANK


class GUI:
    def __init__(self):
        self.size = (1280, 720)
        self.tm = None
        self.paused = True
        self.kill_run_thread = True
        self.run_thread = None
        self.image_size = 1     # doesn't work how I wanted it to
        self.buffer = np.zeros((self.size[1]*self.image_size, self.size[0]*self.image_size, 3), dtype=np.float32)

    def create_image(self) -> np.ndarray:
        if self.tm is None:
            return np.ones((self.size[1]*self.image_size, self.size[0]*self.image_size, 3), dtype=np.float32)

        # some image magic
        g = tm_to_diagraph(self.tm)
        g.graph_attr['rankdir'] = 'LR'
        g.graph_attr['size'] = f"{self.size[1]*self.image_size/96},{self.size[0]*self.image_size/96}"
        g_bytes = g.pipe(format='png')
        img = PIL.Image.open(io.BytesIO(g_bytes))
        img = img.convert('RGB')
        in_numpy = np.array(img)/255.0
        in_numpy = in_numpy.astype(np.float32)
        return in_numpy

    def update_tape_table(self, tape: Tape):
        dpg.delete_item("tape table", children_only=True)
        dpg.add_table_column(parent="tape table", label="Tape", width_fixed=True, width=40)
        for i, symbol in enumerate(tape.tape):
            if symbol == BLANK:
                symbol = '_'
            with dpg.table_row(parent="tape table"):
                if i == tape.head:
                    dpg.add_text(symbol, color=(255, 255, 0))
                else:
                    dpg.add_text(symbol)

    def update_input(self):
        tape = dpg.get_value("input tape")
        if len(str(tape)) != 0 and str(tape)[-1] not in self.tm.input_alphabet:
            while len(str(tape)) > 0 and str(tape)[-1] not in self.tm.input_alphabet:
                tape = tape[:-1]

            # wish this worked
            # dpg.configure_item("input tape", callback=lambda: None)
            # dpg.set_value("input tape", tape)
            # dpg.configure_item("input tape", callback=self.update_input)

            # instead I have to do this
            dpg.delete_item("input tape")
            dpg.add_input_text(label="Input Tape", tag="input tape", callback=self.update_input, default_value=tape, parent="Input", width=-1)
            # dpg.focus_item("input tape")

        self.tm.tape = Tape(list(tape), 0)
        self.update_tape_table(Tape(list(tape), 0))

    def update_graph(self):
        img_array = self.create_image()
        self.buffer[:] = 1.0
        self.buffer[:img_array.shape[0], :img_array.shape[1], :] = img_array

    def update_status(self, status="working"):
        if self.tm is not None:
            if self.tm.is_accepted():
                status = "accepted"
            elif self.tm.is_rejected():
                status = "rejected"
            elif self.tm.is_final():
                status = "final"
        dpg.set_value("status", f"Status: {status}")

    def step_tm(self):
        if self.tm.is_final():
            return
        dpg.configure_item("input tape", enabled=False)
        self.tm.step()
        self.update_status()
        self.update_graph()
        self.update_tape_table(self.tm.tape)

    def run_tm_thread(self):
        while not self.tm.is_final() and not self.paused:
            if self.kill_run_thread:
                return
            self.step_tm()
            time.sleep(dpg.get_value("sleep timer"))

    def run_tm(self):
        if not self.paused:
            self.paused = True
            self.kill_run_thread = True
            self.run_thread.join()
            dpg.configure_item("step self.tm", enabled=True)
            dpg.configure_item("run self.tm", label="Run")
            return

        dpg.configure_item("input tape", enabled=False)
        dpg.configure_item("step self.tm", enabled=False)
        dpg.configure_item("run self.tm", label="Pause")
        self.update_tape_table(self.tm.tape)

        self.kill_run_thread = False
        self.paused = False
        self.run_thread = Thread(target=self.run_tm_thread)
        self.run_thread.start()

    def reset_tm(self):
        dpg.configure_item("run self.tm", label="Run")
        self.paused = True
        self.kill_run_thread = True
        self.tm.reset()
        self.tm.tape = Tape(list(dpg.get_value("input tape")), 0)
        self.update_status("initial")
        self.unlock_input()

    def lock_input(self):
        dpg.configure_item("input tape", enabled=False)
        dpg.configure_item("step self.tm", enabled=False)
        dpg.configure_item("run self.tm", enabled=False)
        dpg.configure_item("reset self.tm", enabled=False)
        dpg.set_value("alphabet", f"Alphabet: null")
        dpg.set_value("description", f"Description: null")
        dpg.set_value("input tape", "")
        self.update_tape_table(Tape([], 0))
        self.update_graph()

    def unlock_input(self):
        dpg.configure_item("input tape", enabled=True)
        dpg.configure_item("step self.tm", enabled=True)
        dpg.configure_item("run self.tm", enabled=True)
        dpg.configure_item("reset self.tm", enabled=True)
        dpg.set_value("alphabet", f"Alphabet: {self.tm.input_alphabet}")
        dpg.set_value("description", f"Description: {self.tm.description}")
        self.update_tape_table(self.tm.tape)
        self.update_graph()

    def load_tm(self):
        if not self.paused:
            return
        try:
            self.tm = load_tm(dpg.get_value("File Path"))
            self.tm.tape = Tape(list(dpg.get_value("input tape")), 0)
            self.unlock_input()
            self.update_status("initial")
        except:
            print("Error loading TM")
            self.tm = None
            self.update_status("null")
            self.lock_input()

    def run(self):
        dpg.create_context()
        dpg.create_viewport()
        dpg.setup_dearpygui()

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(width=self.size[0]*self.image_size, height=self.size[1]*self.image_size, tag="graph texture", default_value=self.buffer, format=dpg.mvFormat_Float_rgb)

        with dpg.window(label="Turing Machine", tag="Turing Machine"):
            with dpg.group(horizontal=True):
                with dpg.group(horizontal=False, width=300):
                    with dpg.child_window(label="Config", tag="Config"):
                        with dpg.child_window(label="Input File", tag="Input File", height=85):
                            dpg.add_text(f"Path to input file", tag="path label", color=(0, 200, 255))
                            dpg.add_input_text(label="File Path", tag="File Path", width=-1, default_value="assets/tm_two_words.json")
                            dpg.add_button(label="Load", callback=self.load_tm, tag="load self.tm")

                        with dpg.child_window(label="Input", tag="Input", height=60):
                            dpg.add_text(f"Input tape", tag="input label", color=(0, 200, 255))
                            dpg.add_input_text(label="Input Tape", tag="input tape", callback=self.update_input, width=-1, show=True, enabled=False)

                        with dpg.child_window(label="Graph Settings", height=130, tag="Graph Settings"):
                            dpg.add_text(f"Controls", tag="settings label", color=(0, 200, 255))
                            dpg.add_button(label="Run", callback=self.run_tm, tag="run self.tm", enabled=False)
                            dpg.add_button(label="Step", callback=self.step_tm, tag="step self.tm", enabled=False)
                            dpg.add_button(label="Reset", callback=self.reset_tm, tag="reset self.tm", enabled=False)
                            dpg.add_slider_float(label="Sleep Timer", tag="sleep timer", min_value=0, max_value=2, default_value=1)

                        with dpg.child_window(label="self.tm Info",  height=130, tag="self.tm Info"):
                            dpg.add_text(f"Turing machine information", tag="info label", color=(0, 200, 255))
                            dpg.add_text(f"Alphabet: null", tag="alphabet", wrap=260)
                            dpg.add_text(f"Status: null", tag="status", wrap=260)
                            dpg.add_text(f"Description: null", tag="description", wrap=260)

                        with dpg.table(header_row=True, borders_innerH=True, borders_outerH=True, borders_innerV=True, borders_outerV=True, tag="tape table"):
                            dpg.add_table_column(label="Tape", width_fixed=True)

                with dpg.child_window(label="Graph", tag="Graph", autosize_y=True, autosize_x=True):
                    with dpg.theme(tag="plot_theme"):
                        with dpg.theme_component(dpg.mvPlot):
                            dpg.add_theme_color(dpg.mvPlotCol_PlotBg, (255, 255, 255), category=dpg.mvThemeCat_Plots)

                    with dpg.plot(label="Graph Plot", tag="Graph Plot", no_menus=True, no_title=True, width=-1, height=-1):
                        dpg.add_plot_axis(dpg.mvXAxis, no_gridlines=True, no_tick_marks=True, no_tick_labels=True, tag="x axis")
                        with dpg.plot_axis(dpg.mvYAxis, no_gridlines=True, no_tick_marks=True, no_tick_labels=True, tag="y axis"):
                            dpg.add_image_series("graph texture", [0, 0], [self.size[0]*10, self.size[1]*10], tag="graph image")

                    dpg.bind_item_theme("Graph Plot", "plot_theme")

        dpg.show_viewport()
        dpg.set_primary_window("Turing Machine", True)
        self.lock_input()

        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

        dpg.destroy_context()
