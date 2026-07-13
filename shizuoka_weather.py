import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# 設定: 静岡 (地点番号: 47656 / アメダスID: 50431)
PREC_NO = 50
BLOCK_NO = 47656
CSV_PATH = 'shizuoka_weather.csv'
IMAGE_PATH = 'shizuoka_weather_plot.png'
LOG_PATH = 'weather_update.log'

def log(message):
    """コンソールとファイルの両方にログを出力する"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(full_message + '\n')

# 日本語フォント設定（OS自動判定）
import platform
if platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'MS Gothic'
else:
    # Linux (GitHub Actions) 用: Noto Sans CJK JP
    plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'Noto Sans CJK', 'DejaVu Sans']

def get_normal_data():
    """気象庁のHPから平年値 (1991-2020) の5日ごとのデータを取得する"""
    url = f"https://www.data.jma.go.jp/stats/etrn/view/nml_sfc_mb5d.php?prec_no={PREC_NO}&block_no={BLOCK_NO}&year=&month=&day=&view=p1"
    
    log(f"平年値データ取得中: {url}")
    
    try:
        response = requests.get(url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.find('table', class_='data2_s')
        if not table:
            log("エラー: 平年値テーブルが見つかりませんでした。")
            return {}
        
        rows = table.find_all('tr')
        normal_dict = {}
        current_month = 1
        
        for row in rows:
            # td または th を取得 (月は th の場合があるため)
            cols = row.find_all(['td', 'th'])
            if len(cols) < 5: continue
            
            # 月の判定 (行の最初のセルが "1月" などの形式かチェック)
            first_cell = cols[0].text.strip()
            
            # 半旬が含まれるセルを探す
            period_idx = -1
            for i, col in enumerate(cols):
                if '半旬' in col.text:
                    period_idx = i
                    break
            
            if period_idx == -1: continue
            
            # 月の更新
            if period_idx == 1: # 0番目が月の列
                m_str = first_cell.replace('月', '')
                if m_str.isdigit():
                    current_month = int(m_str)
            
            period_str = cols[period_idx].text.strip()
            period = int(period_str.replace('第', '').replace('半旬', ''))
            key = f"{current_month}/{period}"
            
            # インデックスの決定: 期間（1~5日）の次の列が降水量
            data_start_idx = period_idx + 2
            
            def to_f(val):
                try: 
                    v = val.strip().replace(')', '').replace(']', '').replace(' ]', '')
                    return float(v)
                except: return 0.0
            
            normal_dict[key] = {
                '平年降水量': to_f(cols[data_start_idx].text),
                '平年平均気温': to_f(cols[data_start_idx + 1].text),
                '平年最高気温': to_f(cols[data_start_idx + 2].text),
                '平年最低気温': to_f(cols[data_start_idx + 3].text)
            }
            
        if not normal_dict:
            log("警告: 平年値データの解析結果が空です。テーブル構造が変わった可能性があります。")
        else:
            log(f"平年値データ取得完了: {len(normal_dict)}件のデータを取得しました。")
        return normal_dict
    except Exception as e:
        log(f"平年値取得時にエラーが発生しました: {e}")
        return {}

def get_2026_data(year=2026):
    """気象庁のHPから2026年の時点データを取得する"""
    url = f"https://www.data.jma.go.jp/stats/etrn/view/mb5daily_s1.php?prec_no={PREC_NO}&block_no={BLOCK_NO}&year={year}&month=&day=&view="
    
    print(f"2026年データ取得中: {url}")
    
    try:
        response = requests.get(url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.find('table', class_='data2_s')
        if not table:
            return []
        
        rows = table.find_all('tr')
        data_list = []
        current_month = 1
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 5: continue
            
            first_text = cols[0].text.strip()
            if '半旬' not in first_text:
                m_str = first_text.replace('月', '')
                if m_str.isdigit():
                    current_month = int(m_str)
                base = 1
            else:
                base = 0
            
            period_str = cols[base].text.strip()
            if '半旬' not in period_str: continue
            
            period = int(period_str.replace('第', '').replace('半旬', ''))
            label = f"{current_month}/{period}"
            sort_date = f"{year}-{current_month:02d}-{(period - 1) * 5 + 1:02d}"
            
            # インデックス: base+4:降水量, base+8:平均, base+9:最高, base+10:最低
            def to_f(val, is_precip=False):
                v = val.strip().replace(')', '').replace(']', '')
                if v == '--' or v == '': return 0.0 if is_precip else None
                try: return float(v)
                except: return None

            t_avg = to_f(cols[base + 8].text)

            # ── 取得範囲の判定（完了済み半旬のみ取得）───────────────
            # 第N半旬はN×5日目まで → (今日-1)//5 = 完了済み半旬数
            # 例）今日=9日 → (9-1)//5=1 → 第1半旬（1〜5日）まで取得
            #     今日=11日 → (11-1)//5=2 → 第2半旬（6〜10日）まで取得
            # ※ GitHub Actions は UTC で動作するため JST(+9h) に変換して判定する
            from datetime import timezone, timedelta
            JST = timezone(timedelta(hours=9))
            now = datetime.now(JST)
            last_complete_period = (now.day - 1) // 5  # 0=なし, 1〜6

            if current_month > now.month:
                # 未来月はすべてスキップ
                continue
            if current_month == now.month and period > last_complete_period:
                # 当月の未確定半旬はスキップ
                continue
            if t_avg is None:
                # 値がない行はスキップ（過去月でも）
                continue

            data_list.append({
                'SortDate': sort_date,
                'Label': label,
                '実測降水量': to_f(cols[base + 4].text, True),
                '実測平均気温': t_avg,
                '実測最高気温': to_f(cols[base + 9].text),
                '実測最低気温': to_f(cols[base + 10].text)
            })
        return data_list
    except Exception as e:
        print(f"2026年データ取得エラー: {e}")
        return []

def update_csv(actual_data, normal_dict):
    """実測値と平年値を統合してCSVを保存する"""
    if not actual_data:
        print("更新する実測データがありません。")
        return
    
    actual_df = pd.DataFrame(actual_data)
    
    # 平年値をマッピング
    normal_rows = []
    for label in actual_df['Label']:
        normal_rows.append(normal_dict.get(label, {}))
    
    normal_df = pd.DataFrame(normal_rows)
    combined_df = pd.concat([actual_df, normal_df], axis=1)
    
    # 期待される列が存在しない場合は空の列を追加（後の処理でのエラー防止）
    expected_cols = ['平年降水量', '平年平均気温', '平年最高気温', '平年最低気温']
    for col in expected_cols:
        if col not in combined_df.columns:
            combined_df[col] = np.nan
    
    combined_df.to_csv(CSV_PATH, index=False)
    log(f"CSVを更新しました: {CSV_PATH}")

def create_plot():
    """実測値と平年値を比較するグラフを作成する"""
    if not os.path.exists(CSV_PATH):
        print("CSVファイルが見つかりません。")
        return
    
    df = pd.read_csv(CSV_PATH)
    if len(df) < 1:
        print("データが不足しています。")
        return
    
    x = np.arange(len(df['Label']))
    width = 0.35  # 棒グラフの幅
    
    fig, ax1 = plt.subplots(figsize=(14, 8))
    
    # 気温のプロット (実線:2026年, 点線:平年値)
    # 2026年 (実線)
    ax1.plot(x, df['実測最高気温'], 'r-', linewidth=2, label='2026年 最高気温')
    ax1.plot(x, df['実測平均気温'], 'g-', linewidth=2, label='2026年 平均気温')
    ax1.plot(x, df['実測最低気温'], 'b-', linewidth=2, label='2026年 最低気温')
    
    # 平年値 (点線)
    if '平年最高気温' in df.columns:
        ax1.plot(x, df['平年最高気温'], 'r--', linewidth=1.5, alpha=0.7, label='平年 最高気温')
        ax1.plot(x, df['平年平均気温'], 'g--', linewidth=1.5, alpha=0.7, label='平年 平均気温')
        ax1.plot(x, df['平年最低気温'], 'b--', linewidth=1.5, alpha=0.7, label='平年 最低気温')
    
    ax1.set_xlabel('時期 (月/半旬)')
    ax1.set_ylabel('気温 (℃)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(df['Label'], rotation=45)
    ax1.legend(loc='upper left', ncol=2, fontsize='small')
    ax1.grid(True, linestyle='--', alpha=0.5)
    
    # 降水量のプロット (右軸, 並べて表示)
    ax2 = ax1.twinx()
    ax2.bar(x - width/2, df['実測降水量'], width, alpha=0.5, color='royalblue', label='2026年 降水量')
    if '平年降水量' in df.columns:
        ax2.bar(x + width/2, df['平年降水量'], width, alpha=0.3, color='gray', label='平年 降水量')
    
    ax2.set_ylabel('降水量 (mm)')
    
    # 降水量の最大値を計算（列が存在しない場合は 0 を使用）
    act_prec_max = df['実測降水量'].max() if '実測降水量' in df.columns else 0
    norm_prec_max = df['平年降水量'].max() if '平年降水量' in df.columns else 0
    # NaNを排除して最大値を取る
    y_max = max(pd.Series([act_prec_max, norm_prec_max]).fillna(0))
    ax2.set_ylim(0, y_max * 1.5 + 50)
    ax2.legend(loc='upper right', fontsize='small')
    
    plt.title(f"静岡市の気象推移比較: 2026年実測 vs 平年値 (1991-2020)")
    
    # 表示の間引き (データが多い場合)
    if len(x) > 20:
        for i, t in enumerate(ax1.get_xticklabels()):
            if i % 2 != 0: t.set_visible(False)

    plt.tight_layout()
    plt.savefig(IMAGE_PATH)
    log(f"比較グラフを保存しました: {IMAGE_PATH}")

def create_normal_only_plot(normal_dict, actual_data=None):
    """平年値データに2026年の実測値を重ねて、1年間の気象推移グラフを作成する"""
    if not normal_dict:
        log("平年値データが空のため、グラフを作成できません。")
        return

    # データを整形
    labels = []
    precip_norm = []
    t_avg_norm = []
    t_max_norm = []
    t_min_norm = []
    
    precip_2026 = []
    t_avg_2026 = []
    t_max_2026 = []
    t_min_2026 = []

    # 2026年データのマッピング
    actual_map = {d['Label']: d for d in (actual_data or [])}

    # 1月から12月まで順に並べる
    for m in range(1, 13):
        for p in range(1, 7):
            key = f"{m}/{p}"
            if key in normal_dict:
                d = normal_dict[key]
                labels.append(key)
                precip_norm.append(d['平年降水量'])
                t_avg_norm.append(d['平年平均気温'])
                t_max_norm.append(d['平年最高気温'])
                t_min_norm.append(d['平年最低気温'])
                
                # 2026年データがあれば追加
                if key in actual_map:
                    ad = actual_map[key]
                    precip_2026.append(ad['実測降水量'])
                    t_avg_2026.append(ad['実測平均気温'])
                    t_max_2026.append(ad['実測最高気温'])
                    t_min_2026.append(ad['実測最低気温'])
                else:
                    precip_2026.append(np.nan)
                    t_avg_2026.append(np.nan)
                    t_max_2026.append(np.nan)
                    t_min_2026.append(np.nan)

    x = np.arange(len(labels))
    width = 0.35
    
    fig, ax1 = plt.subplots(figsize=(16, 9))
    
    # 気温 (平年値: 点線, 2026年: 実線)
    # 平年値
    ax1.plot(x, t_max_norm, color='tomato', linestyle='--', alpha=0.6, label='平年 最高気温', linewidth=1)
    ax1.plot(x, t_avg_norm, color='mediumseagreen', linestyle='--', alpha=0.6, label='平年 平均気温', linewidth=1)
    ax1.plot(x, t_min_norm, color='cornflowerblue', linestyle='--', alpha=0.6, label='平年 最低気温', linewidth=1)
    
    # 2026年
    ax1.plot(x, t_max_2026, color='red', linestyle='-', marker='o', markersize=4, label='2026年 最高気温', linewidth=2.5)
    ax1.plot(x, t_avg_2026, color='green', linestyle='-', marker='s', markersize=4, label='2026年 平均気温', linewidth=2.5)
    ax1.plot(x, t_min_2026, color='blue', linestyle='-', marker='^', markersize=4, label='2026年 最低気温', linewidth=2.5)
    
    ax1.set_xlabel('時期 (月/半旬)')
    ax1.set_ylabel('気温 (℃)')
    ax1.set_ylim(-5, 40) # 静岡の気温範囲をカバー
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=45)
    ax1.legend(loc='upper left', ncol=2, fontsize='small')
    ax1.grid(True, linestyle=':', alpha=0.6)
    
    # 降水量 (棒グラフ: 平年値を後ろに、2026年前面に)
    ax2 = ax1.twinx()
    # NoneをNaNに変換してNumPy配列化
    precip_norm_arr = np.array([v if v is not None else np.nan for v in precip_norm], dtype=float)
    precip_2026_arr = np.array([v if v is not None else np.nan for v in precip_2026], dtype=float)
    ax2.bar(x - width/2, precip_norm_arr, width, alpha=0.2, color='gray', label='平年 降水量')
    ax2.bar(x + width/2, precip_2026_arr, width, alpha=0.5, color='royalblue', label='2026年 降水量')
    
    ax2.set_ylabel('降水量 (mm)')
    # 降水量の最大値に合わせてスケール調整
    p_max_norm = np.nanmax(precip_norm_arr) if len(precip_norm_arr) > 0 and not np.all(np.isnan(precip_norm_arr)) else 0
    p_max_2026 = np.nanmax(precip_2026_arr) if len(precip_2026_arr) > 0 and not np.all(np.isnan(precip_2026_arr)) else 0
    p_max = max(p_max_norm, p_max_2026) if max(p_max_norm, p_max_2026) > 0 else 100
    ax2.set_ylim(0, p_max * 1.5 + 20)
    ax2.legend(loc='upper right', fontsize='small')
    
    plt.title("静岡市の気象推移: 2026年実測 vs 平年値 (1991-2020)")
    
    # 表示の間引き
    for i, t in enumerate(ax1.get_xticklabels()):
        if i % 3 != 0: t.set_visible(False)

    plt.tight_layout()
    norm_image_path = 'shizuoka_normal_plot.png'
    plt.savefig(norm_image_path)
    log(f"重ね合わせグラフを保存しました: {norm_image_path}")

if __name__ == "__main__":
    log("--- 自動更新処理開始 ---")
    # 1. 2026年の実測値を取得
    actual_data = get_2026_data(2026)
    
    # 2. 平年値を取得
    normal_dict = get_normal_data()
    
    # 3. 平年値単体のグラフ作成
    create_normal_only_plot(normal_dict, actual_data)
    
    # 4. CSV更新と比較グラフ作成
    update_csv(actual_data, normal_dict)
    create_plot()
    log("--- 自動更新処理完了 ---")
