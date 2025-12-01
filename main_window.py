# main_window.py

import sys
import time
import json
# janomeライブラリが必要です (pip install janome)
from janome.tokenizer import Tokenizer
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QMenu, QVBoxLayout, 
                               QPushButton, QFileDialog, QScrollBar, QInputDialog, 
                               QLineEdit, QHBoxLayout, QLabel, QSplitter) # QSplitterを追加
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Slot, Qt, QTimer, Signal

#合成音声系
from vo_se_engine import VO_SE_Engine # エンジンのインポート
import numpy as np 


from timeline_widget import TimelineWidget
from keyboard_sidebar_widget import KeyboardSidebarWidget
from midi_manager import load_midi_file, MidiInputManager, midi_signals
from data_models import NoteEvent
from graph_editor_widget import GraphEditorWidget # 新しいウィジェットをインポート

from timeline_widget import TimelineWidget
from keyboard_sidebar_widget import KeyboardSidebarWidget
from midi_manager import load_midi_file, MidiInputManager, midi_signals
from data_models import NoteEvent

class MainWindow(QMainWindow):
    """
    アプリケーションのメインウィンドウクラス。
    UIの構築、イベント接続、全体的なアプリケーションロジックを管理する。
    """
    
# main_window.py の MainWindow.__init__ メソッド

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("統合MIDIアプリケーション")
        self.setGeometry(100, 100, 700, 400) # 幅を少し広げた

        
        self.vo_se_engine = VO_SE_Engine()       
　　　 # キャラクター選択UIの追加
        self.character_selector = QComboBox(self)
        for char_id, char_info in self.vocal_engine.characters.items():
            self.character_selector.addItem(char_info.name, userData=char_id)
        self.character_selector.currentIndexChanged.connect(self.on_character_changed)
        
        # レイアウトにセレクターを追加
        button_layout.addWidget(self.character_selector) # 例えば open_button の隣など

        # 初期キャラクターの設定
        self.vo_se_engine.set_active_character("char_001")



        # --- UIコンポーネントの初期化 ---
        self.status_label = QLabel("アプリケーション起動中...", self)
        self.timeline_widget = TimelineWidget()
        self.keyboard_sidebar = KeyboardSidebarWidget(
            self.timeline_widget.key_height_pixels,
            self.timeline_widget.lowest_note_display
        )
        self.graph_editor_widget = GraphEditorWidget() # 追加: グラフエディタウィジェット
        
        self.play_button = QPushButton("再生/停止", self)
        self.record_button = QPushButton("録音 開始/停止", self)
        self.open_button = QPushButton("MIDIファイルを開く", self)
        self.loop_button = QPushButton("ループ再生: OFF", self)

        # ↓テンポ設定UIを出現★
        self.tempo_label = QLabel("テンポ (BPM):", self)
        self.tempo_input = QLineEdit(str(self.timeline_widget.tempo), self)
        self.tempo_input.setFixedWidth(50)
        self.tempo_input.returnPressed.connect(self.update_tempo_from_input) # Enterキーで更新できる
      
        
                
        self.h_scrollbar = QScrollBar(Qt.Horizontal)
        self.h_scrollbar.setRange(0, 0)
        self.v_scrollbar = QScrollBar(Qt.Vertical)
        self.v_scrollbar.setRange(0, 500)

        # --- 再生・録音制御のための変数とタイマー ---
        self.is_recording = False
        self.is_playing = False
        self.is_looping = False
        self.is_looping_selection = False  #選択範囲ループ判定
        self.current_playback_time = 0.0
        self.start_time_real = 0.0

        # 再生タイマーの設定
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

        # タイムラインエリアをコンテナウィジェットにラップ
        timeline_container = QWidget()
        timeline_container.setLayout(timeline_area_layout)
        
        # QSplitterを使ってタイムラインとグラフエディタを分割
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.addWidget(timeline_container)
        self.main_splitter.addWidget(self.graph_editor_widget)
        self.main_splitter.setSizes([self.height() * 0.7, self.height() * 0.3]) # 初期サイズ比を設定
        

        # ボタンを横並びに配置するコード
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.record_button)
        button_layout.addWidget(self.loop_button)

        #テンポ 
        button_layout.addWidget(self.tempo_label)
        button_layout.addWidget(self.tempo_input)

        button_layout.addWidget(self.open_button)

        
        # メインレイアウトの構築
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.main_splitter) # main_splitterを配置
        main_layout.addWidget(self.h_scrollbar)
        main_layout.addLayout(button_layout)
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

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
        
        # スクロールバーとウィジェットの同期
        self.h_scrollbar.valueChanged.connect(self.timeline_widget.set_scroll_x_offset)
        self.v_scrollbar.valueChanged.connect(self.timeline_widget.set_scroll_y_offset)
       self.v_scrollbar.valueChanged.connect(self.keyboard_sidebar.set_scroll_y_offset)
        
         self.h_scrollbar.valueChanged.connect(self.graph_editor_widget.set_scroll_x_offset) # GraphEditorにも同期
        self.timeline_widget.zoom_changed_signal.connect(self.graph_editor_widget.set_pixels_per_beat) # GraphEditorにも同期
        
        self.timeline_widget.zoom_changed_signal.connect(self.update_scrollbar_range)
        self.timeline_widget.vertical_zoom_changed_signal.connect(self.update_scrollbar_v_range)
        self.timeline_widget.notes_changed_signal.connect(self.update_scrollbar_range) # ★追加: 新しいシグナルを接続
        
        # GraphEditorからのシグナル受信
        self.graph_editor_widget.pitch_data_changed.connect(self.on_pitch_data_updated)

        # --- MIDI入力マネージャーの起動 (自動ポート検出) ---
        available_ports = MidiInputManager.get_available_ports()
        if available_ports:
            selected_port_name = available_ports if isinstance(available_ports, list) else available_ports
            print(f"MIDIポート '{selected_port_name}' に自動接続します。")
            self.status_label.setText(f"MIDIポート: {selected_port_name} に接続済み")
            self.midi_manager = MidiInputManager(selected_port_name)
            self.midi_manager.start()
        else:
            print("利用可能なMIDIポートが見つかりませんでした。")
            self.status_label.setText("警告: MIDIポートが見つかりません。")
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
        self.save_action = QAction("プロジェクト保存(&S)", self)
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
        
        # ----------------------------------------
        # 再生中の場合: 停止処理を実行
        # ----------------------------------------
        if self.is_playing:
            self.is_playing = False
            self.playback_timer.stop()
            self.play_button.setText("再生/停止")
            self.status_label.setText("再生停止しました。")
            self.playing_notes = {} # 再生管理リストをクリア

            # pyaudioストリームをフラッシュし、停止中にする
            if self.vo_se_engine and hasattr(self.vo_se_engine, 'stream') and self.vo_se_engine.stream.is_active():
                 # TODO: エンジン内で再生中のスレッドも停止させる仕組みが必要
                 self.vo_se_engine.stream.stop_stream()
                 # self.vo_se_engine.stream.start_stream() # 再開は再生直前で良い
            

        # ----------------------------------------
        # 停止中の場合: 音声生成と再生開始処理を実行
        # ----------------------------------------
        else:
            # 録音中であれば、先に録音を停止する
            if self.is_recording:
                self.on_record_toggled()
            
            # --- 再生範囲の取得 ---
            if self.is_looping_selection and self.timeline_widget.get_selected_notes():
                 start_time, end_time = self.timeline_widget.get_selected_notes_range()
            else:
                 # 選択範囲がない場合や通常ループの場合、プロジェクト全体の範囲を取得
                 start_time, end_time = self.timeline_widget.get_project_duration_and_start()

            if start_time >= end_time:
                 self.status_label.setText("ノートが存在しないため再生できません。")
                 return

            notes = self.timeline_widget.notes_list
            pitch = self.pitch_data # MainWindow が保持しているピッチデータ
            
            try:
                self.status_label.setText("音声生成中...お待ちください。")
                QApplication.processEvents() # UIを更新してユーザーにメッセージを表示

                # --- ここでエンジンを呼び出して音声を生成（時間がかかる処理） ---
                audio_track = self.vo_se_engine.synthesize_track(
                    notes,         
                    pitch,         
                    start_time, 
                    end_time
                )
                
                # --- 生成後にオーディオ再生とGUIの再生状態を開始 ---
                
                # エンジンのストリームが停止中であれば再開する
                if hasattr(self.vo_se_engine, 'stream') and not self.vo_se_engine.stream.is_active():
                    self.vo_se_engine.stream.start_stream()

                # 生成された音声を別スレッドで再生開始
                import threading
                # play_audioメソッド内でストリームに書き込む
                playback_thread = threading.Thread(target=self.vo_se_engine.play_audio, args=(audio_track,))
                playback_thread.daemon = True 
                playback_thread.start()
                
                # GUIの再生状態を更新
                self.current_playback_time = start_time # 再生開始位置をセット
                self.start_time_real = time.time() - self.current_playback_time
                self.is_playing = True
                self.playback_timer.start() # UI上のカーソル移動タイマーを開始
                
                self.play_button.setText("■ 再生中 (停止)")
                self.status_label.setText(f"再生開始しました (範囲: {start_time:.2f}s - {end_time:.2f}s)。")

            except Exception as e: # ValueErrorだけでなく一般的なエラーもキャッチ
                 self.status_label.setText(f"再生エラーが発生しました: {e}")
                 print(f"再生エラーの詳細: {e}")

                


    @Slot()
    def on_loop_button_toggled(self):
        """ループ再生ボタンのハンドラ"""
        # ループモードを切り替える
        self.is_looping_selection = not self.is_looping_selection

        if self.is_looping_selection:
            self.loop_button.setText("選択範囲ループ: ON")
            self.status_label.setText("選択範囲でのループ再生を有効にしました。")
            self.is_looping = True # 選択範囲ループ時は全体のループも必然的にON
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
            self.timeline_widget.update_scrollbar_range_after_recording()
        else:
            if self.is_playing:
                self.on_play_pause_toggled()

            import time
            self.is_recording = True
            self.record_button.setText("■ 録音中 (停止)")
            self.status_label.setText("録音開始しました。MIDI入力を待っています...")
            # self.timeline_widget.notes_list = []
            self.timeline_widget.set_recording_state(True, time.time())

#キャラクター変更スロット
    @Slot()
    def on_character_changed(self):
        char_id = self.character_selector.currentData()
        self.vo_se_engine.set_active_character(char_id)

    
# main_window.py 内

    @Slot()
    def update_playback_cursor(self):
        """タイマーイベントごとに呼び出され、再生カーソル位置とオーディオ再生を同期更新する"""
        if self.is_playing:
            current_system_time = time.time()
            self.current_playback_time = current_system_time - self.start_time_real
            
            # --- オーディオ再生バッファの管理 ---
            # NOTE: このリアルタイムのアプローチは非常に複雑です。
            # ここでは、再生タイミングになったノートのバッファを生成し、直ちにストリームに書き込む簡易的な方法を維持します。
            
            notes_to_play_on = []
            notes_to_play_off = []
            for note in self.timeline_widget.notes_list:
                if note not in self.playing_notes:
                    if self.current_playback_time >= note.start_time and self.current_playback_time < note.start_time + note.duration:
                        notes_to_play_on.append(note)
                else:
                    if self.current_playback_time >= note.start_time + note.duration:
                        notes_to_play_off.append(note)
            
            for note in notes_to_play_off:
                # このタイミングで note_off を音声エンジンまたはストリームに送る必要がある
                del self.playing_notes[note]
            
            for note in notes_to_play_on:
                self.playing_notes[note] = True
                
                duration_left = note.start_time + note.duration - self.current_playback_time
                if duration_left > 0:
                   # VO-SE Engine の簡易合成機能を使用してバッファを取得
                   # （VO-SE Engine内に generate_audio_buffer のロジックを統合した前提）
                   audio_buffer = self.vo_se_engine.generate_note_buffer(
                       note.note_number, 0, duration_left, self.current_playback_time
                   )
                   
                   if audio_buffer.size > 0:
                        # 生成したバッファを pyaudio ストリームに書き込む
                        # self.vo_se_engine.stream は pyaudio ストリームである前提
                        self.vo_se_engine.stream.write(audio_buffer.tobytes())

            # --- ループ処理のロジック ---
            if self.is_looping:
                if self.is_looping_selection:
                    project_start_time, project_end_time = self.timeline_widget.get_selected_notes_range()
                else:
                    project_start_time, project_end_time = self.timeline_widget.get_project_duration_and_start()
                
                if self.current_playback_time >= project_end_time and project_end_time > project_start_time:
                    self.current_playback_time = project_start_time
                    self.start_time_real = time.time() - self.current_playback_time
                
                if self.current_playback_time < project_start_time:
                    self.current_playback_time = project_start_time
                    self.start_time_real = time.time() - self.current_playback_time

            # --- GUIの更新と自動スクロール ---
            self.timeline_widget.set_current_time(self.current_playback_time)
            # GraphEditorWidgetの再生カーソルも更新
            self.graph_editor_widget.set_current_time(self.current_playback_time)

            # 自動スクロールのロジック
            current_beats = self.timeline_widget.seconds_to_beats(self.current_playback_time)
            cursor_x_pos = current_beats * self.timeline_widget.pixels_per_beat
            viewport_width = self.timeline_widget.width()
            target_scroll_x = cursor_x_pos - (viewport_width / 2)
            max_scroll_value = self.h_scrollbar.maximum()
            min_scroll_value = self.h_scrollbar.minimum()
            clamped_scroll_x = max(min_scroll_value, min(max_scroll_value, target_scroll_x))
            self.h_scrollbar.setValue(int(clamped_scroll_x))


    @Slot()
    def update_scrollbar_range(self):
        """ズーム変更時やノートリスト変更時などに水平スクロールバーの範囲を動的に更新する"""
        if not self.timeline_widget.notes_list:
            self.h_scrollbar.setRange(0, 0)
            return
        
        # ↓↓↓↓ 新しいロジックに置き換え ↓↓↓↓
        # プロジェクトの最大拍数を取得
        max_beats = self.timeline_widget.get_max_beat_position()
        
        # 最大拍数に対応するピクセル位置を計算
        max_x_position = max_beats * self.timeline_widget.pixels_per_beat
        
        # スクロールバーの最大値は、コンテンツの終わりからビューポートの幅を引いた値
        # スクロール可能な範囲を設定
        viewport_width = self.timeline_widget.width()
        max_scroll_value = max(0, int(max_x_position - viewport_width))
        
        self.h_scrollbar.setRange(0, max_scroll_value)
        # ↑↑↑↑ 新しいロジックに置き換え ↑↑↑↑
        
        # Note: このメソッド内で以前呼び出していた timeline_widget.update_scrollbar_range_after_recording() 
        # のロジックはここに移管されたため、呼び出しは不要です。


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
            pitch_data = [p_event.to_dict() for p_event in self.pitch_data] # ★追加: ピッチデータをdictに変換
            
            save_data_structure = {
                "app_id": "Vocaloid_Clone_App_12345", 
                "type": "note_project_data", 
                "notes": notes_data,
                "pitch_data": pitch_data # ★追加: JSON構造にピッチデータを含める
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
            import mido
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
            loaded_pitch_data = [] # ★追加: 読み込んだピッチデータを一時的に保持
            
            if filepath.lower().endswith('.json'):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get("app_id") == "Vocaloid_Clone_App_12345":
                            notes_data = data.get("notes", [])
                            notes_list = [NoteEvent.from_dict(d) for d in notes_data]
                            # ★追加: ピッチデータを読み込み、PitchEventオブジェクトに変換
                            pitch_data_dicts = data.get("pitch_data", [])
                            loaded_pitch_data = [PitchEvent.from_dict(d) for d in pitch_data_dicts]

                            self.status_label.setText(f"プロジェクトファイルの読み込み完了。ノート数: {len(notes_list)}, ピッチポイント数: {len(loaded_pitch_data)}")
                        else:
                            self.status_label.setText("エラー: サポートされていないプロジェクト形式です。")
                except Exception as e:
                    self.status_label.setText(f"JSONファイルの読み込みエラー: {e}")
                    return

            elif filepath.lower().endswith(('.mid', '.midi')):
                # MIDIファイルからの読み込み時はピッチデータは生成されない
                data_dicts = load_midi_file(filepath)
                if data_dicts:
                    notes_list = [NoteEvent.from_dict(d) for d in data_dicts]
                    self.status_label.setText(f"MIDIファイルの読み込み完了。イベント数: {len(notes_list)}")
            
            if notes_list or loaded_pitch_data:
                # ノートリストをTimelineWidgetに設定
                self.timeline_widget.set_notes(notes_list)
                # MainWindowのピッチデータも更新
                self.pitch_data = loaded_pitch_data
                # GraphEditorWidgetにもピッチデータを設定して描画させる
                self.graph_editor_widget.set_pitch_events(self.pitch_data)

                self.update_scrollbar_range()
                self.update_scrollbar_v_range()

    @Slot(int, int, str)
    def update_gui_with_midi(self, note_number: int, velocity: int, event_type: str):
        """MIDI入力マネージャーからの信号を受け取り、ステータスラベルを更新するスロット。"""
        if event_type == 'on':
            self.status_label.setText(f"ノートオン: {note_number} (Velocity: {velocity})")
        elif event_type == 'off':
            self.status_label.setText(f"ノートオフ: {note_number}")

    


    def closeEvent(self, event):
        """アプリケーション終了時のクリーンアップ処理。MIDIマネージャー、オーディオストリーム、そしてVO-SE Engineを停止・終了する。"""
        
        # 1. MIDIマネージャーの停止
        if self.midi_manager: 
            self.midi_manager.stop()
        
        # 2. PyAudio ストリームのクリーンアップ（古い実装が残っている場合の安全策）
        #    VO-SE Engine に処理を委譲する場合はこの部分は不要になりますが、
        #    両方の実装が混在していたため、ここでは両方有効な状態としています。
        if hasattr(self, 'stream') and self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'p'):
            self.p.terminate()

        # 3. VO-SE Engine インスタンスのクローズ処理を呼び出す
        #    （オーディオクリーンアップをVO-SE Engine内に集約した場合）
        if self.vo_se_engine:
            self.vo_se_engine.close()

        # イベントを受け入れてウィンドウを閉じる
        event.accept()

  

    @Slot(list)
    def on_pitch_data_updated(self, new_pitch_events: list):
        """GraphEditorWidgetから更新されたピッチデータを受け取る"""
        self.pitch_data = new_pitch_events
        print(f"ピッチデータが更新されました。総ポイント数: {len(self.pitch_data)}")

    @Slot()
    def update_tempo_from_input(self):
        """テンポ入力欄から値を取得し、タイムラインウィジェットなどに反映させる"""
        try:
            new_tempo = float(self.tempo_input.text())
            if 30.0 <= new_tempo <= 300.0: # テンポ範囲を制限
                # TimelineWidgetに新しいテンポを通知
                self.timeline_widget.tempo = new_tempo
                # GraphEditorWidgetに新しいテンポを通知
                self.graph_editor_widget.tempo = new_tempo
                
                # テンポ変更に伴い、描画やスクロール範囲も更新
                self.timeline_widget.update()
                self.graph_editor_widget.update()
                self.update_scrollbar_range()
                self.status_label.setText(f"テンポを {new_tempo} BPM に更新しました。")
            else:
                raise ValueError("テンポは30から300の範囲で入力してください。")
        except ValueError as e:
            self.status_label.setText(f"エラー: {e}")
            self.tempo_input.setText(str(self.timeline_widget.tempo)) # 無効な値は元の値に戻す




    def keyPressEvent(self, event: QKeyEvent):
        """
        キーボードショートカットのイベントハンドラ。
        スペースキーで再生/停止を切り替える。
        """
        if event.key() == Qt.Key_Space:
            # スペースキーが押されたら、再生/停止ボタンのスロットを呼び出す
            self.on_play_pause_toggled()
            event.accept() # イベントを処理済みとしてマーク
        
        elif event.key() == Qt.Key_R and event.modifiers() == Qt.ControlModifier:
            # Ctrl+R で録音開始/停止 (例)
            self.on_record_toggled()
            event.accept()

        elif event.key() == Qt.Key_L and event.modifiers() == Qt.ControlModifier:
            # Ctrl+L でループ切り替え (例)
            self.on_loop_button_toggled()
            event.accept()

        # ウィジェットにフォーカスがある状態で Delete/Backspaceが押された場合の処理
        # TimelineWidgetで既に実装されているかもしれませんが、MainWindowでも一括処理可能
        elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            # 現在フォーカスがあるウィジェットがTimelineWidgetなら、その削除機能を呼び出す
            if self.centralWidget().findFocus() == self.timeline_widget:
                 self.timeline_widget.delete_selected_notes()
                 event.accept()

        else:
            # 他のキーイベントは親クラス（QMainWindow）に任せる
            super().keyPressEvent(event)






# main_window.py の on_play_pause_toggled 内（簡易オフライン再生版）


    @Slot()
    def on_play_pause_toggled(self):
        """再生/停止ボタンのハンドラ"""
        
        # ----------------------------------------
        # 再生中の場合: 停止処理を実行
        # ----------------------------------------
        if self.is_playing:
            self.is_playing = False
            self.playback_timer.stop()
            
            # TODO: VO-SE Engineで再生中の音声があれば停止させる仕組みが必要
            # 例: self.vo_se_engine.stop_playback() 
            
            self.play_button.setText("再生/停止")
            self.status_label.setText("再生停止しました。")
            self.playing_notes = {} # 再生管理リストをクリア
            

        # ----------------------------------------
        # 停止中の場合: 音声生成と再生開始処理を実行
        # ----------------------------------------
        else:
            # 録音中であれば、先に録音を停止する
            if self.is_recording:
                self.on_record_toggled()
            
            # --- ループ範囲を取得（TODO箇所を修正） ---
            if self.is_looping_selection and self.timeline_widget.get_selected_notes():
                 start_time, end_time = self.timeline_widget.get_selected_notes_range()
            else:
                 # 選択範囲がない場合や通常ループの場合、プロジェクト全体の範囲を取得
                 start_time, end_time = self.timeline_widget.get_project_duration_and_start()

            if start_time >= end_time:
                 self.status_label.setText("ノートが存在しないため再生できません。")
                 return

            # --- ここでエンジンを呼び出して音声を生成 ---
            # これは時間がかかるため、UIをブロックしないように別スレッドで実行するのが理想的。
            # ただし、ここでは簡易的にメインスレッドで実行。
            notes = self.timeline_widget.notes_list
            pitch = self.pitch_data # MainWindow が保持しているピッチデータ
            
            try:
                self.status_label.setText("音声生成中...お待ちください。")
                QApplication.processEvents() # UIを更新してユーザーにメッセージを表示

                # 音声生成（時間がかかる処理）
                audio_track = self.vo_se_engine.synthesize_track(notes, pitch, start_time, end_time)
                
                # 生成が完了したら再生準備
                self.current_playback_time = start_time # 再生開始位置をセット
                self.start_time_real = time.time() - self.current_playback_time
                
                self.is_playing = True
                self.playback_timer.start() # UI上のカーソル移動タイマーを開始
                
                # --- 生成された音声を別スレッドで再生開始 ---
                # UIタイマーとは独立してオーディオ再生スレッドを起動する
                import threading
                # play_audioメソッド内でブロッキング再生（最後まで再生してから戻る）を想定
                playback_thread = threading.Thread(target=self.vo_se_engine.play_audio, args=(audio_track,))
                playback_thread.daemon = True # メインアプリ終了時に一緒に終了させる
                playback_thread.start()
                
                self.play_button.setText("■ 再生中 (停止)")
                self.status_label.setText(f"再生開始しました (範囲: {start_time:.2f}s - {end_time:.2f}s)。")

            except ValueError as e:
                self.status_label.setText(f"再生エラー: {e}")
            except Exception as e:
                 self.status_label.setText(f"予期せぬエラーが発生しました: {e}")
