# -*- coding: utf-8 -*-
"""ԳԱԴՈՒԿՅԱՆԻ_ՊԱՀԱՆՋՆԵՐԸ.xlsx — 2 թերթ։
  ԱՄՓՈՓ           — օրվա պատկերը, բացվում է առաջինը
  ԱՌԱՋԱԴՐԱՆՔՆԵՐ   — ամբողջ ցուցակը

⚠ 05_Archive/Drafts-2026-09-09/update.bat (legacy)-ը այս ֆայլը ՉԻ վերակառուցում։
Գործարկում՝  python .claude/tools/build_requirements_workbook.py
"""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "policy"))
import paths as _paths                                   # ONE business-root resolver
_BUSINESS_ROOT = _paths.root_name()
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule
from openpyxl.utils import get_column_letter as CL

from xlsx_style import *
from requirements_data import DEMANDS

TODAY = datetime.date.today()
ST_COLOR = {"Արված": GREEN, "Ընթացքում": AMBER,
            "Չսկսված": RED, "Պարզ չէ": SLATE}
ST_BG = {"Արված": GREEN_BG, "Ընթացքում": AMBER_BG,
         "Չսկսված": RED_BG, "Պարզ չէ": SLATE_BG}
ST_LIST = '"Արված,Ընթացքում,Չսկսված,Պարզ չէ"'

def is_open(st): return st != "Արված"

def when(d):
    if not d: return "—"
    n = (d - TODAY).days
    t = d.strftime("%m-%d")
    if n < 0:  return f"{t} · ուշացած"
    if n == 0: return f"{t} · ԱՅՍՕՐ"
    if n == 1: return f"{t} · ՎԱՂԸ"
    return f"{t} · {HY_SHORT[d.weekday()]}"

def urgency(d):
    if not d: return 9
    n = (d - TODAY).days
    return 0 if n < 0 else 1 if n == 0 else 2 if n == 1 else 3

wb = openpyxl.Workbook()

# ═════════════════════════ ԱՄՓՈՓ ═════════════════════════
s = wb.active; s.title = "ԱՄՓՈՓ"; s.sheet_properties.tabColor = RED
s.sheet_view.showGridLines = False
W = {"A": 2, "B": 2.4, "C": 15, "D": 17, "E": 17, "F": 17,
     "G": 17, "H": 17, "I": 15, "J": 21, "K": 2}
for k, v in W.items():
    s.column_dimensions[k].width = v
STRIPE, DATE_C, TITLE_A, TITLE_B, ST_C, BALL_C, LASTC = 2, 3, 4, 8, 9, 10, 10

def paint_s(r1, c1, r2, c2, color): paint(s, r1, c1, r2, c2, color)
paint_s(1, 1, 120, 11, PAPER)

s.row_dimensions[1].height = 38
put(s, 1, DATE_C, LASTC, "ՕՐՎԱ ՊԱՏԿԵՐ", size=19, bold=True, color=NAVY)
s.row_dimensions[2].height = 18
put(s, 2, DATE_C, LASTC,
    f"{TODAY.strftime('%Y-%m-%d')}, {HY[TODAY.weekday()]}   ·   "
    f"@P1-ի առաջադրանքները   ·   թվերը ինքնաշխատ են",
    size=9.5, color=MUTED)
paint_s(3, STRIPE, 3, LASTC, NAVY); s.row_dimensions[3].height = 3
s.row_dimensions[4].height = 14
r = 5

FIRST, LAST = 6, 6 + len(DEMANDS) - 1
STC = f"'ԱՌԱՋԱԴՐԱՆՔՆԵՐ'!$D${FIRST}:$D${LAST}"
DUE = f"'ԱՌԱՋԱԴՐԱՆՔՆԵՐ'!$F${FIRST}:$F${LAST}"

def tile(row, c1, c2, label, formula, color, bg):
    paint_s(row, c1, row + 2, c2, bg)
    outline(s, row, c1, row + 2, c2, color)
    s.row_dimensions[row].height = 9
    put(s, row + 1, c1, c2, formula, size=30, bold=True, color=color,
        align="center", h=42)
    put(s, row + 2, c1, c2, label, size=9, bold=True, color=color,
        align="center", h=22)

# չորս սյունակ՝ C-D · E-F · G-H · I-J
QUADS = [(3, 4), (5, 6), (7, 8), (9, 10)]
tile(r, *QUADS[0], "ԸՆԴԱՄԵՆԸ", f"=COUNTA({STC})", NAVY, "EAEEF3")
tile(r, *QUADS[1], "ԱՐՎԱԾ", f'=COUNTIF({STC},"Արված")', GREEN, GREEN_BG)
tile(r, *QUADS[2], "ԸՆԹԱՑՔՈՒՄ", f'=COUNTIF({STC},"Ընթացքում")', AMBER, AMBER_BG)
tile(r, *QUADS[3], "ՉՍԿՍՎԱԾ", f'=COUNTIF({STC},"Չսկսված")', RED, RED_BG)
r += 3; s.row_dimensions[r].height = 10; r += 1

tile(r, *QUADS[0], "ՈՒՇԱՑԱԾ",
     f'=SUMPRODUCT(({DUE}<>"")*({DUE}<TODAY())*({STC}<>"Արված"))', RED, RED_BG)
tile(r, *QUADS[1], "ԱՅՍՕՐ",
     f'=SUMPRODUCT(({DUE}=TODAY())*({STC}<>"Արված"))', AMBER, AMBER_BG)
tile(r, *QUADS[2], "ՎԱՂԸ",
     f'=SUMPRODUCT(({DUE}=TODAY()+1)*({STC}<>"Արված"))', AMBER, AMBER_BG)
tile(r, *QUADS[3], "ԱՎԵԼԻ ՈՒՇ",
     f'=SUMPRODUCT(({DUE}>TODAY()+1)*({STC}<>"Արված"))', BLUE, BLUE_BG)
r += 3; s.row_dimensions[r].height = 22; r += 1

def section(row, text, color, count):
    put(s, row, DATE_C, LASTC - 1, text, size=12, bold=True, color=color, h=26)
    put(s, row, LASTC, LASTC, str(count), size=12, bold=True, color=color,
        align="right")
    paint_s(row + 1, STRIPE, row + 1, LASTC, color)
    s.row_dimensions[row + 1].height = 2
    s.row_dimensions[row + 2].height = 8
    return row + 3

def line(row, n, what, st, due, ball, accent, plain=False):
    """Մեկ տող՝ ամսաթիվ | ինչ | կարգավիճակ | գնդակը"""
    paint_s(row, STRIPE, row, LASTC, CARD)
    paint_s(row, STRIPE, row, STRIPE, accent)
    outline(s, row, STRIPE, row, LASTC)
    lbl = (due.strftime("%m-%d") if due else "—") if plain else when(due)
    put(s, row, DATE_C, DATE_C, lbl, size=9, bold=True, color=accent)
    put(s, row, TITLE_A, TITLE_B, f"{n}.  {what}", size=10.5, color=INK)
    put(s, row, ST_C, ST_C, st, size=9, bold=True,
        color=ST_COLOR.get(st, MUTED), align="center")
    paint_s(row, ST_C, row, ST_C, ST_BG.get(st, "FFFFFF"))
    up = ball.isupper() and ball != "—"
    put(s, row, BALL_C, BALL_C, ball, size=9, bold=up,
        color=(RED if up else MUTED), align="right", h=30)
    s.row_dimensions[row + 1].height = 3
    return row + 2

opened = [d for d in DEMANDS if is_open(d[2])]
done = [d for d in DEMANDS if not is_open(d[2])]
GROUPS = [(0, "ՈՒՇԱՑԱԾ", RED), (1, "ԱՅՍՕՐ", RED),
          (2, "ՎԱՂԸ", AMBER), (3, "ԱՎԵԼԻ ՈՒՇ", BLUE),
          (9, "ԺԱՄԿԵՏ ՉԿԱ", SLATE)]
for key, label, color in GROUPS:
    grp = sorted([d for d in opened if urgency(d[4]) == key],
                 key=lambda d: (d[4] or datetime.date(2099, 1, 1), d[0]))
    if not grp: continue
    r = section(r, label, color, len(grp))
    for d in grp:
        r = line(r, d[0], d[1], d[2], d[4], d[6], color)
    s.row_dimensions[r].height = 12
    r += 1

if done:
    r = section(r, "ՓԱԿՎԱԾ", GREEN, len(done))
    for d in done:
        r = line(r, d[0], d[1], d[2], d[4], d[6], GREEN, plain=True)

r += 1
put(s, r, DATE_C, LASTC,
    "Կարմիրով գրված անունը նշանակում է՝ գնդակը իր մոտ է, ես սպասում եմ։",
    size=9, italic=True, color=MUTED, h=18)

# ═════════════════════════ ԱՌԱՋԱԴՐԱՆՔՆԵՐ ═════════════════════════
ws = wb.create_sheet("ԱՌԱՋԱԴՐԱՆՔՆԵՐ")
ws.sheet_properties.tabColor = NAVY
ws.sheet_view.showGridLines = False
ws.column_dimensions["A"].width = 2
ws.row_dimensions[1].height = 36
c = ws.cell(row=1, column=2, value="ԳԱԴՈՒԿՅԱՆԻ ԱՌԱՋԱԴՐԱՆՔՆԵՐԸ")
c.font = Font(name="Calibri", size=18, bold=True, color=NAVY)
ws.merge_cells("B1:H1")
ws.row_dimensions[2].height = 17
c = ws.cell(row=2, column=2,
            value=f"{TODAY.strftime('%Y-%m-%d')}, {HY[TODAY.weekday()]}   ·   "
                  f"{len(DEMANDS)} կետ, որից {len(opened)} բաց   ·   "
                  f"կարգավիճակն ու մեկնաբանությունը քոնն են   ·   "
                  f"ժամկետը լրացրել եմ ես՝ ըստ քո մեկնաբանության")
c.font = Font(name="Calibri", size=9, color=MUTED)
ws.merge_cells("B2:H2")
for col in range(2, 9):
    ws.cell(row=3, column=col).fill = PatternFill("solid", fgColor=NAVY)
ws.row_dimensions[3].height = 2.5
ws.row_dimensions[4].height = 10

COLS = [("№", 5), ("Ինչ է ուզում", 46), ("Կարգավիճակ", 13),
        ("Քո մեկնաբանությունը", 62), ("Ժամկետ", 13),
        ("Ում մոտ է գնդակը", 18), ("Ժամկետի հիմքը", 46)]
for j, (h, w) in enumerate(COLS, 2):
    c = ws.cell(row=5, column=j, value=h)
    c.fill = PatternFill("solid", fgColor=NAVY)
    c.font = Font(name="Calibri", color="FFFFFF", bold=True, size=9.5)
    c.alignment = Alignment(horizontal="center", vertical="center",
                            wrap_text=True)
    ws.column_dimensions[CL(j)].width = w
ws.row_dimensions[5].height = 32
ws.freeze_panes = "C6"

r = FIRST
for n, what, st, com, due, src, ball in DEMANDS:
    for j, v in enumerate([n, what, st, com, due, ball, src], 2):
        c = ws.cell(row=r, column=j, value=v)
        c.border = Border(bottom=side(), left=side(), right=side())
        c.alignment = Alignment(vertical="center", wrap_text=(j in (3, 5, 8)),
                                horizontal=("center" if j in (2, 4, 6)
                                            else "left"))
        up = ball.isupper() and ball != "—"
        c.font = Font(name="Calibri", size=9.5, bold=(j in (2, 4)),
                      italic=(j == 8),
                      color=(ST_COLOR.get(st, INK) if j == 4 else
                             RED if (j == 7 and up) else
                             MUTED if j == 8 else INK))
        if isinstance(v, datetime.date):
            c.number_format = "yyyy-mm-dd"
    ws.row_dimensions[r].height = 56 if com else 34
    r += 1

END = r - 1
dv = DataValidation(type="list", formula1=ST_LIST, allow_blank=True)
ws.add_data_validation(dv); dv.add(f"D{FIRST}:D{END}")
ws.conditional_formatting.add(f"F{FIRST}:F{END}", FormulaRule(
    formula=[f'AND($F{FIRST}<>"",$F{FIRST}<TODAY(),$D{FIRST}<>"Արված")'],
    fill=PatternFill("solid", fgColor=RED_BG), font=Font(color=RED, bold=True)))
ws.conditional_formatting.add(f"F{FIRST}:F{END}", FormulaRule(
    formula=[f'$F{FIRST}=TODAY()'],
    fill=PatternFill("solid", fgColor=AMBER_BG),
    font=Font(color=AMBER, bold=True)))

c = ws.cell(row=END + 2, column=2,
            value="Կետ 6-ը «Արված» է, բայց մեկնաբանությունը չորս նոր պայման "
                  "է դնում — հետևիր, որ չկորչեն։")
c.font = Font(name="Calibri", size=9, italic=True, color=MUTED)
ws.merge_cells(start_row=END + 2, start_column=2, end_row=END + 2, end_column=8)

wb.active = 0
out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), _BUSINESS_ROOT, "05_Archive",
                   f"@P1-requirements-{TODAY.strftime('%Y-%m-%d')}.xlsx")   # LEGACY output: superseded by Tasks.xlsx (05_Archive keeps history)
wb.save(out)
print(f"{os.path.basename(out)}  ·  {len(DEMANDS)} կետ  ·  "
      f"բաց՝ {len(opened)}  ·  փակված՝ {len(done)}")
