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
