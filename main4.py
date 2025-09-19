import cv2
import numpy as np
import pyautogui
import time
import threading
import sys
import msvcrt
import keyboard
from multiprocessing import Pool, cpu_count
from functools import partial

def get_drawing_area():
    print("描画範囲を指定してください:")
    print("1. 左上の角をクリックしてください")

    while True:
        try:
            input("準備ができたらEnterを押してください...")
            print("3秒後に左上の点を記録します。マウスを左上の位置に置いてください！")
            time.sleep(3)
            x1, y1 = pyautogui.position()
            print(f"左上の点: ({x1}, {y1})")
            break
        except KeyboardInterrupt:
            print("キャンセルされました")
            return None

    print("2. 右下の角をクリックしてください")

    while True:
        try:
            input("準備ができたらEnterを押してください...")
            print("3秒後に右下の点を記録します。マウスを右下の位置に置いてください！")
            time.sleep(3)
            x2, y2 = pyautogui.position()
            print(f"右下の点: ({x2}, {y2})")
            break
        except KeyboardInterrupt:
            print("キャンセルされました")
            return None

    return (x1, y1, x2, y2)

def floyd_steinberg_dither(img, black_threshold=80, white_threshold=200):
    """
    改良版フロイド・スタインバーグ・ディザリング
    
    Args:
        img: 入力画像
        black_threshold: この値以下は強制的に黒 (0-255)
        white_threshold: この値以上は強制的に白 (0-255)
    """
    img = img.astype(np.float32) / 255.0
    height, width = img.shape
    
    # 閾値を0-1の範囲に変換
    black_thresh = black_threshold / 255.0
    white_thresh = white_threshold / 255.0
    
    print(f"ディザリング設定: 黒固定 ≤{black_threshold}, 白固定 ≥{white_threshold}, 中間部のみディザリング")
    
    for y in range(height - 1):
        for x in range(1, width - 1):
            old_pixel = img[y, x]
            
            # 閾値による固定処理
            if old_pixel <= black_thresh:
                new_pixel = 0.0  # 強制的に黒
            elif old_pixel >= white_thresh:
                new_pixel = 1.0  # 強制的に白
            else:
                # 中間部のみディザリング処理
                new_pixel = 1.0 if old_pixel > 0.5 else 0.0
            
            img[y, x] = new_pixel
            
            # 誤差拡散（固定された部分は誤差が小さい）
            error = old_pixel - new_pixel
            
            # 誤差拡散の重みを調整（固定部分は誤差拡散を抑制）
            if old_pixel <= black_thresh or old_pixel >= white_thresh:
                # 固定部分は誤差拡散を弱める
                error_weight = 0.3
            else:
                # 中間部は通常の誤差拡散
                error_weight = 1.0
            
            img[y, x + 1] += error * error_weight * 7/16
            img[y + 1, x - 1] += error * error_weight * 3/16
            img[y + 1, x] += error * error_weight * 5/16
            img[y + 1, x + 1] += error * error_weight * 1/16
    
    return (img * 255).astype(np.uint8)

def process_row_chunk(args):
    """行チャンクを並列処理する関数"""
    y_chunk, y_to_x_dict, draw_x1, draw_y1, draw_width, draw_height = args
    paths = []
    
    for target_y in y_chunk:
        # この行の黒ピクセルのX座標を取得
        if target_y not in y_to_x_dict:
            continue
            
        x_coords = sorted(y_to_x_dict[target_y])
        if not x_coords:
            continue
        
        # 座標ペアを作成
        row_pixels = [(x, target_y) for x in x_coords]
        
        # 連続する範囲を見つける
        current_path = [row_pixels[0]]
        
        for i in range(1, len(row_pixels)):
            prev_x = row_pixels[i-1][0]
            curr_x = row_pixels[i][0]
            
            # 連続している（距離が近い）場合は同じパスに追加
            if abs(curr_x - prev_x) <= 3:
                current_path.append(row_pixels[i])
            else:
                # パスを保存して新しいパスを開始
                if len(current_path) >= 2:
                    paths.append(current_path)
                current_path = [row_pixels[i]]
        
        # 最後のパスを追加
        if len(current_path) >= 2:
            paths.append(current_path)
    
    return paths

def create_optimized_paths(binary_img, draw_x1, draw_y1, draw_width, draw_height):
    """黒ピクセルを最小クリック数で描画するパスを生成（並列処理版）"""
    height, width = binary_img.shape
    
    print("黒ピクセルを検索中...")
    # NumPyを使って高速に黒ピクセルを取得
    black_y, black_x = np.where(binary_img == 0)
    
    if len(black_x) == 0:
        return []
    
    print(f"黒ピクセル数: {len(black_x)}")
    
    # 描画座標に変換
    draw_x_coords = draw_x1 + ((black_x / width) * draw_width).astype(int)
    draw_y_coords = draw_y1 + ((black_y / height) * draw_height).astype(int)
    
    # Y座標ごとにX座標をグループ化（効率的なデータ構造）
    y_to_x_dict = {}
    for x, y in zip(draw_x_coords, draw_y_coords):
        if y not in y_to_x_dict:
            y_to_x_dict[y] = []
        y_to_x_dict[y].append(x)
    
    # Y座標の一意な値を取得
    unique_y = sorted(y_to_x_dict.keys())
    
    # CPUコア数を取得（メモリ使用量を考慮して制限）
    pixel_count = len(black_x)
    if pixel_count > 200000:
        num_cores = min(cpu_count(), 4)  # 大量のピクセルの場合は4コアまで
    elif pixel_count > 100000:
        num_cores = min(cpu_count(), 6)  # 中程度の場合は6コアまで
    else:
        num_cores = min(cpu_count(), 8)  # 少ない場合は8コアまで
    
    print(f"並列処理開始: {num_cores}コア使用 (ピクセル数: {pixel_count})")
    
    # Y座標をチャンクに分割
    chunk_size = max(1, len(unique_y) // num_cores)
    y_chunks = [unique_y[i:i + chunk_size] for i in range(0, len(unique_y), chunk_size)]
    
    # 並列処理用の引数を準備
    args_list = [(chunk, y_to_x_dict, draw_x1, draw_y1, draw_width, draw_height) 
                 for chunk in y_chunks if chunk]
    
    # 並列処理でパスを生成
    with Pool(processes=num_cores) as pool:
        chunk_results = pool.map(process_row_chunk, args_list)
    
    # 結果をマージ
    all_paths = []
    for chunk_paths in chunk_results:
        all_paths.extend(chunk_paths)
    
    print(f"並列処理完了: {len(all_paths)}パス生成")
    return all_paths

# 中止フラグとリスナー
stop_drawing = False

def keyboard_listener():
    """キーボード監視スレッド（改善版）"""
    global stop_drawing
    try:
        while not stop_drawing:
            # Escキー、Spaceキー、Enterキーのいずれかで中止
            if keyboard.is_pressed('esc') or keyboard.is_pressed('space') or keyboard.is_pressed('enter'):
                stop_drawing = True
                print("\n描画を中止しています...")
                pyautogui.mouseUp()
                break
            time.sleep(0.05)  # より頻繁にチェック
    except Exception as e:
        print(f"キーボード監視エラー: {e}")
        # フォールバック: Windows標準の方法
        try:
            while not stop_drawing:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key in [b'\r', b' ', b'\x1b']:  # Enter、Space、Esc
                        stop_drawing = True
                        print("\n描画を中止しています...")
                        pyautogui.mouseUp()
                        break
                time.sleep(0.1)
        except:
            pass

def check_stop():
    """中止フラグをチェック"""
    global stop_drawing
    if stop_drawing:
        pyautogui.mouseUp()
        return True
    return False

def main():
    # 入力画像を選択
    print("入力画像を選択してください:")
    print("1. input.png")
    print("2. 123886908_p0_master1200.jpg")
    print("3. その他のファイル名を入力")
    
    choice = input("選択 (1/2/3): ")
    
    if choice == "1":
        input_file = "input.png"
    elif choice == "2":
        input_file = "123886908_p0_master1200.jpg"
    elif choice == "3":
        input_file = input("ファイル名を入力: ")
    else:
        input_file = "input.png"
    
    # 元画像を読み込み
    img = cv2.imread(input_file, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"エラー: {input_file}が見つかりません")
        return
    
    print(f"元画像サイズ: {img.shape}")
    
    # 描画範囲を取得
    area = get_drawing_area()
    if area is None:
        return
    
    draw_x1, draw_y1, draw_x2, draw_y2 = area
    draw_width = abs(draw_x2 - draw_x1)
    draw_height = abs(draw_y2 - draw_y1)
    
    print(f"描画範囲: ({draw_x1}, {draw_y1}) から ({draw_x2}, {draw_y2})")
    print(f"サイズ: {draw_width} x {draw_height}")
    
    # 描画範囲に合わせて画像を最適化
    height, width = img.shape
    target_width = min(draw_width, 1000)  # 最大1000ピクセルに制限
    target_height = min(draw_height, 1000)
    
    # アスペクト比を保持して最適なサイズを計算
    aspect_ratio = width / height
    target_aspect = target_width / target_height
    
    if aspect_ratio > target_aspect:
        # 横長の場合
        new_width = target_width
        new_height = int(target_width / aspect_ratio)
    else:
        # 縦長の場合
        new_height = target_height
        new_width = int(target_height * aspect_ratio)
    
    # リサイズが必要な場合のみ実行
    if new_width != width or new_height != height:
        img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
        print(f"描画範囲に最適化してリサイズ: {img.shape}")
    
    # 閾値設定
    print("\n閾値設定（黒ピクセル数を調整）:")
    print("1. デフォルト設定 (黒≤80, 白≥200)")
    print("2. 強めの設定 (黒≤100, 白≥180) - 黒ピクセル多め")
    print("3. 弱めの設定 (黒≤60, 白≥220) - 黒ピクセル少なめ")
    print("4. 軽量設定 (黒≤120, 白≥160) - 大幅削減")
    print("5. 超軽量設定 (黒≤140, 白≥140) - 最大削減")
    print("6. カスタム設定")
    
    threshold_choice = input("選択 (1/2/3/4/5/6): ")
    
    if threshold_choice == "1":
        black_threshold, white_threshold = 80, 200
    elif threshold_choice == "2":
        black_threshold, white_threshold = 100, 180
    elif threshold_choice == "3":
        black_threshold, white_threshold = 60, 220
    elif threshold_choice == "4":
        black_threshold, white_threshold = 120, 160
        print("軽量設定: 中間グレーのみディザリング、大幅な点数削減")
    elif threshold_choice == "5":
        black_threshold, white_threshold = 140, 140
        print("超軽量設定: ディザリングなし、完全2値化のみ")
    elif threshold_choice == "6":
        black_threshold = int(input("黒固定の閾値 (0-255, 推奨: 60-140): ") or "80")
        white_threshold = int(input("白固定の閾値 (0-255, 推奨: 140-220): ") or "200")
        
        # 閾値の妥当性チェック
        if black_threshold > white_threshold:
            print("警告: 黒閾値が白閾値より大きいです。デフォルト値を使用します。")
            black_threshold, white_threshold = 80, 200
    else:
        black_threshold, white_threshold = 80, 200
    
    # フロイド・スタインバーグ・ディザリングを実行
    print("改良版フロイド・スタインバーグ・ディザリングを実行中...")
    binary_img = floyd_steinberg_dither(img.copy(), black_threshold, white_threshold)
    
    # ディザリング結果を保存
    cv2.imwrite("dither_result.png", binary_img)
    print("ディザリング結果を 'dither_result.png' に保存しました")
    
    # 黒ピクセル数の統計
    total_pixels = binary_img.size
    black_pixels = np.sum(binary_img == 0)
    white_pixels = np.sum(binary_img == 255)
    black_ratio = (black_pixels / total_pixels) * 100
    
    print(f"ディザリング画像サイズ: {binary_img.shape}")
    print(f"黒ピクセル数: {black_pixels} ({black_ratio:.1f}%)")
    print(f"白ピクセル数: {white_pixels} ({100-black_ratio:.1f}%)")
    
    # 最適化されたパスを生成
    print("最適化されたパスを生成中...")
    paths = create_optimized_paths(binary_img, draw_x1, draw_y1, draw_width, draw_height)
    
    if not paths:
        print("描画するパスが見つかりませんでした")
        return
    
    print(f"生成されたパス数: {len(paths)}")
    total_points = sum(len(path) for path in paths)
    print(f"総描画点数: {total_points}")
    
    # クリック削減率の計算（ゼロ除算を回避）
    if total_points > 0:
        reduction_rate = (1 - len(paths) / total_points) * 100
        print(f"クリック削減率: {reduction_rate:.1f}%")
    else:
        print("クリック削減率: 計算不可（描画点なし）")
    
    # プレビュー画像作成
    preview_img = np.full((int(draw_height), int(draw_width), 3), 255, dtype=np.uint8)
    
    for path_idx, path in enumerate(paths):
        # パスごとに異なる色で表示（デバッグ用）
        color = (0, 0, 0)  # 黒
        
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            
            # 描画範囲内の座標に変換
            rel_x1 = x1 - draw_x1
            rel_y1 = y1 - draw_y1
            rel_x2 = x2 - draw_x1
            rel_y2 = y2 - draw_y1
            
            if (0 <= rel_x1 < draw_width and 0 <= rel_y1 < draw_height and
                0 <= rel_x2 < draw_width and 0 <= rel_y2 < draw_height):
                cv2.line(preview_img, (rel_x1, rel_y1), (rel_x2, rel_y2), color, 1)
    
    cv2.imwrite("drawing_preview_optimized.png", preview_img)
    print("最適化されたプレビューを 'drawing_preview_optimized.png' に保存しました")
    
    # 描画前の最終確認
    print(f"\n=== 描画準備完了 ===")
    print(f"画像: {input_file}")
    print(f"描画範囲: {draw_width} x {draw_height} ピクセル")
    total_draw_points = sum(len(path) for path in paths)
    print(f"生成パス数: {len(paths)}")
    print(f"総描画点数: {total_draw_points}")
    
    if total_draw_points > 0:
        reduction_rate = (1 - len(paths) / total_draw_points) * 100
        print(f"クリック削減率: {reduction_rate:.1f}%")
    else:
        print("クリック削減率: 計算不可")
        
    print(f"推定描画時間: {len(paths) * 0.02:.1f}秒")
    
    # 描画速度設定
    print("\n描画速度を選択してください:")
    print("1. 最高速度 (duration=0, sleep=0) - 推奨")
    print("2. 高速 (duration=0.001, sleep=0.001)")
    print("3. 中速 (duration=0.005, sleep=0.005)")
    print("4. 安全速度 (duration=0.01, sleep=0.01)")
    
    speed_choice = input("選択 (1/2/3/4): ")
    
    if speed_choice == "1":
        move_duration = 0
        sleep_time = 0
        print("最高速度モード: 瞬間描画")
    elif speed_choice == "2":
        move_duration = 0.001
        sleep_time = 0.001
        print("高速モード")
    elif speed_choice == "3":
        move_duration = 0.005
        sleep_time = 0.005
        print("中速モード")
    elif speed_choice == "4":
        move_duration = 0.01
        sleep_time = 0.01
        print("安全速度モード")
    else:
        move_duration = 0
        sleep_time = 0
        print("デフォルト: 最高速度モード")
    
    # 実際の描画を実行するか確認
    response = input("\n実際の描画を開始しますか？ (y/n): ")
    if response.lower() != "y":
        print("描画をキャンセルしました")
        print("以下のファイルが保存されています:")
        print("- dither_result.png (ディザリング結果)")
        print("- drawing_preview_optimized.png (描画予定のプレビュー)")
        return
    
    print("3秒後に描画開始します。描画アプリにフォーカスを移してください！")
    print("※ 描画中にEsc、Space、Enterキーのいずれかを押すと中止できます")
    print("※ マウスが動かせない場合でもキーボードで中止可能です")
    time.sleep(3)
    
    # 超高速描画のための設定
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    pyautogui.MINIMUM_DURATION = 0  # 最小移動時間を0に
    pyautogui.MINIMUM_SLEEP = 0     # 最小スリープ時間を0に
    
    # キーボード監視を開始
    keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
    keyboard_thread.start()
    
    # 最適化されたパスで描画
    print(f"最適化描画開始: {len(paths)}パス")
    
    for path_idx, path in enumerate(paths):
        if check_stop():
            break
        
        if path_idx % 50 == 0:  # 進捗表示頻度を下げて高速化
            print(f"描画進行: {path_idx}/{len(paths)}パス")
        
        if len(path) < 2:
            continue
        
        # パスの開始点に移動
        pyautogui.moveTo(path[0][0], path[0][1])
        pyautogui.mouseDown()
        
        # パスをなぞる（設定された速度で）
        for point in path[1:]:
            if check_stop():
                break
            pyautogui.moveTo(point[0], point[1], duration=move_duration)
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        if not stop_drawing:
            pyautogui.mouseUp()
        if sleep_time > 0:
            time.sleep(sleep_time)  # パス間の休憩
    
    if stop_drawing:
        print("描画が中止されました！")
    else:
        print("描画完了！")

if __name__ == "__main__":
    main()
