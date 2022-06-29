import os
import sqlite3
import csv
import sys
from functools import wraps
from pprint import pp, pprint
from traceback import print_exception

from PyQt5 import uic
from PyQt5.QtGui import QPixmap, QPalette, QBrush
from PyQt5.QtWidgets import *


def handle_exception(exc_type, exc_value, exc_traceback):
    with open(r"log.txt", "a") as f:
        print_exception(exc_type, exc_value, exc_traceback, file=f)
    return sys.__excepthook__(exc_type, exc_value, exc_traceback)


def dbg(filename):
    def decorator(func):
        @wraps(func)
        def wrapper(*a, **kwa):
            res = func(*a, **kwa)
            with open(filename, "a") as f:
                pp(a, stream=f)
                pp(kwa, stream=f)
                print(res, file=f)
            return res

        return wrapper

    return decorator


# Чтобы программа всегда могла найти путь к файлам
@dbg(r"log.txt")
def resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(relative)


class SelectEnterType(QMainWindow):
    def __init__(self):
        super().__init__()
        self.show()
        self.setup_UI()

    def setup_UI(self):
        self.setWindowTitle("Serial numbers verification")
        self.setFixedSize(700, 600)
        # Система координат
        self.x = 700
        self.y = 600
        # Загрузка интерфейса
        uic.loadUi(resource_path("templates/SelectEnterTypeTemplate.ui"), self)
        self.setCentralWidget(self.gridWidget)
        # Установка фона
        palette = QPalette()
        palette.setBrush(QPalette.Background, QBrush(QPixmap(resource_path("backgrounds/img.png"))))
        self.setPalette(palette)

        self.opt_1_btn.clicked.connect(lambda: self.move_on("opt_multiple"))
        self.opt_2_btn.clicked.connect(lambda: self.move_on("opt_db"))
        self.opt_3_btn.clicked.connect(lambda: self.move_on("opt_by_himself"))

    def move_on(self, enter_type):
        self.close()
        self.next = EnterSNListWindow(enter_type)


class EnterSNListWindow(QMainWindow):
    def __init__(self, enter_type):
        super().__init__()
        self.show()
        self.dialog = None
        self.SN_LIST = []
        self.setup_UI(enter_type)

    def setup_UI(self, enter_type):
        self.setFixedSize(700, 600)
        # Система координат
        self.x = 700
        self.y = 600
        # Загрузка интерфейса
        uic.loadUi(resource_path("templates/MainWindowTemplate.ui"), self)
        self.setCentralWidget(self.gridWidget)

        # Options
        if enter_type == "opt_db":
            try:
                db_path_file = open(resource_path("data_files/db_path.txt"), "r")
            except FileNotFoundError:
                db_path_file = open(resource_path("data_files/db_path.txt"), "w")
                db_path_file.write("/")
                self.db_path = "/"
                db_path_file.close()
            finally:
                self.db_path = open(resource_path("data_files/db_path.txt"), "r").readlines()[0].strip()

            db_filename, ok_pressed = QFileDialog.getOpenFileName(self,
                                                                  "Select database file",
                                                                  self.db_path,
                                                                  filter="Database files(*.db)")
            if not ok_pressed:
                self.return_back()
            else:
                with open(resource_path("data_files/db_path.txt"), "w") as path_file:
                    path_file.write(db_filename)
                self.cur = self.get_cursor(db_filename)
                # Максимальный номер заказа в БД
                last_order_num = int(self.cur.execute("""SELECT MAX(OrdKey) FROM TableOrder;""").fetchone()[0])

                order_num, ok2_pressed = QInputDialog.getInt(
                    self, "", "Введите номер заказа",
                    last_order_num, 1, last_order_num, 1)
                if not ok2_pressed:
                    self.return_back()
                self.tuple_sn_list = self.cur.execute("""SELECT EsnValueKey 
                    FROM TableEncSerNum WHERE EsnOrder=?""", (order_num,)).fetchall()
                for elem in self.tuple_sn_list:
                    if str(elem[0]) != "":
                        self.SN_LIST.append(str(elem[0]))
                self.order_data = self.cur.execute("""SELECT OrdDateCr, OrdCount 
                    FROM TableOrder WHERE OrdKey=?""", (order_num,))
        elif enter_type == "opt_by_himself":
            self.dialog = QDialog(self)
            uic.loadUi(resource_path("templates/PasteSerialNumbersTemplate.ui"), self.dialog)
            # self.dialog.buttonBox.rejected.connect(self.return_back)
            # self.dialog.buttonBox.accepted.connect(self.opt_db_dialog_accepted)
            if self.dialog.exec():
                text = self.dialog.textEdit.toPlainText()
                for line in text.split("\n"):
                    number = line.strip()
                    if number != '':
                        self.SN_LIST.append(number)
            else:
                self.return_back()
        elif enter_type == "opt_multiple":
            pass

        pprint(self.SN_LIST)
        # Временно
        for elem in self.SN_LIST:
            self.listWidget.addItem(str(elem))

    def get_cursor(self, db_filename):
        con = sqlite3.connect(db_filename, uri=True)
        cur = con.cursor()
        return cur

    def return_back(self):
        if self.dialog:
            self.dialog.close()
        self.close()
        self.next = SelectEnterType()

    def opt_db_dialog_accepted(self):
        self.dialog.textEdit


if __name__ == '__main__':
    sys.excepthook = handle_exception
    app = QApplication(sys.argv)
    select_window = SelectEnterType()
    select_window.show()
    sys.exit(app.exec_())
