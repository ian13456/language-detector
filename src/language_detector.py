import os
import csv
import sys
import uuid
import shutil
import atexit
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QColor, QBrush
from PyQt5.QtWidgets import QMainWindow, QWidget, QApplication, QFileDialog, QTableWidgetItem

from .ui import Ui_MainWindow


class LanguageDetector(QWidget):
    def __init__(self):
        self.language_dict = dict()

        self.init_ui()
        self.init_listeners()
        self.init_frequencies()

    def init_ui(self):
        self.app = QApplication(sys.argv)
        self.main_window = QMainWindow()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self.main_window)
        self.main_window.setWindowTitle('Language Detector')

        header_cells = [
            self.ui.languagesTable.horizontalHeaderItem(i) for i in range(3)]
        for cell in header_cells:
            cell.setBackground(QBrush(QColor(37, 50, 75)))
        self.ui.languagesTable.verticalHeader().setStyleSheet(
            "background-color: rgb(37, 50, 75)")

    def init_listeners(self):
        self.ui.importButton.clicked.connect(lambda: self.import_file())
        self.ui.runButton.clicked.connect(lambda: self.predict())
        atexit.register(self.on_terminate)

    def init_frequencies(self):
        with open(Path('assets/letter-frequency.ihf'), encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=';')

            line_count = 0
            for row in csv_reader:
                if line_count == 0:
                    for language in row:
                        self.language_dict[language] = dict()

                for language in row:
                    self.language_dict[language][row['Letter']] = row[language]

                line_count += 1

    def run(self):
        self.main_window.show()
        sys.exit(self.app.exec_())

    def import_file(self):
        filename = self.ask_for_file()

        if filename == '':
            return

        with open(filename, encoding='utf-8') as text:
            whole_text = text.read()
            self.ui.inputBox.setText(whole_text)

    def predict(self):
        text = self.ui.inputBox.toPlainText().lower().replace(' ', '')

        if not text:
            self.ui.graph.setText("Empty Input Detected.")
            return

        text_letter_lookup = dict()

        for letter in text:
            if letter in self.language_dict['Letter']:
                if letter in text_letter_lookup:
                    text_letter_lookup[letter] += 1
                else:
                    text_letter_lookup[letter] = 1

        # normalize data
        sum = 0
        for count in text_letter_lookup.values():
            sum += count

        text_letter_freq = dict()
        for letter, count in text_letter_lookup.items():
            text_letter_freq[letter] = count / sum

        # calculate difference
        text_scores = dict()
        for language in self.language_dict:
            if language != 'Letter':
                score = 0

                for letter in text_letter_freq:
                    expected = float(
                        self.language_dict[language][letter]) / 100.0
                    if letter in text_letter_freq:
                        score += abs(expected - text_letter_freq[letter]) ** 2
                    else:
                        score += expected ** 2

                text_scores[language] = score

        # print(text_scores)
        prediction_results = sorted(
            text_scores.items(), key=lambda item: item[1])

        self.list(prediction_results)
        self.graph(prediction_results)

    def list(self, prediction_results):
        index = 0

        self.ui.languagesTable.clearContents()
        self.ui.languagesTable.setRowCount(len(prediction_results))

        values = [1 / v[1] for v in prediction_results]
        total = sum(values)
        percentages = [v / total for v in values]

        for language in prediction_results:
            self.ui.languagesTable.setItem(
                index, 0, QTableWidgetItem(language[0]))
            self.ui.languagesTable.setItem(
                index, 1, QTableWidgetItem(str(round(percentages[index] * 100, 2))+'%'))
            self.ui.languagesTable.setItem(
                index, 2, QTableWidgetItem(str(round(language[1] * 100, 2))))
            index += 1

    def graph(self, prediction_results):
        ypos = np.arange(len(prediction_results))

        languages = [l[0] for l in prediction_results]
        values = [1 / v[1] for v in prediction_results]
        total = sum(values)
        values = [v / total for v in values]
        explode = np.zeros(len(prediction_results))
        explode[0] = 0.1

        plt.title('Percent Possibility of All Languages')
        plt.xticks(ypos, languages)
        plt.ylabel('score')
        # plt.bar(ypos, values)
        plt.pie(values, labels=languages, autopct='%1.1f%%',
                shadow=True, startangle=90, explode=explode, pctdistance=0.85)

        fig = plt.gcf()
        fig.autofmt_xdate()
        plt.tight_layout()

        file_loc = str(Path(f"saves/{str(uuid.uuid1())}.png"))
        plt.savefig(file_loc)

        pixmap = QPixmap(file_loc)
        self.ui.graph.setPixmap(pixmap)
        plt.clf()

        right_width = pixmap.width()
        left_width = self.main_window.width() - right_width
        self.ui.splitter.setSizes([left_width, right_width])

    def on_terminate(self):
        # removed saved images
        folder = Path('saves')
        for filename in os.listdir(folder):
            if filename == '.gitignore':
                continue
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

    def ask_for_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(QWidget(),
                                                  "Choose a Text File",
                                                  "",
                                                  "All Files (*);;Python Files (*.py)",
                                                  options=options)
        if filename:
            return filename
        return ''
