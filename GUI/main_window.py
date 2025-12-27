# main_window.py ファイル全体のインポートリスト（参考用）
import sys
import time
import json
from janome.tokenizer import Tokenizer
import mido 

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QMenu, QVBoxLayout, 
                               QPushButton, QFileDialog, QScrollBar, QInputDialog, 
                               QLineEdit, QHBoxLayout, QLabel, QSplitter, QComboBox)
from PySide6.QtGui import QAction, QKeySequence, QKeyEvent
from PySide6.QtCore import Slot, Qt, QTimer, Signal

from GUI.vo_se_engine import VO_SE_Engine

import numpy as np 

from .timeline_widget import TimelineWidget
from .keyboard_sidebar_widget import KeyboardSidebarWidget
from .midi_manager import load_midi_file, MidiInputManager, midi_signals
from .data_models import NoteEvent, PitchEvent
from .graph_editor_widget import GraphEditorWidget


class MainWindow(QMainWindow):
    """
    アプリケーションのメインウィンドウクラス。
    UIの構築、イベント接続、全体的なアプリケーションロジックを管理する。
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VO-SE Pro")
        self.setGeometry(100, 100, 700, 400)
        
        self.vo_se_engine = VO_SE_Engine()
        self.pitch_data = [] # self.pitch_data をここで初期化

        # --- UIコンポーネントの初期化 ---
        self.status_label = QLabel("起動中... =」", self) # ステータスバーとして最下部に配置
        
        # ★GUI改修案1: 再生時間表示ラベルを追加
        self.time_display_label = QLabel("00:00.00", self) 
        self.time_display_label.setFixedWidth(100)
        self.time_display_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #00ff00;")

        self.timeline_widget = TimelineWidget()
        self.keyboard_sidebar = KeyboardSidebarWidget(
            self.timeline_widget.key_height_pixels,
            self.timeline_widget.lowest_note_display
        )
        self.graph_editor_widget = GraphEditorWidget()
        
        self.play_button = QPushButton("再生/停止", self)
        self.record_button = QPushButton("録音 開始/停止", self)
        self.open_button = QPushButton("MIDIファイルを開く", self)
        self.loop_button = QPushButton("ループ再生: OFF", self)
        
        # ★GUI改修案1: テンポラベルをシンプルに
        self.tempo_label = QLabel("BPM:", self) 
        self.tempo_input = QLineEdit(str(self.timeline_widget.tempo), self)
        self.tempo_input.setFixedWidth(50)
        self.tempo_input.returnPressed.connect(self.update_tempo_from_input) 
      
        self.h_scrollbar = QScrollBar(Qt.Horizontal)
        self.h_scrollbar.setRange(0, 0)
        self.v_scrollbar = QScrollBar(Qt.Vertical)
        self.v_scrollbar.setRange(0, 500)

        # --- 再生・録音制御のための変数とタイマー ---
        self.is_recording = False
        self.is_playing = False
        self.is_looping = False
        self.is_looping_selection = False
        self.current_playback_time = 0.0
        self.start_time_real = 0.0
        self.playing_notes = {}

        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.update_playback_cursor)
        self.playback_timer.setInterval(10)

        # --- レイアウト構築 ---
        timeline_area_layout = QHBoxLayout()
        timeline_area_layout.addWidget(self.keyboard_sidebar)
        timeline_area_layout.addWidget(self.timeline_widget)
        timeline_area_layout.addWidget(self.v_scrollbar)
        timeline_area_layout.setSpacing(0)
        timeline_area_layout.setContentsMargins(0, 0, 0, 0)

        timeline_container = QWidget()
        timeline_container.setLayout(timeline_area_layout)
        
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.addWidget(timeline_container)
        self.main_splitter.addWidget(self.graph_editor_widget)
        self.main_splitter.setSizes([self.height() * 0.7, self.height() * 0.3])
        

        # ボタンを横並びに配置するコード
        button_layout = QHBoxLayout()
        # ★GUI改修案1: 再生時間表示をボタンの左隣に配置
        button_layout.addWidget(self.time_display_label) 
        
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.record_button)
        button_layout.addWidget(self.loop_button)

        # キャラクター選択UIの追加
        self.character_selector = QComboBox(self)
        for char_id, char_info in self.vo_se_engine.characters.items(): 
            self.character_selector.addItem(char_info.name, userData=char_id)
        self.character_selector.currentIndexChanged.connect(self.on_character_changed)
        button_layout.addWidget(self.character_selector) 

       #  MIDIポート選択UIの追加
        self.midi_port_selector = QComboBox(self)
        self.midi_port_selector.currentIndexChanged.connect(self.on_midi_port_changed)
        button_layout.addWidget(self.midi_port_selector)

        #テンポ表示
        button_layout.addWidget(self.tempo_label)
        button_layout.addWidget(self.tempo_input)
        button_layout.addWidget(self.open_button)

        # メインレイアウトの構築
        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout) # ボタンレイアウトを上部に配置
        main_layout.addWidget(self.main_splitter)
        main_layout.addWidget(self.h_scrollbar)
        main_layout.addWidget(self.status_label) # ステータスバーは最下部のまま

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
        self.vo_se_engine.set_active_character("char_001")


        # --- アクション、メニュー、シグナルの接続 ---
        self.setup_actions()
        self.setup_menus()
        self.addAction(self.copy_action)
        self.addAction(self.paste_action)
        self.addAction(self.save_action)

        self.play_button.clicked.connect(self.on_play_pause_toggled)
        self.record_button.clicked.connect(self.on_record_toggled)
        self.open_button.clicked.connect(self.open_file_dialog_and_load_midi)
        self.loop_button.clicked.connect(self.on_loop_button_toggled)
        midi_signals.midi_event_signal.connect(self.update_gui_with_midi)
        midi_signals.midi_event_signal.connect(self.timeline_widget.highlight_note)
        midi_signals.midi_event_record_signal.connect(self.timeline_widget.record_midi_event)
        
        self.h_scrollbar.valueChanged.connect(self.timeline_widget.set_scroll_x_offset)
        self.v_scrollbar.valueChanged.connect(self.timeline_widget.set_scroll_y_offset)
        self.v_scrollbar.valueChanged.connect(self.keyboard_sidebar.set_scroll_y_offset)
        
        self.h_scrollbar.valueChanged.connect(self.graph_editor_widget.set_scroll_x_offset)
        self.timeline_widget.zoom_changed_signal.connect(self.graph_editor_widget.set_pixels_per_beat)
        
        self.timeline_widget.zoom_changed_signal.connect(self.update_scrollbar_range)
        self.timeline_widget.vertical_zoom_changed_signal.connect(self.update_scrollbar_v_range)
        self.timeline_widget.notes_changed_signal.connect(self.update_scrollbar_range)
        
        self.graph_editor_widget.pitch_data_changed.connect(self.on_pitch_data_updated)


        # --- MIDI入力マネージャーの起動 (MIDI接続)---
        available_ports = MidiInputManager.get_available_ports()
        if available_ports:
            # コンボボックスにポート名を追加
            for port_name in available_ports:
                self.midi_port_selector.addItem(port_name, userData=port_name)
            
            # 最初のポートをデフォルトで選択し、接続を開始する
            # on_midi_port_changed スロットが自動的に呼び出される
            # self.midi_port_selector.setCurrentIndex(0) 

        else:
            # ポートが見つからない場合の処理
            print("利用可能なMIDIポートが見つかりませんでした。")
            self.status_label.setText("警告: MIDIポートが見つかりません。")
            self.midi_port_selector.addItem("ポートなし")
            self.midi_port_selector.setEnabled(False)
            self.midi_manager = None
        
        self.timeline_widget.set_current_time(self.current_playback_time)

  


    # --- アクションとメニューの設定メソッド ---
    def setup_actions(self):
        self.copy_action = QAction("コピー", self)
        self.copy_action.setShortcuts(QKeySequence.StandardKey.Copy)
        self.copy_action.triggered.connect(self.timeline_widget.copy_selected_notes_to_clipboard)
        self.paste_action = QAction("ペースト", self)
        self.paste_action.setShortcuts(QKeySequence.StandardKey.Paste)
        self.paste_action.triggered.connect(self.timeline_widget.paste_notes_from_clipboard)
        self.save_action = QAction("プロジェクトを保存(&S)", self)
        self.save_action.setShortcuts(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.save_file_dialog_and_save_midi)

    def setup_menus(self):
        file_menu = self.menuBar().addMenu("ファイル(&F)")
        file_menu.addAction(self.save_action)
        
        export_action = QAction("MIDIファイルとしてエクスポート...", self)
        export_action.triggered.connect(self.export_to_midi_file)
        file_menu.addAction(export_action)

        edit_menu = self.menuBar().addMenu("編集(&E)")
        edit_menu.addAction(self.copy_action)
        edit_menu.addAction(self.paste_action)

    @Slot()
    def on_play_pause_toggled(self):
        """再生/停止ボタンのハンドラ"""
        
        if self.is_playing:
            self.is_playing = False
            self.playback_timer.stop()
            
            # TODO: VO-SE Engineで再生中の音声があれば停止させる仕組みが必要
            # 前回のバージョンの停止ロジックを統合
            if self.vo_se_engine and hasattr(self.vo_se_engine, 'stream') and self.vo_se_engine.stream.is_active():
                 self.vo_se_engine.stream.stop_stream()
            
            self.play_button.setText("再生/停止")
            self.status_label.setText("再生停止しました。")
            self.playing_notes = {}
            

        else:
            if self.is_recording:
                self.on_record_toggled()
            
            # get_selected_notes_range は選択範囲がない場合、プロジェクト全体を返すためそのまま使える
            start_time, end_time = self.timeline_widget.get_selected_notes_range()

            if start_time >= end_time:
                 self.status_label.setText("ノートが存在しないため再生できません。")
                 return

            notes = self.timeline_widget.notes_list
            pitch = self.pitch_data
            
            try:
                self.status_label.setText("音声生成中...お待ちください。")
                QApplication.processEvents()

                audio_track = self.vo_se_engine.synthesize_track(notes, pitch, start_time, end_time)
                
                # エンジンのストリームが停止中であれば再開する (前回のバージョンのロジック)
                if hasattr(self.vo_se_engine, 'stream') and not self.vo_se_engine.stream.is_active():
                    self.vo_se_engine.stream.start_stream()

                self.current_playback_time = start_time
                self.start_time_real = time.time() - self.current_playback_time
                
                self.is_playing = True
                self.playback_timer.start()
                
                import threading
                playback_thread = threading.Thread(target=self.vo_se_engine.play_audio, args=(audio_track,))
                playback_thread.daemon = True
                playback_thread.start()
                
                self.play_button.setText("■ 再生中 (停止)")
                self.status_label.setText(f"再生開始しました (範囲: {start_time:.2f}s - {end_time:.2f}s)。")

            except Exception as e: # ValueErrorだけでなく一般的なエラーもキャッチ
                 self.status_label.setText(f"再生エラーが発生しました: {e}")
                 print(f"再生エラーの詳細: {e}")
                
    @Slot()
    def on_loop_button_toggled(self):
        """ループ再生ボタンのハンドラ"""
        self.is_looping_selection = not self.is_looping_selection

        if self.is_looping_selection:
            self.loop_button.setText("選択範囲ループ: ON")
            self.status_label.setText("選択範囲でのループ再生を有効にしました。")
            self.is_looping = True
        else:
            self.loop_button.setText("ループ再生: OFF")
            self.status_label.setText("ループ再生を無効にしました。")
            self.is_looping = False

    @Slot()
    def on_record_toggled(self):
        """録音 開始/停止ボタンのハンドラ"""
        if self.is_recording:
            self.is_recording = False
            self.record_button.setText("録音 開始/停止")
            self.status_label.setText("録音停止しました。")
            self.timeline_widget.set_recording_state(False, 0.0)
        else:
            if self.is_playing:
                self.on_play_pause_toggled()

            import time
            self.is_recording = True
            self.record_button.setText("■ 録音中 (停止)")
            self.status_label.setText("録音開始しました。MIDI入力を待っています...")
            self.timeline_widget.set_recording_state(True, time.time())

    @Slot()
    def on_character_changed(self):
        char_id = self.character_selector.currentData()
        self.vo_se_engine.set_active_character(char_id)


    
    @Slot()
    def update_playback_cursor(self):
        """タイマーイベントごとに呼び出され、再生カーソル位置とGUIを同期更新する"""
        if self.is_playing:
            # --- 再生時刻の同期 ---
            # システム時刻から計算するのではなく、VO_SE_Engineの現在時刻を取得する
            self.current_playback_time = self.vo_se_engine.current_time_playback 
           
            # 再生時間を MM:SS.ms 形式にフォーマット
            mins = int(self.current_playback_time / 60)
            secs = int(self.current_playback_time % 60)
            msecs = int((self.current_playback_time - int(self.current_playback_time)) * 100)
            time_str = f"{mins:02}:{secs:02}.{msecs:02}"
            self.time_display_label.setText(time_str)
          
            
            # --- ループ処理のロジック ---
            # ここではGUI側でループ範囲監視と巻き戻しを行う
            if self.is_looping:
                project_start_time, project_end_time = self.timeline_widget.get_selected_notes_range()
                
                # 再生時間が終了範囲を超えたら、開始時間まで巻き戻す
                if self.current_playback_time >= project_end_time and project_end_time > project_start_time:
                    self.current_playback_time = project_start_time
                    # VO_SE_Engineの内部時刻も巻き戻す必要がある
                    self.vo_se_engine.current_time_playback = self.current_playback_time 
                
                # 再生時間が開始範囲より前なら、開始時間まで進める (通常は発生しない想定だが安全策)
                if self.current_playback_time < project_start_time:
                    self.current_playback_time = project_start_time
                    # VO_SE_Engineの内部時刻も巻き戻す必要がある
                    self.vo_se_engine.current_time_playback = self.current_playback_time 

            # --- GUIの更新と自動スクロール ---
            self.timeline_widget.set_current_time(self.current_playback_time)
            self.graph_editor_widget.set_current_time(self.current_playback_time)

            # 自動スクロールのロジック
            current_beats = self.timeline_widget.seconds_to_beats(self.current_playback_time)
            cursor_x_pos = current_beats * self.timeline_widget.pixels_per_beat
            viewport_width = self.timeline_widget.width()
            
            # カーソルがビューポートの中心に来るようにスクロール位置を計算
            target_scroll_x = cursor_x_pos - (viewport_width / 2)
            
            # スクロールバーの有効範囲に収める
            max_scroll_value = self.h_scrollbar.maximum()
            min_scroll_value = self.h_scrollbar.minimum()
            clamped_scroll_x = max(min_scroll_value, min(max_scroll_value, target_scroll_x))
            
            # スクロールバーの値を設定（GUIが自動的にスクロールする）
            self.h_scrollbar.setValue(int(clamped_scroll_x))


    @Slot()
    def update_scrollbar_range(self):
        """ズーム変更時やノートリスト変更時などに水平スクロールバーの範囲を動的に更新する"""
        if not self.timeline_widget.notes_list:
            self.h_scrollbar.setRange(0, 0)
            return
        
        max_beats = self.timeline_widget.get_max_beat_position()
        max_x_position = max_beats * self.timeline_widget.pixels_per_beat
        viewport_width = self.timeline_widget.width()
        max_scroll_value = max(0, int(max_x_position - viewport_width))
        
        self.h_scrollbar.setRange(0, max_scroll_value)


    @Slot()
    def update_scrollbar_v_range(self):
        """垂直スクロールバーの範囲とサイドバーの高さを更新する"""
        key_h = self.timeline_widget.key_height_pixels
        full_height = 128 * key_h
        viewport_height = self.timeline_widget.height()

        max_scroll_value = max(0, int(full_height - viewport_height + key_h))
        self.v_scrollbar.setRange(0, max_scroll_value)

        self.keyboard_sidebar.set_key_height_pixels(key_h)


    @Slot()
    def save_file_dialog_and_save_midi(self):
        """ファイルダイアログを開き、現在のノートデータとピッチデータをJSONファイルとして保存する。"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "プロジェクトを保存", "", "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            notes_data = [note.to_dict() for note in self.timeline_widget.notes_list]
            pitch_data = [p_event.to_dict() for p_event in self.pitch_data] 
            
            save_data_structure = {
                "app_id": "Vocaloid_Clone_App_12345",
                "type": "note_project_data",
                "tempo_bpm": self.timeline_widget.tempo,
                "notes": notes_data,
                "pitch_data": pitch_data
            }
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(save_data_structure, f, indent=2, ensure_ascii=False)
                self.status_label.setText(f"プロジェクトを保存しました: {filepath}")
            except Exception as e:
                self.status_label.setText(f"保存エラー: {e}")

    @Slot()
    def export_to_midi_file(self):
        """現在のノートデータを標準MIDIファイル形式でエクスポートする。（歌詞は自動分割）"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "MIDIファイルとしてエクスポート (歌詞付き)", "", "MIDI Files (*.mid *.midi)"
        )
        if filepath:
            mid = mido.MidiFile()
            track = mido.MidiTrack()
            mid.tracks.append(track)
            mid.ticks_per_beat = 480

            midi_tempo = mido.bpm2tempo(self.timeline_widget.tempo)
            track.append(mido.MetaMessage('set_tempo', tempo=midi_tempo, time=0))
            track.append(mido.MetaMessage('track_name', name='Vocal Track 1', time=0))

            sorted_notes = sorted(self.timeline_widget.notes_list, key=lambda note: note.start_time)
            tokenizer = Tokenizer() 
            current_tick = 0

            for note in sorted_notes:
                tokens = [token.surface for token in tokenizer.tokenize(note.lyrics, wakati=True)]
                note_start_beats = self.timeline_widget.seconds_to_beats(note.start_time)
                note_duration_beats = self.timeline_widget.seconds_to_beats(note.duration)
                
                if note.lyrics and tokens:
                    beats_per_syllable = note_duration_beats / len(tokens)
                    ticks_per_syllable = int(beats_per_syllable * mid.ticks_per_beat)

                    delta_time_on = int(note_start_beats * mid.ticks_per_beat) - current_tick
                    track.append(mido.Message('note_on', note=note.note_number, velocity=note.velocity, time=delta_time_on))
                    current_tick += delta_time_on

                    for i, syllable in enumerate(tokens):
                        lyric_delta_time = ticks_per_syllable if i > 0 else 0
                        track.append(mido.MetaMessage('lyric', text=syllable, time=lyric_delta_time))
                        current_tick += lyric_delta_time

                    total_syllable_ticks = len(tokens) * ticks_per_syllable
                    note_off_delta_time = int(note_duration_beats * mid.ticks_per_beat) - total_syllable_ticks
                    if note_off_delta_time < 0: note_off_delta_time = 0

                    track.append(mido.Message('note_off', note=note.note_number, velocity=note.velocity, time=note_off_delta_time))
                    current_tick += note_off_delta_time
                else:
                    delta_time_on = int(note_start_beats * mid.ticks_per_beat) - current_tick
                    track.append(mido.Message('note_on', note=note.note_number, velocity=note.velocity, time=delta_time_on))
                    current_tick += delta_time_on
                    delta_time_off = int(note_duration_beats * mid.ticks_per_beat)
                    track.append(mido.Message('note_off', note=note.note_number, velocity=note.velocity, time=delta_time_off))
                    current_tick += delta_time_off

            track.append(mido.MetaMessage('end_of_track', time=0))
            
            try:
                mid.save(filepath)
                self.status_label.setText(f"MIDIファイル（歌詞付き）のエクスポート完了: {filepath}")
            except Exception as e:
                self.status_label.setText(f"MIDIファイル保存エラー: {e}")

    @Slot()
    def open_file_dialog_and_load_midi(self):
        """ファイルダイアログを開き、MIDIファイルまたはJSONプロジェクトファイルを読み込む。"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "ファイルを開く", "",
            "Project Files (*.json);;MIDI Files (*.mid *.midi);;All Files (*)"
        )
        if filepath:
            notes_list = []
            loaded_pitch_data = []
            loaded_tempo = None

            # --- JSONプロジェクトファイルの読み込み処理 ---
            if filepath.lower().endswith('.json'):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get("app_id") == "Vocaloid_Clone_App_12345":
                            notes_data = data.get("notes", [])
                            notes_list = [NoteEvent.from_dict(d) for d in notes_data]
                            pitch_data_dicts = data.get("pitch_data", [])
                            loaded_pitch_data = [PitchEvent.from_dict(d) for d in pitch_data_dicts] 
                            loaded_tempo = data.get("tempo_bpm", None)

                            self.status_label.setText(f"プロジェクトファイルの読み込み完了。ノート数: {len(notes_list)}, ピッチポイント数: {len(loaded_pitch_data)}")
                        else:
                            self.status_label.setText("エラー: サポートされていないプロジェクト形式です。")
                except Exception as e:
                    self.status_label.setText(f"JSONファイルの読み込みエラー: {e}")
                    return

            # --- 標準MIDIファイルの読み込み処理 ---
            elif filepath.lower().endswith(('.mid', '.midi')):
                try:
                    # MIDIファイルからテンポ情報を取得
                    mid = mido.MidiFile(filepath)
                    for track in mid.tracks:
                        for msg in track:
                            if msg.type == 'set_tempo':
                                loaded_tempo = mido.tempo2bpm(msg.tempo)
                                break
                        if loaded_tempo: break
                    
                    # MIDIファイルからノートデータを取得 (midi_managerのヘルパー関数を使用)
                    data_dicts = load_midi_file(filepath)
                    # ★注: load_midi_fileはdictを返すため、NoteEventオブジェクトに変換し直す
                    if data_dicts:
                        notes_list = [NoteEvent.from_dict(d) for d in data_dicts]
                      
                        for note in notes_list:
                            if note.lyrics and not note.phonemes: # 歌詞はあるが音素がない場合
                                note.phonemes = self._get_yomi_from_lyrics(note.lyrics)
                          
                        self.status_label.setText(f"MIDIファイルの読み込み完了。イベント数: {len(notes_list)}")
                except Exception as e:
                     self.status_label.setText(f"MIDIファイルの読み込みエラー: {e}")

            # --- 読み込んだデータをUIとエンジンに反映させる ---
            if notes_list or loaded_pitch_data:
                # 既存のデータをクリアし、新しいデータをセット
                self.timeline_widget.set_notes(notes_list)
                self.pitch_data = loaded_pitch_data
                self.graph_editor_widget.set_pitch_events(self.pitch_data)

                # テンポ情報があれば反映
                if loaded_tempo is not None:
                    try:
                        new_tempo = float(loaded_tempo)
                        self.tempo_input.setText(str(new_tempo))
                        # update_tempo_from_inputを呼び出して全ウィジェットに反映
                        self.update_tempo_from_input() 
                    except ValueError:
                        self.status_label.setText("警告: テンポ情報が無効なため、デフォルトテンポを使用します。")

                # スクロールバーの範囲を更新
                self.update_scrollbar_range()
                self.update_scrollbar_v_range()

    @Slot(list)
    def on_pitch_data_updated(self, new_pitch_events: list):
        """GraphEditorWidgetから更新されたピッチデータを受け取る"""
        # PitchEvent型への型ヒントを追加
        self.pitch_data: list[PitchEvent] = new_pitch_events
        print(f"ピッチデータが更新されました。総ポイント数: {len(self.pitch_data)}")


    @Slot()
    def update_tempo_from_input(self):
        """テンポ入力欄から値を取得し、タイムラインウィジェットなどに反映させる"""
        try:
            new_tempo = float(self.tempo_input.text())
            if 30.0 <= new_tempo <= 300.0:
                self.timeline_widget.tempo = new_tempo
                self.vo_se_engine.set_tempo(new_tempo)
                
                # ★修正箇所: GraphEditorWidgetにもテンポを通知する
                self.graph_editor_widget.tempo = new_tempo # コメントアウトを外す

                self.update_scrollbar_range()
                self.status_label.setText(f"テンポを {new_tempo} BPM に更新しました。")
            else:
                raise ValueError("テンポは30から300の範囲で入力してください。")
        except ValueError as e:
            self.status_label.setText(f"エラー: {e}")
            self.tempo_input.setText(str(self.timeline_widget.tempo))


    def keyPressEvent(self, event: QKeyEvent):
        """
        キーボードショートカットのイベントハンドラ。
        スペースキーで再生/停止を切り替える。
        """
        if event.key() == Qt.Key_Space:
            self.on_play_pause_toggled()
            event.accept()
        
        elif event.key() == Qt.Key_R and event.modifiers() == Qt.ControlModifier:
            self.on_record_toggled()
            event.accept()

        elif event.key() == Qt.Key_L and event.modifiers() == Qt.ControlModifier:
            self.on_loop_button_toggled()
            event.accept()

        elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            if self.centralWidget().findFocus() == self.timeline_widget:
                 self.timeline_widget.delete_selected_notes()
                 event.accept()

        else:
            super().keyPressEvent(event)


    @Slot(int, int, str)
    def update_gui_with_midi(self, note_number: int, velocity: int, event_type: str):
        """MIDI入力マネージャーからの信号を受け取り、ステータスラベルを更新するスロット。"""
        if event_type == 'on':
            self.status_label.setText(f"ノートオン: {note_number} (Velocity: {velocity})")
        elif event_type == 'off':
            self.status_label.setText(f"ノートオフ: {note_number}")
          

    @Slot()
    def on_midi_port_changed(self):
        """MIDIポート選択コンボボックスの変更ハンドラ"""
        selected_port_name = self.midi_port_selector.currentData()
        
        if self.midi_manager:
            self.midi_manager.stop() # 現在のポートを停止
            self.midi_manager = None

        if selected_port_name and selected_port_name != "ポートなし":
            self.midi_manager = MidiInputManager(selected_port_name)
            self.midi_manager.start() # 新しいポートで開始
            self.status_label.setText(f"MIDIポート: {selected_port_name} に接続済み")
        else:
             self.status_label.setText("警告: 有効なMIDIポートが選択されていません。")

    


    def closeEvent(self, event):
        """アプリケーション終了時のクリーンアップ処理。"""
        
        if self.midi_manager: 
            self.midi_manager.stop()
        
        if self.vo_se_engine:
            self.vo_se_engine.close()

        event.accept()


def export_to_wav(self, notes, filename="output/result.wav"):
    # 全てのノート情報をC言語が読める構造体配列に変換して渡す
    # C言語側で「全ノートを繋ぎ合わせて一つのWAVにする」処理を実行させる
    self.lib.start_export(filename.encode('utf-8'))
    for note in notes:
        hz = self.midi_to_hz(note.pitch)
        self.lib.add_note_to_queue(hz, note.start_time, note.duration)
    self.lib.execute_render() # 実行


def on_export_button_clicked(self):
    # 1. タイムラインにノートがあるか確認
    notes = self.timeline_widget.get_all_notes()
    if not notes:
        QMessageBox.warning(self, "エラー", "書き出すノートがありません。")
        return

    # 2. ファイル保存ダイアログを表示
    # 第2引数はタイトル、第3引数はデフォルトのパス、第4引数はファイル形式のフィルタ
    default_path = os.path.expanduser("~/Documents/output.wav") # 初期値を書類フォルダに
    file_path, _ = QFileDialog.getSaveFileName(
        self, 
        "音声ファイルを保存", 
        default_path, 
        "WAV Files (*.wav);;All Files (*)"
    )

    # 3. ユーザーがキャンセルせずにパスを選択した場合のみ実行
    if file_path:
        try:
            # エンジンに選択されたパスを渡してレンダリング
            self.engine_wrapper.export_wav(notes, file_path)
            
            # 完了メッセージ
            QMessageBox.information(self, "完了", f"書き出しが完了しました：\n{file_path}")
            
            # 保存したフォルダを自動で開く（オプション）
            # os.startfile(os.path.dirname(file_path)) # Windowsの場合
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"書き出し中にエラーが発生しました：\n{str(e)}")
