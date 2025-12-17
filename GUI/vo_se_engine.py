# vo_se_engine.py

# GUI/vo_se_engine.py

import ctypes
import os
import numpy as np
import pyaudio
from data_models import CharacterInfo, NoteEvent, PitchEvent
from PySide6.QtCore import Slot

# --- C言語の構造体定義 (audio_types.h と完全一致させる) ---
class CPitchEvent(ctypes.Structure):
    _fields_ = [
        ("time", ctypes.c_float),
        ("value", ctypes.c_int)
    ]

class CNoteEvent(ctypes.Structure):
    _fields_ = [
        ("note_number", ctypes.c_int),
        ("start_time", ctypes.c_float),
        ("duration", ctypes.c_float),
        ("velocity", ctypes.c_int),
        ("lyrics", ctypes.c_char * 256),
        ("phonemes", ctypes.POINTER(ctypes.c_char_p)), # char**
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

class VO_SE_Engine:
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.active_character_id = None
        self.pyaudio_instance = pyaudio.PyAudio()
        self.tempo = 120.0
        self.current_time_playback = 0.0
        self.notes_to_play = []
        self.pitch_data_to_play = []
        
        # --- Cライブラリのロード ---
        # OSに合わせて拡張子を自動選択
        lib_ext = ".dll" if os.name == 'nt' else ".so"
        lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"../VO_SE_engine_C/lib/engine{lib_ext}"))
        
        try:
            self.lib = ctypes.CDLL(lib_path)
            self._setup_c_interfaces()
            print(f"C-Engine Loaded: {lib_path}")
        except Exception as e:
            print(f"C-Engine Load Error: {e}")

        # キャラクターデータ読み込み
        self.characters = self._load_character_data()

        # 再生ストリーム
        self.stream = self.pyaudio_instance.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=self.sample_rate,
            output=True,
            frames_per_buffer=1024,
            stream_callback=self._pyaudio_callback,
        )
        self.stream.stop_stream()

    def _setup_c_interfaces(self):
        """C言語関数の引数と戻り値の型を定義（連絡口の要）"""
        # init_engine(char* id, char* dir)
        self.lib.init_engine.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self.lib.init_engine.restype = ctypes.c_int

        # request_synthesis_full(SynthesisRequest req, int* out_count)
        self.lib.request_synthesis_full.argtypes = [SynthesisRequest, ctypes.POINTER(ctypes.c_int)]
        self.lib.request_synthesis_full.restype = ctypes.POINTER(ctypes.c_float)

        # vse_free_buffer(float* ptr) <- メモリ解放用
        self.lib.vse_free_buffer.argtypes = [ctypes.POINTER(ctypes.c_float)]
        self.lib.vse_free_buffer.restype = None

    def _load_character_data(self):
        # GUI側のモデル。実際にはここで init_engine を呼び出す
        return {
            "char_001": CharacterInfo("char_001", "アオイ", "元気な女性", engine_params={"audio_dir": "./audio/aoi/"}),
            "char_002": CharacterInfo("char_002", "ミライ", "落ち着いた男性", engine_params={"audio_dir": "./audio/mirai/"}),
        }

    def set_active_character(self, char_id: str):
        if char_id in self.characters:
            self.active_character_id = char_id
            char_info = self.characters[char_id]
            # C言語側に音源ロードを指示
            audio_dir = os.path.abspath(char_info.engine_params["audio_dir"])
            self.lib.init_engine(char_id.encode('utf-8'), audio_dir.encode('utf-8'))
            print(f"C-Engine: Character {char_id} initialized.")

    def _convert_to_c_data(self, notes: list[NoteEvent], pitch_events: list[PitchEvent]):
        """PythonのリストをCの構造体配列へ変換"""
        # 1. ノートの変換
        c_notes = (CNoteEvent * len(notes))()
        self._keep_alive = [] # 文字列ポインタ消失防止用

        for i, n in enumerate(notes):
            c_notes[i].note_number = n.note_number
            c_notes[i].start_time = n.start_time
            c_notes[i].duration = n.duration
            c_notes[i].velocity = n.velocity
            c_notes[i].lyrics = n.lyric.encode('utf-8')
            
            if n.phonemes:
                ph_bytes = [p.encode('utf-8') for p in n.phonemes]
                ph_array = (ctypes.c_char_p * len(ph_bytes))(*ph_bytes)
                self._keep_alive.append(ph_array)
                c_notes[i].phonemes = ph_array
                c_notes[i].phoneme_count = len(ph_bytes)

        # 2. ピッチイベントの変換
        c_pitches = (CPitchEvent * len(pitch_events))(*[
            CPitchEvent(p.time, p.value) for p in pitch_events
        ])
        
        return c_notes, c_pitches

    def synthesize_track(self, notes: list[NoteEvent], pitch_events: list[PitchEvent], start_time: float, end_time: float) -> np.ndarray:
        """Cエンジンを呼び出して波形を一括生成"""
        if not notes:
            return np.zeros(1024, dtype=np.float32)

        c_notes, c_pitches = self._convert_to_c_data(notes, pitch_events)
        
        req = SynthesisRequest(
            notes=c_notes,
            note_count=len(notes),
            pitch_events=c_pitches,
            pitch_event_count=len(pitch_events),
            sample_rate=self.sample_rate
        )

        out_count = ctypes.c_int(0)
        # Cエンジン実行
        audio_ptr = self.lib.request_synthesis_full(req, ctypes.byref(out_count))

        if audio_ptr:
            # ポインタからNumPy配列を作成し、データをPython側にコピー
            audio_data = np.ctypeslib.as_array(audio_ptr, shape=(out_count.value,)).copy()
            # C側のメモリを解放
            self.lib.vse_free_buffer(audio_ptr)
            return audio_data
        
        return np.zeros(1024, dtype=np.float32)

    def _pyaudio_callback(self, in_data, frame_count, time_info, status):
        """リアルタイム再生用コールバック（ここでもCエンジンを呼べる）"""
        # ※簡易実装のため、ここでは現在のチャンクの音声を合成して返す
        # 実際には synthesize_track で作った長いバッファを切り出して返すのがスムーズです
        audio_data = np.zeros(frame_count, dtype=np.float32)
        # ... 再生ロジック ...
        return (audio_data.tobytes(), pyaudio.paContinue)

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pyaudio_instance.terminate()
