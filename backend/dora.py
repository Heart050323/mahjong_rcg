from ultralytics import YOLO
import cv2
import json
import os
import argparse
import tempfile

def recognize_dora_tiles(image_path, model_path="./models/best.pt", output_dir=None):
    """
    ドラ表示牌を認識する関数
    
    Args:
        image_path: 入力画像のパス
        model_path: モデルファイルのパス
        output_dir: 出力ディレクトリ（Noneの場合は一時ディレクトリを使用）
    
    Returns:
        list: 認識結果のリスト
    """
    if not os.path.exists(model_path):
        print(f"モデルファイル {model_path} が見つかりません。")
        return []
    
    if not os.path.exists(image_path):
        print(f"画像ファイル {image_path} が見つかりません。")
        return []
    
    # モデルを読み込み
    model = YOLO(model_path)
    
    # 出力ディレクトリの設定
    if output_dir is None:
        output_dir = tempfile.mkdtemp()
    else:
        os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 推論実行
        results = model.predict(
            source=image_path, 
            imgsz=960, 
            conf=0.25, 
            verbose=False
        )
        
        # 結果をJSON形式で保存
        detections = []
        if results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls)
                name = results[0].names[cls_id]
                conf = float(box.conf)
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append({
                    "class_id": cls_id,
                    "name": name,
                    "confidence": round(conf, 3),
                    "bbox": [x1, y1, x2, y2]
                })
        
        # 結果をJSONファイルに保存
        base_filename = os.path.splitext(os.path.basename(image_path))[0]
        json_path = os.path.join(output_dir, f"{base_filename}_dora_result.json")
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(detections, f, ensure_ascii=False, indent=2)
        
        print(f"ドラ表示牌認識結果を '{json_path}' に保存しました。")
        print(f"検出された牌: {len(detections)}枚")
        
        for detection in detections:
            print(f"  - {detection['name']} (信頼度: {detection['confidence']*100:.1f}%)")
        
        return detections
        
    except Exception as e:
        print(f"ドラ表示牌認識中にエラーが発生しました: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description='ドラ表示牌認識スクリプト')
    parser.add_argument('--input', type=str, required=True, help='入力画像のパス')
    parser.add_argument('--output', type=str, help='出力ディレクトリ（省略時は一時ディレクトリ）')
    parser.add_argument('--model', type=str, default='./models/best.pt', help='モデルファイルのパス')
    
    args = parser.parse_args()
    
    # ドラ表示牌認識を実行
    detections = recognize_dora_tiles(
        image_path=args.input,
        model_path=args.model,
        output_dir=args.output
    )
    
    if detections:
        print(f"\n=== ドラ表示牌認識完了 ===")
        print(f"検出された牌数: {len(detections)}")
        
        # 信頼度の高い順にソート
        sorted_detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        
        print("\n検出結果（信頼度順）:")
        for i, detection in enumerate(sorted_detections, 1):
            print(f"{i}. {detection['name']} (信頼度: {detection['confidence']*100:.1f}%)")
    else:
        print("ドラ表示牌が検出されませんでした。")

if __name__ == "__main__":
    main()
