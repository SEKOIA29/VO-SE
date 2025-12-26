# app_main.py
import sys
import os
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# PyInstallerのスプラッシュスクリーン制御用
try:
    import pyi_splash
except ImportError:
    pyi_splash = None

# 自作モジュールのインポート（パスはプロジェクト構成に合わせる）
from GUI.main_window import MainWindow
from GUI.vo_se_engine import VoSeEngineWrapper

def main():
    # 1. 高DPI対応（GUIを表示する前に必須）
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # --- 2. アプリの初期化（スプラッシュ表示中に行う処理） ---
    
    # メッセージの更新（スプラッシュ上に文字を出せる場合）
    if pyi_splash:
        pyi_splash.update_text("エンジンを初期化中...")

    # (A) C言語エンジンのロード
    # ここで DLL/dylib のロードと関数定義が行われる
    engine = VoSeEngineWrapper() 

    if pyi_splash:
        pyi_splash.update_text("音源データを読み込み中...")

    # (B) メインウィンドウの作成
    # ここで TimelineWidget やサイドバーなどの重いGUIパーツが生成される
    window = MainWindow(engine=engine)

    # (C) 擬似的な待機（ロードが速すぎてスプラッシュが見えない場合用）
    # time.sleep(1) 

    # --- 3. セットアップ完了、スプラッシュを閉じる ---
    if pyi_splash:
        pyi_splash.close()

    # 4. メインウィンドウを表示してアプリ開始
    window.show()
    sys.exit(app.exec())




# Windowsに独立してると教えるやつ
if os.name == 'nt':
    myappid = 'mycompany.myproduct.vo-se.1.0' # 任意のID
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)



# ----------------------------------------------------------------------
# Pythonスクリプトが直接実行された場合にのみ、以下のブロックが実行される
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # QApplication インスタンスの作成
    app = QApplication(sys.argv)
    
    # --- GUI改修ステップ3 のスタイルシートを適用 ---
    app.setStyleSheet("""
        /* アプリケーション全体の基本フォントと背景色 */
        QMainWindow {
            background-color: #2e2e2e; /* 暗いグレーの背景 */
            color: #eeeeee;            /* 明るいテキスト色 */
        }
        
        /* QPushButton のスタイル設定 */
        QPushButton {
            background-color: #007acc; /* 目立つ青色 */
            border: none;
            color: white;
            padding: 6px 12px;
            margin: 3px;
            border-radius: 4px; /* 角を少し丸くする */
        }
        QPushButton:hover {
            background-color: #005f99; /* ホバー時の色 */
        }
        QPushButton:pressed {
            background-color: #004c80; /* クリック時の色 */
        }

        /* QLabel のスタイル */
        QLabel {
            color: #eeeeee;
            margin: 2px;
        }

        /* QLineEdit (テキスト入力欄) のスタイル */
        QLineEdit {
            background-color: #3e3e3e;
            border: 1px solid #555555;
            padding: 4px;
            color: #eeeeee;
        }
        
        /* QComboBox (キャラクター選択) のスタイル */
        QComboBox {
            background-color: #3e3e3e;
            color: #eeeeee;
            border: 1px solid #555555;
            padding: 4px;
        }

        /* QScrollBar (スクロールバー) のスタイル */
        QScrollBar:horizontal {
            border: 1px solid #444444;
            background: #333333;
            height: 12px;
            margin: 0px;
        }
        QScrollBar:vertical {
            border: 1px solid #444444;
            background: #333333;
            width: 12px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background: #007acc;
            min-width: 20px;
        }
        QScrollBar::handle:vertical {
            background: #007acc;
            min-height: 20px;
        }

        /* QSplitter のハンドル（分割バー）のスタイル */
        QSplitter::handle {
            background-color: #555;
        }
    """)
    # --- スタイルシートここまで ---
    
    # メインウィンドウのインスタンスを作成し、表示する
    window = MainWindow() 
    window.show()
    
    # アプリケーションのイベントループ（ユーザー操作の待ち受け）を開始する
    sys.exit(app.exec())
