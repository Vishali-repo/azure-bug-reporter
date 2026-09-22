import os
import ctypes
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

import keyboard
import pystray
from PIL import Image, ImageDraw, ImageTk

from azure_devops import AzureDevOpsClient
from screenshot import capture_screenshot


# =========================================================
# WINDOWS DPI AWARENESS
# =========================================================

if os.name == "nt":

    try:

        ctypes.windll.shcore.SetProcessDpiAwareness(
            2
        )

    except Exception:

        try:

            ctypes.windll.user32.SetProcessDPIAware()

        except Exception:
            pass


# =========================================================
# COLORS
# =========================================================

BG_COLOR = "#F4F7FB"

CARD_COLOR = "#FFFFFF"

PRIMARY = "#2563EB"
PRIMARY_HOVER = "#1D4ED8"

SUCCESS = "#16A34A"
SUCCESS_LIGHT = "#ECFDF5"

ERROR = "#DC2626"
ERROR_LIGHT = "#FEF2F2"

TEXT = "#172033"
SECONDARY_TEXT = "#64748B"

BORDER = "#D9E2EF"

HEADER_START = "#1E40AF"
HEADER_END = "#2563EB"


# =========================================================
# APPLICATION
# =========================================================

class BugReporterApp:

    def __init__(
        self,
        root
    ):

        self.root = root

        # -------------------------------------------------
        # Window
        # -------------------------------------------------

        self.root.title(
            "Azure Bug Reporter"
        )

        window_width = 600
        window_height = 720

        self.root.geometry(
            f"{window_width}x{window_height}"
        )

        self.root.minsize(
            600,
            720
        )

        screen_width = (
            self.root.winfo_screenwidth()
        )

        x = (
            screen_width - window_width
        ) // 2

        y = 18

        self.root.geometry(
            f"{window_width}x{window_height}"
            f"+{x}+{y}"
        )

        self.root.configure(
            bg=BG_COLOR
        )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.hide_window
        )

        # -------------------------------------------------
        # Variables
        # -------------------------------------------------

        self.projects = []

        self.project_var = tk.StringVar()

        self.parent_task_var = tk.StringVar(
            value=""
        )

        # Actual selected Azure DevOps Task ID
        self.selected_parent_task_id = None

        # Search result list
        self.parent_tasks = []

        # Debounce timer
        self.parent_search_after_id = None

        # Prevent selection from triggering search
        self.parent_task_selecting = False

        self.category_var = tk.StringVar(
            value="Build"
        )

        self.title_var = tk.StringVar()

        self.status_var = tk.StringVar(
            value="Ready"
        )

        self.screenshot_path = None

        self.tray_icon = None

        self.preview_image = None

        self.parent_dropdown = None

        self.parent_listbox = None

        # -------------------------------------------------
        # Styles
        # -------------------------------------------------

        self.setup_styles()

        # -------------------------------------------------
        # UI
        # -------------------------------------------------

        self.build_ui()

        # -------------------------------------------------
        # Azure DevOps
        # -------------------------------------------------

        try:

            self.client = AzureDevOpsClient()

            self.load_projects()

        except Exception as e:

            self.client = None

            self.set_status(
                f"Azure DevOps connection error: {e}",
                error=True
            )

        # -------------------------------------------------
        # Global Shortcut
        # -------------------------------------------------

        try:

            keyboard.add_hotkey(
                "ctrl+shift+s",
                self.global_capture,
                suppress=True
            )

        except Exception as e:

            print(
                f"Global hotkey error: {e}"
            )

        # -------------------------------------------------
        # Tray
        # -------------------------------------------------

        self.root.after(
            1000,
            self.create_tray
        )

        # -------------------------------------------------
        # Start Hidden
        # -------------------------------------------------

        self.root.withdraw()

    # =====================================================
    # STYLES
    # =====================================================

    def setup_styles(
        self
    ):

        style = ttk.Style()

        try:

            style.theme_use(
                "clam"
            )

        except Exception:
            pass

        style.configure(
            "Custom.TCombobox",
            fieldbackground="white",
            background="white",
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=7
        )

        style.configure(
            "Custom.TEntry",
            fieldbackground="white",
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=7
        )

    # =====================================================
    # BUILD UI
    # =====================================================

    def build_ui(
        self
    ):

        # -------------------------------------------------
        # HEADER
        # -------------------------------------------------

        header = tk.Frame(
            self.root,
            bg=HEADER_START,
            height=105
        )

        header.pack(
            fill="x"
        )

        header.pack_propagate(
            False
        )

        icon_frame = tk.Frame(
            header,
            bg="#FFFFFF",
            width=55,
            height=55
        )

        icon_frame.pack(
            side="left",
            padx=(20, 12),
            pady=20
        )

        icon_frame.pack_propagate(
            False
        )

        tk.Label(
            icon_frame,
            text="🐞",
            font=("Segoe UI Emoji", 25),
            bg="#FFFFFF"
        ).pack(
            expand=True
        )

        title_frame = tk.Frame(
            header,
            bg=HEADER_START
        )

        title_frame.pack(
            side="left",
            fill="y"
        )

        tk.Label(
            title_frame,
            text="Azure Bug Reporter",
            font=("Segoe UI", 20, "bold"),
            fg="white",
            bg=HEADER_START
        ).pack(
            anchor="w",
            pady=(17, 0)
        )

        tk.Label(
            title_frame,
            text=(
                "Capture a screenshot and create "
                "an Azure DevOps bug quickly."
            ),
            font=("Segoe UI", 9),
            fg="#DBEAFE",
            bg=HEADER_START
        ).pack(
            anchor="w",
            pady=(2, 0)
        )

        # -------------------------------------------------
        # MAIN CONTAINER
        # -------------------------------------------------

        container = tk.Frame(
            self.root,
            bg=BG_COLOR
        )

        container.pack(
            fill="both",
            expand=True
        )

        # -------------------------------------------------
        # PROJECT / PARENT TASK CARD
        # -------------------------------------------------

        top_card = self.create_card(
            container
        )

        top_card.pack(
            fill="x",
            padx=16,
            pady=(14, 7)
        )

        top_card.grid_columnconfigure(
            0,
            weight=1
        )

        top_card.grid_columnconfigure(
            1,
            weight=1
        )

        # -------------------------------------------------
        # PROJECT
        # -------------------------------------------------

        self.create_field_label(
            top_card,
            "Azure DevOps Project",
            0,
            0
        )

        self.project_combo = ttk.Combobox(
            top_card,
            textvariable=self.project_var,
            state="readonly",
            style="Custom.TCombobox"
        )

        self.project_combo.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(14, 7),
            pady=(3, 12)
        )

        self.project_combo.bind(
            "<<ComboboxSelected>>",
            self.project_changed
        )

        # -------------------------------------------------
        # PARENT TASK
        # -------------------------------------------------

        self.create_field_label(
            top_card,
            "Parent Task",
            0,
            1
        )

        self.parent_entry = ttk.Entry(
            top_card,
            textvariable=self.parent_task_var,
            style="Custom.TEntry"
        )

        self.parent_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(7, 14),
            pady=(3, 12)
        )

        self.parent_entry.bind(
            "<KeyRelease>",
            self.parent_task_search_changed
        )

        self.parent_entry.bind(
            "<Down>",
            self.parent_task_move_down
        )

        self.parent_entry.bind(
            "<Up>",
            self.parent_task_move_up
        )

        self.parent_entry.bind(
            "<Return>",
            self.parent_task_select_enter
        )

        self.parent_entry.bind(
            "<Escape>",
            self.hide_parent_dropdown
        )

        # -------------------------------------------------
        # BUG CATEGORY / TITLE
        # -------------------------------------------------

        second_card = self.create_card(
            container
        )

        second_card.pack(
            fill="x",
            padx=16,
            pady=7
        )

        second_card.grid_columnconfigure(
            0,
            weight=1
        )

        second_card.grid_columnconfigure(
            1,
            weight=1
        )

        # Category

        self.create_field_label(
            second_card,
            "Bug Category",
            0,
            0
        )

        categories = [
            "Build",
            "Business Logic",
            "CURD I/O",
            "Database",
            "Deploy",
            "Performance",
            "Security",
            "Typo",
            "UI",
            "UX",
            "Validation"
        ]

        self.category_combo = ttk.Combobox(
            second_card,
            textvariable=self.category_var,
            values=categories,
            state="readonly",
            style="Custom.TCombobox"
        )

        self.category_combo.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(14, 7),
            pady=(3, 12)
        )

        # Title

        self.create_field_label(
            second_card,
            "Bug Title",
            0,
            1
        )

        self.title_entry = ttk.Entry(
            second_card,
            textvariable=self.title_var,
            style="Custom.TEntry"
        )

        self.title_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(7, 14),
            pady=(3, 12)
        )

        # -------------------------------------------------
        # SCREENSHOT CARD
        # -------------------------------------------------

        screenshot_card = self.create_card(
            container
        )

        screenshot_card.pack(
            fill="x",
            padx=16,
            pady=7
        )

        screenshot_header = tk.Frame(
            screenshot_card,
            bg=CARD_COLOR
        )

        screenshot_header.pack(
            fill="x",
            padx=14,
            pady=(10, 5)
        )

        tk.Label(
            screenshot_header,
            text="📷  Screenshot",
            font=("Segoe UI", 11, "bold"),
            fg=TEXT,
            bg=CARD_COLOR
        ).pack(
            side="left"
        )

        self.screenshot_status_label = tk.Label(
            screenshot_header,
            text="No screenshot captured",
            font=("Segoe UI", 8),
            fg=SECONDARY_TEXT,
            bg=CARD_COLOR
        )

        self.screenshot_status_label.pack(
            side="right"
        )

        # Preview

        preview_container = tk.Frame(
            screenshot_card,
            bg="#F8FAFC",
            highlightbackground=BORDER,
            highlightthickness=1
        )

        preview_container.pack(
            fill="x",
            padx=14,
            pady=(2, 10)
        )

        self.preview_label = tk.Label(
            preview_container,
            text=(
                "📷\n\n"
                "Click \"Capture Area\" "
                "to take a screenshot"
            ),
            font=("Segoe UI", 9),
            fg=SECONDARY_TEXT,
            bg="#F8FAFC",
            justify="center"
        )

        self.preview_label.pack(
            fill="x",
            ipady=16
        )

        # Screenshot Buttons

        button_row = tk.Frame(
            screenshot_card,
            bg=CARD_COLOR
        )

        button_row.pack(
            fill="x",
            padx=14,
            pady=(0, 12)
        )

        self.capture_button = tk.Button(
            button_row,
            text="📷  Capture Area",
            command=self.capture_screenshot,
            bg=PRIMARY,
            fg="white",
            activebackground=PRIMARY_HOVER,
            activeforeground="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=14,
            pady=7
        )

        self.capture_button.pack(
            side="left"
        )

        self.recapture_button = tk.Button(
            button_row,
            text="⟳  Re-capture",
            command=self.capture_screenshot,
            bg="white",
            fg=PRIMARY,
            activebackground="#EFF6FF",
            activeforeground=PRIMARY,
            font=("Segoe UI", 9),
            relief="flat",
            highlightbackground=BORDER,
            highlightthickness=1,
            cursor="hand2",
            padx=14,
            pady=7
        )

        self.recapture_button.pack(
            side="left",
            padx=8
        )

        # -------------------------------------------------
        # CREATE BUG BUTTON
        # -------------------------------------------------

        self.create_button = tk.Button(
            container,
            text="🐞  Create Azure DevOps Bug",
            command=self.create_bug,
            bg=PRIMARY,
            fg="white",
            activebackground=PRIMARY_HOVER,
            activeforeground="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            cursor="hand2",
            pady=9
        )

        self.create_button.pack(
            fill="x",
            padx=16,
            pady=(8, 7)
        )

        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        status_card = tk.Frame(
            container,
            bg="#FFFFFF",
            highlightbackground=BORDER,
            highlightthickness=1
        )

        status_card.pack(
            fill="x",
            padx=16,
            pady=7
        )

        status_inner = tk.Frame(
            status_card,
            bg="#FFFFFF"
        )

        status_inner.pack(
            fill="x",
            padx=12,
            pady=9
        )

        tk.Label(
            status_inner,
            text="●",
            font=("Segoe UI", 12),
            fg=SUCCESS,
            bg="#FFFFFF"
        ).pack(
            side="left"
        )

        status_text_frame = tk.Frame(
            status_inner,
            bg="#FFFFFF"
        )

        status_text_frame.pack(
            side="left",
            padx=8
        )

        tk.Label(
            status_text_frame,
            text="Status",
            font=("Segoe UI", 8, "bold"),
            fg=SECONDARY_TEXT,
            bg="#FFFFFF"
        ).pack(
            anchor="w"
        )

        self.status_label = tk.Label(
            status_text_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 9, "bold"),
            fg=TEXT,
            bg="#FFFFFF",
            wraplength=500,
            justify="left"
        )

        self.status_label.pack(
            anchor="w"
        )

        # -------------------------------------------------
        # SECURITY TIP
        # -------------------------------------------------

        tip = tk.Frame(
            container,
            bg="#EFF6FF",
            highlightbackground="#BFDBFE",
            highlightthickness=1
        )

        tip.pack(
            fill="x",
            padx=16,
            pady=7
        )

        tk.Label(
            tip,
            text="ⓘ",
            font=("Segoe UI", 13),
            fg=PRIMARY,
            bg="#EFF6FF"
        ).pack(
            side="left",
            padx=(10, 5)
        )

        tk.Label(
            tip,
            text=(
                "Keep .env private — "
                "it contains the Azure DevOps PAT."
            ),
            font=("Segoe UI", 8),
            fg="#1E40AF",
            bg="#EFF6FF"
        ).pack(
            side="left",
            pady=8
        )

        # -------------------------------------------------
        # FOOTER
        # -------------------------------------------------

        footer = tk.Frame(
            container,
            bg=BG_COLOR
        )

        footer.pack(
            fill="x",
            padx=16,
            pady=(6, 10)
        )

        tk.Label(
            footer,
            text=(
                "📷 Screenshot   →   ✏ Annotation   →   "
                "🐞 Azure DevOps Bug   →   📎 Attachment   →   "
                "🔗 Parent Task"
            ),
            font=("Segoe UI", 7),
            fg=SECONDARY_TEXT,
            bg=BG_COLOR
        ).pack(
            anchor="center"
        )

    # =====================================================
    # CARD
    # =====================================================

    def create_card(
        self,
        parent
    ):

        return tk.Frame(
            parent,
            bg=CARD_COLOR,
            highlightbackground=BORDER,
            highlightthickness=1
        )

    # =====================================================
    # FIELD LABEL
    # =====================================================

    def create_field_label(
        self,
        parent,
        text,
        row,
        column
    ):

        tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 9, "bold"),
            fg=TEXT,
            bg=CARD_COLOR
        ).grid(
            row=row,
            column=column,
            sticky="w",
            padx=14,
            pady=(10, 2)
        )

    # =====================================================
    # LOAD PROJECTS
    # =====================================================

    def load_projects(
        self
    ):

        def worker():

            try:

                projects = (
                    self.client.get_projects()
                )

                self.root.after(
                    0,
                    lambda:
                    self.populate_projects(
                        projects
                    )
                )

            except Exception as e:

                self.root.after(
                    0,
                    lambda:
                    self.set_status(
                        f"Unable to load projects: {e}",
                        error=True
                    )
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    # =====================================================
    # POPULATE PROJECTS
    # =====================================================

    def populate_projects(
        self,
        projects
    ):

        self.projects = projects

        names = [
            project["name"]
            for project in projects
        ]

        self.project_combo["values"] = (
            names
        )

        if names:

            self.project_var.set(
                names[0]
            )

            self.clear_parent_task()

            self.set_status(
                "Ready"
            )

    # =====================================================
    # PROJECT CHANGED
    # =====================================================

    def project_changed(
        self,
        event=None
    ):

        self.clear_parent_task()

        project = (
            self.project_var.get().strip()
        )

        if project:

            self.set_status(
                "Project selected. "
                "Search for a Parent Task."
            )

    # =====================================================
    # CLEAR PARENT TASK
    # =====================================================

    def clear_parent_task(
        self
    ):

        self.selected_parent_task_id = None

        self.parent_tasks = []

        self.parent_task_var.set(
            ""
        )

        if self.parent_search_after_id:

            try:

                self.root.after_cancel(
                    self.parent_search_after_id
                )

            except Exception:
                pass

            self.parent_search_after_id = None

        self.hide_parent_dropdown()

    # =====================================================
    # PARENT TASK SEARCH - KEY RELEASE
    # =====================================================

    def parent_task_search_changed(
        self,
        event=None
    ):

        # -------------------------------------------------
        # Ignore navigation keys
        # -------------------------------------------------

        if event and event.keysym in (
            "Up",
            "Down",
            "Return",
            "Escape",
            "Left",
            "Right",
            "Home",
            "End"
        ):

            return

        # -------------------------------------------------
        # Ignore selection-generated changes
        # -------------------------------------------------

        if self.parent_task_selecting:

            return

        search_text = (
            self.parent_task_var.get().strip()
        )

        # Manual typing means old selection
        # is no longer valid.

        self.selected_parent_task_id = None

        project = (
            self.project_var.get().strip()
        )

        if not project:

            self.hide_parent_dropdown()

            return

        if not search_text:

            self.hide_parent_dropdown()

            return

        # -------------------------------------------------
        # Cancel Previous Search Timer
        # -------------------------------------------------

        if self.parent_search_after_id:

            try:

                self.root.after_cancel(
                    self.parent_search_after_id
                )

            except Exception:
                pass

            self.parent_search_after_id = None

        # -------------------------------------------------
        # Wait 500ms Before Calling Azure DevOps
        # -------------------------------------------------

        self.parent_search_after_id = (
            self.root.after(
                500,
                lambda:
                self.start_parent_task_search(
                    project,
                    search_text
                )
            )
        )

    # =====================================================
    # START PARENT TASK SEARCH
    # =====================================================

    def start_parent_task_search(
        self,
        project,
        search_text
    ):

        self.parent_search_after_id = None

        # -------------------------------------------------
        # Check Text Did Not Change
        # -------------------------------------------------

        if (
            self.parent_task_var.get().strip()
            != search_text
        ):

            return

        # -------------------------------------------------
        # Check Project Did Not Change
        # -------------------------------------------------

        if (
            self.project_var.get().strip()
            != project
        ):

            return

        # -------------------------------------------------
        # Show Searching
        # -------------------------------------------------

        self.show_parent_dropdown(
            [
                {
                    "id": None,
                    "title": "Searching...",
                    "state": ""
                }
            ]
        )

        self.set_status(
            "Searching Parent Tasks..."
        )

        # -------------------------------------------------
        # Background Search
        # -------------------------------------------------

        def worker():

            try:

                results = (
                    self.client.search_parent_tasks(
                        project,
                        search_text
                    )
                )

                self.root.after(
                    0,
                    lambda:
                    self.show_parent_search_results(
                        project,
                        search_text,
                        results
                    )
                )

            except Exception as e:

                self.root.after(
                    0,
                    lambda:
                    self.parent_task_search_error(
                        str(e)
                    )
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    # =====================================================
    # SEARCH RESULTS
    # =====================================================

    def show_parent_search_results(
        self,
        project,
        search_text,
        results
    ):

        # -------------------------------------------------
        # Ignore Old Search Results
        # -------------------------------------------------

        if (
            self.project_var.get().strip()
            != project
        ):

            return

        if (
            self.parent_task_var.get().strip()
            != search_text
        ):

            return

        self.parent_tasks = results

        # -------------------------------------------------
        # No Results
        # -------------------------------------------------

        if not results:

            self.show_parent_dropdown(
                [
                    {
                        "id": None,
                        "title": (
                            "No matching Tasks found"
                        ),
                        "state": ""
                    }
                ]
            )

            self.set_status(
                "No matching Parent Tasks found."
            )

            return

        # -------------------------------------------------
        # Display Results
        # -------------------------------------------------

        self.show_parent_dropdown(
            results
        )

        self.set_status(
            f"{len(results)} Parent Task(s) found."
        )

    # =====================================================
    # SEARCH ERROR
    # =====================================================

    def parent_task_search_error(
        self,
        error
    ):

        self.parent_tasks = []

        self.show_parent_dropdown(
            [
                {
                    "id": None,
                    "title": (
                        "Unable to search Azure DevOps"
                    ),
                    "state": ""
                }
            ]
        )

        self.set_status(
            "Parent Task search failed.",
            error=True
        )

        print(
            f"Parent Task search error: {error}"
        )

    # =====================================================
    # SHOW PARENT DROPDOWN
    # =====================================================

    def show_parent_dropdown(
        self,
        results
    ):

        self.hide_parent_dropdown()

        if not self.parent_entry.winfo_exists():

            return

        # -------------------------------------------------
        # Position
        # -------------------------------------------------

        x = (
            self.parent_entry.winfo_rootx()
        )

        y = (
            self.parent_entry.winfo_rooty()
            + self.parent_entry.winfo_height()
        )

        width = max(
            250,
            self.parent_entry.winfo_width()
        )

        # -------------------------------------------------
        # Height
        # -------------------------------------------------

        item_height = 38

        height = min(
            240,
            max(
                42,
                len(results) * item_height
            )
        )

        # -------------------------------------------------
        # Dropdown Window
        # -------------------------------------------------

        dropdown = tk.Toplevel(
            self.root
        )

        self.parent_dropdown = dropdown

        dropdown.overrideredirect(
            True
        )

        dropdown.attributes(
            "-topmost",
            True
        )

        dropdown.geometry(
            f"{width}x{height}"
            f"+{x}+{y}"
        )

        dropdown.configure(
            bg="white"
        )

        # -------------------------------------------------
        # Listbox
        # -------------------------------------------------

        listbox = tk.Listbox(
            dropdown,
            bg="white",
            fg=TEXT,
            selectbackground="#DBEAFE",
            selectforeground=TEXT,
            highlightthickness=1,
            highlightbackground=BORDER,
            relief="flat",
            font=("Segoe UI", 9),
            activestyle="none"
        )

        listbox.pack(
            fill="both",
            expand=True
        )

        self.parent_listbox = listbox

        # -------------------------------------------------
        # Populate
        # -------------------------------------------------

        for result in results:

            task_id = result.get(
                "id"
            )

            title = result.get(
                "title",
                ""
            )

            state = result.get(
                "state",
                ""
            )

            if task_id is None:

                display_text = title

            else:

                display_text = (
                    f"{task_id} - {title}"
                )

                if state:

                    display_text += (
                        f"  [{state}]"
                    )

            listbox.insert(
                tk.END,
                display_text
            )

        # -------------------------------------------------
        # First Item
        # -------------------------------------------------

        if results:

            listbox.selection_set(
                0
            )

            listbox.activate(
                0
            )

        # -------------------------------------------------
        # Mouse
        # -------------------------------------------------

        listbox.bind(
            "<ButtonRelease-1>",
            self.parent_task_list_click
        )

        # -------------------------------------------------
        # Keyboard
        # -------------------------------------------------

        listbox.bind(
            "<Return>",
            self.parent_task_select_enter
        )

        listbox.bind(
            "<Escape>",
            lambda event:
            self.hide_parent_dropdown()
        )

    # =====================================================
    # HIDE DROPDOWN
    # =====================================================

    def hide_parent_dropdown(
        self,
        event=None
    ):

        if self.parent_dropdown:

            try:

                self.parent_dropdown.destroy()

            except Exception:
                pass

        self.parent_dropdown = None

        self.parent_listbox = None

    # =====================================================
    # MOVE DOWN
    # =====================================================

    def parent_task_move_down(
        self,
        event=None
    ):

        if not self.parent_listbox:

            return "break"

        current = (
            self.parent_listbox.curselection()
        )

        if not current:

            index = 0

        else:

            index = (
                current[0] + 1
            )

        last_index = (
            self.parent_listbox.size()
            - 1
        )

        if index > last_index:

            index = last_index

        if last_index >= 0:

            self.parent_listbox.selection_clear(
                0,
                tk.END
            )

            self.parent_listbox.selection_set(
                index
            )

            self.parent_listbox.activate(
                index
            )

        return "break"

    # =====================================================
    # MOVE UP
    # =====================================================

    def parent_task_move_up(
        self,
        event=None
    ):

        if not self.parent_listbox:

            return "break"

        current = (
            self.parent_listbox.curselection()
        )

        if not current:

            index = 0

        else:

            index = (
                current[0] - 1
            )

        if index < 0:

            index = 0

        last_index = (
            self.parent_listbox.size()
            - 1
        )

        if last_index >= 0:

            self.parent_listbox.selection_clear(
                0,
                tk.END
            )

            self.parent_listbox.selection_set(
                index
            )

            self.parent_listbox.activate(
                index
            )

        return "break"

    # =====================================================
    # ENTER
    # =====================================================

    def parent_task_select_enter(
        self,
        event=None
    ):

        if not self.parent_listbox:

            return "break"

        selection = (
            self.parent_listbox.curselection()
        )

        if not selection:

            return "break"

        index = selection[0]

        self.select_parent_task(
            index
        )

        return "break"

    # =====================================================
    # CLICK
    # =====================================================

    def parent_task_list_click(
        self,
        event=None
    ):

        if not self.parent_listbox:

            return

        selection = (
            self.parent_listbox.curselection()
        )

        if not selection:

            return

        index = selection[0]

        self.select_parent_task(
            index
        )

    # =====================================================
    # SELECT TASK
    # =====================================================

    def select_parent_task(
        self,
        index
    ):

        if index < 0:

            return

        if index >= len(
            self.parent_tasks
        ):

            return

        task = (
            self.parent_tasks[index]
        )

        task_id = task.get(
            "id"
        )

        title = task.get(
            "title",
            ""
        )

        # -------------------------------------------------
        # Ignore Informational Rows
        # -------------------------------------------------

        if task_id is None:

            return

        self.parent_task_selecting = True

        try:

            # Store only ID internally
            self.selected_parent_task_id = (
                str(task_id)
            )

            # Display ID + Title
            self.parent_task_var.set(
                f"{task_id} - {title}"
            )

        finally:

            self.parent_task_selecting = False

        self.hide_parent_dropdown()

        self.set_status(
            f"Parent Task {task_id} selected."
        )

    # =====================================================
    # SCREENSHOT
    # =====================================================

    def capture_screenshot(
        self
    ):

        try:

            self.hide_parent_dropdown()

            self.root.withdraw()

            self.root.update()

            screenshot = capture_screenshot(
                self.root
            )

            if screenshot:

                self.screenshot_path = (
                    screenshot
                )

                self.show_screenshot_preview(
                    screenshot
                )

                self.set_status(
                    "Screenshot captured successfully."
                )

            else:

                self.set_status(
                    "Screenshot capture cancelled."
                )

            self.root.deiconify()

            self.root.lift()

            self.root.focus_force()

        except Exception as e:

            self.root.deiconify()

            self.root.lift()

            messagebox.showerror(
                "Screenshot Error",
                str(e),
                parent=self.root
            )

    # =====================================================
    # SCREENSHOT PREVIEW
    # =====================================================

    def show_screenshot_preview(
        self,
        path
    ):

        try:

            image = Image.open(
                path
            )

            image.thumbnail(
                (500, 120)
            )

            self.preview_image = (
                ImageTk.PhotoImage(
                    image
                )
            )

            self.preview_label.configure(
                image=self.preview_image,
                text="",
                bg="#F8FAFC"
            )

            self.screenshot_status_label.configure(
                text="✓ Screenshot captured",
                fg=SUCCESS
            )

        except Exception as e:

            self.preview_label.configure(
                image="",
                text=f"Preview error:\n{e}"
            )

    # =====================================================
    # CREATE BUG
    # =====================================================

    def create_bug(
        self
    ):

        self.hide_parent_dropdown()

        project = (
            self.project_var.get().strip()
        )

        parent_id = (
            self.selected_parent_task_id
        )

        category = (
            self.category_var.get().strip()
        )

        bug_title = (
            self.title_var.get().strip()
        )

        # -------------------------------------------------
        # Project
        # -------------------------------------------------

        if not project:

            messagebox.showwarning(
                "Validation",
                "Please select an Azure DevOps project.",
                parent=self.root
            )

            return

        # -------------------------------------------------
        # Parent Task
        # -------------------------------------------------

        if not parent_id:

            messagebox.showwarning(
                "Validation",
                "Please search and select a Parent Task.",
                parent=self.root
            )

            return

        if not str(
            parent_id
        ).isdigit():

            messagebox.showwarning(
                "Validation",
                "Please select a valid Parent Task.",
                parent=self.root
            )

            return

        # -------------------------------------------------
        # Category
        # -------------------------------------------------

        if not category:

            messagebox.showwarning(
                "Validation",
                "Please select Bug Category.",
                parent=self.root
            )

            return

        # -------------------------------------------------
        # Title
        # -------------------------------------------------

        if not bug_title:

            messagebox.showwarning(
                "Validation",
                "Please enter Bug Title.",
                parent=self.root
            )

            return

        # -------------------------------------------------
        # Screenshot
        # -------------------------------------------------

        if not self.screenshot_path:

            messagebox.showwarning(
                "Validation",
                "Please capture a screenshot first.",
                parent=self.root
            )

            return

        # -------------------------------------------------
        # Disable Button
        # -------------------------------------------------

        self.create_button.configure(
            state="disabled",
            text="Creating Azure DevOps Bug..."
        )

        self.set_status(
            "Uploading screenshot and creating bug..."
        )

        # -------------------------------------------------
        # Background Worker
        # -------------------------------------------------

        def worker():

            try:

                attachment_url = (
                    self.client.upload_attachment(
                        project,
                        self.screenshot_path
                    )
                )

                result = (
                    self.client.create_bug(
                        project,
                        bug_title,
                        parent_id,
                        category,
                        attachment_url
                    )
                )

                bug_id = result.get(
                    "id"
                )

                bug_url = (
                    result.get(
                        "_links",
                        {}
                    )
                    .get(
                        "html",
                        {}
                    )
                    .get(
                        "href"
                    )
                )

                self.root.after(
                    0,
                    lambda:
                    self.bug_created(
                        bug_id,
                        bug_url
                    )
                )

            except Exception as e:

                self.root.after(
                    0,
                    lambda:
                    self.bug_creation_failed(
                        str(e)
                    )
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    # =====================================================
    # BUG CREATED
    # =====================================================

    def bug_created(
        self,
        bug_id,
        bug_url
    ):

        self.create_button.configure(
            state="normal",
            text="🐞  Create Azure DevOps Bug"
        )

        self.set_status(
            f"Bug {bug_id} created successfully.",
            success=True
        )

        # -------------------------------------------------
        # Delete Screenshot
        # -------------------------------------------------

        if self.screenshot_path:

            try:

                if os.path.exists(
                    self.screenshot_path
                ):

                    os.remove(
                        self.screenshot_path
                    )

            except Exception:
                pass

        self.screenshot_path = None

        # -------------------------------------------------
        # Reset Screenshot Preview
        # -------------------------------------------------

        self.preview_label.configure(
            image="",
            text=(
                "📷\n\n"
                "Click \"Capture Area\" "
                "to take a screenshot"
            ),
            bg="#F8FAFC"
        )

        self.screenshot_status_label.configure(
            text="No screenshot captured",
            fg=SECONDARY_TEXT
        )

        # -------------------------------------------------
        # Reset Title
        # -------------------------------------------------

        self.title_var.set(
            ""
        )

        # -------------------------------------------------
        # Keep Project and Parent Task
        # -------------------------------------------------
        #
        # This allows multiple Bugs to be created
        # under the same Parent Task.
        #
        # -------------------------------------------------

        if bug_url:

            open_result = messagebox.askyesno(
                "Bug Created",
                (
                    f"Bug {bug_id} was created successfully.\n\n"
                    "Open the bug in Azure DevOps?"
                ),
                parent=self.root
            )

            if open_result:

                webbrowser.open(
                    bug_url
                )

    # =====================================================
    # BUG CREATION FAILED
    # =====================================================

    def bug_creation_failed(
        self,
        error
    ):

        self.create_button.configure(
            state="normal",
            text="🐞  Create Azure DevOps Bug"
        )

        self.set_status(
            "Bug creation failed.",
            error=True
        )

        messagebox.showerror(
            "Bug Creation Failed",
            error,
            parent=self.root
        )

    # =====================================================
    # STATUS
    # =====================================================

    def set_status(
        self,
        message,
        success=False,
        error=False
    ):

        self.status_var.set(
            message
        )

        if success:

            self.status_label.configure(
                fg=SUCCESS
            )

        elif error:

            self.status_label.configure(
                fg=ERROR
            )

        else:

            self.status_label.configure(
                fg=TEXT
            )

    # =====================================================
    # SHOW WINDOW
    # =====================================================

    def show_window(
        self
    ):

        self.root.deiconify()

        self.root.lift()

        self.root.focus_force()

    # =====================================================
    # HIDE WINDOW
    # =====================================================

    def hide_window(
        self
    ):

        self.hide_parent_dropdown()

        self.root.withdraw()

    # =====================================================
    # GLOBAL SCREENSHOT
    # =====================================================

    def global_capture(
        self
    ):

        self.root.after(
            0,
            self.capture_screenshot
        )

    # =====================================================
    # TRAY
    # =====================================================

    def create_tray(
        self
    ):

        try:

            image = Image.new(
                "RGB",
                (64, 64),
                "#2563EB"
            )

            draw = ImageDraw.Draw(
                image
            )

            draw.rectangle(
                (16, 16, 48, 48),
                fill="white"
            )

            draw.rectangle(
                (22, 22, 42, 42),
                fill="#2563EB"
            )

            menu = pystray.Menu(

                pystray.MenuItem(
                    "Open Bug Reporter",
                    lambda icon, item:
                    self.root.after(
                        0,
                        self.show_window
                    )
                ),

                pystray.MenuItem(
                    "Capture Screenshot",
                    lambda icon, item:
                    self.root.after(
                        0,
                        self.capture_screenshot
                    )
                ),

                pystray.MenuItem(
                    "Exit",
                    lambda icon, item:
                    self.exit_application()
                )
            )

            self.tray_icon = pystray.Icon(
                "Azure Bug Reporter",
                image,
                "Azure Bug Reporter",
                menu
            )

            threading.Thread(
                target=self.tray_icon.run,
                daemon=True
            ).start()

        except Exception as e:

            print(
                f"Tray error: {e}"
            )

    # =====================================================
    # EXIT
    # =====================================================

    def exit_application(
        self
    ):

        try:

            keyboard.unhook_all_hotkeys()

        except Exception:
            pass

        try:

            if self.tray_icon:

                self.tray_icon.stop()

        except Exception:
            pass

        self.root.after(
            0,
            self.root.destroy
        )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = BugReporterApp(
        root
    )

    root.mainloop()