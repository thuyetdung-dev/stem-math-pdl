"""Engine dựng hình minh họa Toán bằng SVG.

Không dùng model sinh ảnh: mọi khối hình được vẽ bằng toán học nên tỉ lệ luôn
đúng theo số đo trong đề, chữ số luôn sắc nét và đúng dấu tiếng Việt.
"""

import math
import re

W, H = 1280, 720
COS30 = math.cos(math.radians(30))
SIN30 = 0.5

FONT = "'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"

C = {
    "ink": "#16261f",
    "line": "#1d2b24",
    "water": "#7cc4e8",
    "water_dark": "#4a9fcc",
    "water_top": "#a8dcf2",
    "glass": "#eaf6fc",
    "wood": "#c99a5c",
    "wood_dark": "#a2763d",
    "metal": "#c9d2cd",
    "metal_dark": "#9aa8a1",
    "sky": "#eef6f0",
    "ground": "#e6ddc6",
    "leaf": "#7fae7a",
    "leaf_dark": "#5d8c5b",
    "skin": "#f6d3b0",
    "hair": "#2b2118",
    "shirt": "#8fbfa8",
    "shorts": "#5c7f9c",
    "paper": "#ffffff",
    "banner": "#fbeec8",
}

UNITS = {"mm": 0.001, "cm": 0.01, "dm": 0.1, "m": 1.0, "km": 1000.0}


# ---------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------

def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def parse_len(raw):
    """'3m' -> 3.0 ; 'r = 10cm' -> 0.1 ; None -> None (quy về mét)."""
    if raw is None:
        return None
    match = re.search(r"([\d]+(?:[.,]\d+)?)\s*(mm|cm|dm|km|m)?", str(raw))
    if not match:
        return None
    value = float(match.group(1).replace(",", "."))
    return value * UNITS.get(match.group(2) or "m", 1.0)


def ratios(values, floor=0.3):
    """Chuẩn hóa các số đo về tỉ lệ tương đối, chặn dưới để hình không bẹp."""
    clean = [v for v in values if v]
    if not clean:
        return [1.0 for _ in values]
    top = max(clean)
    return [max(floor, (v / top)) if v else 0.6 for v in values]


def iso(x, y, z):
    return ((x - z) * COS30, (x + z) * SIN30 - y)


def fit(points, cx, cy, max_w, max_h, bottom=None):
    """Đưa tập điểm thô vào khung, giữ nguyên tỉ lệ. bottom: neo đáy hình xuống mặt đất."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    span_x = max(max(xs) - min(xs), 1e-6)
    span_y = max(max(ys) - min(ys), 1e-6)
    s = min(max_w / span_x, max_h / span_y)
    ox = cx - (min(xs) + max(xs)) / 2 * s
    oy = (bottom - max(ys) * s) if bottom is not None else cy - (min(ys) + max(ys)) / 2 * s
    return (lambda p: (ox + p[0] * s, oy + p[1] * s)), s


def poly(points, fill, opacity=1.0, stroke=None, width=2.4):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    stroke = stroke or C["line"]
    return (f'<polygon points="{d}" fill="{fill}" fill-opacity="{opacity}" '
            f'stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round"/>')


def label(x, y, text, size=27, weight=700, anchor="middle", fill=None, rotate=0):
    """Vẽ chữ với viền trắng dựng thành phần tử riêng để mọi trình duyệt đều hiện đúng."""
    fill = fill or C["ink"]
    transform = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate else ""
    common = (f'x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
              f'font-weight="{weight}" text-anchor="{anchor}" dominant-baseline="central"')
    safe = esc(text)
    return (f'<text {common} fill="none" stroke="#ffffff" stroke-width="{min(size * 0.24, 8):.1f}" '
            f'stroke-linejoin="round"{transform}>{safe}</text>'
            f'<text {common} fill="{fill}"{transform}>{safe}</text>')


def dim_line(p1, p2, away_from, text, offset=40, size=26):
    """Đường kích thước hai đầu mũi tên, tự đẩy ra phía ngoài hình."""
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1
    nx, ny = -dy / length, dx / length
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    if (mx + nx - away_from[0]) ** 2 + (my + ny - away_from[1]) ** 2 < \
       (mx - nx - away_from[0]) ** 2 + (my - ny - away_from[1]) ** 2:
        nx, ny = -nx, -ny

    ax, ay = x1 + nx * offset, y1 + ny * offset
    bx, by = x2 + nx * offset, y2 + ny * offset
    ext = 7
    out = [
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{ax + nx * ext:.1f}" y2="{ay + ny * ext:.1f}" '
        f'stroke="{C["line"]}" stroke-width="1.6" stroke-dasharray="5 4"/>',
        f'<line x1="{x2:.1f}" y1="{y2:.1f}" x2="{bx + nx * ext:.1f}" y2="{by + ny * ext:.1f}" '
        f'stroke="{C["line"]}" stroke-width="1.6" stroke-dasharray="5 4"/>',
        f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{C["line"]}" '
        f'stroke-width="2.4" marker-start="url(#arrow)" marker-end="url(#arrow)"/>',
    ]
    if text:
        out.append(label((ax + bx) / 2 + nx * 20, (ay + by) / 2 + ny * 20, text, size=size))
    return "".join(out)


# ---------------------------------------------------------------------------
# Các khối hình
# ---------------------------------------------------------------------------

def draw_box(dims, cx, cy, max_w, max_h, filled=True, bottom=None, compact=False):
    """Hình hộp chữ nhật / hình lập phương, chiếu isometric."""
    L, D, Hh = ratios([parse_len(dims.get("length")),
                       parse_len(dims.get("width")),
                       parse_len(dims.get("height"))])
    raw = [iso(x, y, z) for x in (0, L) for y in (0, Hh) for z in (0, D)]
    tf, _ = fit(raw, cx, cy, max_w, max_h, bottom)
    P = lambda x, y, z: tf(iso(x, y, z))

    top = [P(0, Hh, 0), P(L, Hh, 0), P(L, Hh, D), P(0, Hh, D)]
    right = [P(L, Hh, 0), P(L, 0, 0), P(L, 0, D), P(L, Hh, D)]
    front = [P(0, Hh, D), P(L, Hh, D), P(L, 0, D), P(0, 0, D)]
    centroid = (cx, cy)

    body = C["water"] if filled else C["glass"]
    base = max(p[1] for p in (P(L, 0, D), P(L, 0, 0), P(0, 0, D)))
    svg = [
        f'<ellipse cx="{cx:.1f}" cy="{base + 10:.1f}" rx="{max_w * 0.42:.1f}" ry="14" '
        f'fill="{C["ink"]}" fill-opacity=".10"/>',
        poly(front, body, 0.72),
        poly(right, C["water_dark"] if filled else C["metal"], 0.68),
        poly(top, C["water_top"] if filled else C["paper"], 0.9),
    ]
    off, size = (16, 17) if compact else (44, 26)
    svg.append(dim_line(P(0, 0, D), P(L, 0, D), centroid, dims.get("length"), off, size))
    svg.append(dim_line(P(L, 0, D), P(L, 0, 0), centroid, dims.get("width"), off, size))
    svg.append(dim_line(P(L, Hh, 0), P(L, 0, 0), centroid, dims.get("height"), off, size))
    return "".join(svg)


def draw_cylinder(dims, cx, cy, max_w, max_h, cutaway=False, bottom=None):
    """Hình trụ đứng, có thể vẽ dạng cắt kỹ thuật cho khung phóng to."""
    r_val = parse_len(dims.get("radius")) or (parse_len(dims.get("diameter")) or 0) / 2
    h_val = parse_len(dims.get("height"))
    rr, hh = ratios([r_val, h_val], floor=0.35)
    aspect = (2 * rr) / max(hh, 1e-6)
    box_h = min(max_h, max_w / max(aspect, 1e-6))
    box_w = box_h * aspect
    ry = box_w * 0.17
    if bottom is not None:
        cy = bottom - box_h / 2 - ry

    left, right = cx - box_w / 2, cx + box_w / 2
    top, bottom = cy - box_h / 2, cy + box_h / 2
    fill = C["wood"] if not cutaway else C["wood"]

    svg = [
        f'<path d="M{left:.1f},{top:.1f} L{left:.1f},{bottom:.1f} '
        f'A{box_w / 2:.1f},{ry:.1f} 0 0 0 {right:.1f},{bottom:.1f} L{right:.1f},{top:.1f} Z" '
        f'fill="{fill}" stroke="{C["line"]}" stroke-width="2.6" stroke-linejoin="round"/>',
        f'<ellipse cx="{cx:.1f}" cy="{top:.1f}" rx="{box_w / 2:.1f}" ry="{ry:.1f}" '
        f'fill="{C["water_top"] if not cutaway else C["wood_dark"]}" stroke="{C["line"]}" stroke-width="2.6"/>',
    ]
    if cutaway:
        svg.append(f'<ellipse cx="{cx:.1f}" cy="{bottom:.1f}" rx="{box_w / 2:.1f}" ry="{ry:.1f}" '
                   f'fill="none" stroke="{C["line"]}" stroke-width="1.6" stroke-dasharray="6 5"/>')
        svg.append(f'<line x1="{cx:.1f}" y1="{top:.1f}" x2="{right:.1f}" y2="{top:.1f}" '
                   f'stroke="{C["line"]}" stroke-width="2.2" marker-end="url(#arrow)"/>')
        if dims.get("radius"):
            svg.append(label(cx, top - 34, dims["radius"], size=20))
        svg.append(dim_line((right + 14, top), (right + 14, bottom + ry), (cx - 999, cy),
                            dims.get("height"), 10, 20))
    else:
        if dims.get("diameter"):
            svg.append(dim_line((left, top), (right, top), (cx, cy + 999), dims["diameter"], 38))
        elif dims.get("radius"):
            svg.append(dim_line((cx, top), (right, top), (cx, cy + 999), dims["radius"], 38))
        svg.append(dim_line((right, top), (right, bottom), (cx - 999, cy), dims.get("height"), 30))
    return "".join(svg)


def draw_cone(dims, cx, cy, max_w, max_h, bottom=None):
    r_val = parse_len(dims.get("radius")) or (parse_len(dims.get("diameter")) or 0) / 2
    rr, hh = ratios([r_val, parse_len(dims.get("height"))], floor=0.35)
    aspect = (2 * rr) / max(hh, 1e-6)
    box_h = min(max_h, max_w / max(aspect, 1e-6))
    box_w = box_h * aspect
    ry = box_w * 0.17
    if bottom is not None:
        cy = bottom - box_h / 2 - ry
    left, right = cx - box_w / 2, cx + box_w / 2
    apex_y, base_y = cy - box_h / 2, cy + box_h / 2

    return "".join([
        f'<path d="M{cx:.1f},{apex_y:.1f} L{left:.1f},{base_y:.1f} '
        f'A{box_w / 2:.1f},{ry:.1f} 0 0 0 {right:.1f},{base_y:.1f} Z" fill="{C["water"]}" '
        f'fill-opacity=".78" stroke="{C["line"]}" stroke-width="2.6" stroke-linejoin="round"/>',
        f'<ellipse cx="{cx:.1f}" cy="{base_y:.1f}" rx="{box_w / 2:.1f}" ry="{ry:.1f}" fill="none" '
        f'stroke="{C["line"]}" stroke-width="1.6" stroke-dasharray="6 5"/>',
        f'<line x1="{cx:.1f}" y1="{apex_y:.1f}" x2="{cx:.1f}" y2="{base_y:.1f}" stroke="{C["line"]}" '
        f'stroke-width="1.6" stroke-dasharray="6 5"/>',
        dim_line((cx, base_y), (right, base_y), (cx, cy - 999), dims.get("radius"), 34),
        dim_line((right + 20, apex_y), (right + 20, base_y), (cx - 999, cy), dims.get("height"), 14),
    ])


def draw_sphere(dims, cx, cy, max_w, max_h):
    r = min(max_w, max_h) / 2
    return "".join([
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="url(#ball)" stroke="{C["line"]}" stroke-width="2.6"/>',
        f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{r:.1f}" ry="{r * 0.28:.1f}" fill="none" '
        f'stroke="{C["line"]}" stroke-width="1.6" stroke-dasharray="6 5"/>',
        dim_line((cx, cy), (cx + r, cy), (cx, cy - 999),
                 dims.get("radius") or dims.get("diameter"), 0),
    ])


def draw_pyramid(dims, cx, cy, max_w, max_h, bottom=None):
    L, Hh = ratios([parse_len(dims.get("length")) or parse_len(dims.get("width")),
                    parse_len(dims.get("height"))])
    raw = [iso(x, 0, z) for x in (0, L) for z in (0, L)] + [iso(L / 2, Hh, L / 2)]
    tf, _ = fit(raw, cx, cy, max_w, max_h, bottom)
    P = lambda x, y, z: tf(iso(x, y, z))
    apex = P(L / 2, Hh, L / 2)
    a, b, c, d = P(0, 0, 0), P(L, 0, 0), P(L, 0, L), P(0, 0, L)
    return "".join([
        poly([a, b, c, d], C["metal"], 0.5),
        poly([d, c, apex], C["water"], 0.7),
        poly([c, b, apex], C["water_dark"], 0.7),
        dim_line(d, c, (cx, cy), dims.get("length") or dims.get("width"), 42),
        dim_line((apex[0] + 40, apex[1]), (c[0] + 40, c[1]), (cx, cy), dims.get("height"), 12),
    ])


def draw_prism(dims, cx, cy, max_w, max_h, bottom=None):
    """Lăng trụ đứng đáy tam giác."""
    B, Hh, Dd = ratios([parse_len(dims.get("base")) or parse_len(dims.get("length")),
                        parse_len(dims.get("height")),
                        parse_len(dims.get("width")) or parse_len(dims.get("depth"))])
    raw = [iso(x, y, z) for x in (0, B) for y in (0, Hh) for z in (0, Dd)]
    tf, _ = fit(raw, cx, cy, max_w, max_h, bottom)
    P = lambda x, y, z: tf(iso(x, y, z))
    front = [P(0, 0, Dd), P(B, 0, Dd), P(B / 2, Hh, Dd)]
    back = [P(0, 0, 0), P(B, 0, 0), P(B / 2, Hh, 0)]
    return "".join([
        poly(back, C["metal"], 0.45),
        poly([back[1], front[1], front[2], back[2]], C["water_dark"], 0.65),
        poly(front, C["water"], 0.75),
        dim_line(front[0], front[1], (cx, cy), dims.get("base") or dims.get("length"), 40),
        dim_line((front[1][0] + 34, front[1][1]), (front[1][0] + 34, front[2][1]), (cx, cy),
                 dims.get("height"), 12),
    ])


def draw_rect2d(dims, cx, cy, max_w, max_h):
    L, Hh = ratios([parse_len(dims.get("length")), parse_len(dims.get("width")) or parse_len(dims.get("height"))])
    aspect = L / max(Hh, 1e-6)
    h = min(max_h, max_w / max(aspect, 1e-6))
    w = h * aspect
    x, y = cx - w / 2, cy - h / 2
    return "".join([
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="4" fill="{C["water"]}" '
        f'fill-opacity=".55" stroke="{C["line"]}" stroke-width="2.6"/>',
        dim_line((x, y + h), (x + w, y + h), (cx, cy), dims.get("length"), 40),
        dim_line((x + w, y), (x + w, y + h), (cx, cy), dims.get("width") or dims.get("height"), 40),
    ])


def draw_circle2d(dims, cx, cy, max_w, max_h):
    r = min(max_w, max_h) / 2
    return "".join([
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{C["water"]}" fill-opacity=".5" '
        f'stroke="{C["line"]}" stroke-width="2.6"/>',
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="{C["line"]}"/>',
        dim_line((cx, cy), (cx + r, cy), (cx, cy - 999), dims.get("radius") or dims.get("diameter"), 0),
    ])


SHAPES = {
    "box": draw_box, "cube": draw_box, "rectangular_prism": draw_box, "tank": draw_box,
    "cylinder": draw_cylinder, "cone": draw_cone, "sphere": draw_sphere,
    "pyramid": draw_pyramid, "prism": draw_prism,
    "rectangle": draw_rect2d, "square": draw_rect2d, "circle": draw_circle2d,
}


# ---------------------------------------------------------------------------
# Nhân vật và bối cảnh
# ---------------------------------------------------------------------------

def schoolboy(cx, ground_y, scale=1.0, holding=True, hold_type="ladle"):
    s = scale
    hip = ground_y - 118 * s
    shoulder = ground_y - 210 * s
    head_y = ground_y - 246 * s
    parts = [
        f'<ellipse cx="{cx:.1f}" cy="{ground_y:.1f}" rx="{46 * s:.1f}" ry="{9 * s:.1f}" fill="{C["ink"]}" fill-opacity=".13"/>',
        # chân
        f'<path d="M{cx - 17 * s:.1f},{hip:.1f} L{cx - 21 * s:.1f},{ground_y - 6 * s:.1f}" stroke="{C["skin"]}" '
        f'stroke-width="{20 * s:.1f}" stroke-linecap="round"/>',
        f'<path d="M{cx + 17 * s:.1f},{hip:.1f} L{cx + 22 * s:.1f},{ground_y - 6 * s:.1f}" stroke="{C["skin"]}" '
        f'stroke-width="{20 * s:.1f}" stroke-linecap="round"/>',
        f'<rect x="{cx - 34 * s:.1f}" y="{ground_y - 10 * s:.1f}" width="{28 * s:.1f}" height="{10 * s:.1f}" rx="{5 * s:.1f}" fill="{C["shorts"]}"/>',
        f'<rect x="{cx + 8 * s:.1f}" y="{ground_y - 10 * s:.1f}" width="{28 * s:.1f}" height="{10 * s:.1f}" rx="{5 * s:.1f}" fill="{C["shorts"]}"/>',
        # quần
        f'<path d="M{cx - 30 * s:.1f},{hip - 18 * s:.1f} L{cx + 30 * s:.1f},{hip - 18 * s:.1f} '
        f'L{cx + 27 * s:.1f},{hip + 18 * s:.1f} L{cx + 4 * s:.1f},{hip + 18 * s:.1f} L{cx:.1f},{hip - 12 * s:.1f} '
        f'L{cx - 4 * s:.1f},{hip + 18 * s:.1f} L{cx - 27 * s:.1f},{hip + 18 * s:.1f} Z" fill="{C["shorts"]}" '
        f'stroke="{C["line"]}" stroke-width="{2 * s:.1f}" stroke-linejoin="round"/>',
        # áo
        f'<path d="M{cx - 32 * s:.1f},{shoulder + 6 * s:.1f} Q{cx:.1f},{shoulder - 12 * s:.1f} {cx + 32 * s:.1f},{shoulder + 6 * s:.1f} '
        f'L{cx + 31 * s:.1f},{hip - 12 * s:.1f} L{cx - 31 * s:.1f},{hip - 12 * s:.1f} Z" fill="{C["shirt"]}" '
        f'stroke="{C["line"]}" stroke-width="{2.2 * s:.1f}" stroke-linejoin="round"/>',
        # tay trái buông
        f'<path d="M{cx - 30 * s:.1f},{shoulder + 16 * s:.1f} L{cx - 38 * s:.1f},{shoulder + 84 * s:.1f}" '
        f'stroke="{C["skin"]}" stroke-width="{16 * s:.1f}" stroke-linecap="round"/>',
        # đầu
        f'<circle cx="{cx:.1f}" cy="{head_y:.1f}" r="{34 * s:.1f}" fill="{C["skin"]}" stroke="{C["line"]}" stroke-width="{2.2 * s:.1f}"/>',
        f'<path d="M{cx - 35 * s:.1f},{head_y - 8 * s:.1f} Q{cx - 24 * s:.1f},{head_y - 42 * s:.1f} {cx + 2 * s:.1f},{head_y - 36 * s:.1f} '
        f'Q{cx + 30 * s:.1f},{head_y - 32 * s:.1f} {cx + 35 * s:.1f},{head_y - 6 * s:.1f} '
        f'Q{cx + 16 * s:.1f},{head_y - 22 * s:.1f} {cx - 12 * s:.1f},{head_y - 14 * s:.1f} Z" fill="{C["hair"]}"/>',
        f'<circle cx="{cx - 12 * s:.1f}" cy="{head_y + 2 * s:.1f}" r="{3.6 * s:.1f}" fill="{C["ink"]}"/>',
        f'<circle cx="{cx + 12 * s:.1f}" cy="{head_y + 2 * s:.1f}" r="{3.6 * s:.1f}" fill="{C["ink"]}"/>',
        f'<path d="M{cx - 8 * s:.1f},{head_y + 16 * s:.1f} Q{cx:.1f},{head_y + 24 * s:.1f} {cx + 8 * s:.1f},{head_y + 16 * s:.1f}" '
        f'fill="none" stroke="{C["ink"]}" stroke-width="{2.4 * s:.1f}" stroke-linecap="round"/>',
    ]
    if holding:
        # tay phải vươn ra cầm gáo
        parts.append(
            f'<path d="M{cx + 30 * s:.1f},{shoulder + 16 * s:.1f} L{cx + 74 * s:.1f},{shoulder + 54 * s:.1f}" '
            f'stroke="{C["skin"]}" stroke-width="{16 * s:.1f}" stroke-linecap="round"/>')
        if hold_type == "ladle":
            parts.append(
                f'<line x1="{cx + 66 * s:.1f}" y1="{shoulder + 50 * s:.1f}" x2="{cx + 116 * s:.1f}" y2="{shoulder + 96 * s:.1f}" '
                f'stroke="{C["wood_dark"]}" stroke-width="{7 * s:.1f}" stroke-linecap="round"/>')
        if hold_type == "ladle":
            parts.append(
                f'<path d="M{cx + 104 * s:.1f},{shoulder + 92 * s:.1f} l{34 * s:.1f},0 l{-5 * s:.1f},{26 * s:.1f} '
                f'l{-24 * s:.1f},0 Z" fill="{C["wood"]}" stroke="{C["line"]}" stroke-width="{2.2 * s:.1f}" stroke-linejoin="round"/>')
            parts.append(
                f'<ellipse cx="{cx + 121 * s:.1f}" cy="{shoulder + 92 * s:.1f}" rx="{17 * s:.1f}" ry="{5 * s:.1f}" '
                f'fill="{C["water_top"]}" stroke="{C["line"]}" stroke-width="{2 * s:.1f}"/>')
        else:
            parts.append(
                f'<rect x="{cx + 62 * s:.1f}" y="{shoulder + 40 * s:.1f}" width="{44 * s:.1f}" height="{27 * s:.1f}" '
                f'rx="{4 * s:.1f}" fill="{C["water"]}" fill-opacity=".8" stroke="{C["line"]}" stroke-width="{2.2 * s:.1f}"/>')
    return "".join(parts)


def bush(x, y, r, dark=False):
    fill = C["leaf_dark"] if dark else C["leaf"]
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" fill-opacity=".85"/>'
            f'<circle cx="{x - r * 0.7:.1f}" cy="{y + r * 0.25:.1f}" r="{r * 0.66:.1f}" fill="{fill}" fill-opacity=".85"/>'
            f'<circle cx="{x + r * 0.7:.1f}" cy="{y + r * 0.25:.1f}" r="{r * 0.7:.1f}" fill="{fill}" fill-opacity=".85"/>')


def potted_plant(x, ground_y, s=1.0):
    return "".join([
        bush(x, ground_y - 62 * s, 26 * s),
        f'<path d="M{x - 24 * s:.1f},{ground_y - 44 * s:.1f} L{x + 24 * s:.1f},{ground_y - 44 * s:.1f} '
        f'L{x + 17 * s:.1f},{ground_y:.1f} L{x - 17 * s:.1f},{ground_y:.1f} Z" fill="#d08a63" '
        f'stroke="{C["line"]}" stroke-width="2" stroke-linejoin="round"/>',
    ])


# ---------------------------------------------------------------------------
# Ghép toàn cảnh
# ---------------------------------------------------------------------------

GROUND_Y = 556


def defs():
    return f'''<defs>
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
  <path d="M0,1 L10,5 L0,9 z" fill="{C['line']}"/>
</marker>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#f4fbf6"/><stop offset="1" stop-color="{C['sky']}"/>
</linearGradient>
<radialGradient id="ball" cx="35%" cy="30%">
  <stop offset="0" stop-color="{C['water_top']}"/><stop offset="1" stop-color="{C['water_dark']}"/>
</radialGradient>
</defs>'''


def background():
    return "".join([
        f'<rect width="{W}" height="{H}" fill="url(#sky)"/>',
        f'<rect x="0" y="{GROUND_Y}" width="{W}" height="{H - GROUND_Y}" fill="{C["ground"]}"/>',
        f'<line x1="0" y1="{GROUND_Y}" x2="{W}" y2="{GROUND_Y}" stroke="{C["line"]}" stroke-width="2" stroke-opacity=".35"/>',
        bush(66, GROUND_Y - 30, 44, True), bush(1164, GROUND_Y - 26, 34, True),
        potted_plant(158, GROUND_Y, 0.8), potted_plant(1234, GROUND_Y, 0.9),
    ])


def callout(cx, cy, r, inner_svg, from_pt):
    return "".join([
        f'<line x1="{from_pt[0]:.1f}" y1="{from_pt[1]:.1f}" x2="{cx - r * 0.72:.1f}" y2="{cy + r * 0.72:.1f}" '
        f'stroke="{C["line"]}" stroke-width="2" stroke-dasharray="7 5"/>',
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{C["paper"]}" fill-opacity=".97" '
        f'stroke="{C["line"]}" stroke-width="3"/>',
        inner_svg,
    ])


def banner(cx, cy, text):
    if not text:
        return ""
    w = max(240, len(str(text)) * 21 + 90)
    h = 56
    x, y = cx - w / 2, cy - h / 2
    tail = 26
    return "".join([
        f'<path d="M{x:.1f},{y:.1f} H{x + w:.1f} L{x + w + tail:.1f},{y + h / 2:.1f} L{x + w:.1f},{y + h:.1f} '
        f'H{x:.1f} L{x - tail:.1f},{y + h / 2:.1f} Z" fill="{C["banner"]}" stroke="{C["line"]}" '
        f'stroke-width="2.6" stroke-linejoin="round"/>',
        label(cx, cy, text, size=30, weight=800),
    ])


def render_scene(spec):
    """spec: dict do Gemini trả về. Trả về chuỗi SVG hoàn chỉnh."""
    figures = spec.get("figures") or []
    main = figures[0] if figures else {"type": "box", "dims": {}}
    sub = figures[1] if len(figures) > 1 else None

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
             defs(), background()]

    # Bố cục co giãn: có nhân vật thì khối chính lùi sang trái, không thì đặt giữa khung.
    char = spec.get("character") or {}
    has_side = bool(sub) or char.get("enabled", True)
    mx, mw, mh = (366, 450, 292) if has_side else (600, 620, 340)

    drawer = SHAPES.get(str(main.get("type", "box")).lower(), draw_box)
    try:
        parts.append(drawer(main.get("dims") or {}, mx, 380, mw, mh, bottom=GROUND_Y - 8))
    except TypeError:
        parts.append(drawer(main.get("dims") or {}, mx, 380, mw, mh))
    if main.get("label"):
        parts.append(label(mx, 104 if has_side else 74, main["label"], size=26, weight=700))

    # nhân vật bên phải, đứng trên mặt đất
    if char.get("enabled", True):
        sub_type = str((sub or {}).get("type", "")).lower()
        parts.append(schoolboy(792, GROUND_Y, 1.0, holding=bool(sub),
                               hold_type="ladle" if sub_type in ("cylinder", "cone") else "object"))
        if char.get("caption"):
            parts.append(label(792, GROUND_Y + 42, char["caption"], size=24, weight=600))

    # vật thể phụ trong khung phóng to
    if sub:
        sub_drawer = SHAPES.get(str(sub.get("type", "cylinder")).lower(), draw_cylinder)
        kwargs = {"cutaway": True} if sub_drawer is draw_cylinder else {}
        if sub_drawer in (draw_box, draw_prism, draw_pyramid):
            kwargs["compact"] = True
        inner = sub_drawer(sub.get("dims") or {}, 1064, 200, 84, 96, **kwargs)
        parts.append(callout(1086, 200, 130, inner, (912, 396)))
        if sub.get("label"):
            parts.append(label(1086, 360, sub["label"], size=23, weight=600))

    # số lần lặp lại
    badge = spec.get("badge") or {}
    if badge.get("text"):
        parts.append(label(1086, 442, badge["text"], size=60, weight=800))
    if badge.get("caption"):
        parts.append(label(1086, 492, badge["caption"], size=24, weight=600))

    if spec.get("note"):
        parts.append(label(700 if has_side else 1104, 160, spec["note"], size=28, weight=700))

    parts.append(banner(640, 676, spec.get("question")))
    parts.append("</svg>")
    return "".join(parts)
