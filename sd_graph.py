#!/usr/bin/env python3
"""Supply and demand shift diagram generator.

Draws the standard textbook picture: one curve shifts left or right, the old
and new equilibria are marked, and the shortage/surplus at the old price is
shown along with what happens to price and quantity.

Command line:
    python sd_graph.py --determinant Income --curve demand --shift right
    python sd_graph.py -d "Input prices" -c supply -s left -o inputs.pdf
    python sd_graph.py            # no arguments: asks for each value

From Python:
    from sd_graph import draw_graph
    fig = draw_graph("Income", curve="demand", shift="right")
    fig.savefig("income.png", dpi=200)
"""

import argparse
import re
import sys

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

# Everything is laid out on a fixed canvas (units = pixels at 100 dpi, y up).
CANVAS_W, CANVAS_H = 690, 608
ORIGIN_X, ORIGIN_Y = 87.5, 97
AXIS_TOP, AXIS_RIGHT = 549, 584
ARROW_LEN, ARROW_HALF_W = 10, 4.75

HALF_W, HALF_H = 134.5, 166  # half-extent of each curve around its midpoint
SLOPE = HALF_H / HALF_W
SHIFT = 87  # horizontal distance between the old and new curve
EQ_Y = 307  # height of the original equilibrium
# The original equilibrium sits off-centre so the shifted curve stays in frame.
EQ_X = {"right": 328.5, "left": 328.5 + SHIFT}

TITLE_X, TITLE_Y = 329, 573
NOTE_LEFT_X, NOTE_RIGHT_X = 88, 570
NOTE_Y = (61, 37)

# Times New Roman where it is installed, otherwise the closest serif available.
# Later entries also fill in any glyphs (e.g. arrows) the first one lacks.
SERIF_FONTS = ("Times New Roman", "Times", "Nimbus Roman", "Liberation Serif",
               "STIXGeneral", "DejaVu Serif")
_installed = {f.name for f in font_manager.fontManager.ttflist}
FONT = {
    "family": [f for f in SERIF_FONTS if f in _installed] or ["serif"],
    "math_fontfamily": "stix",
    "color": "black",
}
TITLE_SIZE, AXIS_LABEL_SIZE, TEXT_SIZE, TICK_SIZE = 17.3, 13, 11.4, 11

AXIS_LW, CURVE_LW, GUIDE_LW = 2.2, 1.9, 1.0
GUIDE_DASHES = (0, (4.2, 3.2))
DOT_SIZE = 9.5

CURVES = {"d": "demand", "demand": "demand", "s": "supply", "supply": "supply"}
SHIFTS = {
    "r": "right", "right": "right", "increase": "right", "inc": "right", "+": "right",
    "l": "left", "left": "left", "decrease": "left", "dec": "left", "-": "left",
}


def _plain(text):
    """Escape user text that sits outside a $...$ math span."""
    return re.sub(r"[\\$]",
                  lambda m: r"\$" if m[0] == "$" else r"$\backslash$", text)


def _math(text):
    """Escape user text that sits inside a $...$ math span."""
    text = re.sub(r'[\\#^_~"`]', "", text)  # mathtext cannot print these
    text = re.sub(r"([$%{}])", r"\\\1", text)
    return text.replace(" ", r"\ ")


def _sub(label, n, italic=False):
    """`label` with subscript `n`, e.g. P1 or D2."""
    n = rf"\mathit{{{n}}}" if italic else str(n)
    return f"{_plain(label)}$_{{{n}}}$"


def _curve_ends(kind, mid_x):
    """Endpoints (left, right) of a demand or supply line centred on mid_x."""
    rise = HALF_H if kind == "supply" else -HALF_H
    return (mid_x - HALF_W, EQ_Y - rise), (mid_x + HALF_W, EQ_Y + rise)


def draw_graph(
    determinant="",
    curve="demand",
    shift="right",
    title="Market for Goods and Services",
    price_label="P",
    quantity_label="Q",
    demand_label="D",
    supply_label="S",
    show_notes=True,
):
    """Build the diagram and return the matplotlib Figure.

    determinant: what caused the shift (e.g. "Income"); printed under the graph.
    curve:       "demand" or "supply" - the curve that shifts.
    shift:       "right" (increase) or "left" (decrease).
    """
    try:
        curve = CURVES[curve.strip().lower()]
    except KeyError:
        raise ValueError(f"curve must be 'demand' or 'supply', got {curve!r}") from None
    try:
        shift = SHIFTS[shift.strip().lower()]
    except KeyError:
        raise ValueError(f"shift must be 'left' or 'right', got {shift!r}") from None

    fig = plt.figure(figsize=(CANVAS_W / 100, CANVAS_H / 100), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, CANVAS_W)
    ax.set_ylim(0, CANVAS_H)
    ax.axis("off")

    def text(x, y, s, size=TEXT_SIZE, **kw):
        kw = {"ha": "center", "va": "center", **FONT, **kw}
        ax.text(x, y, s, fontsize=size, **kw)

    # Axes, drawn as one mitred line with an arrowhead on each end.
    ax.add_line(Line2D(
        [ORIGIN_X, ORIGIN_X, AXIS_RIGHT - ARROW_LEN / 2],
        [AXIS_TOP - ARROW_LEN / 2, ORIGIN_Y, ORIGIN_Y],
        color="black", lw=AXIS_LW, solid_joinstyle="miter", solid_capstyle="butt",
    ))
    ax.add_patch(Polygon(
        [(ORIGIN_X, AXIS_TOP),
         (ORIGIN_X - ARROW_HALF_W, AXIS_TOP - ARROW_LEN),
         (ORIGIN_X + ARROW_HALF_W, AXIS_TOP - ARROW_LEN)],
        closed=True, fc="black", ec="none",
    ))
    ax.add_patch(Polygon(
        [(AXIS_RIGHT, ORIGIN_Y),
         (AXIS_RIGHT - ARROW_LEN, ORIGIN_Y + ARROW_HALF_W),
         (AXIS_RIGHT - ARROW_LEN, ORIGIN_Y - ARROW_HALF_W)],
        closed=True, fc="black", ec="none",
    ))
    text(ORIGIN_X - 22, AXIS_TOP + 10, _plain(price_label), size=AXIS_LABEL_SIZE)
    text(AXIS_RIGHT - 5, ORIGIN_Y - 20, _plain(quantity_label),
         size=AXIS_LABEL_SIZE, ha="left")
    text(TITLE_X, TITLE_Y, _plain(title), size=TITLE_SIZE)

    # Curves: both originals plus the shifted copy of whichever one moves.
    dx = SHIFT if shift == "right" else -SHIFT
    eq_x = EQ_X[shift]
    labels = {"demand": demand_label, "supply": supply_label}
    lines = [("demand", eq_x, 1), ("supply", eq_x, 1), (curve, eq_x + dx, 2)]
    for kind, mid_x, n in lines:
        (x0, y0), (x1, y1) = _curve_ends(kind, mid_x)
        ax.add_line(Line2D([x0, x1], [y0, y1], color="black", lw=CURVE_LW,
                           solid_capstyle="butt", zorder=3))
        # Demand is labelled at its bottom end, supply at its top end.
        off_x, off_y = (7, -13) if kind == "demand" else (6.5, 6.5)
        text(x1 + off_x, y1 + off_y, _sub(labels[kind], n, italic=True),
             style="italic", ha="left")

    # Old equilibrium, new equilibrium, and where the new curve sits at the
    # old price (the gap between the two is the shortage or surplus).
    old_eq = (eq_x, EQ_Y)
    new_eq = (eq_x + dx / 2,
              EQ_Y + (SLOPE if curve == "demand" else -SLOPE) * dx / 2)
    at_old_price = (eq_x + dx, EQ_Y)
    points = [old_eq, new_eq, at_old_price]

    guide = {"color": "black", "lw": GUIDE_LW, "linestyle": GUIDE_DASHES,
             "zorder": 2}
    ax.add_line(Line2D([ORIGIN_X, max(old_eq[0], at_old_price[0])],
                       [EQ_Y, EQ_Y], **guide))
    ax.add_line(Line2D([ORIGIN_X, new_eq[0]], [new_eq[1], new_eq[1]], **guide))
    for x, y in points:
        ax.add_line(Line2D([x, x], [ORIGIN_Y, y], **guide))
    ax.plot(*zip(*points), "o", color="black", ms=DOT_SIZE, mew=0, zorder=4)

    for y, n in ((old_eq[1], 1), (new_eq[1], 2)):
        text(ORIGIN_X - 5, y - 2, _sub(price_label, n), size=TICK_SIZE, ha="right")
    for (x, _), n in zip(points, (1, 3, 2)):
        text(x, ORIGIN_Y - 18, _sub(quantity_label, n), size=TICK_SIZE)

    if show_notes:
        left = {"ha": "left"}
        right = {"ha": "right"}
        if determinant:
            text(NOTE_LEFT_X, NOTE_Y[0], f"Determinant: {_plain(determinant)}", **left)
        change = "increase" if shift == "right" else "decrease"
        text(NOTE_LEFT_X, NOTE_Y[1],
             f"{curve.capitalize()} shifts to the {shift} ({change})", **left)

        # At the old price: more demand or less supply leaves a shortage.
        shortage = (curve == "demand") == (shift == "right")
        q = _plain(quantity_label)
        q_d = rf"{q}$_{{\mathrm{{{_math(demand_label)}}}}}$"
        q_s = rf"{q}$_{{\mathrm{{{_math(supply_label)}}}}}$"
        text(NOTE_RIGHT_X, NOTE_Y[0],
             f"{q_d} > {q_s} (shortage)" if shortage else f"{q_s} > {q_d} (surplus)",
             **right)
        p_arrow = "\u2191" if shortage else "\u2193"
        q_arrow = "\u2191" if shift == "right" else "\u2193"
        text(NOTE_RIGHT_X, NOTE_Y[1],
             f"{_plain(price_label)}{p_arrow}   {q}{q_arrow}", **right)

    return fig


def _ask(prompt, default=None, choices=None):
    hint = f" [{default}]" if default else ""
    while True:
        answer = input(f"{prompt}{hint}: ").strip() or (default or "")
        if choices is None or answer.lower() in choices:
            return answer
        print(f"  Please enter one of: {', '.join(sorted(set(choices.values())))}")


def _prompt_for_args(args):
    args.determinant = _ask("Determinant (what caused the shift, e.g. Income)")
    args.curve = _ask("Which curve shifts? (demand/supply)", "demand", CURVES)
    args.shift = _ask("Which direction? (left/right)", "right", SHIFTS)
    args.title = _ask("Title", args.title)
    args.price_label = _ask("Price axis label", args.price_label)
    args.quantity_label = _ask("Quantity axis label", args.quantity_label)
    args.output = _ask("Save as", args.output)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate a supply and demand shift diagram.",
        epilog="Run with no arguments to be asked for each value.",
    )
    parser.add_argument("-d", "--determinant", default="",
                        help="what caused the shift, e.g. Income")
    parser.add_argument("-c", "--curve", default="demand", type=str.lower,
                        choices=sorted(CURVES), metavar="{demand,supply}",
                        help="the curve that shifts (default: demand)")
    parser.add_argument("-s", "--shift", default="right", type=str.lower,
                        choices=sorted(SHIFTS), metavar="{left,right}",
                        help="direction of the shift (default: right)")
    parser.add_argument("-t", "--title", default="Market for Goods and Services")
    parser.add_argument("--price-label", default="P", help="vertical axis label")
    parser.add_argument("--quantity-label", default="Q", help="horizontal axis label")
    parser.add_argument("--demand-label", default="D", help="demand curve label")
    parser.add_argument("--supply-label", default="S", help="supply curve label")
    parser.add_argument("--no-notes", action="store_true",
                        help="leave out the text under the graph")
    parser.add_argument("-o", "--output", default="sd_graph.png",
                        help="output file; the extension picks the format "
                             "(.png, .pdf, .svg) (default: sd_graph.png)")
    parser.add_argument("--dpi", type=int, default=200,
                        help="resolution for image output (default: 200)")
    parser.add_argument("--show", action="store_true",
                        help="also open the graph in a window")

    raw = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(raw)
    if not raw:
        _prompt_for_args(args)

    fig = draw_graph(
        determinant=args.determinant,
        curve=args.curve,
        shift=args.shift,
        title=args.title,
        price_label=args.price_label,
        quantity_label=args.quantity_label,
        demand_label=args.demand_label,
        supply_label=args.supply_label,
        show_notes=not args.no_notes,
    )
    fig.savefig(args.output, dpi=args.dpi)
    print(f"Saved {args.output}")
    if args.show:
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
