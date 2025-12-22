# vo_se_engine.py

import ctypes
import os
import platform
import numpy as np
import pyaudio
from data_models import NoteEvent, PitchEvent, CharacterInfo

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

