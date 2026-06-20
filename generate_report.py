"""
generate_report.py
静岡市 気象データ 半旬別 平年比較レポート生成スクリプト
CSVを読み込み、各半旬の実測値と平年値を比較したコメント付きHTMLレポートを出力する。
"""

import os
import base64
import pandas as pd
import numpy as np
from datetime import datetime

# ─── パス設定 ────────────────────────────────────────────────
WORKDIR       = os.path.dirname(os.path.abspath(__file__))
CSV_PATH      = os.path.join(WORKDIR, 'shizuoka_weather.csv')
MAIN_PLOT     = os.path.join(WORKDIR, 'shizuoka_normal_plot.png')
COMP_PLOT     = os.path.join(WORKDIR, 'shizuoka_weather_plot.png')
OUTPUT_HTML   = os.path.join(WORKDIR, 'shizuoka_weather_report.html')
LOG_PATH      = os.path.join(WORKDIR, 'weather_update.log')

YEAR          = 2026
STATION_NAME  = '静岡市'


# ─── ユーティリティ ─────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def img_to_base64(path):
    """画像ファイルをBase64文字列に変換（HTMLへ埋め込み用）"""
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


# ─── コメント生成ロジック ────────────────────────────────────

def temp_comment(diff: float, label: str) -> str:
    """気温差からコメントを生成する"""
    if diff is None or np.isnan(diff):
        return '―'
    abs_d = abs(diff)
    sign  = '高' if diff > 0 else '低'
    sign_neg = '低' if diff > 0 else '高'
    if abs_d >= 3.0:
        return f'平年より<strong>{abs_d:.1f}℃大幅に{sign}い</strong>'
    elif abs_d >= 1.5:
        return f'平年より{abs_d:.1f}℃{sign}い'
    elif abs_d >= 0.5:
        return f'平年よりやや{sign}い（{diff:+.1f}℃）'
    else:
        return f'平年並み（{diff:+.1f}℃）'


def precip_comment(actual: float, normal: float) -> str:
    """降水量から平年比コメントを生成する"""
    if actual is None or normal is None:
        return '―'
    if np.isnan(actual) or np.isnan(normal):
        return '―'
    if normal == 0:
        if actual == 0:
            return '降水なし（平年も同様）'
        else:
            return f'平年0mmに対し{actual:.1f}mm'
    ratio = actual / normal
    diff  = actual - normal
    if ratio >= 3.0:
        return f'平年の<strong>{ratio:.1f}倍（+{diff:.0f}mm）</strong>と著しく多い'
    elif ratio >= 1.5:
        return f'平年より多い（{ratio:.1f}倍 / +{diff:.0f}mm）'
    elif ratio >= 0.8:
        return f'平年並み（{ratio:.1f}倍 / {diff:+.0f}mm）'
    elif ratio >= 0.3:
        return f'平年より少ない（{ratio:.1f}倍 / {diff:+.0f}mm）'
    else:
        return f'<strong>著しく少ない</strong>（{ratio:.1f}倍 / {diff:+.0f}mm）'


def overall_comment(row) -> str:
    """1半旬のトータル概評コメントを生成する"""
    t_diff   = row.get('平均気温差')
    p_ratio  = row.get('降水量比')
    parts    = []

    # 気温評価
    if t_diff is not None and not np.isnan(t_diff):
        if abs(t_diff) >= 3.0:
            sign = '高温' if t_diff > 0 else '低温'
            parts.append(f'<span class="badge badge-{"hot" if t_diff>0 else "cold"}">{sign}顕著</span>')
        elif abs(t_diff) >= 1.5:
            sign = '高め' if t_diff > 0 else '低め'
            parts.append(f'<span class="badge badge-{"warm" if t_diff>0 else "cool"}">{sign}</span>')

    # 降水量評価
    if p_ratio is not None and not np.isnan(p_ratio):
        if p_ratio >= 3.0:
            parts.append('<span class="badge badge-wet">多雨顕著</span>')
        elif p_ratio >= 1.5:
            parts.append('<span class="badge badge-wet-mild">やや多雨</span>')
        elif p_ratio <= 0.3:
            parts.append('<span class="badge badge-dry">寡雨顕著</span>')
        elif p_ratio <= 0.6:
            parts.append('<span class="badge badge-dry-mild">やや少雨</span>')

    if not parts:
        parts.append('<span class="badge badge-normal">平年並み</span>')

    return ' '.join(parts)


def period_label(label: str) -> str:
    """'6/3' → '6月 第3半旬（11〜15日）' のように変換する"""
    m, p = label.split('/')
    m, p = int(m), int(p)
    day_start = (p - 1) * 5 + 1
    day_end   = p * 5 if p < 6 else 31  # 第6半旬は月末まで
    return f'{m}月 第{p}半旬（{day_start}〜{day_end}日ごろ）'


# ─── 月別サマリーコメント ────────────────────────────────────

def month_summary(month_df) -> str:
    """月のデータフレームから月別サマリーを生成する"""
    avg_t_diff = month_df['平均気温差'].mean()
    total_actual = month_df['実測降水量'].sum()
    total_normal = month_df['平年降水量'].sum()

    lines = []
    # 気温
    if abs(avg_t_diff) >= 2.0:
        sign = '高温' if avg_t_diff > 0 else '低温'
        lines.append(f'月平均気温は平年より<b>{avg_t_diff:+.1f}℃</b>と{sign}傾向が顕著でした。')
    elif abs(avg_t_diff) >= 0.8:
        sign = '高め' if avg_t_diff > 0 else '低め'
        lines.append(f'月平均気温は平年よりやや{sign}（{avg_t_diff:+.1f}℃）でした。')
    else:
        lines.append(f'月平均気温は概ね平年並み（{avg_t_diff:+.1f}℃）でした。')

    # 降水量
    if total_normal > 0:
        ratio = total_actual / total_normal
        diff  = total_actual - total_normal
        if ratio >= 2.0:
            lines.append(f'月降水量は平年の<b>{ratio:.1f}倍（+{diff:.0f}mm）</b>と著しく多くなりました。')
        elif ratio >= 1.3:
            lines.append(f'月降水量は平年より多く（{ratio:.1f}倍 / +{diff:.0f}mm）でした。')
        elif ratio <= 0.5:
            lines.append(f'月降水量は平年の<b>{ratio:.1f}倍（{diff:.0f}mm）</b>と著しく少なくなりました。')
        elif ratio <= 0.8:
            lines.append(f'月降水量は平年より少なめ（{ratio:.1f}倍 / {diff:.0f}mm）でした。')
        else:
            lines.append(f'月降水量は概ね平年並み（{ratio:.1f}倍 / {diff:+.0f}mm）でした。')
    return '　'.join(lines)


# ─── HTML生成 ────────────────────────────────────────────────

def render_html(df: pd.DataFrame, generated_at: str) -> str:
    """データフレームからHTMLを組み立てる"""

    main_b64 = img_to_base64(MAIN_PLOT)
    comp_b64 = img_to_base64(COMP_PLOT)

    # 月ごとにグループ化
    months = sorted(df['月'].unique())

    # 月別セクションHTML
    month_sections = ''
    for m in months:
        mdf = df[df['月'] == m].copy()
        summary = month_summary(mdf)
        month_name = f'{m}月'

        # 各行のHTMLを構築
        rows_html = ''
        for _, row in mdf.iterrows():
            t_avg_diff  = row['平均気温差']
            t_max_diff  = row['最高気温差']
            t_min_diff  = row['最低気温差']
            p_actual    = row['実測降水量']
            p_normal    = row['平年降水量']

            badge_html  = overall_comment(row)
            p_cmt       = precip_comment(p_actual, p_normal)
            t_avg_cmt   = temp_comment(t_avg_diff, '平均')
            t_max_cmt   = temp_comment(t_max_diff, '最高')
            t_min_cmt   = temp_comment(t_min_diff, '最低')
            p_label     = period_label(row['Label'])

            def fmt(v, unit=''):
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    return '―'
                return f'{v:.1f}{unit}'

            # 気温差のクラス
            def diff_cls(d):
                if d is None or np.isnan(d): return ''
                if d >= 2.0: return 'class="val-hot"'
                if d >= 0.5: return 'class="val-warm"'
                if d <= -2.0: return 'class="val-cold"'
                if d <= -0.5: return 'class="val-cool"'
                return 'class="val-normal"'

            rows_html += f'''
            <tr>
              <td class="period-cell">
                <div class="period-name">{p_label}</div>
                <div class="period-badges">{badge_html}</div>
              </td>
              <td class="data-group">
                <div class="data-row">
                  <span class="data-label">実測</span>
                  <span class="data-val">{fmt(row["実測平均気温"],"℃")}</span>
                  <span class="data-val">{fmt(row["実測最高気温"],"℃")}</span>
                  <span class="data-val">{fmt(row["実測最低気温"],"℃")}</span>
                </div>
                <div class="data-row">
                  <span class="data-label">平年</span>
                  <span class="data-val muted">{fmt(row["平年平均気温"],"℃")}</span>
                  <span class="data-val muted">{fmt(row["平年最高気温"],"℃")}</span>
                  <span class="data-val muted">{fmt(row["平年最低気温"],"℃")}</span>
                </div>
                <div class="data-row">
                  <span class="data-label">差</span>
                  <span {diff_cls(t_avg_diff)}>{fmt(t_avg_diff,"℃")}</span>
                  <span {diff_cls(t_max_diff)}>{fmt(t_max_diff,"℃")}</span>
                  <span {diff_cls(t_min_diff)}>{fmt(t_min_diff,"℃")}</span>
                </div>
              </td>
              <td class="data-group">
                <div class="data-row">
                  <span class="data-label">実測</span>
                  <span class="data-val">{fmt(p_actual,"mm")}</span>
                </div>
                <div class="data-row">
                  <span class="data-label">平年</span>
                  <span class="data-val muted">{fmt(p_normal,"mm")}</span>
                </div>
              </td>
              <td class="comment-cell">
                <div class="comment-item">🌡️ 平均: {t_avg_cmt}</div>
                <div class="comment-item">☀️ 最高: {t_max_cmt}</div>
                <div class="comment-item">🌙 最低: {t_min_cmt}</div>
                <div class="comment-item">🌧️ 降水: {p_cmt}</div>
              </td>
            </tr>'''

        month_sections += f'''
        <section class="month-section" id="month-{m}">
          <div class="month-header">
            <h2 class="month-title">{m}月の気象概況</h2>
            <p class="month-summary">{summary}</p>
          </div>
          <div class="table-wrapper">
            <table class="weather-table">
              <thead>
                <tr>
                  <th class="th-period">期間</th>
                  <th class="th-temp">
                    気温（平均 / 最高 / 最低）<br>
                    <span class="th-sub">実測 → 平年 → 差</span>
                  </th>
                  <th class="th-precip">降水量</th>
                  <th class="th-comment">コメント</th>
                </tr>
              </thead>
              <tbody>
                {rows_html}
              </tbody>
            </table>
          </div>
        </section>'''

    # ナビゲーション
    nav_items = ''.join(
        f'<a href="#month-{m}" class="nav-item">{m}月</a>' for m in months
    )

    # グラフ埋め込み
    charts_html = ''
    if main_b64:
        charts_html += f'''
        <section class="chart-section">
          <h2 class="section-title">📈 年間推移グラフ（実測 vs 平年値）</h2>
          <img src="data:image/png;base64,{main_b64}" alt="年間気象推移グラフ" class="chart-img">
        </section>'''
    if comp_b64:
        charts_html += f'''
        <section class="chart-section">
          <h2 class="section-title">📊 気温・降水量 比較グラフ</h2>
          <img src="data:image/png;base64,{comp_b64}" alt="気温降水量比較グラフ" class="chart-img">
        </section>'''

    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{STATION_NAME} {YEAR}年 気象データ 半旬別平年比較レポート</title>
  <meta name="description" content="{STATION_NAME}の{YEAR}年気象データを半旬ごとに平年値と比較・分析したレポート。気温・降水量の差異をわかりやすくコメント化。">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700&family=Inter:wght@300;400;500;700&display=swap');

    :root {{
      --bg:          #0f1117;
      --bg2:         #1a1d27;
      --bg3:         #22263a;
      --border:      #2e3350;
      --accent:      #5b8af0;
      --accent2:     #7c6af7;
      --text:        #e2e8f7;
      --text-sub:    #8b96b2;
      --hot:         #ff6b6b;
      --warm:        #ff9f43;
      --cool:        #74b9ff;
      --cold:        #a29bfe;
      --wet:         #0984e3;
      --wet-mild:    #74b9ff;
      --dry:         #e17055;
      --dry-mild:    #fdcb6e;
      --normal:      #55efc4;
      --radius:      12px;
      --radius-sm:   6px;
    }}

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Noto Sans JP', 'Inter', sans-serif;
      min-height: 100vh;
      line-height: 1.6;
    }}

    /* ─── ヘッダー ── */
    .site-header {{
      background: linear-gradient(135deg, #1a1d27 0%, #1e2340 50%, #16213e 100%);
      border-bottom: 1px solid var(--border);
      padding: 32px 24px 24px;
      position: sticky;
      top: 0;
      z-index: 100;
      backdrop-filter: blur(12px);
    }}
    .header-inner {{
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      gap: 20px;
      flex-wrap: wrap;
    }}
    .header-icon {{ font-size: 2.5rem; }}
    .header-text h1 {{
      font-size: 1.5rem;
      font-weight: 700;
      background: linear-gradient(135deg, #5b8af0, #a29bfe);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }}
    .header-text .subtitle {{
      color: var(--text-sub);
      font-size: 0.85rem;
      margin-top: 2px;
    }}
    .generated-at {{
      margin-left: auto;
      color: var(--text-sub);
      font-size: 0.8rem;
      text-align: right;
    }}

    /* ─── ナビゲーション ── */
    .month-nav {{
      background: var(--bg2);
      border-bottom: 1px solid var(--border);
      padding: 10px 24px;
      display: flex;
      gap: 6px;
      overflow-x: auto;
      position: sticky;
      top: 94px;
      z-index: 99;
    }}
    .nav-item {{
      color: var(--text-sub);
      text-decoration: none;
      padding: 4px 14px;
      border-radius: 20px;
      font-size: 0.85rem;
      border: 1px solid var(--border);
      white-space: nowrap;
      transition: all 0.2s ease;
    }}
    .nav-item:hover {{
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }}

    /* ─── メインコンテンツ ── */
    .main {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 24px;
    }}

    /* ─── 月セクション ── */
    .month-section {{
      margin-bottom: 48px;
      scroll-margin-top: 140px;
    }}
    .month-header {{
      background: linear-gradient(135deg, var(--bg2), var(--bg3));
      border: 1px solid var(--border);
      border-radius: var(--radius) var(--radius) 0 0;
      padding: 20px 24px;
    }}
    .month-title {{
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--accent);
      margin-bottom: 8px;
    }}
    .month-summary {{
      color: var(--text-sub);
      font-size: 0.9rem;
      line-height: 1.7;
    }}
    .month-summary b {{
      color: var(--text);
    }}

    /* ─── テーブル ── */
    .table-wrapper {{
      overflow-x: auto;
      border: 1px solid var(--border);
      border-top: none;
      border-radius: 0 0 var(--radius) var(--radius);
    }}
    .weather-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
    }}
    .weather-table thead tr {{
      background: var(--bg3);
    }}
    .weather-table th {{
      padding: 12px 16px;
      text-align: center;
      font-weight: 600;
      color: var(--text-sub);
      font-size: 0.8rem;
      border-bottom: 1px solid var(--border);
      border-right: 1px solid var(--border);
    }}
    .weather-table th:last-child {{ border-right: none; }}
    .th-sub {{
      font-size: 0.7rem;
      font-weight: 400;
      opacity: 0.7;
    }}

    .weather-table tbody tr {{
      border-bottom: 1px solid var(--border);
      transition: background 0.15s ease;
    }}
    .weather-table tbody tr:last-child {{ border-bottom: none; }}
    .weather-table tbody tr:hover {{ background: rgba(91,138,240,0.05); }}

    .weather-table td {{
      padding: 14px 16px;
      vertical-align: top;
      border-right: 1px solid var(--border);
    }}
    .weather-table td:last-child {{ border-right: none; }}

    /* 期間セル */
    .period-cell {{ min-width: 180px; }}
    .period-name {{
      font-weight: 600;
      font-size: 0.9rem;
      color: var(--text);
      margin-bottom: 6px;
    }}
    .period-badges {{ display: flex; gap: 4px; flex-wrap: wrap; }}

    /* データグループ */
    .data-group {{ min-width: 160px; }}
    .data-row {{
      display: flex;
      gap: 8px;
      align-items: center;
      padding: 2px 0;
      font-size: 0.82rem;
    }}
    .data-label {{
      color: var(--text-sub);
      min-width: 28px;
      font-size: 0.75rem;
    }}
    .data-val {{ min-width: 46px; text-align: right; font-variant-numeric: tabular-nums; }}
    .muted {{ color: var(--text-sub); }}

    /* コメントセル */
    .comment-cell {{ min-width: 220px; }}
    .comment-item {{
      font-size: 0.82rem;
      color: var(--text-sub);
      padding: 2px 0;
      line-height: 1.5;
    }}
    .comment-item strong {{ color: #fff; }}

    /* ─── 数値のカラーリング ── */
    .val-hot   {{ color: var(--hot);  font-weight: 600; }}
    .val-warm  {{ color: var(--warm); }}
    .val-cool  {{ color: var(--cool); }}
    .val-cold  {{ color: var(--cold); font-weight: 600; }}
    .val-normal {{ color: var(--text); }}

    /* ─── バッジ ── */
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.72rem;
      font-weight: 600;
      letter-spacing: 0.03em;
    }}
    .badge-hot     {{ background: rgba(255,107,107,0.2); color: var(--hot);       border: 1px solid rgba(255,107,107,0.4); }}
    .badge-warm    {{ background: rgba(255,159,67,0.2);  color: var(--warm);      border: 1px solid rgba(255,159,67,0.4); }}
    .badge-cool    {{ background: rgba(116,185,255,0.2); color: var(--cool);      border: 1px solid rgba(116,185,255,0.4); }}
    .badge-cold    {{ background: rgba(162,155,254,0.2); color: var(--cold);      border: 1px solid rgba(162,155,254,0.4); }}
    .badge-wet     {{ background: rgba(9,132,227,0.2);   color: var(--wet);       border: 1px solid rgba(9,132,227,0.4); }}
    .badge-wet-mild {{ background: rgba(116,185,255,0.15); color: var(--wet-mild); border: 1px solid rgba(116,185,255,0.3); }}
    .badge-dry     {{ background: rgba(225,112,85,0.2);  color: var(--dry);       border: 1px solid rgba(225,112,85,0.4); }}
    .badge-dry-mild {{ background: rgba(253,203,110,0.2); color: var(--dry-mild); border: 1px solid rgba(253,203,110,0.4); }}
    .badge-normal  {{ background: rgba(85,239,196,0.15); color: var(--normal);    border: 1px solid rgba(85,239,196,0.3); }}

    /* ─── グラフセクション ── */
    .chart-section {{
      margin-bottom: 48px;
    }}
    .section-title {{
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 16px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border);
    }}
    .chart-img {{
      width: 100%;
      border-radius: var(--radius);
      border: 1px solid var(--border);
      display: block;
    }}

    /* ─── フッター ── */
    .site-footer {{
      text-align: center;
      padding: 24px;
      color: var(--text-sub);
      font-size: 0.8rem;
      border-top: 1px solid var(--border);
      margin-top: 32px;
    }}

    /* ─── スクロールバー ── */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: var(--bg); }}
    ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--accent); }}
  </style>
</head>
<body>

  <header class="site-header">
    <div class="header-inner">
      <div class="header-icon">🌤</div>
      <div class="header-text">
        <h1>{STATION_NAME} {YEAR}年 気象データ 半旬別平年比較レポート</h1>
        <div class="subtitle">データソース: 気象庁｜平年値: 1991-2020年｜半旬 = 5日ごとの区切り</div>
      </div>
      <div class="generated-at">
        生成日時<br>{generated_at}
      </div>
    </div>
  </header>

  <nav class="month-nav">
    {nav_items}
    <a href="#charts" class="nav-item">📈 グラフ</a>
  </nav>

  <main class="main">
    {month_sections}

    <div id="charts">
      {charts_html}
    </div>
  </main>

  <footer class="site-footer">
    {STATION_NAME} 気象データ 半旬別平年比較レポート｜{YEAR}年｜データ: 気象庁 地点番号 47656
  </footer>

</body>
</html>'''


# ─── メイン処理 ─────────────────────────────────────────────

def main():
    log("--- レポート生成開始 ---")

    if not os.path.exists(CSV_PATH):
        log(f"エラー: CSVファイルが見つかりません: {CSV_PATH}")
        log("先に shizuoka_weather.py を実行してデータを取得してください。")
        return

    df = pd.read_csv(CSV_PATH)
    if df.empty:
        log("エラー: CSVにデータがありません。")
        return

    log(f"CSVを読み込みました: {len(df)}行")

    # 差分・比率の計算
    df['平均気温差'] = df['実測平均気温'] - df['平年平均気温']
    df['最高気温差'] = df['実測最高気温'] - df['平年最高気温']
    df['最低気温差'] = df['実測最低気温'] - df['平年最低気温']
    df['降水量比']   = df.apply(
        lambda r: r['実測降水量'] / r['平年降水量'] if r['平年降水量'] > 0 else np.nan,
        axis=1
    )

    # 月列を追加
    df['月'] = df['Label'].apply(lambda x: int(x.split('/')[0]))

    generated_at = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    html = render_html(df, generated_at)

    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)

    log(f"レポートを出力しました: {OUTPUT_HTML}")
    log("--- レポート生成完了 ---")

    # ブラウザで自動表示
    import webbrowser
    webbrowser.open(OUTPUT_HTML)
    log("ブラウザで開きました。")


if __name__ == '__main__':
    main()
