from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import io
import json
import os
import subprocess
import tempfile
from PIL import Image
from datetime import datetime

app = Flask(__name__)
CORS(app)

# デバッグ用画像保存フォルダ
DEBUG_IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'debug_images')
os.makedirs(DEBUG_IMAGES_DIR, exist_ok=True)

def save_base64_image(image_data, filename):
    """Base64画像データをファイルに保存"""
    try:
        # base64デコード
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # 一時ファイルに保存
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        image.save(temp_path, 'JPEG')
        return temp_path
    except Exception as e:
        print(f"画像保存エラー: {e}")
        return None

def save_debug_image(image_data, image_type):
    """デバッグ用に画像を保存"""
    try:
        # base64デコード
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # タイムスタンプ付きファイル名を生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # ミリ秒まで
        filename = f"{timestamp}_{image_type}.jpg"
        debug_path = os.path.join(DEBUG_IMAGES_DIR, filename)
        
        # デバッグフォルダに保存
        image.save(debug_path, 'JPEG', quality=95)
        print(f"🖼️ デバッグ画像保存: {filename}")
        return debug_path
    except Exception as e:
        print(f"🚨 デバッグ画像保存エラー: {e}")
        return None

def run_process_script(image_path, output_dir):
    """process.pyを実行して牌認識を行う"""
    try:
        # process.pyを実行
        cmd = [
            'python', 'process.py',
            '--input', image_path,
            '--output', output_dir
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode != 0:
            print(f"process.py実行エラー: {result.stderr}")
            return None
        
        # 結果JSONファイルを探す
        json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
        if not json_files:
            return None
        
        json_path = os.path.join(output_dir, json_files[0])
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except Exception as e:
        print(f"process.py実行エラー: {e}")
        return None

def run_dora_script(image_path, output_dir):
    """dora.pyを実行してドラ表示牌認識を行う"""
    try:
        # dora.pyを実行
        cmd = [
            'python', 'dora.py',
            '--input', image_path,
            '--output', output_dir
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode != 0:
            print(f"dora.py実行エラー: {result.stderr}")
            return None
        
        # 結果JSONファイルを探す
        json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
        if not json_files:
            return None
        
        json_path = os.path.join(output_dir, json_files[0])
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except Exception as e:
        print(f"dora.py実行エラー: {e}")
        return None

def run_calculate_script(hand_json_path, dora_json_path, options):
    """caluculate.pyを実行して点数計算を行う"""
    try:
        # 一時JSONファイルを作成（hand_json_pathは既にJSONデータのリスト）
        temp_json = os.path.join(tempfile.gettempdir(), 'temp_hand.json')
        with open(temp_json, 'w', encoding='utf-8') as f:
            json.dump(hand_json_path, f)
        
        # caluculate.pyを実行
        cmd = [
            'python', 'caluculate.py',
            '--json', temp_json,
            '--threshold', '0.5'
        ]
        
        # オプションを追加
        if options.get('riichi'):
            cmd.append('--riichi')
        if options.get('ron'):
            cmd.append('--ron')
        if options.get('closed'):
            cmd.append('--closed')
        
        # 風の設定
        if options.get('roundWind'):
            cmd.extend(['--round_wind', options['roundWind']])
        if options.get('playerWind'):
            cmd.extend(['--seat_wind', options['playerWind']])
        
        # ドラ表示牌の設定
        if dora_json_path:
            print(f'🀅 ドラ表示牌処理開始: {len(dora_json_path)}枚の認識結果')
            dora_codes = []
            for i, detection in enumerate(dora_json_path):
                confidence = detection.get('confidence', 0)
                class_id = detection.get('class_id', 0)
                print(f'  ドラ{i+1}: class_id={class_id}, confidence={confidence:.3f}')
                
                if confidence > 0.5:
                    if 0 <= class_id < 40:  # 有効な牌の範囲
                        tile_codes = [
                            "1m","2m","3m","4m","5m","6m","7m","8m","9m",
                            "1p","2p","3p","4p","5p","6p","7p","8p","9p",
                            "1s","2s","3s","4s","5s","6s","7s","8s","9s",
                            "1z","2z","3z","4z","5z","6z","7z",
                            "0m","0p","0s"
                        ]
                        if class_id < len(tile_codes):
                            tile_code = tile_codes[class_id]
                            dora_codes.append(tile_code)
                            print(f'    → 採用: {tile_code}')
                        else:
                            print(f'    → 無効なclass_id: {class_id}')
                    else:
                        print(f'    → class_id範囲外: {class_id}')
                else:
                    print(f'    → 信頼度不足: {confidence:.3f} < 0.5')
            
            if dora_codes:
                print(f'📝 ドラコード配列: {dora_codes}')
                dora_string = ''.join(dora_codes)
                print(f'📝 結合結果: "{dora_string}"')
                print(f'📝 結合後の長さ: {len(dora_string)}文字')
                
                cmd.extend(['--dora', dora_string])
                print(f'✅ ドラ表示牌設定: {dora_string} ({len(dora_codes)}枚)')
                
                # コマンドライン引数を確認
                print(f'📋 最終コマンド引数に含まれるドラ: --dora {dora_string}')
            else:
                print('⚠️ 有効なドラ表示牌なし')
        else:
            print('ℹ️ ドラ表示牌データなし')
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode != 0:
            print(f"caluculate.py実行エラー: {result.stderr}")
            return None
        
        # 結果を解析（標準出力から点数情報を抽出）
        output_lines = result.stdout.strip().split('\n')
        result_data = {
            'han': 0,
            'fu': 0,
            'cost': {},
            'yaku': [],
            'raw_output': result.stdout
        }
        
        print(f"caluculate.py出力: {result.stdout}")  # デバッグ用
        
        # JSON形式の出力を優先的に使用
        for line in output_lines:
            if line.startswith('JSON_RESULT: '):
                try:
                    json_str = line[13:]  # "JSON_RESULT: "を除去
                    json_data = json.loads(json_str)
                    
                    # costが文字列の場合は辞書に変換
                    if isinstance(json_data.get('cost'), str):
                        try:
                            # 文字列を辞書に変換
                            cost_str = json_data['cost'].replace("'", '"')  # シングルクォートをダブルクォートに変換
                            json_data['cost'] = json.loads(cost_str)
                        except:
                            pass
                    
                    result_data.update(json_data)
                    return result_data
                except Exception as e:
                    print(f"JSON解析エラー: {e}")
                    pass
        
        # JSON形式がない場合は従来の解析
        for line in output_lines:
            if '翻数:' in line:
                try:
                    han_text = line.split(':')[1].strip()
                    result_data['han'] = int(han_text.replace('翻', ''))
                except:
                    pass
            elif '符数:' in line:
                try:
                    fu_text = line.split(':')[1].strip()
                    result_data['fu'] = int(fu_text.replace('符', ''))
                except:
                    pass
            elif '支払い/合計点:' in line:
                try:
                    cost_text = line.split(':')[1].strip()
                    result_data['cost'] = cost_text
                except:
                    pass
            elif line.startswith('- '):
                # 役の情報を抽出
                yaku_name = line[2:].split(' (')[0]
                result_data['yaku'].append(yaku_name)
        
        return result_data
        
    except Exception as e:
        print(f"caluculate.py実行エラー: {e}")
        return None

@app.route('/api/calculate', methods=['POST'])
def calculate_score():
    try:
        data = request.json
        print('📥 ===== API計算リクエスト受信 =====')
        
        # フロントエンドからのデータ取得
        hand_tiles_data = data.get('handTiles', [])
        dora_tiles_data = data.get('doraTiles', [])
        riichi = data.get('riichi', False)
        win_type = data.get('winType', 'tsumo')
        round_wind = data.get('roundWind', '東')
        player_wind = data.get('playerWind', '東')
        
        print(f'📋 受信パラメータ:')
        print(f'  手牌画像: {len(hand_tiles_data)}枚')
        print(f'  ドラ画像: {len(dora_tiles_data)}枚')
        print(f'  リーチ: {riichi}')
        print(f'  和了方法: {win_type}')
        print(f'  場風: {round_wind}')
        print(f'  自風: {player_wind}')
        
        if not hand_tiles_data:
            print('❌ 手牌画像なし')
            return jsonify({'error': '手牌の画像がありません'}), 400
        
        # 一時ディレクトリを作成
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 手牌画像を保存
            hand_image_path = save_base64_image(hand_tiles_data[0], 'hand_tiles.jpg')
            if not hand_image_path:
                return jsonify({'error': '手牌画像の保存に失敗しました'}), 400
            
            # デバッグ用画像保存
            save_debug_image(hand_tiles_data[0], 'hand_tiles')
            
            # 手牌認識を実行
            print('🀄 手牌認識開始...')
            hand_detections = run_process_script(hand_image_path, temp_dir)
            if not hand_detections:
                print('❌ 手牌認識失敗')
                return jsonify({'error': '手牌の認識に失敗しました'}), 400
            print(f'✅ 手牌認識完了: {len(hand_detections)}枚検出')
            
            # ドラ表示牌認識
            dora_detections = None
            if dora_tiles_data:
                print('🀅 ドラ表示牌認識開始...')
                dora_image_path = save_base64_image(dora_tiles_data[0], 'dora_tiles.jpg')
                if dora_image_path:
                    # デバッグ用画像保存
                    save_debug_image(dora_tiles_data[0], 'dora_tiles')
                    dora_detections = run_dora_script(dora_image_path, temp_dir)
                    if dora_detections:
                        print(f'✅ ドラ表示牌認識完了: {len(dora_detections)}枚検出')
                    else:
                        print('⚠️ ドラ表示牌認識失敗')
            else:
                print('ℹ️ ドラ表示牌なし')
            
            # 風の文字列を英語に変換
            def convert_wind_to_english(wind_str):
                wind_map = {
                    '東': 'east',
                    '南': 'south', 
                    '西': 'west',
                    '北': 'north'
                }
                return wind_map.get(wind_str, 'east')
            
            # 点数計算のオプション
            options = {
                'riichi': riichi,
                'ron': win_type == 'ron',
                'closed': True,  # 常に門前として計算
                'roundWind': convert_wind_to_english(round_wind),
                'playerWind': convert_wind_to_english(player_wind)
            }
            
            # 点数計算を実行
            print('🧮 点数計算開始...')
            result = run_calculate_script(hand_detections, dora_detections, options)
            if not result:
                print('❌ 点数計算失敗')
                return jsonify({'error': '点数計算に失敗しました'}), 400
            
            print(f'✅ 点数計算完了: {result["han"]}翻 {result["fu"]}符')
            print(f'🔍 計算結果詳細:')
            print(f'  翻数: {result["han"]}')
            print(f'  符数: {result["fu"]}')
            print(f'  点数: {result["cost"]}')
            print(f'  役: {result["yaku"]} ({len(result.get("yaku", []))}個)')
            
            # 結果の整形
            response = {
                'han': result['han'],
                'fu': result['fu'],
                'cost': result['cost'],
                'yaku': result['yaku'],
                'recognized_hand_tiles': len(hand_detections),
                'recognized_dora_tiles': len(dora_detections) if dora_detections else 0,
                'raw_output': result['raw_output']
            }
            
            print('📤 API応答データ:')
            print(f'  翻数: {response["han"]}')
            print(f'  符数: {response["fu"]}')
            print(f'  点数: {response["cost"]}')
            print(f'  役: {response["yaku"]}')
            print(f'  認識枚数: 手牌{response["recognized_hand_tiles"]}枚, ドラ{response["recognized_dora_tiles"]}枚')
            return jsonify(response)
            
        finally:
            # 一時ファイルを削除
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        print(f'🚨 API計算エラー: {e}')
        return jsonify({'error': f'計算エラー: {str(e)}'}), 500

@app.route('/api/recognize', methods=['POST'])
def recognize_single_tile():
    """単一の牌を認識するエンドポイント"""
    try:
        data = request.json
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'error': '画像データがありません'}), 400
        
        # 一時ディレクトリを作成
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 画像を保存
            image_path = save_base64_image(image_data, 'single_tile.jpg')
            if not image_path:
                return jsonify({'error': '画像の保存に失敗しました'}), 400
            
            # 牌認識を実行
            detections = run_process_script(image_path, temp_dir)
            if not detections:
                return jsonify({'error': '牌の認識に失敗しました'}), 400
            
            # 最も信頼度の高い結果を返す
            if detections:
                best_detection = max(detections, key=lambda x: x.get('confidence', 0))
                return jsonify({
                    'tile': best_detection.get('name', 'unknown'),
                    'confidence': best_detection.get('confidence', 0)
                })
            else:
                return jsonify({'tile': 'unknown', 'confidence': 0})
                
        finally:
            # 一時ファイルを削除
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"認識エラー: {e}")
        return jsonify({'error': f'認識エラー: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({'status': 'ok', 'message': '麻雀牌認識API is running'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
