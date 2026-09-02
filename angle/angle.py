#!/usr/bin/env python3
"""DESIGN 4 — the hook in stock aluminium. Model, validation, cut/drill files, audit.

Same load path as the hook: a CLIP bears on the fridge's top corner and carries all the weight;
two BARS hang from it down the side panel; magnets on the bars hold the assembly flat; a PLATE
across the bars carries the VESA. No custom laser part — three pieces of 6061 stock, drilled.

    CLIP    2 x 2 x 3/16 in angle, 12 in. One leg on the fridge top over foam, the other down the
            side. Four holes in the hanging leg take the bars.
    BARS    2 x 1/4 in flat bar, 24 in, two of them, 250 mm apart (the torsion floor is 240).
            Each carries two O36 K&J MM-C-36 male-stud magnets above and below the plate, and
            two 1/4-20 bolts to the plate.
    PLATE   3/16 x 5 in flat bar, 12 in long, across the bars. VESA 100 in the middle. FIVE inches,
            not eight: the display's rear box carries the Pi's fan at ~R82 on the box's vertical
            axis, and a plate taller than ~134 mm would blank it (CLAUDE.md 1.5). 5 in = 127 mm
            stops 3.5 mm short of the fan opening, and the VESA holes still clear its edge by 2T.

Two things follow from the geometry that a sketch hid:
  - The clip must live INSIDE the hinge-cover window (400 mm from the rear edge on the later
    reading). Centred on the case it would run 57 mm into the cover, so it is placed against the
    window with a 20 mm margin, and the display sits ~77 mm rearward of the case centre. The
    cover lifts off (Charles), so that can be recovered; the model reports it rather than hides it.
  - The standoff is the magnet height, 8 mm, so the pad is 5/16 in foam (7.94 mm) — in the pad
    band. That pad, not the O48's 7/16 in, goes everywhere design 4 touches paint.

Validate-then-write, as every generator here: refuses to write if any ERROR stands. Writes three
DXFs (the clip's hanging leg as a drill template, the bar, the plate) with params JSON in the
shape audit_dxf.py expects, then audits each.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ezdxf                          # noqa: E402

import audit_dxf                      # noqa: E402
from bracket_common import LOG_LEVELS, configure_logging   # noqa: E402

LOG = logging.getLogger("angle")
IN = 25.4
LBF_PER_KG = 2.2046226218
N_PER_LBF = 4.4482216
AL_DENSITY_G_CC = 2.70
AL_YIELD_PSI = 35_000.0          # 6061-T6, conservative (spec minimum)
AL_E_MPA = 68_900.0
PAD_BAND = (-0.60, 0.30)         # pad thickness minus magnet standoff, mm (CLAUDE.md 1.5)
SF_FLOOR = 4.0
FEELS_RIGID_MM = 0.2
FOAM_PSI_LIMIT = 3.0             # 12 psi compresses the pad 25 %; keep the bearing far under it
OUT = Path(__file__).resolve().parent / "dxf"


@dataclass(frozen=True)
class Angle:
    # --- the appliance and the display, as the other designs have them ---
    fridge_h: float = 1743.07
    fridge_d: float = 609.6
    clear_window: float = 400.05     # rear edge to hinge cover, 2026-08-31 reading (the later one)
    cover_margin: float = 20.0       # kept back from the cover, as design 2 does
    fridge_corner_r: float = 12.0    # assumed, unmeasured
    screen_centre: float = 1331.0
    display_w: float = 324.65        # portrait
    display_h: float = 555.23
    display_kg: float = 3.94
    rear_box: float = 25.0
    box_w: float = 134.0             # portrait: short axis horizontal
    fan_r: float = 82.0              # SCALED off the drawing, on the box's vertical axis
    fan_dia: float = 30.0
    cg_from_box_face: float = 29.4
    vesa: float = 100.0
    vesa_hole_dia: float = 4.4
    press_lbf: float = 5.0
    grab_lbf: float = 20.0           # assumed abuse case on the bottom edge
    # --- stock ---
    clip_leg: float = 2.0 * IN
    clip_t: float = 0.1875 * IN     # 3/16, not 1/4: the bar bolts need 2T of edge inside a 2 in leg
    clip_len: float = 12.0 * IN
    clip_inside_r: float = 3.0       # extruded 6061 angle, typical
    bar_w: float = 2.0 * IN
    bar_t: float = 0.25 * IN
    bar_len: float = 24.0 * IN
    bar_spacing: float = 250.0
    plate_w: float = 12.0 * IN       # across the bars
    plate_h: float = 5.0 * IN        # the fan sets this
    plate_t: float = 0.1875 * IN    # 3/16: VESA holes at 13.5 mm from a 5 in bar's edge need 2T <= 13.5
    # --- magnets: K&J MM-C-36 ---
    magnet_dia: float = 36.0
    magnet_h: float = 8.0
    magnet_stud: str = "M6"
    magnet_hole_dia: float = 6.5
    magnet_rated_lbf: float = 90.4
    magnet_mass_kg: float = 0.058     # ESTIMATE — K&J list MM-C-32 at 26 g; scaled
    derate: float = 0.35
    magnet_gap_to_plate: float = 10.0
    # --- fasteners ---
    bolt_dia: float = 0.25 * IN      # 1/4-20, bars to clip and bars to plate
    bolt_hole_dia: float = 6.6
    clip_overlap: float = 2.0 * IN   # the bar runs the full leg and butts the clip's top leg
    # --- pads ---
    pad: float = 5.0 / 16.0 * IN     # 7.94 mm

    # ------------------------------------------------------------- placement
    @property
    def clip_from_rear(self) -> float:
        """Rear edge of the clip from the fridge's rear edge: as far forward as the cover allows."""
        return self.clear_window - self.cover_margin - self.clip_len

    @property
    def clip_centre_from_rear(self) -> float:
        return self.clip_from_rear + self.clip_len / 2.0

    @property
    def display_bias_rearward(self) -> float:
        """How far the screen centre sits behind the case's mid-depth."""
        return self.fridge_d / 2.0 - self.clip_centre_from_rear

    @property
    def hinge_margin(self) -> float:
        return self.clear_window - (self.clip_from_rear + self.clip_len)

    @property
    def plate_top(self) -> float:
        return self.screen_centre + self.plate_h / 2.0

    @property
    def plate_bottom(self) -> float:
        return self.screen_centre - self.plate_h / 2.0

    @property
    def magnet_rows(self) -> tuple[float, float]:
        return (self.plate_bottom - self.magnet_dia / 2.0 - self.magnet_gap_to_plate,
                self.plate_top + self.magnet_dia / 2.0 + self.magnet_gap_to_plate)

    @property
    def bar_top(self) -> float:
        return self.fridge_h - self.clip_leg + self.clip_overlap

    @property
    def bar_bottom(self) -> float:
        return self.bar_top - self.bar_len

    @property
    def bar_below_lower_magnet(self) -> float:
        return self.magnet_rows[0] - self.magnet_dia / 2.0 - self.bar_bottom

    @property
    def bar_above_display(self) -> float:
        """Bare bar visible above the display's top edge."""
        return self.fridge_h - (self.screen_centre + self.display_h / 2.0)

    @property
    def plate_fan_clearance(self) -> float:
        """Plate edge to the near edge of the fan opening, on the box's vertical axis."""
        return (self.fan_r - self.fan_dia / 2.0) - self.plate_h / 2.0

    @property
    def bar_inner_gap(self) -> float:
        return self.bar_spacing - self.bar_w

    @property
    def bar_edge_margin(self) -> float:
        return (self.bar_w - self.magnet_dia) / 2.0

    @property
    def clip_flat_gap(self) -> float:
        return 0.293 * max(0.0, self.fridge_corner_r - self.clip_inside_r)

    # ------------------------------------------------------------- masses and loads
    @property
    def hardware_kg(self) -> float:
        clip = (2 * self.clip_leg - self.clip_t) * self.clip_t * self.clip_len
        bars = 2 * self.bar_w * self.bar_t * self.bar_len
        plate = self.plate_w * self.plate_h * self.plate_t
        return (clip + bars + plate) * AL_DENSITY_G_CC / 1e6

    @property
    def hanging_lbf(self) -> float:
        return (self.display_kg + self.hardware_kg + 4 * self.magnet_mass_kg) * LBF_PER_KG

    @property
    def bearing_psi(self) -> float:
        return self.hanging_lbf / ((self.clip_leg / IN) * (self.clip_len / IN))

    @property
    def standoff(self) -> float:
        return self.magnet_h

    @property
    def cg_offset(self) -> float:
        return self.standoff + self.bar_t + self.plate_t + self.cg_from_box_face

    @property
    def display_face(self) -> float:
        return self.standoff + self.bar_t + self.plate_t + self.rear_box + 18.0

    @property
    def overturning_in_lbf(self) -> float:
        return self.hanging_lbf * self.cg_offset / IN

    @property
    def torsion_in_lbf(self) -> float:
        return self.press_lbf * (self.display_w / 2.0 / IN)

    @property
    def torsion_per_magnet_lbf(self) -> float:
        return self.torsion_in_lbf / (self.bar_spacing / IN) / 2.0

    @property
    def magnet_derated_lbf(self) -> float:
        return self.magnet_rated_lbf * self.derate

    @property
    def magnet_sf_touch(self) -> float:
        return self.magnet_derated_lbf / self.torsion_per_magnet_lbf

    @property
    def peel_lbf(self) -> float:
        """W x d / H on the lower pair, H from the clip corner to the lower row."""
        return self.overturning_in_lbf * IN / (self.fridge_h - self.magnet_rows[0])

    @property
    def magnet_sf_peel(self) -> float:
        return self.magnet_derated_lbf / (self.peel_lbf / 2.0)

    @property
    def magnet_sf_grab(self) -> float:
        return self.magnet_derated_lbf / (self.grab_lbf / 2.0)

    # ------------------------------------------------------------- stresses
    @property
    def bar_z_in3(self) -> float:
        return (self.bar_w / IN) * (self.bar_t / IN) ** 2 / 6.0

    @property
    def bar_overturning_psi(self) -> float:
        """The overturning moment reacted at the clip and the upper magnets, split over two bars."""
        return self.overturning_in_lbf / 2.0 / self.bar_z_in3

    @property
    def bar_overturning_sf(self) -> float:
        return AL_YIELD_PSI / self.bar_overturning_psi

    @property
    def bar_touch_flex_mm(self) -> float:
        """Each bar as a beam between its two magnets, the touch couple applied at the plate bolts.

        Load at mid-span of a simply supported beam: delta = F L^3 / (48 E I). Then amplified out
        to the screen edge by torsion_arm / (spacing/2), as the other designs report it.
        """
        f_n = self.torsion_per_magnet_lbf * 2.0 * N_PER_LBF      # the pair's share lands on one bar
        span = self.magnet_rows[1] - self.magnet_rows[0]
        i_mm4 = self.bar_w * self.bar_t ** 3 / 12.0
        flex = f_n * span ** 3 / (48.0 * AL_E_MPA * i_mm4)
        return flex * (self.display_w / 2.0) / (self.bar_spacing / 2.0)

    @property
    def bar_touch_psi(self) -> float:
        f = self.torsion_per_magnet_lbf * 2.0
        span_in = (self.magnet_rows[1] - self.magnet_rows[0]) / IN
        return f * span_in / 4.0 / self.bar_z_in3

    @property
    def plate_psi(self) -> float:
        """Plate weak axis: the VESA couple carried out to the bar bolts, strip = plate height."""
        lever_in = (self.bar_spacing / 2.0 - self.vesa / 2.0) / IN
        z = (self.plate_h / IN) * (self.plate_t / IN) ** 2 / 6.0
        return self.torsion_per_magnet_lbf * 2.0 * lever_in / z

    @property
    def clip_bolt_shear_psi(self) -> float:
        """Four 1/4 in bolts carry the hanging load in single shear at the clip."""
        area = math.pi / 4.0 * (self.bolt_dia / IN) ** 2
        return self.hanging_lbf / 4.0 / area

    # ------------------------------------------------------------- hole schedules, part coords
    def bar_holes(self) -> list[dict]:
        """Bar in its own coords: x across (0..bar_w), y along (0 at the BOTTOM end)."""
        cx = self.bar_w / 2.0
        y0 = self.bar_bottom
        holes = []
        for r in self.magnet_rows:
            holes.append(dict(tag="magnet", x=cx, y=r - y0, dia=self.magnet_hole_dia))
        for r in (self.screen_centre - self.plate_h / 2.0 + 25.0, self.screen_centre + self.plate_h / 2.0 - 25.0):
            holes.append(dict(tag="plate_bolt", x=cx, y=r - y0, dia=self.bolt_hole_dia))
        for r in (self.bar_top - 17.0, self.bar_top - 37.0):     # 17: hole edge 13.7 from the bar's top, >= 2T
            holes.append(dict(tag="clip_bolt", x=cx, y=r - y0, dia=self.bolt_hole_dia))
        return holes

    def plate_holes(self) -> list[dict]:
        cx, cy = self.plate_w / 2.0, self.plate_h / 2.0
        holes = [dict(tag="vesa", x=cx + sx * self.vesa / 2.0, y=cy + sy * self.vesa / 2.0, dia=self.vesa_hole_dia)
                 for sx in (-1, 1) for sy in (-1, 1)]
        for sx in (-1, 1):
            for yy in (25.0, self.plate_h - 25.0):
                holes.append(dict(tag="bar_bolt", x=cx + sx * self.bar_spacing / 2.0, y=yy, dia=self.bolt_hole_dia))
        return holes

    def clip_holes(self) -> list[dict]:
        """The hanging leg as a flat: x along the clip (0..clip_len), y down the leg (0 at the corner)."""
        cx = self.clip_len / 2.0
        holes = []
        for sx in (-1, 1):
            for yy in (self.clip_leg - 17.0, self.clip_leg - 37.0):      # same 17 / 37 from the top as the bar
                holes.append(dict(tag="bar_bolt", x=cx + sx * self.bar_spacing / 2.0, y=yy, dia=self.bolt_hole_dia))
        return holes

    def parts(self) -> dict[str, dict]:
        return {
            "D4_clip_leg": dict(w=self.clip_len, h=self.clip_leg, t=self.clip_t, holes=self.clip_holes(),
                                qty=1, stock="2 x 2 x 3/16 in 6061 angle, 12 in — drill the HANGING leg"),
            "D4_bar": dict(w=self.bar_w, h=self.bar_len, t=self.bar_t, holes=self.bar_holes(),
                           qty=2, stock="2 x 1/4 in 6061 flat bar, 24 in"),
            "D4_plate": dict(w=self.plate_w, h=self.plate_h, t=self.plate_t, holes=self.plate_holes(),
                             qty=1, stock="5 x 3/16 in 6061 flat bar, 12 in"),
        }


# ------------------------------------------------------------------------------ validation
def validate(a: Angle) -> list[tuple[str, str, str]]:
    issues: list[tuple[str, str, str]] = []

    def check(ok: bool, sev: str, tag: str, msg: str) -> None:
        if not ok:
            issues.append((sev, tag, msg))
        LOG.log(logging.DEBUG if ok else logging.WARNING, "check %s %s  %s", "ok     " if ok else sev, tag, msg)

    lo, hi = PAD_BAND
    ex = a.pad - a.standoff
    check(lo <= ex <= hi, "ERROR", "pad_band", f"pad {a.pad:.2f} vs standoff {a.standoff:.2f}: {ex:+.2f} mm, band {lo}/{hi}")
    check(a.bar_spacing >= 240.0, "ERROR", "torsion_floor", f"magnet spacing {a.bar_spacing:.0f} < 240 floor")
    check(a.bar_edge_margin >= 0.0, "ERROR", "magnet_on_bar", f"O{a.magnet_dia:.0f} disc on a {a.bar_w:.1f} bar: {a.bar_edge_margin:.1f} mm each side")
    check(a.hinge_margin >= 0.0, "ERROR", "hinge_cover", f"clip front edge {a.hinge_margin:.1f} mm from the hinge cover")
    check(a.clip_from_rear >= 0.0, "ERROR", "clip_rear", f"clip rear edge {a.clip_from_rear:.1f} mm from the fridge rear edge")
    check(a.plate_fan_clearance >= 0.0, "ERROR", "fan_opening", f"plate edge {a.plate_fan_clearance:.1f} mm from the Pi fan opening (R{a.fan_r:.0f}, O{a.fan_dia:.0f}, scaled ±5)")
    check(a.plate_fan_clearance >= 5.0, "WARNING", "fan_opening_margin", f"plate edge only {a.plate_fan_clearance:.1f} mm from the fan opening against a ±5 mm scaled figure — MEASURE the box")
    check(a.bar_inner_gap >= a.box_w, "ERROR", "box_between_bars", f"{a.bar_inner_gap:.1f} mm between the bars vs the {a.box_w:.0f} mm box")
    check(a.bearing_psi <= FOAM_PSI_LIMIT, "ERROR", "bearing", f"{a.bearing_psi:.2f} psi on the top foam, limit {FOAM_PSI_LIMIT}")
    check(a.clip_flat_gap * 1.2 <= a.pad, "ERROR", "corner_gap", f"corner lift {a.clip_flat_gap:.2f} x 1.2 vs pad {a.pad:.2f}")
    check(a.bar_below_lower_magnet >= 10.0, "ERROR", "bar_length", f"bar ends {a.bar_below_lower_magnet:.1f} mm below the lower magnet disc")
    check(a.magnet_sf_touch >= SF_FLOOR, "ERROR", "magnet_touch", f"SF {a.magnet_sf_touch:.1f}x on touch")
    check(a.magnet_sf_peel >= SF_FLOOR, "ERROR", "magnet_peel", f"SF {a.magnet_sf_peel:.1f}x on peel")
    check(a.magnet_sf_grab >= 2.0, "WARNING", "magnet_grab", f"SF {a.magnet_sf_grab:.1f}x on a {a.grab_lbf:.0f} lb grab (assumed abuse case)")
    check(a.bar_overturning_sf >= SF_FLOOR, "ERROR", "bar_bending", f"bar {a.bar_overturning_psi:.0f} psi, SF {a.bar_overturning_sf:.1f}x")
    check(AL_YIELD_PSI / a.bar_touch_psi >= SF_FLOOR, "ERROR", "bar_touch", f"bar {a.bar_touch_psi:.0f} psi under the touch couple")
    check(AL_YIELD_PSI / a.plate_psi >= SF_FLOOR, "ERROR", "plate_bending", f"plate {a.plate_psi:.0f} psi")
    check(a.bar_touch_flex_mm < FEELS_RIGID_MM, "WARNING", "touch_flex", f"screen edge moves {a.bar_touch_flex_mm:.3f} mm under {a.press_lbf:.0f} lb")
    # holes: 2T to any edge, 1T web between holes, per part
    for name, part in a.parts().items():
        t = part["t"]
        for h in part["holes"]:
            edge = min(h["x"], h["y"], part["w"] - h["x"], part["h"] - h["y"]) - h["dia"] / 2.0
            check(edge >= 2.0 * t, "ERROR", f"hole_edge[{name}]", f"{h['tag']} at ({h['x']:.1f}, {h['y']:.1f}) is {edge:.1f} mm from the edge, needs {2 * t:.1f}")
            for o in part["holes"]:
                if o is h:
                    continue
                web = math.hypot(h["x"] - o["x"], h["y"] - o["y"]) - h["dia"] / 2.0 - o["dia"] / 2.0
                check(web >= t, "ERROR", f"hole_web[{name}]", f"{h['tag']} to {o['tag']}: {web:.1f} mm web, needs {t:.1f}")
    # the magnet disc must clear the plate bolts on the bar
    for h in a.bar_holes():
        if h["tag"] == "magnet":
            for o in a.bar_holes():
                if o["tag"] == "plate_bolt":
                    gap = abs(h["y"] - o["y"]) - a.magnet_dia / 2.0 - o["dia"] / 2.0
                    check(gap >= 2.0, "ERROR", "magnet_vs_plate_bolt", f"magnet face {gap:.1f} mm from a plate bolt")
    return issues


def report(a: Angle) -> dict:
    return dict(
        clip_from_rear_mm=a.clip_from_rear, display_bias_rearward_mm=a.display_bias_rearward,
        hinge_margin_mm=a.hinge_margin, magnet_rows_mm=list(a.magnet_rows), bar_top_mm=a.bar_top,
        bar_bottom_mm=a.bar_bottom, bar_above_display_mm=a.bar_above_display,
        plate_fan_clearance_mm=a.plate_fan_clearance, hardware_kg=a.hardware_kg,
        hanging_lbf=a.hanging_lbf, bearing_psi=a.bearing_psi, cg_offset_mm=a.cg_offset,
        display_face_mm=a.display_face, overturning_in_lbf=a.overturning_in_lbf,
        torsion_in_lbf=a.torsion_in_lbf, torsion_per_magnet_lbf=a.torsion_per_magnet_lbf,
        magnet_derated_lbf=a.magnet_derated_lbf, magnet_sf_touch=a.magnet_sf_touch,
        peel_lbf=a.peel_lbf, magnet_sf_peel=a.magnet_sf_peel, magnet_sf_grab=a.magnet_sf_grab,
        bar_overturning_psi=a.bar_overturning_psi, bar_overturning_sf=a.bar_overturning_sf,
        bar_touch_psi=a.bar_touch_psi, bar_touch_flex_mm=a.bar_touch_flex_mm,
        plate_psi=a.plate_psi, plate_sf=AL_YIELD_PSI / a.plate_psi,
        clip_bolt_shear_psi=a.clip_bolt_shear_psi, clip_flat_gap_mm=a.clip_flat_gap,
        pad_excess_mm=a.pad - a.standoff,
    )


# ------------------------------------------------------------------------------ files
def write_part(name: str, part: dict, out_dir: Path) -> tuple[Path, Path]:
    d = ezdxf.new("R2010", setup=True)
    d.header["$INSUNITS"] = 4
    msp = d.modelspace()
    w, h = part["w"], part["h"]
    msp.add_lwpolyline([(0, 0), (w, 0), (w, h), (0, h)], close=True)
    for hole in part["holes"]:
        msp.add_circle((hole["x"], hole["y"]), hole["dia"] / 2.0)
    dxf = out_dir / f"{name}.dxf"
    d.saveas(dxf)
    expected = dict(insunits=4, layers=["0"], lwpolyline_count=1, circle_count=len(part["holes"]),
                    bend_line_count=0, extents_mm=[0.0, 0.0, w, h],
                    hole_diameters_mm=sorted({round(x["dia"], 4) for x in part["holes"]}))
    js = out_dir / f"{name}.json"
    js.write_text(json.dumps(dict(part=name, stock=part["stock"], qty=part["qty"], thickness_mm=part["t"],
                                  holes=part["holes"], expected_dxf=expected), indent=2), encoding="utf-8")
    return dxf, js


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = ap.parse_args(argv)
    configure_logging(args.log_level)
    a = Angle()
    issues = validate(a)
    errors = [i for i in issues if i[0] == "ERROR"]
    for sev, tag, msg in issues:
        LOG.log(logging.ERROR if sev == "ERROR" else logging.WARNING, "[%s] %s", tag, msg)
    if errors:
        LOG.error("REFUSING TO WRITE: %d error(s)", len(errors))
        return 1
    r = report(a)
    LOG.info("clip %.0f in at %.0f-%.0f mm from the rear (display %.0f mm rearward of centre, %.0f mm to the cover)",
             a.clip_len / IN, a.clip_from_rear, a.clip_from_rear + a.clip_len, a.display_bias_rearward, a.hinge_margin)
    LOG.info("bars %.0f in x2 at %.0f centres, magnets at %.0f / %.0f; plate %.0f x %.0f; fan clearance %.1f mm",
             a.bar_len / IN, a.bar_spacing, *a.magnet_rows, a.plate_w, a.plate_h, a.plate_fan_clearance)
    LOG.info("hangs %.1f lb, %.2f psi on the top; magnet SF touch %.0fx / peel %.0fx / grab %.1fx; bar SF %.0fx; "
             "plate SF %.0fx; screen edge %.3f mm", a.hanging_lbf, a.bearing_psi, a.magnet_sf_touch, a.magnet_sf_peel,
             a.magnet_sf_grab, a.bar_overturning_sf, r["plate_sf"], a.bar_touch_flex_mm)
    if args.dry_run:
        LOG.info("--dry-run: validation passed, nothing written")
        return 0
    args.out_dir.mkdir(parents=True, exist_ok=True)
    rc = 0
    for name, part in a.parts().items():
        dxf, js = write_part(name, part, args.out_dir)
        rc |= audit_dxf.main(["--dxf", str(dxf), "--expect", str(js), "--log-level", "WARNING"])
        LOG.info("wrote %s (%d holes) — %s", dxf.name, len(part["holes"]), "audited" if rc == 0 else "AUDIT FAILED")
    (args.out_dir / "D4_params.json").write_text(
        json.dumps(dict(params=asdict(a), engineering=r, parts={k: dict(w=v["w"], h=v["h"], t=v["t"], qty=v["qty"],
                                                                        stock=v["stock"], holes=v["holes"])
                                                                for k, v in a.parts().items()},
                        issues=[dict(severity=s, tag=t, message=m) for s, t, m in issues]), indent=2),
        encoding="utf-8")
    return rc


if __name__ == "__main__":
    sys.exit(main())
