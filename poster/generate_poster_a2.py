"""
Generator Poster Pameran ISO A2 (420 x 594 mm) - Galileo Vacuum Fall Experiment
Menghasilkan 3 berkas output siap cetak & siap edit:
1. poster_galileo_A2.svg       (Vektor berlapis & dapat diedit per objek di CorelDRAW/Illustrator/Inkscape/Canva)
2. poster_galileo_A2.pdf       (PDF ukuran fisik ISO A2 420x594 mm)
3. poster_galileo_A2_print.png (Gambar raster 300 DPI: 4961 x 7016 px)
"""

import os
import sys
import base64
from xml.sax.saxutils import escape

from PySide6.QtCore import Qt, QSizeF, QRectF
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPdfWriter, QPageSize
from PySide6.QtSvg import QSvgRenderer


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
POSTER_DIR = os.path.dirname(os.path.abspath(__file__))

VIEW_W = 2100  # 420 mm * 5 px/mm
VIEW_H = 2970  # 594 mm * 5 px/mm


def encode_png_base64(path: str) -> str:
    """Mengonversi file gambar PNG menjadi data URI base64 agar SVG berdiri mandiri."""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def svg_card(x: float, y: float, w: float, h: float, rx: float = 26,
             fill: str = "#FFFFFF", stroke: str = "#CBD5E1", stroke_w: float = 3,
             with_shadow: bool = True) -> str:
    """Membuat kartu rounded-rectangle dengan opsional soft drop-shadow tanpa SVG filter."""
    parts = []
    if with_shadow:
        parts.append(
            f'<rect x="{x + 4}" y="{y + 8}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="#CBD5E1" fill-opacity="0.45"/>'
        )
    parts.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}"/>'
    )
    return "\n    ".join(parts)


def svg_feather(cx: float, cy: float, scale: float = 1.0, angle_deg: float = -22,
                color: str = "#D97706", opacity: float = 1.0) -> str:
    """Ilustrasi vektor sehelai bulu yang dapat diedit komponennya."""
    return (
        f'<g transform="translate({cx},{cy}) rotate({angle_deg}) scale({scale})" opacity="{opacity}">\n'
        f'      <path d="M -38,6 C -22,-22 14,-28 42,-8 C 22,18 -14,22 -38,6 Z" '
        f'fill="#FDE68A" stroke="{color}" stroke-width="2.2"/>\n'
        f'      <path d="M -44,8 Q 0,-4 44,-9" fill="none" stroke="#92400E" stroke-width="2.6" stroke-linecap="round"/>\n'
        f'      <line x1="-18" y1="-2" x2="-10" y2="-16" stroke="{color}" stroke-width="1.4"/>\n'
        f'      <line x1="0" y1="-4" x2="8" y2="-19" stroke="{color}" stroke-width="1.4"/>\n'
        f'      <line x1="16" y1="-6" x2="24" y2="-16" stroke="{color}" stroke-width="1.4"/>\n'
        f'      <line x1="-12" y1="2" x2="-4" y2="15" stroke="{color}" stroke-width="1.4"/>\n'
        f'      <line x1="6" y1="0" x2="14" y2="13" stroke="{color}" stroke-width="1.4"/>\n'
        f'    </g>'
    )


def svg_iron_ball(cx: float, cy: float, r: float = 18, opacity: float = 1.0) -> str:
    """Ilustrasi vektor bola besi metalik."""
    return (
        f'<g opacity="{opacity}">\n'
        f'      <circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#metalSphere)" stroke="#0F172A" stroke-width="2"/>\n'
        f'      <circle cx="{cx - r * 0.32}" cy="{cy - r * 0.32}" r="{r * 0.25}" fill="#FFFFFF" fill-opacity="0.65"/>\n'
        f'    </g>'
    )


def svg_arrow(x1: float, y1: float, x2: float, y2: float, color: str = "#0F172A",
              width: float = 4, head_len: float = 12) -> str:
    """Panah vektor arah fisis (gaya/kecepatan) tanpa SVG marker agar kompatibel lintas editor."""
    import math
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-3:
        return ""
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    bx, by = x2 - ux * head_len, y2 - uy * head_len
    hw = head_len * 0.52
    p1x, p1y = bx + px * hw, by + py * hw
    p2x, p2y = bx - px * hw, by - py * hw
    return (
        f'<g>\n'
        f'      <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
        f'stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>\n'
        f'      <polygon points="{x2:.1f},{y2:.1f} {p1x:.1f},{p1y:.1f} {p2x:.1f},{p2y:.1f}" fill="{color}"/>\n'
        f'    </g>'
    )


def svg_text_lines(x: float, y: float, lines: list[str], font_size: float = 20,
                   line_height: float = 29, fill: str = "#334155",
                   weight: str = "500", anchor: str = "start",
                   family: str = "Segoe UI, Arial, sans-serif") -> str:
    """Menyusun paragraf teks SVG multiline yang dapat diedit."""
    out = []
    for i, line in enumerate(lines):
        ly = y + i * line_height
        out.append(
            f'<text x="{x}" y="{ly}" font-family="{family}" font-size="{font_size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(line)}</text>'
        )
    return "\n    ".join(out)


def build_poster_svg() -> str:
    """Membangun keseluruhan struktur SVG Poster ISO A2 Galileo Vacuum Fall."""
    jtp_uri = encode_png_base64(os.path.join(ASSETS_DIR, "logo_jtp.png"))
    sc_uri = encode_png_base64(os.path.join(ASSETS_DIR, "logo_science_center_clean.png"))

    # Grid background lines every 50 px (10 mm)
    grid_lines = []
    for gx in range(50, VIEW_W, 50):
        grid_lines.append(f'<line x1="{gx}" y1="0" x2="{gx}" y2="{VIEW_H}" stroke="#E2E8F0" stroke-width="1"/>')
    for gy in range(50, VIEW_H, 50):
        grid_lines.append(f'<line x1="0" y1="{gy}" x2="{VIEW_W}" y2="{gy}" stroke="#E2E8F0" stroke-width="1"/>')

    # CAD tube internal sub-grid
    cad_grid = []
    for gx in range(1140, 2005, 40):
        cad_grid.append(f'<line x1="{gx}" y1="520" x2="{gx}" y2="1730" stroke="#E2E8F0" stroke-width="0.9"/>')
    for gy in range(550, 1730, 40):
        cad_grid.append(f'<line x1="1110" y1="{gy}" x2="2005" y2="{gy}" stroke="#E2E8F0" stroke-width="0.9"/>')

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="420mm" height="594mm"
     viewBox="0 0 {VIEW_W} {VIEW_H}"
     version="1.1">
  <title>Poster Wahana Eksperimen Jatuh Bebas Galileo - Jatim Park Mega Science Center</title>
  <defs>
    <linearGradient id="glassTube" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#BAE6FD" stop-opacity="0.55"/>
      <stop offset="18%" stop-color="#FFFFFF" stop-opacity="0.75"/>
      <stop offset="50%" stop-color="#E0F2FE" stop-opacity="0.30"/>
      <stop offset="85%" stop-color="#FFFFFF" stop-opacity="0.65"/>
      <stop offset="100%" stop-color="#94A3B8" stop-opacity="0.45"/>
    </linearGradient>
    <radialGradient id="metalSphere" cx="35%" cy="30%" r="68%">
      <stop offset="0%" stop-color="#E2E8F0"/>
      <stop offset="45%" stop-color="#475569"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </radialGradient>
    <linearGradient id="footerGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#0F172A"/>
      <stop offset="100%" stop-color="#1E293B"/>
    </linearGradient>
  </defs>

  <!-- ==================== LAYER 0: BACKGROUND & TECHNICAL GRID ==================== -->
  <g id="layer-background">
    <rect x="0" y="0" width="{VIEW_W}" height="{VIEW_H}" fill="#F1F5F9"/>
    {"".join(grid_lines)}
    <rect x="28" y="28" width="{VIEW_W - 56}" height="{VIEW_H - 56}" rx="34"
          fill="none" stroke="#CBD5E1" stroke-width="2.5"/>
  </g>

  <!-- ==================== LAYER 1: ZONA 1 HEADER BRANDING ==================== -->
  <g id="layer-zona1-header">
    {svg_card(60, 55, 1980, 305, rx=28)}

    <!-- Logo Kiri: Jawa Timur Park Group (Aspek rasio asli 512x227) -->
    <image x="95" y="132" width="320" height="142" preserveAspectRatio="xMidYMid meet" xlink:href="{jtp_uri}"/>
    <line x1="445" y1="90" x2="445" y2="325" stroke="#CBD5E1" stroke-width="3"/>

    <!-- Tengah: Judul Utama & Hook Pertanyaan -->
    <rect x="652" y="80" width="760" height="42" rx="21" fill="#DCFCE7" stroke="#86EFAC" stroke-width="2"/>
    <text x="1032" y="108" font-family="Segoe UI, Arial, sans-serif" font-size="19" font-weight="800"
          fill="#15803D" text-anchor="middle" letter-spacing="1">WAHANA EKSPERIMEN FISIKA KLASIK &amp; KINEMATIKA VAKUM</text>

    <text x="1032" y="192" font-family="Segoe UI, Arial, sans-serif" font-size="56" font-weight="900"
          fill="#0F172A" text-anchor="middle" letter-spacing="0.5">EKSPERIMEN JATUH BEBAS GALILEO</text>

    <text x="1032" y="252" font-family="Segoe UI, Arial, sans-serif" font-size="27" font-weight="800"
          fill="#EA580C" text-anchor="middle">"Mana yang Jatuh Lebih Cepat: Bola Besi atau Sehelai Bulu?"</text>

    <rect x="632" y="282" width="800" height="44" rx="12" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="2"/>
    <text x="1032" y="311" font-family="Segoe UI, Arial, sans-serif" font-size="19" font-weight="700"
          fill="#475569" text-anchor="middle">Tinggi Tabung h = 2,000 m   •   Aktuator 3-Servo ESP32   •   Kamera High-Speed 120 FPS</text>

    <!-- Logo Kanan: Museum Mega Science Center (Aspek rasio asli 407x165) -->
    <line x1="1620" y1="90" x2="1620" y2="325" stroke="#CBD5E1" stroke-width="3"/>
    <image x="1645" y="128" width="365" height="148" preserveAspectRatio="xMidYMid meet" xlink:href="{sc_uri}"/>
  </g>

  <!-- ==================== LAYER 2: ZONA 2 FISIKA DI BALIK FENOMENA ==================== -->
  <g id="layer-zona2-fisika">
    {svg_card(60, 395, 965, 1370, rx=26)}

    <!-- Header Seksi -->
    <rect x="95" y="428" width="10" height="58" rx="5" fill="#16A34A"/>
    <text x="122" y="448" font-family="Segoe UI, Arial, sans-serif" font-size="19" font-weight="800" fill="#16A34A">01 / FISIKA DI BALIK FENOMENA</text>
    <text x="122" y="484" font-family="Segoe UI, Arial, sans-serif" font-size="28" font-weight="800" fill="#0F172A">Mengapa Benda Berbeda Massa Bisa Jatuh Bersamaan?</text>

    <!-- Sub-card 2A: Tabung Berisi Udara -->
    <rect x="95" y="518" width="895" height="378" rx="20" fill="#FFF7ED" stroke="#FDBA74" stroke-width="2.5"/>
    <rect x="120" y="538" width="540" height="38" rx="19" fill="#FFEDD5" stroke="#FB923C" stroke-width="1.5"/>
    <text x="390" y="564" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="800"
          fill="#C2410C" text-anchor="middle">A. KONDISI BERUDARA  (P = 1 atm,  ρ = 1,225 kg/m³)</text>

    <!-- Diagram Gaya Sub-card 2A -->
    <rect x="120" y="592" width="245" height="282" rx="16" fill="#FFFFFF" stroke="#FED7AA" stroke-width="2"/>
    <text x="242" y="618" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="800" fill="#9A3412" text-anchor="middle">DIAGRAM GAYA BEBAS</text>
    <line x1="242" y1="628" x2="242" y2="835" stroke="#FED7AA" stroke-width="1.5" stroke-dasharray="5,5"/>

    <!-- Bola di udara (lebih rendah = jatuh cepat) -->
    {svg_arrow(182, 738, 182, 704, color="#EA580C", width=3, head_len=9)}
    <text x="150" y="718" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="700" fill="#EA580C" text-anchor="middle">F<tspan baseline-shift="sub" font-size="10">drag</tspan></text>
    {svg_iron_ball(182, 758, r=17)}
    {svg_arrow(182, 777, 182, 830, color="#0F172A", width=4.5, head_len=11)}
    <text x="155" y="815" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="800" fill="#0F172A" text-anchor="middle">m·g</text>

    <!-- Bulu di udara (tertinggal di atas karena drag besar) -->
    {svg_arrow(302, 680, 302, 624, color="#EA580C", width=4.5, head_len=11)}
    <text x="334" y="648" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="800" fill="#EA580C" text-anchor="middle">F<tspan baseline-shift="sub" font-size="10">drag</tspan></text>
    {svg_feather(302, 695, scale=0.82)}
    {svg_arrow(302, 715, 302, 760, color="#475569", width=3.5, head_len=10)}
    <text x="330" y="750" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="800" fill="#475569" text-anchor="middle">m·g</text>
    <text x="242" y="859" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="800" fill="#C2410C" text-anchor="middle">Bola Besi Mendahului Bulu</text>

    <!-- Rumus & Penjelasan 2A -->
    <rect x="385" y="592" width="580" height="84" rx="14" fill="#FFFFFF" stroke="#FB923C" stroke-width="2"/>
    <text x="675" y="634" font-family="Segoe UI, Arial, sans-serif" font-size="27" font-weight="800" fill="#0F172A" text-anchor="middle">m · a  =  m · g  −  ½ · ρ · C<tspan baseline-shift="sub" font-size="19">d</tspan> · A · v²</text>
    <text x="675" y="663" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="700" fill="#C2410C" text-anchor="middle">Persamaan Jatuh dengan Gaya Hambat Aerodinamika (Drag Force)</text>

    {svg_text_lines(390, 712, [
        "• Bulu memiliki rasio luas penampang terhadap",
        "  massa (A / m) yang sangat besar.",
        "• Tabrakan molekul udara dari bawah menghasilkan",
        "  gaya hambat besar sehingga bulu melayang lambat.",
        "• Bola besi berdensitas tinggi mudah menembus",
        "  udara dan langsung mencapai dasar tabung."
    ], font_size=19, line_height=28, fill="#334155", weight="600")}

    <!-- Sub-card 2B: Tabung Vakum -->
    <rect x="95" y="916" width="895" height="378" rx="20" fill="#F0FDF4" stroke="#86EFAC" stroke-width="2.5"/>
    <rect x="120" y="936" width="560" height="38" rx="19" fill="#DCFCE7" stroke="#22C55E" stroke-width="1.5"/>
    <text x="400" y="962" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="800"
          fill="#047857" text-anchor="middle">B. KONDISI VAKUM / HAMPA  (P → 0 Pa,  ρ ≈ 0)</text>

    <!-- Diagram Gaya Sub-card 2B -->
    <rect x="120" y="990" width="245" height="282" rx="16" fill="#FFFFFF" stroke="#BBF7D0" stroke-width="2"/>
    <text x="242" y="1016" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="800" fill="#047857" text-anchor="middle">F<tspan baseline-shift="sub" font-size="11">drag</tspan> = 0  (HAMPA)</text>
    <line x1="138" y1="1125" x2="346" y2="1125" stroke="#16A34A" stroke-width="2" stroke-dasharray="6,4"/>

    {svg_iron_ball(182, 1125, r=17)}
    {svg_arrow(182, 1144, 182, 1212, color="#16A34A", width=4.5, head_len=11)}
    <text x="182" y="1232" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="800" fill="#047857" text-anchor="middle">a = g</text>

    {svg_feather(302, 1125, scale=0.82)}
    {svg_arrow(302, 1144, 302, 1212, color="#16A34A", width=4.5, head_len=11)}
    <text x="302" y="1232" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="800" fill="#047857" text-anchor="middle">a = g</text>
    <text x="242" y="1259" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="800" fill="#15803D" text-anchor="middle">Jatuh Sejajar &amp; Serentak!</text>

    <!-- Rumus & Penjelasan 2B -->
    <rect x="385" y="990" width="580" height="84" rx="14" fill="#FFFFFF" stroke="#22C55E" stroke-width="2"/>
    <text x="675" y="1032" font-family="Segoe UI, Arial, sans-serif" font-size="28" font-weight="900" fill="#047857" text-anchor="middle">F<tspan baseline-shift="sub" font-size="19">drag</tspan> = 0   ⟹   a = g = 9,807 m/s²</text>
    <text x="675" y="1061" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="700" fill="#059669" text-anchor="middle">Percepatan gravitasi INDEPENDEN terhadap massa benda (m)!</text>

    {svg_text_lines(390, 1110, [
        "• Pompa vakum menguras molekul udara dari dalam",
        "  silinder hingga gaya gesek udara lenyap (F_drag = 0).",
        "• Tanpa hambatan udara, massa inersia saling",
        "  meniadakan massa gravitasi: a = (m · g) / m = g.",
        "• Bola besi dan bulu bergerak identik serta",
        "  menyentuh dasar tabung secara bersamaan."
    ], font_size=19, line_height=28, fill="#334155", weight="600")}

    <!-- Sub-card 2C: Prediksi Teoritis pada h = 2.000 m -->
    <rect x="95" y="1316" width="895" height="415" rx="20" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="2.5"/>
    <text x="122" y="1356" font-family="Segoe UI, Arial, sans-serif" font-size="21" font-weight="900" fill="#0F172A">PREDIKSI TEORITIS VAKUM  (Tinggi Jatuh h = 2,000 m)</text>

    <!-- Card Metric 1: Waktu Jatuh -->
    <rect x="120" y="1376" width="415" height="205" rx="18" fill="#ECFDF5" stroke="#16A34A" stroke-width="2.5"/>
    <text x="327" y="1410" font-family="Segoe UI, Arial, sans-serif" font-size="17" font-weight="800" fill="#047857" text-anchor="middle">WAKTU JATUH VAKUM (t)</text>
    <text x="327" y="1444" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="800" fill="#0F172A" text-anchor="middle">t  =  √(2h / g)</text>
    <text x="327" y="1520" font-family="Segoe UI, Arial, sans-serif" font-size="54" font-weight="900" fill="#15803D" text-anchor="middle">638,5 ms</text>
    <text x="327" y="1558" font-family="Segoe UI, Arial, sans-serif" font-size="17" font-weight="700" fill="#059669" text-anchor="middle">(= 0,6385 detik setelah bucket dibuka)</text>

    <!-- Card Metric 2: Kecepatan Akhir -->
    <rect x="555" y="1376" width="415" height="205" rx="18" fill="#EFF6FF" stroke="#0284C7" stroke-width="2.5"/>
    <text x="762" y="1410" font-family="Segoe UI, Arial, sans-serif" font-size="17" font-weight="800" fill="#0369A1" text-anchor="middle">KECEPATAN TUMBUKAN (v)</text>
    <text x="762" y="1444" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="800" fill="#0F172A" text-anchor="middle">v  =  √(2 · g · h)</text>
    <text x="762" y="1520" font-family="Segoe UI, Arial, sans-serif" font-size="54" font-weight="900" fill="#0284C7" text-anchor="middle">6,26 m/s</text>
    <text x="762" y="1558" font-family="Segoe UI, Arial, sans-serif" font-size="17" font-weight="700" fill="#0369A1" text-anchor="middle">(≈ 22,5 km/jam saat tiba di dasar)</text>

    <!-- Strip Kalkulasi & Error Propagation -->
    <rect x="120" y="1600" width="850" height="106" rx="14" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="2"/>
    <text x="145" y="1638" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="800" fill="#0F172A">KALKULASI PERCEPATAN GRAVITASI REAL-TIME:</text>
    <text x="145" y="1678" font-family="Segoe UI, Arial, sans-serif" font-size="23" font-weight="900" fill="#0284C7">g<tspan baseline-shift="sub" font-size="16">ukur</tspan> = 2h / Δt²</text>
    <text x="342" y="1677" font-family="Segoe UI, Arial, sans-serif" font-size="17" font-weight="600" fill="#475569">dengan ketidakpastian sistem δg/g ≈ ±1,3% pada sampling 120 FPS.</text>
  </g>

  <!-- ==================== LAYER 3: ZONA 3 ARSITEKTUR CAD & KAMERA 120 FPS ==================== -->
  <g id="layer-zona3-instrumentasi">
    {svg_card(1075, 395, 965, 1370, rx=26)}

    <!-- Header Seksi -->
    <rect x="1110" y="428" width="10" height="58" rx="5" fill="#0284C7"/>
    <text x="1137" y="448" font-family="Segoe UI, Arial, sans-serif" font-size="19" font-weight="800" fill="#0284C7">02 / ARSITEKTUR WAHANA &amp; INSTRUMENTASI</text>
    <text x="1137" y="484" font-family="Segoe UI, Arial, sans-serif" font-size="28" font-weight="800" fill="#0F172A">Skema Tabung Vakum, 3-Servo ESP32 &amp; Kamera 120 FPS</text>

    <!-- Kanvas CAD Blueprint -->
    <rect x="1110" y="518" width="895" height="1213" rx="20" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="2.5"/>
    {"".join(cad_grid)}

    <!-- ===== Rakitan Atas: 2 Hopper + Bucket Kolektor ===== -->
    <!-- Servo 1: Penyimpan Bulu -->
    <rect x="1235" y="546" width="115" height="62" rx="10" fill="#FFEDD5" stroke="#EA580C" stroke-width="2.5"/>
    <text x="1292" y="569" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="800" fill="#C2410C" text-anchor="middle">SERVO 1</text>
    {svg_feather(1292, 592, scale=0.52)}

    <!-- Servo 2: Penyimpan Bola -->
    <rect x="1380" y="546" width="115" height="62" rx="10" fill="#E2E8F0" stroke="#1E293B" stroke-width="2.5"/>
    <text x="1437" y="569" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="800" fill="#0F172A" text-anchor="middle">SERVO 2</text>
    {svg_iron_ball(1437, 592, r=10)}

    <!-- Corong ke Bucket -->
    <line x1="1292" y1="608" x2="1335" y2="656" stroke="#EA580C" stroke-width="3" stroke-dasharray="5,4"/>
    <line x1="1437" y1="608" x2="1395" y2="656" stroke="#1E293B" stroke-width="3" stroke-dasharray="5,4"/>

    <!-- Bucket Kolektor / Servo 3 -->
    <rect x="1255" y="656" width="220" height="72" rx="12" fill="#DCFCE7" stroke="#16A34A" stroke-width="3"/>
    <text x="1365" y="679" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="900" fill="#15803D" text-anchor="middle">BUCKET KOLEKTOR (SERVO 3)</text>
    {svg_feather(1332, 707, scale=0.48)}
    {svg_iron_ball(1398, 707, r=11)}
    <line x1="1265" y1="728" x2="1465" y2="728" stroke="#15803D" stroke-width="5"/>

    <!-- ===== Silinder Tabung Vakum Utama (y = 740..1535) ===== -->
    <!-- Tutup Flens Atas & Bawah -->
    <rect x="1245" y="732" width="240" height="22" rx="6" fill="#475569" stroke="#0F172A" stroke-width="2"/>
    <rect x="1245" y="1520" width="240" height="32" rx="8" fill="#334155" stroke="#0F172A" stroke-width="2"/>
    <rect x="1268" y="1508" width="194" height="12" rx="4" fill="#64748B"/>

    <!-- Dinding Kaca Silinder -->
    <rect x="1265" y="754" width="200" height="754" fill="url(#glassTube)" stroke="#475569" stroke-width="4"/>
    <line x1="1285" y1="764" x2="1285" y2="1500" stroke="#FFFFFF" stroke-width="5" stroke-opacity="0.7"/>

    <!-- Garis Dimensi Tinggi Tabung (Kiri Tabung: x = 1220) -->
    <line x1="1210" y1="754" x2="1255" y2="754" stroke="#0F172A" stroke-width="2"/>
    <line x1="1210" y1="1508" x2="1255" y2="1508" stroke="#0F172A" stroke-width="2"/>
    <line x1="1225" y1="758" x2="1225" y2="1504" stroke="#0F172A" stroke-width="2.5"/>
    <polygon points="1225,754 1219,768 1231,768" fill="#0F172A"/>
    <polygon points="1225,1508 1219,1494 1231,1494" fill="#0F172A"/>
    <rect x="1122" y="1096" width="122" height="58" rx="10" fill="#FFFFFF" stroke="#0F172A" stroke-width="2"/>
    <text x="1183" y="1122" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="900" fill="#0F172A" text-anchor="middle">Tinggi Tabung</text>
    <text x="1183" y="1144" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="900" fill="#0284C7" text-anchor="middle">h = 2,000 m</text>

    <!-- Penanda Kinematika (Stroboscopic Trajectory) -->
    <!-- 0 ms (t0 = 0, y=754) -->
    <text x="1202" y="782" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="800" fill="#15803D" text-anchor="end">t₀ = 0 ms</text>
    <!-- 319 ms (0.50 m, y=942) -->
    <line x1="1265" y1="942" x2="1465" y2="942" stroke="#94A3B8" stroke-width="1.5" stroke-dasharray="4,4"/>
    <text x="1202" y="947" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="700" fill="#475569" text-anchor="end">319 ms</text>
    {svg_feather(1322, 942, scale=0.52, opacity=0.45)}
    {svg_iron_ball(1408, 942, r=11, opacity=0.45)}

    <!-- 451 ms (1.00 m, y=1131) -->
    <line x1="1265" y1="1131" x2="1465" y2="1131" stroke="#94A3B8" stroke-width="1.5" stroke-dasharray="4,4"/>
    {svg_feather(1322, 1131, scale=0.52, opacity=0.68)}
    {svg_iron_ball(1408, 1131, r=11, opacity=0.68)}

    <!-- 553 ms (1.50 m, y=1319) -->
    <line x1="1265" y1="1319" x2="1465" y2="1319" stroke="#94A3B8" stroke-width="1.5" stroke-dasharray="4,4"/>
    <text x="1202" y="1324" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="700" fill="#475569" text-anchor="end">553 ms</text>
    {svg_feather(1322, 1319, scale=0.52, opacity=0.88)}
    {svg_iron_ball(1408, 1319, r=11, opacity=0.88)}

    <!-- Zona Deteksi Optik Kamera (ROI Box Hijau + Garis Finish Merah) -->
    <rect x="1256" y="1352" width="218" height="154" rx="8" fill="#22C55E" fill-opacity="0.12"
          stroke="#16A34A" stroke-width="3.5" stroke-dasharray="10,6"/>
    <line x1="1260" y1="1490" x2="1470" y2="1490" stroke="#EF4444" stroke-width="3.5"/>
    {svg_feather(1322, 1486, scale=0.56)}
    {svg_iron_ball(1408, 1486, r=12)}
    <text x="1202" y="1494" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="900" fill="#DC2626" text-anchor="end">638,5 ms</text>
    <rect x="1126" y="1392" width="116" height="44" rx="8" fill="#DCFCE7" stroke="#16A34A" stroke-width="1.8"/>
    <text x="1184" y="1412" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="900" fill="#15803D" text-anchor="middle">ZONA ROI</text>
    <text x="1184" y="1429" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="700" fill="#047857" text-anchor="middle">Garis Finis</text>

    <!-- ===== Kolom Anotasi Teknis Kanan CAD (x = 1520..1985) ===== -->
    <!-- Callout 1: Mekanisme 3-Servo ESP32 -->
    <line x1="1475" y1="692" x2="1520" y2="650" stroke="#EA580C" stroke-width="2.5" stroke-dasharray="6,4"/>
    <circle cx="1475" cy="692" r="5" fill="#EA580C"/>
    <rect x="1520" y="546" width="465" height="224" rx="16" fill="#FFFFFF" stroke="#EA580C" stroke-width="2.5"/>
    <text x="1542" y="578" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="900" fill="#C2410C">AKTUATOR 2-TAHAP (ESP32)</text>
    {svg_text_lines(1542, 610, [
        "• Servo 1 (GPIO 18): Muat bulu ke kolektor",
        "• Servo 2 (GPIO 19): Muat bola ke kolektor",
        "• Servo 3 (GPIO 21): Buka bucket serentak",
        "  pada t₀ = 0,0 ms (0 μs selisih lepas)",
        "• Bucket tetap terbuka hingga tombol Reset"
    ], font_size=17, line_height=28, fill="#334155", weight="600")}

    <!-- Callout 2: Pompa Vakum & Kedap Udara -->
    <line x1="1465" y1="882" x2="1520" y2="882" stroke="#475569" stroke-width="3"/>
    <rect x="1465" y="870" width="18" height="24" rx="3" fill="#475569"/>
    <rect x="1520" y="805" width="465" height="160" rx="16" fill="#FFFFFF" stroke="#64748B" stroke-width="2.5"/>
    <text x="1542" y="838" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="900" fill="#0F172A">SISTEM POMPA &amp; KATUP VAKUM</text>
    {svg_text_lines(1542, 870, [
        "• Tabung akrilik tebal tersegel rapat O-ring.",
        "• Pompa menguras udara keluar hingga kondisi",
        "  mendekati vakum sempurna (P → 0 Pa)."
    ], font_size=17, line_height=28, fill="#334155", weight="600")}

    <!-- Callout 3: Profil Kinematika GLBB -->
    <rect x="1520" y="1000" width="465" height="205" rx="16" fill="#ECFDF5" stroke="#16A34A" stroke-width="2.5"/>
    <text x="1542" y="1034" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="900" fill="#047857">PROFIL LINTASAN JATUH (y = ½gt²)</text>
    {svg_text_lines(1542, 1068, [
        "• t = 0,000 s   →   Posisi y = 0,00 m (Puncak)",
        "• t = 0,319 s   →   Posisi y = 0,50 m",
        "• t = 0,451 s   →   Posisi y = 1,00 m",
        "• t = 0,638 s   →   Tiba di dasar y = 2,00 m"
    ], font_size=17, line_height=31, fill="#065F46", weight="700")}

    <!-- Callout 4: Kamera High-Speed 120 FPS + FOV Cone -->
    <polygon points="1474,1360 1525,1412 1525,1452 1474,1500" fill="#0284C7" fill-opacity="0.14"/>
    <line x1="1474" y1="1360" x2="1525" y2="1418" stroke="#0284C7" stroke-width="2" stroke-dasharray="6,4"/>
    <line x1="1474" y1="1500" x2="1525" y2="1446" stroke="#0284C7" stroke-width="2" stroke-dasharray="6,4"/>
    <!-- Ikon Lensa Kamera -->
    <rect x="1508" y="1410" width="24" height="44" rx="5" fill="#0284C7" stroke="#0F172A" stroke-width="2"/>

    <rect x="1532" y="1240" width="453" height="295" rx="16" fill="#EFF6FF" stroke="#0284C7" stroke-width="2.5"/>
    <text x="1554" y="1274" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="900" fill="#0369A1">KAMERA HIGH-SPEED OV2710</text>
    {svg_text_lines(1554, 1308, [
        "• Laju Akuisisi: 120 FPS (640×480 MJPG)",
        "• Resolusi Temporal: Δt = 8,33 ms / frame",
        "• Shutter Manual: 1/128 detik (7,81 ms)",
        "  bebas motion blur objek jatuh cepat",
        "• Dead-Time Gate: 150 ms anti getaran",
        "• Frame Differencing menghentikan waktu",
        "  otomatis tepat saat impak di Zona ROI"
    ], font_size=16.5, line_height=29, fill="#0F172A", weight="600")}

    <!-- Footer Strip dalam Kartu Instrumentasi -->
    <rect x="1130" y="1592" width="855" height="114" rx="16" fill="#0F172A"/>
    <text x="1158" y="1628" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="900" fill="#38BDF8">SINKRONISASI PRESISI HARDWARE ↔ KOMPUTER</text>
    <text x="1158" y="1660" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="600" fill="#F8FAFC">ESP32 mencatat waktu rilis (mikrodetik) saat Bucket terbuka  →  Kamera 120 FPS merekam</text>
    <text x="1158" y="1687" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="600" fill="#CBD5E1">frame pra-impak &amp; pasca-impak ke Rolling Buffer (150 frame) untuk inspeksi Slow-Motion.</text>
  </g>

  <!-- ==================== LAYER 4: ZONA 4 PANDUAN EKSPERIMEN PENGUNJUNG ==================== -->
  <g id="layer-zona4-panduan">
    {svg_card(60, 1800, 1980, 640, rx=26)}

    <rect x="95" y="1832" width="10" height="58" rx="5" fill="#EA580C"/>
    <text x="122" y="1852" font-family="Segoe UI, Arial, sans-serif" font-size="19" font-weight="800" fill="#EA580C">03 / PANDUAN EKSPERIMEN PENGUNJUNG</text>
    <text x="122" y="1888" font-family="Segoe UI, Arial, sans-serif" font-size="30" font-weight="800" fill="#0F172A">4 Langkah Interaktif Mengoperasikan Wahana pada Layar Sentuh</text>

    <!-- LANGKAH 1 -->
    <rect x="95" y="1920" width="455" height="485" rx="20" fill="#FFF7ED" stroke="#EA580C" stroke-width="2.5"/>
    <circle cx="145" cy="1970" r="24" fill="#EA580C"/>
    <text x="145" y="1979" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="900" fill="#FFFFFF" text-anchor="middle">1</text>
    <text x="184" y="1978" font-family="Segoe UI, Arial, sans-serif" font-size="23" font-weight="900" fill="#0F172A">MUAT BULU</text>

    <rect x="122" y="2016" width="401" height="48" rx="10" fill="#EA580C"/>
    <text x="322" y="2047" font-family="Segoe UI, Arial, sans-serif" font-size="19" font-weight="800" fill="#FFFFFF" text-anchor="middle">1. Muat Bulu (Servo 1)</text>

    <!-- Mini Diagram Langkah 1 -->
    <rect x="122" y="2084" width="401" height="122" rx="14" fill="#FFFFFF" stroke="#FED7AA" stroke-width="2"/>
    {svg_feather(255, 2124, scale=0.68)}
    {svg_arrow(310, 2116, 310, 2166, color="#EA580C", width=4, head_len=10)}
    <rect x="355" y="2138" width="110" height="46" rx="8" fill="#DCFCE7" stroke="#16A34A" stroke-width="2"/>
    <text x="410" y="2167" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="800" fill="#15803D" text-anchor="middle">Bucket</text>

    {svg_text_lines(124, 2242, [
        "Sentuh tombol oranye pada layar.",
        "Servo 1 melepaskan bulu agar jatuh",
        "ke dalam bucket penampung di atas",
        "tabung. Stopwatch belum menyala."
    ], font_size=19, line_height=29, fill="#334155", weight="600")}
    <rect x="122" y="2360" width="401" height="30" rx="8" fill="#FFEDD5"/>
    <text x="322" y="2381" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="800" fill="#C2410C" text-anchor="middle">Status: Bulu Siap di Bucket [OK]</text>

    <!-- LANGKAH 2 -->
    <rect x="585" y="1920" width="455" height="485" rx="20" fill="#F8FAFC" stroke="#334155" stroke-width="2.5"/>
    <circle cx="635" cy="1970" r="24" fill="#1E293B"/>
    <text x="635" y="1979" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="900" fill="#FFFFFF" text-anchor="middle">2</text>
    <text x="674" y="1978" font-family="Segoe UI, Arial, sans-serif" font-size="23" font-weight="900" fill="#0F172A">MUAT BOLA BESI</text>

    <rect x="612" y="2016" width="401" height="48" rx="10" fill="#1E293B"/>
    <text x="812" y="2047" font-family="Segoe UI, Arial, sans-serif" font-size="19" font-weight="800" fill="#FFFFFF" text-anchor="middle">2. Muat Bola (Servo 2)</text>

    <!-- Mini Diagram Langkah 2 -->
    <rect x="612" y="2084" width="401" height="122" rx="14" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="2"/>
    {svg_iron_ball(745, 2124, r=14)}
    {svg_arrow(798, 2116, 798, 2166, color="#1E293B", width=4, head_len=10)}
    <rect x="840" y="2138" width="122" height="46" rx="8" fill="#DCFCE7" stroke="#16A34A" stroke-width="2"/>
    {svg_feather(875, 2160, scale=0.40)}
    {svg_iron_ball(925, 2160, r=9)}

    {svg_text_lines(614, 2242, [
        "Sentuh tombol biru tua. Servo 2",
        "memuat bola besi ke bucket yang",
        "sama dengan bulu. Kedua objek siap",
        "pada ketinggian awal identik."
    ], font_size=19, line_height=29, fill="#334155", weight="600")}
    <rect x="612" y="2360" width="401" height="30" rx="8" fill="#E2E8F0"/>
    <text x="812" y="2381" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="800" fill="#0F172A" text-anchor="middle">Status: Bola &amp; Bulu Siap di Bucket [OK]</text>

    <!-- LANGKAH 3 -->
    <rect x="1075" y="1920" width="455" height="485" rx="20" fill="#ECFDF5" stroke="#16A34A" stroke-width="2.5"/>
    <circle cx="1125" cy="1970" r="24" fill="#16A34A"/>
    <text x="1125" y="1979" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="900" fill="#FFFFFF" text-anchor="middle">3</text>
    <text x="1164" y="1978" font-family="Segoe UI, Arial, sans-serif" font-size="23" font-weight="900" fill="#0F172A">BUKA BUCKET (DROP)</text>

    <rect x="1102" y="2016" width="401" height="48" rx="10" fill="#16A34A"/>
    <text x="1302" y="2047" font-family="Segoe UI, Arial, sans-serif" font-size="19" font-weight="800" fill="#FFFFFF" text-anchor="middle">3. BUKA BUCKET (SIMULTAN)</text>

    <!-- Mini Diagram Langkah 3 -->
    <rect x="1102" y="2084" width="401" height="122" rx="14" fill="#FFFFFF" stroke="#86EFAC" stroke-width="2"/>
    <line x1="1150" y1="2104" x2="1280" y2="2104" stroke="#16A34A" stroke-width="3" stroke-dasharray="5,4"/>
    {svg_feather(1185, 2138, scale=0.45)}
    {svg_iron_ball(1245, 2138, r=10)}
    {svg_arrow(1215, 2152, 1215, 2192, color="#16A34A", width=4, head_len=9)}
    <rect x="1325" y="2106" width="150" height="78" rx="10" fill="#F0FDF4" stroke="#16A34A" stroke-width="2"/>
    <text x="1400" y="2136" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="800" fill="#047857" text-anchor="middle">STOPWATCH</text>
    <text x="1400" y="2166" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="900" fill="#15803D" text-anchor="middle">638,5 ms</text>

    {svg_text_lines(1104, 2242, [
        "Sentuh tombol hijau utama! Pintu",
        "bucket terbuka serentak, stopwatch",
        "mulai berhitung dan kamera 120 FPS",
        "mengukur g serta waktu jatuh (dt)."
    ], font_size=19, line_height=29, fill="#334155", weight="600")}
    <rect x="1102" y="2360" width="401" height="30" rx="8" fill="#DCFCE7"/>
    <text x="1302" y="2381" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="800" fill="#15803D" text-anchor="middle">Amati: Keduanya mendarat bersamaan!</text>

    <!-- LANGKAH 4 -->
    <rect x="1565" y="1920" width="440" height="485" rx="20" fill="#EFF6FF" stroke="#0284C7" stroke-width="2.5"/>
    <circle cx="1615" cy="1970" r="24" fill="#0284C7"/>
    <text x="1615" y="1979" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="900" fill="#FFFFFF" text-anchor="middle">4</text>
    <text x="1654" y="1978" font-family="Segoe UI, Arial, sans-serif" font-size="23" font-weight="900" fill="#0F172A">SLOW-MO &amp; RESET</text>

    <rect x="1592" y="2016" width="386" height="48" rx="10" fill="#FEE2E2" stroke="#EF4444" stroke-width="2"/>
    <text x="1785" y="2047" font-family="Segoe UI, Arial, sans-serif" font-size="19" font-weight="800" fill="#B91C1C" text-anchor="middle">Reset Posisi Aktuator</text>

    <!-- Mini Diagram Langkah 4: Slider Timeline -->
    <rect x="1592" y="2084" width="386" height="122" rx="14" fill="#FFFFFF" stroke="#BAE6FD" stroke-width="2"/>
    <text x="1785" y="2114" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="800" fill="#0369A1" text-anchor="middle">INSPEKSI FRAME-BY-FRAME (120 FPS)</text>
    <line x1="1625" y1="2148" x2="1945" y2="2148" stroke="#CBD5E1" stroke-width="8" stroke-linecap="round"/>
    <line x1="1625" y1="2148" x2="1815" y2="2148" stroke="#0284C7" stroke-width="8" stroke-linecap="round"/>
    <circle cx="1815" cy="2148" r="13" fill="#0284C7" stroke="#FFFFFF" stroke-width="3"/>
    <text x="1785" y="2188" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="800" fill="#0284C7" text-anchor="middle">◄ -8,3 ms   |   Δt = 638,5 ms   |   +8,3 ms ►</text>

    {svg_text_lines(1594, 2242, [
        "Geser slider di bawah kamera untuk",
        "memutar ulang momen pendaratan",
        "tiap 8,33 ms. Tekan Reset untuk",
        "mengunci semua servo kembali standby."
    ], font_size=19, line_height=29, fill="#334155", weight="600")}
    <rect x="1592" y="2360" width="386" height="30" rx="8" fill="#E0F2FE"/>
    <text x="1785" y="2381" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="800" fill="#0369A1" text-anchor="middle">Siap untuk eksperimen selanjutnya!</text>
  </g>

  <!-- ==================== LAYER 5: ZONA 5 SEJARAH SAINS & FOOTER ==================== -->
  <g id="layer-zona5-sejarah">
    {svg_card(60, 2475, 1980, 345, rx=26)}

    <!-- Kolom Kiri: Galileo 1589 -->
    <rect x="95" y="2508" width="90" height="44" rx="12" fill="#0284C7"/>
    <text x="140" y="2538" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="900" fill="#FFFFFF" text-anchor="middle">1589</text>
    <text x="202" y="2538" font-family="Segoe UI, Arial, sans-serif" font-size="25" font-weight="900" fill="#0F172A">Galileo Galilei (Pisa, Italia)</text>
    {svg_text_lines(95, 2588, [
        "Selama hampir dua milenium, pemikiran Aristoteles diyakini benar bahwa",
        "benda lebih berat pasti jatuh lebih cepat. Melalui eksperimen bidang",
        "miring dan analisis logika benda terikat, Galileo merumuskan bahwa",
        "di ruang bebas gesekan, semua benda jatuh dengan percepatan sama."
    ], font_size=20, line_height=31, fill="#334155", weight="600")}
    <rect x="95" y="2716" width="915" height="68" rx="12" fill="#EFF6FF" stroke="#BAE6FD" stroke-width="1.8"/>
    <text x="115" y="2746" font-family="Segoe UI, Arial, sans-serif" font-size="17" font-weight="800" fill="#0369A1">INTISARI GALILEO:</text>
    <text x="115" y="2770" font-family="Segoe UI, Arial, sans-serif" font-size="16.5" font-weight="600" fill="#1E293B">Perbedaan waktu jatuh di udara semata-mata disebabkan oleh hambatan udara, bukan massa.</text>

    <!-- Pemisah Tengah -->
    <line x1="1045" y1="2505" x2="1045" y2="2790" stroke="#CBD5E1" stroke-width="3"/>

    <!-- Kolom Kanan: Apollo 15 (1971) -->
    <rect x="1085" y="2508" width="90" height="44" rx="12" fill="#16A34A"/>
    <text x="1130" y="2538" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="900" fill="#FFFFFF" text-anchor="middle">1971</text>
    <text x="1192" y="2538" font-family="Segoe UI, Arial, sans-serif" font-size="25" font-weight="900" fill="#0F172A">Misi Apollo 15 di Bulan (NASA)</text>
    {svg_text_lines(1085, 2588, [
        "Komandan David Scott membuktikan teori Galileo secara langsung di",
        "permukaan Bulan yang tidak memiliki atmosfer. Ia menjatuhkan palu",
        "geologi (1,32 kg) dan bulu elang (0,03 kg) bersamaan — keduanya",
        "mendarat di tanah Bulan pada momen yang persis sama!"
    ], font_size=20, line_height=31, fill="#334155", weight="600")}
    <rect x="1085" y="2716" width="775" height="68" rx="12" fill="#ECFDF5" stroke="#BBF7D0" stroke-width="1.8"/>
    <text x="1105" y="2746" font-family="Segoe UI, Arial, sans-serif" font-size="17" font-weight="800" fill="#047857">"TUAN GALILEO TERNYATA BENAR!"</text>
    <text x="1105" y="2770" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="600" fill="#1E293B">— Komandan David Scott, 2 Agustus 1971 (Siaran Langsung NASA TV)</text>

    <!-- Ikon Bulan Kanan Bawah -->
    <circle cx="1945" cy="2742" r="36" fill="#E2E8F0" stroke="#94A3B8" stroke-width="2"/>
    <circle cx="1932" cy="2732" r="7" fill="#CBD5E1"/>
    <circle cx="1958" cy="2752" r="9" fill="#CBD5E1"/>
    <text x="1945" y="2798" font-family="Segoe UI, Arial, sans-serif" font-size="13.5" font-weight="800" fill="#475569" text-anchor="middle">g<tspan baseline-shift="sub" font-size="10">Bulan</tspan> = 1,62 m/s²</text>

    <!-- Footer Strip -->
    <rect x="60" y="2844" width="1980" height="70" rx="18" fill="url(#footerGrad)"/>
    <text x="100" y="2886" font-family="Segoe UI, Arial, sans-serif" font-size="20" font-weight="800" fill="#F8FAFC">
      JATIM PARK MEGA SCIENCE CENTER DAN BUDAYA  •  WAHANA FISIKA EKSPERIMENTAL
    </text>
    <text x="2000" y="2886" font-family="Segoe UI, Arial, sans-serif" font-size="19" font-weight="700" fill="#38BDF8" text-anchor="end">
      Engineered by Yotta Aksara Energi  •  ISO A2 Print Standard (420 × 594 mm)
    </text>
  </g>
</svg>
'''
    return svg


def render_svg_to_pdf_and_png(svg_path: str, pdf_path: str, png_print_path: str, png_preview_path: str):
    """Merender berkas SVG menjadi PDF ISO A2 (420x594 mm) dan PNG 300 DPI (4961x7016 px)."""
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    renderer = QSvgRenderer(svg_path)
    if not renderer.isValid():
        raise RuntimeError(f"SVG tidak valid saat dimuat QSvgRenderer: {svg_path}")

    # 1. Export ke PDF ukuran fisik ISO A2 (420 x 594 mm)
    pdf_writer = QPdfWriter(pdf_path)
    pdf_writer.setPageSize(QPageSize(QSizeF(420.0, 594.0), QPageSize.Millimeter, "A2"))
    pdf_writer.setResolution(300)
    pdf_painter = QPainter(pdf_writer)
    renderer.render(pdf_painter, QRectF(0, 0, pdf_writer.width(), pdf_writer.height()))
    pdf_painter.end()

    # 2. Export ke PNG 300 DPI (4961 x 7016 px)
    print_img = QImage(4961, 7016, QImage.Format_ARGB32)
    print_img.fill(0xFFFFFFFF)
    png_painter = QPainter(print_img)
    png_painter.setRenderHint(QPainter.Antialiasing, True)
    png_painter.setRenderHint(QPainter.TextAntialiasing, True)
    png_painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(png_painter, QRectF(0, 0, 4961, 7016))
    png_painter.end()
    print_img.save(png_print_path, "PNG")

    # 3. Export preview ringan (1400 x 1980 px) untuk inspeksi cepat
    preview_img = print_img.scaled(1400, 1980, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    preview_img.save(png_preview_path, "PNG")


def main():
    os.makedirs(POSTER_DIR, exist_ok=True)
    svg_path = os.path.join(POSTER_DIR, "poster_galileo_A2.svg")
    pdf_path = os.path.join(POSTER_DIR, "poster_galileo_A2.pdf")
    png_print_path = os.path.join(POSTER_DIR, "poster_galileo_A2_print.png")
    png_preview_path = r"C:\Users\karim\.gemini\antigravity\brain\02ad705f-8fc8-4263-878c-e3dd622bd6f9\poster_galileo_A2_preview.png"

    svg_content = build_poster_svg()
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    render_svg_to_pdf_and_png(svg_path, pdf_path, png_print_path, png_preview_path)
    print(f"OK SVG : {svg_path}")
    print(f"OK PDF : {pdf_path}")
    print(f"OK PNG : {png_print_path} (4961x7016 @ 300 DPI)")
    print(f"OK PREV: {png_preview_path}")


if __name__ == "__main__":
    main()
