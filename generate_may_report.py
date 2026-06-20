"""
静岡市 2026年5月 気象分析レポート PDF生成スクリプト
Pillow で画像を描画し、PDF として保存（フォント埋め込み問題を回避）
"""
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os

# ── フォント設定 ──────────────────────────────────────────────────
FONT_NORMAL = r'C:\Windows\Fonts\msgothic.ttc'
FONT_BOLD   = r'C:\Windows\Fonts\msgothic.ttc'

def font(size, bold=False):
    idx = 2 if bold else 0   # ttcサブフォント: 0=MS Gothic, 2=MS Gothic Bold相当
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_NORMAL, size, index=idx)
    except:
        return ImageFont.truetype(FONT_NORMAL, size, index=0)

# ── CSV読み込み ─────────────────────────────────────────────────
CSV_PATH   = 'shizuoka_weather.csv'
GRAPH1     = 'shizuoka_normal_plot.png'
OUTPUT_PDF = '静岡市_2026年5月_気象分析レポート.pdf'

df  = pd.read_csv(CSV_PATH)
may = df[df['Label'].str.startswith('5/')].copy().reset_index(drop=True)

LABEL_MAP = {
    '5/1': '5/1 (1〜5日)',
    '5/2': '5/2 (6〜10日)',
    '5/3': '5/3 (11〜15日)',
    '5/4': '5/4 (16〜20日)',
}

def get_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

c_prec = get_col(df, ['実測降水量'])
c_avg  = get_col(df, ['実測平均気温'])
c_max  = get_col(df, ['実測最高気温'])
c_min  = get_col(df, ['実測最低気温'])
c_navg = get_col(df, ['平年平均気温'])

def v(row, col):
    if col and col in row.index and pd.notna(row[col]):
        return row[col]
    return None

def fmt(val):
    return '―' if val is None else f'{val:.1f}'

def diff_str(ar, nr):
    if ar is None or nr is None:
        return '―'
    d = ar - nr
    return f'+{d:.1f}' if d >= 0 else f'{d:.1f}'

# ── 色定義 ──────────────────────────────────────────────────────
C_HEADER  = (46,  109, 164)
C_TITLE   = (26,  58,  92)
C_ROW1    = (232, 240, 251)
C_ROW2    = (255, 255, 255)
C_RED     = (192, 57,  43)
C_BLUE    = (41,  128, 185)
C_GREEN   = (39,  174, 96)
C_GRAY    = (127, 140, 141)
C_BGBOX   = (234, 242, 251)
WHITE     = (255, 255, 255)
BLACK     = (0,   0,   0)

# ── A4 @ 150dpi ─────────────────────────────────────────────────
DPI = 150
W   = int(8.27  * DPI)   # 1240
H   = int(11.69 * DPI)   # 1754
M   = 60                  # マージン

def draw_rect(d, x, y, w, h, fill, outline=None, width=1):
    d.rectangle([x, y, x+w, y+h], fill=fill,
                outline=outline, width=width)

def draw_text(d, x, y, text, fnt, fill=BLACK, anchor='lt'):
    d.text((x, y), text, font=fnt, fill=fill, anchor=anchor)

now_str = datetime.now().strftime('%Y年%m月%d日 %H:%M 作成')

# ════════════════════════════════════════════════════════════════
# ページ1
# ════════════════════════════════════════════════════════════════
img1 = Image.new('RGB', (W, H), WHITE)
d1   = ImageDraw.Draw(img1)

y = M

# タイトルバー
bar_h = 90
draw_rect(d1, M, y, W - 2*M, bar_h, fill=C_HEADER)
draw_text(d1, W//2, y + 22, '静岡市 2026年5月 気象分析レポート',
          font(26, bold=True), fill=WHITE, anchor='mt')
draw_text(d1, W//2, y + 60, f'静岡気象観測所（地点番号 47656）　{now_str}',
          font(14), fill=(208, 232, 255), anchor='mt')
y += bar_h + 30

# データ表ヘッダー
draw_text(d1, M, y, '■ 観測データ（半旬別）',
          font(18, bold=True), fill=C_TITLE)
y += 32

headers = ['期間', '平均気温\n(実測) ℃', '平均気温\n(平年) ℃',
           '偏差 ℃', '最高気温\n(実測) ℃', '最低気温\n(実測) ℃', '降水量\n(mm)']
col_w_ratio = [0.19, 0.12, 0.12, 0.10, 0.12, 0.12, 0.17]
tbl_w = W - 2*M
col_widths = [int(r * tbl_w) for r in col_w_ratio]
col_xs = [M + sum(col_widths[:i]) for i in range(len(col_widths))]
row_h  = 52

# ヘッダー行
for i, (cx, cw, hdr) in enumerate(zip(col_xs, col_widths, headers)):
    draw_rect(d1, cx, y, cw-2, row_h, fill=C_HEADER)
    lines = hdr.split('\n')
    ty = y + (row_h - len(lines)*18) // 2
    for ln in lines:
        draw_text(d1, cx + cw//2, ty, ln, font(13, bold=True),
                  fill=WHITE, anchor='mt')
        ty += 18
y += row_h

# データ行
for ri, (_, row) in enumerate(may.iterrows()):
    bg    = C_ROW1 if ri % 2 == 0 else C_ROW2
    avg_r = v(row, c_avg)
    avg_n = v(row, c_navg)
    diff  = diff_str(avg_r, avg_n)

    cells = [
        LABEL_MAP.get(row['Label'], row['Label']),
        fmt(avg_r), fmt(avg_n), diff,
        fmt(v(row, c_max)), fmt(v(row, c_min)), fmt(v(row, c_prec))
    ]
    for ci, (cx, cw, cell) in enumerate(zip(col_xs, col_widths, cells)):
        draw_rect(d1, cx, y, cw-2, row_h, fill=bg,
                  outline=(180,180,180), width=1)
        color = C_RED if (ci == 3 and diff != '―') else BLACK
        fnt   = font(14, bold=(ci==3 and diff!='―'))
        draw_text(d1, cx + cw//2, y + row_h//2, cell,
                  fnt, fill=color, anchor='mm')
    y += row_h

y += 35

# ── コメント ────────────────────────────────────────────────────
def section_header(d, y, mark, title, color):
    draw_text(d, M, y, f'{mark} {title}', font(17, bold=True), fill=color)
    draw_rect(d, M, y+26, tbl_w, 3, fill=color)
    return y + 38

def body_lines(d, y, lines, fnt_size=15):
    fnt = font(fnt_size)
    for l in lines:
        draw_text(d, M+10, y, l, fnt, fill=BLACK)
        y += fnt_size + 8
    return y

draw_text(d1, M, y, '■ 分析コメント', font(18, bold=True), fill=C_TITLE)
draw_rect(d1, M, y+28, tbl_w, 4, fill=C_HEADER)
y += 50

y = section_header(d1, y, '◆', '高温傾向：全期間で平年を上回る', C_RED)
y = body_lines(d1, y, [
    '2026年5月の静岡市は、観測されたすべての半旬で平年気温を超過しており、',
    '平均で約+1.0℃前後の高温が続いています。特に5月後半（5/4：16〜20日）は',
    '平均気温が20.7℃と最も高く、平年差も+1.3℃と今月最大の偏差を記録しています。',
])
y += 12

y = section_header(d1, y, '◆', '上旬の記録的降水 → 中旬以降は乾燥', C_BLUE)
y = body_lines(d1, y, [
    '月初（5/1期：1〜5日）には138.0mmという突出した降水量が観測されました。',
    '平年値（32.9mm）の約4.2倍であり、この期間に強い雨が集中したことがわかります。',
    '一方、5/2・5/3期（6〜15日）は降水量ゼロが続いており、上旬の集中降雨と',
    '中旬以降の乾燥という極端な分布が特徴的です。',
])
y += 12

y = section_header(d1, y, '◆', '気温の上昇トレンド', C_GREEN)
y = body_lines(d1, y, [
    '平均気温は5/1の18.7℃から5/4の20.7℃へと段階的に上昇しており、',
    '初夏へ向けての着実な昇温が見られます。最高気温も25℃台に乗り始め、',
    '夏日（最高気温25℃以上）が意識される時期に入っています。',
])
y += 18

# 総括ボックス
summary_lines = [
    '2026年5月の静岡市は「高温・降水量偏在」の月。梅雨入り前にもかかわらず',
    '上旬に大雨をまとめて受け、その後は晴天と高温が続く展開。農業（水管理・',
    '病害）や熱中症対策において注意が必要な気象条件が続いています。',
]
box_h = 18 + 30 + len(summary_lines) * 26 + 20
d1.rounded_rectangle([M, y, M+tbl_w, y+box_h],
                      radius=10, fill=C_BGBOX,
                      outline=C_HEADER, width=2)
draw_text(d1, W//2, y + 14, '【 総括 】',
          font(16, bold=True), fill=C_TITLE, anchor='mt')
sy = y + 48
for l in summary_lines:
    draw_text(d1, W//2, sy, l, font(14), fill=C_TITLE, anchor='mt')
    sy += 26

# ════════════════════════════════════════════════════════════════
# ページ2：グラフ
# ════════════════════════════════════════════════════════════════
pages = [img1]

if os.path.exists(GRAPH1):
    img2 = Image.new('RGB', (W, H), WHITE)
    d2   = ImageDraw.Draw(img2)

    # ヘッダー
    draw_rect(d2, M, M, W-2*M, 75, fill=C_HEADER)
    draw_text(d2, W//2, M+22,
              '静岡市の気象推移: 2026年実測 vs 平年値（1991-2020）',
              font(22, bold=True), fill=WHITE, anchor='mt')

    # グラフ画像
    graph_img = Image.open(GRAPH1).convert('RGB')
    gw = W - 2*M
    gh = int(graph_img.height * gw / graph_img.width)
    graph_img = graph_img.resize((gw, gh), Image.LANCZOS)
    gy = M + 90
    img2.paste(graph_img, (M, gy))

    # キャプション
    draw_text(d2, W//2, gy + gh + 15,
              '図1：静岡市 2026年実測 vs 平年値（気温・降水量）',
              font(14), fill=C_GRAY, anchor='mt')

    pages.append(img2)

# ── PDF保存 ──────────────────────────────────────────────────────
# RGB → P (パレット) ではなく、RGBのまま保存
# PillowのPDF保存はJPEGエンコーダを使うためRGBを一時PNG化してから結合
import io

def img_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

# PNG経由でPDF保存
pages_rgb = [p.convert('RGB') for p in pages]
pages_rgb[0].save(
    OUTPUT_PDF,
    save_all=True,
    append_images=pages_rgb[1:] if len(pages_rgb) > 1 else [],
    resolution=DPI,
    format='PDF',
)
print(f'PDF保存完了: {OUTPUT_PDF}')
