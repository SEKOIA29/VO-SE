# vo_se_engine.py

from typing import Self
import numpy as np
import pyaudio
import json
import os
import soundfile as sf 
from data_models import CharacterInfo, NoteEvent, PitchEvent # data_modelsから必要なクラスをインポート
from PySide6.QtCore import Slot

class VO_SE_Engine:
    def __init__(self, sample_rate=44100):
        Self.sample_rate = sample_rate
        # self._load_character_data() を呼び出してキャラクターデータをロードする
        Self.characters = Self._load_character_data() 
        Self.active_character_id = None
        Self.pyaudio_instance = pyaudio.PyAudio()
        Self.tempo = 120.0 
        Self.current_time_playback = 0.0 
        Self.notes_to_play = []        
        Self.pitch_data_to_play = []  
        Self.note_phases = {} 
        
        Self.audio_samples = {} #wavデータを保持する辞書
        Self._load_all_character_samples() #全音源を読み込むメソッドを呼び出す

        Self.stream = Self.pyaudio_instance.open(format=pyaudio.paFloat32,
                                  channels=1,
                                  rate=self.sample_rate,
                                  output=True,
                                  frames_per_buffer=1024,
                                  stream_callback=self._pyaudio_callback) 
        Self.stream.stop_stream()



        def _load_character_data(self):
        # engine_params に 'audio_dir' パスを追加
         self.characters = {
            "char_001": CharacterInfo("char_001", "アオイ", "元気な女性ボーカル",
                                      engine_params={"audio_dir": "./audio/aoi/"},
                                      waveform_type="sample_based"),
            "char_002": CharacterInfo("char_002", "ミライ", "落ち着いた男性ボーカル",
                                      engine_params={"audio_dir": "./audio/mirai/"},
                                      waveform_type="sample_based"),
        }
        self.active_character_id = None
        self.pyaudio_instance = pyaudio.PyAudio()
        self.tempo = 120.0
        self.current_time_playback = 0.0
        self.notes_to_play = []
        self.pitch_data_to_play = []
        self.note_phases = {}
        self.audio_samples = {}



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
                                       duration_samples: int # 生成すべき最終的なサンプル数
                                      ) -> np.ndarray:
        
        # 'sample_based' 以外の場合は、サイン波生成のフォールバックメソッドを呼び出す
         if self.characters[self.active_character_id].waveform_type != "sample_based":
            return self._generate_synth_note(note, pitch_events, duration_samples)

        audio_data = np.zeros(duration_samples, dtype=np.float32)
        char_id = self.active_character_id
        
        if not note.phonemes: return audio_data

        # 音素のタイミングを均等割り当てで計算
        samples_per_phoneme = duration_samples / len(note.phonemes)
        current_sample_pos = 0

        for i, phoneme in enumerate(note.phonemes):
            if phoneme not in self.audio_samples.get(char_id, {}):
                print(f"警告: 音素 '{phoneme}' の音源が見つかりません。")
                current_sample_pos += samples_per_phoneme
                continue
            
            sample_data = self.audio_samples[char_id][phoneme]
            target_length = int(samples_per_phoneme)
            
            # ★時間伸縮（リサンプリングによる単純な速度調整）
            processed_sample = np.interp(
                np.linspace(0, len(sample_data), target_length),
                np.arange(len(sample_data)),
                sample_data
            )
            
            # TODO: クロスフェードはまだ実装していませんが、境界のノイズ低減のために簡易的なものを適用
            if i > 0:
                fade_len = min(int(self.sample_rate * 0.005), len(processed_sample), len(audio_data) - int(current_sample_pos)) # 5msクロスフェード
                if fade_len > 0:
                    fade_out = np.linspace(1.0, 0.0, fade_len)
                    fade_in = np.linspace(0.0, 1.0, fade_len)
                    # 重ね合わせ部分の処理
                    overlap_pos = int(current_sample_pos - fade_len)
                    audio_data[overlap_pos:int(current_sample_pos)] = audio_data[overlap_pos:int(current_sample_pos)] * fade_out + processed_sample[:fade_len] * fade_in
                    processed_sample = processed_sample[fade_len:] # フェードイン部分は削除
                    current_sample_pos += fade_len

            # オーディオデータに結合
            end_pos = int(current_sample_pos + len(processed_sample))
            if end_pos > duration_samples:
                end_pos = duration_samples
                processed_sample = processed_sample[:end_pos - int(current_sample_pos)]
            
            if len(processed_sample) > 0:
                audio_data[int(current_sample_pos):end_pos] += processed_sample * (note.velocity / 127.0)

            current_sample_pos += len(processed_sample)
            
        # TODO: この段階ではピッチベンドは適用が難しい（合成後に全体のピッチを変えるか検討）

        return audio_data.astype(np.float32)




   
    def close(self):
        """終了処理"""
        if self.stream and self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()

    def start_playback_stream(self, notes, pitch_data, start_time):
        self.note_phases = {} 

        self.notes_to_play = notes
        self.pitch_data_to_play = pitch_data
        self.current_time_playback = start_time
        if not self.stream.is_active():
            self.stream.start_stream()

    def stop_playback_stream(self):
        if self.stream.is_active():
            self.stream.stop_stream()
            self.note_phases = {}


    def _pyaudio_callback(self, in_data, frame_count, time_info, status):
        """PyAudioによって別スレッドで呼び出され、次のオーディオバッファを生成する"""
        
        audio_data = np.zeros(frame_count, dtype=np.float32)
        
        start_time_chunk = self.current_time_playback
        end_time_chunk = start_time_chunk + (frame_count / self.sample_rate)

        for note in self.notes_to_play:
            # チャンクと重なる音符のみを処理
            if note.start_time + note.duration > start_time_chunk and note.start_time < end_time_chunk:
                
                # 音符の開始・終了時刻とチャンクの開始・終了時刻の重なり合う部分を計算
                gen_start_sec = max(start_time_chunk, note.start_time)
                gen_end_sec = min(end_time_chunk, note.start_time + note.duration)

                if gen_start_sec >= gen_end_sec:
                    continue
                
                # 修正したヘルパー関数を呼び出し、必要な時間範囲だけを生成させる
                note_buffer = self._generate_note_with_pitch_bend(
                    note, 
                    self.pitch_data_to_play, 
                    start_time_sec=gen_start_sec, # <-- ここを変更
                    end_time_sec=gen_end_sec      # <-- ここを変更
                )
                
                # 生成されたバッファを、チャンク内の正しい位置に加算する
                # チャンク先頭からの相対サンプル位置
                copy_start_in_chunk = int((gen_start_sec - start_time_chunk) * self.sample_rate)
                copy_end_in_chunk = copy_start_in_chunk + note_buffer.shape[0]

                if copy_start_in_chunk < frame_count and copy_end_in_chunk > 0:
                     # 範囲チェックを行いながら加算
                    valid_copy_end = min(frame_count, copy_end_in_chunk)
                    valid_src_end = valid_copy_end - copy_start_in_chunk

                    audio_data[copy_start_in_chunk:valid_copy_end] += note_buffer[:valid_src_end]
        
        # 再生時間を更新
        self.current_time_playback = end_time_chunk

        return audio_data.tobytes(), pyaudio.paContinue




    def _load_all_character_samples(self):
        """全てのキャラクターの音源サンプルを読み込み、メモリにキャッシュする"""
        for char_id, char_info in self.characters.items():
            audio_dir = char_info.engine_params.get("audio_dir")
            if audio_dir and os.path.isdir(audio_dir):
                self.audio_samples[char_id] = {}
                for filename in os.listdir(audio_dir):
                    if filename.endswith(".wav"):
                        phoneme_name = filename[:-4] # ファイル名から拡張子を削除
                        filepath = os.path.join(audio_dir, filename)
                        try:
                            data, sr = sf.read(filepath)
                            if data.ndim > 1: data = data.mean(axis=1)
                            # サンプリングレートの不一致を警告
                            if sr != self.sample_rate:
                                print(f"警告: {filename} のSRが一致しません ({sr}Hz != {self.sample_rate}Hz)")
                            self.audio_samples[char_id][phoneme_name] = data
                        except Exception as e:
                            print(f"音源読み込みエラー {filepath}: {e}")
            print(f"'{char_info.name}' の音源を {len(self.audio_samples.get(char_id, {}))} 件読み込みました。")



    def _generate_synth_note(self, note: NoteEvent, pitch_events: list[PitchEvent], duration_samples: int) -> np.ndarray:
          """
          サイン波/矩形波による単音生成ヘルパー関数（フォールバック用）
         """
        
          waveform = np.zeros(duration_samples, dtype=np.float32)
          base_hz = self.value_to_hz(note.note_number)
          sorted_pitch_events = sorted(pitch_events, key=lambda p: p.time)
        
          char_info = self.characters[self.active_character_id]
          # waveform_type はこのメソッド内では 'sine', 'square', 'sawtooth' のいずれかを想定
          waveform_type = char_info.waveform_type 

          phase = 0.0

          for i in range(duration_samples):
            current_time = note.start_time + (i / self.sample_rate)
            
            current_pitch_value = 0 
            for p_event in sorted_pitch_events:
                if p_event.time <= current_time:
                    current_pitch_value = p_event.value
                else:
                    break

            current_hz = self.apply_pitch_bend(base_hz, current_pitch_value)
            
            # 位相の更新: phase += (2 * pi * frequency / sample_rate)
            phase += (2 * np.pi * current_hz / self.sample_rate)
            
            if waveform_type == "sine":
                waveform[i] = np.sin(phase)
            elif waveform_type == "square":
                waveform[i] = np.sign(np.sin(phase))
            elif waveform_type == "sawtooth":
                normalized_phase = np.mod(phase / (2 * np.pi), 1.0)
                waveform[i] = 2 * (normalized_phase - 0.5)
            else:
                # デフォルトまたは未知の波形タイプの場合はサイン波を使用
                waveform[i] = np.sin(phase)

             # エンベロープ適用（簡易的なフェードイン・アウト）
            fade_len = int(min(0.01, note.duration / 2.0) * self.sample_rate)
            envelope = np.ones(duration_samples)
            if fade_len > 0:
                 envelope[:fade_len] = np.linspace(0, 1, fade_len)
                 envelope[-fade_len:] = np.linspace(1, 0, fade_len)
        
    return (waveform * envelope * 0.5 * (note.velocity / 127.0)).astype(np.float32)
# ...existing code...
        # エンベロープ適用（簡易的なフェードイン・アウト）
    fade_len = int(min(0.01, note.duration / 2.0) * self.sample_rate)
    envelope = np.ones(duration_samples)
    if fade_len > 0:
            envelope[:fade_len] = np.linspace(0, 1, fade_len)
            envelope[-fade_len:] = np.linspace(1, 0, fade_len)

    return (waveform * envelope * 0.5 * (note.velocity / 127.0)).astype(np.float32)
# ...existing code...
# ...existing code...
        # エンベロープ適用（簡易的なフェードイン・アウト）
    fade_len = int(min(0.01, note.duration / 2.0) * self.sample_rate)
    envelope = np.ones(duration_samples)
    if fade_len > 0:
            envelope[:fade_len] = np.linspace(0, 1, fade_len)
            envelope[-fade_len:] = np.linspace(1, 0, fade_len)

    return (waveform * envelope * 0.5 * (note.velocity / 127.0)).astype(np.float32)
# ...existing code...
