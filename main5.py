import cv2
import numpy as np
import pyautogui
import time
import threading
import sys
import msvcrt
import keyboard
from multiprocessing import Pool, cpu_count

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

def create_binary_image(img, threshold=127, method="otsu"):
    """
    完全白黒2値化（点描なし）
    
    Args:
        img: 入力画像
        threshold: 閾値 (0-255)
        method: 変換方法 ("simple", "otsu", "adaptive")
    """
    if method == "simple":
        _, binary = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)
        print(f"シンプル2値化 (閾値: {threshold})")
        
    elif method == "otsu":
        threshold_otsu, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        print(f"大津の手法 (自動決定閾値: {threshold_otsu:.1f})")
        
    elif method == "adaptive":
        binary = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        print("適応的2値化")
    
    return binary

def create_contour_paths(binary_img, draw_x1, draw_y1, draw_width, draw_height):
    """輪郭線から描画パスを生成"""
    # 輪郭を抽出
    contours, hierarchy = cv2.findContours(binary_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # 小さすぎる輪郭を除去
    min_area = 50
    contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
    
    print(f"検出された輪郭数: {len(contours)}")
    
    # 輪郭を面積でソート（大きい順）
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    paths = []
    img_height, img_width = binary_img.shape
    
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        print(f"輪郭 {i + 1}: {len(contour)}点, 面積: {area:.1f}")
        
        # 輪郭を滑らかにする
        epsilon = 0.005 * cv2.arcLength(contour, True)
        smoothed_contour = cv2.approxPolyDP(contour, epsilon, True)
        
        if len(smoothed_contour) < 3:
            continue
        
        # 輪郭の点をスケール後の座標に変換
        path_points = []
        for point in smoothed_contour:
            x, y = point[0]
            scaled_x = draw_x1 + int((x / img_width) * draw_width)
            scaled_y = draw_y1 + int((y / img_height) * draw_height)
            path_points.append((scaled_x, scaled_y))
        
        # 最初の点に戻って閉じる
        if len(path_points) > 0:
            path_points.append(path_points[0])
        
        paths.append(path_points)
    
    return paths

def create_fill_paths(binary_img, draw_x1, draw_y1, draw_width, draw_height):
    """黒い領域を塗りつぶすパスを生成（スキャンライン方式）"""
    height, width = binary_img.shape
    
    # 黒ピクセルを検索
    black_y, black_x = np.where(binary_img == 0)
    
    if len(black_x) == 0:
        return []
    
    print(f"黒ピクセル数: {len(black_x)}")
    
    # 描画座標に変換
    draw_x_coords = draw_x1 + ((black_x / width) * draw_width).astype(int)
    draw_y_coords = draw_y1 + ((black_y / height) * draw_height).astype(int)
    
    # Y座標ごとにX座標をグループ化
    y_to_x_dict = {}
    for x, y in zip(draw_x_coords, draw_y_coords):
        if y not in y_to_x_dict:
            y_to_x_dict[y] = []
        y_to_x_dict[y].append(x)
    
    paths = []
    
    for y in sorted(y_to_x_dict.keys()):
        x_coords = sorted(set(y_to_x_dict[y]))  # 重複除去
        
        if not x_coords:
            continue
        
        # 連続する範囲を見つける
        current_path = [(x_coords[0], y)]
        
        for i in range(1, len(x_coords)):
            prev_x = x_coords[i-1]
            curr_x = x_coords[i]
            
            # 連続している場合は同じパスに追加
            if curr_x - prev_x <= 2:
                current_path.append((curr_x, y))
            else:
                # パスを保存して新しいパスを開始
                if len(current_path) >= 2:
                    paths.append(current_path)
                current_path = [(curr_x, y)]
        
        # 最後のパスを追加
        if len(current_path) >= 2:
            paths.append(current_path)
    
    return paths

# 中止フラグとリスナー
stop_drawing = False

def keyboard_listener():
    """キーボード監視スレッド"""
    global stop_drawing
    try:
        while not stop_drawing:
            if keyboard.is_pressed('esc') or keyboard.is_pressed('space') or keyboard.is_pressed('enter'):
                stop_drawing = True
                print("\n描画を中止しています...")
                pyautogui.mouseUp()
                break
            time.sleep(0.05)
    except Exception as e:
        print(f"キーボード監視エラー: {e}")
        try:
            while not stop_drawing:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key in [b'\r', b' ', b'\x1b']:
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
    target_width = min(draw_width, 1000)
    target_height = min(draw_height, 1000)
    
    aspect_ratio = width / height
    target_aspect = target_width / target_height
    
    if aspect_ratio > target_aspect:
        new_width = target_width
        new_height = int(target_width / aspect_ratio)
    else:
        new_height = target_height
        new_width = int(target_height * aspect_ratio)
    
    if new_width != width or new_height != height:
        img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
        print(f"描画範囲に最適化してリサイズ: {img.shape}")
    
    # 2値化方法を選択
    print("\n2値化方法を選択してください:")
    print("1. 大津の手法 (自動閾値) - 推奨")
    print("2. シンプル閾値 (手動)")
    print("3. 適応的閾値 (局所的)")
    
    method_choice = input("選択 (1/2/3): ")
    
    if method_choice == "1":
        binary_img = create_binary_image(img, method="otsu")
    elif method_choice == "2":
        threshold = int(input("閾値を入力 (0-255, 推奨: 127): ") or "127")
        binary_img = create_binary_image(img, threshold, "simple")
    elif method_choice == "3":
        binary_img = create_binary_image(img, method="adaptive")
    else:
        binary_img = create_binary_image(img, method="otsu")
    
    # 2値化結果を保存
    cv2.imwrite("binary_result.png", binary_img)
    print("2値化結果を 'binary_result.png' に保存しました")
    
    # 黒ピクセル数の統計
    total_pixels = binary_img.size
    black_pixels = np.sum(binary_img == 0)
    white_pixels = np.sum(binary_img == 255)
    black_ratio = (black_pixels / total_pixels) * 100
    
    print(f"2値化画像サイズ: {binary_img.shape}")
    print(f"黒ピクセル数: {black_pixels} ({black_ratio:.1f}%)")
    print(f"白ピクセル数: {white_pixels} ({100-black_ratio:.1f}%)")
    
    # 描画方法を選択
    print("\n描画方法を選択してください:")
    print("1. 輪郭線のみ (線画風)")
    print("2. 塗りつぶし (ベタ塗り風)")
    print("3. 輪郭線＋塗りつぶし (完全再現)")
    
    draw_method = input("選択 (1/2/3): ")
    
    all_paths = []
    
    if draw_method in ["1", "3"]:
        # 輪郭線パスを生成
        print("輪郭線パスを生成中...")
        contour_paths = create_contour_paths(binary_img, draw_x1, draw_y1, draw_width, draw_height)
        all_paths.extend(contour_paths)
        print(f"輪郭線パス数: {len(contour_paths)}")
    
    if draw_method in ["2", "3"]:
        # 塗りつぶしパスを生成
        print("塗りつぶしパスを生成中...")
        fill_paths = create_fill_paths(binary_img, draw_x1, draw_y1, draw_width, draw_height)
        all_paths.extend(fill_paths)
        print(f"塗りつぶしパス数: {len(fill_paths)}")
    
    if not all_paths:
        print("描画するパスが見つかりませんでした")
        return
    
    print(f"総パス数: {len(all_paths)}")
    total_points = sum(len(path) for path in all_paths)
    print(f"総描画点数: {total_points}")
    
    if total_points > 0:
        reduction_rate = (1 - len(all_paths) / total_points) * 100
        print(f"クリック削減率: {reduction_rate:.1f}%")
    
    # プレビュー画像作成
    preview_img = np.full((int(draw_height), int(draw_width), 3), 255, dtype=np.uint8)
    
    for path in all_paths:
        if len(path) < 2:
            continue
        
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            
            rel_x1 = x1 - draw_x1
            rel_y1 = y1 - draw_y1
            rel_x2 = x2 - draw_x1
            rel_y2 = y2 - draw_y1
            
            if (0 <= rel_x1 < draw_width and 0 <= rel_y1 < draw_height and
                0 <= rel_x2 < draw_width and 0 <= rel_y2 < draw_height):
                cv2.line(preview_img, (rel_x1, rel_y1), (rel_x2, rel_y2), (0, 0, 0), 1)
    
    cv2.imwrite("drawing_preview_binary.png", preview_img)
    print("プレビューを 'drawing_preview_binary.png' に保存しました")
    
    # 描画前の最終確認
    print(f"\n=== 描画準備完了 ===")
    print(f"画像: {input_file}")
    print(f"描画範囲: {draw_width} x {draw_height} ピクセル")
    print(f"総パス数: {len(all_paths)}")
    print(f"推定描画時間: {len(all_paths) * 0.02:.1f}秒")
    
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
        print("- binary_result.png (2値化結果)")
        print("- drawing_preview_binary.png (描画予定のプレビュー)")
        return
    
    print("3秒後に描画開始します。描画アプリにフォーカスを移してください！")
    print("※ 描画中にEsc、Space、Enterキーのいずれかを押すと中止できます")
    time.sleep(3)
    
    # 超高速描画のための設定
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    pyautogui.MINIMUM_DURATION = 0
    pyautogui.MINIMUM_SLEEP = 0
    
    # キーボード監視を開始
    keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
    keyboard_thread.start()
    
    # 描画実行
    print(f"描画開始: {len(all_paths)}パス")
    
    for path_idx, path in enumerate(all_paths):
        if check_stop():
            break
        
        if path_idx % 50 == 0:
            print(f"描画進行: {path_idx}/{len(all_paths)}パス")
        
        if len(path) < 2:
            continue
        
        # パスの開始点に移動
        pyautogui.moveTo(path[0][0], path[0][1])
        pyautogui.mouseDown()
        
        # パスをなぞる
        for point in path[1:]:
            if check_stop():
                break
            pyautogui.moveTo(point[0], point[1], duration=move_duration)
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        if not stop_drawing:
            pyautogui.mouseUp()
        if sleep_time > 0:
            time.sleep(sleep_time)
    
    if stop_drawing:
        print("描画が中止されました！")
    else:
        print("描画完了！")

if __name__ == "__main__":
    main()
