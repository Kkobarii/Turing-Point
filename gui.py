import time
import dearpygui.dearpygui as dpg
import PIL.Image
import io
import numpy as np

from threading import Thread
from turing_machine import Tape, BLANK, tm_to_diagraph, load_tm


class GUI:
    def __init__(self):
        self.size = (1280, 720)
        self.tm = None
        self.buffer = np.zeros((self.size[1], self.size[0], 3), dtype=np.float32)
        self.paused = True
        self.kill_thread = True
        self.run_thread = None
        self.image_size = 100

    def create_image(self) -> np.ndarray:
        if self.tm is None:
            return np.ones((self.size[1], self.size[0], 3), dtype=np.float32)

        # some image magic
        g = tm_to_diagraph(self.tm)
        g.graph_attr['rankdir'] = 'LR'
        g.graph_attr['size'] = f"{self.size[1]/96},{self.size[0]/96}"
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
                    dpg.add_text(symbol, color=[100, 255, 0])
                else:
                    dpg.add_text(symbol)

    def update_input(self):
        tape = dpg.get_value("input tape")
        if len(str(tape)) != 0 and str(tape)[-1] not in self.tm.input_alphabet:
            while len(str(tape)) > 0 and str(tape)[-1] not in self.tm.input_alphabet:
                tape = tape[:-1]

            # dpg.configure_item("input tape", callback=lambda: None)
            # dpg.set_value("input tape", tape)
            # dpg.configure_item("input tape", callback=self.update_input)

            dpg.delete_item("input tape")
            dpg.add_input_text(label="Input Tape", tag="input tape", callback=self.update_input, default_value=tape, parent="Input", width=-1)
            # dpg.focus_item("input tape")

        self.tm.tape = Tape(list(tape), 0)
        self.update_tape_table(Tape(list(tape), 0))

    def update_graph(self):
        self.buffer[:] = 1.0
        img_array = self.create_image()
        self.buffer[:img_array.shape[0], :img_array.shape[1], :] = img_array

    def run_tm_thread(self):
        while not self.tm.is_final() and not self.paused:
            if self.kill_thread:
                return
            self.tm.step()
            self.update_graph()
            self.update_tape_table(self.tm.tape)
            time.sleep(dpg.get_value("sleep timer"))

    def run_tm(self):
        if not self.paused:
            self.paused = True
            self.kill_thread = True
            self.run_thread.join()
            dpg.configure_item("step self.tm", enabled=True)
            dpg.configure_item("run self.tm", label="Run")
            return

        dpg.configure_item("input tape", enabled=False)
        dpg.configure_item("step self.tm", enabled=False)
        dpg.configure_item("run self.tm", label="Pause")
        self.update_tape_table(self.tm.tape)

        self.kill_thread = False
        self.paused = False
        self.run_thread = Thread(target=self.run_tm_thread)
        self.run_thread.start()

    def step_tm(self):
        if self.tm.is_final():
            return
        dpg.configure_item("input tape", enabled=False)
        self.tm.step()
        self.update_graph()
        self.update_tape_table(self.tm.tape)

    def reset_tm(self):
        dpg.configure_item("input tape", enabled=True)
        dpg.configure_item("step self.tm", enabled=True)
        dpg.configure_item("run self.tm", label="Run")
        self.paused = True
        self.kill_thread = True
        self.tm.reset()
        self.tm.tape = Tape(list(dpg.get_value("input tape")), 0)
        self.update_tape_table(self.tm.tape)
        self.update_graph()

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
        try:
            self.tm = load_tm(dpg.get_value("File Path"))
            self.unlock_input()
        except:
            print("Error loading TM")
            self.tm = None
            self.lock_input()

    def run(self):
        dpg.create_context()
        dpg.create_viewport()
        dpg.setup_dearpygui()

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(width=self.size[0], height=self.size[1], tag="graph texture", default_value=self.buffer, format=dpg.mvFormat_Float_rgb)

        with dpg.window(label="Turing Machine", tag="Turing Machine"):
            with dpg.group(horizontal=True):
                with dpg.group(horizontal=False, width=300):
                    with dpg.child_window(label="Input File", tag="Input File", height=80):
                        dpg.add_input_text(label="File Path", tag="File Path", width=-1, default_value="assets/tm_two_words.json")
                        dpg.add_button(label="Load", callback=self.load_tm, tag="load self.tm")

                    with dpg.child_window(label="Config", tag="Config"):
                        with dpg.child_window(label="Input", tag="Input", height=40):
                            dpg.add_input_text(label="Input Tape", tag="input tape", callback=self.update_input, width=-1, show=True, enabled=False)

                        with dpg.child_window(label="Graph Settings", height=120, tag="Graph Settings"):
                            dpg.add_button(label="Run", callback=self.run_tm, tag="run self.tm", enabled=False)
                            dpg.add_button(label="Step", callback=self.step_tm, tag="step self.tm", enabled=False)
                            dpg.add_button(label="Reset", callback=self.reset_tm, tag="reset self.tm", enabled=False)
                            dpg.add_slider_float(label="Sleep Timer", tag="sleep timer", min_value=0, max_value=2, default_value=1)

                        with dpg.child_window(label="self.tm Info",  height=100, tag="self.tm Info"):
                            dpg.add_text(f"Alphabet: null", tag="alphabet", wrap=260)
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
            self.update_graph()
            dpg.render_dearpygui_frame()

        dpg.destroy_context()
