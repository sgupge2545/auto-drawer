import cv2
import numpy as np

def convert_to_binary(input_path, output_path, threshold=127, method="simple"):
    """
    画像を白と黒のみに変換する
    
    Args:
        input_path: 入力画像のパス
        output_path: 出力画像のパス
        threshold: 閾値 (0-255)
        method: 変換方法 ("simple", "otsu", "adaptive")
    """
    # 画像を読み込み（グレースケール）
    img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"エラー: {input_path}が見つかりません")
        return None
    
    print(f"元画像サイズ: {img.shape}")
    
    if method == "simple":
        # シンプルな閾値処理
        _, binary = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)
        print(f"シンプル閾値処理 (閾値: {threshold})")
        
    elif method == "otsu":
        # 大津の手法（自動閾値決定）
        threshold_otsu, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        print(f"大津の手法 (自動決定閾値: {threshold_otsu:.1f})")
        
    elif method == "adaptive":
        # 適応的閾値処理
        binary = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        print("適応的閾値処理")
    
    else:
        print("エラー: 不正な変換方法です")
        return None
    
    # 結果を保存
    cv2.imwrite(output_path, binary)
    print(f"2値化画像を {output_path} に保存しました")
    
    # 統計情報
    white_pixels = np.sum(binary == 255)
    black_pixels = np.sum(binary == 0)
    total_pixels = binary.size
    
    print(f"白ピクセル: {white_pixels} ({white_pixels/total_pixels*100:.1f}%)")
    print(f"黒ピクセル: {black_pixels} ({black_pixels/total_pixels*100:.1f}%)")
    
    return binary

def main():
    input_file = "123886908_p0_master1200.jpg"
    
    print("画像を白と黒のみに変換します")
    print("\n変換方法を選択してください:")
    print("1. シンプル閾値 (手動で閾値を指定)")
    print("2. 大津の手法 (自動で最適な閾値を決定)")
    print("3. 適応的閾値 (局所的に閾値を調整)")
    
    choice = input("選択 (1/2/3): ")
    
    if choice == "1":
        threshold = int(input("閾値を入力 (0-255, 推奨: 127): ") or "127")
        binary = convert_to_binary(input_file, "binary_simple.png", threshold, "simple")
        
    elif choice == "2":
        binary = convert_to_binary(input_file, "binary_otsu.png", method="otsu")
        
    elif choice == "3":
        binary = convert_to_binary(input_file, "binary_adaptive.png", method="adaptive")
        
    else:
        print("無効な選択です")
        return
    
    if binary is not None:
        print("\n変換完了！")
        
        # 複数の方法で比較したい場合
        compare = input("他の方法でも変換しますか？ (y/n): ")
        if compare.lower() == "y":
            print("\n比較用に全ての方法で変換中...")
            convert_to_binary(input_file, "binary_simple_127.png", 127, "simple")
            convert_to_binary(input_file, "binary_otsu.png", method="otsu")
            convert_to_binary(input_file, "binary_adaptive.png", method="adaptive")
            print("全ての変換が完了しました")

if __name__ == "__main__":
    main()
