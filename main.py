import csv
import os
import platform
import sqlite3
import subprocess
import sys
import time
from functools import wraps
from pprint import pp
from traceback import print_exception

from PyQt5 import uic, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPalette, QBrush, QStandardItemModel, QStandardItem, QColor
from PyQt5.QtWidgets import *

SN_LIST = []
# Следующие методы нужны для взаимодействия с локальной БД - реализация мультиоператорного ввода


def update_operator_num(order_num, cur, conn):
    table_op_quant = cur.execute("""SELECT operators_quant FROM control_table WHERE order_num=?""", (order_num,)).fetchone()
    if not table_op_quant:
        cur.execute("INSERT INTO control_table (order_num, operators_quant) VALUES (?, 0)", (order_num,))
        table_op_quant = 1
    else:
        table_op_quant = table_op_quant[0] + 1
    cur.execute("""UPDATE control_table SET operators_quant=? WHERE order_num=?""", (table_op_quant, order_num,))
    conn.commit()
    call_string = str(f"ALTER TABLE order_{order_num} ADD operator_{table_op_quant} VARCHAR(20)")
    cur.execute(call_string)
    conn.commit()


def minus_one_operator(order_num, cur, conn):
    table_op_quant = cur.execute("""SELECT operators_quant FROM control_table WHERE order_num=?""", (order_num,)).fetchone()
    if not table_op_quant:
        cur.execute("INSERT INTO control_table (order_num, operators_quant) VALUES (?, 0)", (order_num,))
        table_op_quant = 0
    else:
        table_op_quant = table_op_quant[0] - 1
    cur.execute("""UPDATE control_table SET operators_quant=? WHERE order_num=?""", (table_op_quant, order_num,))
    conn.commit()
    call_string = str(f"ALTER TABLE order_{order_num} DROP COLUMN operator_{table_op_quant}")
    cur.execute(call_string)
    conn.commit()


def reset_operator_num(order_num, cur, conn):
    # Пока не используется, можно с его помощью сбросить прогресс всех операторов
    cur.execute("""UPDATE control_table SET operators_quant=0 WHERE order_num=?""", (order_num,))
    call_string = str(f"DROP TABLE order_{order_num}")
    cur.execute(call_string)
    conn.commit()


def get_operator_num(order_num, cur, _):
    table_op_quant: int = int(cur.execute("""SELECT operators_quant FROM control_table WHERE order_num=?""", (order_num,)).fetchone()[0])
    return table_op_quant


def modify_local_db(order_num, cur, con):
    cur.execute("""CREATE TABLE IF NOT EXISTS control_table(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                                                            order_num TEXT NOT NULL,
                                                            operators_quant INTEGER DEFAULT 0 NOT NULL)""")
    con.commit()
    call_string = str(f"CREATE TABLE IF NOT EXISTS order_{order_num}(id INTEGER PRIMARY KEY AUTOINCREMENT "
                      f"NOT NULL)")
    cur.execute(call_string)
    con.commit()


def clean(op_list: list):
    res = []
    for elem in op_list:
        if elem:
            res.append(elem)
    return res


def get_cursor(db_filename):
    # Получение курсора у любой БД
    con = sqlite3.connect(db_filename, uri=True)
    cur = con.cursor()
    return con, cur


def open_file(path):
    # Служебный метод - открыть Проводник / Finder
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
    # Декоратор, который записывает в log.txt все операции с файлами
    # Нужен для корректной сборки .exe-шника
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


@dbg(r"/Users/eremin/Desktop/log.txt")
def resource_path(relative):
    # Чтобы программа всегда могла найти путь к файлам
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
        # Подключение к локальной базе данных
        self.local_db_path = self.find_local_db_path()
        self.local_con, self.local_cur = get_cursor(self.local_db_path)
        # Всякое ненужное
        self.dialog = None
        self.order_num = 0
        self.last_order_num = 0
        if SN_LIST:
            self.SN_LIST = list(set(SN_LIST))
        else:
            self.SN_LIST = []
        self.setup_UI(enter_type)
        # Для подтверждения отсутствия повторений в таблице
        self.added = []

    def setup_UI(self, enter_type):
        self.setFixedSize(700, 600)
        # self.resize(700, 600)
        # Загрузка интерфейса
        # self.ui = Ui_MainWindow()
        # self.setupUi(self)
        uic.loadUi(resource_path("templates/MainWindowTemplate.ui"), self)
        self.setCentralWidget(self.gridWidget)
        # Установка фона
        palette = QPalette()
        palette.setBrush(QPalette.Background, QBrush(QPixmap(resource_path("backgrounds/img.png"))))
        self.setPalette(palette)

        self.modify_table()
        # Настройка крутилки
        self.dial.setMinimum(1)
        self.dial.setMaximum(7)
        value = 5
        self.dial.setValue(value)
        self.dial.valueChanged.connect(lambda: self.change_background())
        # Подключение кнопок
        self.save_btn.clicked.connect(self.save_table)
        self.return_home_btn.clicked.connect(self.return_back)
        self.delete_all_btn.clicked.connect(self.delete_all)
        self.code_scanned_btn.clicked.connect(self.code_scanned)
        self.add_data_btn.clicked.connect(self.add_data)
        self.export_local_db_button.clicked.connect(self.export_local_db)
        # Options
        self.added = []
        for elem in self.SN_LIST:
            if elem not in self.added:
                self.model.appendRow([QStandardItem(elem),
                                      QStandardItem(""),
                                      QStandardItem("Not found"),
                                      ])
                self.added.append(elem)

        # Изучаем возможные способы ввода данных
        if enter_type == "opt_db":
            self.export_local_db_button.hide()
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
                # Подключение к базе данных
                _, cur = get_cursor(db_filename)
                # Максимальный номер заказа в БД
                self.last_order_num = int(cur.execute("""SELECT MAX(OrdKey) FROM TableOrder;""").fetchone()[0])

                order_num, ok2_pressed = QInputDialog.getInt(
                    self, "", "Введите номер заказа",
                    self.last_order_num, 1, self.last_order_num, 1)
                if not ok2_pressed:
                    self.return_back()
                self.tuple_sn_list = cur.execute("""SELECT EsnValueKey 
                    FROM TableEncSerNum WHERE EsnOrder=?""", (order_num,)).fetchall()
                for elem in self.tuple_sn_list:
                    if str(elem[0]) != "" and str(elem[0]) not in self.SN_LIST:
                        self.SN_LIST.append(str(elem[0]))
                self.order_data = cur.execute("""SELECT OrdDateCr, OrdCount 
                    FROM TableOrder WHERE OrdKey=?""", (order_num,)).fetchall()
                self.order_num = order_num
        elif enter_type == "opt_by_himself":
            self.export_local_db_button.hide()
            self.dialog = QDialog(self)
            uic.loadUi(resource_path("templates/PasteSerialNumbersTemplate.ui"), self.dialog)
            if self.dialog.exec():
                text = self.dialog.textEdit.toPlainText()
                for line in text.split("\n"):
                    clear_line = line.strip()
                    if not clear_line.isdigit():
                        if "производство" in clear_line.lower():
                            self.order_num = clear_line.split()[4]
                    else:
                        number = clear_line
                        if number != '' and number not in self.SN_LIST:
                            self.SN_LIST.append(number)
            else:
                self.return_back()
        elif enter_type == "opt_multiple":
            self.add_data_btn.hide()
            # Добываем номер заказа
            order_num, ok_pressed = QInputDialog.getInt(self, "", "Введите номер заказа",
                                            self.last_order_num, 1, 40000, 1)
            if not ok_pressed:
                self.return_back()
            else:
                self.order_num = order_num
                # ВАЖНО!!
                modify_local_db(self.order_num, self.local_cur, self.local_con)
                update_operator_num(self.order_num, self.local_cur, self.local_con)
                # ОБНОВЛЯЕМ ПОРЯДКОВЫЙ НОМЕР ОПЕРАТОРА
                real_operator_num = get_operator_num(self.order_num, self.local_cur, self.local_con)
                self.dialog = QDialog(self)
                uic.loadUi(resource_path("templates/MultiOperatorTemplate.ui"), self.dialog)
                self.dialog.comment_label.setText(f"Оператор номер {get_operator_num(self.order_num, self.local_cur, self.local_con)}")
                if self.dialog.exec():
                    op_column_name = f"operator_{real_operator_num}"
                    if op_column_name == "operator_1":
                        # Получаем текст
                        text = self.dialog.textEdit.toPlainText()
                        for line in text.split("\n"):
                            number = line.strip()
                            if number and number not in self.SN_LIST:
                                call_string = str(f"INSERT INTO order_{self.order_num}({op_column_name}) VALUES (\'{number}\')")
                                self.local_cur.execute(call_string)
                                self.local_con.commit()
                                # Добавить в локальный список
                                self.SN_LIST.append(number)
                    else:
                        self.local_con.commit()
                        call_string = str(f"SELECT operator_{int(real_operator_num) - 1} FROM order_{self.order_num}")
                        prev_op_list = clean([_[0] for _ in self.local_cur.execute(call_string).fetchall()])
                        print("PREV op:", prev_op_list)
                        curr_op_list = []
                        # Получаем текст
                        text = self.dialog.textEdit.toPlainText()
                        for line in text.split("\n"):
                            number = line.strip()
                            if number and number not in curr_op_list:
                                curr_op_list.append(number)
                        print("CURR op:", curr_op_list)

                        prev_op_list, curr_op_list = set(prev_op_list), set(curr_op_list)
                        if prev_op_list & curr_op_list:
                            for elem in prev_op_list & curr_op_list:
                                self.SN_LIST.append(elem)
                                # Найти в первой колонке
                                call_string = str(f"""UPDATE order_{self.order_num} SET operator_{real_operator_num} = {elem}
                                WHERE id = (SELECT id FROM order_{self.order_num} WHERE operator_{int(real_operator_num) - 1} = {elem})""")
                                self.local_cur.execute(call_string)
                                self.local_con.commit()
                            for elem in curr_op_list - prev_op_list:
                                if elem:
                                    call_string = str(f"INSERT INTO order_{self.order_num}({op_column_name}) VALUES (\'{elem}\')")
                                    self.local_cur.execute(call_string)
                                    self.local_con.commit()

                            # сообщения, если что-либо пошло не так
                            if (prev_op_list - curr_op_list) and (curr_op_list - prev_op_list):
                                msg = QMessageBox()
                                msg.setIcon(QMessageBox.Warning)
                                msg.setWindowModality(Qt.ApplicationModal)
                                msg.setText("Warning!")
                                msg.setInformativeText(f'Предыдущий оператор добавил номера,  которые были не найдены '
                                                       f'у вас: {list(prev_op_list - curr_op_list)},  а вы добавили '
                                                       f'номера,  не обнаруженные у предыдущего оператора: '
                                                       f'{list(curr_op_list - prev_op_list)}')
                                msg.setWindowTitle("Warning")
                                msg.exec_()
                            elif prev_op_list - curr_op_list:
                                msg = QMessageBox()
                                msg.setIcon(QMessageBox.Warning)
                                msg.setWindowModality(Qt.ApplicationModal)
                                msg.setText("Warning!")
                                msg.setInformativeText(f'Предыдущий оператор добавил номера, которые были не найдены '
                                                       f'у вас: {list(prev_op_list - curr_op_list)}')
                                msg.setWindowTitle("Warning")
                                msg.exec_()
                            elif curr_op_list - prev_op_list:
                                msg = QMessageBox()
                                msg.setIcon(QMessageBox.Warning)
                                msg.setWindowModality(Qt.ApplicationModal)
                                msg.setText("Warning!")
                                msg.setInformativeText(f'Вы добавили '
                                                       f'номера, не обнаруженные у предыдущего оператора: '
                                                       f'{list(curr_op_list - prev_op_list)}')
                                msg.setWindowTitle("Warning")
                                msg.exec_()
                        else:
                            msg = QMessageBox()
                            msg.setIcon(QMessageBox.Warning)
                            msg.setWindowModality(Qt.ApplicationModal)
                            msg.setText("Warning!")
                            msg.setInformativeText('У вас не совпало ни одного номера с предыдущим оператором!')
                            msg.setWindowTitle("Warning")
                            msg.exec_()
                            minus_one_operator(self.order_num, self.local_cur, self.local_con)
                            self.return_back()
                else:
                    minus_one_operator(self.order_num, self.local_cur, self.local_con)
                    self.return_back()

        # Для надежности
        for elem in self.SN_LIST:
            if elem not in self.added:
                self.model.appendRow([QStandardItem(elem),
                                      QStandardItem(""),
                                      QStandardItem("Not found"),
                                      ])
                self.added.append(elem)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == Qt.Key_Return:
            code = self.scan_field.text().strip()
            if code != "":
                self.code_scanned()

    def export_local_db(self):
        try:
            csv_path_file = open(resource_path("data_files/order_data_csv_path.txt"), "r")
        except FileNotFoundError:
            csv_path_file = open(resource_path("data_files/order_data_csv_path.txt"), "w")
            csv_path_file.write("/")
            self.csv_path = "/"
            csv_path_file.close()
        finally:
            self.csv_path = open(resource_path("data_files/order_data_csv_path.txt"), "r").readlines()[0].strip()

        filename, ok3_pressed = QFileDialog.getSaveFileName(self, "Select where to save a .csv file",
                                                            self.csv_path.rsplit("/", maxsplit=1)[
                                                                0] + "/" + f"order_{self.order_num}_data.csv",
                                                            "*.csv")
        if not ok3_pressed:
            return
        call_string = str(f"SELECT * FROM order_{self.order_num}")
        data = self.local_cur.execute(call_string).fetchall()
        with open(filename, "w") as outf:
            writer = csv.writer(outf, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerows(data)
        with open(resource_path("data_files/order_data_csv_path.txt"), "w") as path_file:
            path_file.write(filename)
        try:
            open_file(filename.rsplit("/", maxsplit=1)[0])
            # open_file(filename)
            # subprocess.call(["open", filename.rsplit("/", maxsplit=1)[0]])
        except Exception as e:
            print("Unexpected exception:", e)

    def code_scanned(self):
        self.add_data_btn.hide()
        code = self.scan_field.text().strip()
        if code != "":
            table_code = self.model.findItems(code, flags=Qt.MatchExactly, column=0)
            if not table_code:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowModality(Qt.ApplicationModal)
                msg.setText("Warning!")
                msg.setInformativeText(
                    f'Serial number \'{code}\' was not found in initial list. It will be added at your list with '
                    f'\"Added later\" status.')
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
            self.scan_field.clear()

    def change_background(self):
        # Изменение фона
        value = int(self.dial.value())
        if value == 7:
            self.label.setText("<p style='color: rgb(250, 250, 250)' align='left'>Поле для сканирования</p>")
            self.return_home_btn.setStyleSheet("text-align: left; color: white; text-decoration:underline; "
                                               "background-color: transparent; font-weight: italic;")
        elif value == 3:
            self.return_home_btn.setStyleSheet("text-align: left; color: white; text-decoration:underline; "
                                               "background-color: transparent; font-weight: italic;")
        else:
            self.label.setText("<p style='color: rgb(0, 0, 0)' align='left'>Поле для сканирования</p>")
            self.return_home_btn.setStyleSheet("text-align:left; color: rgb(10, 87, 182); background-color: transparent; "
                                               "text-decoration: underline; font-weight: italic;")
        palette = QPalette()
        palette.setBrush(QPalette.Background, QBrush(QPixmap(resource_path(f"backgrounds/vector_{value}.jpeg"))))
        self.setPalette(palette)

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

        filename, ok3_pressed = QFileDialog.getSaveFileName(self, "Select where to save a .csv file",
                                                            self.csv_path.rsplit("/", maxsplit=1)[
                                                                0] + "/order_" + str(self.order_num) + time.strftime(
                                                                "_%Y-%m-%d_%H-%M-%S", time.localtime()) + ".csv",
                                                            "*.csv")
        if not ok3_pressed:
            return
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
            print("Unexpected exception:", e)
        # self.SN_LIST = []

    def find_local_db_path(self):
        try:
            local_db_path_file = open(resource_path("data_files/local_db_path.txt"), "r")
        except FileNotFoundError:
            local_db_path_file = open(resource_path("data_files/local_db_path.txt"), "w")
            local_db_path, ok4_pressed = QFileDialog.getSaveFileName(self, "Select where to save a local database",
                                                                     "/local_database.db", "*.db")
            while not ok4_pressed:
                local_db_path, ok4_pressed = QFileDialog.getSaveFileName(self,
                                                                         "Select where to save a local database",
                                                                         "/local_database.db", "*.db")
            local_db_path_file.write(local_db_path)
            local_db_path_file.close()
        finally:
            local_db_path = open(resource_path("data_files/local_db_path.txt"), "r").readlines()[0].strip()
        return local_db_path

    def add_data(self):
        SN_LIST.extend(self.SN_LIST)
        self.return_back()

    def delete_all(self):
        self.SN_LIST = []
        global SN_LIST
        SN_LIST = []
        pixmap = QPixmap(resource_path("img/splash.png"))
        splash = QSplashScreen(pixmap)
        splash.show()
        self.model.clear()
        self.modify_table()
        time.sleep(2)
        splash.finish(self)

    def modify_table(self):
        self.model = QStandardItemModel()
        self.tableView.setModel(self.model)
        self.model.setHorizontalHeaderLabels(["number", "confirmation", "status"])
        # Горизонтальная метка расширяет остальную часть окна и заполняет форму
        self.tableView.horizontalHeader().setStretchLastSection(True)
        # Горизонтальное направление, размер таблицы увеличивается до соответствующего размера
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Кисти
        self.okay_brush = QBrush(QColor(0, 255, 127, 150))
        self.was_not_here_brush = QBrush(QColor(0, 100, 0, 180))

    def return_back(self):
        self.order_num = 0
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
