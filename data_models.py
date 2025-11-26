# data_models.py

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
    def __init__(self, note_number: int, start_time: float, duration: float, velocity: int, lyrics: str = ""):
        self.note_number = note_number
        self.start_time = start_time
        self.duration = duration
        self.velocity = velocity
        self.lyrics = lyrics
        self.is_selected = False # GUI操作のための情報
        self.is_playing = False  # 追加: 再生中かどうかのフラグ

    def __repr__(self):
        return f"Note(pitch={self.note_number}, start={self.start_time:.2f}s, dur={self.duration:.2f}s, lyric='{self.lyrics}')"
    
    def to_dict(self):
        """クリップボードやファイル保存用に、辞書（JSON形式）に変換するメソッド"""
        return {
            "pitch": self.note_number,
            "start": self.start_time,
            "duration": self.duration,
            "velocity": self.velocity,
            "lyrics": self.lyrics
        }
        
    @staticmethod
    def from_dict(data: dict):
        """辞書（JSON形式）からオブジェクトに復元する（ペースト処理で使用）"""
        return NoteEvent(
            data['pitch'],
            data['start'],
            data['duration'],
            data['velocity'],
            data.get('lyrics', '')
        )
