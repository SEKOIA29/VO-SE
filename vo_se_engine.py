# vo_se_engine.py

import numpy as np
import pyaudio
import json
import os
from data_models import CharacterInfo, NoteEvent, PitchEvent # data_modelsから必要なクラスをインポート

class VO_SE_Engine: # クラス名を修正
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.characters = self._load_character_data()
        self.active_character_id = None
        self.pyaudio_instance = pyaudio.PyAudio()
        # pyaudio ストリームを初期化時に開いておく (リアルタイムバッファリング用)
        self.stream = self.pyaudio_instance.open(format=pyaudio.paFloat32,
                                  channels=1,
                                  rate=self.sample_rate,
                                  output=True,
                                  frames_per_buffer=1024) # BUFFER_SIZEは適宜調整

        def _load_character_data(self):
        # ... 
        return {
            # アオイは「ノコギリ波」を使う
            "char_001": CharacterInfo("char_001", "アオイ", "元気な女性ボーカル", waveform_type="sawtooth"),
            # ミライは「矩形波」を使う
            "char_002": CharacterInfo("char_002", "ミライ", "落ち着いた男性ボーカル", waveform_type="square"),
        }


    def set_active_character(self, char_id: str):
        if char_id in self.characters:
            self.active_character_id = char_id
            print(f"アクティブキャラクターを {self.characters[char_id].name} に設定しました。")
        else:
            print(f"エラー: キャラクターID {char_id} が見つかりません。")

    def value_to_hz(self, note_number: int) -> float:
        """MIDIノート番号を周波数(Hz)に変換します。"""
        return 440.0 * (2.0 ** ((note_number - 69) / 12.0))

    def apply_pitch_bend(self, base_hz: float, pitch_value: int) -> float:
        """ピッチベンド値（-8192〜8191）を周波数に適用します。（±2半音の範囲で簡易実装）"""
        pitch_bend_cents = (pitch_value / 8192.0) * 200.0 # 2半音(200セント)の範囲
        return base_hz * (2.0 ** (pitch_bend_cents / 1200.0))

    def synthesize_track(self, notes: list[NoteEvent], pitch_events: list[PitchEvent], start_time: float, end_time: float):
        """
        楽譜データとピッチデータから音声波形を生成する（オフライン生成用）。
        """
        if not self.active_character_id:
            raise ValueError("アクティブキャラクターが設定されていません。")
            
        char_info = self.characters[self.active_character_id]
        print(f"'{char_info.name}' の設定で合成中...")
        
        duration = end_time - start_time
        num_samples = int(duration * self.sample_rate)
        audio_data = np.zeros(num_samples, dtype=np.float32)

        # ノートごとに波形を生成し、メインのオーディオトラックに加算する
        for note in notes:
            if note.start_time >= end_time or note.start_time + note.duration <= start_time:
                continue # 再生範囲外のノートはスキップ

            note_start_sample = int((note.start_time - start_time) * self.sample_rate)
            note_duration_samples = int(note.duration * self.sample_rate)
            
            # ノート単体のバッファを生成する（ここでピッチベンドを適用しながら生成する）
            note_buffer = self._generate_note_with_pitch_bend(note, pitch_events, duration_samples=note_duration_samples)
            
            # メインバッファの適切な位置に加算（ノートが重なってもミックスされる）
            end_index = min(note_start_sample + note_duration_samples, num_samples)
            if note_start_sample < end_index:
                audio_data[note_start_sample:end_index] += note_buffer[:end_index - note_start_sample]

        return audio_data

 


    def _generate_note_with_pitch_bend(self, note: NoteEvent, pitch_events: list[PitchEvent], duration_samples: int):
        """
        単一のノートに対して、ピッチベンドとキャラクターの波形タイプを適用した波形を生成するヘルパー関数。
        """
        
        waveform = np.zeros(duration_samples, dtype=np.float32)
        base_hz = self.value_to_hz(note.note_number)
        sorted_pitch_events = sorted(pitch_events, key=lambda p: p.time)
        
        # 現在アクティブなキャラクターの波形タイプを取得
        char_info = self.characters[self.active_character_id]
        waveform_type = char_info.waveform_type

        # 位相管理用の変数
        # 各サンプル生成時に位相を累積していくことで、周波数変化がスムーズになります
        phase = 0.0

        for i in range(duration_samples):
            current_time = note.start_time + (i / self.sample_rate)
            
            # 現在時刻におけるピッチベンド値を見つける
            current_pitch_value = 0 
            for p_event in sorted_pitch_events:
                if p_event.time <= current_time:
                    current_pitch_value = p_event.value
                else:
                    break

            # ピッチベンドを適用した現在の周波数を計算
            current_hz = self.apply_pitch_bend(base_hz, current_pitch_value)
            
            # --- ここで波形を生成（波形タイプを反映） ---
            
            # 位相の更新: phase += (2 * pi * frequency / sample_rate)
            phase += (2 * np.pi * current_hz / self.sample_rate)
            
            if waveform_type == "sine":
                waveform[i] = np.sin(phase)
            elif waveform_type == "square":
                waveform[i] = np.sign(np.sin(phase))
            elif waveform_type == "sawtooth":
                # 位相を0から1の範囲に正規化してノコギリ波の計算に使う
                normalized_phase = np.mod(phase / (2 * np.pi), 1.0)
                waveform[i] = 2 * (normalized_phase - 0.5)
            else:
                # デフォルトはサイン波
                waveform[i] = np.sin(phase)

        # エンベロープ適用（簡易的なフェードイン・アウト）
        fade_len = int(min(0.01, note.duration / 2.0) * self.sample_rate)
        envelope = np.ones(duration_samples)
        envelope[:fade_len] = np.linspace(0, 1, fade_len)
        envelope[-fade_len:] = np.linspace(1, 0, fade_len)
        
        # 最終的な音量調整（エンベロープ、マスター音量0.5、ベロシティ）
        return (waveform * envelope * 0.5 * (note.velocity / 127.0)).astype(np.float32)




    def generate_note_buffer(self, note_number: int, pitch_value: int, duration_seconds: float, time_offset: float):
        """リアルタイムバッファリング用の簡易生成関数（単一ノート）"""
        # synthesize_track のロジックを簡略化して流用
        base_hz = self.value_to_hz(note_number)
        current_hz = self.apply_pitch_bend(base_hz, pitch_value)
        num_samples = int(duration_seconds * self.sample_rate)
        t = np.arange(num_samples) / self.sample_rate
        waveform = np.sin(2 * np.pi * current_hz * t) * 0.5
        return waveform.astype(np.float32)


    def play_audio(self, audio_data: np.ndarray):
        """生成されたオーディオデータを再生するヘルパー関数（別スレッドから呼び出す）"""
        # stream = self.pyaudio_instance.open(...) # __init__で開いたものを使用する
        if self.stream.is_active():
            self.stream.write(audio_data.tobytes())
            # self.stream.stop_stream() # stop_streamは呼ばない (常時アクティブにしておく)

    def close(self):
        """終了処理"""
        if self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()
        self.pyaudio_instance.terminate()
