"""Окно приложения «Генератор чисел Loto Max и Lotto 6/49».

Запуск без сборки:  python3 lotto_app.py
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import i18n
import lotto_core as core
import lotto_data as data
import lotto_update as upd
from i18n import t


def app_title() -> str:
    return t("app.title")


# Периоды: код -> дни назад / «последние N» / с даты. Названия — period.<код>.
PERIODS = {"all": None, "y10": 3653, "y5": 1826, "y1": 365, "n100": "n100", "n50": "n50",
           "max50": "max50", "max52": "max52"}
MAX_ONLY_PERIODS = ("max50", "max52")
# Ширина строки тиража на главной панели, в знаках: самая длинная —
# французская «Lotto Max ven 16/10/2026:  … compl. 52» (59 знаков).
BOARD_WIDTH = 62


# Какие розыгрыши учитывать. Дополнительные — это MaxMillions (по 1 000 000 $)
# и с 14.04.2026 MaxPlus (от 100 000 $) у Lotto Max: в файле BCLC это строки
# того же тиража с номером последовательности больше нуля. Названия — kind.<код>.
KINDS = ("main", "all", "extra")
SELF_TEST = os.environ.get("LOTTO_SELFTEST") == "1"
CHECK_EVERY_MS = 10 * 60 * 1000   # раз в 10 минут смотрим, не пора ли обновиться


# Оформление в стиле лотереи: зелёное сукно, золото, красный.
FELT = "#0f5a30"          # фон окна
FELT_DARK = "#0a3f22"
FELT_LIGHT = "#1f8a4c"
CREAM = "#fffdf6"         # таблицы и тексты
GOLD = "#f2c14e"
GOLD_LIGHT = "#ffe9a3"
GOLD_DARK = "#c8901a"
RED = "#d7262b"
RED_LIGHT = "#ff7a6b"
GREEN_BTN = "#1ea65a"
ON_FELT = "#f4fff7"       # основной текст на зелёном
ON_FELT_MUTED = "#c8ebd4"
INK = "#13261b"


def apply_theme(root: tk.Tk) -> ttk.Style:
    """Тема «лотерейный стол». clam — единственная встроенная тема, которая
    на Mac позволяет красить кнопки и вкладки (стандартная aqua — нет)."""
    st = ttk.Style(root)
    st.theme_use("clam")
    root.configure(background=FELT)
    base = ("Helvetica", 13)
    st.configure(".", background=FELT, foreground=ON_FELT, font=base,
                 fieldbackground="#ffffff", bordercolor=FELT_DARK,
                 lightcolor=FELT_LIGHT, darkcolor=FELT_DARK, troughcolor=FELT_DARK,
                 focuscolor=GOLD, selectbackground=GOLD, selectforeground=INK)
    st.configure("TFrame", background=FELT)
    st.configure("TLabel", background=FELT, foreground=ON_FELT)
    st.configure("Muted.TLabel", foreground=ON_FELT_MUTED)
    st.configure("Gold.TLabel", foreground=GOLD_LIGHT)
    st.configure("Title.TLabel", foreground=GOLD, font=("Helvetica", 24, "bold"))
    st.configure("TLabelframe", background=FELT, bordercolor=GOLD_DARK, relief="solid")
    st.configure("TLabelframe.Label", background=FELT, foreground=GOLD,
                 font=("Helvetica", 14, "bold"))
    # Кнопки: золотые выпуклые; главные — крупнее; «купить» — красная.
    for name, bg, fg, hi in (("TButton", GOLD, INK, GOLD_LIGHT),
                             ("Big.TButton", GOLD, INK, GOLD_LIGHT),
                             ("Red.TButton", RED, "#ffffff", RED_LIGHT),
                             ("Green.TButton", GREEN_BTN, "#ffffff", "#5fe39b")):
        st.configure(name, background=bg, foreground=fg, bordercolor=GOLD_DARK,
                     lightcolor=hi, darkcolor=GOLD_DARK, relief="raised",
                     padding=(12, 6), font=("Helvetica", 13, "bold"))
        st.map(name, background=[("pressed", GOLD_DARK), ("active", hi),
                                 ("disabled", "#8aa596")],
               relief=[("pressed", "sunken")])
    for name in ("Big.TButton", "Red.TButton", "Green.TButton"):
        st.configure(name, font=("Helvetica", 17, "bold"), padding=(18, 12))
    st.configure("TCheckbutton", background=FELT, foreground=ON_FELT,
                 indicatorbackground="#ffffff", indicatorforeground=INK)
    st.map("TCheckbutton", background=[("active", FELT)],
           indicatorbackground=[("selected", GOLD)])
    st.configure("TRadiobutton", background=FELT, foreground=ON_FELT,
                 indicatorbackground="#ffffff", indicatorforeground=INK)
    st.map("TRadiobutton", background=[("active", FELT)],
           indicatorbackground=[("selected", GOLD)])
    st.configure("TCombobox", fieldbackground="#ffffff", foreground=INK,
                 background=GOLD, arrowcolor=INK)
    st.map("TCombobox", fieldbackground=[("readonly", "#ffffff")],
           foreground=[("readonly", INK)], selectbackground=[("readonly", "#ffffff")],
           selectforeground=[("readonly", INK)])
    st.configure("TSpinbox", fieldbackground="#ffffff", foreground=INK,
                 background=GOLD, arrowcolor=INK)
    st.configure("TNotebook", background=FELT, borderwidth=0, tabmargins=(2, 6, 2, 0))
    st.configure("TNotebook.Tab", background=FELT_DARK, foreground=ON_FELT_MUTED,
                 padding=(14, 7), font=("Helvetica", 13, "bold"), bordercolor=FELT_DARK)
    st.map("TNotebook.Tab", background=[("selected", GOLD), ("active", FELT_LIGHT)],
           foreground=[("selected", INK)])
    st.configure("Treeview", background=CREAM, fieldbackground=CREAM, foreground=INK,
                 rowheight=26, bordercolor=GOLD_DARK)
    st.map("Treeview", background=[("selected", GOLD)], foreground=[("selected", INK)])
    st.configure("Treeview.Heading", background=FELT_DARK, foreground=GOLD_LIGHT,
                 font=("Helvetica", 12, "bold"), relief="flat")
    st.map("Treeview.Heading", background=[("active", FELT_LIGHT)])
    for bar in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        st.configure(bar, background=GOLD, troughcolor=FELT_DARK, bordercolor=FELT_DARK,
                     lightcolor=GOLD_LIGHT, darkcolor=GOLD_DARK, arrowcolor=INK,
                     gripcount=0, arrowsize=14)
        st.map(bar, background=[("active", GOLD_LIGHT), ("pressed", GOLD_DARK)])
    st.configure("Horizontal.TProgressbar", background=GOLD, troughcolor=FELT_DARK)
    st.configure("Horizontal.TScale", background=GOLD, troughcolor=FELT_DARK)
    return st


def autowrap(label: ttk.Label, pad: int = 16) -> ttk.Label:
    """Перенос длинного текста по ширине: подпись должна быть упакована с fill="x"."""
    label.bind("<Configure>", lambda e: label.configure(wraplength=max(200, e.width - pad)))
    return label


class ScrollFrame(ttk.Frame):
    """Область с вертикальной прокруткой (золотая полоса справа).

    Содержимое кладётся в self.inner. Колёсико мыши и трекпад листают,
    пока указатель над областью.
    """

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, highlightthickness=0, background=FELT, borderwidth=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, padding=(12, 12, 16, 12))
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._win, width=e.width))
        self.bind("<Enter>", lambda e: self.bind_all("<MouseWheel>", self._wheel))
        self.bind("<Leave>", lambda e: self.unbind_all("<MouseWheel>"))

    def _wheel(self, e) -> None:
        step = -e.delta if abs(e.delta) < 20 else -e.delta // 120   # Mac / Windows
        self.canvas.yview_scroll(int(step), "units")


def mix(a: str, b: str, k: float) -> str:
    """Смесь двух цветов #rrggbb: k=0 — первый, k=1 — второй."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * k):02x}" for x, y in zip(ca, cb))


def heat_color(t: float) -> str:
    """0 — холодное (синее), 1 — горячее (красное)."""
    t = max(0.0, min(1.0, t))
    stops = [(0.0, (49, 99, 206)), (0.5, (240, 240, 240)), (1.0, (214, 48, 49))]
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if t <= b:
            k = (t - a) / (b - a)
            r, g, bl = (round(ca[i] + (cb[i] - ca[i]) * k) for i in range(3))
            return f"#{r:02x}{g:02x}{bl:02x}"
    return "#d63031"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        settings = data.load_settings()
        i18n.set_lang(settings.get("lang", i18n.DEFAULT))
        self.title(app_title())
        self.geometry("1400x880")
        self.minsize(1240, 780)

        self.all_draws: dict[str, list[core.Draw]] = {}
        self.extra_draws: dict[str, list[core.Draw]] = {}
        self._updating = False
        self.sources: dict[str, Path | None] = {}
        self.stats: core.Stats | None = None
        self.fixed: set[int] = set()
        self.generated: list[list[int]] = []     # последние варианты
        self.marked: set[int] = set()             # их номера с галочкой
        self.excluded: set[int] = set()

        self.game_var = tk.StringVar(value=core.LOTTO_MAX.title)
        self.period_code = "all"
        self.kind_code = "main"
        self.strategy_var = tk.StringVar(value="hot")
        self.tickets_var = tk.IntVar(value=10)
        self.strength_var = tk.DoubleVar(value=1.0)
        self.avoid_popular_var = tk.BooleanVar(value=settings.get("avoid_popular", True))
        self.limit_var = tk.StringVar(value=f"{data.weekly_limit():g}")
        self.province_code = data.province_code(settings.get("province"))
        self.status_var = tk.StringVar()

        self._build()
        self.load_all()
        if not SELF_TEST:
            self.after(300, self.show_disclaimer_once)
            self.after(1500, self.auto_update_tick)
            self.after(6000, lambda: self.on_app_update(quiet=True))

    # ------------------------------------------------------------------ UI
    def _build(self) -> None:
        apply_theme(self)
        head = ttk.Frame(self, padding=(14, 10, 14, 0))
        head.pack(fill="x")
        logo = tk.Canvas(head, width=96, height=34, highlightthickness=0, background=FELT)
        logo.pack(side="left")
        for i, (col, hi, txt) in enumerate(((RED, RED_LIGHT, "7"), (GOLD, GOLD_LIGHT, "52"),
                                            ("#2d7fd3", "#8fd0ff", "49"))):
            x = 4 + i * 31
            logo.create_oval(x + 1, 3, x + 31, 33, fill="#062a17", outline="")
            logo.create_oval(x, 1, x + 30, 31, fill=col, outline="")
            logo.create_oval(x + 6, 5, x + 15, 12, fill=hi, outline="")
            logo.create_text(x + 15, 17, text=txt, fill="#ffffff" if i != 1 else INK,
                             font=("Helvetica", 11, "bold"))
        ttk.Label(head, text="Lotto Generator", style="Title.TLabel").pack(side="left", padx=10)
        ttk.Label(head, text="Lotto Max · Lotto 6/49", style="Muted.TLabel").pack(side="left")

        top = ttk.Frame(self, padding=(12, 10, 12, 4))
        top.pack(fill="x")
        ttk.Label(top, text=t("top.game")).pack(side="left")
        game_box = ttk.Combobox(top, textvariable=self.game_var, state="readonly", width=14,
                                values=[g.title for g in core.GAMES.values()])
        game_box.pack(side="left", padx=(4, 16))
        game_box.bind("<<ComboboxSelected>>", lambda e: self.on_game_change())

        ttk.Label(top, text=t("top.period")).pack(side="left")
        self.period_box = ttk.Combobox(top, state="readonly", width=34)
        self.period_box.pack(side="left", padx=(4, 16))
        self.period_box.bind("<<ComboboxSelected>>", lambda e: self.on_period_pick())

        ttk.Label(top, text=t("top.kind")).pack(side="left")
        self.kind_box = ttk.Combobox(top, state="readonly", width=28,
                                     values=[t(f"kind.{k}") for k in KINDS])
        self.kind_box.pack(side="left", padx=(4, 16))
        self.kind_box.bind("<<ComboboxSelected>>", lambda e: self.on_kind_pick())

        # Служебные кнопки — в шапке справа, чтобы не теснили выбор лотереи.
        ttk.Button(head, text=t("btn.update_app"),
                   command=lambda: self.on_app_update(quiet=False)).pack(side="right")
        ttk.Button(head, text=t("btn.import_csv"), command=self.on_import).pack(side="right",
                                                                               padx=6)
        ttk.Button(head, text=t("btn.update_draws"), command=self.on_update).pack(side="right")

        self.info_var = tk.StringVar()
        autowrap(ttk.Label(self, textvariable=self.info_var, padding=(12, 0),
                           style="Muted.TLabel")).pack(fill="x")
        autowrap(ttk.Label(self, textvariable=self.status_var, padding=(12, 2),
                           style="Gold.TLabel")).pack(fill="x")

        # Главная панель: последний тираж каждой игры и что по нему у моих билетов.
        board = ttk.LabelFrame(self, text=t("board.title"),
                               padding=(12, 6))
        board.pack(fill="x", padx=12, pady=(4, 0))
        self.board_vars: dict[str, tuple[tk.StringVar, tk.StringVar]] = {}
        for g in core.GAMES.values():
            row = ttk.Frame(board)
            row.pack(fill="x", pady=2)
            nums, mine = tk.StringVar(), tk.StringVar()
            ttk.Label(row, textvariable=nums, font=("Menlo", 15, "bold"),
                      width=BOARD_WIDTH).pack(side="left")
            autowrap(ttk.Label(row, textvariable=mine, font=("Helvetica", 13),
                               foreground=GOLD_LIGHT)).pack(side="left", padx=10, fill="x",
                                                            expand=True)
            self.board_vars[g.key] = (nums, mine)

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)

        # --- левая часть: шары
        left = ttk.Frame(body)
        left.pack(side="left", fill="y")
        ttk.Label(left, text=t("left.title"),
                  font=("Helvetica", 14, "bold")).pack(anchor="w")
        ttk.Label(left, text=t("left.hint"), wraplength=410,
                  foreground=ON_FELT_MUTED).pack(anchor="w", pady=(2, 6))
        self.canvas = tk.Canvas(left, width=420, height=450, highlightthickness=0,
                                background=FELT)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_ball_click)
        self.sel_var = tk.StringVar()
        ttk.Label(left, textvariable=self.sel_var, wraplength=410,
                  style="Gold.TLabel").pack(anchor="w", pady=4)
        ttk.Button(left, text=t("left.reset"),
                   command=self.clear_marks).pack(anchor="w")

        # --- правая часть: вкладки
        nb = ttk.Notebook(body)
        self.nb = nb
        nb.pack(side="left", fill="both", expand=True, padx=(16, 0))
        nb.bind("<<NotebookTabChanged>>", lambda e: self._redraw_tab())
        self._build_generator(nb)
        self._build_my_tickets(nb)
        self._build_table(nb)
        self._build_history(nb)
        self._build_backtest(nb)
        self._build_honest(nb)
        self._build_about(nb)
        self._build_lang(nb)

        autowrap(ttk.Label(self, padding=(12, 0, 12, 8), foreground=GOLD_LIGHT,
                           text=t("footer"))).pack(fill="x")

    def _build_generator(self, nb: ttk.Notebook) -> None:
        sf = ScrollFrame(nb)
        self.gen_scroll = sf
        nb.add(sf, text=t("tab.gen"))
        f = sf.inner
        style = ttk.Style(self)
        style.configure("Big.TButton", font=("Helvetica", 16, "bold"), padding=(14, 10))

        big = ttk.Frame(f)
        big.pack(fill="x", pady=(0, 10))
        ttk.Button(big, text=t("gen.btn10"), style="Big.TButton",
                   command=self.on_generate_10).pack(side="left")
        ttk.Button(big, text=t("gen.shop"), style="Red.TButton",
                   command=self.on_open_shop).pack(side="left", padx=10)

        prov = ttk.Frame(f)
        prov.pack(fill="x", pady=(0, 10))
        ttk.Label(prov, text=t("gen.province")).pack(side="left")
        codes = list(data.PROVINCES)
        prov_box = ttk.Combobox(prov, state="readonly", width=40,
                                values=[t(f"prov.{c}") for c in codes])
        prov_box.current(codes.index(self.province_code))
        prov_box.pack(side="left", padx=6)

        def pick_province(_e=None):
            self.province_code = codes[prov_box.current()]
            data.save_settings(province=self.province_code)
        prov_box.bind("<<ComboboxSelected>>", pick_province)

        ttk.Checkbutton(
            f, variable=self.avoid_popular_var,
            command=lambda: data.save_settings(avoid_popular=self.avoid_popular_var.get()),
            text=t("gen.avoid")).pack(anchor="w")
        autowrap(ttk.Label(f, style="Muted.TLabel", padding=(26, 0, 0, 8),
                           text=t("gen.avoid_hint"))).pack(fill="x")
        ttk.Label(f, text=t("gen.how"), font=("Helvetica", 13, "bold")).pack(anchor="w")
        for key in core.STRATEGIES:
            ttk.Radiobutton(f, text=core.strategy_name(key), value=key,
                            variable=self.strategy_var).pack(anchor="w", pady=1)

        row = ttk.Frame(f)
        row.pack(anchor="w", pady=(10, 4))
        ttk.Label(row, text=t("gen.count")).pack(side="left")
        ttk.Spinbox(row, from_=1, to=50, textvariable=self.tickets_var,
                    width=5).pack(side="left", padx=6)

        row2 = ttk.Frame(f)
        row2.pack(anchor="w", pady=4)
        ttk.Label(row2, text=t("gen.strength")).pack(side="left")
        ttk.Scale(row2, from_=0.0, to=3.0, variable=self.strength_var,
                  length=180).pack(side="left", padx=6)
        self.strength_lbl = ttk.Label(row2, width=4)
        self.strength_lbl.pack(side="left")
        self.strength_var.trace_add("write", lambda *a: self.strength_lbl.config(
            text=f"{self.strength_var.get():.1f}"))
        self.strength_lbl.config(text="1.0")

        btns = ttk.Frame(f)
        btns.pack(anchor="w", pady=(8, 6))
        ttk.Button(btns, text=t("gen.btn_n"),
                   command=self.on_generate).pack(side="left")
        ttk.Button(btns, text=t("gen.copy"), command=self.on_copy).pack(side="left", padx=6)

        autowrap(ttk.Label(f, foreground=ON_FELT_MUTED,
                           text=t("gen.click_hint"))).pack(fill="x")
        style.configure("Big.Treeview", font=("Menlo", 16), rowheight=32)
        style.configure("Big.Treeview.Heading", font=("Helvetica", 12, "bold"))
        box = ttk.Frame(f)
        box.pack(fill="both", expand=True)
        self.gen_tree = ttk.Treeview(box, columns=("mark", "n", "nums", "hist"),
                                     show="headings", style="Big.Treeview",
                                     selectmode="none", height=10)
        for c, key, w, a in (("mark", "col.bought_mark", 80, "center"),
                             ("n", "col.n", 50, "center"), ("nums", "col.nums", 330, "w"),
                             ("hist", "col.hist", 420, "w")):
            self.gen_tree.heading(c, text=t(key))
            self.gen_tree.column(c, width=w, anchor=a, stretch=(c == "hist"))
        sb = ttk.Scrollbar(box, orient="vertical", command=self.gen_tree.yview)
        self.gen_tree.configure(yscrollcommand=sb.set)
        self.gen_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.gen_tree.bind("<Button-1>", self.on_gen_click)

        save = ttk.Frame(f)
        save.pack(fill="x", pady=(6, 0))
        ttk.Button(save, text=t("gen.save"), style="Green.TButton",
                   command=self.on_save_bought).pack(side="left")
        ttk.Button(save, text=t("gen.mark_all"), command=self.on_mark_all).pack(side="left",
                                                                                 padx=10)
        self.bought_info = tk.StringVar()
        autowrap(ttk.Label(f, textvariable=self.bought_info, foreground=GOLD_LIGHT)).pack(
            fill="x", pady=(6, 0))

    def _build_my_tickets(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text=t("tab.mine"))
        self.my_summary = tk.StringVar()
        ttk.Label(f, textvariable=self.my_summary,
                  font=("Helvetica", 13, "bold")).pack(anchor="w", pady=(0, 6))
        box = ttk.Frame(f)                 # таблица — последней, на оставшееся место
        cols = ("game", "bought", "draw", "nums", "cost", "won", "result")
        self.my_tree = ttk.Treeview(box, columns=cols, show="headings", height=5,
                                    style="Big.Treeview", selectmode="browse")
        for c, w in (("game", 100), ("bought", 105), ("draw", 110), ("nums", 290),
                     ("cost", 60), ("won", 90), ("result", 330)):
            self.my_tree.heading(c, text=t(f"col.{c}"))
            self.my_tree.column(c, width=w, minwidth=w, anchor="w", stretch=(c == "result"))
        # Самое важное — первым: числа, тираж, результат; остальное правее.
        self.my_tree["displaycolumns"] = ("nums", "draw", "result", "won", "cost",
                                          "game", "bought")
        self.my_tree.tag_configure("win", background="#ffe9a3")
        sb = ttk.Scrollbar(box, orient="vertical", command=self.my_tree.yview)
        # «Лотерея» и «Куплен» не помещаются по ширине — до них прокрутка вбок.
        self.my_xscroll = ttk.Scrollbar(box, orient="horizontal", command=self.my_tree.xview)
        self.my_tree.configure(yscrollcommand=sb.set, xscrollcommand=self.my_xscroll.set)
        self.my_xscroll.pack(side="bottom", fill="x")
        self.my_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        # Низ вкладки крепится к нижнему краю снизу вверх: пояснение, деньги,
        # кнопки. Тогда при длинном тексте сжимается таблица, а не пропадают кнопки.
        autowrap(ttk.Label(f, foreground=ON_FELT_MUTED,
                           text=t("mine.note"))).pack(side="bottom", fill="x", pady=(6, 0))
        self.money_var = tk.StringVar()
        autowrap(ttk.Label(f, textvariable=self.money_var, font=("Helvetica", 13, "bold"),
                           foreground=GOLD_LIGHT)).pack(side="bottom", fill="x", pady=(8, 0))
        btns2 = ttk.Frame(f)
        btns2.pack(side="bottom", fill="x", pady=(6, 0))
        btns = ttk.Frame(f)
        btns.pack(side="bottom", fill="x", pady=(6, 0))
        self.my_buttons = (btns, btns2)
        ttk.Button(btns, text=t("mine.add"),
                   command=self.on_add_manual).pack(side="left")
        ttk.Button(btns, text=t("mine.delete"),
                   command=self.on_delete_ticket).pack(side="left", padx=8)
        ttk.Button(btns, text=t("mine.set_won"),
                   command=self.on_set_won).pack(side="left")
        ttk.Button(btns2, text=t("mine.export"),
                   command=self.on_export).pack(side="left")
        ttk.Button(btns2, text=t("mine.import"),
                   command=self.on_import_tickets).pack(side="left", padx=8)
        ttk.Label(btns2, text=t("mine.limit")).pack(side="left")
        lim = ttk.Spinbox(btns2, from_=0, to=10000, increment=5, width=7,
                          textvariable=self.limit_var, command=self.on_limit_change)
        lim.pack(side="left", padx=4)
        lim.bind("<FocusOut>", lambda e: self.on_limit_change())
        lim.bind("<Return>", lambda e: self.on_limit_change())
        box.pack(fill="both", expand=True)

    def _build_table(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text=t("tab.freq"))
        cols = ("num", "count", "share", "since")
        self.tree = ttk.Treeview(f, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=t(f"col.{c}"), command=lambda c=c: self.sort_table(c))
            self.tree.column(c, anchor="center", width=130)
        sb = ttk.Scrollbar(f, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self._sort = ("count", True)

    def _build_history(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text=t("tab.draws"))
        self.hist = ttk.Treeview(f, columns=("date", "nums", "bonus"), show="headings")
        for c, w in (("date", 120), ("nums", 300), ("bonus", 80)):
            self.hist.heading(c, text=t(f"col.{c}"))
            self.hist.column(c, anchor="center", width=w)
        sb = ttk.Scrollbar(f, orient="vertical", command=self.hist.yview)
        self.hist.configure(yscrollcommand=sb.set)
        self.hist.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

    def _build_backtest(self, nb: ttk.Notebook) -> None:
        sf = ScrollFrame(nb)
        nb.add(sf, text=t("tab.test"))
        f = sf.inner
        autowrap(ttk.Label(f, text=t("test.intro"))).pack(fill="x")
        row = ttk.Frame(f)
        row.pack(anchor="w", pady=8)
        ttk.Label(row, text=t("test.last")).pack(side="left")
        self.bt_last = tk.StringVar(value="300")
        ttk.Combobox(row, textvariable=self.bt_last, state="readonly", width=6,
                     values=["100", "300", "600", "1000"]).pack(side="left", padx=6)
        self.bt_btn = ttk.Button(row, text=t("test.run"), command=self.on_backtest)
        self.bt_btn.pack(side="left", padx=6)
        self.bt_prog = ttk.Progressbar(row, length=200, mode="determinate")
        self.bt_prog.pack(side="left", padx=6)
        cols = ("s", "n", "avg", "exp", "h3", "h4")
        self.bt_tree = ttk.Treeview(f, columns=cols, show="headings", height=8)
        for c, key, w in (("s", "col.strategy", 300), ("n", "col.tickets", 75),
                          ("avg", "col.avg", 115), ("exp", "col.exp", 100),
                          ("h3", "col.h3", 95), ("h4", "col.h4", 95)):
            self.bt_tree.heading(c, text=t(key))
            self.bt_tree.column(c, width=w, anchor="w" if c == "s" else "center")
        self.bt_tree.pack(fill="x")
        self.bt_verdict = tk.StringVar()
        autowrap(ttk.Label(f, textvariable=self.bt_verdict, style="Gold.TLabel",
                           font=("Helvetica", 14, "bold"))).pack(fill="x", pady=10)

    def on_backtest(self) -> None:
        g = self.game
        draws = self.all_draws.get(g.key, [])
        if len(draws) < 50:
            messagebox.showinfo(app_title(), t("test.few"))
            return
        last = min(int(self.bt_last.get()), len(draws) - 1)
        self.bt_btn.state(["disabled"])
        self.bt_prog.config(maximum=last, value=0)
        self.bt_verdict.set(t("test.running", game=g.title, n=last))

        def prog(i, n):
            if i % 10 == 0 or i == n:
                self.after(0, lambda: self.bt_prog.config(value=i))

        def work():
            import random as _r
            rows = core.backtest(g, draws, list(core.STRATEGIES), last=last,
                                 seed=_r.randrange(1 << 30), progress=prog)
            self.after(0, lambda: self._show_backtest(g, last, rows))

        threading.Thread(target=work, daemon=True).start()

    def _show_backtest(self, g: core.Game, last: int, rows) -> None:
        self.bt_btn.state(["!disabled"])
        self.bt_tree.delete(*self.bt_tree.get_children())
        for r in rows:
            self.bt_tree.insert("", "end", values=(
                core.strategy_name(r.strategy), r.tickets, i18n.num(r.avg_matches, 3),
                i18n.num(r.expected_avg, 3), r.hits3, r.hits4))
        best = max(rows, key=lambda r: r.avg_matches)
        exp = rows[0].expected_avg
        odd = [r for r in rows if abs(r.z) > 3]
        text = t("test.head", game=g.title, n=last, exp=i18n.num(exp, 3),
                 se=i18n.num(3 * rows[0].se, 3), best=core.strategy_name(best.strategy),
                 avg=i18n.num(best.avg_matches, 3))
        if odd:
            qa, qb = ("“", "”") if i18n.lang() == "en" else ("«", "»")
            text += t("test.odd", list=", ".join(f"{qa}{core.strategy_name(r.strategy)}{qb}"
                                                 for r in odd))
        else:
            text += t("test.ok")
        self.bt_verdict.set(text)

    def _build_honest(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text=t("tab.odds"))
        self.honest = tk.Text(f, wrap="word", font=("Helvetica", 14), relief="flat",
                              background=CREAM, foreground=INK, padx=14, pady=12,
                              highlightthickness=2, highlightbackground=GOLD_DARK)
        self.honest.pack(fill="both", expand=True)

    def _build_about(self, nb: ttk.Notebook) -> None:
        sf = ScrollFrame(nb)
        nb.add(sf, text=t("tab.about"))
        f = sf.inner
        ttk.Label(f, text=t("about.title"), style="Title.TLabel").pack(anchor="w")
        autowrap(ttk.Label(f, text=t("about.body"), font=("Helvetica", 14),
                           padding=(0, 8, 0, 12))).pack(fill="x")
        box = ttk.LabelFrame(f, text="  " + t("about.disclaimer_title") + "  ", padding=12)
        box.pack(fill="x", pady=(4, 12))
        autowrap(ttk.Label(box, text=t("about.disclaimer"), style="Gold.TLabel",
                           font=("Helvetica", 14, "bold"))).pack(fill="x")
        ver = upd.current_version()
        ttk.Label(f, style="Muted.TLabel",
                  text=t("about.version", v=ver[:7] if ver else t("about.version_dev"))
                  ).pack(anchor="w")

    def show_disclaimer_once(self) -> None:
        """Предупреждение об ответственности — при первом запуске, один раз."""
        if data.load_settings().get("disclaimer_ok"):
            return
        messagebox.showinfo(t("about.disclaimer_title"), t("about.disclaimer"), parent=self)
        data.save_settings(disclaimer_ok=True)

    def _build_lang(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=24)
        nb.add(f, text=t("lang.tab"))
        ttk.Label(f, text="Язык / Language / Langue", style="Title.TLabel").pack(anchor="w")
        autowrap(ttk.Label(f, text=t("lang.note"), style="Muted.TLabel",
                           padding=(0, 6, 0, 16))).pack(fill="x")
        for code, flag in (("ru", "🇷🇺"), ("en", "🇬🇧"), ("fr", "🇫🇷")):
            name = i18n.STRINGS[code]["lang.name"]
            style = "Green.TButton" if code == i18n.lang() else "Big.TButton"
            mark = "  ✓" if code == i18n.lang() else ""
            ttk.Button(f, text=f"{flag}  {name}{mark}", style=style, width=22,
                       command=lambda c=code: self.set_language(c)).pack(anchor="w", pady=6)

    redraw_fix = True

    def _redraw_tab(self) -> None:
        """На Mac вкладка, на которую вернулись, иногда остаётся пустой (видно
        на снимках сборки). Сдвиг вкладок на 1 пиксель и обратно заставляет
        перерисовать её содержимое."""
        if not self.redraw_fix:
            return
        self.nb.configure(padding=1)
        self.after(30, lambda: self.nb.winfo_exists() and self.nb.configure(padding=0))

    def set_language(self, code: str) -> None:
        """Сменить язык: запомнить и перерисовать окно, сохранив выбор и билеты."""
        if code == i18n.lang():
            return
        i18n.set_lang(code)
        data.save_settings(lang=code)
        tab = self.nb.index(self.nb.select()) if hasattr(self, "nb") else 0
        for w in self.winfo_children():
            w.destroy()
        self.title(app_title())
        self._build()
        self.on_game_change(keep_marks=True)
        self.fill_my_tickets()
        if self.generated:
            self.fill_generated()
        # На Mac вкладка, выбранная до первой раскладки окна, остаётся пустой
        # (так было с «🌐 Языком»): сначала раскладка, потом выбор вкладки.
        self.update_idletasks()
        self.after_idle(lambda: self.nb.select(tab))

    # ------------------------------------------------------------ данные
    @property
    def game(self) -> core.Game:
        return next(g for g in core.GAMES.values() if g.title == self.game_var.get())

    def load_all(self) -> None:
        for g in core.GAMES.values():
            got = data.load_text(g)
            if got:
                text, path = got
                self.all_draws[g.key], self.extra_draws[g.key] = core.parse_all(text, g)
                self.sources[g.key] = path
            else:
                self.all_draws[g.key], self.extra_draws[g.key] = [], []
                self.sources[g.key] = None
        self.on_game_change()
        self.fill_my_tickets()

    def period_codes(self) -> list[str]:
        return [c for c in PERIODS
                if c not in MAX_ONLY_PERIODS or self.game.key == "LOTTOMAX"]

    def on_period_pick(self) -> None:
        self.period_code = self.period_codes()[self.period_box.current()]
        self.refresh()

    def on_kind_pick(self) -> None:
        self.kind_code = KINDS[self.kind_box.current()]
        self.refresh()

    def on_game_change(self, keep_marks: bool = False) -> None:
        codes = self.period_codes()
        if self.period_code not in codes:
            self.period_code = "all"
        self.period_box.config(values=[t(f"period.{c}") for c in codes])
        self.period_box.current(codes.index(self.period_code))
        # У 6/49 дополнительных розыгрышей шарами в файле нет: «миллионный»
        # Gold Ball разыгрывает номер билета, а не числа.
        if not self.extra_draws.get(self.game.key):
            self.kind_code = "main"
        self.kind_box.current(KINDS.index(self.kind_code))
        self.kind_box.config(state="readonly" if self.extra_draws.get(self.game.key)
                             else "disabled")
        if not keep_marks:
            self.fixed.clear()
            self.excluded.clear()
        self.refresh()

    def selected_draws(self) -> list[core.Draw]:
        kind = self.kind_code
        main = self.all_draws.get(self.game.key, [])
        extra = self.extra_draws.get(self.game.key, [])
        draws = {"main": main, "extra": extra,
                 "all": sorted(main + extra, key=lambda d: d.when)}[kind]
        p = self.period_code
        if p == "max50":
            return core.filter_draws(draws, since=core.LOTTO_MAX_50_FROM)
        if p == "max52":
            return core.filter_draws(draws, since=core.LOTTO_MAX_52_FROM)
        v = PERIODS.get(p)
        if v is None:
            return draws
        if isinstance(v, str):
            return core.filter_draws(draws, last_n=int(v[1:]))
        return core.filter_draws(draws, since=date.today() - timedelta(days=v))

    def refresh(self) -> None:
        draws = self.selected_draws()
        g = self.game
        self.stats = core.compute_stats(g, draws)
        all_d = self.all_draws.get(g.key, [])
        if draws:
            src = self.sources.get(g.key)
            self.info_var.set(t("info.sample", game=g.title, n=len(draws),
                                d1=i18n.d(draws[0].when), d2=i18n.d(draws[-1].when),
                                main=len(all_d), extra=len(self.extra_draws.get(g.key, []))))
        else:
            self.info_var.set(t("info.empty", game=g.title))
        self.show_status()
        self.draw_balls()
        self.fill_table()
        self.fill_history(all_d)
        self.fill_honest()

    # ------------------------------------------------------------ шары
    def ball_layout(self):
        cols, r, gap = 7, 24, 7
        for i, n in enumerate(sorted(self.stats.numbers)):
            cx = 16 + r + (i % cols) * (2 * r + gap + 4)
            cy = 10 + r + (i // cols) * (2 * r + gap)
            yield n, cx, cy, r

    def draw_balls(self) -> None:
        c = self.canvas
        c.delete("all")
        st = self.stats
        if not st or not st.draws:
            c.create_text(210, 200, text=t("left.nodata"), font=("Helvetica", 16), fill=ON_FELT)
            self.sel_var.set("")
            return
        counts = [s.count for s in st.numbers.values()]
        lo, hi = min(counts), max(counts)
        for n, cx, cy, r in self.ball_layout():
            s = st.numbers[n]
            heat = (s.count - lo) / (hi - lo) if hi > lo else 0.5
            fill = "#8f9a94" if n in self.excluded else heat_color(heat)
            # объёмный шар: тень, сам шар, блик
            c.create_oval(cx - r + 2, cy - r + 4, cx + r + 2, cy + r + 4, fill="#062a17",
                          outline="")
            outline, width = (GOLD, 4) if n in self.fixed else ("#ffffff", 1)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill,
                          outline=outline, width=width, tags=(f"b{n}",))
            c.create_oval(cx - r * 0.55, cy - r * 0.78, cx - r * 0.05, cy - r * 0.42,
                          fill=mix(fill, "#ffffff", 0.6), outline="")
            for dx, dy, col in ((1, 1, "#1a1a1a"), (0, 0, "#ffffff")):
                c.create_text(cx + dx, cy - 7 + dy, text=str(n), fill=col,
                              font=("Helvetica", 16, "bold"))
                c.create_text(cx + dx, cy + 12 + dy, text=str(s.count), fill=col,
                              font=("Helvetica", 10, "bold"))
            if n in self.excluded:
                c.create_line(cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8,
                              fill="#555", width=2)
        f = ", ".join(map(str, sorted(self.fixed))) or t("none")
        x = ", ".join(map(str, sorted(self.excluded))) or t("none")
        self.sel_var.set(t("left.sel", f=f, x=x))

    def on_ball_click(self, event) -> None:
        if not self.stats:
            return
        for n, cx, cy, r in self.ball_layout():
            if (event.x - cx) ** 2 + (event.y - cy) ** 2 <= r * r:
                if n in self.fixed:
                    self.fixed.discard(n)
                    self.excluded.add(n)
                elif n in self.excluded:
                    self.excluded.discard(n)
                else:
                    if len(self.fixed) >= self.game.pick:
                        messagebox.showinfo(app_title(), t("left.max_pinned",
                                                           pick=self.game.pick))
                        return
                    self.fixed.add(n)
                self.draw_balls()
                return

    def clear_marks(self) -> None:
        self.fixed.clear()
        self.excluded.clear()
        self.draw_balls()

    # ------------------------------------------------------------ вкладки
    def fill_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        if not self.stats or not self.stats.draws:
            return
        key, rev = self._sort
        getter = {"num": lambda s: s.number, "count": lambda s: s.count,
                  "share": lambda s: s.share,
                  "since": lambda s: s.draws_since if s.draws_since is not None else 10**9}
        for s in sorted(self.stats.numbers.values(), key=getter[key], reverse=rev):
            self.tree.insert("", "end", values=(
                s.number, s.count, f"{s.share * 100:.1f}%",
                t("freq.never") if s.draws_since is None else s.draws_since))

    def sort_table(self, col: str) -> None:
        key, rev = self._sort
        self._sort = (col, not rev if key == col else col != "num")
        self.fill_table()

    def fill_history(self, draws: list[core.Draw]) -> None:
        self.hist.delete(*self.hist.get_children())
        for d in reversed(draws[-300:]):
            self.hist.insert("", "end", values=(
                i18n.d(d.when), "  ".join(f"{n:2d}" for n in d.numbers),
                d.bonus if d.bonus is not None else ""))

    def fill_honest(self) -> None:
        st, g = self.stats, self.game
        box = self.honest
        box.config(state="normal")
        box.delete("1.0", "end")
        if not st or not st.draws:
            box.config(state="disabled")
            return
        top = st.ranked()[:5]
        low = st.ranked(reverse=False)[:5]
        odds = format(g.odds(date.today()), ",").replace(",", " " if i18n.lang() != "en" else ",")
        parts = [
            t("odds.jackpot", game=g.title, pick=g.pick, odds=odds),
            t("odds.max4") if g.key == "LOTTOMAX" else "",
            t("odds.same"),
            t("odds.period", n=len(st.draws), exp=f"{st.expected:.0f}"),
            t("odds.top", list=", ".join(f"{s.number} ({s.count})" for s in top)),
            t("odds.low", list=", ".join(f"{s.number} ({s.count})" for s in low)),
            t("odds.chi", p=f"{st.p_value:.0%}"),
            (t("odds.fair") if st.p_value >= 0.05 else t("odds.unusual")) + "\n\n",
            t("odds.memory"),
            t("odds.extra", n=len(self.extra_draws.get(g.key, [])))
            if self.extra_draws.get(g.key) else t("odds.goldball"),
            t("odds.no_amounts"),
            t("odds.tip"),
        ]
        box.insert("end", "".join(parts))
        box.config(state="disabled")

    # ------------------------------------------------------------ действия
    def on_generate(self) -> None:
        if not self.stats or not self.stats.draws:
            messagebox.showwarning(app_title(), t("gen.nodata"))
            return
        try:
            n = max(1, min(50, int(self.tickets_var.get())))
            tickets = core.generate(self.stats, self.strategy_var.get(), n,
                                    self.fixed, self.excluded, self.strength_var.get(),
                                    avoid=self.bought_combos(self.game.key),
                                    avoid_popular=self.avoid_popular_var.get())
        except (ValueError, tk.TclError) as e:
            messagebox.showwarning(app_title(), str(e))
            return
        if not tickets:
            messagebox.showinfo(app_title(), t("gen.none_new"))
            return
        self.generated = tickets
        self.generated_game = self.game.key
        self.marked = set()
        self.bought_info.set("")
        self.fill_generated()

    def fill_generated(self) -> None:
        g = core.GAMES[getattr(self, "generated_game", self.game.key)]
        all_d = self.all_draws.get(g.key, [])
        self.gen_tree.delete(*self.gen_tree.get_children())
        for i, ticket in enumerate(self.generated):
            m = core.history_matches(all_d, ticket)
            hist = ", ".join(t("gen.hist_line", k=k, pick=g.pick, v=v)
                             for k, v in sorted(m.items(), reverse=True))
            self.gen_tree.insert("", "end", iid=str(i), values=(
                "☑" if i in self.marked else "☐", i + 1,
                "  ".join(f"{x:2d}" for x in ticket), hist or t("gen.hist_none")))

    def on_gen_click(self, event) -> None:
        row = self.gen_tree.identify_row(event.y)
        if row == "":
            return
        i = int(row)
        self.marked ^= {i}
        self.gen_tree.set(row, "mark", "☑" if i in self.marked else "☐")

    def on_mark_all(self) -> None:
        self.marked = set(range(len(self.generated)))
        self.fill_generated()

    def bought_combos(self, game_key: str) -> set[tuple[int, ...]]:
        return {tuple(t["numbers"]) for t in data.load_tickets() if t.get("game") == game_key}

    def on_save_bought(self) -> None:
        if not self.marked:
            messagebox.showinfo(app_title(), t("gen.need_marks"))
            return
        g = core.GAMES[self.generated_game]
        today = date.today()
        draw = core.next_draw(g, today)
        chosen = [self.generated[i] for i in sorted(self.marked)]
        try:
            added = data.add_tickets(g.key, chosen, today.isoformat(), draw.isoformat())
        except OSError as e:
            messagebox.showerror(app_title(), t("gen.save_err", e=e))
            return
        self.bought_info.set(t("gen.saved", n=added, d=i18n.d(draw)))
        self.fill_my_tickets()
        if data.over_limit(data.load_tickets(), today):
            m = data.money_summary(data.load_tickets(), today)
            messagebox.showwarning(app_title(), t("limit.over", spent=i18n.num(m["week"]),
                                                  lim=f"{data.weekly_limit():g}"))

    def fill_my_tickets(self) -> None:
        self.my_tree.delete(*self.my_tree.get_children())
        self._my_items = data.load_tickets()
        waiting = won = 0
        for i, tk_ in reversed(list(enumerate(self._my_items))):
            g = core.GAMES.get(tk_.get("game"))
            if g is None:
                continue
            try:
                day = date.fromisoformat(tk_["draw"])
                bought = date.fromisoformat(tk_["bought"])
            except (KeyError, ValueError):
                continue
            r = core.check_ticket(g, tk_["numbers"], day, self.all_draws.get(g.key, []),
                                  self.extra_draws.get(g.key, []))
            waiting += not r.drawn
            won += bool(r.prize or r.maxmillions)
            self.my_tree.insert("", "end", iid=str(i), tags=("win",) if r.prize else (),
                                values=(g.title, i18n.d(bought), i18n.d(day),
                                        "  ".join(f"{x:2d}" for x in tk_["numbers"]),
                                        i18n.num(data.ticket_cost(tk_)),
                                        i18n.num(float(tk_["won"])) if tk_.get("won") else "",
                                        r.text(g)))
        self.my_summary.set(t("mine.summary", n=len(self._my_items), w=waiting, p=won))
        m = data.money_summary(self._my_items, date.today())
        lim = data.weekly_limit()
        net = m["won"] - m["total"]
        self.money_var.set(t(
            "mine.money", week=i18n.num(m["week"]),
            of=t("mine.money_of", lim=f"{lim:g}") if lim else "",
            month=i18n.num(m["month"]), total=i18n.num(m["total"]), won=i18n.num(m["won"]),
            net=("+" if net >= 0 else "−") + i18n.num(abs(net))))
        self.fill_board()

    def fill_board(self) -> None:
        """Последний тираж каждой игры и итог по моим билетам на него."""
        items = data.load_tickets()
        for g in core.GAMES.values():
            nums_v, mine_v = self.board_vars[g.key]
            mains = self.all_draws.get(g.key, [])
            if not mains:
                nums_v.set(t("board.nodata", game=g.title))
                mine_v.set("")
                continue
            last = mains[-1]
            bonus = "  " + t("board.bonus", b=last.bonus) if last.bonus is not None else ""
            nums_v.set(f"{g.title:<10} {core.weekday_name(last.when, short=True)} "
                       f"{i18n.d(last.when)}:  "
                       + " ".join(f"{x:2d}" for x in last.numbers) + bonus)
            mine = [x for x in items if x.get("game") == g.key
                    and x.get("draw") == last.when.isoformat()]
            waiting = sum(1 for x in items if x.get("game") == g.key
                          and x.get("draw", "") > last.when.isoformat())
            if not mine:
                mine_v.set(t("board.none") + (t("board.waiting", n=waiting) if waiting else ""))
                continue
            res = [core.check_ticket(g, x["numbers"], last.when, mains,
                                     self.extra_draws.get(g.key, [])) for x in mine]
            best = max(r.matches for r in res)
            money = sum(1 for r in res if r.prize in ("cash", "jackpot"))
            free = sum(1 for r in res if r.prize == "free")
            mm = sum(r.maxmillions for r in res)
            text = t("board.summary", n=len(mine), best=best, pick=g.pick, cash=money, free=free)
            if mm:
                text += t("board.mm", n=mm)
            if waiting:
                text += t("board.waiting", n=waiting)
            mine_v.set(text)

    # ----------------------------------------------- обновление программы
    def on_app_update(self, quiet: bool) -> None:
        """Проверяет новую версию на GitHub; ставит только с согласия."""
        bundle = upd.app_bundle()
        if bundle is None:
            if not quiet:
                messagebox.showinfo(app_title(), t("upd.not_frozen"))
            return

        def work():
            try:
                info = upd.check()
                err = None
            except Exception as e:      # сеть, GitHub — сообщаем, не падаем
                info, err = None, e
            self.after(0, lambda: self._after_check(info, err, quiet, bundle))

        if not quiet:
            self.status_var.set(t("status.checking_app"))
        threading.Thread(target=work, daemon=True).start()

    def _after_check(self, info, err, quiet: bool, bundle) -> None:
        if err is not None:
            if not quiet:
                messagebox.showwarning(app_title(), t("upd.check_failed", e=err))
            self.show_status()
            return
        if info is None:
            if not quiet:
                messagebox.showinfo(app_title(), t("upd.latest"))
            self.show_status()
            return
        size = info["size"] / 1_000_000
        if not messagebox.askyesno(
                app_title(), t("upd.ask", size=f"{size:.0f}")):
            self.show_status()
            return
        self.status_var.set(t("status.downloading"))

        def work():
            try:
                new_app = upd.download_and_stage(info)
                err2 = None
            except Exception as e:
                new_app, err2 = None, e
            self.after(0, lambda: self._after_download(new_app, err2, bundle))

        threading.Thread(target=work, daemon=True).start()

    def _after_download(self, new_app, err, bundle) -> None:
        if err is not None:
            messagebox.showerror(app_title(), t("upd.failed", e=err))
            self.show_status()
            return
        upd.install_and_restart(new_app, bundle)
        self.destroy()

    def on_set_won(self) -> None:
        sel = self.my_tree.selection()
        if not sel:
            messagebox.showinfo(app_title(), t("mine.select_first"))
            return
        item = self._my_items[int(sel[0])]
        amount = simpledialog.askfloat(
            app_title(), t("mine.won_prompt"), parent=self,
            minvalue=0, initialvalue=float(item.get("won", 0) or 0))
        if amount is None:
            return
        try:
            data.set_won(item, amount)
        except ValueError as e:
            messagebox.showerror(app_title(), str(e))
        self.fill_my_tickets()

    def on_export(self) -> None:
        """Файл билетов для iPhone (тот же формат my_tickets.json)."""
        path = filedialog.asksaveasfilename(title=t("mine.export_title"), defaultextension=".json",
                                            initialfile="my_tickets.json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
        import json
        Path(path).write_text(json.dumps(data.load_tickets(), ensure_ascii=False, indent=1),
                              encoding="utf-8")
        messagebox.showinfo(app_title(), t("mine.exported"))

    def on_import_tickets(self) -> None:
        path = filedialog.askopenfilename(title=t("mine.import_title"),
                                          filetypes=[("JSON", "*.json"), (t("all_files"), "*")])
        if not path:
            return
        import json
        try:
            n = data.import_tickets(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError) as e:
            messagebox.showerror(app_title(), t("mine.read_err", e=e))
            return
        self.fill_my_tickets()
        messagebox.showinfo(app_title(), t("mine.imported", n=n))

    def on_limit_change(self) -> None:
        try:
            v = max(0.0, float(self.limit_var.get().replace(",", ".")))
        except ValueError:
            self.limit_var.set(f"{data.weekly_limit():g}")
            return
        data.save_settings(weekly_limit=v)
        self.fill_my_tickets()

    def on_delete_ticket(self) -> None:
        sel = self.my_tree.selection()
        if not sel:
            messagebox.showinfo(app_title(), t("mine.select_first"))
            return
        item = self._my_items[int(sel[0])]
        if messagebox.askyesno(app_title(), t("mine.confirm_delete",
                                              nums=" ".join(map(str, item["numbers"])))):
            data.remove_ticket(item)
            self.fill_my_tickets()

    def on_add_manual(self) -> None:
        win = tk.Toplevel(self)
        win.title(t("man.title"))
        win.transient(self)
        frm = ttk.Frame(win, padding=14)
        frm.pack(fill="both", expand=True)
        game_v = tk.StringVar(value=self.game.title)
        ttk.Label(frm, text=t("man.game")).grid(row=0, column=0, sticky="w", pady=4)
        game_box = ttk.Combobox(frm, textvariable=game_v, state="readonly", width=14,
                                values=[x.title for x in core.GAMES.values()])
        game_box.grid(row=0, column=1, sticky="w")
        ttk.Label(frm, text=t("man.nums")).grid(row=1, column=0, sticky="w", pady=4)
        nums_v = tk.StringVar()
        entry = ttk.Entry(frm, textvariable=nums_v, width=32, font=("Menlo", 16))
        entry.grid(row=1, column=1, sticky="w")
        ttk.Label(frm, text=t("man.date", fmt=t("fmt.date_hint"))).grid(row=2, column=0,
                                                                       sticky="w", pady=4)
        draw_v = tk.StringVar()
        ttk.Entry(frm, textvariable=draw_v, width=14).grid(row=2, column=1, sticky="w")

        def game_of() -> core.Game:
            return next(x for x in core.GAMES.values() if x.title == game_v.get())

        def set_default_draw(*_):
            draw_v.set(i18n.d(core.next_draw(game_of(), date.today())))
        game_box.bind("<<ComboboxSelected>>", set_default_draw)
        set_default_draw()

        def add():
            g = game_of()
            try:
                day = datetime.strptime(draw_v.get().strip(), t("fmt.date")).date()
            except ValueError:
                messagebox.showwarning(app_title(), t("man.bad_date", fmt=t("fmt.date_hint"),
                                                      ex=i18n.d(date(2026, 10, 20))), parent=win)
                return
            try:
                nums = core.parse_numbers(nums_v.get(), g, day)
            except ValueError as e:
                msg = str(e)
                messagebox.showwarning(app_title(), msg, parent=win)
                return
            n = data.add_tickets(g.key, [nums], date.today().isoformat(), day.isoformat())
            self.fill_my_tickets()
            nums_v.set("")
            status.set(t("man.added") if n else t("man.dup"))
            entry.focus_set()

        ttk.Button(frm, text=t("man.add"), command=add).grid(row=3, column=1, sticky="w",
                                                           pady=8)
        status = tk.StringVar()
        ttk.Label(frm, textvariable=status, foreground=GOLD_LIGHT).grid(row=4, column=1,
                                                                       sticky="w")
        entry.bind("<Return>", lambda e: add())
        entry.focus_set()

    def on_generate_10(self) -> None:
        self.tickets_var.set(10)
        self.on_generate()

    def shop_url(self) -> str:
        return data.PROVINCES.get(self.province_code, data.PROVINCES[data.DEFAULT_PROVINCE])

    def on_open_shop(self) -> None:
        """Открывает официальный сайт лотереи. Покупает человек сам."""
        if data.over_limit(data.load_tickets(), date.today()):
            m = data.money_summary(data.load_tickets(), date.today())
            if not messagebox.askyesno(
                    app_title(), t("shop.over_limit", spent=i18n.num(m["week"]),
                                   lim=f"{data.weekly_limit():g}")):
                return
        if not self.generated:
            self.on_generate_10()
        self.on_copy()
        webbrowser.open(self.shop_url())
        self.status_var.set(t("status.shop_opened"))

    def on_copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append("\n".join(
            f"{i}. " + " ".join(map(str, t)) for i, t in enumerate(self.generated, 1)))

    # ------------------------------------------------------- обновление
    def show_status(self) -> None:
        last = data.last_update()
        today = date.today()
        nxt = core.next_draw(self.game, today)
        when = t("status.today") if nxt == today else \
            f"{core.weekday_name(nxt)} {nxt.strftime(t('fmt.date_short'))}"
        upd_at = last.strftime(t("fmt.datetime")) if last else t("status.never")
        self.status_var.set(t("status.auto", last=upd_at, game=self.game.title, when=when))

    def auto_update_tick(self) -> None:
        """Тихо обновляет данные, если с прошлого раза прошло 3 часа."""
        if not self._updating and data.needs_update(data.last_update(), datetime.now()):
            self.on_update(quiet=True)
        self.after(CHECK_EVERY_MS, self.auto_update_tick)

    def on_update(self, quiet: bool = False) -> None:
        if self._updating:
            return
        self._updating = True
        self.status_var.set(t("status.checking_draws"))
        old = {k: list(v) for k, v in self.all_draws.items()}

        def work():
            report = data.update_all()
            self.after(0, lambda: self._after_update(report, old, quiet))

        threading.Thread(target=work, daemon=True).start()

    def _after_update(self, report: dict[str, tuple[bool, str]], old: dict,
                      quiet: bool) -> None:
        self._updating = False
        self.load_all_silent()
        fresh = []
        for g in core.GAMES.values():
            if old.get(g.key):
                for d in core.new_draws(old[g.key], self.all_draws.get(g.key, [])):
                    fresh.append(f"{g.title} {i18n.d(d.when)}: "
                                 + "  ".join(map(str, d.numbers)))
        failed = [f"{k}: {text}" for k, (ok, text) in report.items() if not ok]
        if fresh:
            mine = self.draw_report(old)
            data.notify(app_title(), mine or t("new.one", d=fresh[-1]))
            messagebox.showinfo(app_title(), t("new.title") + "\n\n" + "\n".join(fresh)
                                + ("\n\n" + mine if mine else "")
                                + "\n\n" + t("new.checked"))
        elif not quiet:
            messagebox.showinfo(app_title(), "\n".join(f"{k}: {text}"
                                                       for k, (ok, text) in report.items()))
        if failed and quiet:
            self.status_var.set(t("status.update_failed", why="; ".join(failed)))

    def draw_report(self, old: dict) -> str:
        """Короткий итог по моим билетам на только что вышедшие тиражи."""
        items = data.load_tickets()
        parts = []
        for g in core.GAMES.values():
            mains = self.all_draws.get(g.key, [])
            for d in core.new_draws(old.get(g.key, []), mains):
                mine = [x for x in items if x.get("game") == g.key
                        and x.get("draw") == d.when.isoformat()]
                if not mine:
                    continue
                res = [core.check_ticket(g, x["numbers"], d.when, mains,
                                         self.extra_draws.get(g.key, [])) for x in mine]
                best = max(r.matches for r in res)
                prizes = sum(1 for r in res if r.prize or r.maxmillions)
                parts.append(t("new.report", game=g.title, d=d.when.strftime(t("fmt.date_short")),
                               n=len(mine), best=best, pick=g.pick, p=prizes))
        return "; ".join(parts)

    def load_all_silent(self) -> None:
        for g in core.GAMES.values():
            got = data.load_text(g)
            if got:
                self.all_draws[g.key], self.extra_draws[g.key] = core.parse_all(got[0], g)
                self.sources[g.key] = got[1]
        self.refresh()
        self.fill_my_tickets()

    def on_import(self) -> None:
        path = filedialog.askopenfilename(
            title=t("csv.title", game=self.game.title),
            filetypes=[("CSV", "*.csv"), (t("all_files"), "*")])
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
            n = data.save_checked(self.game, text, data.user_dir())
        except Exception as e:
            messagebox.showerror(app_title(), str(e))
            return
        self.load_all_silent()
        messagebox.showinfo(app_title(), t("csv.loaded", game=self.game.title, n=n))


def selftest() -> None:
    """Проверка при сборке: окно открывается, данные есть, билеты получаются."""
    import tempfile
    os.environ["LOTTO_DATA_DIR"] = tempfile.mkdtemp()   # не трогаем настоящие билеты
    app = App()
    app.update()
    for title in (g.title for g in core.GAMES.values()):
        app.game_var.set(title)
        app.on_game_change()
        n = len(app.all_draws[app.game.key])
        assert n >= app.game.min_draws, f"{title}: тиражей {n}"
        app.strategy_var.set("hot")
        app.on_generate_10()
        assert len(app.generated) == 10 == len(app.gen_tree.get_children())
        text = "\n".join(" ".join(map(str, t)) for t in app.generated)
        extra = len(app.extra_draws[app.game.key])
        for kind in KINDS:
            app.kind_code = kind
            app.refresh()
            print(f"  {kind}: розыгрышей в выборке {len(app.stats.draws)}")
        app.kind_code = "main"
        app.refresh()
        print(f"SELFTEST {title}: тиражей {n}, MaxMillions {extra}")
        print(app.status_var.get())
        print(text)
    # «Мои билеты»: галочки → сохранение → больше не предлагаются → сверка.
    app.game_var.set(core.LOTTO_MAX.title)
    app.on_game_change()
    app.strategy_var.set("top")
    app.on_generate_10()
    first_top = list(app.generated[0])
    app.marked = {0, 1, 2, 3, 4}
    app.on_save_bought()
    saved = app.bought_combos("LOTTOMAX")
    assert len(saved) == 5 and len(app.my_tree.get_children()) == 5, saved
    assert all(t("res.waiting") in app.my_tree.set(r, "result")
               for r in app.my_tree.get_children())
    app.on_generate_10()
    again = {tuple(t) for t in app.generated}
    assert not again & saved, again & saved
    assert app.generated[0] != first_top, (first_top, app.generated[0])
    last = app.all_draws["LOTTOMAX"][-1]
    data.add_tickets("LOTTOMAX", [list(last.numbers)], last.when.isoformat(),
                     last.when.isoformat())
    app.fill_my_tickets()
    results = [app.my_tree.set(r, "result") for r in app.my_tree.get_children()]
    assert any(r.startswith(t("res.matches", m=7, pick=7)) and t("prize.jackpot") in r
               for r in results), results
    print("SELFTEST мои билеты:", app.my_summary.get())
    app.nb.select(1)
    app.update()
    assert app.my_xscroll.winfo_ismapped(), "нет прокрутки вбок у «Моих билетов»"
    assert all(b.winfo_ismapped() for b in app.my_buttons), "кнопки «Моих билетов» не видны"
    app.my_tree.xview_moveto(1.0)
    app.update()
    assert app.my_tree.xview()[1] == 1.0, app.my_tree.xview()
    app.my_tree.xview_moveto(0.0)
    for r in app.my_tree.get_children():
        print("  ", app.my_tree.item(r)["values"])

    # Главная панель и самообновление.
    for key, (nums, mine) in app.board_vars.items():
        print("SELFTEST панель:", nums.get(), "|", mine.get())
        assert nums.get() and t("board.nodata", game="") not in nums.get()
    expect = os.environ.get("EXPECT_VERSION")
    if expect:
        assert upd.current_version() == expect, (upd.current_version(), expect)
        assert upd.app_bundle() is not None, "не нашли .app"
        print("SELFTEST версия:", upd.current_version(), "в", upd.app_bundle())
    hi = [d for d in app.all_draws["LOTTOMAX"] if d.when >= core.LOTTO_MAX_52_FROM]
    print(f"SELFTEST тиражей Lotto Max по правилам 1–52: {len(hi)}, "
          f"чисел 51/52 в них: {sum(1 for d in hi for x in d.numbers if x > 50)}")

    # Проверка на истории, деньги, «редкие у людей» — на настоящих тиражах.
    rows = core.backtest(core.LOTTO_MAX, app.all_draws["LOTTOMAX"], list(core.STRATEGIES),
                         last=200)
    app.game_var.set(core.LOTTO_MAX.title)
    app._show_backtest(core.LOTTO_MAX, 200, rows)
    for r in app.bt_tree.get_children():
        print("SELFTEST проверка:", app.bt_tree.item(r)["values"])
    print("SELFTEST вывод:", app.bt_verdict.get())
    assert len(app.bt_tree.get_children()) == len(core.STRATEGIES)
    print("SELFTEST деньги:", app.money_var.get())
    assert app.money_var.get().startswith(t("mine.money").split("{")[0])
    app.avoid_popular_var.set(True)
    app.strategy_var.set("random")
    app.on_generate_10()
    assert not any(core.popular_reasons(t, core.LOTTO_MAX) for t in app.generated)

    shots_dir = os.environ.get("LOTTO_SHOTS_DIR")
    if shots_dir:
        shots(app, Path(shots_dir))

    # Языки: окно перерисовывается, выбор, варианты и билеты сохраняются.
    rows_before = len(app.my_tree.get_children())
    gen_before = [list(x) for x in app.generated]
    app.period_code = "y5"
    app.on_game_change(keep_marks=True)
    for code in ("en", "fr", "ru"):
        app.nb.select(7)                   # как у человека: кнопки языка — на этой вкладке
        app.update()
        app.set_language(code)
        app.update()
        assert i18n.lang() == code and data.load_settings().get("lang") == code
        tabs = [app.nb.tab(i, "text") for i in range(app.nb.index("end"))]
        assert tabs[0] == i18n.STRINGS[code]["tab.gen"], tabs
        assert i18n.STRINGS[code]["tab.about"] in tabs, tabs
        assert app.title() == i18n.STRINGS[code]["app.title"]
        assert len(app.my_tree.get_children()) == rows_before
        assert app.generated == gen_before and len(app.gen_tree.get_children()) == 10
        assert app.period_code == "y5" and app.period_box.get() == t("period.y5")
        assert t("res.waiting") in " ".join(app.my_tree.set(r, "result")
                                            for r in app.my_tree.get_children())
        for nums, _ in app.board_vars.values():   # строка тиража не обрезана
            assert len(nums.get()) <= BOARD_WIDTH, (len(nums.get()), nums.get())
        # Язык меняют, стоя на вкладке «Язык»: после перерисовки она не пустая.
        page = app.nametowidget(app.nb.select())
        assert app.nb.index("current") == 7 and page.winfo_children()
        assert all(w.winfo_ismapped() for w in page.winfo_children()), \
            [w.winfo_ismapped() for w in page.winfo_children()]
        app.nb.select(1)
        app.update()
        assert all(b.winfo_ismapped() for b in app.my_buttons), f"{code}: кнопки не видны"
        app.nb.select(7)
        app.update()
        print(f"SELFTEST язык {code}: вкладки {tabs}")
        print("   ", app.status_var.get())
        print("   ", app.bt_verdict.get()[:80] if app.bt_verdict.get() else "")
        if shots_dir and code != "ru":
            shots(app, Path(shots_dir), prefix=f"{code}-",
                  which=("5-lang", "1-gen", "2-mine", "6-about"))

    if shots_dir:
        # После смены языка: «ушёл с вкладки и вернулся» — без поправки и с ней.
        for fix in (False, True):
            app.redraw_fix = fix
            for code in ("fr", "ru"):
                app.nb.select(7)
                app.update()
                app.set_language(code)
                app.update()
            for tab in (1, 2, 5, 7):
                app.nb.select(tab)
                app.update()
                app.nb.select(0)
                app.update()
                shots(app, Path(shots_dir), prefix=f"diag-{'fix' if fix else 'raw'}-{tab}-",
                      which=("back",))
        app.redraw_fix = True

    opened = []
    webbrowser.open = opened.append       # браузер в самопроверке не открываем
    for prov in data.PROVINCES:
        app.province_code = prov
        app.on_open_shop()
    assert opened == list(data.PROVINCES.values()), opened
    print("SELFTEST сайты:", opened)
    app.destroy()
    print("SELFTEST OK")


def shots(app: "App", folder: Path, prefix: str = "",
          which: tuple = ("1-gen", "1b-gen-bottom", "2-mine", "3-test", "4-odds", "6-about")) -> None:
    """Снимки окна для проверки оформления (кладутся в folder при сборке)."""
    import subprocess
    import time
    folder.mkdir(parents=True, exist_ok=True)
    app.geometry("1400x870+0+30")
    nb = app.nb
    plan = {"1-gen": 0, "1b-gen-bottom": 0, "2-mine": 1, "3-test": 4, "4-odds": 5,
            "6-about": 6, "5-lang": 7}
    if which == ("back",):              # вернуться на вкладку, где были до «Генератора»
        plan = {"back": int(prefix.split("-")[2])}
    for name in which:
        nb.select(plan[name])
        app.gen_scroll.canvas.yview_moveto(1.0 if name == "1b-gen-bottom" else 0.0)
        app.lift()
        app.attributes("-topmost", True)
        for _ in range(10):
            app.update()
            time.sleep(0.1)
        try:
            subprocess.run(["screencapture", "-x", "-R0,0,1400,910",
                            str(folder / f"{prefix}{name}.png")], timeout=20, check=True)
            print("SHOT", name, "ok")
        except Exception as e:      # снимок — не повод валить сборку
            print("SHOT-FAIL", name, e)


def main() -> None:
    if os.environ.get("LOTTO_SELFTEST") == "1":
        selftest()
        return
    App().mainloop()


if __name__ == "__main__":
    main()
