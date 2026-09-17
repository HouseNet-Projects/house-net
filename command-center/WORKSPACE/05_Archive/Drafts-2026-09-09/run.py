# -*- coding: utf-8 -*-
"""Թարմացնում է ամեն ինչ՝ ռեեստրը և գրաֆիկը։
Գործարկվում է ԹԱՐՄԱՑՆԵԼ.bat-ից կամ՝  python run.py"""
import os, sys, runpy, datetime, io

ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(ROOT, "04_WhatsApp", "գործիքներ")
HY = ["երկուշաբթի","երեքշաբթի","չորեքշաբթի","հինգշաբթի","ուրբաթ","շաբաթ","կիրակի"]

def main():
    if not os.path.isdir(TOOLS):
        print("ՍԽԱԼ՝ գործիքների պանակը չգտնվեց՝", TOOLS); return 1
    sys.path.insert(0, TOOLS)
    os.chdir(os.path.join(ROOT, "04_WhatsApp"))
    today = datetime.date.today()

    print("═" * 62)
    print(f"  ԹԱՐՄԱՑՈՒՄ  ·  {today.strftime('%Y-%m-%d')}, {HY[today.weekday()]}")
    print("═" * 62)

    ok = True
    for script, label in (("կառուցել.py", "Ռեեստր"), ("գրաֆիկ.py", "Գրաֆիկ")):
        path = os.path.join(TOOLS, script)
        print(f"\n  {label} …")
        try:
            runpy.run_path(path, run_name="__main__")
        except PermissionError:
            print(f"  ⚠  Ֆայլը բաց է Excel-ում։ Փակիր և նորից գործարկիր։")
            ok = False
        except Exception as e:
            print(f"  ⚠  {type(e).__name__}: {e}")
            ok = False

    print("\n" + "═" * 62)
    print("  ՊԱՏՐԱՍՏ Է" if ok else "  ԱՎԱՐՏՎԵՑ ՍԽԱԼՆԵՐՈՎ — տես վերևում")
    print("═" * 62)
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
