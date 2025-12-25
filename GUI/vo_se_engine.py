# vo_se_engine.py

import ctypes
import os
import platform
import numpy as np
import pyaudio
from data_models import NoteEvent, PitchEvent, CharacterInfo
import ctypes
import math
import sys

def get_resource_path(relative_path):
    # PyInstallerが展開する一時フォルダのパス、または通常実行時のパスを取得
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

# DLLの読み込み部分
dll_name = "engine.dll" if os.name == 'nt' else "engine.dylib"
dll_path = get_resource_path(f"VO_SE_engine_C/lib/{dll_name}")
self.lib = ctypes.CDLL(dll_path)
if getattr(sys, 'frozen', False):
    # インストーラー（実行ファイル）として動いている場合
    base_dir = sys._MEIPASS
else:
    # 通常のPythonスクリプトとして動いている場合
    base_dir = os.path.dirname(os.path.abspath(__file__))

# C言語側の構造体と合わせる
class C_NoteEvent(ctypes.Structure):
    _fields_ = [
        ("frequency", ctypes.c_float),
        ("duration", ctypes.c_float),
        ("lyric", ctypes.c_char_p)
    ]

def export_wav(self, notes_list, output_path="output/output.wav"):
    # 1. PythonのノートリストをC言語用の構造体配列に変換
    c_notes_array = (C_NoteEvent * len(notes_list))()
    
    for i, note in enumerate(notes_list):
        c_notes_array[i].frequency = self.midi_to_hz(note.pitch)
        c_notes_array[i].duration = note.duration
        c_notes_array[i].lyric = note.lyric.encode('utf-8')

    # 2. C言語の書き出し関数を呼び出す
    self.lib.execute_render_to_file(
        output_path.encode('utf-8'), 
        c_notes_array, 
        len(notes_list)
    )
    

class VoSeEngineWrapper:
    def __init__(self):
        # C言語でビルドしたDLLをロード
        try:
            self.lib = ctypes.CDLL("./VO_SE_engine_C/lib/engine.dll")
            # C関数の引数型定義: void set_target_frequency(float freq)
            self.lib.set_target_frequency.argtypes = [ctypes.c_float]
        except Exception as e:
            print(f"DLLロード失敗: {e}")
        # OSに応じたライブラリのロード
        dll_path = os.path.abspath("./VO_SE_engine_C/lib/engine.dll")
        self.lib = ctypes.CDLL(dll_path)

        # C関数の型定義
        # void set_frequency(float hz)
        self.lib.set_frequency.argtypes = [ctypes.c_float]
        self.lib.play_note.argtypes = []

    def midi_to_hz(self, midi_note):
        # MIDIノート番号から周波数(Hz)への変換公式
        return 440.0 * math.pow(2.0, (midi_note - 69.0) / 12.0)

    def set_pitch(self, midi_note):
        hz = self.midi_to_hz(midi_note)
        print(f"DEBUG: 周波数 {hz:.2f}Hz をエンジンに送信")
        self.lib.set_frequency(hz)

    def play_preview(self):
        self.lib.play_note()



def get_base_path():
    """実行ファイル(Nuitka/PyInstaller)化されていても、開発中でも正しくルートを返す"""
    if hasattr(sys, '_MEIPASS'):
        # パッケージ化（1ファイル化）された時の一時展開先
        return sys._MEIPASS
    # 開発中の実行時（GUI/vo_se_engine.pyから見たプロジェクトルート）
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# --- 実際の使用例 ---
base = get_base_path()

# 拡張子の自動判別
ext = ".dll" if platform.system() == "Windows" else ".dylib"

# C言語エンジンのパスを結合
lib_path = os.path.join(base, "VO_SE_engine_C", "lib", f"engine{ext}")

# 音源フォルダのパスを結合
audio_dir = os.path.join(base, "audio_data")

print(f"Loading Engine from: {lib_path}")
print(f"Audio Data Path: {audio_dir}")



class VO_SE_Engine:
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.active_character_id = None
        self._keep_alive = []  # C側へ渡すデータのメモリ解放を防ぐ

        # --- 1. C 言語ライブラリ (.dylib / .dll) のパスを特定 ---
        # OS に応じて拡張子を自動判別
        ext = ".dylib" if platform.system() == "Darwin" else ".dll"
        # ライブラリの保存場所（VO_SE_engine_C/lib/ 内）を指定
        base_dir = os.path.dirname(os.path.abspath(__file__))
        lib_path = os.path.join(base_dir, "../VO_SE_engine_C/lib/engine" + ext)

        # --- 2. ライブラリを Python にロード ---
        try:
            # これが「連絡口」を開く核心の処理です
            self.lib = ctypes.CDLL(lib_path)
            
            # C 言語の関数の「引数」と「戻り値」の型を Python に教えてあげる (大事！)
            self._setup_c_interfaces()
            print(f"C-Engine Loaded Successfully: {lib_path}")
        except Exception as e:
            print(f"C-Engine Load Error: {e}")
            print("注意: 先に 'make' 等で C 言語をビルドして engine" + ext + " を作成してください。")

        # --- 3. 音声再生用 (PyAudio) の初期化 ---
        self.pyaudio_instance = pyaudio.PyAudio()

    def _setup_c_interfaces(self):
        """C 言語の関数を Python で正しく呼べるように設定する"""
        # init_engine(char* char_id, char* audio_dir)
        self.lib.init_engine.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self.lib.init_engine.restype = ctypes.c_int

        # request_synthesis_full(...) -> float*
        from .vo_se_engine import SynthesisRequest # 構造体定義
        self.lib.request_synthesis_full.argtypes = [SynthesisRequest, ctypes.POINTER(ctypes.c_int)]
        self.lib.request_synthesis_full.restype = ctypes.POINTER(ctypes.c_float)

        # vse_free_buffer(float*)
        self.lib.vse_free_buffer.argtypes = [ctypes.POINTER(ctypes.c_float)]
        self.lib.vse_free_buffer.restype = None


    def switch_character(self, char_id: str):
        """
        GUIから選ばれたIDを元に、Cエンジンへ切り替えを指示する
        """
        if char_id not in self.available_characters:
            print(f"エラー: {char_id} というキャラクターは名簿にありません。")
            return False
        
        char = self.available_characters[char_id]
        
        # パスを絶対パスに変換（C言語側で確実に読み込むため）
        abs_path = os.path.abspath(char.audio_dir)
        
        # C言語の init_engine(char* id, char* dir) を呼び出し
        # 2025年現在、文字列は .encode('utf-8') で渡すのが鉄則です
        result = self.lib.init_engine(
            char.id.encode('utf-8'), 
            abs_path.encode('utf-8')
        )
        
        if result == 0:
            self.current_char_id = char_id
            print(f"C-Engine: {char.name} への切り替えに成功しました。")
            return True
        else:
            print(f"C-Engine: {char.name} の音源ロードに失敗しました。")
            return False



# --- 1. C言語と共通のデータ構造定義 (ctypes) ---

class CPitchEvent(ctypes.Structure):
    _fields_ = [("time", ctypes.c_float), ("value", ctypes.c_int)]

class CNoteEvent(ctypes.Structure):
    _fields_ = [
        ("note_number", ctypes.c_int),
        ("start_time", ctypes.c_float),
        ("duration", ctypes.c_float),
        ("velocity", ctypes.c_int),
        ("lyrics", ctypes.c_char * 256),
        ("phonemes", ctypes.POINTER(ctypes.c_char_p)), # char** 型
        ("phoneme_count", ctypes.c_int)
    ]

class SynthesisRequest(ctypes.Structure):
    _fields_ = [
        ("notes", ctypes.POINTER(CNoteEvent)),
        ("note_count", ctypes.c_int),
        ("pitch_events", ctypes.POINTER(CPitchEvent)),
        ("pitch_event_count", ctypes.c_int),
        ("sample_rate", ctypes.c_int)
    ]

# --- 2. エンジン本体のクラス ---

class VO_SE_Engine:
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.active_character_id = None
        self.pyaudio_instance = pyaudio.PyAudio()
        self._keep_alive = [] # Cへ渡すデータのメモリ解放を防ぐためのリスト

        # --- C言語ライブラリのロード (OS自動判別) ---
        ext = ".dylib" if platform.system() == "Darwin" else ".dll"
        lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"../VO_SE_engine_C/lib/engine{ext}"))
        
        try:
            self.lib = ctypes.CDLL(lib_path)
            self._setup_c_interfaces()
            print(f"C-Engine Loaded: {lib_path}")
        except Exception as e:
            print(f"C-Engine Load Error: {e}\nビルドされたライブラリが lib/ にあるか確認してください。")

    　　# GUI/vo_se_engine.py の VO_SE_Engine クラス内に追加

　　　def load_character(self, char_id: str, folder_path: str):
        """
        C言語エンジンに音源の読み込みを命令する
        """
        path_bytes = os.path.abspath(folder_path).encode('utf-8')
        id_bytes = char_id.encode('utf-8')
    
        # C言語の init_engine を呼び出す
        result = self.lib.init_engine(id_bytes, path_bytes)
    
        if result == 0:
           print(f"成功: キャラクター {char_id} をロードしました。")
        else:
           print(f"失敗: {folder_path} が見つからないか、読み込めませんでした。")


    def _setup_c_interfaces(self):
        """C言語関数の引数と戻り値を設定"""
        # init_engine(char* id, char* dir)
        self.lib.init_engine.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self.lib.init_engine.restype = ctypes.c_int

        # request_synthesis_full(SynthesisRequest, int*)
        self.lib.request_synthesis_full.argtypes = [SynthesisRequest, ctypes.POINTER(ctypes.c_int)]
        self.lib.request_synthesis_full.restype = ctypes.POINTER(ctypes.c_float)

        # vse_free_buffer(float*)
        self.lib.vse_free_buffer.argtypes = [ctypes.POINTER(ctypes.c_float)]
        self.lib.vse_free_buffer.restype = None

    def set_active_character(self, char_info: CharacterInfo):
        """キャラクターを切り替え、Cエンジンに音源をロードさせる"""
        self.active_character_id = char_info.id
        audio_dir = os.path.abspath(char_info.engine_params.get("audio_dir", ""))
        result = self.lib.init_engine(char_info.id.encode('utf-8'), audio_dir.encode('utf-8'))
        if result == 0:
            print(f"Character {char_info.name} loaded successfully.")
        else:
            print(f"Failed to load character {char_info.name}.")

    def _convert_to_c_structs(self, py_notes, py_pitches):
        """PythonのリストをCの構造体配列に変換"""
        self._keep_alive = [] # 以前のデータをクリア
        
        # 1. ノートの変換
        c_notes = (CNoteEvent * len(py_notes))()
        for i, n in enumerate(py_notes):
            c_notes[i].note_number = n.note_number
            c_notes[i].start_time = n.start_time
            c_notes[i].duration = n.duration
            c_notes[i].velocity = n.velocity
            c_notes[i].lyrics = n.lyric.encode('utf-8')
            
            # 音素リスト(char**)の構築
            if n.phonemes:
                ph_bytes = [p.encode('utf-8') for p in n.phonemes]
                ph_array = (ctypes.c_char_p * len(ph_bytes))(*ph_bytes)
                self._keep_alive.append(ph_array) # C側実行中に消えないよう保持
                c_notes[i].phonemes = ph_array
                c_notes[i].phoneme_count = len(ph_bytes)

        # 2. ピッチイベントの変換
        c_pitches = (CPitchEvent * len(py_pitches))(*[
            CPitchEvent(p.time, p.value) for p in py_pitches
        ])
        
        return c_notes, c_pitches

    def synthesize(self, notes: list[NoteEvent], pitch_events: list[PitchEvent]) -> np.ndarray:
        """Cエンジンを呼び出して音声を合成し、NumPy配列を返す"""
        if not notes: return np.zeros(0, dtype=np.float32)

        c_notes, c_pitches = self._convert_to_c_structs(notes, pitch_events)
        
        req = SynthesisRequest(
            notes=c_notes,
            note_count=len(notes),
            pitch_events=c_pitches,
            pitch_event_count=len(pitch_events),
            sample_rate=self.sample_rate
        )

        out_count = ctypes.c_int(0)
        # C関数の呼び出し
        audio_ptr = self.lib.request_synthesis_full(req, ctypes.byref(out_count))

        if audio_ptr:
            # ポインタからNumPy配列を作成し、Python側へコピー
            raw_data = np.ctypeslib.as_array(audio_ptr, shape=(out_count.value,))
            audio_data = raw_data.copy()
            
            # C側のメモリを解放
            self.lib.vse_free_buffer(audio_ptr)
            return audio_data
        
        return np.zeros(0, dtype=np.float32)

    def play_audio(self, audio_data: np.ndarray):
        """合成した音声を再生する"""
        if audio_data.size == 0: return
        stream = self.pyaudio_instance.open(
            format=pyaudio.paFloat32, channels=1, rate=self.sample_rate, output=True
        )
        stream.write(audio_data.tobytes())
        stream.stop_stream()
        stream.close()

    def close(self):
        """終了処理"""
        self.pyaudio_instance.terminate()

