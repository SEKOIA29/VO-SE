# app_main.py

import sys
# main_window.py ファイルから MainWindow クラスをインポートする
from GUI.main_window import MainWindow 



# PySide6 の QApplication クラスをインポートする
from PySide6.QtWidgets import QApplication

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
