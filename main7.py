import cv2
import numpy as np
import json

def get_canvas_size():
    print("キャンバスサイズを指定してください:")
    
    try:
        width = int(input("キャンバス幅 (推奨: 800): ") or "800")
        height = int(input("キャンバス高さ (推奨: 600): ") or "600")
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

def create_fill_paths(binary_img, canvas_width, canvas_height):
    """黒い領域を塗りつぶすパスを生成"""
    height, width = binary_img.shape
    
    # 黒ピクセルを検索
    black_y, black_x = np.where(binary_img == 0)
    
    if len(black_x) == 0:
        return []
    
    print(f"黒ピクセル数: {len(black_x)}")
    
    # キャンバス座標に変換（0,0から開始）
    draw_x_coords = ((black_x / width) * canvas_width).astype(int)
    draw_y_coords = ((black_y / height) * canvas_height).astype(int)
    
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
        current_path = [{"x": int(x_coords[0]), "y": int(y)}]
        
        for i in range(1, len(x_coords)):
            prev_x = x_coords[i-1]
            curr_x = x_coords[i]
            
            # 連続している場合は同じパスに追加
            if curr_x - prev_x <= 2:
                current_path.append({"x": int(curr_x), "y": int(y)})
            else:
                # パスを保存して新しいパスを開始
                if len(current_path) >= 2:
                    paths.append(current_path)
                current_path = [{"x": int(curr_x), "y": int(y)}]
        
        # 最後のパスを追加
        if len(current_path) >= 2:
            paths.append(current_path)
    
    return paths

def generate_javascript_code(paths, canvas_width, canvas_height, canvas_selector="canvas"):
    """ブラウザコンソールで実行するJavaScriptコードを生成"""
    
    js_code = f"""
// 🚀 Auto Canvas Drawer - ブラウザ注入版
// 使用方法: このコードをブラウザの開発者ツールのコンソールにペーストして実行

(function() {{
    // キャンバス要素を取得
    let canvas;
    if ('{canvas_selector}' === 'canvas') {{
        canvas = document.querySelector('canvas');
    }} else {{
        canvas = document.querySelector('{canvas_selector}');
    }}
    
    if (!canvas) {{
        console.error('❌ キャンバスが見つかりません！');
        console.log('💡 利用可能なキャンバス:', document.querySelectorAll('canvas'));
        return;
    }}
    
    console.log('✅ キャンバスを発見:', canvas);
    console.log('📏 キャンバスサイズ:', canvas.width, 'x', canvas.height);
    
    const ctx = canvas.getContext('2d');
    
    // 描画データ（圧縮形式）
    const compressedData = {json.dumps([[p["x"], p["y"]] for path in paths for p in path], separators=(",", ":"))};
    const pathLengths = {json.dumps([len(path) for path in paths], separators=(",", ":"))};
    
    // データを復元
    let dataIndex = 0;
    const originalPaths = [];
    for (const length of pathLengths) {{
        const path = [];
        for (let i = 0; i < length; i++) {{
            const [x, y] = compressedData[dataIndex++];
            path.push({{x, y}});
        }}
        originalPaths.push(path);
    }}
    
    // キャンバスサイズに合わせてスケール調整
    const scaleX = canvas.width / {canvas_width};
    const scaleY = canvas.height / {canvas_height};
    
    console.log('🔧 スケール調整:', 'X=' + scaleX.toFixed(3), 'Y=' + scaleY.toFixed(3));
    
    // パスをスケール
    const paths = originalPaths.map(path => 
        path.map(point => ({{
            x: Math.round(point.x * scaleX),
            y: Math.round(point.y * scaleY)
        }}))
    );
    
    console.log('📊 描画データ読み込み完了:');
    console.log('- 総パス数:', paths.length.toLocaleString());
    console.log('- 総描画点数:', paths.reduce((sum, path) => sum + path.length, 0).toLocaleString());
    
    // 描画関数
    function drawInstant() {{
        console.time('⚡ 瞬間描画');
        
        // 現在の描画設定を保存
        const originalStrokeStyle = ctx.strokeStyle;
        const originalLineWidth = ctx.lineWidth;
        const originalLineCap = ctx.lineCap;
        const originalLineJoin = ctx.lineJoin;
        
        // 描画設定
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
        
        // 描画設定を復元
        ctx.strokeStyle = originalStrokeStyle;
        ctx.lineWidth = originalLineWidth;
        ctx.lineCap = originalLineCap;
        ctx.lineJoin = originalLineJoin;
        
        console.timeEnd('⚡ 瞬間描画');
        console.log('🎉 描画完了！');
    }}
    
    // アニメーション描画関数
    async function drawAnimated(speed = 10) {{
        console.time('🎬 アニメーション描画');
        
        // 現在の描画設定を保存
        const originalStrokeStyle = ctx.strokeStyle;
        const originalLineWidth = ctx.lineWidth;
        const originalLineCap = ctx.lineCap;
        const originalLineJoin = ctx.lineJoin;
        
        // 描画設定
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 1;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        
        for (let i = 0; i < paths.length; i++) {{
            const path = paths[i];
            
            if (path.length < 2) continue;
            
            ctx.beginPath();
            ctx.moveTo(path[0].x, path[0].y);
            
            for (let j = 1; j < path.length; j++) {{
                ctx.lineTo(path[j].x, path[j].y);
            }}
            
            ctx.stroke();
            
            // 進捗表示
            if (i % 100 === 0) {{
                const progress = ((i + 1) / paths.length * 100).toFixed(1);
                console.log(`📈 進捗: ${{progress}}% (${{i + 1}}/${{paths.length}})`);
            }}
            
            // 速度調整
            if (i % speed === 0) {{
                await new Promise(resolve => setTimeout(resolve, 1));
            }}
        }}
        
        // 描画設定を復元
        ctx.strokeStyle = originalStrokeStyle;
        ctx.lineWidth = originalLineWidth;
        ctx.lineCap = originalLineCap;
        ctx.lineJoin = originalLineJoin;
        
        console.timeEnd('🎬 アニメーション描画');
        console.log('🎉 アニメーション描画完了！');
    }}
    
    // クリア関数
    function clearCanvas() {{
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        console.log('🧹 キャンバスをクリアしました');
    }}
    
    // グローバル関数として登録
    window.autoDrawInstant = drawInstant;
    window.autoDrawAnimated = drawAnimated;
    window.autoClearCanvas = clearCanvas;
    
    console.log('🎨 Auto Canvas Drawer が準備完了！');
    console.log('');
    console.log('📋 使用可能なコマンド:');
    console.log('  autoDrawInstant()     - 瞬間描画');
    console.log('  autoDrawAnimated()    - アニメーション描画 (デフォルト速度)');
    console.log('  autoDrawAnimated(1)   - 高速アニメーション');
    console.log('  autoDrawAnimated(50)  - 低速アニメーション');
    console.log('  autoClearCanvas()     - キャンバスクリア');
    console.log('');
    console.log('💡 すぐに描画を開始するには: autoDrawInstant()');
    
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
    
    # キャンバスサイズに合わせて画像を最適化
    height, width = img.shape
    
    # アスペクト比を保持してキャンバスに収まるようにリサイズ
    aspect_ratio = width / height
    canvas_aspect = canvas_width / canvas_height
    
    if aspect_ratio > canvas_aspect:
        # 横長の画像：幅をキャンバス幅に合わせる
        new_width = min(canvas_width, 1000)  # 最大1000ピクセル
        new_height = int(new_width / aspect_ratio)
    else:
        # 縦長の画像：高さをキャンバス高さに合わせる
        new_height = min(canvas_height, 1000)  # 最大1000ピクセル
        new_width = int(new_height * aspect_ratio)
    
    if new_width != width or new_height != height:
        img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
        print(f"キャンバスサイズに最適化してリサイズ: {img.shape}")
    
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
    paths = create_fill_paths(binary_img, canvas_width, canvas_height)
    
    if not paths:
        print("描画するパスが見つかりませんでした")
        return
    
    print(f"生成されたパス数: {len(paths)}")
    total_points = sum(len(path) for path in paths)
    print(f"総描画点数: {total_points}")
    
    # データサイズをチェック
    estimated_size = total_points * 20  # 1点あたり約20バイト
    print(f"推定データサイズ: {estimated_size / 1024 / 1024:.1f}MB")
    
    if estimated_size > 5 * 1024 * 1024:  # 5MB以上
        print("⚠️  データが大きすぎます。以下の対策を推奨:")
        print("1. 画像サイズを小さくする")
        print("2. 閾値を調整して黒ピクセルを減らす")
        print("3. データを分割する")
        
        choice = input("続行しますか？ (y/n): ")
        if choice.lower() != "y":
            return
    
    # キャンバスセレクタを指定
    print("\nキャンバス要素の指定方法:")
    print("1. 自動検出 (最初のcanvas要素)")
    print("2. ID指定 (例: #myCanvas)")
    print("3. クラス指定 (例: .drawing-canvas)")
    print("4. その他のCSSセレクタ")
    
    selector_choice = input("選択 (1/2/3/4): ")
    
    if selector_choice == "1":
        canvas_selector = "canvas"
    elif selector_choice == "2":
        canvas_id = input("canvas要素のID (# は不要): ")
        canvas_selector = f"#{canvas_id}"
    elif selector_choice == "3":
        canvas_class = input("canvas要素のクラス名 (. は不要): ")
        canvas_selector = f".{canvas_class}"
    elif selector_choice == "4":
        canvas_selector = input("CSSセレクタを入力: ")
    else:
        canvas_selector = "canvas"
    
    # JavaScriptコードを生成
    js_code = generate_javascript_code(paths, canvas_width, canvas_height, canvas_selector)
    
    # JSファイルに保存
    output_file = "auto_drawer_inject.js"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(js_code)
    
    print(f"\n🚀 JavaScriptコードを生成しました: {output_file}")
    print("\n📋 使用方法:")
    print("1. 対象サイトをブラウザで開く")
    print("2. F12キーで開発者ツールを開く")
    print("3. Consoleタブを選択")
    print("4. 生成されたJSファイルの内容をコピー&ペースト")
    print("5. Enterキーで実行")
    print("6. autoDrawInstant() で瞬間描画！")
    
    print(f"\n💡 キャンバスセレクタ: {canvas_selector}")
    print("💡 もしキャンバスが見つからない場合は、セレクタを変更してください")

if __name__ == "__main__":
    main()
