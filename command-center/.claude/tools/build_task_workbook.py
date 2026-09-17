# -*- coding: utf-8 -*-
"""Կառուցում է ԱՌԱՋԱԴՐԱՆՔՆԵՐ.xlsx-ը՝ 8 թերթ։
Գործարկում՝ 05_Archive/Drafts-2026-09-09/update.bat (legacy) կամ  python .claude/tools/build_task_workbook.py"""
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
from task_registry_data import IN, OUT, LOG, PEOPLE, QUESTIONS, TODAY

FAR = datetime.date(2099, 1, 1)
def is_open(x): return x["st"] in OPEN_ST
def key_date(x): return x.get("due") or x.get("nxt") or FAR

def bucket(x):
    if not is_open(x): return "փակ"
    d = key_date(x)
    if d is FAR: return "անժամկետ"
    n = (d - TODAY).days
    return "անց" if n < 0 else "այսօր" if n == 0 else "վաղը" if n == 1 else "առաջիկա"

ORDER = [("անց", "ԺԱՄԿԵՏԱՆՑ", RED), ("այսօր", "ԱՅՍՕՐ", AMBER),
         ("վաղը", "ՎԱՂԸ", AMBER), ("առաջիկա", "ԱՌԱՋԻԿԱ", BLUE),
         ("անժամկետ", "ԺԱՄԿԵՏ ՉԿԱ", MUTED), ("փակ", "ՓԱԿՎԱԾ", GREEN)]

wb = openpyxl.Workbook()
day = f"{TODAY.strftime('%Y-%m-%d')}, {HY[TODAY.weekday()]}"

# ══════════════════════ 1. ԱՄՓՈՓ ══════════════════════
d = wb.active; d.title = "ԱՄՓՈՓ"; d.sheet_properties.tabColor = RED
grid(d, stripe=False)
paint(d, 1, 1, 90, MARGIN_R, PAPER)
r = title_block(d, "ՕՐՎԱ ՊԱՏԿԵՐ",
                f"{day}   ·   թվերը ինքնաշխատ են՝ ՍՏԱՑՎԱԾ և ՏՐՎԱԾ թերթերից")

NI, NO = len(IN) + 1, len(OUT) + 1
SI, SO = "'ՍՏԱՑՎԱԾ'", "'ՏՐՎԱԾ'"
def f_in(cond):  return f"=SUMPRODUCT(({SI}!A2:A{NI}<>\"\")*{cond})"
OPEN_I = f'({SI}!J2:J{NI}<>"Կատարված")*({SI}!J2:J{NI}<>"Չեղարկված")'
OPEN_O = f'({SO}!I2:I{NO}<>"Կատարված")*({SO}!I2:I{NO}<>"Չեղարկված")'

def tile(row, c1, c2, label, formula, color, bg):
    paint(d, row, c1, row + 2, c2, bg)
    outline(d, row, c1, row + 2, c2, color)
    d.row_dimensions[row].height = 7
    put(d, row + 1, c1, c2, formula, size=24, bold=True, color=color,
        align="center", h=32)
    put(d, row + 2, c1, c2, label, size=8.5, bold=True, color=color,
        align="center", h=19)

q = half(4)
tile(r, *q[0], "ԺԱՄԿԵՏԱՆՑ",
     f_in(f'({SI}!H2:H{NI}<>"")*({SI}!H2:H{NI}<TODAY())*{OPEN_I}'), RED, RED_BG)
tile(r, *q[1], "ԱՅՍՕՐ",
     f_in(f'({SI}!H2:H{NI}=TODAY())*{OPEN_I}'), AMBER, AMBER_BG)
tile(r, *q[2], "ՎԱՂԸ",
     f_in(f'({SI}!H2:H{NI}=TODAY()+1)*{OPEN_I}'), AMBER, AMBER_BG)
tile(r, *q[3], "ԲԱՑ ԸՆԴԱՄԵՆԸ", f_in(OPEN_I), BLUE, BLUE_BG)
r += 3; d.row_dimensions[r].height = 8; r += 1

tile(r, *q[0], "ԵՍ ԵՄ ՍՊԱՍՈՒՄ",
     f"=SUMPRODUCT(({SO}!A2:A{NO}<>\"\")*{OPEN_O})", SLATE, SLATE_BG)
tile(r, *q[1], "ԱՅՍՕՐ ՍՏՈՒԳԵԼՈՒ",
     f"=SUMPRODUCT(({SO}!K2:K{NO}<>\"\")*({SO}!K2:K{NO}<=TODAY())*{OPEN_O})",
     SLATE, SLATE_BG)
tile(r, *q[2], "ՓԱԿՎԱԾ",
     f'=COUNTIF({SI}!J2:J{NI},"Կատարված")', GREEN, GREEN_BG)
tile(r, *q[3], "ԲԱՑ ՀԱՐՑ",
     f"=COUNTIF('ՀԱՐՑԵՐ'!E2:E20,\"Բաց\")", MUTED, SLATE_BG)
r += 3; d.row_dimensions[r].height = 16; r += 1

# ── երկու սիմետրիկ վահանակ ──
L, R = half(2)
today_i = sorted([x for x in IN if is_open(x) and x["due"]
                  and (x["due"] - TODAY).days <= 0], key=lambda x: x["due"])
tom_i = sorted([x for x in IN if is_open(x)
                and x["due"] == TODAY + datetime.timedelta(days=1)],
               key=lambda x: x["id"])

put(d, r, L[0], L[1], f"ԱՅՍՕՐ ԵՎ ԺԱՄԿԵՏԱՆՑ  ·  {len(today_i)}",
    size=11, bold=True, color=RED, h=24)
put(d, r, R[0], R[1], f"ՎԱՂԸ  ·  {len(tom_i)}", size=11, bold=True,
    color=AMBER, h=24)
paint(d, r + 1, L[0], r + 1, L[1], RED)
paint(d, r + 1, R[0], r + 1, R[1], AMBER)
d.row_dimensions[r + 1].height = 1.5
d.row_dimensions[r + 2].height = 5
r += 3

def mini(ws, row, c1, c2, x, color):
    paint(ws, row, c1, row + 1, c2, CARD)
    outline(ws, row, c1, row + 1, c2)
    put(ws, row, c1, c1, x["id"][-5:], size=8, bold=True, color=FAINT)
    put(ws, row, c1 + 1, c2, date_badge(x["due"], x["st"], TODAY,
        x.get("due_t", ""))[0], size=8, bold=True, color=color, align="right")
    ws.row_dimensions[row].height = 13
    put(ws, row + 1, c1, c2, x["task"], size=9.5, bold=True, color=INK,
        wrap=True, h=28)

for i in range(max(len(today_i), len(tom_i))):
    if i < len(today_i): mini(d, r, L[0], L[1], today_i[i], RED)
    if i < len(tom_i):   mini(d, r, R[0], R[1], tom_i[i], AMBER)
    r += 2
    d.row_dimensions[r].height = 4
    r += 1

d.row_dimensions[r].height = 10; r += 1
waiting = sorted([x for x in OUT if is_open(x)], key=lambda x: key_date(x))
r = section(d, r, "ՍՊԱՍՈՒՄ ԵՄ ՈՒՐԻՇԻՑ", SLATE, f"{len(waiting)}")
for x in waiting:
    paint(d, r, C_FIRST, r, C_LAST, CARD); outline(d, r, C_FIRST, r, C_LAST)
    put(d, r, C_FIRST, C_FIRST, x["to"], size=9, bold=True, color=INK)
    put(d, r, C_FIRST + 1, C_LAST - 2, x["task"], size=9, color=INK, wrap=True)
    b = date_badge(key_date(x) if key_date(x) is not FAR else None,
                   x["st"], TODAY, x.get("due_t", ""))
    put(d, r, C_LAST - 1, C_LAST, b[0], size=8, bold=True, color=b[1],
        align="right", h=24)
    r += 1

# ══════════════════════ 2. ՕՐՎԱ ՊԼԱՆ ══════════════════════
p = wb.create_sheet("ՕՐՎԱ ՊԼԱՆ"); p.sheet_properties.tabColor = AMBER
grid(p, stripe=False)
paint(p, 1, 1, 120, MARGIN_R, PAPER)
r = title_block(p, "ՕՐՎԱ ՊԼԱՆ",
                f"{day}   ·   տպելու համար պատրաստ   ·   վերևից ներքև՝ ըստ հրատապության")

def checkline(ws, row, n, x, color, extra):
    paint(ws, row, C_FIRST, row + 1, C_LAST, CARD)
    outline(ws, row, C_FIRST, row + 1, C_LAST)
    put(ws, row, C_FIRST, C_FIRST, f"☐  {n}", size=11, bold=True, color=color)
    put(ws, row, C_FIRST + 1, C_LAST - 2, x["task"], size=10.5, bold=True,
        color=INK, wrap=True)
    b = date_badge(x.get("due"), x["st"], TODAY, x.get("due_t", ""))
    put(ws, row, C_LAST - 1, C_LAST, b[0], size=8, bold=True, color=b[1],
        align="right", h=30)
    put(ws, row + 1, C_FIRST, C_FIRST, x["id"][-5:], size=8, color=FAINT)
    put(ws, row + 1, C_FIRST + 1, C_LAST, extra, size=9, color=BLUE,
        wrap=True, h=22)
    return row + 2

n = 0
for key, label, color in [("անց", "ՆԱԽ ՍՐԱՆՔ — ԺԱՄԿԵՏԸ ԱՆՑԵԼ Է", RED),
                          ("այսօր", "ԱՅՍՕՐ", AMBER)]:
    grp = sorted([x for x in IN if bucket(x) == key], key=lambda x: x["due"])
    if not grp: continue
    r = section(p, r, label, color, f"{len(grp)}")
    for x in grp:
        n += 1
        r = checkline(p, r, n, x, color, "→  " + (x["next"] or "—"))
        p.row_dimensions[r].height = 4; r += 1

chk = sorted([x for x in OUT if is_open(x) and x["nxt"] and x["nxt"] <= TODAY],
             key=lambda x: x["nxt"])
if chk:
    r = section(p, r, "ԱՅՍՕՐ ՍՏՈՒԳԵԼՈՒ ՈՒՐԻՇԻՑ", SLATE, f"{len(chk)}")
    for x in chk:
        n += 1
        r = checkline(p, r, n, x, SLATE, f"→  {x['to']} · {x['ch']}"
                      + (f" · {x['btx']}" if x["btx"] else ""))
        p.row_dimensions[r].height = 4; r += 1

r += 1
put(p, r, C_FIRST, C_LAST, f"Ընդամենը այսօրվա համար՝ {n} կետ։", size=9,
    italic=True, color=MUTED, h=18)

# ══════════════════════ 3. ՔԱՐՏԵՐ ══════════════════════
c = wb.create_sheet("ՔԱՐՏԵՐ"); c.sheet_properties.tabColor = NAVY
grid(c)
paint(c, 1, 1, 460, MARGIN_R, PAPER)
r = title_block(c, "ԱՌԱՋԱԴՐԱՆՔՆԵՐԻ ՏԱԽՏԱԿ",
    f"{day}   ·   ձախ շերտը՝ առաջնահերթություն   ·   կապույտ տողը՝ հաջորդ քայլ")

def card(ws, row, *, stripe, ident, status, badge, title, meta, quote,
         sol, nxt, foot, dim=False):
    body = MUTED if dim else INK
    paint(ws, row, STRIPE, row + 6, C_LAST, CARD)
    paint(ws, row, STRIPE, row + 6, STRIPE, stripe)
    ws.merge_cells(start_row=row, start_column=STRIPE,
                   end_row=row + 6, end_column=STRIPE)
    outline(ws, row, STRIPE, row + 6, C_LAST)
    a, b_, cc = C_FIRST, C_FIRST + 3, C_FIRST + 5
    put(ws, row, a, b_ - 1, ident, size=9, bold=True, color=FAINT, h=19)
    sc, sbg = ST.get(status, (MUTED, SLATE_BG))
    put(ws, row, b_, cc - 1, status.upper(), size=8.5, bold=True,
        color=sc, align="center")
    paint(ws, row, b_, row, cc - 1, sbg)
    put(ws, row, cc, C_LAST, badge[0], size=8.5, bold=True, color=badge[1],
        align="right")
    put(ws, row+1, C_FIRST, C_LAST, title, size=11.5, bold=True,
        color=body, wrap=True, h=34)
    put(ws, row+2, C_FIRST, C_LAST, meta, size=8.5, color=MUTED, h=15)
    put(ws, row+3, C_FIRST, C_LAST, quote, size=8.5, italic=True,
        color=MUTED, wrap=True, h=30)
    put(ws, row+4, C_FIRST, C_LAST, sol, size=9, color=body, wrap=True, h=22)
    put(ws, row+5, C_FIRST, C_LAST, nxt, size=9, bold=True,
        color=(FAINT if dim else BLUE), wrap=True, h=22)
    put(ws, row+6, C_FIRST, C_LAST, foot, size=8, color=FAINT, h=16)
    ws.row_dimensions[row + 7].height = 8
    return row + 8

def foot_in(x):
    bits = []
    bits.append("Ժամկետը՝ " + x["src"])
    if x["dep"]: bits.append("Կախված է՝ " + x["dep"])
    if x["btx"]: bits.append(x["btx"])
    if x["note"]: bits.append(x["note"])
    return "   ·   ".join(bits) if bits else "—"

put(c, r, C_FIRST, C_LAST, "ՍՏԱՑՎԱԾ — ինչ է ինձնից սպասվում",
    size=11, bold=True, color=INK, h=24); r += 2
for key, label, color in ORDER:
    grp = sorted([x for x in IN if bucket(x) == key], key=lambda x: key_date(x))
    if not grp: continue
    r = section(c, r, label, color, f"{len(grp)}")
    for x in grp:
        r = card(c, r, stripe=PRI.get(x["pri"], FAINT), ident=x["id"],
            status=x["st"],
            badge=date_badge(x["due"], x["st"], TODAY, x["due_t"]),
            title=x["task"],
            meta=f"Ումից՝ {x['frm']}   ·   {x['got'].strftime('%m-%d')} {x['t']}"
                 f"   ·   {x['ch']}   ·   պատասխանատու՝ {x['who']}"
                 f"   ·   {x['pri']}",
            quote=x["raw"],
            sol="Լուծում՝ " + (x["sol"] or x["res"] or "—"),
            nxt="→  " + (x["next"] or "—"),
            foot=foot_in(x), dim=not is_open(x))
    r += 1

r += 1
put(c, r, C_FIRST, C_LAST, "ՏՐՎԱԾ — ինչ եմ ես հանձնարարել",
    size=11, bold=True, color=INK, h=26); r += 2
for key, label, color in ORDER:
    grp = sorted([x for x in OUT if bucket(x) == key], key=lambda x: key_date(x))
    if not grp: continue
    r = section(c, r, label, color, f"{len(grp)}")
    for x in grp:
        r = card(c, r, stripe=PRI.get(x["pri"], FAINT), ident=x["id"],
            status=x["st"],
            badge=date_badge(x["due"] or x["nxt"], x["st"], TODAY, x["due_t"]),
            title=x["task"],
            meta=f"Ում՝ {x['to']}   ·   տրվել՝ {x['got'].strftime('%m-%d')}"
                 f"   ·   {x['ch']}   ·   վերջին ստուգում՝ "
                 f"{x['last'].strftime('%m-%d') if x['last'] else '—'}"
                 f"   ·   {x['pri']}",
            quote="Ինչի համար՝ " + x["why"],
            sol="Ստացվածը՝ " + (x["res"] or "դեռ ոչինչ"),
            nxt="→  Հաջորդ ստուգում՝ "
                + (x["nxt"].strftime("%m-%d") if x["nxt"] else "նշված չէ"),
            foot=(x["btx"] + "   ·   " if x["btx"] else "") + (x["note"] or "—"),
            dim=not is_open(x))
    r += 1

# ══════════════════════ 4-5. ՏՎՅԱԼՆԵՐԻ ԹԵՐԹԵՐ ══════════════════════
def datasheet(name, cols, rows, tab, status_col, pri_col, due_col):
    ws = wb.create_sheet(name); ws.sheet_properties.tabColor = tab
    header_row(ws, 1, cols)
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{CL(len(cols))}{len(rows) + 1}"
    for i, row in enumerate(rows, 2):
        for j, v in enumerate(row, 1):
            cell = ws.cell(row=i, column=j, value=v)
            cell.font = Font(name="Calibri", size=9.5)
            cell.border = Border(bottom=side())
            cell.alignment = Alignment(vertical="top",
                                       wrap_text=cols[j-1][1] > 20)
            if isinstance(v, datetime.date): cell.number_format = "yyyy-mm-dd"
        ws.row_dimensions[i].height = 46
    for col, formula in ((status_col, STATUSES), (pri_col, PRIORITIES)):
        dv = DataValidation(type="list", formula1=formula, allow_blank=True)
        ws.add_data_validation(dv); dv.add(f"{col}2:{col}400")
    rng = f"A2:{CL(len(cols))}400"
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'AND(${due_col}2<>"",${due_col}2<TODAY(),'
                 f'${status_col}2<>"Կատարված",${status_col}2<>"Չեղարկված")'],
        fill=PatternFill("solid", fgColor=RED_BG),
        font=Font(color=RED, size=9.5)))
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'AND(${due_col}2=TODAY(),${status_col}2<>"Կատարված")'],
        fill=PatternFill("solid", fgColor=AMBER_BG)))
    ws.conditional_formatting.add(rng, FormulaRule(
        formula=[f'OR(${status_col}2="Կատարված",${status_col}2="Չեղարկված")'],
        fill=PatternFill("solid", fgColor=SLATE_BG),
        font=Font(color=MUTED, size=9.5)))
    return ws

datasheet("ՍՏԱՑՎԱԾ",
    [("ID",16),("Ստացվել է",11),("Ժամ",7),("Ումից",13),("Ալիք",11),
     ("Առաջադրանք",40),("Բնօրինակ տեքստ",44),("Վերջնաժամկետ",12),
     ("Առաջնահերթ.",11),("Կարգավիճակ",12),("Պատասխանատու",14),
     ("Կախված է",18),("Լուծում",36),("Հաջորդ քայլ",36),("Արդյունք",24),
     ("Bitrix24",16),("Փակվել է",11),("Ժամկետի աղբյուր",20),("Նշում",38)],
    [[x["id"],x["got"],x["t"],x["frm"],x["ch"],x["task"],x["raw"],x["due"],
      x["pri"],x["st"],x["who"],x["dep"],x["sol"],x["next"],x["res"],
      x["btx"],x["closed"],x["src"],x["note"]] for x in IN],
    BLUE, "J", "I", "H")

datasheet("ՏՐՎԱԾ",
    [("ID",16),("Տրվել է",11),("Ում եմ տվել",15),("Ալիք",11),
     ("Առաջադրանք",40),("Ինչի համար",30),("Վերջնաժամկետ",12),
     ("Առաջնահերթ.",11),("Կարգավիճակ",12),("Վերջին ստուգում",13),
     ("Հաջորդ ստուգում",13),("Ստացվածը",28),("Bitrix24",18),
     ("Փակվել է",11),("Ժամկետի աղբյուր",20),("Նշում",34)],
    [[x["id"],x["got"],x["to"],x["ch"],x["task"],x["why"],x["due"],
      x["pri"],x["st"],x["last"],x["nxt"],x["res"],x["btx"],
      x["closed"],x["src"],x["note"]] for x in OUT],
    AMBER, "I", "H", "G")

# ══════════════════════ 6. ԳՐԱՆՑԱՄԱՏՅԱՆ ══════════════════════
lg = wb.create_sheet("ԳՐԱՆՑԱՄԱՏՅԱՆ"); lg.sheet_properties.tabColor = GREEN
header_row(lg, 1, [("Ամսաթիվ",12),("Առաջադրանք",16),("Ինչ արվեց",48),
                   ("Ում հետ",16),("Արդյունք",32),("Հաջորդ քայլ",32)])
lg.freeze_panes = "A2"
for i, e in enumerate(sorted(LOG, key=lambda z: z["d"], reverse=True), 2):
    for j, v in enumerate([e["d"],e["tid"],e["what"],e["who"],e["res"],e["nxt"]], 1):
        cell = lg.cell(row=i, column=j, value=v)
        cell.font = Font(name="Calibri", size=9.5)
        cell.border = Border(bottom=side())
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        if isinstance(v, datetime.date): cell.number_format = "yyyy-mm-dd"
    lg.row_dimensions[i].height = 30
lg.auto_filter.ref = f"A1:F{len(LOG) + 1}"

# ══════════════════════ 7. ԱՆՁԻՆՔ ══════════════════════
pp = wb.create_sheet("ԱՆՁԻՆՔ"); pp.sheet_properties.tabColor = SLATE
header_row(pp, 1, [("Անուն",18),("Դեր / պաշտոն",34),("Ալիք",22),
                   ("Բաց հանձնարարական",20),("Նշում",56)])
pp.freeze_panes = "A2"
for i, x in enumerate(PEOPLE, 2):
    cnt = sum(1 for o in OUT if o["to"] == x["name"] and is_open(o))
    for j, v in enumerate([x["name"], x["role"], x["ch"], cnt, x["note"]], 1):
        cell = pp.cell(row=i, column=j, value=v)
        cell.font = Font(name="Calibri", size=9.5,
                         bold=(j == 1),
                         color=(RED if j == 2 and "ՊԱՐԶԵԼՈՒ" in str(v) else INK))
        cell.border = Border(bottom=side())
        cell.alignment = Alignment(vertical="center", wrap_text=(j == 5),
                                   horizontal="center" if j == 4 else "left")
    pp.row_dimensions[i].height = 30

# ══════════════════════ 8. ՀԱՐՑԵՐ ══════════════════════
qq = wb.create_sheet("ՀԱՐՑԵՐ"); qq.sheet_properties.tabColor = RED
header_row(qq, 1, [("Հարցը",56),("Ո՞վ է պատասխանում",20),
                   ("Ինչու է կարևոր",44),("Կապված ID",18),("Վիճակ",16)])
qq.freeze_panes = "A2"
for i, x in enumerate(QUESTIONS, 2):
    for j, v in enumerate([x["q"], x["who"], x["why"], x["tid"], x["st"]], 1):
        cell = qq.cell(row=i, column=j, value=v)
        cell.font = Font(name="Calibri", size=9.5, bold=(j == 1),
                         color=(RED if j == 5 and v == "Բաց" else INK))
        cell.border = Border(bottom=side())
        cell.alignment = Alignment(vertical="center", wrap_text=(j in (1, 3)),
                                   horizontal="center" if j == 5 else "left")
    qq.row_dimensions[i].height = 34

wb.active = 0
out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), _BUSINESS_ROOT, "05_Archive", f"Task-workbook-8-sheet-{TODAY.strftime('%Y-%m-%d')}.xlsx")   # LEGACY: Tasks.xlsx is the canonical register
wb.save(out)
print(f"ԱՌԱՋԱԴՐԱՆՔՆԵՐ.xlsx  ·  {len(IN)} ստացված  ·  {len(OUT)} տրված  "
      f"·  {len(LOG)} գրառում  ·  {len(QUESTIONS)} բաց հարց")
