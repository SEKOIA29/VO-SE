# data_models.py

from dataclasses import dataclass, field
from typing import List, Dict
from dataclasses import dataclass


class PitchEvent:
    """
    ピッチベンドのデータ構造を定義するクラス
    """
    def __init__(self, time: float, value: int): # valueは通常-8192から8191の範囲を想定
        self.time = time
        self.value = value

    def __repr__(self):
        return f"Pitch(time={self.time:.2f}s, value={self.value})"

    def to_dict(self):
        return {"time": self.time, "value": self.value}

    @staticmethod
    def from_dict(data: dict):
        return PitchEvent(data['time'], data['value'])


class NoteEvent:
    """
    ボーカロイドの音符（ノート）のデータ構造を定義するクラス
    """
    # ★修正: phonemes を引数とプロパティに追加
    def __init__(self, note_number: int, start_time: float, duration: float, velocity: int, lyrics: str = "", phonemes: list[str] = None):
        self.note_number = note_number
        self.start_time = start_time  # 開始秒
        self.duration = duration      # 長さ（秒）
        self.pitch = pitch            # MIDIノート番号 (69 = A4 = 440Hz)
        self.lyric = lyric            # 歌詞（"a", "i" など）
        # ★修正: デフォルト値を None から [] に変更
        self.phonemes = phonemes if phonemes is not None else [] 
        self.is_selected = False # GUI操作のための情報
        self.is_playing = False  # 追加: 再生中かどうかのフラグ

    def __repr__(self):
        # phonemesの表示を追加
        return f"Note(pitch={self.note_number}, start={self.start_time:.2f}s, dur={self.duration:.2f}s, lyric='{self.lyrics}', phonemes={self.phonemes})"
    
    def to_dict(self):
        """クリップボードやファイル保存用に、辞書（JSON形式）に変換するメソッド"""
        return {
            "pitch": self.note_number,
            "start": self.start_time,
            "duration": self.duration,
            "velocity": self.velocity,
            "lyrics": self.lyrics,
            "phonemes": self.phonemes # ★追加
        }
        
    @staticmethod
    def from_dict(data: dict):
        """辞書（JSON形式）からオブジェクトに復元する（ペースト処理で使用）"""
        return NoteEvent(
            data['pitch'],
            data['start'],
            data['duration'],
            data['velocity'],
            data.get('lyrics', ''),
            data.get('phonemes', []) # ★追加: デフォルト値として空のリストを設定
        )


class CharacterInfo:
    def __init__(self, char_id: str, name: str, description: str, engine_params: dict = None, waveform_type: str = "sine"): # waveform_typeを追加
        self.char_id = char_id
        self.name = name
        self.description = description
        self.engine_params = engine_params if engine_params is not None else {} 
        self.waveform_type = waveform_type # 'sine', 'square', 'sawtooth', 'sample_based'などを想定

@dataclass
class NoteEvent:
    note_number: int
    start_time: float
    duration: float
    velocity: int = 100
    lyric: str = ""
    phonemes: List[str] = field(default_factory=list)

@dataclass
class PitchEvent:
    time: float
    value: int

@dataclass
class CharacterInfo:
    id: str
    name: str
    description: str
    engine_params: Dict
    waveform_type: str = "sample_based"


@dataclass
class CharacterInfo:
    id: str           # "char_001" など
    name: str         # "アオイ" など
    audio_dir: str    # "audio_data/aoi" などのパス



