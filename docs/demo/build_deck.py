"""Build the 7 slide demo deck (space theme, one GIF + walkthrough steps per slide).

usage: python3 build_deck.py out.pptx [--only N]   (needs python-pptx)
GIFs (s1.gif to s7.gif) and bg.png are read from the folder this script is in.
"""
import os
import re
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = HERE

WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BODY = RGBColor(0xC9, 0xD6, 0xEE)
MUTED = RGBColor(0x8F, 0xA3, 0xC8)
BLUE = RGBColor(0x7F, 0xB4, 0xFF)
AMBER = RGBColor(0xFF, 0xB5, 0x47)
GREEN = RGBColor(0x5F, 0xD6, 0xA4)
CORAL = RGBColor(0xFF, 0x7A, 0x7A)
PANEL = RGBColor(0x0A, 0x12, 0x2E)
EDGE = RGBColor(0x34, 0x58, 0xA0)
COLORS = {"g": GREEN, "a": AMBER, "r": CORAL, "b": BLUE, "w": WHITE}

SLIDES = [
    {
        "title": "Will it burn in a Moon base?",
        "lede": "NASA's burn tests never reached the oxygen level a Moon base is expected to use.",
        "gif": "s1.gif",
        "typed": False,
        "steps": [
            "A Moon base is expected to run at about <a>30% oxygen or more</a>.",
            "NASA's burn tests flew in orbit, in <w>microgravity</w> (near weightlessness). <w>None were on the Moon.</w>",
            "The Moon is a map. Each dot is a material NASA tested, and you can drag it to spin.",
            "Our question: <a>did any test ever reach 30%?</a>",
        ],
        "notes": "A Moon base will likely run at 30 percent oxygen or more. NASA's burn tests flew in orbit. Did any of them reach that level? This site answers that, and shows exactly where the evidence stops.",
    },
    {
        "title": "Ask a question, get an answer with its evidence",
        "lede": "Typed in plain words. The answer comes from code and the test data, never from an AI.",
        "gif": "s2.gif",
        "typed": True,
        "steps": [
            "We type: <w>Will PMMA burn at 30% oxygen?</w> PMMA is a clear plastic NASA uses as a standard test fuel.",
            "The verdict is <r>BEYOND</r>: NASA never tested PMMA that high. It does <w>not</w> say PMMA will or will not burn.",
            "The three closest real tests are listed, all at 22.2% oxygen. <w>Quenched</w> means the flame went out on its own.",
            "A check confirms <g>every number</g> in the answer is in the data.",
        ],
        "notes": "We type a question. The answer is BEYOND, which means nobody tested PMMA that high. The closest tests are shown, and every number is checked against the data.",
    },
    {
        "title": "What INSIDE, NEAR and BEYOND mean",
        "lede": "Three questions about PMMA, from a level that was tested to one that never was.",
        "gif": "s3.gif",
        "typed": True,
        "steps": [
            "<g>INSIDE</g> (20% oxygen): within what was tested. Real tests exist there.",
            "<a>NEAR</a> (23% oxygen): just outside the tested range, within 1.0 oxygen point. The tests are close.",
            "<r>BEYOND</r> (30% oxygen): outside everything tested, so no test can say what happens.",
            "The highest PMMA test was <w>22.2% oxygen</w>.",
        ],
        "notes": "Three typed questions. At 20 percent we are inside the tested range. At 23 we are just outside, so near. At 30 we are beyond anything tested.",
    },
    {
        "title": "The evidence chart: where NASA's tests stop",
        "lede": "One row per material. One tick per real NASA test, colored by how it ended.",
        "gif": "s4.gif",
        "typed": False,
        "steps": [
            "Each <w>row</w> is a material. Each <w>tick</w> is one real test.",
            "Hover a row to see its test count and outcomes. <w>PMMA has 102 tests</w> and its last tick is at 22.2%.",
            "The shaded band on the right is the <a>30% Moon base</a> level.",
            "<r>No test is in the band.</r> The best low pressure test stops at 26.2%.",
        ],
        "notes": "Every tick is a real NASA test. All of them stop before the shaded Moon base band. That empty band is the main finding.",
    },
    {
        "title": "Materials, and how each test ended",
        "lede": "Click a material on the Moon to open its card.",
        "gif": "s5.gif",
        "typed": False,
        "steps": [
            "<w>PMMA</w>: 102 tests, 76 with a known outcome, 13.6 to 22.2% oxygen, airflow 0 to 20 cm/s.",
            "<w>SIBAL</w> (a cotton and fiberglass fabric): 32 tests. Nomex, silicone and wax have only 4, 4 and 1.",
            "<w>Quenched</w>: the flame went out on its own. <w>Blow off</w>: the airflow pushed it off. <w>No ignition</w>: it never lit.",
            "If the notes do not say how a test ended, we write <w>unknown</w>. We never guess.",
        ],
        "notes": "Each material has a card with its tests, outcomes and oxygen range. The outcome words are read from NASA's crew notes.",
    },
    {
        "title": "The closest evidence to a Moon base",
        "lede": "Cotton at 26% oxygen has no normal pressure test, so the site shows the one low pressure test.",
        "gif": "s6.gif",
        "typed": True,
        "steps": [
            "We type: <w>Will cotton burn at 26% oxygen?</w>",
            "<r>BEYOND</r> again. No cotton test at normal pressure exists. The only one is <w>Saffire V, test V-2</w>.",
            "Saffire V flew in a cargo spacecraft at low pressure (70.7 kPa). At <a>26.2% oxygen</a> the cotton kept burning.",
            "It is the closest NASA data to 30%, shown <w>separately</w> from the normal pressure tests.",
        ],
        "notes": "Cotton at 26 percent is also beyond the normal tests. The one low pressure Saffire V test is the closest evidence, and it is shown on its own.",
    },
    {
        "title": "Ranking, limits and honesty",
        "lede": "Which of NASA's 24 combustion experiments matter most for fire safety in a habitat.",
        "gif": "s7.gif",
        "typed": False,
        "steps": [
            "We rank all 24 experiments. <w>BASS-II is first</w>, with a reason for every point. The ranking is <a>our judgment, not NASA's</a>.",
            "<w>Open details</w> shows an experiment's objective, fuels, conditions and sensors.",
            "The <w>Limits and rules</w> panel lists every threshold the site uses.",
            "<r>All tests were in microgravity.</r> The Moon has about one sixth of Earth's gravity.",
        ],
        "notes": "We rank the 24 NASA experiments and show the reason for every point. The limits panel lists every rule. Every test was in microgravity, which is not the Moon's gravity.",
    },
]

TOKEN = re.compile(r"<([gabrw])>(.*?)</\1>")


def add_runs(par, text, size, base_color):
    pos = 0
    for m in TOKEN.finditer(text):
        if m.start() > pos:
            r = par.add_run()
            r.text = text[pos:m.start()]
            style(r, size, base_color)
        r = par.add_run()
        r.text = m.group(2)
        style(r, size, COLORS[m.group(1)], bold=True)
        pos = m.end()
    if pos < len(text):
        r = par.add_run()
        r.text = text[pos:]
        style(r, size, base_color)


def style(run, size, color, bold=False, font="Arial"):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = font
    run.font.color.rgb = color


def textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    return tb, tf


def build(only=None, out="deck.pptx"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    total = len(SLIDES)
    for idx, s in enumerate(SLIDES, 1):
        if only and idx != only:
            continue
        sl = prs.slides.add_slide(blank)
        sl.shapes.add_picture(os.path.join(HERE, "bg.png"), 0, 0, prs.slide_width, prs.slide_height)

        _, tf = textbox(sl, 0.6, 0.38, 9, 0.3)
        r = tf.paragraphs[0].add_run()
        r.text = f"FLAME IN FREEFALL   /   {idx} OF {total}"
        style(r, 11, BLUE, font="Courier New")

        _, tf = textbox(sl, 0.6, 0.72, 12.1, 0.8, MSO_ANCHOR.MIDDLE)
        r = tf.paragraphs[0].add_run()
        r.text = s["title"]
        style(r, 34, WHITE, bold=True)

        _, tf = textbox(sl, 0.6, 1.5, 12.1, 0.4)
        r = tf.paragraphs[0].add_run()
        r.text = s["lede"]
        style(r, 15, MUTED)

        # GIF frame and picture (GIF is 960x549).
        fx, fy, fw = 0.6, 2.1, 7.75
        pw = fw - 0.14
        ph = pw * 549 / 960
        fh = ph + 0.14
        frame = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(fx), Inches(fy), Inches(fw), Inches(fh))
        frame.adjustments[0] = 0.015
        frame.fill.solid()
        frame.fill.fore_color.rgb = PANEL
        frame.line.color.rgb = EDGE
        frame.line.width = Pt(1.5)
        frame.shadow.inherit = False
        pic = sl.shapes.add_picture(os.path.join(DEMO, s["gif"]), Inches(fx + 0.07), Inches(fy + 0.07), Inches(pw), Inches(ph))
        pic._element.nvPicPr.cNvPr.set("descr", f"Screen recording for slide {idx}: {s['title']}")

        _, tf = textbox(sl, fx, fy + fh + 0.1, fw, 0.3)
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = "Live recording of the real site" + ("  /  questions typed live" if s["typed"] else "")
        style(r, 11, MUTED, font="Courier New")

        # Walkthrough steps.
        _, tf = textbox(sl, 8.8, 2.1, 4.0, 0.3)
        r = tf.paragraphs[0].add_run()
        r.text = "WHAT YOU ARE SEEING"
        style(r, 11, AMBER, bold=True, font="Courier New")

        y = 2.55
        step_h = (fh - 0.45) / len(s["steps"])
        for n, text in enumerate(s["steps"], 1):
            dot = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(8.8), Inches(y + 0.02), Inches(0.36), Inches(0.36))
            dot.fill.solid()
            dot.fill.fore_color.rgb = RGBColor(0x14, 0x2A, 0x5C)
            dot.line.color.rgb = BLUE
            dot.line.width = Pt(1.25)
            dot.shadow.inherit = False
            dtf = dot.text_frame
            dtf.margin_left = dtf.margin_right = dtf.margin_top = dtf.margin_bottom = 0
            dtf.vertical_anchor = MSO_ANCHOR.MIDDLE
            dp = dtf.paragraphs[0]
            dp.alignment = PP_ALIGN.CENTER
            dr = dp.add_run()
            dr.text = str(n)
            style(dr, 12, WHITE, bold=True)
            _, ttf = textbox(sl, 9.32, y, 3.5, step_h - 0.08)
            add_runs(ttf.paragraphs[0], text, 13, BODY)
            y += step_h

        _, tf = textbox(sl, 0.6, 7.02, 10, 0.25)
        r = tf.paragraphs[0].add_run()
        r.text = "TEAM LOST IN ANDROMEDUS   /   NASA SPACE APPS 2026"
        style(r, 10, MUTED, font="Courier New")
        _, tf = textbox(sl, 11.7, 7.02, 1.1, 0.25)
        tf.paragraphs[0].alignment = PP_ALIGN.RIGHT
        r = tf.paragraphs[0].add_run()
        r.text = f"{idx} / {total}"
        style(r, 10, MUTED, font="Courier New")

        sl.notes_slide.notes_text_frame.text = s["notes"]
    prs.save(out)
    print("saved", out)


if __name__ == "__main__":
    out = sys.argv[1]
    only = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[2] == "--only" else None
    build(only, out)
