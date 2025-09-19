import cv2
import pyautogui
import time
import numpy as np
import random
import threading
import sys
import msvcrt


def get_drawing_area():
    print("描画範囲を指定してください:")
    print("1. 左上の角をクリックしてください")

    # 左上の点を取得
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

    # 右下の点を取得
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


# 描画範囲を取得
area = get_drawing_area()
if area is None:
    exit()

draw_x1, draw_y1, draw_x2, draw_y2 = area
draw_width = abs(draw_x2 - draw_x1)
draw_height = abs(draw_y2 - draw_y1)

# 最小サイズを確保
if draw_width < 10:
    draw_width = 500
if draw_height < 10:
    draw_height = 500

print(f"描画範囲: ({draw_x1}, {draw_y1}) から ({draw_x2}, {draw_y2})")
print(f"サイズ: {draw_width} x {draw_height}")

# サイズが0の場合はエラーで終了
if draw_width <= 0 or draw_height <= 0:
    print("エラー: 描画範囲が正しく指定されていません")
    print("左上と右下の点が異なる位置になるように指定してください")
    exit()


def create_hatching_pattern(img, draw_x1, draw_y1, draw_width, draw_height):
    """ハッチング/点描パターンを生成"""
    img_height, img_width = img.shape

    blurred = cv2.GaussianBlur(img, (3, 3), 0)

    scale = 3
    target_w = max(1, int(draw_width // scale))
    target_h = max(1, int(draw_height // scale))

    resized = cv2.resize(blurred, (target_w, target_h), interpolation=cv2.INTER_AREA)
    work = resized.astype(np.float32) / 255.0

    for y in range(target_h - 1):
        row = work[y]
        for x in range(1, target_w - 1):
            old = row[x]
            new = 0.0 if old < 0.5 else 1.0
            row[x] = new
            err = old - new
            work[y, x + 1] = np.clip(work[y, x + 1] + err * (7.0 / 16.0), 0.0, 1.0)
            work[y + 1, x - 1] = np.clip(work[y + 1, x - 1] + err * (3.0 / 16.0), 0.0, 1.0)
            work[y + 1, x] = np.clip(work[y + 1, x] + err * (5.0 / 16.0), 0.0, 1.0)
            work[y + 1, x + 1] = np.clip(work[y + 1, x + 1] + err * (1.0 / 16.0), 0.0, 1.0)

    binary = (work < 0.5).astype(np.uint8)

    def morton_code(ix: int, iy: int, bits: int) -> int:
        code = 0
        for b in range(bits):
            code |= ((ix >> b) & 1) << (2 * b)
            code |= ((iy >> b) & 1) << (2 * b + 1)
        return code

    bits = max(target_w - 1, target_h - 1).bit_length()
    points = []
    for y in range(target_h):
        row = binary[y]
        for x in range(target_w):
            if row[x] != 0:
                px = draw_x1 + int(x * scale + scale * 0.5)
                py = draw_y1 + int(y * scale + scale * 0.5)
                sx = min(max(int((px - draw_x1) / draw_width * (img_width - 1)), 0), img_width - 1)
                sy = min(max(int((py - draw_y1) / draw_height * (img_height - 1)), 0), img_height - 1)
                brightness = float(img[sy, sx])
                code = morton_code(x, y, bits)
                points.append((code, px, py, brightness))

    points.sort(key=lambda t: t[0])
    drawing_points = [(px, py, brightness) for _, px, py, brightness in points]
    return drawing_points


def create_stroke_pattern(img, draw_x1, draw_y1, draw_width, draw_height):
    """ストローク（線画）パターンを生成"""
    img_height, img_width = img.shape

    # エッジ検出
    edges = cv2.Canny(img, 50, 150)

    # Sobelフィルタで方向を計算
    sobel_x = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)

    # 勾配の角度を計算
    angles = np.arctan2(sobel_y, sobel_x)

    strokes = []
    step = 12

    print("ストロークパターンを生成中...")

    for y in range(0, img_height, step):
        for x in range(0, img_width, step):
            # 明度チェック
            brightness = img[y, x] if y < img_height and x < img_width else 255

            # 暗い部分のみストロークを描画
            if brightness < 180:
                # エッジの方向に沿ったストローク
                angle = angles[y, x] if y < img_height and x < img_width else 0

                # ストロークの長さ（暗いほど長く）
                stroke_length = int((255 - brightness) / 255 * 15) + 5

                # ストロークの開始点
                start_x = draw_x1 + int((x / img_width) * draw_width)
                start_y = draw_y1 + int((y / img_height) * draw_height)

                # ストロークの終了点
                end_x = start_x + int(np.cos(angle) * stroke_length)
                end_y = start_y + int(np.sin(angle) * stroke_length)

                strokes.append((start_x, start_y, end_x, end_y))

    return strokes


# 画像を読み込み
img = cv2.imread("input.png", cv2.IMREAD_GRAYSCALE)
if img is None:
    print("input.pngが見つかりません")
    exit()

img_height, img_width = img.shape

# 描画モードを選択
print("\n描画モードを選択してください:")
print("1. 点描/ハッチング（鉛筆デッサン風）")
print("2. ストローク（クロッキー風）")
print("3. 従来の輪郭線")

mode = input("モードを選択 (1/2/3): ")

if mode == "1":
    # 点描/ハッチングモード
    drawing_points = create_hatching_pattern(
        img, draw_x1, draw_y1, draw_width, draw_height
    )

    # プレビュー画像作成
    preview_img = np.full((int(draw_height), int(draw_width), 3), 255, dtype=np.uint8)

    for x, y, brightness in drawing_points:
        # 描画範囲内の点のみ描画
        rel_x = x - draw_x1
        rel_y = y - draw_y1
        if 0 <= rel_x < draw_width and 0 <= rel_y < draw_height:
            # 明度に応じて点の濃さを調整
            intensity = int((255 - brightness) / 255 * 200)
            color = max(55, 255 - intensity)
            cv2.circle(preview_img, (rel_x, rel_y), 1, (color, color, color), -1)

    print(f"生成された点数: {len(drawing_points)}")

elif mode == "2":
    # ストロークモード
    strokes = create_stroke_pattern(img, draw_x1, draw_y1, draw_width, draw_height)

    # プレビュー画像作成
    preview_img = np.full((int(draw_height), int(draw_width), 3), 255, dtype=np.uint8)

    for start_x, start_y, end_x, end_y in strokes:
        rel_start_x = start_x - draw_x1
        rel_start_y = start_y - draw_y1
        rel_end_x = end_x - draw_x1
        rel_end_y = end_y - draw_y1

        if (
            0 <= rel_start_x < draw_width
            and 0 <= rel_start_y < draw_height
            and 0 <= rel_end_x < draw_width
            and 0 <= rel_end_y < draw_height
        ):
            cv2.line(
                preview_img,
                (rel_start_x, rel_start_y),
                (rel_end_x, rel_end_y),
                (0, 0, 0),
                1,
            )

    print(f"生成されたストローク数: {len(strokes)}")

else:
    # 従来の輪郭線モード
    # ガウシアンブラーでノイズ除去
    blurred = cv2.GaussianBlur(img, (5, 5), 0)

    # 適応的2値化でより良い結果を得る
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # モルフォロジー処理でノイズ除去と線の補完
    kernel = np.ones((3, 3), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    # 輪郭を抽出（階層構造も取得）
    contours, hierarchy = cv2.findContours(
        thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )

    # 小さすぎる輪郭を除去
    min_area = 50
    contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]

    print(f"検出された輪郭数: {len(contours)}")

    # 描画範囲のサイズで空の画像を作成（白背景）
    preview_img = np.full((int(draw_height), int(draw_width), 3), 255, dtype=np.uint8)

    # 輪郭を面積でソート（大きい順）
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    # 各輪郭を描画
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        print(f"輪郭 {i + 1}: {len(contour)}点, 面積: {area:.1f}")

        # 輪郭を滑らかにする
        epsilon = 0.005 * cv2.arcLength(contour, True)
        smoothed_contour = cv2.approxPolyDP(contour, epsilon, True)

        # 輪郭の点をスケール後の座標に変換
        scaled_points = []
        for point in smoothed_contour:
            x, y = point[0]
            scaled_x = (x / img_width) * draw_width
            scaled_y = (y / img_height) * draw_height
            scaled_points.append([int(scaled_x), int(scaled_y)])

        # 線の太さを輪郭の大きさに応じて調整
        line_thickness = max(1, int(3 * (area / (img_width * img_height)) * 100))
        line_thickness = min(line_thickness, 5)

        # 線を描画（黒色、調整された太さ）
        if len(scaled_points) > 1:
            scaled_contour = np.array(scaled_points, dtype=np.int32).reshape((-1, 1, 2))
            preview_img = np.ascontiguousarray(preview_img)
            cv2.polylines(
                preview_img, [scaled_contour], True, (0, 0, 0), line_thickness
            )

# 画像を保存
output_filename = "drawing_preview.png"
cv2.imwrite(output_filename, preview_img)
print(f"\n描画予定の画像を '{output_filename}' として保存しました")
print(f"画像サイズ: {draw_width} x {draw_height}")

# 実際の描画を実行するか確認
response = input("\n実際の描画を開始しますか？ (y/n): ")
if response.lower() != "y":
    print("描画をキャンセルしました")
    exit()

print("3秒後に描画開始します。描画アプリにフォーカスを移してください！")
print("※ 描画中にEnterキーを押すと中止できます")
time.sleep(3)

# 高速描画のための設定
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

# 中止フラグ
stop_drawing = False
input_thread = None


def input_listener():
    """入力監視スレッド（Windows用）"""
    global stop_drawing
    try:
        while not stop_drawing:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\r':  # Enterキーで中止
                    stop_drawing = True
                    print("\n描画を中止しています...")
                    pyautogui.mouseUp()  # マウスを離す
                    break
            time.sleep(0.1)
    except:
        pass


def check_stop():
    """中止フラグをチェック"""
    global stop_drawing
    if stop_drawing:
        pyautogui.mouseUp()  # マウスを離す
        return True
    return False


def start_input_monitoring():
    """入力監視を開始"""
    global input_thread
    input_thread = threading.Thread(target=input_listener, daemon=True)
    input_thread.start()


# 入力監視を開始
start_input_monitoring()


if mode == "1":
    # 連続描画モード（クリックし続ける）
    print(f"連続描画開始: {len(drawing_points)}点")

    if drawing_points:
        pyautogui.mouseDown()

        prev_x = None
        prev_y = None
        total = len(drawing_points)
        for i, (x, y, brightness) in enumerate(drawing_points):
            if check_stop():
                break

            if i % 100 == 0:
                print(f"描画進行: {i}/{total}")

            if prev_x is not None and abs(x - prev_x) <= 0 and abs(y - prev_y) <= 0:
                continue

            pyautogui.moveTo(x, y, duration=0.0)

            if brightness < 100:
                time.sleep(0.0025)
            else:
                time.sleep(0.0008)

            prev_x = x
            prev_y = y

        if not stop_drawing:
            pyautogui.mouseUp()

elif mode == "2":
    # ストロークモード（連続描画）
    print(f"ストローク描画開始: {len(strokes)}本")

    connect_threshold = 40.0
    visited = [False] * len(strokes)
    ordered_groups = []

    idx = 0
    while idx < len(strokes):
        try:
            start_i = next(i for i, v in enumerate(visited) if not v)
        except StopIteration:
            break

        visited[start_i] = True
        sx, sy, ex, ey = strokes[start_i]
        group = [(sx, sy, ex, ey)]
        current_x, current_y = ex, ey

        while True:
            best_j = -1
            best_flip = False
            best_dist = 1e12

            for j, v in enumerate(visited):
                if v:
                    continue
                csx, csy, cex, cey = strokes[j]
                d1 = ((current_x - csx) ** 2 + (current_y - csy) ** 2) ** 0.5
                d2 = ((current_x - cex) ** 2 + (current_y - cey) ** 2) ** 0.5
                if d1 < best_dist:
                    best_dist = d1
                    best_j = j
                    best_flip = False
                if d2 < best_dist:
                    best_dist = d2
                    best_j = j
                    best_flip = True

            if best_j == -1 or best_dist > connect_threshold:
                break

            visited[best_j] = True
            nsx, nsy, nex, ney = strokes[best_j]
            if best_flip:
                nsx, nsy, nex, ney = nex, ney, nsx, nsy
            group.append((nsx, nsy, nex, ney))
            current_x, current_y = nex, ney

        ordered_groups.append(group)
        idx += 1

    for group_idx, group in enumerate(ordered_groups):
        if check_stop():
            break
        if not group:
            continue
        first_stroke = group[0]
        pyautogui.moveTo(first_stroke[0], first_stroke[1])
        pyautogui.mouseDown()

        for stroke in group:
            if check_stop():
                break
            start_x, start_y, end_x, end_y = stroke
            pyautogui.moveTo(end_x, end_y, duration=0.004)
            time.sleep(0.0008)

        if not stop_drawing:
            pyautogui.mouseUp()
        time.sleep(0.03)

else:
    # 従来の輪郭線描画
    for i, contour in enumerate(contours):
        # スペースキーチェック
        if check_stop():
            break

        area = cv2.contourArea(contour)
        print(f"描画中: 輪郭 {i + 1}/{len(contours)}")

        # 描画用の高品質な滑らか化
        perimeter = cv2.arcLength(contour, True)
        if area > 5000:
            epsilon = 0.003 * perimeter  # 大きな輪郭は詳細保持
        elif area > 1000:
            epsilon = 0.007 * perimeter  # 中程度
        else:
            epsilon = 0.015 * perimeter  # 小さな輪郭は滑らか

        smoothed_contour = cv2.approxPolyDP(contour, epsilon, True)

        if len(smoothed_contour) < 2:
            continue

        # 最初の点へ移動
        x, y = smoothed_contour[0][0]
        scaled_x = draw_x1 + (x / img_width) * draw_width
        scaled_y = draw_y1 + (y / img_height) * draw_height
        pyautogui.moveTo(scaled_x, scaled_y)
        pyautogui.mouseDown()

        # 輪郭の点を順になぞる（高速）
        for point in smoothed_contour[1:]:
            # スペースキーチェック
            if check_stop():
                break

            x, y = point[0]
            scaled_x = draw_x1 + (x / img_width) * draw_width
            scaled_y = draw_y1 + (y / img_height) * draw_height
            pyautogui.moveTo(scaled_x, scaled_y, duration=0.001)

        # 最初の点に戻って閉じる
        if not stop_drawing:
            x, y = smoothed_contour[0][0]
            scaled_x = draw_x1 + (x / img_width) * draw_width
            scaled_y = draw_y1 + (y / img_height) * draw_height
            pyautogui.moveTo(scaled_x, scaled_y, duration=0.001)

        if not stop_drawing:
            pyautogui.mouseUp()
        time.sleep(0.1)  # 短い休憩

if stop_drawing:
    print("描画が中止されました！")
else:
    print("描画完了！")
