import cv2
import numpy as np
import json

def get_drawing_area():
    print("描画範囲を指定してください:")
    
    try:
        x1 = int(input("左上X座標: "))
        y1 = int(input("左上Y座標: "))
        x2 = int(input("右下X座標: "))
        y2 = int(input("右下Y座標: "))
        return (x1, y1, x2, y2)
    except ValueError:
        print("数値を入力してください")
        return None

def create_binary_image(img, threshold=127, method="otsu"):
    """完全白黒2値化"""
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

def create_fill_paths(binary_img, draw_x1, draw_y1, draw_width, draw_height):
    """黒い領域を塗りつぶすパスを生成"""
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
        current_path = [{"x": x_coords[0], "y": y}]
        
        for i in range(1, len(x_coords)):
            prev_x = x_coords[i-1]
            curr_x = x_coords[i]
            
            # 連続している場合は同じパスに追加
            if curr_x - prev_x <= 2:
                current_path.append({"x": curr_x, "y": y})
            else:
                # パスを保存して新しいパスを開始
                if len(current_path) >= 2:
                    paths.append(current_path)
                current_path = [{"x": curr_x, "y": y}]
        
        # 最後のパスを追加
        if len(current_path) >= 2:
            paths.append(current_path)
    
    return paths

def generate_html_with_paths(paths, canvas_width, canvas_height):
    """描画パスを含むHTMLを生成"""
    
    html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Auto Canvas Drawer - 超高速描画</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f0f0f0;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        #canvas {{
            border: 2px solid #333;
            background: white;
        }}
        .controls {{
            margin: 20px 0;
            text-align: center;
        }}
        button {{
            padding: 10px 20px;
            margin: 5px;
            border: none;
            border-radius: 5px;
            background: #007bff;
            color: white;
            cursor: pointer;
            font-size: 16px;
        }}
        button:hover {{
            background: #0056b3;
        }}
        button:disabled {{
            background: #6c757d;
            cursor: not-allowed;
        }}
        .stats {{
            margin: 10px 0;
            padding: 10px;
            background: #e9ecef;
            border-radius: 5px;
            font-family: monospace;
        }}
        .progress {{
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
            display: none;
        }}
        .progress-bar {{
            height: 100%;
            background: #28a745;
            width: 0%;
            transition: width 0.1s ease;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Auto Canvas Drawer - 超高速描画</h1>
        <p>Pythonで前処理済み。瞬間描画可能！</p>
        
        <canvas id="canvas" width="{canvas_width}" height="{canvas_height}"></canvas>
        
        <div class="controls">
            <button id="drawBtn">瞬間描画</button>
            <button id="animateBtn">アニメーション描画</button>
            <button id="clearBtn">クリア</button>
            <button id="downloadBtn">画像保存</button>
        </div>
        
        <div class="progress">
            <div class="progress-bar" id="progressBar"></div>
        </div>
        
        <div class="stats">
            <strong>描画データ:</strong><br>
            総パス数: {len(paths):,}<br>
            総描画点数: {sum(len(path) for path in paths):,}<br>
            キャンバスサイズ: {canvas_width} x {canvas_height}
        </div>
    </div>

    <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        
        // Pythonで生成された描画パス
        const paths = {json.dumps(paths, indent=2)};
        
        let isDrawing = false;
        
        function clearCanvas() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }}
        
        function drawInstant() {{
            if (isDrawing) return;
            
            console.time('瞬間描画');
            
            ctx.strokeStyle = '#000000';
            ctx.lineWidth = 1;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            
            // 全パスを一気に描画
            for (const path of paths) {{
                if (path.length < 2) continue;
                
                ctx.beginPath();
                ctx.moveTo(path[0].x, path[0].y);
                
                for (let i = 1; i < path.length; i++) {{
                    ctx.lineTo(path[i].x, path[i].y);
                }}
                
                ctx.stroke();
            }}
            
            console.timeEnd('瞬間描画');
            console.log('描画完了！');
        }}
        
        async function drawAnimated() {{
            if (isDrawing) return;
            
            isDrawing = true;
            document.getElementById('drawBtn').disabled = true;
            document.getElementById('animateBtn').disabled = true;
            
            const progress = document.querySelector('.progress');
            const progressBar = document.getElementById('progressBar');
            
            progress.style.display = 'block';
            
            ctx.strokeStyle = '#000000';
            ctx.lineWidth = 1;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            
            console.time('アニメーション描画');
            
            for (let i = 0; i < paths.length; i++) {{
                const path = paths[i];
                
                if (path.length < 2) continue;
                
                ctx.beginPath();
                ctx.moveTo(path[0].x, path[0].y);
                
                for (let j = 1; j < path.length; j++) {{
                    ctx.lineTo(path[j].x, path[j].y);
                }}
                
                ctx.stroke();
                
                // 進捗更新
                const progress_percent = ((i + 1) / paths.length) * 100;
                progressBar.style.width = progress_percent + '%';
                
                // 10パスごとに少し待機
                if (i % 10 === 0) {{
                    await new Promise(resolve => setTimeout(resolve, 1));
                }}
            }}
            
            console.timeEnd('アニメーション描画');
            
            progress.style.display = 'none';
            isDrawing = false;
            document.getElementById('drawBtn').disabled = false;
            document.getElementById('animateBtn').disabled = false;
            
            console.log('アニメーション描画完了！');
        }}
        
        function downloadImage() {{
            const link = document.createElement('a');
            link.download = 'auto_drawing.png';
            link.href = canvas.toDataURL();
            link.click();
        }}
        
        // イベントリスナー
        document.getElementById('drawBtn').addEventListener('click', drawInstant);
        document.getElementById('animateBtn').addEventListener('click', drawAnimated);
        document.getElementById('clearBtn').addEventListener('click', clearCanvas);
        document.getElementById('downloadBtn').addEventListener('click', downloadImage);
        
        console.log(`描画データ読み込み完了: ${{paths.length}}パス`);
    </script>
</body>
</html>"""
    
    return html_template

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
        print(f"エラー: {{input_file}}が見つかりません")
        return
    
    print(f"元画像サイズ: {{img.shape}}")
    
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
    black_ratio = (black_pixels / total_pixels) * 100
    
    print(f"2値化画像サイズ: {binary_img.shape}")
    print(f"黒ピクセル数: {black_pixels} ({black_ratio:.1f}%)")
    
    # 塗りつぶしパスを生成
    print("描画パスを生成中...")
    paths = create_fill_paths(binary_img, draw_x1, draw_y1, draw_width, draw_height)
    
    if not paths:
        print("描画するパスが見つかりませんでした")
        return
    
    print(f"生成されたパス数: {len(paths)}")
    total_points = sum(len(path) for path in paths)
    print(f"総描画点数: {total_points}")
    
    # HTMLファイルを生成
    html_content = generate_html_with_paths(paths, draw_width, draw_height)
    
    output_file = "auto_drawer.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n🚀 HTMLファイルを生成しました: {output_file}")
    print("ブラウザで開いて「瞬間描画」ボタンを押してください！")
    print("描画データは既にHTMLに埋め込まれています。")

if __name__ == "__main__":
    main()
