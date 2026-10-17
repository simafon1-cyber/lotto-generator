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

import lotto_core as core
import lotto_data as data
import lotto_update as upd

APP_TITLE = "Генератор чисел — Lotto Max и Lotto 6/49"

PERIODS = {
    "Всё время": None,
    "Последние 10 лет": 3653,
    "Последние 5 лет": 1826,
    "Последний год": 365,
    "Последние 100 тиражей": "n100",
    "Последние 50 тиражей": "n50",
}
PERIOD_MAX50 = "С 14.05.2019 (Lotto Max 1–50 и 1–52)"
PERIOD_MAX52 = "С 14.04.2026 (новые правила, 1–52)"


# Какие розыгрыши учитывать. Дополнительные — это MaxMillions (по 1 000 000 $)
# и с 14.04.2026 MaxPlus (от 100 000 $) у Lotto Max: в файле BCLC это строки
# того же тиража с номером последовательности больше нуля.
KINDS = {
    "Только основные": "main",
    "Основные + MaxMillions/MaxPlus": "all",
    "Только MaxMillions/MaxPlus": "extra",
}
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
        self.title(APP_TITLE)
        self.geometry("1400x880")
        self.minsize(1240, 780)

        self.all_draws: dict[str, list[core.Draw]] = {}
        self.extra_draws: dict[str, list[core.Draw]] = {}
        self._updating = False
        settings = data.load_settings()
        self.sources: dict[str, Path | None] = {}
        self.stats: core.Stats | None = None
        self.fixed: set[int] = set()
        self.generated: list[list[int]] = []     # последние варианты
        self.marked: set[int] = set()             # их номера с галочкой
        self.excluded: set[int] = set()

        self.game_var = tk.StringVar(value=core.LOTTO_MAX.title)
        self.period_var = tk.StringVar(value="Всё время")
        self.strategy_var = tk.StringVar(value="hot")
        self.tickets_var = tk.IntVar(value=10)
        self.strength_var = tk.DoubleVar(value=1.0)
        self.kind_var = tk.StringVar(value="Только основные")
        self.avoid_popular_var = tk.BooleanVar(value=settings.get("avoid_popular", True))
        self.limit_var = tk.StringVar(value=f"{data.weekly_limit():g}")
        province = settings.get("province")
        self.province_var = tk.StringVar(
            value=province if province in data.PROVINCES else data.DEFAULT_PROVINCE)
        self.status_var = tk.StringVar()

        self._build()
        self.load_all()
        if not SELF_TEST:
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
        ttk.Label(top, text="Лотерея:").pack(side="left")
        game_box = ttk.Combobox(top, textvariable=self.game_var, state="readonly", width=14,
                                values=[g.title for g in core.GAMES.values()])
        game_box.pack(side="left", padx=(4, 16))
        game_box.bind("<<ComboboxSelected>>", lambda e: self.on_game_change())

        ttk.Label(top, text="Период:").pack(side="left")
        self.period_box = ttk.Combobox(top, textvariable=self.period_var, state="readonly",
                                       width=28)
        self.period_box.pack(side="left", padx=(4, 16))
        self.period_box.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(top, text="Розыгрыши:").pack(side="left")
        self.kind_box = ttk.Combobox(top, textvariable=self.kind_var, state="readonly",
                                     width=22, values=list(KINDS))
        self.kind_box.pack(side="left", padx=(4, 16))
        self.kind_box.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # Служебные кнопки — в шапке справа, чтобы не теснили выбор лотереи.
        ttk.Button(head, text="⬆ Обновить программу",
                   command=lambda: self.on_app_update(quiet=False)).pack(side="right")
        ttk.Button(head, text="Загрузить CSV…", command=self.on_import).pack(side="right",
                                                                           padx=6)
        ttk.Button(head, text="↻ Обновить тиражи", command=self.on_update).pack(side="right")

        self.info_var = tk.StringVar()
        autowrap(ttk.Label(self, textvariable=self.info_var, padding=(12, 0),
                           style="Muted.TLabel")).pack(fill="x")
        autowrap(ttk.Label(self, textvariable=self.status_var, padding=(12, 2),
                           style="Gold.TLabel")).pack(fill="x")

        # Главная панель: последний тираж каждой игры и что по нему у моих билетов.
        board = ttk.LabelFrame(self, text="  Последние тиражи и ваши билеты  ",
                               padding=(12, 6))
        board.pack(fill="x", padx=12, pady=(4, 0))
        self.board_vars: dict[str, tuple[tk.StringVar, tk.StringVar]] = {}
        for g in core.GAMES.values():
            row = ttk.Frame(board)
            row.pack(fill="x", pady=2)
            nums, mine = tk.StringVar(), tk.StringVar()
            ttk.Label(row, textvariable=nums, font=("Menlo", 15, "bold"),
                      width=58).pack(side="left")
            autowrap(ttk.Label(row, textvariable=mine, font=("Helvetica", 13),
                               foreground=GOLD_LIGHT)).pack(side="left", padx=10, fill="x",
                                                            expand=True)
            self.board_vars[g.key] = (nums, mine)

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)

        # --- левая часть: шары
        left = ttk.Frame(body)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Частота каждого числа",
                  font=("Helvetica", 14, "bold")).pack(anchor="w")
        ttk.Label(left, text="Красное — выпадало чаще, синее — реже.\n"
                             "Щелчок: закрепить (зелёное кольцо) → исключить "
                             "(серое) → обычное.",
                  foreground=ON_FELT_MUTED).pack(anchor="w", pady=(2, 6))
        self.canvas = tk.Canvas(left, width=420, height=450, highlightthickness=0,
                                background=FELT)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_ball_click)
        self.sel_var = tk.StringVar()
        ttk.Label(left, textvariable=self.sel_var, wraplength=410,
                  style="Gold.TLabel").pack(anchor="w", pady=4)
        ttk.Button(left, text="Сбросить закреплённые и исключённые",
                   command=self.clear_marks).pack(anchor="w")

        # --- правая часть: вкладки
        nb = ttk.Notebook(body)
        nb.pack(side="left", fill="both", expand=True, padx=(16, 0))
        self._build_generator(nb)
        self._build_my_tickets(nb)
        self._build_table(nb)
        self._build_history(nb)
        self._build_backtest(nb)
        self._build_honest(nb)

        ttk.Label(self, padding=(12, 0, 12, 8), foreground=GOLD_LIGHT,
                  text="Каждый тираж независим: прошлые частоты не повышают шанс выигрыша. "
                       "Играйте только на те деньги, которые не жалко потерять.").pack(fill="x")

    def _build_generator(self, nb: ttk.Notebook) -> None:
        sf = ScrollFrame(nb)
        self.gen_scroll = sf
        nb.add(sf, text="Генератор")
        f = sf.inner
        style = ttk.Style(self)
        style.configure("Big.TButton", font=("Helvetica", 16, "bold"), padding=(14, 10))

        big = ttk.Frame(f)
        big.pack(fill="x", pady=(0, 10))
        ttk.Button(big, text="🎲  Сгенерировать 10 вариантов", style="Big.TButton",
                   command=self.on_generate_10).pack(side="left")
        ttk.Button(big, text="🛒  Открыть сайт для покупки", style="Red.TButton",
                   command=self.on_open_shop).pack(side="left", padx=10)

        prov = ttk.Frame(f)
        prov.pack(fill="x", pady=(0, 10))
        ttk.Label(prov, text="Где покупаете (провинция):").pack(side="left")
        prov_box = ttk.Combobox(prov, textvariable=self.province_var, state="readonly",
                                width=36, values=list(data.PROVINCES))
        prov_box.pack(side="left", padx=6)
        prov_box.bind("<<ComboboxSelected>>",
                      lambda e: data.save_settings(province=self.province_var.get()))

        ttk.Checkbutton(
            f, variable=self.avoid_popular_var,
            command=lambda: data.save_settings(avoid_popular=self.avoid_popular_var.get()),
            text="Избегать комбинаций, которые часто выбирают люди").pack(anchor="w")
        autowrap(ttk.Label(f, style="Muted.TLabel", padding=(26, 0, 0, 8),
                           text="Дни рождения 1–31, ряды подряд, «лесенки», одинаковые "
                                "последние цифры. Шанс выиграть тот же, но джекпот "
                                "реже придётся делить.")).pack(fill="x")
        ttk.Label(f, text="Как выбирать числа:", font=("Helvetica", 13, "bold")).pack(anchor="w")
        for key, label in core.STRATEGIES.items():
            ttk.Radiobutton(f, text=label, value=key,
                            variable=self.strategy_var).pack(anchor="w", pady=1)

        row = ttk.Frame(f)
        row.pack(anchor="w", pady=(10, 4))
        ttk.Label(row, text="Сколько билетов:").pack(side="left")
        ttk.Spinbox(row, from_=1, to=50, textvariable=self.tickets_var,
                    width=5).pack(side="left", padx=6)

        row2 = ttk.Frame(f)
        row2.pack(anchor="w", pady=4)
        ttk.Label(row2, text="Сила перекоса к частым/редким:").pack(side="left")
        ttk.Scale(row2, from_=0.0, to=3.0, variable=self.strength_var,
                  length=180).pack(side="left", padx=6)
        self.strength_lbl = ttk.Label(row2, width=4)
        self.strength_lbl.pack(side="left")
        self.strength_var.trace_add("write", lambda *a: self.strength_lbl.config(
            text=f"{self.strength_var.get():.1f}"))
        self.strength_lbl.config(text="1.0")

        btns = ttk.Frame(f)
        btns.pack(anchor="w", pady=(8, 6))
        ttk.Button(btns, text="Сгенерировать столько, сколько указано",
                   command=self.on_generate).pack(side="left")
        ttk.Button(btns, text="Копировать", command=self.on_copy).pack(side="left", padx=6)

        autowrap(ttk.Label(f, foreground=ON_FELT_MUTED,
                           text="Щёлкните по строке, чтобы поставить галочку ☑ у купленных "
                                "вариантов, затем «Сохранить купленные».")).pack(fill="x")
        style.configure("Big.Treeview", font=("Menlo", 16), rowheight=32)
        style.configure("Big.Treeview.Heading", font=("Helvetica", 12, "bold"))
        box = ttk.Frame(f)
        box.pack(fill="both", expand=True)
        self.gen_tree = ttk.Treeview(box, columns=("mark", "n", "nums", "hist"),
                                     show="headings", style="Big.Treeview",
                                     selectmode="none", height=10)
        for c, t, w, a in (("mark", "Куплен", 80, "center"), ("n", "№", 50, "center"),
                           ("nums", "Числа", 330, "w"),
                           ("hist", "В истории совпало бы", 420, "w")):
            self.gen_tree.heading(c, text=t)
            self.gen_tree.column(c, width=w, anchor=a, stretch=(c == "hist"))
        sb = ttk.Scrollbar(box, orient="vertical", command=self.gen_tree.yview)
        self.gen_tree.configure(yscrollcommand=sb.set)
        self.gen_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.gen_tree.bind("<Button-1>", self.on_gen_click)

        save = ttk.Frame(f)
        save.pack(fill="x", pady=(6, 0))
        ttk.Button(save, text="✅  Сохранить купленные", style="Green.TButton",
                   command=self.on_save_bought).pack(side="left")
        ttk.Button(save, text="Отметить все", command=self.on_mark_all).pack(side="left",
                                                                              padx=10)
        self.bought_info = tk.StringVar()
        autowrap(ttk.Label(f, textvariable=self.bought_info, foreground=GOLD_LIGHT)).pack(
            fill="x", pady=(6, 0))

    def _build_my_tickets(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text="Мои билеты")
        self.my_summary = tk.StringVar()
        ttk.Label(f, textvariable=self.my_summary,
                  font=("Helvetica", 13, "bold")).pack(anchor="w", pady=(0, 6))
        box = ttk.Frame(f)
        box.pack(fill="both", expand=True)
        cols = ("game", "bought", "draw", "nums", "cost", "won", "result")
        self.my_tree = ttk.Treeview(box, columns=cols, show="headings",
                                    style="Big.Treeview", selectmode="browse")
        for c, t, w in (("game", "Лотерея", 100), ("bought", "Куплен", 105),
                        ("draw", "Тираж", 110), ("nums", "Числа", 290),
                        ("cost", "Цена", 60), ("won", "Выиграно", 90),
                        ("result", "Результат", 330)):
            self.my_tree.heading(c, text=t)
            self.my_tree.column(c, width=w, minwidth=w, anchor="w", stretch=(c == "result"))
        # Самое важное — первым: числа, тираж, результат; остальное правее.
        self.my_tree["displaycolumns"] = ("nums", "draw", "result", "won", "cost",
                                          "game", "bought")
        self.my_tree.tag_configure("win", background="#ffe9a3")
        sb = ttk.Scrollbar(box, orient="vertical", command=self.my_tree.yview)
        self.my_tree.configure(yscrollcommand=sb.set)
        self.my_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        btns = ttk.Frame(f)
        btns.pack(fill="x", pady=(6, 0))
        btns2 = ttk.Frame(f)
        btns2.pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="Добавить билет вручную…",
                   command=self.on_add_manual).pack(side="left")
        ttk.Button(btns, text="Удалить выбранный",
                   command=self.on_delete_ticket).pack(side="left", padx=8)
        ttk.Button(btns, text="Записать выигрыш…",
                   command=self.on_set_won).pack(side="left")
        ttk.Button(btns2, text="Сохранить файл… (для iPhone)",
                   command=self.on_export).pack(side="left")
        ttk.Button(btns2, text="Загрузить файл…",
                   command=self.on_import_tickets).pack(side="left", padx=8)
        ttk.Label(btns2, text="   Лимит в неделю, $ (0 — без лимита):").pack(side="left")
        lim = ttk.Spinbox(btns2, from_=0, to=10000, increment=5, width=7,
                          textvariable=self.limit_var, command=self.on_limit_change)
        lim.pack(side="left", padx=4)
        lim.bind("<FocusOut>", lambda e: self.on_limit_change())
        lim.bind("<Return>", lambda e: self.on_limit_change())
        self.money_var = tk.StringVar()
        autowrap(ttk.Label(f, textvariable=self.money_var, font=("Helvetica", 13, "bold"),
                           foreground=GOLD_LIGHT)).pack(fill="x", pady=(8, 0))
        autowrap(ttk.Label(f, foreground=ON_FELT_MUTED,
                           text="После каждого тиража программа сама сверит ваши билеты. "
                                "Окончательную сумму выигрыша всегда проверяйте на сайте "
                                "лотереи или в кассе: здесь видно только, сколько чисел "
                                "совпало.")).pack(fill="x", pady=(6, 0))

    def _build_table(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text="Частоты")
        cols = ("num", "count", "share", "since")
        self.tree = ttk.Treeview(f, columns=cols, show="headings")
        heads = {"num": "Число", "count": "Сколько раз выпало",
                 "share": "% тиражей", "since": "Тиражей назад"}
        for c in cols:
            self.tree.heading(c, text=heads[c], command=lambda c=c: self.sort_table(c))
            self.tree.column(c, anchor="center", width=130)
        sb = ttk.Scrollbar(f, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self._sort = ("count", True)

    def _build_history(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text="Тиражи")
        self.hist = ttk.Treeview(f, columns=("date", "nums", "bonus"), show="headings")
        for c, t, w in (("date", "Дата", 120), ("nums", "Числа", 300), ("bonus", "Бонус", 80)):
            self.hist.heading(c, text=t)
            self.hist.column(c, anchor="center", width=w)
        sb = ttk.Scrollbar(f, orient="vertical", command=self.hist.yview)
        self.hist.configure(yscrollcommand=sb.set)
        self.hist.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

    def _build_backtest(self, nb: ttk.Notebook) -> None:
        sf = ScrollFrame(nb)
        nb.add(sf, text="Проверка")
        f = sf.inner
        autowrap(ttk.Label(f, text=(
            "Честная проверка способов выбора. Для каждого из последних тиражей "
            "программа считает частоты ТОЛЬКО по тиражам до него, делает 10 билетов "
            "каждым способом и смотрит, сколько чисел совпало. Если бы «частые» "
            "числа помогали, у них совпадало бы больше, чем у случайных."))).pack(fill="x")
        row = ttk.Frame(f)
        row.pack(anchor="w", pady=8)
        ttk.Label(row, text="Сколько последних тиражей:").pack(side="left")
        self.bt_last = tk.StringVar(value="300")
        ttk.Combobox(row, textvariable=self.bt_last, state="readonly", width=6,
                     values=["100", "300", "600", "1000"]).pack(side="left", padx=6)
        self.bt_btn = ttk.Button(row, text="Запустить проверку", command=self.on_backtest)
        self.bt_btn.pack(side="left", padx=6)
        self.bt_prog = ttk.Progressbar(row, length=200, mode="determinate")
        self.bt_prog.pack(side="left", padx=6)
        cols = ("s", "n", "avg", "exp", "h3", "h4")
        self.bt_tree = ttk.Treeview(f, columns=cols, show="headings", height=8)
        for c, t, w in (("s", "Способ", 300), ("n", "Билетов", 75),
                        ("avg", "Совпало в ср.", 115), ("exp", "Ожидание", 100),
                        ("h3", "3 и больше", 95), ("h4", "4 и больше", 95)):
            self.bt_tree.heading(c, text=t)
            self.bt_tree.column(c, width=w, anchor="w" if c == "s" else "center")
        self.bt_tree.pack(fill="x")
        self.bt_verdict = tk.StringVar()
        autowrap(ttk.Label(f, textvariable=self.bt_verdict, style="Gold.TLabel",
                           font=("Helvetica", 14, "bold"))).pack(fill="x", pady=10)

    def on_backtest(self) -> None:
        g = self.game
        draws = self.all_draws.get(g.key, [])
        if len(draws) < 50:
            messagebox.showinfo(APP_TITLE, "Мало тиражей для проверки.")
            return
        last = min(int(self.bt_last.get()), len(draws) - 1)
        self.bt_btn.state(["disabled"])
        self.bt_prog.config(maximum=last, value=0)
        self.bt_verdict.set(f"Проверяю {g.title} на {last} тиражах…")

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
                core.STRATEGIES[r.strategy], r.tickets, f"{r.avg_matches:.3f}",
                f"{r.expected_avg:.3f}", r.hits3, r.hits4))
        best = max(rows, key=lambda r: r.avg_matches)
        exp = rows[0].expected_avg
        odd = [r for r in rows if abs(r.z) > 3]
        text = (f"{g.title}, {last} тиражей. Ожидание у случайного билета — "
                f"{exp:.3f} совпадения, обычный разброс ±{3 * rows[0].se:.3f}. "
                f"Лучше всех в этот раз: «{core.STRATEGIES[best.strategy]}» — "
                f"{best.avg_matches:.3f}. ")
        if odd:
            text += ("Разница у способов " + ", ".join(
                f"«{core.STRATEGIES[r.strategy]}»" for r in odd)
                + " больше обычного разброса. Запустите проверку ещё раз: если "
                "повторится — это стоит изучить, если нет — была случайность.")
        else:
            text += ("Все способы в пределах обычного случайного разброса: ни один "
                     "не угадывает лучше случайного. При новом запуске «лучший» "
                     "может смениться.")
        self.bt_verdict.set(text)

    def _build_honest(self, nb: ttk.Notebook) -> None:
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="Шансы")
        self.honest = tk.Text(f, wrap="word", font=("Helvetica", 14), relief="flat",
                              background=CREAM, foreground=INK, padx=14, pady=12,
                              highlightthickness=2, highlightbackground=GOLD_DARK)
        self.honest.pack(fill="both", expand=True)

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

    def on_game_change(self) -> None:
        values = list(PERIODS)
        if self.game.key == "LOTTOMAX":
            values += [PERIOD_MAX50, PERIOD_MAX52]
        self.period_box.config(values=values)
        if self.period_var.get() not in values:
            self.period_var.set("Всё время")
        # У 6/49 дополнительных розыгрышей шарами в файле нет: «миллионный»
        # Gold Ball разыгрывает номер билета, а не числа.
        if self.extra_draws.get(self.game.key):
            self.kind_box.config(state="readonly")
        else:
            self.kind_var.set("Только основные")
            self.kind_box.config(state="disabled")
        self.fixed.clear()
        self.excluded.clear()
        self.refresh()

    def selected_draws(self) -> list[core.Draw]:
        kind = KINDS.get(self.kind_var.get(), "main")
        main = self.all_draws.get(self.game.key, [])
        extra = self.extra_draws.get(self.game.key, [])
        draws = {"main": main, "extra": extra,
                 "all": sorted(main + extra, key=lambda d: d.when)}[kind]
        p = self.period_var.get()
        if p == PERIOD_MAX50:
            return core.filter_draws(draws, since=core.LOTTO_MAX_50_FROM)
        if p == PERIOD_MAX52:
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
            self.info_var.set(
                f"{g.title}: в выборке {len(draws)} розыгрышей, с {draws[0].when:%d.%m.%Y} "
                f"по {draws[-1].when:%d.%m.%Y} (в базе основных {len(all_d)}, "
                f"MaxMillions/MaxPlus {len(self.extra_draws.get(g.key, []))}).")
        else:
            self.info_var.set(f"{g.title}: в выбранной выборке нет розыгрышей. "
                              f"Смените период или вид розыгрышей, либо нажмите "
                              f"«Обновить из интернета».")
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
            c.create_text(235, 200, text="Нет данных", font=("Helvetica", 16), fill=ON_FELT)
            self.sel_var.set("")
            return
        counts = [s.count for s in st.numbers.values()]
        lo, hi = min(counts), max(counts)
        for n, cx, cy, r in self.ball_layout():
            s = st.numbers[n]
            t = (s.count - lo) / (hi - lo) if hi > lo else 0.5
            fill = "#8f9a94" if n in self.excluded else heat_color(t)
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
        f = ", ".join(map(str, sorted(self.fixed))) or "нет"
        x = ", ".join(map(str, sorted(self.excluded))) or "нет"
        self.sel_var.set(f"Закреплены (войдут в каждый билет): {f}\nИсключены: {x}")

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
                        messagebox.showinfo(APP_TITLE, f"В билете {self.game.pick} чисел — "
                                            "больше закрепить нельзя.")
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
                "не выпадало" if s.draws_since is None else s.draws_since))

    def sort_table(self, col: str) -> None:
        key, rev = self._sort
        self._sort = (col, not rev if key == col else col != "num")
        self.fill_table()

    def fill_history(self, draws: list[core.Draw]) -> None:
        self.hist.delete(*self.hist.get_children())
        for d in reversed(draws[-300:]):
            self.hist.insert("", "end", values=(
                d.when.strftime("%d.%m.%Y"), "  ".join(f"{n:2d}" for n in d.numbers),
                d.bonus if d.bonus is not None else ""))

    def fill_honest(self) -> None:
        st, g = self.stats, self.game
        t = self.honest
        t.config(state="normal")
        t.delete("1.0", "end")
        if not st or not st.draws:
            t.config(state="disabled")
            return
        top = st.ranked()[:5]
        low = st.ranked(reverse=False)[:5]
        verdict = ("Такой разброс — обычное дело для честной случайной лотереи."
                   if st.p_value >= 0.05 else
                   "Разброс чуть больше обычного, но при множестве проверок такое "
                   "тоже случается случайно; на будущие тиражи это не влияет.")
        t.insert("end",
                 f"Шанс сорвать главный приз {g.title} одной линией из {g.pick} чисел: 1 к {format(g.odds(date.today()), ',').replace(',', ' ')}.\n"
                 + ("Сейчас в Lotto Max одна игра за 6 $ — это 4 линии, то есть шанс "
                    "на игру в 4 раза выше, чем на линию.\n" if g.key == "LOTTOMAX" else "")
                 + "Это не меняется от того, какие числа вы выберете.\n\n"
                 f"В выбранном периоде {len(st.draws)} тиражей. Каждое число в среднем "
                 f"должно было выпасть около {st.expected:.0f} раз.\n"
                 f"Чаще всех: " + ", ".join(f"{s.number} ({s.count})" for s in top) + "\n"
                 f"Реже всех: " + ", ".join(f"{s.number} ({s.count})" for s in low) + "\n\n"
                 f"Проверка «похоже ли это на чистую случайность» (хи-квадрат): "
                 f"вероятность получить такой разброс случайно ≈ {st.p_value:.0%}.\n"
                 f"{verdict}\n\n"
                 "Что это значит простыми словами: у шаров нет памяти. Частые числа "
                 "не «горячие», а редкие не «должны» выпасть. Генератор выбирает по "
                 "истории, потому что вам так нравится, — это нормально, но выигрыш "
                 "от этого не становится вероятнее.\n\n"
                 + (f"Дополнительные розыгрыши MaxMillions (1 000 000 $) и MaxPlus (от 100 000 $, с 14.04.2026) в базе: "
                    f"{len(self.extra_draws.get(g.key, []))}. Их можно учесть в частотах "
                    "через «Розыгрыши» вверху. "
                    if self.extra_draws.get(g.key) else
                    "У Lotto 6/49 миллионный розыгрыш (Gold Ball) разыгрывает номер "
                    "билета, а не шары, поэтому в частотах его нет. ")
                 + "Суммы джекпотов и число победителей в официальном файле не "
                 "публикуются, поэтому программа их не анализирует.\n\n"
                 "Один полезный приём: если все выбирают «популярные» числа (дни "
                 "рождения 1–31), при выигрыше приз делится на большее число людей. "
                 "Числа выше 31 выбирают реже.")
        t.config(state="disabled")

    # ------------------------------------------------------------ действия
    def on_generate(self) -> None:
        if not self.stats or not self.stats.draws:
            messagebox.showwarning(APP_TITLE, "Нет данных о тиражах.")
            return
        try:
            n = max(1, min(50, int(self.tickets_var.get())))
            tickets = core.generate(self.stats, self.strategy_var.get(), n,
                                    self.fixed, self.excluded, self.strength_var.get(),
                                    avoid=self.bought_combos(self.game.key),
                                    avoid_popular=self.avoid_popular_var.get())
        except (ValueError, tk.TclError) as e:
            messagebox.showwarning(APP_TITLE, str(e))
            return
        if not tickets:
            messagebox.showinfo(APP_TITLE, "Новых вариантов не нашлось — все подходящие "
                                "уже куплены. Снимите закрепления или смените способ.")
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
        for i, t in enumerate(self.generated):
            m = core.history_matches(all_d, t)
            hist = ", ".join(f"{k} из {g.pick}: {v} раз"
                             for k, v in sorted(m.items(), reverse=True))
            self.gen_tree.insert("", "end", iid=str(i), values=(
                "☑" if i in self.marked else "☐", i + 1,
                "  ".join(f"{x:2d}" for x in t), hist or "меньше 3 чисел всегда"))

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
            messagebox.showinfo(APP_TITLE, "Сначала щёлкните по купленным вариантам, "
                                "чтобы появилась галочка ☑.")
            return
        g = core.GAMES[self.generated_game]
        today = date.today()
        draw = core.next_draw(g, today)
        chosen = [self.generated[i] for i in sorted(self.marked)]
        try:
            added = data.add_tickets(g.key, chosen, today.isoformat(), draw.isoformat())
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Не удалось сохранить: {e}")
            return
        self.bought_info.set(f"Сохранено {added} билет(ов) на тираж {draw:%d.%m.%Y}. "
                             f"Они есть во вкладке «Мои билеты» и больше не "
                             f"будут предлагаться.")
        self.fill_my_tickets()
        if data.over_limit(data.load_tickets(), today):
            m = data.money_summary(data.load_tickets(), today)
            messagebox.showwarning(APP_TITLE, f"Лимит недели превышен: потрачено "
                                   f"{m['week']:.2f} $ при лимите {data.weekly_limit():g} $.")

    def fill_my_tickets(self) -> None:
        self.my_tree.delete(*self.my_tree.get_children())
        self._my_items = data.load_tickets()
        waiting = won = 0
        for i, t in reversed(list(enumerate(self._my_items))):
            g = core.GAMES.get(t.get("game"))
            if g is None:
                continue
            try:
                day = date.fromisoformat(t["draw"])
                bought = date.fromisoformat(t["bought"])
            except (KeyError, ValueError):
                continue
            r = core.check_ticket(g, t["numbers"], day, self.all_draws.get(g.key, []),
                                  self.extra_draws.get(g.key, []))
            waiting += not r.drawn
            won += bool(r.prize or r.maxmillions)
            self.my_tree.insert("", "end", iid=str(i), tags=("win",) if r.prize else (),
                                values=(g.title, f"{bought:%d.%m.%Y}", f"{day:%d.%m.%Y}",
                                        "  ".join(f"{x:2d}" for x in t["numbers"]),
                                        f"{data.ticket_cost(t):.2f}",
                                        f"{float(t['won']):.2f}" if t.get("won") else "",
                                        r.text(g)))
        self.my_summary.set(f"Всего билетов: {len(self._my_items)}   ·   ждут тиража: "
                            f"{waiting}   ·   с призом: {won}")
        m = data.money_summary(self._my_items, date.today())
        lim = data.weekly_limit()
        net = m["won"] - m["total"]
        self.money_var.set(
            f"Потрачено: эта неделя {m['week']:.2f} $"
            + (f" из {lim:g} $" if lim else "")
            + f" · этот месяц {m['month']:.2f} $ · всего {m['total']:.2f} $   |   "
            f"выиграно всего {m['won']:.2f} $   |   итог {net:+.2f} $")
        self.fill_board()

    def fill_board(self) -> None:
        """Последний тираж каждой игры и итог по моим билетам на него."""
        items = data.load_tickets()
        for g in core.GAMES.values():
            nums_v, mine_v = self.board_vars[g.key]
            mains = self.all_draws.get(g.key, [])
            if not mains:
                nums_v.set(f"{g.title}: нет данных")
                mine_v.set("")
                continue
            last = mains[-1]
            bonus = f"  бонус {last.bonus}" if last.bonus is not None else ""
            nums_v.set(f"{g.title:<10} {core.WEEKDAY_RU[last.when.weekday()][:2]} "
                       f"{last.when:%d.%m.%Y}:  "
                       + " ".join(f"{x:2d}" for x in last.numbers) + bonus)
            mine = [t for t in items if t.get("game") == g.key
                    and t.get("draw") == last.when.isoformat()]
            waiting = sum(1 for t in items if t.get("game") == g.key
                          and t.get("draw", "") > last.when.isoformat())
            if not mine:
                mine_v.set("ваших билетов на этот тираж нет"
                           + (f" · ждут следующего: {waiting}" if waiting else ""))
                continue
            res = [core.check_ticket(g, t["numbers"], last.when, mains,
                                     self.extra_draws.get(g.key, [])) for t in mine]
            best = max(r.matches for r in res)
            money = sum(1 for r in res if "денежный" in r.prize or r.prize == "ДЖЕКПОТ")
            free = sum(1 for r in res if r.prize == "бесплатный билет")
            mm = sum(r.maxmillions for r in res)
            text = (f"ваших билетов: {len(mine)} · лучший {best} из {g.pick} · "
                    f"денежных призов: {money} · бесплатных билетов: {free}")
            if mm:
                text += f" · MaxMillions/MaxPlus: {mm}!"
            if waiting:
                text += f" · ждут следующего: {waiting}"
            mine_v.set(text)

    # ----------------------------------------------- обновление программы
    def on_app_update(self, quiet: bool) -> None:
        """Проверяет новую версию на GitHub; ставит только с согласия."""
        bundle = upd.app_bundle()
        if bundle is None:
            if not quiet:
                messagebox.showinfo(APP_TITLE, "Программа запущена не из сборки — "
                                    "обновлять нечего.")
            return

        def work():
            try:
                info = upd.check()
                err = None
            except Exception as e:      # сеть, GitHub — сообщаем, не падаем
                info, err = None, e
            self.after(0, lambda: self._after_check(info, err, quiet, bundle))

        if not quiet:
            self.status_var.set("Проверяю новую версию программы на GitHub…")
        threading.Thread(target=work, daemon=True).start()

    def _after_check(self, info, err, quiet: bool, bundle) -> None:
        if err is not None:
            if not quiet:
                messagebox.showwarning(APP_TITLE, f"Не удалось проверить обновление: {err}")
            self.show_status()
            return
        if info is None:
            if not quiet:
                messagebox.showinfo(APP_TITLE, "У вас последняя версия программы.")
            self.show_status()
            return
        size = info["size"] / 1_000_000
        if not messagebox.askyesno(
                APP_TITLE, f"Есть новая версия программы ({size:.0f} МБ).\n\n"
                "Скачать и установить? Программа закроется и через несколько "
                "секунд откроется уже обновлённой. Ваши билеты и настройки "
                "сохранятся."):
            self.show_status()
            return
        self.status_var.set("Скачиваю новую версию… не закрывайте программу.")

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
            messagebox.showerror(APP_TITLE, f"Обновление не удалось: {err}\n"
                                 "Программа осталась прежней.")
            self.show_status()
            return
        upd.install_and_restart(new_app, bundle)
        self.destroy()

    def on_set_won(self) -> None:
        sel = self.my_tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Сначала выберите билет в таблице.")
            return
        item = self._my_items[int(sel[0])]
        amount = simpledialog.askfloat(
            APP_TITLE, "Сколько выиграл этот билет, $?\n(сумму смотрите на сайте лотереи; "
            "бесплатный билет — впишите 0 или его цену)", parent=self,
            minvalue=0, initialvalue=float(item.get("won", 0) or 0))
        if amount is None:
            return
        try:
            data.set_won(item, amount)
        except ValueError as e:
            messagebox.showerror(APP_TITLE, str(e))
        self.fill_my_tickets()

    def on_export(self) -> None:
        """Файл билетов для iPhone (тот же формат my_tickets.json)."""
        path = filedialog.asksaveasfilename(title="Сохранить билеты", defaultextension=".json",
                                            initialfile="my_tickets.json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
        import json
        Path(path).write_text(json.dumps(data.load_tickets(), ensure_ascii=False, indent=1),
                              encoding="utf-8")
        messagebox.showinfo(APP_TITLE, "Сохранено. Отправьте файл на iPhone (AirDrop) и "
                            "там нажмите «Загрузить файл» во вкладке «Мои».")

    def on_import_tickets(self) -> None:
        path = filedialog.askopenfilename(title="Билеты с другого устройства",
                                          filetypes=[("JSON", "*.json"), ("Все файлы", "*")])
        if not path:
            return
        import json
        try:
            n = data.import_tickets(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError) as e:
            messagebox.showerror(APP_TITLE, f"Не удалось прочитать файл: {e}")
            return
        self.fill_my_tickets()
        messagebox.showinfo(APP_TITLE, f"Добавлено билетов: {n}")

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
            messagebox.showinfo(APP_TITLE, "Сначала выберите билет в таблице.")
            return
        item = self._my_items[int(sel[0])]
        if messagebox.askyesno(APP_TITLE, "Удалить билет "
                               + " ".join(map(str, item["numbers"])) + "?"):
            data.remove_ticket(item)
            self.fill_my_tickets()

    def on_add_manual(self) -> None:
        win = tk.Toplevel(self)
        win.title("Добавить купленный билет")
        win.transient(self)
        frm = ttk.Frame(win, padding=14)
        frm.pack(fill="both", expand=True)
        game_v = tk.StringVar(value=self.game.title)
        ttk.Label(frm, text="Лотерея:").grid(row=0, column=0, sticky="w", pady=4)
        game_box = ttk.Combobox(frm, textvariable=game_v, state="readonly", width=14,
                                values=[x.title for x in core.GAMES.values()])
        game_box.grid(row=0, column=1, sticky="w")
        ttk.Label(frm, text="Числа через пробел:").grid(row=1, column=0, sticky="w", pady=4)
        nums_v = tk.StringVar()
        entry = ttk.Entry(frm, textvariable=nums_v, width=32, font=("Menlo", 16))
        entry.grid(row=1, column=1, sticky="w")
        ttk.Label(frm, text="Дата тиража (ДД.ММ.ГГГГ):").grid(row=2, column=0,
                                                              sticky="w", pady=4)
        draw_v = tk.StringVar()
        ttk.Entry(frm, textvariable=draw_v, width=14).grid(row=2, column=1, sticky="w")

        def game_of() -> core.Game:
            return next(x for x in core.GAMES.values() if x.title == game_v.get())

        def set_default_draw(*_):
            draw_v.set(f"{core.next_draw(game_of(), date.today()):%d.%m.%Y}")
        game_box.bind("<<ComboboxSelected>>", set_default_draw)
        set_default_draw()

        def add():
            g = game_of()
            try:
                day = datetime.strptime(draw_v.get().strip(), "%d.%m.%Y").date()
                nums = core.parse_numbers(nums_v.get(), g, day)
            except ValueError as e:
                msg = str(e) if "time data" not in str(e) else \
                    "Дата должна быть в виде ДД.ММ.ГГГГ, например 20.10.2026."
                messagebox.showwarning(APP_TITLE, msg, parent=win)
                return
            n = data.add_tickets(g.key, [nums], date.today().isoformat(), day.isoformat())
            self.fill_my_tickets()
            nums_v.set("")
            status.set("Добавлен." if n else "Такой билет на этот тираж уже есть.")
            entry.focus_set()

        ttk.Button(frm, text="Добавить", command=add).grid(row=3, column=1, sticky="w",
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
        return data.PROVINCES.get(self.province_var.get(),
                                  data.PROVINCES[data.DEFAULT_PROVINCE])

    def on_open_shop(self) -> None:
        """Открывает официальный сайт лотереи. Покупает человек сам."""
        if data.over_limit(data.load_tickets(), date.today()):
            m = data.money_summary(data.load_tickets(), date.today())
            if not messagebox.askyesno(
                    APP_TITLE, f"На этой неделе уже потрачено {m['week']:.2f} $ — это "
                    f"не меньше вашего лимита {data.weekly_limit():g} $.\n\n"
                    "Всё равно открыть сайт покупки?"):
                return
        if not self.generated:
            self.on_generate_10()
        self.on_copy()
        webbrowser.open(self.shop_url())
        self.status_var.set("Сайт открыт в браузере, варианты скопированы — "
                            "окно программы можно держать рядом и переписывать числа.")

    def on_copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append("\n".join(
            f"{i}. " + " ".join(map(str, t)) for i, t in enumerate(self.generated, 1)))

    # ------------------------------------------------------- обновление
    def show_status(self) -> None:
        last = data.last_update()
        today = date.today()
        nxt = core.next_draw(self.game, today)
        when = "сегодня" if nxt == today else \
            f"{core.WEEKDAY_RU[nxt.weekday()]} {nxt:%d.%m}"
        upd = f"{last:%d.%m %H:%M}" if last else "ещё не обновлялось"
        self.status_var.set(
            f"Автообновление: последнее {upd}, проверка каждые 3 часа. "
            f"Следующий тираж {self.game.title}: {when}, около 22:30 по Торонто.")

    def auto_update_tick(self) -> None:
        """Тихо обновляет данные, если с прошлого раза прошло 3 часа."""
        if not self._updating and data.needs_update(data.last_update(), datetime.now()):
            self.on_update(quiet=True)
        self.after(CHECK_EVERY_MS, self.auto_update_tick)

    def on_update(self, quiet: bool = False) -> None:
        if self._updating:
            return
        self._updating = True
        self.status_var.set("Проверяю новые тиражи в интернете…")
        old = {k: list(v) for k, v in self.all_draws.items()}

        def work():
            report = data.update_all()
            self.after(0, lambda: self._after_update(report, old, quiet))

        threading.Thread(target=work, daemon=True).start()

    def _after_update(self, report: dict[str, str], old: dict, quiet: bool) -> None:
        self._updating = False
        self.load_all_silent()
        fresh = []
        for g in core.GAMES.values():
            if old.get(g.key):
                for d in core.new_draws(old[g.key], self.all_draws.get(g.key, [])):
                    fresh.append(f"{g.title} {d.when:%d.%m.%Y}: "
                                 + "  ".join(map(str, d.numbers)))
        failed = [f"{k}: {v}" for k, v in report.items() if not v.startswith("обновлено")]
        if fresh:
            mine = self.draw_report(old)
            data.notify(APP_TITLE, mine or ("Вышел новый тираж: " + fresh[-1]))
            messagebox.showinfo(APP_TITLE, "Вышли новые тиражи:\n\n" + "\n".join(fresh)
                                + ("\n\n" + mine if mine else "")
                                + "\n\nВаши билеты сверены — см. вкладку «Мои билеты».")
        elif not quiet:
            messagebox.showinfo(APP_TITLE, "\n".join(f"{k}: {v}" for k, v in report.items()))
        if failed and quiet:
            self.status_var.set("Не удалось обновить (" + "; ".join(failed)
                                + "). Попробую снова через 10 минут.")

    def draw_report(self, old: dict) -> str:
        """Короткий итог по моим билетам на только что вышедшие тиражи."""
        items = data.load_tickets()
        parts = []
        for g in core.GAMES.values():
            mains = self.all_draws.get(g.key, [])
            for d in core.new_draws(old.get(g.key, []), mains):
                mine = [t for t in items if t.get("game") == g.key
                        and t.get("draw") == d.when.isoformat()]
                if not mine:
                    continue
                res = [core.check_ticket(g, t["numbers"], d.when, mains,
                                         self.extra_draws.get(g.key, [])) for t in mine]
                best = max(r.matches for r in res)
                prizes = sum(1 for r in res if r.prize or r.maxmillions)
                parts.append(f"{g.title} {d.when:%d.%m}: билетов {len(mine)}, "
                             f"лучший {best} из {g.pick}, с призом {prizes}")
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
            title=f"CSV с историей {self.game.title}",
            filetypes=[("CSV", "*.csv"), ("Все файлы", "*")])
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
            n = data.save_checked(self.game, text, data.user_dir())
        except Exception as e:
            messagebox.showerror(APP_TITLE, str(e))
            return
        self.load_all_silent()
        messagebox.showinfo(APP_TITLE, f"{self.game.title}: загружено {n} тиражей.")


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
            app.kind_var.set(kind)
            app.refresh()
            print(f"  {kind}: розыгрышей в выборке {len(app.stats.draws)}")
        app.kind_var.set("Только основные")
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
    assert all("ждёт тиража" in app.my_tree.set(r, "result")
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
    assert any(r.startswith("7 из 7") and "ДЖЕКПОТ" in r for r in results), results
    print("SELFTEST мои билеты:", app.my_summary.get())
    for r in app.my_tree.get_children():
        print("  ", app.my_tree.item(r)["values"])

    # Главная панель и самообновление.
    for key, (nums, mine) in app.board_vars.items():
        print("SELFTEST панель:", nums.get(), "|", mine.get())
        assert nums.get() and "нет данных" not in nums.get()
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
    assert "Потрачено" in app.money_var.get()
    app.avoid_popular_var.set(True)
    app.strategy_var.set("random")
    app.on_generate_10()
    assert not any(core.popular_reasons(t, core.LOTTO_MAX) for t in app.generated)

    if os.environ.get("LOTTO_SHOTS_DIR"):
        shots(app, Path(os.environ["LOTTO_SHOTS_DIR"]))

    opened = []
    webbrowser.open = opened.append       # браузер в самопроверке не открываем
    for prov in data.PROVINCES:
        app.province_var.set(prov)
        app.on_open_shop()
    assert opened == list(data.PROVINCES.values()), opened
    print("SELFTEST сайты:", opened)
    app.destroy()
    print("SELFTEST OK")


def shots(app: "App", folder: Path) -> None:
    """Снимки окна для проверки оформления (кладутся в folder при сборке)."""
    import subprocess
    import time
    folder.mkdir(parents=True, exist_ok=True)
    app.geometry("1400x870+0+30")
    nb = None
    for w in app.winfo_children():
        for c in w.winfo_children():
            if isinstance(c, ttk.Notebook):
                nb = c
    for idx, name in ((0, "1-gen"), (0, "1b-gen-bottom"), (1, "2-mine"), (4, "3-test"),
                      (5, "4-odds")):
        if nb is not None:
            nb.select(idx)
        app.gen_scroll.canvas.yview_moveto(1.0 if name == "1b-gen-bottom" else 0.0)
        app.lift()
        app.attributes("-topmost", True)
        for _ in range(10):
            app.update()
            time.sleep(0.1)
        try:
            subprocess.run(["screencapture", "-x", "-R0,0,1400,910",
                            str(folder / f"{name}.png")], timeout=20, check=True)
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
