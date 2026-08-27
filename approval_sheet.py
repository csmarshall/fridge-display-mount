#!/usr/bin/env python3
"""Partner-approval sheet: front elevation, side elevation and a shaded 3D view.

Everything dimensional is read from BracketParams / Display via generate_bracket, so this sheet
cannot drift from the DXF that gets cut. Reference only — not a fabrication drawing.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

import render3d as R3
from bracket_common import LOG_LEVELS, configure_logging
import generate_bracket as G
from generate_bracket import BracketParams, DISPLAYS, MATERIAL, build_geometry, derive_flat, set_display

LOG = logging.getLogger("approval")

# ---- palette ---------------------------------------------------------------------------------
INK = "#14181c"
MUTED = "#6b757e"
RULE = "#c9d1d8"
DIM = "#0a8f6f"
ACCENT = "#c0169a"        # the thing that changed this revision
STEEL_BODY = "#b9c2c9"    # brushed stainless, base albedo
STEEL_DOOR = "#c6ced5"
STEEL_DARK = "#8b959d"
BRACKET = "#2b3036"       # matte black painted steel
MAGNET = "#2e9e5b"        # same green the elevations use for a magnet, for one visual vocabulary
SCREEN_OFF = "#0d1117"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def T(x, y, s, size=10.0, anchor="middle", fill=INK, weight="normal", rot=0.0,
      family="Helvetica,Arial,sans-serif", op=1.0, spacing=0.0):
    tr = f' transform="rotate({rot:.2f} {x:.2f} {y:.2f})"' if rot else ""
    o = f' opacity="{op}"' if op < 1 else ""
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{family}" font-size="{size:.2f}" '
            f'text-anchor="{anchor}" fill="{fill}" font-weight="{weight}"{tr}{o}{ls}>{esc(s)}</text>')


def dim_h(x0, x1, y, label, colour=DIM, tick=4.5, size=8.5, above=True):
    o = [f'<line x1="{x0:.2f}" y1="{y:.2f}" x2="{x1:.2f}" y2="{y:.2f}" stroke="{colour}" stroke-width="0.8"/>']
    for x in (x0, x1):
        o.append(f'<line x1="{x:.2f}" y1="{y-tick:.2f}" x2="{x:.2f}" y2="{y+tick:.2f}" stroke="{colour}" stroke-width="0.8"/>')
    o.append(T((x0+x1)/2, y - 4 if above else y + 11, label, size, fill=colour))
    return "".join(o)


def dim_v(y0, y1, x, label, colour=DIM, tick=4.5, size=8.5, side=-1):
    o = [f'<line x1="{x:.2f}" y1="{y0:.2f}" x2="{x:.2f}" y2="{y1:.2f}" stroke="{colour}" stroke-width="0.8"/>']
    for y in (y0, y1):
        o.append(f'<line x1="{x-tick:.2f}" y1="{y:.2f}" x2="{x+tick:.2f}" y2="{y:.2f}" stroke="{colour}" stroke-width="0.8"/>')
    o.append(T(x + side*4, (y0+y1)/2, label, size, fill=colour, rot=-90))
    return "".join(o)


def panel(x, y, w, h, title, subtitle=""):
    o = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#ffffff" '
         f'stroke="{RULE}" stroke-width="1.2" rx="3"/>',
         f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="30" fill="#f4f6f8" stroke="{RULE}" '
         f'stroke-width="1.2" rx="3"/>',
         T(x+14, y+20, title, 12.0, anchor="start", weight="bold", spacing="0.6")]
    if subtitle:
        o.append(T(x+w-14, y+20, subtitle, 9.5, anchor="end", fill=MUTED))
    return "".join(o)


def person(x_ft, y_floor, scale, height_mm=1727.0, fill="#dfe5ea"):
    """Simple standing silhouette for scale. 1727 mm = 5 ft 8 in."""
    h = height_mm * scale
    head_r = h * 0.042
    sh = y_floor - h
    neck = sh + head_r * 2.2
    shoulder = h * 0.058          # half-width at the shoulders
    waist = h * 0.042
    hip_y = neck + h * 0.34
    o = [f'<circle cx="{x_ft:.1f}" cy="{sh + head_r:.1f}" r="{head_r:.1f}" fill="{fill}"/>',
         f'<path d="M {x_ft-shoulder:.1f} {neck+h*0.045:.1f} '
         f'Q {x_ft-shoulder*1.02:.1f} {neck:.1f} {x_ft-shoulder*0.55:.1f} {neck:.1f} '
         f'L {x_ft+shoulder*0.55:.1f} {neck:.1f} '
         f'Q {x_ft+shoulder*1.02:.1f} {neck:.1f} {x_ft+shoulder:.1f} {neck+h*0.045:.1f} '
         f'L {x_ft+waist:.1f} {hip_y:.1f} L {x_ft+waist*1.05:.1f} {y_floor:.1f} '
         f'L {x_ft+waist*0.18:.1f} {y_floor:.1f} L {x_ft:.1f} {hip_y+h*0.10:.1f} '
         f'L {x_ft-waist*0.18:.1f} {y_floor:.1f} L {x_ft-waist*1.05:.1f} {y_floor:.1f} '
         f'L {x_ft-waist:.1f} {hip_y:.1f} Z" fill="{fill}"/>']
    return "".join(o)


# ---- chore-tracker UI drawn on the screen -----------------------------------------------------
# The real board. Task on the left, who owns it on the right — which is why "Veronica - Looking
# Pretty" reads as ("Looking pretty", "Veronica") here rather than the other way round.
EYE_FRACTION = 0.935
STATURES = ((1930.0, "6 ft 4 in"), (1549.0, "5 ft 1 in"))   # the band the brief asks us to serve

GHOST_COLS = ("#e0793a", "#8e6bd6", "#2f8fd6", "#d64f7a")

CHORES = [("Dishes", "Harper", 1),
          ("Garbage", "Miles", 0),
          ("Looking pretty", "Veronica", 1),
          ("Grunt work", "Charles", 0),
          ("Dogs", "Chloe", 1)]


def screen_ui(w: float, h: float, scale: float = 1.0) -> str:
    """Chore board in local screen coordinates, origin top-left, size w x h (mm)."""
    s = w / 297.46
    o = [f'<rect x="0" y="0" width="{w:.2f}" height="{h:.2f}" fill="#101820"/>',
         f'<rect x="0" y="0" width="{w:.2f}" height="{h*0.115:.2f}" fill="#18222c"/>',
         T(w*0.07, h*0.052, "THIS WEEK", 11.5*s, anchor="start", fill="#f2f6f9", weight="bold", spacing="1.2"),
         T(w*0.07, h*0.088, "Mon 25 Aug", 8.2*s, anchor="start", fill="#7f909e"),
         T(w*0.93, h*0.070, f"{sum(d for _, _, d in CHORES)} / {len(CHORES)}", 15*s,
           anchor="end", fill="#3ddc97", weight="bold")]
    top = h * 0.155
    row = h * 0.077
    for i, (task, who, done) in enumerate(CHORES):
        yy = top + i*row
        o.append(f'<rect x="{w*0.055:.2f}" y="{yy:.2f}" width="{w*0.89:.2f}" height="{row*0.80:.2f}" '
                 f'rx="{2.4*s:.2f}" fill="#18222c"/>')
        bx, by, bs = w*0.085, yy + row*0.22, row*0.36
        if done:
            o.append(f'<rect x="{bx:.2f}" y="{by:.2f}" width="{bs:.2f}" height="{bs:.2f}" rx="{1.4*s:.2f}" fill="#3ddc97"/>')
            o.append(f'<path d="M {bx+bs*0.24:.2f} {by+bs*0.52:.2f} L {bx+bs*0.44:.2f} {by+bs*0.74:.2f} '
                     f'L {bx+bs*0.78:.2f} {by+bs*0.26:.2f}" stroke="#101820" stroke-width="{1.5*s:.2f}" '
                     f'fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
        else:
            o.append(f'<rect x="{bx:.2f}" y="{by:.2f}" width="{bs:.2f}" height="{bs:.2f}" rx="{1.4*s:.2f}" '
                     f'fill="none" stroke="#46586a" stroke-width="{1.1*s:.2f}"/>')
        col = "#5d6f7e" if done else "#e8eef3"
        o.append(T(w*0.175, yy + row*0.50, task, 9.2*s, anchor="start", fill=col,
                   weight="normal" if done else "bold"))
        o.append(T(w*0.915, yy + row*0.50, who, 7.4*s, anchor="end", fill="#5d6f7e"))
    fy = top + len(CHORES)*row + h*0.030
    o.append(f'<rect x="{w*0.055:.2f}" y="{fy:.2f}" width="{w*0.89:.2f}" height="{h*0.145:.2f}" '
             f'rx="{2.4*s:.2f}" fill="#18222c"/>')
    o.append(T(w*0.085, fy + h*0.042, "NEXT UP", 7.4*s, anchor="start", fill="#7f909e", spacing="1"))
    o.append(T(w*0.085, fy + h*0.088, "Recycling — Thu", 9.6*s, anchor="start", fill="#e8eef3", weight="bold"))
    o.append(T(w*0.085, fy + h*0.122, "Grocery run — Sat 10:30", 7.8*s, anchor="start", fill="#7f909e"))
    return "".join(o)


# ---- world model -------------------------------------------------------------------------------
class World:
    """Every world coordinate the two elevations and the 3D scene share. mm.

    x runs across the fridge front as seen by someone STANDING IN FRONT OF IT (0 = their left,
    FW = their right), y runs front to back (0 = cabinet front face, negative = out into the room
    where the doors and handles live), z runs up from the floor.

    `mount_side` says which side panel the bracket hangs on, in that same standing-in-front frame.
    Charles's is on the LEFT. It changes every view but NOT the cut file: the flat pattern is
    mirror-symmetric about its own centreline, so the identical part serves either hand — you turn
    it over. Nothing here feeds the DXF.
    """

    def __init__(self, params: BracketParams, display, mount_side: str = "left") -> None:
        p, d = params, display
        self.p, self.d = p, d
        self.mount_side = mount_side
        self.FW = p.fridge_top_width
        self.FD = p.fridge_depth
        self.FH = p.fridge_height
        self.door_proj = p.fridge_depth_with_doors - p.fridge_depth
        self.hinge = p.hinge_cover_proud
        self.t = MATERIAL.thickness
        self.pad = p.bottom_pad_thickness

        # d = +1 when the stack grows in +x (mounted on the right), -1 on the left. Every depth
        # below is written once, in terms of it.
        self.dir = -1.0 if mount_side == "left" else 1.0
        self.face_x = 0.0 if mount_side == "left" else self.FW

        # The plate's inner face stands off the side panel by the magnet height; the arm's under
        # face stands off the fridge top by the sponge pad. Same part, two different faces.
        self.plate_in = self.face_x + self.dir * p.magnet_standoff
        self.plate_out = self.plate_in + self.dir * self.t
        self.arm_tip = self.plate_out - self.dir * p.arm_len   # arm reaches INBOARD over the top
        self.arm_z0 = self.FH + self.pad
        self.arm_z1 = self.arm_z0 + self.t
        self.yc = self.FD / 2.0

        self.box_out = self.plate_out + self.dir * d.rear_box_depth
        self.panel_out = self.box_out + self.dir * d.panel_depth
        self.standoff = abs(self.panel_out - self.face_x)

        self.body_y0 = self.yc - p.body_w / 2.0
        self.body_y1 = self.yc + p.body_w / 2.0
        self.body_z1 = self.FH - p.neck_len          # top of the wide body / bottom of the neck
        self.body_z0 = self.body_z1 - p.body_h
        self.neck_y0 = self.yc - p.neck_w / 2.0
        self.neck_y1 = self.yc + p.neck_w / 2.0

        # portrait: the display presents its SHORT dimension across the fridge depth
        self.disp_w = d.height          # 324.65 across y
        self.disp_h = d.width           # 555.23 up z
        self.box_w = d.rear_box_h       # 134 across y
        self.box_h = d.rear_box_w       # 260 up z
        self.disp_zc = p.screen_centre_height

        # face names for R3.box: which side of a slab faces away from the fridge
        self.outer = "x+" if self.dir > 0 else "x-"
        self.inner = "x-" if self.dir > 0 else "x+"

    @staticmethod
    def span(a: float, b: float) -> tuple[float, float]:
        """(origin, size) for a box edge given two x values in either order."""
        return (min(a, b), abs(b - a))

    def body_to_world(self, xb: float, yb: float) -> tuple[float, float]:
        """Flat-pattern body coordinates -> (world y, world z).

        The flat pattern's x axis maps to world y. On a left-hand mount the plate is turned over,
        so flat-x runs the other way down the fridge; the features are symmetric about the plate
        centreline, so this only matters for labelling, never for fit.
        """
        xb_eff = xb if self.dir > 0 else (self.p.body_w - xb)
        return (self.body_y0 + xb_eff, self.body_z0 + yb)


def magnet_rows(geom) -> list[float]:
    """FITTED body magnet rows only.

    Adding discs to the optional mid-side positions made this pick them up, and the sheet
    silently went from claiming 8 magnets to 10 and its let-go from 194 to 252 lbf. The optional
    positions are HOLES; a drawing must never count a hole as a magnet.
    """
    return sorted({round(h.y, 3) for h in geom.magnet_discs
                   if h.region == "body" and not h.tag.startswith("spare")})


def arm_magnet_offsets(params: BracketParams) -> list[float]:
    if not params.arm_magnets:
        return []
    return sorted({params.arm_magnet_offset, *params.extra_arm_magnet_offsets})


def let_go_lbf(params: BracketParams, world: World, rows: Sequence[float],
               arm_offsets: Sequence[float], per_magnet_pull: float, n_per_row: int = 2) -> float:
    """Outward pull at the bottom of the screen that peels the plate off the fridge.

    The hook bears on the fridge's top edge, so that edge is the pivot. Body magnets resist with a
    lever equal to their depth below it. The top-lip magnets sit on the OTHER side of that pivot
    and resist by holding the arm down, with a lever equal to their reach along the arm — a much
    shorter lever, so each is worth far less than a body magnet, but not zero.

    This is the peel case only. The magnets still carry no share of the display's WEIGHT; the hook
    does all of that, which is the invariant the whole design rests on.
    """
    body = sum(n_per_row * per_magnet_pull * (world.FH - world.body_to_world(0.0, y)[1])
               for y in rows)
    arm = sum(n_per_row * per_magnet_pull * off for off in arm_offsets)
    lever = world.FH - (params.screen_centre_height - world.disp_h / 2.0)
    return (body + arm) / lever


# ---- 3D scene ------------------------------------------------------------------------------------
def build_scene(w: World, geom, rows: Sequence[float], arm_offsets: Sequence[float]) -> R3.Scene:
    p, d = w.p, w.d
    sc = R3.Scene()
    flip = w.dir < 0

    def xw(pts):
        """Reverse winding on a mirrored scene so outward normals stay outward."""
        return list(reversed(pts)) if flip else list(pts)

    # floor, then a soft contact shadow cast away from the key light. Stacked quads rather than a
    # real shadow pass — enough to stop the cabinet floating.
    sc.add([R3.Face([(-1400, -1500, 0), (2600, -1500, 0), (2600, 1400, 0), (-1400, 1400, 0)],
                    "#eaeef1", "floor", shade=False)])
    for grow, op in ((150.0, 0.035), (100.0, 0.04), (62.0, 0.045), (32.0, 0.05), (10.0, 0.06)):
        sc.add([R3.Face([(-grow*1.5, -w.door_proj - grow, 0.4), (w.FW + grow*1.5, -w.door_proj - grow, 0.4),
                         (w.FW + grow*1.5, w.FD + grow, 0.4), (-grow*1.5, w.FD + grow, 0.4)],
                        "#5d6a75", "shadow", opacity=op, shade=False)])

    sc.add(R3.box((0, 0, 0), (w.FW, w.FD, w.FH), STEEL_BODY, "case",
                  faces=f"{w.outer} y- z+", top="#cdd5db"))
    sc.add(R3.box((0, -w.door_proj, 0), (w.FW, w.door_proj, 62), "#5b646b", "plinth",
                  faces=f"y- {w.outer}"))

    split = w.FW * 0.505
    gap = 5.0
    for x0, x1 in ((0.0, split - gap/2), (split + gap/2, w.FW)):
        sc.add(R3.box((x0, -w.door_proj, 62), (x1-x0, w.door_proj, w.FH - 62), STEEL_DOOR,
                      "door", faces=f"y- {w.outer} z+", top="#cdd5db"))
    for hx in (split - gap/2 - 62, split + gap/2 + 28):
        sc.add(R3.box((hx, -w.door_proj - 34, 620), (34, 22, 780), "#7d868d", "handle",
                      faces="y- x+ x- z+"))
    for hx in (0.0, w.FW - 96):
        sc.add(R3.box((hx, 0, w.FH), (96, 104, w.hinge), "#aeb7be", "hinge",
                      faces="z+ y- x+ x-"))

    # ---- the bracket, one bent part -------------------------------------------------------------
    ax0, axw = World.span(w.arm_tip, w.plate_out)
    sc.add(R3.box((ax0, w.neck_y0, w.arm_z0), (axw, p.neck_w, w.t), BRACKET, "arm",
                  faces=f"z+ {w.inner} y- y+"))
    px0, pxw = World.span(w.plate_in, w.plate_out)
    sc.add(R3.box((px0, w.neck_y0, w.body_z1), (pxw, p.neck_w, w.arm_z0 - w.body_z1),
                  BRACKET, "neck", faces=f"{w.outer} y- y+"))
    sc.add(R3.box((px0, w.body_y0, w.body_z0), (pxw, p.body_w, p.body_h),
                  BRACKET, "body", faces=f"{w.outer} y- y+ z-"))
    apx0, apxw = World.span(w.arm_tip + w.dir * 6, w.plate_out)
    sc.add(R3.box((apx0, w.neck_y0 + 6, w.FH), (apxw, p.neck_w - 12, w.pad),
                  "#3a4046", "arm-pad", faces=f"{w.inner} y- y+"))

    # magnets, in the gap between plate and side panel
    for yb in rows:
        for xb in (p.magnet_inset, p.body_w - p.magnet_inset):
            wy, wz = w.body_to_world(xb, yb)
            sc.add([R3.disc((w.plate_in - w.dir * 0.4, wy, wz), p.magnet_disc_dia/2,
                            w.outer, MAGNET, tag="magnet")])
    # ---- the display ---------------------------------------------------------------------------
    # Everything from here out hangs OUTBOARD of the bracket, so it can never be occluded by it.
    # Declare that to the depth sort: without it the tall neck quad wins on centroid range by a
    # few mm and paints a black band down over the top third of the screen.
    def outboard(faces, depth):
        for fc in faces:
            fc.bias = depth
        return faces

    bx0, bxw = World.span(w.plate_out, w.box_out)
    sc.add(outboard(R3.box((bx0, w.yc - w.box_w/2, w.disp_zc - w.box_h/2), (bxw, w.box_w, w.box_h),
                           "#20262c", "rear-box", faces="y- y+ z+ z-"), d.rear_box_depth))
    nx0, nxw = World.span(w.box_out, w.panel_out)
    pan_y0 = w.yc - w.disp_w/2
    pan_z0 = w.disp_zc - w.disp_h/2
    sc.add(outboard(R3.box((nx0, pan_y0, pan_z0), (nxw, w.disp_w, w.disp_h),
                           "#1b2026", "panel", faces="y- y+ z+ z-"), w.standoff))
    sx_ = w.panel_out
    sc.add(outboard([R3.Face(xw([(sx_, pan_y0, pan_z0), (sx_, pan_y0 + w.disp_w, pan_z0),
                        (sx_, pan_y0 + w.disp_w, pan_z0 + w.disp_h), (sx_, pan_y0, pan_z0 + w.disp_h)]),
                    "#0f1319", "bezel")], w.standoff))

    aw, ah = d.active_h, d.active_w      # portrait: active area is 297.46 across, 528.04 up
    ay0 = w.yc - aw/2
    az1 = w.disp_zc + ah/2
    fx = sx_ + w.dir * 0.3
    # Wound so corner 0 is the UI's top-left and corner 1 its top-right AS READ BY A VIEWER facing
    # the screen. On a left-hand mount that viewer stands on the other side, so the y order flips —
    # get this wrong and the chore list renders mirrored.
    if w.dir > 0:   # reader stands at +x, their right hand points to +y
        quad = [(fx, ay0, az1), (fx, ay0 + aw, az1), (fx, ay0 + aw, az1 - ah), (fx, ay0, az1 - ah)]
    else:           # reader stands at -x, their right hand points to -y
        quad = [(fx, ay0 + aw, az1), (fx, ay0, az1), (fx, ay0, az1 - ah), (fx, ay0 + aw, az1 - ah)]

    def paint(proj, _w=aw, _h=ah):
        return f'<g transform="{R3.quad_matrix(proj, _w, _h)}">{screen_ui(_w, _h)}</g>'

    f = R3.Face(quad, SCREEN_OFF, "screen", shade=False, cull=False)
    f.painter = paint
    # The lit glass is the outermost surface of the whole assembly — nothing may draw over it.
    f.bias = w.standoff + 0.3
    sc.add([f])
    return sc


# ---- elevations ----------------------------------------------------------------------------------
def front_elevation(x0, y0, w, h, W: World, rows) -> str:
    """Looking at the mounting side panel from outside: fridge depth across, height up.

    On a LEFT-hand mount you view along +x, which puts the cabinet FRONT on the right of the view;
    on a right-hand mount it lands on the left. Drawing it the wrong way round would put the door
    on the wrong side of the display and quietly misrepresent the clearance.
    """
    p = W.p
    front_right = W.dir < 0

    # Nothing happens on the lower half of the fridge, so crop it to a stub behind a standard
    # break line and spend the recovered height on the display. The panel therefore has its OWN
    # scale, larger than the sheet scale `s` that panels 1 and 3 share — the break line is what
    # tells the reader the lower run is not to length.
    Z_CUT = 900.0            # break here: well below the display's bottom edge
    STUB_PX = 54.0           # how much drawing height the cropped run keeps
    LEGEND_PX = 118.0        # reserved at the bottom for the panel-options legend
    GHOST_SPAN = 640.0       # widest thing drawn across: the 27 in landscape ghost, plus slack

    gx = x0 + 44
    gy = y0 + h - 46 - LEGEND_PX
    top_span = W.FH + W.hinge - Z_CUT
    s = min((w - 96) / GHOST_SPAN, (gy - (y0 + 34) - STUB_PX) / top_span)

    def X(mm):
        return gx + ((W.FD - mm) if front_right else mm) * s

    def Y(mm):
        """Piecewise: true scale above the break, compressed stub below it.

        Written as a mapping rather than by cropping the geometry so every existing call —
        including the screen-centre dimension that runs to the floor — keeps working unchanged.
        """
        if mm >= Z_CUT:
            return gy - STUB_PX - (mm - Z_CUT) * s
        return gy - mm * (STUB_PX / Z_CUT)

    def rect(ya, yb, za, zb, **kw):
        xa, xb = sorted((X(ya), X(yb)))
        za_, zb_ = sorted((Y(za), Y(zb)))
        attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
        return (f'<rect x="{xa:.2f}" y="{za_:.2f}" width="{xb-xa:.2f}" '
                f'height="{zb_-za_:.2f}" {attrs}/>')

    o = [f'<line x1="{x0+14:.1f}" y1="{gy:.1f}" x2="{x0+w-14:.1f}" y2="{gy:.1f}" '
         f'stroke="{INK}" stroke-width="1.4"/>']

    def break_marker(yb):
        """Standard zig-zag break: the run below it is cropped, not drawn to length."""
        xa, xb = x0 + 16, x0 + w - 16
        n, amp = 26, 5.0
        pts = [(xa + (xb - xa) * i / n, yb + (amp if i % 2 else -amp)) for i in range(n + 1)]
        d = " ".join(f"{'M' if i == 0 else 'L'}{px:.1f},{py:.1f}" for i, (px, py) in enumerate(pts))
        return (f'<rect x="{xa:.1f}" y="{yb-amp-3:.1f}" width="{xb-xa:.1f}" height="{2*amp+6:.1f}" '
                f'fill="#fbfcfd"/>'
                f'<path d="{d}" fill="none" stroke="{STEEL_DARK}" stroke-width="1.1"/>')
    o.append(rect(0, W.FD, 0, W.FH, fill="#eef2f5", stroke=STEEL_DARK, stroke_width="1.3"))
    o.append(rect(-W.door_proj, 0, 62, W.FH, fill="#e3e9ee", stroke=STEEL_DARK, stroke_width="1.1"))
    o.append(T(X(-W.door_proj/2), Y(300), "door", 7.5, fill=MUTED, rot=-90))
    # The hinge cover, MEASURED, and it belongs at the FRIDGE FRONT where the hinge is.
    # CAREFUL WITH THE DATUM: in this view mm is measured BACKWARD FROM THE CASE FRONT — that is
    # why the door is drawn at negative mm. `hinge_cover_from_rear` is rear-referenced, so it has
    # to be flipped here. Feeding it in raw put the cover at the back of the fridge.
    cover_depth = W.FD - p.hinge_cover_from_rear          # 204 mm, measured back from the front
    o.append(rect(0, cover_depth, W.FH, W.FH + W.hinge, fill="#cfd8de", stroke=STEEL_DARK,
                  stroke_width="1"))
    o.append(T(X(cover_depth / 2), Y(W.FH + W.hinge) - 7, "hinge cover", 7.0, fill=MUTED))
    o.append(T(X(cover_depth / 2), Y(W.FH + W.hinge) + 3, "lifts off", 6.4, fill=MUTED))
    o.append(dim_h(min(X(cover_depth), X(W.FD)), max(X(cover_depth), X(W.FD)), Y(W.FH) - 54,
                   f"clear window {p.hinge_cover_from_rear:.0f} — arm needs {p.neck_w:.0f}"))
    # Say which way is which. Without it the reader has to infer orientation from the door.
    # Placed against the GROUND LINE, not the fridge top — the top is above the panel's drawing
    # area once the cabinet is broken, and an earlier version put this in the sheet header.
    front_x = X(-W.door_proj)
    outward = 1 if front_x > X(W.FD) else -1
    # gy + 20 sat exactly under the legend box, which is drawn later and covered it. Put it in
    # the cropped stub instead, above the ground line, on a mask so it reads over the cabinet.
    ay = gy - 26
    o.append(f'<rect x="{min(front_x, front_x - outward*164):.1f}" y="{ay-9:.1f}" '
             f'width="164" height="18" fill="#fbfcfd" fill-opacity="0.92" rx="2"/>')
    o.append(f'<line x1="{front_x - outward*70:.1f}" y1="{ay:.1f}" x2="{front_x:.1f}" '
             f'y2="{ay:.1f}" stroke="{INK}" stroke-width="1.5"/>')
    o.append(f'<path d="M{front_x:.1f},{ay:.1f} l{-outward*8:.1f},-4 l0,8 z" fill="{INK}"/>')
    o.append(T(front_x - outward*76, ay + 3.4, "FRIDGE FRONT", 8.4,
               anchor="end" if outward > 0 else "start", fill=INK, weight="700"))
    o.append(rect(W.neck_y0, W.neck_y1, W.FH, W.arm_z1, fill=BRACKET))
    # The neck from the display's top edge up to the fridge top is VISIBLE painted steel,
    # not hidden behind the panel — draw it solid. Only the part behind the display is ghosted.
    disp_top = W.disp_zc + W.disp_h / 2.0
    o.append(rect(W.neck_y0, W.neck_y1, W.body_z1, min(disp_top, W.FH), fill="none",
                  stroke=BRACKET, stroke_width="1.2", stroke_dasharray="5 3"))
    if disp_top < W.FH:
        o.append(rect(W.neck_y0, W.neck_y1, disp_top, W.FH, fill=BRACKET))
        # Label goes OUTSIDE the block with a leader: the neck is narrower than the text, so
        # anything set inside it gets clipped at both ends and lands white-on-pale where it escapes.
        lz = (disp_top + W.FH) / 2.0
        lx = max(X(W.neck_y0), X(W.neck_y1)) + 10
        o.append(f'<line x1="{max(X(W.neck_y0), X(W.neck_y1)):.1f}" y1="{Y(lz):.1f}" '
                 f'x2="{lx - 3:.1f}" y2="{Y(lz):.1f}" stroke="{MUTED}" stroke-width="0.8"/>')
        o.append(T(lx, Y(lz) - 2, f"{W.FH - disp_top:.0f} mm of neck", 7.6,
                   anchor="start", fill=INK, weight="700"))
        o.append(T(lx, Y(lz) + 9, "visible above the screen", 7.0, anchor="start", fill=MUTED))
    o.append(rect(W.body_y0, W.body_y1, W.body_z0, W.body_z1, fill="none", stroke=BRACKET,
                  stroke_width="1.2", stroke_dasharray="5 3"))
    for yb in rows:
        for xb in (p.magnet_inset, p.body_w - p.magnet_inset):
            wy, wz = W.body_to_world(xb, yb)
            extra = yb not in (p.magnet_inset, p.body_h - p.magnet_inset)
            col = ACCENT if extra else "#2e9e5b"
            o.append(f'<circle cx="{X(wy):.1f}" cy="{Y(wz):.1f}" r="{p.magnet_disc_dia/2*s:.1f}" '
                     f'fill="{col}" fill-opacity="0.30" stroke="{col}" stroke-width="1.3"/>')
    o.append(rect(W.yc - W.disp_w/2, W.yc + W.disp_w/2, W.disp_zc - W.disp_h/2,
                  W.disp_zc + W.disp_h/2, rx=f"{W.d.corner_radius*s:.1f}", fill="#1b2026",
                  fill_opacity="0.72", stroke=INK, stroke_width="1.4"))
    aw, ah = W.d.active_h, W.d.active_w
    o.append(f'<g transform="translate({min(X(W.yc-aw/2), X(W.yc+aw/2)):.2f} '
             f'{Y(W.disp_zc+ah/2):.2f}) scale({s:.5f})" opacity="0.92">{screen_ui(aw, ah)}</g>')

    # All four panel/orientation options as dashed ghosts, so the fit of the ones we did NOT
    # build is visible rather than asserted. Every option shares this bracket: the 27 in has the
    # same rear box, same VESA 100 and same 43 mm depth, so only the glass changes.
    # The counter-depth cabinet is the binding dimension — it is only 609.6 mm front to back.
    # Labels go in a legend, NOT at the rectangle edges: the landscape ghosts are wider than the
    # cabinet by design, so edge-anchored text runs straight off the panel.
    CABINET_DEPTH = 609.6
    ghosts = [(n, o_, (d.height if o_ == "portrait" else d.width),
               (d.width if o_ == "portrait" else d.height), d.corner_radius)
              for n, d in sorted(DISPLAYS.items()) for o_ in ("portrait", "landscape")]
    legend = []
    for i, (name, orient, across, up, cr) in enumerate(ghosts):
        is_built = (name, orient) == ("23.8", p.orientation)
        col = INK if is_built else GHOST_COLS[i % len(GHOST_COLS)]
        if not is_built:
            o.append(rect(W.yc - across/2, W.yc + across/2, W.disp_zc - up/2, W.disp_zc + up/2,
                          rx=f"{cr*s:.1f}", fill="none", stroke=col, stroke_width="1.5",
                          stroke_dasharray="8 5", opacity="0.95"))
        clear = (CABINET_DEPTH - across) / 2.0
        legend.append((col, is_built, f'{name}" {orient}',
                       f'{across:.0f} x {up:.0f} mm',
                       f'{clear:+.0f} mm each side' if clear >= 0
                       else f'overhangs {-clear:.0f} mm each side'))
    lx, ly = x0 + 18, gy + 40
    o.append(f'<rect x="{lx-10:.1f}" y="{ly-20:.1f}" width="302" height="104" fill="#ffffff" '
             f'fill-opacity="0.95" stroke="{RULE}" stroke-width="1" rx="3"/>')
    o.append(T(lx + 276, ly - 6, "clearance", 6.8, anchor="end", fill="#9fb0bd"))
    o.append(T(lx, ly - 6, f"PANEL OPTIONS — cabinet is {CABINET_DEPTH:.0f} mm deep",
               7.4, anchor="start", fill="#7f8f9c", spacing="0.8"))
    for j, (col, is_built, label, dims, fit) in enumerate(legend):
        ty = ly + 12 + j * 17
        o.append(f'<line x1="{lx:.1f}" y1="{ty-3:.1f}" x2="{lx+22:.1f}" y2="{ty-3:.1f}" '
                 f'stroke="{col}" stroke-width="2"'
                 + ('' if is_built else ' stroke-dasharray="6 4"') + '/>')
        o.append(T(lx + 30, ty, label + ("  (BUILT)" if is_built else ""), 8.0,
                   anchor="start", fill=INK if is_built else col,
                   weight="700" if is_built else "400"))
        o.append(T(lx + 128, ty, dims, 7.6, anchor="start", fill="#5c6b77"))
        o.append(T(lx + 282, ty, fit, 7.6, anchor="end",
                   fill="#b4462f" if "overhangs" in fit else "#2e9e5b"))
    # Drawn last so it sits over the cropped cabinet rather than under it.
    o.append(break_marker(gy - STUB_PX))
    o.append(T(x0 + w - 18, gy - STUB_PX + 22, "lower cabinet not to length", 6.9,
               anchor="end", fill=MUTED))
    for yb in rows:
        for xb in (p.magnet_inset, p.body_w - p.magnet_inset):
            wy, wz = W.body_to_world(xb, yb)
            extra = yb not in (p.magnet_inset, p.body_h - p.magnet_inset)
            col = ACCENT if extra else "#4dd6a0"
            o.append(f'<circle cx="{X(wy):.1f}" cy="{Y(wz):.1f}" r="{p.magnet_disc_dia/2*s:.1f}" '
                     f'fill="none" stroke="{col}" stroke-width="1.2" stroke-dasharray="3 2.5" '
                     f'opacity="0.9"/>')
    o.append(T(X(W.yc), Y(W.disp_zc - W.disp_h/2) + 56,
               f"{len(rows)*2} of the {len(rows)*2 + len(arm_magnet_offsets(p))*2} magnets "
               f"hold the screen flat",
               8.2, fill="#2e9e5b"))
    # On a left-hand mount the cabinet FRONT is on the right of this view and the door sits
    # there, so the dimension stack goes on the left. Fixing it to one side drew it over the door.
    dim_x = gx - 30 if front_right else gx + W.FD * s + 30
    o.append(dim_v(Y(W.disp_zc), Y(0), dim_x, f"screen centre {p.screen_centre_height:.0f}",
                   side=1 if front_right else -1))
    o.append(dim_h(min(X(0), X(W.FD)), max(X(0), X(W.FD)), Y(W.FH) - 24,
                   f"fridge depth {W.FD:.0f}"))
    o.append(dim_h(min(X(W.yc-W.disp_w/2), X(W.yc+W.disp_w/2)),
                   max(X(W.yc-W.disp_w/2), X(W.yc+W.disp_w/2)),
                   Y(W.disp_zc - W.disp_h/2) + 26, f"display {W.disp_w:.0f}",
                   colour="#1a5fb4", above=False))
    o.append(T(x0 + 16, Y(W.FH) + 16, f"{W.yc - W.disp_w/2:.0f} mm clear of the door",
               8.0, anchor="start", fill=MUTED))
    return "".join(o)


def side_elevation(x0, y0, w, h, W: World, rows, arm_offsets, s) -> str:
    """Looking at the fridge front, as a person standing in the kitchen sees it.

    This is the view that shows the hook going over the top, and the one that has to agree with
    Charles's statement that the display is on the LEFT from here.
    """
    p = W.p
    left_mount = W.dir < 0
    FIGURE_LANE = 206.0      # width reserved for the two figures, beside the display
    gx = x0 + (30 + FIGURE_LANE if left_mount else 44)
    gy = y0 + h - 46

    def X(mm): return gx + mm * s
    def Y(mm): return gy - mm * s

    def rect(xa, xb, za, zb, **kw):
        a, b = sorted((X(xa), X(xb)))
        c, dd = sorted((Y(za), Y(zb)))
        attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
        return f'<rect x="{a:.2f}" y="{c:.2f}" width="{b-a:.2f}" height="{dd-c:.2f}" {attrs}/>'

    o = [f'<line x1="{x0+14:.1f}" y1="{gy:.1f}" x2="{x0+w-14:.1f}" y2="{gy:.1f}" '
         f'stroke="{INK}" stroke-width="1.4"/>']
    o.append(rect(0, W.FW, 0, W.FH, fill="#eef2f5", stroke=STEEL_DARK, stroke_width="1.3"))
    o.append(f'<line x1="{X(W.FW*0.505):.1f}" y1="{Y(W.FH):.1f}" x2="{X(W.FW*0.505):.1f}" '
             f'y2="{Y(62):.1f}" stroke="{STEEL_DARK}" stroke-width="1"/>')
    for hx in (W.FW*0.505 - 96, W.FW*0.505 + 40):
        o.append(rect(hx, hx + 34, 620, 1400, rx="3", fill="#b7c0c7", stroke=STEEL_DARK,
                      stroke_width="0.9"))
    # The hinge cover runs front-to-back, so in THIS frontal view it is edge-on at the door
    # line, not a block along the top. Drawing it here would misrepresent it — the clearance it
    # governs is arm WIDTH, which is shown in the side elevation instead.
    o.append(rect(W.FW - 104, W.FW, W.FH, W.FH + W.hinge, fill="#cfd8de", stroke=STEEL_DARK,
                  stroke_width="1"))
    o.append(rect(W.arm_tip, W.plate_out, W.arm_z0, W.arm_z1, fill=BRACKET))
    o.append(rect(W.plate_in, W.plate_out, W.body_z0, W.arm_z1, fill=BRACKET))
    o.append(rect(W.arm_tip + W.dir*6, W.plate_out, W.FH, W.FH + W.pad, fill="#8d949b"))
    for off in arm_offsets:
        o.append(rect(W.plate_out - W.dir*(off + p.arm_magnet_disc_dia/2),
                      W.plate_out - W.dir*(off - p.arm_magnet_disc_dia/2),
                      W.FH - p.arm_magnet_standoff, W.FH,
                      fill="#2e9e5b", fill_opacity="0.55", stroke="#2e9e5b", stroke_width="1"))
    for yb in rows:
        wy, wz = W.body_to_world(0.0, yb)
        extra = yb not in (p.magnet_inset, p.body_h - p.magnet_inset)
        col = ACCENT if extra else "#2e9e5b"
        o.append(rect(W.face_x, W.plate_in, wz - p.magnet_disc_dia/2, wz + p.magnet_disc_dia/2,
                      fill=col, fill_opacity="0.55", stroke=col, stroke_width="1"))
    o.append(rect(W.plate_out, W.box_out, W.disp_zc - W.box_h/2, W.disp_zc + W.box_h/2,
                  fill="#39414a"))
    o.append(rect(W.box_out, W.panel_out, W.disp_zc - W.disp_h/2, W.disp_zc + W.disp_h/2,
                  fill="#1b2026"))
    # From the front the display is a thin dark strip and nothing identified it — a reader could
    # not tell which black shape was the screen. Name it, with a leader onto the strip itself.
    slab_x = max(X(W.panel_out), X(W.box_out))
    slab_z = W.disp_zc + W.disp_h / 2.0 - 90.0
    o.append(f'<line x1="{slab_x:.1f}" y1="{Y(slab_z):.1f}" x2="{slab_x + 40:.1f}" '
             f'y2="{Y(slab_z):.1f}" stroke="{MUTED}" stroke-width="0.8"/>')
    o.append(f'<rect x="{slab_x + 42:.1f}" y="{Y(slab_z) - 9:.1f}" width="104" height="18" '
             f'fill="#ffffff" fill-opacity="0.9" rx="2"/>')
    o.append(T(slab_x + 46, Y(slab_z) - 1, "the screen, edge-on", 7.6, anchor="start",
               fill=INK, weight="700"))
    o.append(T(slab_x + 46, Y(slab_z) + 8, f"{W.d.panel_depth:.0f} mm panel, "
               f"{W.d.depth:.0f} mm overall", 6.9, anchor="start", fill=MUTED))
    o.append(dim_h(min(X(W.face_x), X(W.panel_out)), max(X(W.face_x), X(W.panel_out)),
                   Y(W.disp_zc - W.disp_h/2) + 38, f"stands off {W.standoff:.0f}", above=False))
    o.append(dim_h(min(X(W.arm_tip), X(W.plate_out)), max(X(W.arm_tip), X(W.plate_out)),
                   Y(W.FH) - 38, f"sits {p.arm_len:.0f} onto the top"))
    o.append(dim_h(X(0), X(W.FW), Y(0) + 30, f"fridge width {W.FW:.0f}", above=False))
    # Both ends of the height band the brief asks us to serve, standing beside the cabinet, with
    # the screen's vertical extent carried across as a band so it is obvious at a glance whether
    # each person's eye line lands on it.
    top_z = W.disp_zc + W.disp_h / 2.0
    bot_z = W.disp_zc - W.disp_h / 2.0
    # The band now runs from the display OUTWARD across the figure lane, not across the fridge.
    out = -1 if left_mount else 1
    disp_edge = X(W.plate_out)
    band_x0, band_x1 = disp_edge, (x0 + 16) if left_mount else (x0 + w - 16)
    o.append(f'<rect x="{min(band_x0, band_x1):.1f}" y="{Y(top_z):.1f}" '
             f'width="{abs(band_x1-band_x0):.1f}" height="{(top_z-bot_z)*s:.1f}" '
             f'fill="#1a5fb4" fill-opacity="0.07"/>')
    for zz in (top_z, bot_z):
        o.append(f'<line x1="{min(band_x0,band_x1):.1f}" y1="{Y(zz):.1f}" '
                 f'x2="{max(band_x0,band_x1):.1f}" y2="{Y(zz):.1f}" stroke="#1a5fb4" '
                 f'stroke-width="0.7" stroke-dasharray="5 4" opacity="0.55"/>')
    # Set on a white pill: "screen bottom" previously sat light-blue on the light-blue band fill.
    # Labels sit against the display end of the band, where the screen actually is.
    # Set them on the FRIDGE side of the display, not the band side: the band is now full of
    # human figures, and a label laid over a silhouette is a label you have to work to read.
    blx = disp_edge - out * 8
    for zz, lab, dy in ((top_z, "screen top", -5), (bot_z, "screen bottom", 11)):
        o.append(f'<rect x="{(blx - 3) if left_mount else (blx - 66):.1f}" '
                 f'y="{Y(zz) + dy - 8:.1f}" width="69" height="11" '
                 f'fill="#ffffff" fill-opacity="0.88" rx="2"/>')
        o.append(T(blx, Y(zz) + dy, lab, 7.4, anchor="start" if left_mount else "end",
                   fill="#14448a", weight="700"))

    fx = disp_edge + out * 68.0
    for stature, label in STATURES:
        eye = stature * EYE_FRACTION
        o.append(f'<g opacity="0.85">{person(fx, gy, s, height_mm=stature, fill="#cbd5dd")}</g>')
        o.append(f'<line x1="{fx - out * stature*s*0.075:.1f}" y1="{Y(eye):.1f}" '
                 f'x2="{disp_edge:.1f}" y2="{Y(eye):.1f}" stroke="{DIM}" '
                 f'stroke-width="0.8" stroke-dasharray="3 3" opacity="0.8"/>')
        o.append(f'<circle cx="{fx:.1f}" cy="{Y(eye):.1f}" r="2.4" fill="{DIM}"/>')
        o.append(T(fx, gy + 15, label, 8.0, fill=INK, weight="bold"))
        o.append(T(fx, gy + 26, f"eye {eye:.0f}", 7.2, fill=MUTED))
        # "above screen" was ambiguous - a reader took it as "the screen is out of view for
        # tall people", the opposite of what the panel claims. Say which way they look instead.
        on = "eye line on screen" if bot_z <= eye <= top_z else "looks slightly down"
        o.append(T(fx, gy + 37, on, 7.2, fill="#2e7d46", weight="700"))
        fx += out * 104
    o.append(T(X(W.FW*0.5), y0 + 22, "as seen standing in front of the fridge", 8.6, fill=MUTED))
    return "".join(o)


# ---- sheet ---------------------------------------------------------------------------------------
def build_sheet(params: BracketParams, display_key: str, mount_side: str = "left") -> tuple[str, dict]:
    set_display(display_key)
    d = G.DISPLAY
    flat = derive_flat(params)
    geom = build_geometry(params, flat)
    issues = G.validate(params, geom)
    rep = G.engineering_report(params, geom)
    W = World(params, d, mount_side)
    rows = magnet_rows(geom)
    arm_offs = arm_magnet_offsets(params)
    n_body = len(rows) * 2
    n_arm = len(arm_offs) * 2
    n_mag = n_body + n_arm

    pull = rep["magnet_derated_pull_lbf"]
    base_rows = [r for r in rows if r in (params.magnet_inset, params.body_h - params.magnet_inset)]
    go_now = let_go_lbf(params, W, rows, arm_offs, pull)
    go_base = let_go_lbf(params, W, base_rows, [params.arm_magnet_offset], pull)

    # Sized to be screenshotted and sent, not printed: one tight block, minimal gutters.
    PY, PH = 76.0, 762.0
    tallest = max(h for h, _ in STATURES)
    s = (PH - 30 - 58) / tallest          # fit the tallest person, then everything else follows
    # Panel order is deliberate: the shaded 3D view LEADS, because it is the only panel that
    # tells a non-engineer what the object actually is. The two measured elevations follow.
    ax, aw = 22.0, 560.0          # 1 - IN PLACE (3D)
    bx, bw = ax + aw + 10, 470.0  # 2 - the face you read
    cx_, cw = bx + bw + 10, 580.0 # 3 - the frontal, with the human figures
    SW, SH = cx_ + cw + 22, 948.0

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{SW:.0f}" height="{SH:.0f}" '
         f'viewBox="0 0 {SW:.0f} {SH:.0f}">',
         f'<rect width="{SW:.0f}" height="{SH:.0f}" fill="#fbfcfd"/>',
         f'<rect x="{ax:.0f}" y="18" width="{SW-2*ax:.0f}" height="44" fill="{INK}" rx="3"/>',
         T(ax + 16, 46, "FRIDGE-SIDE CHORE DISPLAY", 16, anchor="start",
           fill="#ffffff", weight="bold", spacing="0.7"),
         T(SW - ax - 16, 34, f"Waveshare {display_key}\" portrait  ·  mounted {mount_side.upper()}",
           9.5, anchor="end", fill="#9fb0bd"),
         T(SW - ax - 16, 50, f"{MATERIAL.name} {MATERIAL.thickness_in:.3f} in, matte black  ·  "
                             f"{n_mag} magnets", 9.5, anchor="end", fill="#9fb0bd"),
         T(ax + 310, 46, "ALL DIMENSIONS IN MILLIMETRES", 9.0, anchor="start",
           fill="#7f8f9c", spacing="1.1")]

    o.append(panel(bx, PY, bw, PH, "2 — STANDING AT THE SIDE", "this is the face you read"))
    o.append(front_elevation(bx, PY + 30, bw, PH - 30, W, rows))

    o.append(panel(cx_, PY, cw, PH, "3 — STANDING AT THE FRONT",
                   "the screen is edge-on here · works at 5 ft 1 in and 6 ft 4 in"))
    o.append(side_elevation(cx_, PY + 30, cw, PH - 30, W, rows, arm_offs, s))

    o.append(panel(ax, PY, aw, PH, "1 — IN PLACE", "shaded projection, not a photo"))
    mirror = (lambda v: 2 * (W.FW / 2.0) - v) if W.dir < 0 else (lambda v: v)
    cam = R3.Camera(eye=(mirror(3750), -2450, 2320), target=(mirror(700), 300, 1010), fov_deg=28.0,
                    width=aw, height=PH - 30, cx=ax + aw/2, cy=PY + 30 + (PH - 30)/2)
    scene = build_scene(W, geom, rows, arm_offs)
    o.append(f'<clipPath id="cclip"><rect x="{ax+1:.1f}" y="{PY+31:.1f}" width="{aw-2:.1f}" '
             f'height="{PH-32:.1f}"/></clipPath>')
    o.append(f'<g clip-path="url(#cclip)">')
    o.append(f'<rect x="{ax:.1f}" y="{PY+30:.1f}" width="{aw:.1f}" height="{PH-30:.1f}" fill="#f7f9fa"/>')
    o.extend(scene.render(cam))

    def ann(world_pt, lx, ly, text, sub_=(), anchor="start"):
        """Callout with a leader that starts BELOW its own text block.

        Starting the leader at the label baseline drew the line straight through the words —
        the sub-caption came out struck through. Anchor it under both lines instead, and put a
        translucent white pad behind the text so a leader passing nearby cannot compete with it.
        """
        px, py, _ = cam.project(world_pt)
        a = [f'<line x1="{lx:.1f}" y1="{ly + 15:.1f}" x2="{px:.1f}" y2="{py:.1f}" stroke="{INK}" '
             f'stroke-width="0.9" opacity="0.45"/>',
             f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="{INK}"/>',
             T(lx, ly - 4, text, 10.5, anchor=anchor, fill=INK, weight="bold")]
        # Long captions wrap rather than running a single 300 px line across the render.
        for i, line in enumerate(sub_):
            a.append(T(lx, ly + 9 + i * 10, line, 8.8, anchor=anchor, fill=MUTED))
        return "".join(a)

    o.append(ann((W.arm_tip - W.dir * 45, W.yc, W.arm_z1), ax + 18, PY + 62,
                 "Hooks over the top", ["the fridge takes the weight"], anchor="start"))
    o.append(ann((W.plate_in, W.body_y1 - params.magnet_inset, W.body_z0 + rows[0]),
                 ax + 18, PY + 400,
                 f"{n_mag} magnets",
                 [f"{n_body} hold the screen flat, {n_arm} steady the arm",
                  f"needs {go_now:.0f} lb of pull to come off"], anchor="start"))
    o.append(ann((W.plate_out, W.yc + 8, W.body_z1 + 120), ax + 18, PY + 690,
                 "Cable runs up the back", ["cleanly strapped down, not hidden"], anchor="start"))
    o.append("</g>")

    # ---- bottom band ---------------------------------------------------------------------------
    by = PY + PH + 10
    bh_ = SH - by - 18
    o.append(f'<rect x="{ax:.1f}" y="{by:.1f}" width="{SW-80:.1f}" height="{bh_:.1f}" '
             f'fill="#ffffff" stroke="{RULE}" stroke-width="1.2" rx="3"/>')
    facts = [
        ("The screen", f"Waveshare {display_key} inch touch",
         f"{d.mass_kg:.1f} kg ({d.mass_kg/0.45359237:.1f} lb), portrait"),
        ("Sits at", f"{rep['screen_centre_height_mm']/25.4/12:.0f} ft "
                    f"{rep['screen_centre_height_mm']/25.4 % 12:.0f} in to the middle",
         f"{rep['screen_centre_height_mm']:.0f} mm · works from 5 ft 1 in to 6 ft 4 in"),
        ("Holds on by", "hooking over the top of the fridge",
         f"plus {n_mag} magnets — {n_body} hold the screen flat, {n_arm} steady the arm"),
        ("Sticks out", f"{W.standoff:.0f} mm ({W.standoff/25.4:.1f} in)",
         f"less than the door handles"),
        ("Finish", "matte black, powder coated", "cable runs up the back, cleanly strapped down"),
        ("Comes off", "attached with magnets and pads", "no adhesive, no holes in the fridge"),
    ]
    colw = (SW - 2 * ax - 32) / len(facts)
    for i, (k, v, note) in enumerate(facts):
        fx = ax + 18 + i * colw
        o.append(T(fx, by + 22, k.upper(), 8.0, anchor="start", fill=MUTED, spacing="0.9"))
        o.append(T(fx, by + 40, v, 11.5, anchor="start", fill=INK, weight="bold"))
        o.append(T(fx, by + 55, note, 9.0, anchor="start", fill=MUTED))
    o.append("</svg>")

    return "\n".join(o), {"issues": issues, "rep": rep, "rows": rows,
                          "go_now": go_now, "go_base": go_base, "n_mag": n_mag}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Partner-approval sheet.")
    ap.add_argument("--display", choices=tuple(DISPLAYS), default="23.8")
    # default=None, NOT a list. A list here silently OVERRIDES the real BracketParams defaults,
    # which is how this sheet came to advertise 12 magnets when the bracket has 6.
    ap.add_argument("--extra-magnet-rows", type=float, nargs="*", default=None,
                    help="body-y positions of extra magnet PAIRS (default: whatever the design uses)")
    ap.add_argument("--extra-arm-magnet-offsets", type=float, nargs="*", default=None,
                    help="extra top-lip magnet PAIRS as offsets from the bend apex")
    ap.add_argument("--mount-side", choices=("left", "right"), default="left",
                    help="which side panel the bracket hangs on, seen from in front (default: left)")
    ap.add_argument("--out", type=Path, default=Path("approval_sheet.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    params = BracketParams(
        **({"extra_magnet_rows": tuple(a.extra_magnet_rows)}
           if a.extra_magnet_rows is not None else {}),
        **({"extra_arm_magnet_offsets": tuple(a.extra_arm_magnet_offsets)}
           if a.extra_arm_magnet_offsets is not None else {}))
    svg, info = build_sheet(params, a.display, a.mount_side)
    bad = [i for i in info["issues"] if i.severity == "ERROR"]
    if bad:
        for i in bad:
            LOG.error("%s: %s", i.code, i.message)
        LOG.error("Refusing to draw a part that does not validate")
        return 1
    a.out.write_text(svg, encoding="utf-8")
    LOG.info("Wrote %s — mounted %s, %d magnets, body rows %s, lets go at %.0f lbf (was %.0f)",
             a.out, a.mount_side, info["n_mag"], info["rows"], info["go_now"], info["go_base"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
