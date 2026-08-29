#!/usr/bin/env python3
"""Acceptance test for bracket_flat.dxf.

Reads the generated DXF back with no knowledge of the generator's internals beyond the
expectations recorded in bracket_params.json, and asserts everything SendCutSend's 2D upload
requires plus the geometry we intended. Exits non-zero on any failure.

Run this after every generation, before uploading anything.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from pathlib import Path
from typing import Sequence

import ezdxf
from ezdxf.math import bulge_to_arc

from bracket_common import (
    INSUNITS_MILLIMETERS,
    LOG_LEVELS,
    REQUIRED_LAYER,
    configure_logging,
)

LOG = logging.getLogger("audit")

# Entity types that can only ever represent an open contour in a 2D cut file. LINE is excluded
# when the part carries a bend line: that one LINE is not a cut path, it is the bend marker
# SendCutSend's app reads, and it is verified separately below.
OPEN_CONTOUR_TYPES = {"ARC", "SPLINE", "ELLIPSE", "POLYLINE"}
TOLERANCE_MM = 0.01


class Auditor:
    """Collects pass/fail results so a run reports every problem, not just the first."""

    def __init__(self) -> None:
        self.failures: list[str] = []
        self.checks = 0

    def assert_that(self, ok: bool, name: str, detail: str) -> bool:
        self.checks += 1
        if ok:
            LOG.debug("PASS %-26s %s", name, detail)
            return True
        self.failures.append(f"{name}: {detail}")
        LOG.error("FAIL %-26s %s", name, detail)
        return False


def lwpolyline_extents(entity) -> tuple[float, float, float, float]:
    """Bounding box of a bulged LWPOLYLINE, sampling arcs so bulges outside the vertex hull count."""
    points = [(p[0], p[1], p[4]) for p in entity.get_points(format="xyseb")]
    xs: list[float] = []
    ys: list[float] = []
    count = len(points)
    for i in range(count):
        x, y, bulge = points[i]
        xs.append(x)
        ys.append(y)
        if i == count - 1 and not entity.closed:
            break
        nx, ny, _ = points[(i + 1) % count]
        if abs(bulge) < 1e-12:
            continue
        center, start_angle, end_angle, radius = bulge_to_arc((x, y), (nx, ny), bulge)
        sweep = end_angle - start_angle
        if bulge > 0:
            while sweep <= 0:
                sweep += 2 * math.pi
        else:
            while sweep >= 0:
                sweep -= 2 * math.pi
        for step in range(1, 17):
            angle = start_angle + sweep * step / 16
            xs.append(center.x + radius * math.cos(angle))
            ys.append(center.y + radius * math.sin(angle))
    return min(xs), min(ys), max(xs), max(ys)


def audit(dxf_path: Path, expect_path: Path) -> int:
    LOG.info("Auditing %s against %s", dxf_path, expect_path)
    expected = json.loads(expect_path.read_text(encoding="utf-8"))["expected_dxf"]
    aud = Auditor()

    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    entities = list(msp)
    LOG.info("Loaded %d modelspace entities from DXF version %s", len(entities), doc.dxfversion)

    # --- units -----------------------------------------------------------------------
    insunits = doc.header.get("$INSUNITS", 0)
    aud.assert_that(
        insunits == expected["insunits"], "units",
        f"$INSUNITS = {insunits}, expected {expected['insunits']} (millimetres)",
    )

    # --- single layer ----------------------------------------------------------------
    used_layers = sorted({e.dxf.layer for e in entities})
    aud.assert_that(
        used_layers == expected["layers"], "single_layer",
        f"entities occupy layers {used_layers}, expected {expected['layers']}",
    )

    # --- entity mix / open contours --------------------------------------------------
    kinds: dict[str, int] = {}
    for entity in entities:
        kinds[entity.dxftype()] = kinds.get(entity.dxftype(), 0) + 1
    LOG.debug("entity census: %s", kinds)
    expected_bend_lines = expected.get("bend_line_count", 0)
    if not expected_bend_lines:
        OPEN_CONTOUR_TYPES.add("LINE")
    stray = sorted(set(kinds) & OPEN_CONTOUR_TYPES)
    aud.assert_that(
        not stray, "no_open_contours",
        f"found open-contour entity types {stray}; every cut path must be a closed "
        f"LWPOLYLINE or CIRCLE" if stray else "no LINE/ARC/SPLINE/ELLIPSE/POLYLINE entities",
    )
    allowed = {"LWPOLYLINE", "CIRCLE"} | ({"LINE"} if expected_bend_lines else set())
    unexpected = sorted(set(kinds) - allowed)
    aud.assert_that(
        not unexpected, "entity_types",
        f"unexpected entity types {unexpected} — annotation or stray geometry"
        if unexpected else f"only {sorted(allowed)} present",
    )

    polylines = [e for e in entities if e.dxftype() == "LWPOLYLINE"]
    circles = [e for e in entities if e.dxftype() == "CIRCLE"]
    open_polys = [e for e in polylines if not e.closed]
    aud.assert_that(
        not open_polys, "closed_polylines",
        f"{len(open_polys)} of {len(polylines)} LWPOLYLINEs have the closed flag clear"
        if open_polys else f"all {len(polylines)} LWPOLYLINEs closed",
    )
    aud.assert_that(
        len(polylines) == expected["lwpolyline_count"], "lwpolyline_count",
        f"{len(polylines)} LWPOLYLINEs, expected {expected['lwpolyline_count']}",
    )
    aud.assert_that(
        len(circles) == expected["circle_count"], "circle_count",
        f"{len(circles)} CIRCLEs, expected {expected['circle_count']}",
    )

    # --- bend line -------------------------------------------------------------------
    lines = [e for e in entities if e.dxftype() == "LINE"]
    aud.assert_that(
        len(lines) == expected_bend_lines, "bend_line_count",
        f"{len(lines)} LINE entities, expected {expected_bend_lines}",
    )
    if expected_bend_lines and len(lines) == expected_bend_lines:
        line = lines[0]
        start, end = line.dxf.start, line.dxf.end
        want_y = expected["bend_line_y_mm"]
        want_x0, want_x1 = expected["bend_line_x_range_mm"]
        aud.assert_that(
            abs(start.y - want_y) <= TOLERANCE_MM and abs(end.y - want_y) <= TOLERANCE_MM,
            "bend_line_position",
            f"bend line at y = ({start.y:.3f}, {end.y:.3f}), expected {want_y:.3f} mm",
        )
        got = sorted((start.x, end.x))
        aud.assert_that(
            abs(got[0] - want_x0) <= TOLERANCE_MM and abs(got[1] - want_x1) <= TOLERANCE_MM,
            "bend_line_span",
            f"bend line spans x {got[0]:.3f} to {got[1]:.3f}, expected {want_x0:.3f} to "
            f"{want_x1:.3f} mm (the full bend length, no more, no less)",
        )
        linetype = line.dxf.get("linetype", "BYLAYER")
        aud.assert_that(
            linetype.upper() == "DASHED", "bend_line_linetype",
            f"bend line linetype is {linetype!r}, expected 'DASHED' — SendCutSend reads a solid "
            f"line as a cut path, which would slice the part in half",
        )

    # --- extents ---------------------------------------------------------------------
    xs_min, ys_min, xs_max, ys_max = [], [], [], []
    for entity in polylines:
        x0, y0, x1, y1 = lwpolyline_extents(entity)
        xs_min.append(x0); ys_min.append(y0); xs_max.append(x1); ys_max.append(y1)
    # LINE entities are deliberately excluded: the bend line is a marker, not cut geometry, so it
    # must not widen the part's extents.
    for circle in circles:
        cx, cy, _ = circle.dxf.center
        r = circle.dxf.radius
        xs_min.append(cx - r); ys_min.append(cy - r); xs_max.append(cx + r); ys_max.append(cy + r)
    actual = (min(xs_min), min(ys_min), max(xs_max), max(ys_max))
    want = tuple(expected["extents_mm"])
    deltas = [abs(a - w) for a, w in zip(actual, want)]
    LOG.debug("extents actual=%s expected=%s deltas=%s",
              [round(v, 4) for v in actual], want, [round(d, 4) for d in deltas])
    aud.assert_that(
        max(deltas) <= TOLERANCE_MM, "extents",
        f"extents {tuple(round(v, 3) for v in actual)} mm vs expected "
        f"{tuple(round(v, 3) for v in want)} mm (max delta {max(deltas):.4f} mm)",
    )

    # --- hole diameters --------------------------------------------------------------
    found_dias = sorted({round(c.dxf.radius * 2.0, 4) for c in circles})
    want_dias = sorted(expected["hole_diameters_mm"])
    aud.assert_that(
        len(found_dias) == len(want_dias)
        and all(abs(a - b) <= TOLERANCE_MM for a, b in zip(found_dias, want_dias)),
        "hole_diameters",
        f"circle diameters {found_dias} mm, expected {want_dias} mm",
    )

    # --- interior features inside the outline bbox -----------------------------------
    outline = max(polylines, key=lambda e: (lambda b: (b[2] - b[0]) * (b[3] - b[1]))(lwpolyline_extents(e)))
    ox0, oy0, ox1, oy1 = lwpolyline_extents(outline)
    inside = True
    for circle in circles:
        cx, cy, _ = circle.dxf.center
        r = circle.dxf.radius
        if not (ox0 <= cx - r and cx + r <= ox1 and oy0 <= cy - r and cy + r <= oy1):
            inside = False
            LOG.error("circle at (%.2f, %.2f) r%.2f falls outside the outline bbox", cx, cy, r)
    for entity in polylines:
        if entity is outline:
            continue
        x0, y0, x1, y1 = lwpolyline_extents(entity)
        if not (ox0 <= x0 and x1 <= ox1 and oy0 <= y0 and y1 <= oy1):
            inside = False
            LOG.error("window bbox (%.2f, %.2f)-(%.2f, %.2f) falls outside the outline bbox", x0, y0, x1, y1)
    aud.assert_that(inside, "features_inside_outline", "every interior feature lies within the outline extents")

    # --- zero-length / degenerate geometry -------------------------------------------
    degenerate = [c for c in circles if c.dxf.radius <= 0.0]
    aud.assert_that(not degenerate, "positive_radii", f"{len(degenerate)} circle(s) with non-positive radius"
                    if degenerate else "all circle radii positive")

    LOG.info("Audit finished: %d checks, %d failure(s)", aud.checks, len(aud.failures))
    if aud.failures:
        for failure in aud.failures:
            LOG.error("  %s", failure)
        return 1
    LOG.info("ACCEPT: %s is compliant and matches the generated parameters", dxf_path)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Acceptance test for the generated bracket DXF.")
    p.add_argument("--dxf", type=Path, default=Path("bracket_flat.dxf"))
    p.add_argument("--expect", type=Path, default=Path("bracket_params.json"))
    p.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = p.parse_args(argv)
    configure_logging(args.log_level)
    if not args.dxf.exists():
        LOG.error("DXF not found: %s — run generate_bracket.py first", args.dxf)
        return 2
    if not args.expect.exists():
        LOG.error("Expectations file not found: %s — run generate_bracket.py first", args.expect)
        return 2
    return audit(args.dxf, args.expect)


if __name__ == "__main__":
    sys.exit(main())
