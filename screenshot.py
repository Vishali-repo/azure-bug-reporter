import os
import sys
import ctypes
import math
import tkinter as tk
from tkinter import simpledialog, messagebox
from datetime import datetime
from pathlib import Path

from PIL import (
    ImageGrab,
    ImageTk,
    ImageDraw,
    ImageFont
)


# =========================================================
# DPI
# =========================================================

if os.name == "nt":

    try:

        ctypes.windll.shcore.SetProcessDpiAwareness(2)

    except Exception:

        try:

            ctypes.windll.user32.SetProcessDPIAware()

        except Exception:

            pass


# =========================================================
# Application Folder
# =========================================================

# =========================================================
# Application Folder / Screenshot Storage
# =========================================================

if getattr(sys, "frozen", False):

    BASE_DIR = Path(
        sys.executable
    ).resolve().parent

else:

    BASE_DIR = Path(
        __file__
    ).resolve().parent


LOCAL_APP_DATA = Path(
    os.environ.get(
        "LOCALAPPDATA",
        Path.home()
    )
)


SCREENSHOT_FOLDER = (
    LOCAL_APP_DATA
    / "Azure Bug Reporter"
    / "screenshots"
)


SCREENSHOT_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

# =========================================================
# Colors
# =========================================================

COLORS = {

    "Red": "#EF4444",

    "Orange": "#F97316",

    "Yellow": "#EAB308",

    "Green": "#22C55E",

    "Blue": "#2563EB",

    "Purple": "#A855F7",

    "Black": "#111827",

    "White": "#FFFFFF"
}


# =========================================================
# Screenshot Tool
# =========================================================

class ScreenshotTool:

    def __init__(
        self,
        parent
    ):

        self.parent = parent

        self.overlay = None

        self.editor = None

        self.original_screen = None

        self.cropped_image = None

        self.overlay_canvas = None

        self.canvas = None

        self.tk_image = None

        self.selection_rectangle = None

        self.start_x = 0

        self.start_y = 0

        self.current_x = 0

        self.current_y = 0

        self.last_x = None

        self.last_y = None

        self.selection = None

        self.tool = "arrow"

        self.color = COLORS["Red"]

        self.line_width = 3

        self.drawing = False

        self.annotations = []

        self.active_shape = None

        self.editor_scale = 1.0

        self.result = None

        self.finished = tk.BooleanVar(
            self.parent,
            value=False
        )

        self.color_buttons = []


    # =====================================================
    # START
    # =====================================================

    def start(self):

        self.original_screen = ImageGrab.grab(
            all_screens=True
        )

        screen_width = (
            self.original_screen.width
        )

        screen_height = (
            self.original_screen.height
        )


        self.overlay = tk.Toplevel(
            self.parent
        )

        self.overlay.overrideredirect(
            True
        )

        self.overlay.geometry(
            f"{screen_width}x{screen_height}+0+0"
        )

        self.overlay.attributes(
            "-topmost",
            True
        )

        self.overlay.attributes(
            "-alpha",
            0.30
        )

        self.overlay.configure(
            bg="black"
        )


        self.overlay_canvas = tk.Canvas(
            self.overlay,
            width=screen_width,
            height=screen_height,
            highlightthickness=0,
            cursor="crosshair",
            bg="black"
        )

        self.overlay_canvas.pack(
            fill="both",
            expand=True
        )


        self.overlay_canvas.create_text(
            screen_width // 2,
            35,
            text=(
                "Drag to select an area   |   ESC to cancel"
            ),
            fill="white",
            font=(
                "Segoe UI",
                14,
                "bold"
            )
        )


        self.overlay_canvas.bind(
            "<ButtonPress-1>",
            self.selection_start
        )

        self.overlay_canvas.bind(
            "<B1-Motion>",
            self.selection_drag
        )

        self.overlay_canvas.bind(
            "<ButtonRelease-1>",
            self.selection_end
        )

        self.overlay.bind(
            "<Escape>",
            self.cancel
        )

        self.overlay.focus_force()

        self.parent.update()


    # =====================================================
    # AREA SELECTION
    # =====================================================

    def selection_start(
        self,
        event
    ):

        self.start_x = event.x

        self.start_y = event.y

        self.current_x = event.x

        self.current_y = event.y


        if self.selection_rectangle:

            self.overlay_canvas.delete(
                self.selection_rectangle
            )


        self.selection_rectangle = (
            self.overlay_canvas.create_rectangle(
                self.start_x,
                self.start_y,
                self.current_x,
                self.current_y,
                outline="#22C55E",
                width=3
            )
        )


    def selection_drag(
        self,
        event
    ):

        self.current_x = event.x

        self.current_y = event.y


        if self.selection_rectangle:

            self.overlay_canvas.coords(
                self.selection_rectangle,
                self.start_x,
                self.start_y,
                self.current_x,
                self.current_y
            )


    def selection_end(
        self,
        event
    ):

        self.current_x = event.x

        self.current_y = event.y


        x1 = min(
            self.start_x,
            self.current_x
        )

        y1 = min(
            self.start_y,
            self.current_y
        )

        x2 = max(
            self.start_x,
            self.current_x
        )

        y2 = max(
            self.start_y,
            self.current_y
        )


        width = x2 - x1

        height = y2 - y1


        if width < 10 or height < 10:

            return


        self.selection = (
            x1,
            y1,
            x2,
            y2
        )


        if self.overlay:

            self.overlay.destroy()

            self.overlay = None


        self.cropped_image = (
            self.original_screen.crop(
                self.selection
            )
        )


        self.open_editor()


    # =====================================================
    # EDITOR
    # =====================================================

    def open_editor(self):

        self.editor = tk.Toplevel(
            self.parent
        )

        self.editor.title(
            "Screenshot Editor"
        )

        self.editor.attributes(
            "-topmost",
            True
        )

        self.editor.protocol(
            "WM_DELETE_WINDOW",
            self.cancel_editor
        )


        screen_width = (
            self.editor.winfo_screenwidth()
        )

        screen_height = (
            self.editor.winfo_screenheight()
        )


        max_width = int(
            screen_width * 0.88
        )

        max_height = int(
            screen_height * 0.72
        )


        image_width = (
            self.cropped_image.width
        )

        image_height = (
            self.cropped_image.height
        )


        scale_x = (
            max_width /
            image_width
        )

        scale_y = (
            max_height /
            image_height
        )


        self.editor_scale = min(
            1.0,
            scale_x,
            scale_y
        )


        display_width = max(
            1,
            int(
                image_width *
                self.editor_scale
            )
        )

        display_height = max(
            1,
            int(
                image_height *
                self.editor_scale
            )
        )


        window_width = min(
            screen_width - 40,
            max(
                850,
                display_width + 40
            )
        )

        window_height = min(
            screen_height - 40,
            max(
                280,
                display_height + 165
            )
        )


        x = (
            screen_width -
            window_width
        ) // 2

        y = (
            screen_height -
            window_height
        ) // 2


        self.editor.geometry(
            f"{window_width}x{window_height}+{x}+{y}"
        )


        # =================================================
        # TOOLBAR
        # =================================================

        toolbar = tk.Frame(
            self.editor,
            bg="#111827",
            height=62
        )

        toolbar.pack(
            fill="x"
        )

        toolbar.pack_propagate(
            False
        )


        def add_tool(
            text,
            tool_name
        ):

            button = tk.Button(
                toolbar,
                text=text,
                command=lambda:
                self.set_tool(tool_name),
                bg="#1F2937",
                fg="white",
                activebackground="#374151",
                activeforeground="white",
                relief="flat",
                padx=10,
                pady=7,
                cursor="hand2"
            )

            button.pack(
                side="left",
                padx=2,
                pady=10
            )


        add_tool(
            "✏ Pen",
            "pen"
        )

        add_tool(
            "━ Line",
            "line"
        )

        add_tool(
            "➜ Arrow",
            "arrow"
        )

        add_tool(
            "▭ Rectangle",
            "rectangle"
        )

        add_tool(
            "T Text",
            "text"
        )


        tk.Button(
            toolbar,
            text="↶ Undo",
            command=self.undo,
            bg="#1F2937",
            fg="white",
            activebackground="#374151",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=7,
            cursor="hand2"
        ).pack(
            side="left",
            padx=(10, 2),
            pady=10
        )


        tk.Button(
            toolbar,
            text="Clear",
            command=self.clear_annotations,
            bg="#1F2937",
            fg="white",
            activebackground="#374151",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=7,
            cursor="hand2"
        ).pack(
            side="left",
            padx=2,
            pady=10
        )


        tk.Button(
            toolbar,
            text="✕ Cancel",
            command=self.cancel_editor,
            bg="#991B1B",
            fg="white",
            activebackground="#B91C1C",
            activeforeground="white",
            relief="flat",
            padx=11,
            pady=7,
            cursor="hand2"
        ).pack(
            side="right",
            padx=5,
            pady=10
        )


        tk.Button(
            toolbar,
            text="✓ Use Screenshot",
            command=self.use_screenshot,
            bg="#16A34A",
            fg="white",
            activebackground="#15803D",
            activeforeground="white",
            relief="flat",
            padx=11,
            pady=7,
            cursor="hand2"
        ).pack(
            side="right",
            padx=5,
            pady=10
        )


        # =================================================
        # OPTIONS BAR
        # =================================================

        options = tk.Frame(
            self.editor,
            bg="#F8FAFC",
            height=58
        )

        options.pack(
            fill="x"
        )

        options.pack_propagate(
            False
        )


        tk.Label(
            options,
            text="Color:",
            font=(
                "Segoe UI",
                9,
                "bold"
            ),
            bg="#F8FAFC",
            fg="#334155"
        ).pack(
            side="left",
            padx=(12, 5)
        )


        # Color buttons

        for name, color in COLORS.items():

            button = tk.Button(
                options,
                bg=color,
                activebackground=color,
                width=2,
                height=1,
                relief="solid",
                bd=1,
                cursor="hand2",
                command=lambda c=color:
                self.set_color(c)
            )

            button.pack(
                side="left",
                padx=2,
                pady=13
            )

            self.color_buttons.append(
                button
            )


        tk.Label(
            options,
            text="  Width:",
            font=(
                "Segoe UI",
                9,
                "bold"
            ),
            bg="#F8FAFC",
            fg="#334155"
        ).pack(
            side="left",
            padx=(10, 4)
        )


        self.width_var = tk.StringVar(
            value="3"
        )


        width_menu = tk.OptionMenu(
            options,
            self.width_var,
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "8",
            "10",
            command=self.set_width
        )

        width_menu.configure(
            bg="white",
            fg="#334155",
            activebackground="#E2E8F0",
            relief="solid",
            bd=1,
            highlightthickness=0,
            font=(
                "Segoe UI",
                9
            )
        )

        width_menu.pack(
            side="left"
        )


        self.color_indicator = tk.Label(
            options,
            text="●",
            font=(
                "Segoe UI",
                17
            ),
            fg=self.color,
            bg="#F8FAFC"
        )

        self.color_indicator.pack(
            side="right",
            padx=15
        )


        # =================================================
        # CANVAS
        # =================================================

        canvas_frame = tk.Frame(
            self.editor,
            bg="#111827"
        )

        canvas_frame.pack(
            fill="both",
            expand=True
        )


        self.canvas = tk.Canvas(
            canvas_frame,
            width=display_width,
            height=display_height,
            bg="#111827",
            highlightthickness=0,
            cursor="crosshair"
        )

        self.canvas.pack(
            expand=True
        )


        display_image = (
            self.cropped_image
        )


        if self.editor_scale != 1.0:

            display_image = (
                self.cropped_image.resize(
                    (
                        display_width,
                        display_height
                    )
                )
            )


        self.tk_image = ImageTk.PhotoImage(
            display_image
        )


        self.canvas.create_image(
            0,
            0,
            image=self.tk_image,
            anchor="nw",
            tags="background"
        )


        self.canvas.bind(
            "<ButtonPress-1>",
            self.draw_start
        )

        self.canvas.bind(
            "<B1-Motion>",
            self.draw_motion
        )

        self.canvas.bind(
            "<ButtonRelease-1>",
            self.draw_end
        )


        self.editor.bind(
            "<Escape>",
            lambda event:
            self.cancel_editor()
        )


        self.editor.focus_force()


    # =====================================================
    # COLOR
    # =====================================================

    def set_color(
        self,
        color
    ):

        self.color = color

        self.color_indicator.configure(
            fg=color
        )


        # Highlight selected color

        for button in self.color_buttons:

            button.configure(
                bd=1
            )


    # =====================================================
    # WIDTH
    # =====================================================

    def set_width(
        self,
        value
    ):

        try:

            self.line_width = int(
                value
            )

        except Exception:

            self.line_width = 3


    # =====================================================
    # TOOL
    # =====================================================

    def set_tool(
        self,
        tool
    ):

        self.tool = tool

        if self.canvas:

            self.canvas.configure(
                cursor=(
                    "xterm"
                    if tool == "text"
                    else "crosshair"
                )
            )


    # =====================================================
    # DRAW START
    # =====================================================

    def draw_start(
        self,
        event
    ):

        self.start_x = event.x

        self.start_y = event.y

        self.current_x = event.x

        self.current_y = event.y

        self.last_x = event.x

        self.last_y = event.y


        # -------------------------------------------------
        # TEXT
        # -------------------------------------------------

        if self.tool == "text":

            text = simpledialog.askstring(
                "Add Text",
                "Enter text:",
                parent=self.editor
            )


            if text:

                item = self.canvas.create_text(
                    event.x,
                    event.y,
                    text=text,
                    fill=self.color,
                    anchor="nw",
                    font=(
                        "Segoe UI",
                        16,
                        "bold"
                    )
                )


                self.annotations.append(
                    item
                )


            return


        self.drawing = True


        # -------------------------------------------------
        # PEN
        # -------------------------------------------------

        if self.tool == "pen":

            item = self.canvas.create_oval(
                event.x - 1,
                event.y - 1,
                event.x + 1,
                event.y + 1,
                fill=self.color,
                outline=self.color
            )

            self.annotations.append(
                item
            )


        # -------------------------------------------------
        # LINE
        # -------------------------------------------------

        elif self.tool == "line":

            self.active_shape = (
                self.canvas.create_line(
                    self.start_x,
                    self.start_y,
                    self.current_x,
                    self.current_y,
                    fill=self.color,
                    width=self.line_width
                )
            )


        # -------------------------------------------------
        # ARROW
        # -------------------------------------------------

        elif self.tool == "arrow":

            self.active_shape = (
                self.canvas.create_line(
                    self.start_x,
                    self.start_y,
                    self.current_x,
                    self.current_y,
                    fill=self.color,
                    width=self.line_width,
                    arrow=tk.LAST,
                    arrowshape=(
                        16,
                        20,
                        7
                    )
                )
            )


        # -------------------------------------------------
        # RECTANGLE
        # -------------------------------------------------

        elif self.tool == "rectangle":

            self.active_shape = (
                self.canvas.create_rectangle(
                    self.start_x,
                    self.start_y,
                    self.current_x,
                    self.current_y,
                    outline=self.color,
                    width=self.line_width
                )
            )


    # =====================================================
    # DRAW MOTION
    # =====================================================

    def draw_motion(
        self,
        event
    ):

        if not self.drawing:

            return


        self.current_x = event.x

        self.current_y = event.y


        # -------------------------------------------------
        # PEN
        # -------------------------------------------------

        if self.tool == "pen":

            item = self.canvas.create_line(
                self.last_x,
                self.last_y,
                self.current_x,
                self.current_y,
                fill=self.color,
                width=self.line_width,
                capstyle=tk.ROUND,
                smooth=True
            )


            self.annotations.append(
                item
            )


            self.last_x = (
                self.current_x
            )

            self.last_y = (
                self.current_y
            )


        # -------------------------------------------------
        # SHAPES
        # -------------------------------------------------

        elif self.active_shape:

            self.canvas.coords(
                self.active_shape,
                self.start_x,
                self.start_y,
                self.current_x,
                self.current_y
            )


        self.canvas.update_idletasks()


    # =====================================================
    # DRAW END
    # =====================================================

    def draw_end(
        self,
        event
    ):

        if not self.drawing:

            return


        self.current_x = event.x

        self.current_y = event.y


        if self.active_shape:

            self.canvas.coords(
                self.active_shape,
                self.start_x,
                self.start_y,
                self.current_x,
                self.current_y
            )


            self.annotations.append(
                self.active_shape
            )


            self.active_shape = None


        self.drawing = False


    # =====================================================
    # UNDO
    # =====================================================

    def undo(self):

        if not self.annotations:

            return


        item = self.annotations.pop()


        try:

            self.canvas.delete(
                item
            )

        except Exception:

            pass


    # =====================================================
    # CLEAR
    # =====================================================

    def clear_annotations(self):

        for item in self.annotations:

            try:

                self.canvas.delete(
                    item
                )

            except Exception:

                pass


        self.annotations.clear()


    # =====================================================
    # FINAL IMAGE
    # =====================================================

    def create_final_image(self):

        final_image = (
            self.cropped_image.copy()
        )

        draw = ImageDraw.Draw(
            final_image
        )


        scale = self.editor_scale


        if scale <= 0:

            scale = 1.0


        def original_x(x):

            return int(
                x / scale
            )


        def original_y(y):

            return int(
                y / scale
            )


        line_width = max(
            1,
            int(
                self.line_width / scale
            )
        )


        font_size = max(
            12,
            int(
                16 / scale
            )
        )


        font = None


        try:

            font_path = os.path.join(
                os.environ.get(
                    "WINDIR",
                    "C:\\Windows"
                ),
                "Fonts",
                "segoeui.ttf"
            )


            if os.path.exists(
                font_path
            ):

                font = ImageFont.truetype(
                    font_path,
                    font_size
                )


        except Exception:

            font = None


        # -------------------------------------------------
        # Draw annotations
        # -------------------------------------------------

        for item in self.annotations:

            try:

                item_type = (
                    self.canvas.type(item)
                )

                coords = (
                    self.canvas.coords(item)
                )


                if item_type == "line":

                    x1 = original_x(
                        coords[0]
                    )

                    y1 = original_y(
                        coords[1]
                    )

                    x2 = original_x(
                        coords[2]
                    )

                    y2 = original_y(
                        coords[3]
                    )


                    color = (
                        self.canvas.itemcget(
                            item,
                            "fill"
                        )
                    )


                    draw.line(
                        (
                            x1,
                            y1,
                            x2,
                            y2
                        ),
                        fill=color,
                        width=line_width
                    )


                    arrow_type = (
                        self.canvas.itemcget(
                            item,
                            "arrow"
                        )
                    )


                    if arrow_type == "last":

                        self.draw_arrow_head(
                            draw,
                            x1,
                            y1,
                            x2,
                            y2,
                            line_width,
                            color
                        )


                elif item_type == "rectangle":

                    x1 = original_x(
                        coords[0]
                    )

                    y1 = original_y(
                        coords[1]
                    )

                    x2 = original_x(
                        coords[2]
                    )

                    y2 = original_y(
                        coords[3]
                    )


                    color = (
                        self.canvas.itemcget(
                            item,
                            "outline"
                        )
                    )


                    draw.rectangle(
                        (
                            x1,
                            y1,
                            x2,
                            y2
                        ),
                        outline=color,
                        width=line_width
                    )


                elif item_type == "text":

                    x = original_x(
                        coords[0]
                    )

                    y = original_y(
                        coords[1]
                    )


                    text = (
                        self.canvas.itemcget(
                            item,
                            "text"
                        )
                    )


                    color = (
                        self.canvas.itemcget(
                            item,
                            "fill"
                        )
                    )


                    draw.text(
                        (
                            x,
                            y
                        ),
                        text,
                        fill=color,
                        font=font
                    )


            except Exception as e:

                print(
                    f"Annotation conversion error: {e}"
                )


        return final_image


    # =====================================================
    # ARROW HEAD
    # =====================================================

    def draw_arrow_head(
        self,
        draw,
        x1,
        y1,
        x2,
        y2,
        width,
        color
    ):

        angle = math.atan2(
            y2 - y1,
            x2 - x1
        )


        length = max(
            15,
            int(
                18 / max(
                    self.editor_scale,
                    0.1
                )
            )
        )


        angle1 = (
            angle + 2.6
        )

        angle2 = (
            angle - 2.6
        )


        p1 = (
            x2 +
            length *
            math.cos(angle1),

            y2 +
            length *
            math.sin(angle1)
        )


        p2 = (
            x2 +
            length *
            math.cos(angle2),

            y2 +
            length *
            math.sin(angle2)
        )


        draw.polygon(
            [
                (x2, y2),
                p1,
                p2
            ],
            fill=color
        )


    # =====================================================
    # USE SCREENSHOT
    # =====================================================

    def use_screenshot(self):

        try:

            final_image = (
                self.create_final_image()
            )


            timestamp = (
                datetime.now().strftime(
                    "%Y%m%d_%H%M%S_%f"
                )
            )


            filename = (
                f"screenshot_{timestamp}.png"
            )


            path = (
                SCREENSHOT_FOLDER /
                filename
            )


            final_image.save(
                path,
                format="PNG"
            )


            if not path.exists():

                raise RuntimeError(
                    "Screenshot file was not created."
                )


            self.result = str(
                path
            )


            if self.editor:

                self.editor.destroy()

                self.editor = None


            self.parent.deiconify()

            self.parent.lift()

            self.finished.set(
                True
            )


        except Exception as e:

            messagebox.showerror(
                "Screenshot Error",
                str(e),
                parent=self.editor
            )


    # =====================================================
    # CANCEL EDITOR
    # =====================================================

    def cancel_editor(self):

        self.result = None


        if self.editor:

            self.editor.destroy()

            self.editor = None


        self.parent.deiconify()

        self.finished.set(
            True
        )


    # =====================================================
    # CANCEL SELECTION
    # =====================================================

    def cancel(
        self,
        event=None
    ):

        self.result = None


        if self.overlay:

            self.overlay.destroy()

            self.overlay = None


        self.parent.deiconify()

        self.finished.set(
            True
        )


# =========================================================
# PUBLIC FUNCTION
# =========================================================

def capture_screenshot(parent):

    tool = ScreenshotTool(
        parent
    )

    tool.start()

    parent.wait_variable(
        tool.finished
    )

    return tool.result