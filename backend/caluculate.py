
import json
import argparse
import sys
import subprocess
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple


# === mahjongライブラリの存在確認 ===
def ensure_mahjong(debug: bool=False):
    try:
        import mahjong  # noqa: F401
        if debug:
            print("[debug] mahjong は既に存在します")
        return
    except Exception:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--upgrade", "mahjong"], check=True)
        import mahjong  # noqa: F401


# === mahjong モジュールの読み込み ===
def _import_mahjong():
    from mahjong.hand_calculating.hand import HandCalculator
    from mahjong.tile import TilesConverter
    try:
        from mahjong.wind import EAST, SOUTH, WEST, NORTH
    except Exception:
        from mahjong.constants import EAST, SOUTH, WEST, NORTH
    from mahjong.hand_calculating.hand_config import HandConfig, OptionalRules
    return HandCalculator, TilesConverter, (EAST, SOUTH, WEST, NORTH), HandConfig, OptionalRules


# === class id → 牌コード ===
CLASS_ID_TO_CODE = [
    "1m","2m","3m","4m","5m","6m","7m","8m","9m",
    "1p","2p","3p","4p","5p","6p","7p","8p","9p",
    "1s","2s","3s","4s","5s","6s","7s","8s","9s",
    "1z","2z","3z","4z","5z","6z","7z",
    "0m","0p","0s",
]


def get_class_id(d: Dict[str, Any]) -> int | None:
    for k in ("class", "class_id", "cls", "category_id"):
        if k in d:
            try:
                return int(d[k])
            except Exception:
                return None
    return None


def get_confidence(d: Dict[str, Any]) -> float:
    for k in ("confidence", "conf", "score"):
        if k in d:
            try:
                return float(d[k])
            except Exception:
                return 0.0
    return 0.0


def counts_from_detections(dets: List[Dict[str, Any]], threshold=0.5):
    counts = Counter()
    kept: List[Tuple[str, float, List[float]]] = []
    for d in dets:
        cid = get_class_id(d)
        if cid is None or cid < 0 or cid >= len(CLASS_ID_TO_CODE):
            continue
        conf = get_confidence(d)
        if conf < threshold:
            continue
        code = CLASS_ID_TO_CODE[cid]
        bbox = d.get("bbox", [0, 0, 0, 0])
        counts[code] += 1
        kept.append((code, conf, bbox))
    return counts, kept


def to_pretty_counts(counts: Counter) -> str:
    lines = []
    def suit_block(suit, title, nums):
        block = []
        for n in nums:
            code = f"{n}{suit}"
            c = counts.get(code, 0)
            if suit in "mps" and n == 5:
                rc = counts.get(f"0{suit}", 0)
                total = c + rc
                if total > 0:
                    block.append(f"{code}:{c} (赤:{rc}, 合計:{total})")
            elif c > 0:
                block.append(f"{code}:{c}")
        if block:
            lines.append(f"{title}  " + "  ".join(block))
    suit_block("m", "萬子", range(1, 10))
    suit_block("p", "筒子", range(1, 10))
    suit_block("s", "索子", range(1, 10))

    honors_names = ["東","南","西","北","白","發","中"]
    honors_block = [f"{honors_names[n-1]}(z):{counts.get(f'{n}z', 0)}" for n in range(1,8) if counts.get(f"{n}z", 0)]
    if honors_block:
        lines.append("字牌  " + "  ".join(honors_block))
    return "\n".join(lines) if lines else "(カウントなし)"


def select_14_tiles(kept: List[Tuple[str, float, List[float]]]) -> List[str]:
    kept_sorted = sorted(kept, key=lambda x: x[1], reverse=True)
    result = []
    per_normal_counts = defaultdict(int)
    per_code_counts = defaultdict(int)
    def base_five(code): return {"0m": "5m", "0p": "5p", "0s": "5s"}.get(code, code)
    for code, _, _ in kept_sorted:
        base = base_five(code)
        if per_normal_counts[base] >= 4 or per_code_counts[code] >= 4:
            continue
        result.append(code)
        per_normal_counts[base] += 1
        per_code_counts[code] += 1
        if len(result) == 14:
            break
    return result


def tiles_list_to_string(tiles):
    buckets = {"m": [], "p": [], "s": [], "z": []}
    for c in tiles:
        n_str, suit = c[:-1], c[-1]
        # 赤ドラの処理: 0を5に変換
        if n_str == "0":
            n_str = "5"
        buckets[suit].append(int(n_str))
    parts = []
    for s in ("m","p","s","z"):
        if buckets[s]:
            parts.append("".join(str(n) for n in sorted(buckets[s])) + s)
    return "".join(parts)


def safe_string_to_136_array(TilesConverter, tiles_str):
    if not tiles_str:
        return []
    
    try:
        return TilesConverter.string_to_136_array(tiles=tiles_str)
    except TypeError:
        man, pin, sou, honors = "", "", "", ""
        tmp = ""
        for ch in tiles_str:
            if ch in "mpsz":
                if ch == "m": 
                    man += tmp
                    tmp = ""
                elif ch == "p": 
                    pin += tmp
                    tmp = ""
                elif ch == "s": 
                    sou += tmp
                    tmp = ""
                elif ch == "z": 
                    honors += tmp
                    tmp = ""
            else:
                tmp += ch
        
        return TilesConverter.string_to_136_array(man=man, pin=pin, sou=sou, honors=honors)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=str, required=True)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--closed", action="store_true")
    ap.add_argument("--ron", action="store_true")
    ap.add_argument("--riichi", action="store_true")
    ap.add_argument("--round_wind", type=str, default="east")
    ap.add_argument("--seat_wind", type=str, default="east")
    ap.add_argument("--dora", type=str, default="")
    args, _ = ap.parse_known_args()

    # 引数の確認
    print("🔍 ===== 受信引数確認 =====")
    print(f"  ドラ引数: '{args.dora}' (長さ: {len(args.dora)})")
    print(f"  リーチ: {args.riichi}, 門前: {args.closed}, ロン: {args.ron}")
    print(f"  場風: {args.round_wind}, 自風: {args.seat_wind}")

    ensure_mahjong()
    HandCalculator, TilesConverter, (EAST, SOUTH, WEST, NORTH), HandConfig, OptionalRules = _import_mahjong()

    with open(args.json, "r", encoding="utf-8") as f:
        detections = json.load(f)
    counts, kept = counts_from_detections(detections, threshold=args.threshold)

    print("🀄 ===== 存在する牌とその枚数 =====")
    print(to_pretty_counts(counts))
    


    if not kept:
        print("❌ 有効な検出がありません。")
        return

    winning_tile_info = max(kept, key=lambda x: x[2][2])  # xmax
    winning_tile = winning_tile_info[0]
    print(f"🎯 自動判定されたあがり牌: {winning_tile}")

    tiles14 = select_14_tiles(kept)
    if len(tiles14) < 14:
        print(f"⚠️ 枚数不足: {len(tiles14)}枚 (14枚未満)")
        return
    if winning_tile not in tiles14:
        tiles14[-1] = winning_tile

    tiles_str = tiles_list_to_string(tiles14)
    print(f"🧮 ===== 点数計算入力 =====")
    print(f"🀄 手牌(14枚): {tiles_str}")
    print(f"🎯 和了牌: {winning_tile}")

    tiles_136 = safe_string_to_136_array(TilesConverter, tiles_str)
    win_tile_136 = safe_string_to_136_array(TilesConverter, winning_tile)[0]
    
    # ドラインジケーターの変換
    if args.dora:
        print(f"🀅 ドラ表示牌設定: {args.dora} ({len(args.dora.replace('m', '').replace('p', '').replace('s', '').replace('z', ''))}枚)")
        dora_indicators = safe_string_to_136_array(TilesConverter, args.dora)
    else:
        print("ℹ️ ドラ表示牌なし")
        dora_indicators = []

    # --- OptionalRules を安全に設定 ---
    options = OptionalRules()  # 引数なしで作成（互換性のため）
    def set_opt(name, value):
        if hasattr(options, name):
            setattr(options, name, value)

    set_opt("has_open_tanyao", True)   # 喰いタン可
    set_opt("has_aka_dora", True)      # 赤ドラあり
    set_opt("has_double_yakuman", True)
    set_opt("kiriage", False)
    set_opt("kazoe_limit", True)
    set_opt("kiriage_limit", True)     # 無い版では無視される
    set_opt("is_tsumo_loss", False)

    # --- HandConfig 設定 ---
    config = HandConfig(
        is_riichi=args.riichi,
        is_tsumo=not args.ron,
        player_wind={"east": EAST, "south": SOUTH, "west": WEST, "north": NORTH}[args.seat_wind.lower()],
        round_wind={"east": EAST, "south": SOUTH, "west": WEST, "north": NORTH}[args.round_wind.lower()],
        options=options,
    )

    # 追加フラグ（環境で存在するかもしれないものを安全に上書き）
    def set_cfg(name, value):
        setattr(config, name, value)  # HandConfig は基本的に is_*** をサポート

    set_cfg("is_daburu_riichi", False)
    set_cfg("is_ippatsu", False)
    set_cfg("is_haitei", False)
    set_cfg("is_houtei", False)
    set_cfg("is_rinshan", False)
    set_cfg("is_chankan", False)
    set_cfg("is_tenhou", False)
    set_cfg("is_chiihou", False)
    set_cfg("is_renhou", False)
    set_cfg("is_dealer", args.seat_wind.lower() in ("east", "e", "東"))

    calc = HandCalculator()
    try:
        result = calc.estimate_hand_value(
            tiles=tiles_136,
            win_tile=win_tile_136,
            melds=[],
            dora_indicators=dora_indicators,
            config=config
        )
    except Exception as e:
        print(f"🚨 点数計算エラー: {e}")
        print(f"  手牌: {tiles_str}")
        print(f"  和了牌: {winning_tile}")
        print(f"  tiles_136: {tiles_136}")
        print(f"  win_tile_136: {win_tile_136}")
        return

    print("✅ ===== 点数計算結果 =====")
    
    # 結果の検証
    if not result:
        print("❌ 結果がNoneです")
        return
    
    def _yaku_name(y):
        return getattr(y, "name", y.__class__.__name__)

    def _yaku_han(y, is_closed: bool):
        # 役インスタンスが han / han_closed / han_open のどれを持っているかに応じて返す
        if hasattr(y, "han"):
            return getattr(y, "han")
        if is_closed and hasattr(y, "han_closed"):
            return getattr(y, "han_closed")
        if (not is_closed) and hasattr(y, "han_open"):
            return getattr(y, "han_open")
        return None

    if result.yaku:
        print("🎌 役:")
        for y in result.yaku:
            name = _yaku_name(y)
            hv = _yaku_han(y, is_closed=args.closed)
            if hv is not None:
                print(f"  - {name} ({hv}翻)")
            else:
                print(f"  - {name}")
    else:
        print("❌ 役: なし（0翻）")

    print(f"🔢 翻数: {result.han}翻")
    print(f"🎯 符数: {result.fu}符")
    if result.cost:
        print(f"💰 支払い/合計点: {result.cost}")
    if hasattr(result, 'limit') and result.limit:
        print(f"🏆 役満区分: {result.limit}")
    elif hasattr(result, 'yaku') and result.yaku:
        print(f"役: {result.yaku}")

    # 役名を日本語に変換する辞書
    yaku_japanese_map = {
        "Menzen Tsumo": "門前清自摸和",
        "Pinfu": "平和",
        "Sanshoku Doujun": "三色同順",
        "Junchan": "純全帯幺九",
        "Dora": "ドラ",
        "Aka Dora": "赤ドラ",
        "Ittsu": "一通",
        "Riichi": "立直",
        "Ippatsu": "一発",
        "Tanyao": "断幺九",
        "Yakuhai": "役牌",
        "Yakuhai (east)": "役牌（東）",
        "Yakuhai (south)": "役牌（南）",
        "Yakuhai (west)": "役牌（西）",
        "Yakuhai (north)": "役牌（北）",
        "Yakuhai (haku)": "役牌（白）",
        "Yakuhai (hatsu)": "役牌（發）",
        "Yakuhai (chun)": "役牌（中）",
        "Sanshoku Doukou": "三色同刻",
        "Sankantsu": "三槓子",
        "Toitoi": "対々和",
        "Chiitoitsu": "七対子",
        "Honrou": "混老頭",
        "Ryanpeikou": "二盃口",
        "Chanta": "混全帯幺九",
        "Sanankou": "三暗刻",
        "Shousangen": "小三元",
        "Honitsu": "混一色",
        "Chinitsu": "清一色",
        "Kokushi Musou": "国士無双",
        "Suuankou": "四暗刻",
        "Daisangen": "大三元",
        "Tsuuiisou": "字一色",
        "Chinroutou": "清老頭",
        "Ryuuiisou": "緑一色",
        "Suukantsu": "四槓子",
        "Tenhou": "天和",
        "Chiihou": "地和",
        "Renhou": "人和"
    }
    
    # 役名を日本語に変換
    def translate_yaku_name(english_name):
        # ドラの場合は「ドラ」に変換
        if english_name.startswith("Dora"):
            if english_name == "Dora":
                return "ドラ"
            else:
                # "Dora 1" などは「ドラ 1」に変換
                return english_name.replace("Dora", "ドラ")
        return yaku_japanese_map.get(english_name, english_name)
    
    # JSON形式でも出力（API用）
    # costを適切な形式に変換
    cost_dict = None
    if result.cost:
        if hasattr(result.cost, 'main') and hasattr(result.cost, 'additional'):
            cost_dict = {
                "main": result.cost.main,
                "additional": result.cost.additional
            }
        else:
            # 辞書形式でない場合は文字列として扱う
            cost_dict = str(result.cost)
    
    # 役のリストを翻数付きで作成
    yaku_with_han = []
    if result.yaku:
        for y in result.yaku:
            yaku_name = translate_yaku_name(_yaku_name(y))
            han_value = _yaku_han(y, is_closed=args.closed)
            if han_value is not None:
                yaku_with_han.append(f"{yaku_name} ({han_value}翻)")
            else:
                yaku_with_han.append(yaku_name)
    
    json_result = {
        "han": result.han,
        "fu": result.fu,
        "cost": cost_dict,
        "yaku": yaku_with_han
    }
    print(f"JSON_RESULT: {json.dumps(json_result, ensure_ascii=False)}")

    print("\n※ 備考: mahjong 1.4.0 完全対応（HandConfig使用・OptionalRulesは安全設定）")


if __name__ == "__main__":
    main()
