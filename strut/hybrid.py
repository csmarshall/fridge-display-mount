#!/usr/bin/env python3
"""THIRD DESIGN: the hook plate, with feet under it.

The hook already carried its load through the ARM bearing on the fridge top; its magnets only
ever held it flat. This adds struts and feet so the load can go to the FLOOR instead. It is
bought in two PHASES, and the plate is cut once for both:

    phase 1  ARM + MAGNETS      the hook as archived. The four BODY magnets are NOT optional:
                                with nothing else holding the bottom of the plate to the panel,
                                the display's overturning moment would swing it out about the
                                top corner. That is the hook's own invariant (CLAUDE.md 1.1: the
                                magnets resist peel and touch torsion). The four ARM magnets are
                                anti-walk insurance with zero load credit; their holes are cut,
                                they are not bought until the arm is seen to creep.
    phase 2  ARM + STRUTS       bought only if phase 1 proves too lively. Two slotted struts
                                bolt to the plate through TWO rows of holes bracketing the VESA,
                                and stand on the clamped-strut design's feet and lower clamp.
                                The magnets come OFF: the plate now sits on the strut backs at a
                                different standoff and the 11.51 mm magnets no longer meet the
                                panel.

THE PLATE IS THE HOOK GENERATOR'S OUTPUT, NOT A REDRAWING. Until 2026-09-01 this repo drew its
own "hook plate" with six holes — no magnet holes at all, so phase 1 could not have been built
from the file that was quoted. Now generate_hybrid.py calls the hook repo's generate_bracket.py
at this gauge with `--strut-bolts`, and the bolt rows are chosen HERE from that generator's own
params JSON (its holes, windows and magnet discs), so the knowledge of what a bolt must clear
has one home. The generator re-validates whatever it is given and the hook repo's audit
accepts the result. The strut length that fits is a stock coincidence worth writing down
(see strut_overlap).
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

import bom as B
from concept_sheet import IN, Assembly, scs_bend_spec

LOG = logging.getLogger("hybrid")

# A36 / 1008 mild steel. Yield is SendCutSend's A36 figure, the same one the hook generator
# validates against; E is the textbook 200 GPa for carbon steel, which no vendor sheet argues with.
STEEL_YIELD_PSI = 36_000.0
STEEL_E_MPA = 200_000.0
STEEL_DENSITY_G_CC = 7.85
LBF_PER_KG = 2.2046226218
N_PER_LBF = 4.4482216

# Structural floors. SF 4 is what BRIEF.md 3b accepted for the foot at this gauge; 0.2 mm of
# screen-edge movement under a firm press is the "feels rigid" band thickness_study.py drew.
SF_FLOOR = 4.0
FEELS_RIGID_MM = 0.2

# The generated plate's params JSON — written by generate_hybrid.py via the project's own
# generate_bracket.py (one level up), which is the plate's one home.
PLATE_JSON = Path("dxf/H_hook_plate.json")


@dataclass(frozen=True)
class Hybrid:
    # --- from the archived hook design, unchanged ---
    fridge_h: float = 1743.07
    arm_reach: float = 180.0
    neck: float = 257.0
    body: float = 310.0
    body_w: float = 310.0
    arm_w: float = 190.0
    screen_centre: float = 1331.0
    # 0.119 in CRS, where the archived hook shipped at 0.187 in HRPO. The hook's own record
    # (generate_bracket.Material) says 0.187 was chosen "for HEFT and margin, not for
    # stiffness-you-can-feel": plate flex under a touch is 0.064 mm at 0.119 against 0.016 at
    # 0.187, neither perceptible, and the thicker gauge cost +$11.21. Run at 0.119 the hook
    # generator validates with neck SF 30x and body SF 34x (2026-09-01). What 0.119 buys here is
    # one gauge across the whole kit — plate, clamp and feet share a bend spec — and 2.1 kg less
    # hanging on the fridge top. structural() below re-checks it in BOTH phases; the earlier
    # comment "the feet take load off the plate" was wrong for phase 1, where there are no feet.
    plate_t: float = 0.119 * IN
    magnet_standoff: float = 11.51     # O48 pot magnet height = plate-to-panel gap in phase 1
    magnet_mass_kg: float = 1.27 / 8   # per magnet, ESTIMATE — no vendor publishes one (hook BOM)
    display_kg: float = 3.94           # Waveshare 23.8 in, published
    display_cg_from_box_face: float = 29.4   # hook generator: volume-weighted, 18 panel + 25 box
    spacer_len: float = 0.0            # M4 spacers between plate and display, as the hook built it
    press_lbf: float = 5.0             # the governing touch press, at the outer screen edge
    torsion_arm: float = 324.65 / 2.0  # half the portrait width — where the finger lands
    vesa: float = 100.0
    magnet_spacing: float = 246.0      # hook design, unchanged: 310 body, 32 inset
    magnet_disc: float = 48.02         # O48 pot magnet
    n_magnets_fitted: int = 4          # the four BODY magnets. Arm holes cut, magnets not bought.

    # --- what this design adds ---
    # 5 ft, not 4. A 4 ft strut put exactly ONE slot row inside the plate, 17.7 mm above its
    # bottom edge, and a plate held at one edge cantilevers 144 mm to the VESA: 0.876 mm of
    # screen-edge movement under a 5 lb press, four times the feel-rigid band and WORSE than
    # phase 1. A 5 ft strut reaches 38 mm above the plate top (hidden behind the display) and
    # puts six rows inside the plate, of which the lowest and highest CLEAR rows bracket the VESA.
    strut_ft: float = 5.0
    strut_w: float = 1.625 * IN
    strut_d: float = 0.8125 * IN
    slot_pitch: float = 2.0 * IN
    slot_len: float = 28.6
    # NOT the hook's 246 magnet spacing, which is where this started. At 246 the strut bolts sit
    # directly UNDER the lower magnet discs — 14.27 mm between centres against a 24.01 mm disc
    # radius — so the plate could carry magnets or struts but never both, which is the one thing
    # this design needs it to do. Derived from the clamped-strut design instead: it is the first
    # spacing that clears (32.65 mm centre-to-centre against 30.26 needed) AND it makes the foot
    # and lower clamp the SAME PARTS as that design, so the fallback kit needs no new tooling.
    strut_spacing: float = Assembly().strut_spacing
    part_width: float = 55.0           # same edge-margin rule as the clamp design
    # Filled in by the generator from the hook's params JSON (see pick_bolt_rows). Body y, i.e.
    # height above the plate's bottom edge. Empty until a plate has been generated.
    bolt_rows: tuple[float, ...] = ()

    # ------------------------------------------------------------------------- geometry
    @property
    def body_bottom(self) -> float:
        """Where the hook's plate stops. Everything about the feet follows from this."""
        return self.fridge_h - self.neck - self.body

    @property
    def strut_len(self) -> float:
        return self.strut_ft * 12.0 * IN

    @property
    def strut_overlap(self) -> float:
        """How far the strut reaches past the plate's bottom edge.

        A stock coincidence, not design: nothing made the hook's plate stop where a stock length
        lands. If the screen height ever moves, the neck moves, the plate bottom moves, and the
        rows have to be re-picked — which pick_bolt_rows does, and validate() refuses a plate
        whose rows no longer bracket the VESA.
        """
        return self.strut_len - self.body_bottom

    @property
    def strut_above_plate(self) -> float:
        """How far the strut top stands above the plate's top edge (hidden behind the display)."""
        return self.strut_len - (self.body_bottom + self.body)

    @property
    def candidate_rows(self) -> list[float]:
        """Every slot centre of a strut standing on the floor that falls inside the plate. Body y."""
        out, n = [], 0
        while True:
            z = 25.4 + n * self.slot_pitch
            if z > self.strut_len - 11.11:
                return out
            if self.body_bottom < z < self.body_bottom + self.body:
                out.append(z - self.body_bottom)
            n += 1

    @property
    def couple_arm(self) -> float:
        """Arm at the top, lowest bolt row at the bottom. That separation is what stops it tipping."""
        return self.fridge_h - (self.body_bottom + min(self.bolt_rows))

    @property
    def bend_radius(self) -> float:
        """Effective inside radius after forming, mm — SendCutSend's published figure."""
        return scs_bend_spec(self.plate_t).radius_in * IN

    @property
    def bend_deduction(self) -> float:
        """PUBLISHED by SendCutSend for this gauge; the same table Assembly reads.

        Until 2026-09-01 this was re-derived from an estimated 1T radius and K = 0.42, giving
        5.35 mm where the vendor says 4.97 — and the plate was quoted at that flat length.
        """
        return scs_bend_spec(self.plate_t).deduction_in * IN

    @property
    def flat_len(self) -> float:
        """Cross-check only: the hook generator's params JSON is the flat length's home."""
        return self.arm_reach + self.neck + self.body - self.bend_deduction

    # ------------------------------------------------------------------ the fitted stack, by phase
    @property
    def strut_standoff(self) -> float:
        """Plate-to-panel gap once the plate is bolted to the strut backs (phase 2).

        NESTED like the clamp design: the plate lives inside the clamp gap, behind the struts,
        and the display box passes between them. Derived from Assembly so it cannot disagree
        with the clamp sheets.
        """
        a = Assembly()
        return a.gap - a.plate_t

    @property
    def magnet_standoff_mismatch(self) -> float:
        """How far the magnets miss the panel with the struts on. Positive = magnets too tall."""
        return self.magnet_standoff - self.strut_standoff

    # --------------------------------------------------------------- the generated plate
    @classmethod
    def from_plate_json(cls, path: Path = PLATE_JSON, **overrides) -> "Hybrid":
        """The design as the last generated plate embodies it. Refuses to guess if none exists."""
        if not path.exists():
            raise SystemExit(f"{path} not found — run generate_hybrid.py first")
        p = json.loads(path.read_text(encoding="utf-8"))["params"]
        return cls(bolt_rows=tuple(p["strut_bolt_rows"]), **overrides)


def hook_generator_args(h: Hybrid) -> list[str]:
    """The hook generator's command line for this design, less the strut rows."""
    return ["--thickness", f"{h.plate_t / IN:.3f}", "--arm-length", f"{h.arm_reach}",
            "--neck-length", f"{h.neck}", "--body-width", f"{h.body_w}",
            "--body-height", f"{h.body}", "--neck-width", f"{h.arm_w}",
            "--fridge-height", f"{h.fridge_h}", "--press-force", f"{h.press_lbf}"]


def clear_rows(h: Hybrid, hook: dict) -> list[tuple[float, float, str]]:
    """Every candidate row with its worst clearance and what limits it, by the generator's rules.

    Reads the hook's params JSON: holes (1T web), windows (1T), magnet discs (the strut-bolt
    clearance the generator itself enforces), the centre vent and the body edges (2T). Positive
    clearance = the generator will accept the row. This mirrors validate() in generate_bracket
    so that the rows proposed are the rows accepted; the generator remains the arbiter.
    """
    p = hook["params"]
    t = hook["material"]["thickness_mm"]
    two_t = 2.0 * t
    r = p["strut_bolt_dia"] / 2.0
    disc_clear = p["strut_bolt_disc_clearance"]
    x0, y0, x1, y1 = hook["regions"]["body"]
    cx = (x0 + x1) / 2.0
    co = hook["center_opening"]
    out = []
    for row in h.candidate_rows:
        worst, why = math.inf, ""
        for sx in (-1, 1):
            bx = cx + sx * h.strut_spacing / 2.0
            checks = [(min(bx - x0, row - y0, x1 - bx, y1 - row) - r - two_t, "body edge")]
            for hole in hook["holes"]:
                web = math.hypot(bx - hole["x"], row - hole["y"]) - r - hole["dia"] / 2.0
                checks.append((web - t, f"{hole['tag']} hole"))
            for w in hook["windows"]:
                qx = abs(bx - w["cx"]) - (w["w"] / 2.0 - w["r"])
                qy = abs(row - w["cy"]) - (w["h"] / 2.0 - w["r"])
                d = math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - w["r"]
                checks.append((d - r - t, f"window {w['tag']}"))
            for d in hook["magnet_discs"]:
                gap = math.hypot(bx - d["x"], row - d["y"]) - d["dia"] / 2.0 - r
                checks.append((gap - disc_clear, f"{d['tag']} face"))
            checks.append((math.hypot(bx - co["x"], row - co["y"]) - co["dia"] / 2.0 - r - two_t,
                           "centre vent"))
            m, tag = min(checks)
            if m < worst:
                worst, why = m, tag
        out.append((row, worst, why))
        LOG.debug("candidate row %.2f: margin %+.2f (%s)", row, worst, why)
    return out


def pick_bolt_rows(h: Hybrid, hook: dict) -> tuple[float, ...]:
    """The lowest and the highest clear rows, which must bracket the VESA centre.

    Two rows as far apart as the plate allows make the plate a beam between supports rather than
    a cantilever off one edge — that is the whole reason for the 5 ft strut.
    """
    vesa_y = h.body / 2.0
    clear = [row for row, margin, _ in clear_rows(h, hook) if margin >= 0.0]
    below = [r for r in clear if r < vesa_y]
    above = [r for r in clear if r > vesa_y]
    if not below or not above:
        return tuple(clear[:1])
    return (min(below), max(above))


@dataclass(frozen=True)
class Structural:
    """The three numbers that decide whether this gauge is enough, for one fitted phase."""
    phase: str
    standoff: float               # plate to panel, mm
    hanging_lbf: float            # what the arm carries: display + plate (+ magnets)
    overturning_in_lbf: float
    neck_psi: float
    neck_sf: float
    torsion_in_lbf: float
    reaction_spacing: float       # what reacts the torsion: magnet or strut-bolt spacing
    force_per_reaction_lbf: float
    body_lever_mm: float          # cantilever length, or the span between bolt rows
    body_psi: float
    body_sf: float
    plate_flex_mm: float          # out-of-plane, at the load point
    screen_edge_mm: float         # amplified out to where the finger is
    model: str                    # "cantilever" or "beam between rows"

    @property
    def ok(self) -> bool:
        return (self.neck_sf >= SF_FLOOR and self.body_sf >= SF_FLOOR
                and self.screen_edge_mm < FEELS_RIGID_MM)


def structural(h: Hybrid, phase: str, plate_mass_kg: float) -> Structural:
    """Neck bending, body weak-axis bending and touch flex, by the hook generator's own model.

    Same formulas as generate_bracket.py / thickness_study.py so the answers can be compared:
    at 0.119 in the hook generator reports neck SF 30.3x and body SF 33.9x for the magnet phase.

    phase "magnets": plate on the magnets, torsion reacted across the 246 magnet spacing,
                     cantilever from the VESA screw out to the magnet.
    phase "struts":  plate on the strut backs, torsion reacted as a couple across the two
                     struts. With two bolt rows the strip between them is a BEAM loaded at the
                     VESA: delta = F a^2 b^2 / (3 E I L). With one row it is a cantilever.
    """
    t = h.plate_t
    display_lbf = h.display_kg * LBF_PER_KG
    if phase == "magnets":
        standoff = h.magnet_standoff
        extra_kg = h.n_magnets_fitted * h.magnet_mass_kg
        spacing = h.magnet_spacing
        strip_mm = h.magnet_disc
        lever_mm = spacing / 2.0 - h.vesa / 2.0
        second_moment = strip_mm * t ** 3 / 12.0
        force_per_reaction = h.press_lbf * (h.torsion_arm / IN) / (spacing / IN) / 2.0
        flex_mm = (force_per_reaction * N_PER_LBF * lever_mm ** 3
                   / (3.0 * STEEL_E_MPA * second_moment))
        body_moment_in_lbf = force_per_reaction * lever_mm / IN
        model = "cantilever"
    elif phase == "struts":
        standoff = h.strut_standoff
        extra_kg = 0.0
        spacing = h.strut_spacing
        strip_mm = h.strut_w
        second_moment = strip_mm * t ** 3 / 12.0
        force_per_reaction = h.press_lbf * (h.torsion_arm / IN) / (spacing / IN) / 2.0
        vesa_y = h.body / 2.0
        rows = sorted(h.bolt_rows)
        if len(rows) >= 2 and rows[0] < vesa_y < rows[-1]:
            a_mm, b_mm = vesa_y - rows[0], rows[-1] - vesa_y
            lever_mm = a_mm + b_mm
            flex_mm = (force_per_reaction * N_PER_LBF * a_mm ** 2 * b_mm ** 2
                       / (3.0 * STEEL_E_MPA * second_moment * lever_mm))
            body_moment_in_lbf = force_per_reaction * (a_mm * b_mm / lever_mm) / IN
            model = "beam between rows"
        else:
            nearest = min(rows, key=lambda r: abs(r - vesa_y)) if rows else 0.0
            lever_mm = math.hypot(spacing / 2.0 - h.vesa / 2.0, vesa_y - nearest)
            flex_mm = (force_per_reaction * N_PER_LBF * lever_mm ** 3
                       / (3.0 * STEEL_E_MPA * second_moment))
            body_moment_in_lbf = force_per_reaction * lever_mm / IN
            model = "cantilever"
    else:
        raise ValueError(phase)

    plate_lbf = (plate_mass_kg + extra_kg) * LBF_PER_KG
    display_cg = standoff + t + h.spacer_len + h.display_cg_from_box_face
    plate_cg = standoff + t / 2.0
    overturning_in_lbf = (display_lbf * display_cg + plate_lbf * plate_cg) / IN
    neck_z_in3 = (h.arm_w / IN) * (t / IN) ** 2 / 6.0
    neck_psi = overturning_in_lbf / neck_z_in3

    body_z_in3 = (strip_mm / IN) * (t / IN) ** 2 / 6.0
    body_psi = body_moment_in_lbf / body_z_in3
    screen_edge_mm = flex_mm * (h.torsion_arm / (spacing / 2.0))

    return Structural(
        phase=phase, standoff=standoff, hanging_lbf=display_lbf + plate_lbf,
        overturning_in_lbf=overturning_in_lbf, neck_psi=neck_psi,
        neck_sf=STEEL_YIELD_PSI / neck_psi, torsion_in_lbf=h.press_lbf * (h.torsion_arm / IN),
        reaction_spacing=spacing, force_per_reaction_lbf=force_per_reaction,
        body_lever_mm=lever_mm, body_psi=body_psi, body_sf=STEEL_YIELD_PSI / body_psi,
        plate_flex_mm=flex_mm, screen_edge_mm=screen_edge_mm, model=model,
    )


PHASES = ("magnets", "struts")


def validate(h: Hybrid, hook: dict) -> list[tuple[str, str, str]]:
    """Everything this repo adds to the hook generator's own validation. (severity, tag, msg).

    The generator has already refused any row that fouls a feature; these are the checks only
    the strut design knows about. ERRORs stop generate_hybrid writing anything.
    """
    issues: list[tuple[str, str, str]] = []

    def check(ok: bool, severity: str, tag: str, msg: str) -> None:
        if not ok:
            issues.append((severity, tag, msg))
        LOG.log(logging.DEBUG if ok else logging.WARNING, "check %s %s  %s",
                "ok     " if ok else severity, tag, msg)

    vesa_y = h.body / 2.0
    rows = sorted(h.bolt_rows)
    check(len(rows) >= 2 and rows[0] < vesa_y < rows[-1], "ERROR", "rows_bracket_vesa",
          f"bolt rows {list(rows)} do not bracket the VESA at {vesa_y:.1f} — the "
          f"{h.strut_ft:.0f} ft strut's slots no longer fit this plate (neck {h.neck:.0f})")
    flat_h = hook["flat"]["height_mm"]
    check(abs(flat_h - h.flat_len) < 0.01, "ERROR", "flat_length_home",
          f"hook generator flat {flat_h:.3f} vs this repo's {h.flat_len:.3f} — the two bend "
          f"tables disagree")
    plate_kg = hook["engineering"]["plate_mass_kg"]
    if rows:
        for phase in PHASES:
            s = structural(h, phase, plate_kg)
            check(s.neck_sf >= SF_FLOOR, "ERROR", f"neck_bending[{phase}]",
                  f"neck {s.neck_psi:.0f} psi, SF {s.neck_sf:.1f}x < {SF_FLOOR:.0f}x")
            check(s.body_sf >= SF_FLOOR, "ERROR", f"body_weak_axis[{phase}]",
                  f"body {s.body_psi:.0f} psi, SF {s.body_sf:.1f}x < {SF_FLOOR:.0f}x")
            check(s.screen_edge_mm < FEELS_RIGID_MM, "WARNING", f"touch_flex[{phase}]",
                  f"screen edge moves {s.screen_edge_mm:.3f} mm under {h.press_lbf:.0f} lb, "
                  f"outside the {FEELS_RIGID_MM} mm feels-rigid band")
    # The two phases are exclusive in DEPTH as well as in plan. Reported every time so nobody
    # fits the struts with the magnets still on and wonders why the plate rocks.
    check(abs(h.magnet_standoff_mismatch) < 0.5, "WARNING", "magnet_vs_strut_standoff",
          f"magnets stand the plate {h.magnet_standoff:.2f} mm off the panel, the struts "
          f"{h.strut_standoff:.2f} — {abs(h.magnet_standoff_mismatch):.2f} mm apart, so the "
          f"magnets come OFF when the struts go on")
    return issues


def fabricated(h: Hybrid, hook: dict) -> list[B.Fab]:
    a = Assembly()
    n_strut_holes = sum(1 for x in hook["holes"] if x["tag"] == "strut_bolt")
    return [
        B.Fab("H", "HOOK PLATE", 1, hook["flat"]["height_mm"], hook["flat"]["width_mm"], 1,
              f"the archived hook's {len(hook['holes']) - n_strut_holes} holes and "
              f"{len(hook['windows'])} windows, plus {n_strut_holes} x O{a.plate_bolt_dia:.1f} "
              f"strut bolts at {h.strut_spacing:.0f} centres in "
              f"{len(h.bolt_rows)} rows",
              "generate_bracket.py --strut-bolts, at 0.119 in"),
        B.Fab("B", "FOOT", a.n_feet, a.foot_leg + a.foot_rise - B.bend_deduction(a),
              a.foot_width, 1, f"1 slot {a.slot_len:.1f} long",
              "one per strut, per BRIEF.md Part B. UNCHANGED from the clamped-strut design"),
        B.Fab("A", "LOWER CLAMP", 1, a.clamp_leg + a.clamp_short - B.bend_deduction(a),
              a.clamp_width, 1, f"2 square holes 8.38 at {a.strut_spacing:.2f} centres",
              "ONE, not two — the hook does the top. Shares its bolts with the feet"),
    ]


def costed(h: Hybrid) -> list[tuple[str, str, float | None, str]]:
    """Design 3's lines, from the ONE price table (../prices.py). Nothing invented where unpriced."""
    from prices import P, quote_hybrid
    q = quote_hybrid(n_magnets=h.n_magnets_fitted, strut_ft=int(h.strut_ft))
    # Short names for the sheet's cost table; the full descriptions live in prices.py.
    SHORT = {"plate_119": "HOOK PLATE", "magnet": "MAGNETS", "jam_nut": "Jam nuts, pack",
             "washer_os": "Oversized washers, pack", "threadlocker": "Threadlocker",
             "primer": "Primer for threadlocker", "vesa_screws": "VESA screws, pack",
             "spacers": "M4 spacers", "foam_hook": "Foam roll 7/16 in", "velcro": "VELCRO roll",
             "foot": "FOOT", "clamp_bar_q1": "LOWER CLAMP", "strut_5ft": "STRUT 5 ft",
             "strut_4ft": "STRUT 4 ft", "elevator": "Elevator bolts, pack",
             "foam_3mm": "Foam 3 mm", "floor_pad": "Floor pads"}
    out = []
    for g in q.groups:
        for ln in g.lines:
            pr = ln.price
            nm = SHORT.get(ln.key, ln.item)
            if ln.qty != 1:
                nm += f" x{ln.qty:g}"
            out.append((nm, f"{pr.source}, {pr.date}" if pr.date else pr.source, ln.total, pr.note))
    return out


MAGNET_EACH_USD = __import__("prices").P["magnet"].unit   # kept for callers; the home is prices.py


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(message)s")
    h = Hybrid.from_plate_json()
    hook = json.loads(PLATE_JSON.read_text(encoding="utf-8"))
    print(f"\nHOOK + FEET — the third design\n")
    print(f"  plate bottom edge        {h.body_bottom:8.2f} mm above the floor")
    print(f"  strut {h.strut_ft:.0f} ft                {h.strut_len:8.2f}, "
          f"{h.strut_above_plate:.1f} above the plate top")
    print(f"  slot rows in the plate   {[round(r, 1) for r in h.candidate_rows]}")
    print(f"  rows CUT                 {[round(r, 2) for r in h.bolt_rows]}  (body y, VESA at "
          f"{h.body / 2:.0f})")
    print(f"  arm-to-bolt couple       {h.couple_arm:8.2f} mm\n")
    print(f"  flat plate               {hook['flat']['height_mm']:.2f} x "
          f"{hook['flat']['width_mm']:.0f}, 1 bend, deduction {h.bend_deduction:.2f} "
          f"(SendCutSend published, {h.plate_t / IN:.3f} in)")
    print(f"  plate mass               {hook['engineering']['plate_mass_kg']:.2f} kg\n")
    print(f"  {'phase':10} {'standoff':>8} {'hanging':>8} {'neck SF':>8} {'body SF':>8} "
          f"{'flex@edge':>10}  model")
    for phase in PHASES:
        s = structural(h, phase, hook["engineering"]["plate_mass_kg"])
        print(f"  {phase:10} {s.standoff:8.2f} {s.hanging_lbf:7.1f}lb {s.neck_sf:7.1f}x "
              f"{s.body_sf:7.1f}x {s.screen_edge_mm:9.3f}mm  {s.model} "
              f"{'ok' if s.ok else 'FAIL'}")
    print()
    for sev, tag, msg in validate(h, hook):
        print(f"  {sev:8} {tag:28} {msg}")
    tot = 0.0
    print(f"\n  {'item':32} {'cost':>10}   source")
    for nm, src, cost, note in costed(h):
        if cost:
            tot += cost
        print(f"  {nm:32} {('$'+format(cost,'.2f')) if cost else 'NOT PRICED':>10}   {src}")
    print(f"\n  everything priced ${tot:.2f} — see hybrid_overview.svg for the phase split")
    return 0


if __name__ == "__main__":
    sys.exit(main())
