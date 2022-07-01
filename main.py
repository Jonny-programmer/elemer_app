import os
import sqlite3
import csv
import sys
from functools import wraps
from pprint import pp, pprint
import time
import platform
from traceback import print_exception
from typing import Union
import subprocess

from PyQt5 import uic, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPalette, QBrush, QStandardItemModel, QStandardItem, QColor
from PyQt5.QtWidgets import *

from templates.MainWindowTemplate import Ui_MainWindow


SN_LIST = []


def open_file(path):
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


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
@dbg(r"data_files/log.txt")
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
        if SN_LIST != []:
            self.SN_LIST = SN_LIST
        else:
            self.SN_LIST = []
        self.setup_UI(enter_type)

    def setup_UI(self, enter_type):
        self.setFixedSize(700, 600)
        # self.resize(700, 600)
        # Система координат
        self.x = 700
        self.y = 600
        # Загрузка интерфейса
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # """ uic.loadUi(resource_path("templates/MainWindowTemplate.ui"), self)"""
        self.setCentralWidget(self.ui.gridWidget)
        # Установка фона
        palette = QPalette()
        palette.setBrush(QPalette.Background, QBrush(QPixmap(resource_path("backgrounds/img.png"))))
        self.setPalette(palette)

        self.modify_table()
        # Подключение кнопок
        self.ui.save_btn.clicked.connect(self.save_table)
        self.ui.return_home_btn.clicked.connect(self.return_back)
        self.ui.delete_all_btn.clicked.connect(self.delete_all)
        self.ui.code_scanned_btn.clicked.connect(self.code_scanned)
        self.ui.add_data_btn.clicked.connect(self.add_data)
        # Options
        for elem in self.SN_LIST:
            self.model.appendRow([QStandardItem(elem),
                                  QStandardItem(""),
                                  QStandardItem("Not found"),
                                  ])
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

        # Временно
        for elem in self.SN_LIST:
            self.model.appendRow([QStandardItem(elem),
                                  QStandardItem(""),
                                  QStandardItem("Not found"),
                                  ])

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == Qt.Key_Return:
            code = self.ui.scan_field.text().strip()
            if code != "":
                self.code_scanned()

    def code_scanned(self):
        self.ui.add_data_btn.hide()
        code = self.ui.scan_field.text().strip()
        if code != "":
            table_code = self.model.findItems(code, flags=Qt.MatchExactly, column=0)
            if not table_code:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowModality(Qt.ApplicationModal)
                msg.setText("Warning!")
                msg.setInformativeText(f'Serial number \'{code}\' was not found in initial list. It will be added at your list with "Added later" status.')
                msg.setWindowTitle("Warning")
                msg.exec_()

                item = QStandardItem(code)
                item_confirmation = QStandardItem(code)
                their_status = QStandardItem("Added later")

                item.setBackground(self.was_not_here_brush)
                item_confirmation.setBackground(self.was_not_here_brush)
                their_status.setBackground(self.was_not_here_brush)

                self.model.appendRow([item, item_confirmation, their_status])
            else:
                item = table_code[0]
                new_item = QStandardItem(item.text())
                code_found = QStandardItem("Found")
                # Красим
                item.setBackground(self.okay_brush)
                new_item.setBackground(self.okay_brush)
                code_found.setBackground(self.okay_brush)
                # Засовываем в таблицу
                self.model.setItem(item.row(), 1, new_item)
                self.model.setItem(item.row(), 2, code_found)
            self.ui.scan_field.clear()

    def save_table(self):
        try:
            csv_path_file = open(resource_path("data_files/csv_path.txt"), "r")
        except FileNotFoundError:
            csv_path_file = open(resource_path("data_files/csv_path.txt"), "w")
            csv_path_file.write("/")
            self.csv_path = "/"
            csv_path_file.close()
        finally:
            self.csv_path = open(resource_path("data_files/csv_path.txt"), "r").readlines()[0].strip()

        filename, _ = QFileDialog.getSaveFileName(self, "Select where to save a .csv file",
                                                  self.csv_path.rsplit("/", maxsplit=1)[0] + "/" + time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime()) + ".csv",
                                                  "*.csv")
        with open(filename, "w") as outf:
            writer = csv.writer(outf, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(["number", "confirmation", "status"])
            for row in range(0, self.model.rowCount()):
                writer.writerow([self.model.item(row, 0).text(),
                                 self.model.item(row, 1).text(),
                                 self.model.item(row, 2).text(),
                                 ])
        with open(resource_path("data_files/csv_path.txt"), "w") as path_file:
            path_file.write(filename)
        try:
            open_file(filename.rsplit("/", maxsplit=1)[0])
            # open_file(filename)
            # subprocess.call(["open", filename.rsplit("/", maxsplit=1)[0]])
        except Exception as e:
            pass

    def add_data(self):
        SN_LIST.extend(self.SN_LIST)
        self.return_back()

    def delete_all(self):
        self.model.clear()
        self.modify_table()

    def modify_table(self):
        self.model = QStandardItemModel()
        self.ui.tableView.setModel(self.model)
        self.model.setHorizontalHeaderLabels(["number", "confirmation", "status"])
        # Горизонтальная метка расширяет остальную часть окна и заполняет форму
        self.ui.tableView.horizontalHeader().setStretchLastSection(True)
        # Горизонтальное направление, размер таблицы увеличивается до соответствующего размера
        self.ui.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Кисти
        self.okay_brush = QBrush(QColor(0, 255, 127, 150))
        self.was_not_here_brush = QBrush(QColor(0, 100, 0, 180))

    def get_cursor(self, db_filename):
        con = sqlite3.connect(db_filename, uri=True)
        cur = con.cursor()
        return cur

    def return_back(self):
        if self.dialog:
            self.dialog.close()
        self.close()
        self.next = SelectEnterType()


if __name__ == '__main__':
    sys.excepthook = handle_exception
    app = QApplication(sys.argv)
    select_window = SelectEnterType()
    select_window.show()
    sys.exit(app.exec_())
