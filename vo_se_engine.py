# vo_se_engine.py

import numpy as np
import pyaudio
import json
import os
from data_models import CharacterInfo, NoteEvent, PitchEvent # data_modelsから必要なクラスをインポート

class VO_SE_Engine:
        def __init__(self, sample_rate=44100):
        # ... (中略) ...
        self.pyaudio_instance = pyaudio.PyAudio()
        self.tempo = 120.0 
        self.current_time_playback = 0.0 
        self.notes_to_play = []        
        self.pitch_data_to_play = []   

        self.stream = self.pyaudio_instance.open(format=pyaudio.paFloat32,
                                  channels=1,
                                  rate=self.sample_rate,
                                  output=True,
                                  frames_per_buffer=1024,
                                  stream_callback=self._pyaudio_callback) 
        self.stream.stop_stream()



    def _load_character_data(self):
        """キャラクターデータをハードコード（またはファイルから読み込む）ヘルパーメソッド"""
        # 実際にはJSONファイルから読み込むことを想定しているかもしれませんが、ここではハードコード
        return {
            "char_001": CharacterInfo("char_001", "アオイ", "元気な女性ボーカル", waveform_type="sawtooth"),
            "char_002": CharacterInfo("char_002", "ミライ", "落ち着いた男性ボーカル", waveform_type="square"),
        }

    @Slot(float)
    def set_tempo(self, bpm: float):
        """メインウィンドウからテンポ更新を受け取る"""
        self.tempo = bpm

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

    def synthesize_track(self, notes: list[NoteEvent], pitch_events: list[PitchEvent], start_time: float, end_time: float) -> np.ndarray:
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

        for note in notes:
            if note.start_time >= end_time or note.start_time + note.duration <= start_time:
                continue

            note_start_sample = int((note.start_time - start_time) * self.sample_rate)
            note_duration_samples = int(note.duration * self.sample_rate)
            
            note_buffer = self._generate_note_with_pitch_bend(note, pitch_events, duration_samples=note_duration_samples)
            
            end_index = min(note_start_sample + note_duration_samples, num_samples)
            if note_start_sample < end_index:
                # バッファの長さを合わせる必要がある
                src_end_index = min(note_buffer.shape[0], end_index - note_start_sample)
                audio_data[note_start_sample:end_index] += note_buffer[:src_end_index]

        return audio_data
            

       def _generate_note_with_pitch_bend(self, 
                                       note: NoteEvent, 
                                       pitch_events: list[PitchEvent], 
                                       # duration_samples: int # <-- この引数を削除
                                       start_time_sec: float, # <-- 開始時刻を追加
                                       end_time_sec: float    # <-- 終了時刻を追加
                                      ) -> np.ndarray:
        """
        単一のノートに対して、指定された時間範囲のピッチベンドとキャラクターの波形タイプを適用した波形を生成するヘルパー関数。
        """
        
        # 指定範囲のサンプル数を計算
        duration_samples = int((end_time_sec - start_time_sec) * self.sample_rate)
        if duration_samples <= 0:
            return np.zeros(0, dtype=np.float32)

        waveform = np.zeros(duration_samples, dtype=np.float32)
        base_hz = self.value_to_hz(note.note_number)
        sorted_pitch_events = sorted(pitch_events, key=lambda p: p.time)
        
        char_info = self.characters[self.active_character_id]
        waveform_type = char_info.waveform_type

     
        phase = 0.0 

        for i in range(duration_samples):
            # i はチャンク内でのサンプルオフセット
            # current_time は絶対時間
            current_time = start_time_sec + (i / self.sample_rate)
            
            # --- ノートのエンベロープ（音量）計算 ---
            # ノート全体の開始・終了に対する現在の位置に基づいて音量を調整する
            note_pos = current_time - note.start_time
            note_dur = note.duration
            envelope_value = 1.0
            fade_len_sec = 0.01
            
            if note_pos < fade_len_sec:
                envelope_value = note_pos / fade_len_sec
            elif note_pos > note_dur - fade_len_sec:
                envelope_value = (note_dur - note_pos) / fade_len_sec
            
            if envelope_value < 0: envelope_value = 0 # 念のため

            # --- ピッチベンド値の計算 ---
            current_pitch_value = 0 
            for p_event in sorted_pitch_events:
                if p_event.time <= current_time:
                    current_pitch_value = p_event.value
                else:
                    break

            current_hz = self.apply_pitch_bend(base_hz, current_pitch_value)
            ）
                
            phase += (2 * np.pi * current_hz / self.sample_rate)
            
            if waveform_type == "sine":
                sample_value = np.sin(phase)
            elif waveform_type == "square":
                sample_value = np.sign(np.sin(phase))
            elif waveform_type == "sawtooth":
                normalized_phase = np.mod(phase / (2 * np.pi), 1.0)
                sample_value = 2 * (normalized_phase - 0.5)
            else:
                sample_value = np.sin(phase)

            # 音量とベロシティを適用して波形に格納
            waveform[i] = sample_value * envelope_value * 0.5 * (note.velocity / 127.0)

   
        return waveform.astype(np.float32)



   
    def close(self):
        """終了処理"""
        if self.stream and self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()

    def start_playback_stream(self, notes, pitch_data, start_time):
        self.notes_to_play = notes
        self.pitch_data_to_play = pitch_data
        self.current_time_playback = start_time
        if not self.stream.is_active():
            self.stream.start_stream()

    def stop_playback_stream(self):
        if self.stream.is_active():
            self.stream.stop_stream()



    def _pyaudio_callback(self, in_data, frame_count, time_info, status):
        """PyAudioによって別スレッドで呼び出され、次のオーディオバッファを生成する"""
        
        # frame_count: 次に生成すべきサンプル数
        audio_data = np.zeros(frame_count, dtype=np.float32)
        
        # 現在の時刻範囲を計算
        start_time_chunk = self.current_time_playback
        end_time_chunk = start_time_chunk + (frame_count / self.sample_rate)

        for note in self.notes_to_play:
            # チャンクと重なる音符のみを処理
            if note.start_time + note.duration > start_time_chunk and note.start_time < end_time_chunk:
                # この音符がチャンク内で始まる相対時間を計算
                note_start_in_chunk = max(0, int((note.start_time - start_time_chunk) * self.sample_rate))
                
                # 音符の合成（既存のヘルパー関数を再利用）
                # ここでは音符全体ではなく、必要なチャンク部分だけを生成するように _generate_note_with_pitch_bend を調整するか、工夫が必要
                
                # 簡易的な実装として、音符全体を生成して切り貼りする方法:
                note_buffer = self._generate_note_with_pitch_bend(note, self.pitch_data_to_play, 
                                                                    duration_samples=int(note.duration * self.sample_rate))
                
                # チャンクへのコピー範囲を計算
                copy_start = note_start_in_chunk
                copy_end = min(frame_count, note_start_in_chunk + note_buffer.shape[0])
                src_start = 0
                src_end = copy_end - copy_start

                if copy_start < copy_end:
                    audio_data[copy_start:copy_end] += note_buffer[src_start:src_end]
        
        # 再生時間を更新
        self.current_time_playback = end_time_chunk

        # PyAudioにデータを返す
        return audio_data.tobytes(), pyaudio.paContinue


