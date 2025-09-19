import cv2
import numpy as np

def floyd_steinberg_dither(img):
    """フロイド・スタインバーグ・ディザリング"""
    img = img.astype(np.float32) / 255.0
    height, width = img.shape
    
    for y in range(height - 1):
        for x in range(1, width - 1):
            old_pixel = img[y, x]
            new_pixel = 1.0 if old_pixel > 0.5 else 0.0
            img[y, x] = new_pixel
            
            error = old_pixel - new_pixel
            
            # 誤差を周囲のピクセルに拡散
            img[y, x + 1] += error * 7/16
            img[y + 1, x - 1] += error * 3/16
            img[y + 1, x] += error * 5/16
            img[y + 1, x + 1] += error * 1/16
    
    return (img * 255).astype(np.uint8)

def ordered_dither(img, matrix_size=4):
    """組織的ディザリング（ベイヤー・ディザリング）"""
    # ベイヤー行列
    if matrix_size == 2:
        bayer_matrix = np.array([[0, 2], [3, 1]]) / 4.0
    elif matrix_size == 4:
        bayer_matrix = np.array([
            [0, 8, 2, 10],
            [12, 4, 14, 6],
            [3, 11, 1, 9],
            [15, 7, 13, 5]
        ]) / 16.0
    else:
        bayer_matrix = np.array([[0, 2], [3, 1]]) / 4.0
    
    height, width = img.shape
    result = np.zeros_like(img)
    
    for y in range(height):
        for x in range(width):
            threshold = bayer_matrix[y % matrix_size, x % matrix_size]
            result[y, x] = 255 if img[y, x] / 255.0 > threshold else 0
    
    return result

def halftone_dither(img, dot_size=4):
    """ハーフトーン・ディザリング（新聞印刷風）"""
    height, width = img.shape
    result = np.zeros_like(img)
    
    for y in range(0, height, dot_size):
        for x in range(0, width, dot_size):
            # ブロック内の平均輝度を計算
            block = img[y:y+dot_size, x:x+dot_size]
            avg_brightness = np.mean(block) / 255.0
            
            # 輝度に応じた円のサイズを決定
            radius = int((1 - avg_brightness) * dot_size / 2)
            
            # 円を描画
            center_y = y + dot_size // 2
            center_x = x + dot_size // 2
            
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    py = center_y + dy
                    px = center_x + dx
                    
                    if (0 <= py < height and 0 <= px < width and 
                        dx*dx + dy*dy <= radius*radius):
                        result[py, px] = 0  # 黒
                    elif y <= py < y + dot_size and x <= px < x + dot_size:
                        if 0 <= py < height and 0 <= px < width:
                            result[py, px] = 255  # 白
    
    return result

def stippling_dither(img, density_factor=0.3):
    """点描風ディザリング"""
    height, width = img.shape
    result = np.full_like(img, 255)  # 白背景
    
    # 画像の暗さに応じて点を配置
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            brightness = img[y, x] / 255.0
            # 暗いほど点を配置する確率が高い
            if np.random.random() < (1 - brightness) * density_factor:
                # 小さな黒い点を配置
                result[y:y+2, x:x+2] = 0
    
    return result

def main():
    input_file = "64561311_p0.png"
    
    # 画像を読み込み
    img = cv2.imread(input_file, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"エラー: {input_file}が見つかりません")
        return
    
    print(f"元画像サイズ: {img.shape}")
    print("\nディザリング方法を選択してください:")
    print("1. フロイド・スタインバーグ・ディザリング（高品質）")
    print("2. 組織的ディザリング（パターン風）")
    print("3. ハーフトーン・ディザリング（新聞印刷風）")
    print("4. 点描風ディザリング")
    print("5. 全ての方法で変換")
    
    choice = input("選択 (1-5): ")
    
    if choice == "1":
        result = floyd_steinberg_dither(img.copy())
        cv2.imwrite("dither_floyd.png", result)
        print("フロイド・スタインバーグ・ディザリングで変換完了")
        
    elif choice == "2":
        result = ordered_dither(img)
        cv2.imwrite("dither_ordered.png", result)
        print("組織的ディザリングで変換完了")
        
    elif choice == "3":
        result = halftone_dither(img)
        cv2.imwrite("dither_halftone.png", result)
        print("ハーフトーン・ディザリングで変換完了")
        
    elif choice == "4":
        result = stippling_dither(img)
        cv2.imwrite("dither_stippling.png", result)
        print("点描風ディザリングで変換完了")
        
    elif choice == "5":
        print("全ての方法で変換中...")
        
        result1 = floyd_steinberg_dither(img.copy())
        cv2.imwrite("dither_floyd.png", result1)
        
        result2 = ordered_dither(img)
        cv2.imwrite("dither_ordered.png", result2)
        
        result3 = halftone_dither(img)
        cv2.imwrite("dither_halftone.png", result3)
        
        result4 = stippling_dither(img)
        cv2.imwrite("dither_stippling.png", result4)
        
        print("全ての変換が完了しました")
        print("- dither_floyd.png: フロイド・スタインバーグ")
        print("- dither_ordered.png: 組織的ディザリング")
        print("- dither_halftone.png: ハーフトーン")
        print("- dither_stippling.png: 点描風")
        
    else:
        print("無効な選択です")

if __name__ == "__main__":
    main()
