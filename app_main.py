# app_main.py

import sys
# main_window.py ファイルから MainWindow クラスをインポートする
from main_window import MainWindow 

# PySide6 の QApplication クラスをインポートする
from PySide6.QtWidgets import QApplication

# ----------------------------------------------------------------------
# Pythonスクリプトが直接実行された場合にのみ、以下のブロックが実行される
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # QApplication インスタンスの作成
    app = QApplication(sys.argv)
    
    # メインウィンドウのインスタンスを作成し、表示する
    # これにより、MainWindow内で定義された他のウィジェットやデータモデルも初期化される
    window = MainWindow() 
    window.show()
    
    # アプリケーションのイベントループ（ユーザー操作の待ち受け）を開始する
    sys.exit(app.exec())



if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # --- ここからスタイルシートの追加 ---
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2e2e2e;
            color: #eeeeee;
        }
        QPushButton {
            background-color: #007acc;
            border: none;
            color: white;
            padding: 5px 10px;
            margin: 2px;
        }
        QPushButton:hover {
            background-color: #005f99;
        }
        QLabel {
            color: #eeeeee;
        }
        QScrollBar:horizontal {
            border: 1px solid #444444;
            background: #333333;
            height: 10px;
            margin: 0px 0px 0px 0px;
        }
        /* ... 他のウィジェットのスタイルもここに追加 ... */
    """)
    # --- スタイルシートここまで ---

    window = MainWindow() 
    window.show()
    sys.exit(app.exec())
