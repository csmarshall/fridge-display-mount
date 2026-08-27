#!/usr/bin/env python3
"""Minimal 3D scene projector: boxes -> shaded SVG faces.

No renderer is installed on this machine, so this is a small painter's-algorithm projector rather
than a ray tracer. It does perspective projection, outward-normal backface culling, Lambertian
shading against one key light plus a fill, and depth sorting by centroid range. Good enough to read
proportion and alignment from; it is NOT a photograph and must never be captioned as one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence

Vec = tuple[float, float, float]


def sub(a: Vec, b: Vec) -> Vec: return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def add(a: Vec, b: Vec) -> Vec: return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def mul(a: Vec, s: float) -> Vec: return (a[0]*s, a[1]*s, a[2]*s)
def dot(a: Vec, b: Vec) -> float: return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def cross(a: Vec, b: Vec) -> Vec:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def norm(a: Vec) -> Vec:
    m = math.sqrt(dot(a, a))
    return (a[0]/m, a[1]/m, a[2]/m) if m else (0.0, 0.0, 0.0)


def hex_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_hex(c: Sequence[float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v*255))):02x}" for v in c)


@dataclass
class Face:
    pts: list[Vec]
    colour: str
    tag: str = ""
    opacity: float = 1.0
    stroke: str | None = None
    shade: bool = True
    # Faces carrying flat UI are wound for the READER, not for the normal, so culling them by
    # winding would be wrong. Depth sorting alone places them correctly.
    cull: bool = True
    # Faces drawn as flat UI (the screen) carry their own painter, called with the projected quad.
    painter: object | None = None
    # Depth-sort bias, in world mm, subtracted from the face's range before sorting.
    #
    # Centroid-range sorting is only reliable when the competing quads are compact. A TALL quad
    # whose centroid sits high can beat a nearer but lower one by a few mm of range and draw
    # straight through it — which is exactly what the bracket neck did to the screen. Rather than
    # tune a magic number, geometry that is genuinely outboard declares HOW FAR outboard it is
    # (for the display that is the mounting standoff), so the bias is a derived dimension.
    bias: float = 0.0

    def centroid(self) -> Vec:
        n = len(self.pts)
        return (sum(p[0] for p in self.pts)/n, sum(p[1] for p in self.pts)/n, sum(p[2] for p in self.pts)/n)

    def normal(self) -> Vec:
        # Newell's method — robust for near-degenerate quads, unlike a single cross product.
        nx = ny = nz = 0.0
        for i, p in enumerate(self.pts):
            q = self.pts[(i+1) % len(self.pts)]
            nx += (p[1]-q[1])*(p[2]+q[2])
            ny += (p[2]-q[2])*(p[0]+q[0])
            nz += (p[0]-q[0])*(p[1]+q[1])
        return norm((nx, ny, nz))


def box(origin: Vec, size: Vec, colour: str, tag: str = "", opacity: float = 1.0,
        stroke: str | None = None, top: str | None = None, faces: str = "all") -> list[Face]:
    """Axis-aligned box as up to six outward-wound quads.

    `faces` may name a subset ("all", or any of x- x+ y- y+ z- z+ space separated) so interior
    faces that can never be seen are not emitted at all — fewer quads for the depth sort to get
    wrong.
    """
    x0, y0, z0 = origin
    dx, dy, dz = size
    x1, y1, z1 = x0+dx, y0+dy, z0+dz
    want = None if faces == "all" else set(faces.split())
    defs = {
        "x-": [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)],
        "x+": [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
        "y-": [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        "y+": [(x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0)],
        "z-": [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)],
        "z+": [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
    }
    out = []
    for key, pts in defs.items():
        if want is not None and key not in want:
            continue
        out.append(Face(list(pts), top if (key == "z+" and top) else colour, tag or key,
                        opacity, stroke))
    return out


def disc(centre: Vec, radius: float, axis: str, colour: str, segments: int = 28,
         tag: str = "") -> Face:
    """A flat circular face normal to `axis` ('x+', 'x-', 'z+'...), wound outward."""
    cx, cy, cz = centre
    pts: list[Vec] = []
    for i in range(segments):
        a = 2*math.pi*i/segments
        c, s = math.cos(a), math.sin(a)
        if axis[0] == "x":
            pts.append((cx, cy + radius*c, cz + radius*s))
        elif axis[0] == "y":
            pts.append((cx + radius*c, cy, cz + radius*s))
        else:
            pts.append((cx + radius*c, cy + radius*s, cz))
    if axis[0] == "x" and axis[1] == "-":
        pts.reverse()
    if axis[0] == "x" and axis[1] == "+":
        pts = [pts[0]] + pts[1:][::-1]
        pts.reverse()
    return Face(pts, colour, tag or "disc")


@dataclass
class Camera:
    eye: Vec
    target: Vec
    fov_deg: float = 32.0
    up: Vec = (0.0, 0.0, 1.0)
    width: float = 1000.0
    height: float = 800.0
    cx: float = 0.0
    cy: float = 0.0

    def __post_init__(self) -> None:
        self.f = norm(sub(self.target, self.eye))
        self.r = norm(cross(self.f, self.up))
        self.u = cross(self.r, self.f)
        self.focal = (self.height / 2.0) / math.tan(math.radians(self.fov_deg) / 2.0)

    def project(self, p: Vec) -> tuple[float, float, float]:
        d = sub(p, self.eye)
        z = dot(d, self.f)
        z = max(z, 1e-3)
        return (self.cx + self.focal * dot(d, self.r) / z,
                self.cy - self.focal * dot(d, self.u) / z,
                z)

    def range_to(self, p: Vec) -> float:
        return math.sqrt(dot(sub(p, self.eye), sub(p, self.eye)))


@dataclass
class Scene:
    faces: list[Face] = field(default_factory=list)
    key_light: Vec = (-0.38, -0.66, 0.72)
    ambient: float = 0.36
    key: float = 0.68
    fill_light: Vec = (0.80, -0.30, 0.10)
    fill: float = 0.17

    def add(self, faces: Iterable[Face]) -> None:
        self.faces.extend(faces)

    def shade(self, face: Face) -> str:
        base = hex_rgb(face.colour)
        if not face.shade:
            return face.colour
        n = face.normal()
        k = self.ambient
        k += self.key * max(0.0, dot(n, norm(self.key_light)))
        k += self.fill * max(0.0, dot(n, norm(self.fill_light)))
        return rgb_hex([min(1.0, c * k) for c in base])

    def render(self, cam: Camera, cull: bool = True) -> list[str]:
        drawable = []
        for f in self.faces:
            c = f.centroid()
            if cull and f.cull and dot(f.normal(), sub(c, cam.eye)) > 0.0:
                continue
            drawable.append((cam.range_to(c) - f.bias, f))
        drawable.sort(key=lambda t: -t[0])   # far to near
        out: list[str] = []
        for _, f in drawable:
            proj = [cam.project(p) for p in f.pts]
            pts = " ".join(f"{x:.2f},{y:.2f}" for x, y, _ in proj)
            stroke = (f' stroke="{f.stroke}" stroke-width="0.8" stroke-linejoin="round"'
                      if f.stroke else ' stroke="none"')
            op = f' fill-opacity="{f.opacity}"' if f.opacity < 1.0 else ""
            out.append(f'<polygon points="{pts}" fill="{self.shade(f)}"{op}{stroke}/>')
            if f.painter is not None:
                out.append(f.painter(proj))   # type: ignore[operator]
        return out


def quad_matrix(proj: Sequence[tuple[float, float, float]], w: float, h: float) -> str:
    """Affine matrix mapping local (0,0)-(w,h) onto the projected quad's first three corners.

    A perspective quad is not affine, so this shears slightly rather than matching exactly. At the
    camera distances used here the error across a screen face is under a pixel, and it lets flat UI
    be drawn in comfortable local coordinates instead of hand-projected point by point.
    """
    (x0, y0, _), (x1, y1, _), (x2, y2, _) = proj[0], proj[1], proj[3]
    a, b = (x1-x0)/w, (y1-y0)/w
    c, d = (x2-x0)/h, (y2-y0)/h
    return f"matrix({a:.5f} {b:.5f} {c:.5f} {d:.5f} {x0:.3f} {y0:.3f})"
