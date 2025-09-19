import cv2
import numpy as np

def get_canvas_size():
    print("キャンバスサイズを指定してください:")
    
    try:
        width = int(input("キャンバス幅 (推奨: 400): ") or "400")
        height = int(input("キャンバス高さ (推奨: 300): ") or "300")
        return (width, height)
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

def create_ultra_compressed_paths(binary_img, canvas_width, canvas_height):
    """超圧縮形式でパスを生成"""
    height, width = binary_img.shape
    
    # 黒ピクセルを検索
    black_y, black_x = np.where(binary_img == 0)
    
    if len(black_x) == 0:
        return ""
    
    print(f"黒ピクセル数: {len(black_x)}")
    
    # キャンバス座標に変換
    draw_x_coords = ((black_x / width) * canvas_width).astype(np.uint16)
    draw_y_coords = ((black_y / height) * canvas_height).astype(np.uint16)
    
    # Y座標ごとにX座標をグループ化して連続線分を作成
    y_to_x_dict = {}
    for x, y in zip(draw_x_coords, draw_y_coords):
        if y not in y_to_x_dict:
            y_to_x_dict[y] = []
        y_to_x_dict[y].append(x)
    
    # 超圧縮形式: "y:x1-x2,x3-x4;y2:x5-x6"
    compressed_lines = []
    
    for y in sorted(y_to_x_dict.keys()):
        x_coords = sorted(set(y_to_x_dict[y]))
        
        if not x_coords:
            continue
        
        # 連続する範囲を見つけて圧縮
        ranges = []
        start_x = x_coords[0]
        end_x = x_coords[0]
        
        for i in range(1, len(x_coords)):
            if x_coords[i] - end_x <= 2:  # 連続
                end_x = x_coords[i]
            else:
                # 範囲を保存
                if end_x - start_x >= 1:  # 2点以上の線分のみ
                    ranges.append(f"{start_x}-{end_x}")
                start_x = x_coords[i]
                end_x = x_coords[i]
        
        # 最後の範囲
        if end_x - start_x >= 1:
            ranges.append(f"{start_x}-{end_x}")
        
        if ranges:
            compressed_lines.append(f"{y}:{','.join(ranges)}")
    
    # シンプルな圧縮（gzipなし）
    compressed_str = ";".join(compressed_lines)
    
    print(f"圧縮データサイズ: {len(compressed_str)} bytes")
    
    return compressed_str

def generate_ultra_light_javascript(compressed_data, canvas_width, canvas_height, canvas_selector="canvas"):
    """超軽量JavaScriptコードを生成"""
    
    js_code = f"""
// 🚀 Auto Canvas Drawer - 超軽量版
(function() {{
    let canvas;
    if ('{canvas_selector}' === 'canvas') {{
        canvas = document.querySelector('canvas');
    }} else {{
        canvas = document.querySelector('{canvas_selector}');
    }}
    
    if (!canvas) {{
        console.error('❌ キャンバスが見つかりません');
        return;
    }}
    
    console.log('✅ キャンバス発見:', canvas.width + 'x' + canvas.height);
    
    const ctx = canvas.getContext('2d');
    
    // 圧縮データを展開
    function decompressData() {{
        const compressed = `{compressed_data}`;
        
        // データ解析
        const lines = compressed.split(';');
        const paths = [];
        
        // アスペクト比を保持してキャンバス内に収める
        const sourceAspect = {canvas_width} / {canvas_height};
        const canvasAspect = canvas.width / canvas.height;
        
        let scaleX, scaleY, offsetX = 0, offsetY = 0;
        
        if (sourceAspect > canvasAspect) {{
            // 横長の場合：幅に合わせる
            scaleX = canvas.width / {canvas_width};
            scaleY = scaleX;
            offsetY = (canvas.height - {canvas_height} * scaleY) / 2;
        }} else {{
            // 縦長の場合：高さに合わせる
            scaleY = canvas.height / {canvas_height};
            scaleX = scaleY;
            offsetX = (canvas.width - {canvas_width} * scaleX) / 2;
        }}
        
        console.log('🔧 スケール調整:');
        console.log('- 元サイズ:', {canvas_width} + 'x' + {canvas_height});
        console.log('- キャンバス:', canvas.width + 'x' + canvas.height);
        console.log('- スケール:', 'X=' + scaleX.toFixed(3) + ', Y=' + scaleY.toFixed(3));
        console.log('- オフセット:', 'X=' + offsetX.toFixed(1) + ', Y=' + offsetY.toFixed(1));
        
        for (const line of lines) {{
            if (!line || !line.includes(':')) continue;
            
            const colonIndex = line.indexOf(':');
            const yStr = line.substring(0, colonIndex);
            const rangesStr = line.substring(colonIndex + 1);
            
            const y = Math.round(parseInt(yStr) * scaleY + offsetY);
            if (isNaN(y)) continue;
            
            const ranges = rangesStr.split(',');
            
            for (const range of ranges) {{
                if (!range.includes('-')) continue;
                
                const dashIndex = range.indexOf('-');
                const startX = Math.round(parseInt(range.substring(0, dashIndex)) * scaleX + offsetX);
                const endX = Math.round(parseInt(range.substring(dashIndex + 1)) * scaleX + offsetX);
                
                if (!isNaN(startX) && !isNaN(endX) && endX > startX) {{
                    paths.push([[startX, y], [endX, y]]);
                }}
            }}
        }}
        
        return paths;
    }}
    
    function drawInstant() {{
        console.time('⚡ 描画');
        
        const paths = decompressData();
        
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 1;
        ctx.beginPath();
        
        for (const path of paths) {{
            ctx.moveTo(path[0][0], path[0][1]);
            ctx.lineTo(path[1][0], path[1][1]);
        }}
        
        ctx.stroke();
        
        console.timeEnd('⚡ 描画');
        console.log('🎉 完了! パス数:', paths.length);
    }}
    
    function clearCanvas() {{
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }}
    
    // グローバル関数として登録
    window.ultraDraw = drawInstant;
    window.ultraClear = clearCanvas;
    
    console.log('🎨 Ultra Canvas Drawer 準備完了!');
    console.log('💡 コマンド: ultraDraw() / ultraClear()');
    
}})();
"""
    
    return js_code

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
    
    # キャンバスサイズを取得
    canvas_size = get_canvas_size()
    if canvas_size is None:
        return
    
    canvas_width, canvas_height = canvas_size
    
    print(f"キャンバスサイズ: {canvas_width} x {canvas_height}")
    
    # 軽量化のため画像サイズを制限
    height, width = img.shape
    max_size = 300  # さらに小さく制限
    
    if max(width, height) > max_size:
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        
        img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
        print(f"軽量化のためリサイズ: {img.shape}")
    
    # 2値化方法を選択
    print("\n2値化方法を選択してください:")
    print("1. 大津の手法 (自動閾値) - 推奨")
    print("2. 強い閾値 (黒ピクセル削減)")
    
    method_choice = input("選択 (1/2): ")
    
    if method_choice == "2":
        binary_img = create_binary_image(img, 100, "simple")  # 強い閾値
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
    
    if black_pixels > 50000:
        print("⚠️  黒ピクセルが多すぎます。より強い閾値を推奨します。")
        choice = input("続行しますか？ (y/n): ")
        if choice.lower() != "y":
            return
    
    # 超圧縮パスを生成
    print("超圧縮パスを生成中...")
    compressed_data = create_ultra_compressed_paths(binary_img, canvas_width, canvas_height)
    
    if not compressed_data:
        print("描画するパスが見つかりませんでした")
        return
    
    # キャンバスセレクタを指定
    print("\nキャンバス要素の指定:")
    print("1. 自動検出")
    print("2. ID指定")
    
    selector_choice = input("選択 (1/2): ")
    
    if selector_choice == "2":
        canvas_id = input("canvas要素のID: ")
        canvas_selector = f"#{canvas_id}"
    else:
        canvas_selector = "canvas"
    
    # 超軽量JavaScriptコードを生成
    js_code = generate_ultra_light_javascript(compressed_data, canvas_width, canvas_height, canvas_selector)
    
    # JSファイルに保存
    output_file = "ultra_drawer.js"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(js_code)
    
    print(f"\n🚀 超軽量JSファイルを生成: {output_file}")
    print(f"📊 ファイルサイズ: {len(js_code)} bytes ({len(js_code)/1024:.1f}KB)")
    print("\n📋 使用方法:")
    print("1. 対象サイトで開発者ツールを開く")
    print("2. Consoleタブでファイル内容をペースト")
    print("3. ultraDraw() で描画実行！")

if __name__ == "__main__":
    main()
