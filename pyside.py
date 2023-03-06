import sys
import random
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QToolBar, QMainWindow
from PySide6.QtGui import QIcon, QScreen
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl


class MyWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        app_icon = QIcon()
        app_icon.addFile('icons/app_icon.png', QtCore.QSize(50, 50))
        self.setWindowIcon(app_icon)
        self.setWindowIcon(QtGui.QIcon(app_icon))
        self.webV = QWebEngineView()
        self.webV.setUrl(QUrl("http://blog.montek.dev"))

        # navtb = QToolBar("Navigation")
        #
        # # adding this tool bar tot he main window
        # self.addToolBar(navtb)

        layout = QVBoxLayout(self)
        layout.addWidget(self.webV)

    @QtCore.Slot()
    def magic(self):
        pass


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    app.setApplicationName("AI Browser")
    widget = MyWidget()
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())

