# -*- coding: utf-8 -*-

import os
import threading

import numpy as np
from PySide2.QtCharts import QtCharts
from PySide2.QtCore import QEvent, QObject, Qt
from PySide2.QtGui import QColor, QGuiApplication, QKeySequence
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import (QFileDialog, QFrame, QGraphicsDropShadowEffect,
                               QGroupBox, QHeaderView, QLabel, QLineEdit,
                               QProgressBar, QPushButton, QRadioButton,
                               QTableView)
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize, scale

from ViewPCA.callout import Callout
from ViewPCA.coins import Coins
from ViewPCA.model import Model


class Table(QObject):

    def __init__(self, multiprocessing_pool, chart):
        QObject.__init__(self)

        self.module_path = os.path.dirname(__file__)

        self.pool = multiprocessing_pool
        self.chart = chart
        self.model = Model()
        self.model_selection = Model()
        self.coins = Coins(self.pool)

        self.callout = Callout(self.chart)
        self.callout.hide()

        loader = QUiLoader()

        self.main_widget = loader.load(self.module_path + "/ui/table.ui")

        self.table_view = self.main_widget.findChild(QTableView, "table_view")
        table_cfg_frame = self.main_widget.findChild(QFrame, "table_cfg_frame")
        pc_frame = self.main_widget.findChild(QFrame, "pc_frame")
        button_load_data = self.main_widget.findChild(QPushButton, "button_load_data")
        self.pc1_variance_ratio = self.main_widget.findChild(QLabel, "pc1_variance_ratio")
        self.pc1_singular_value = self.main_widget.findChild(QLabel, "pc1_singular_value")
        self.pc2_variance_ratio = self.main_widget.findChild(QLabel, "pc2_variance_ratio")
        self.pc2_singular_value = self.main_widget.findChild(QLabel, "pc2_singular_value")
        self.legend = self.main_widget.findChild(QLineEdit, "legend_name")
        self.groupbox_axis = self.main_widget.findChild(QGroupBox, "groupbox_axis")
        self.groupbox_norm = self.main_widget.findChild(QGroupBox, "groupbox_norm")
        self.preprocessing_none = self.main_widget.findChild(QRadioButton, "radio_none")
        self.preprocessing_normalize = self.main_widget.findChild(QRadioButton, "radio_normalize")
        self.preprocessing_standardize = self.main_widget.findChild(QRadioButton, "radio_standardize")
        self.preprocessing_axis_features = self.main_widget.findChild(QRadioButton, "radio_axis_features")
        self.preprocessing_axis_samples = self.main_widget.findChild(QRadioButton, "radio_axis_samples")
        self.preprocessing_norm_l1 = self.main_widget.findChild(QRadioButton, "radio_norm_l1")
        self.preprocessing_norm_l2 = self.main_widget.findChild(QRadioButton, "radio_norm_l2")
        self.preprocessing_norm_max = self.main_widget.findChild(QRadioButton, "radio_norm_max")
        self.progressbar = self.main_widget.findChild(QProgressBar, "progressbar")

        self.progressbar.hide()

        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_view.setModel(self.model)

        # chart series

        self.series = QtCharts.QScatterSeries(self.table_view)
        self.series.setName("table")
        self.series.setMarkerSize(15)
        self.series.hovered.connect(self.on_hover)

        self.chart.addSeries(self.series)

        self.mapper = QtCharts.QVXYModelMapper()
        self.mapper.setXColumn(1)
        self.mapper.setYColumn(2)
        self.mapper.setSeries(self.series)
        self.mapper.setModel(self.model)

        # selection series

        self.series_selection = QtCharts.QScatterSeries(self.table_view)
        self.series_selection.setName("selection")
        self.series_selection.setMarkerShape(QtCharts.QScatterSeries.MarkerShapeRectangle)
        self.series_selection.setMarkerSize(15)
        self.series_selection.hovered.connect(self.on_hover)

        self.chart.addSeries(self.series_selection)

        self.mapper_selection = QtCharts.QVXYModelMapper()
        self.mapper_selection.setXColumn(1)
        self.mapper_selection.setYColumn(2)
        self.mapper_selection.setSeries(self.series_selection)
        self.mapper_selection.setModel(self.model_selection)

        # effects

        button_load_data.setGraphicsEffect(self.button_shadow())
        table_cfg_frame.setGraphicsEffect(self.card_shadow())
        pc_frame.setGraphicsEffect(self.card_shadow())

        # signals

        button_load_data.clicked.connect(self.open_file)
        self.table_view.selectionModel().selectionChanged.connect(self.selection_changed)
        self.coins.new_spectrum.connect(self.on_new_spectrum)
        self.legend.returnPressed.connect(self.update_legend)
        self.preprocessing_none.toggled.connect(self.on_preprocessing_changed)
        self.preprocessing_normalize.toggled.connect(self.on_preprocessing_changed)
        self.preprocessing_standardize.toggled.connect(self.on_preprocessing_changed)
        self.preprocessing_axis_features.toggled.connect(self.on_preprocessing_axis_changed)
        self.preprocessing_axis_samples.toggled.connect(self.on_preprocessing_axis_changed)
        self.preprocessing_norm_l1.toggled.connect(self.on_preprocessing_norm_changed)
        self.preprocessing_norm_l2.toggled.connect(self.on_preprocessing_norm_changed)
        self.preprocessing_norm_max.toggled.connect(self.on_preprocessing_norm_changed)

        # event filter

        self.table_view.installEventFilter(self)

    def button_shadow(self):
        effect = QGraphicsDropShadowEffect(self.main_widget)

        effect.setColor(QColor(0, 0, 0, 100))
        effect.setXOffset(1)
        effect.setYOffset(1)
        effect.setBlurRadius(5)

        return effect

    def card_shadow(self):
        effect = QGraphicsDropShadowEffect(self.main_widget)

        effect.setColor(QColor(0, 0, 0, 100))
        effect.setXOffset(2)
        effect.setYOffset(2)
        effect.setBlurRadius(5)

        return effect

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Delete:
                self.remove_selected_rows()

                return True
            elif event.matches(QKeySequence.Copy):
                s_model = self.table_view.selectionModel()

                if s_model.hasSelection():
                    selection_range = s_model.selection().constFirst()

                    table_str = ""
                    clipboard = QGuiApplication.clipboard()

                    for i in range(selection_range.top(), selection_range.bottom() + 1):
                        row_value = []

                        for j in range(selection_range.left(), selection_range.right() + 1):
                            row_value.append(s_model.model().index(i, j).data())

                        table_str += "\t".join(row_value) + "\n"

                    clipboard.setText(table_str)

                return True
            elif event.matches(QKeySequence.Paste):
                s_model = self.table_view.selectionModel()

                if s_model.hasSelection():
                    clipboard = QGuiApplication.clipboard()

                    table_str = clipboard.text()
                    table_rows = table_str.splitlines()  # splitlines avoids an empty line at the end

                    selection_range = s_model.selection().constFirst()

                    first_row = selection_range.top()
                    first_col = selection_range.left()
                    last_col_idx = 0
                    last_row_idx = 0

                    for i in range(len(table_rows)):
                        model_i = first_row + i

                        if model_i < self.model.rowCount():
                            row_cols = table_rows[i].split("\t")

                            for j in range(len(row_cols)):
                                model_j = first_col + j

                                if model_j < self.model.columnCount():
                                    self.model.setData(self.model.index(model_i, model_j), row_cols[j], Qt.EditRole)

                                    if model_j > last_col_idx:
                                        last_col_idx = model_j

                            if model_i > last_row_idx:
                                last_row_idx = model_i

                    first_index = self.model.index(first_row, first_col)
                    last_index = self.model.index(last_row_idx, last_col_idx)

                    self.model.dataChanged.emit(first_index, last_index)

                return True
            else:
                return QObject.eventFilter(self, obj, event)
        else:
            return QObject.eventFilter(self, obj, event)

        return QObject.eventFilter(self, obj, event)

    def add_row(self):
        self.model.append_row()

    def remove_selected_rows(self):
        s_model = self.table_view.selectionModel()

        if s_model.hasSelection():
            index_list = s_model.selectedRows()
            int_index_list = []

            for index in index_list:
                int_index_list.append(index.row())

            self.model.remove_rows(int_index_list)

    def open_file(self):
        file_path = QFileDialog.getOpenFileName(self.main_widget, "Open File", os.path.expanduser("~"),
                                                "Coin Tags (*.csv);; *.* (*.*)")[0]

        if file_path != "":
            t = threading.Thread(target=self.coins.load_file, args=(file_path,), daemon=True)
            t.start()

    def on_new_spectrum(self, spectrum, labels):
        self.progressbar.show()

        t = threading.Thread(target=self.do_pca, args=(spectrum, labels), daemon=True)
        t.start()

    def do_pca(self, spectrum_value, labels):
        spectrum = np.copy(spectrum_value)

        if spectrum.size == 0:
            return

        if self.preprocessing_normalize.isChecked():
            axis_type = 1  # axis = 0 for features(columns) and axis=1 for samples(rows)
            norm_type = "l1"

            if self.preprocessing_axis_features.isChecked():  # features
                axis_type = 0

            if self.preprocessing_norm_l2.isChecked():
                norm_type = "l2"
            elif self.preprocessing_norm_max.isChecked():
                norm_type = "max"

            spectrum = normalize(spectrum, copy=False, axis=axis_type, norm=norm_type)
        elif self.preprocessing_standardize.isChecked():
            axis_type = 1

            if self.preprocessing_axis_features.isChecked():  # features
                axis_type = 0

            spectrum = scale(spectrum, copy=False, axis=axis_type)

        pca = PCA(n_components=2, whiten=False)

        pca.fit(spectrum)

        self.pc1_variance_ratio.setText("{0:.1f}%".format(pca.explained_variance_ratio_[0] * 100))
        self.pc2_variance_ratio.setText("{0:.1f}%".format(pca.explained_variance_ratio_[1] * 100))

        self.pc1_singular_value.setText("{0:.1f} ".format(pca.singular_values_[0]))
        self.pc2_singular_value.setText("{0:.1f} ".format(pca.singular_values_[1]))

        reduced_cartesian = pca.fit_transform(spectrum)

        self.model.beginResetModel()

        self.model.data_name = np.asarray(labels)
        self.model.data_pc1 = reduced_cartesian[:, 0]
        self.model.data_pc2 = reduced_cartesian[:, 1]

        self.model.endResetModel()

        first_index = self.model.index(0, 0)
        last_index = self.model.index(self.model.rowCount() - 1, self.model.columnCount() - 1)

        self.model.dataChanged.emit(first_index, last_index)

        self.progressbar.hide()

    def selection_changed(self, selected, deselected):
        s_model = self.table_view.selectionModel()

        if s_model.hasSelection():
            selection_labels = []
            selection_pc1 = []
            selection_pc2 = []
            indexes = s_model.selectedRows()

            for index in indexes:
                row_idx = index.row()

                selection_labels.append(self.model.data_name[row_idx])
                selection_pc1.append(self.model.data_pc1[row_idx])
                selection_pc2.append(self.model.data_pc2[row_idx])

            # update the model used to show the selected rows

            self.model_selection.beginResetModel()

            self.model_selection.data_name = np.asarray(selection_labels)
            self.model_selection.data_pc1 = np.asarray(selection_pc1)
            self.model_selection.data_pc2 = np.asarray(selection_pc2)

            self.model_selection.endResetModel()

            first_index = self.model_selection.index(0, 0)
            last_index = self.model_selection.index(self.model_selection.rowCount() - 1,
                                                    self.model_selection.columnCount() - 1)

            self.model_selection.dataChanged.emit(first_index, last_index)
        else:
            print("no selection")

    def update_legend(self):
        self.series.setName(self.legend.displayText())

    def on_preprocessing_changed(self, state):
        if state:
            if self.preprocessing_none.isChecked():
                self.groupbox_axis.setEnabled(False)
                self.groupbox_norm.setEnabled(False)

            elif self.preprocessing_normalize.isChecked():
                self.groupbox_axis.setEnabled(True)
                self.groupbox_norm.setEnabled(True)

            elif self.preprocessing_standardize.isChecked():
                self.groupbox_axis.setEnabled(True)
                self.groupbox_norm.setEnabled(False)

            self.progressbar.show()

            t = threading.Thread(target=self.do_pca, args=(self.coins.spectrum, self.coins.labels), daemon=True)
            t.start()

    def on_preprocessing_axis_changed(self, state):
        if state:
            self.progressbar.show()

            t = threading.Thread(target=self.do_pca, args=(self.coins.spectrum, self.coins.labels), daemon=True)
            t.start()

    def on_preprocessing_norm_changed(self, state):
        if state:
            self.progressbar.show()

            t = threading.Thread(target=self.do_pca, args=(self.coins.spectrum, self.coins.labels), daemon=True)
            t.start()

    def on_hover(self, point, state):
        if state:
            dx = np.fabs(self.model.data_pc1 - point.x())
            dy = np.fabs(self.model.data_pc2 - point.y())

            idx_list = np.argwhere((dx < 0.00001) & (dy < 0.00001))

            if len(idx_list) == 1:
                label = self.model.data_name[idx_list[0]][0]

                self.callout.set_text(label)
                self.callout.set_anchor(point)
                self.callout.setZValue(11)
                self.callout.updateGeometry()
                self.callout.show()
        else:
            self.callout.hide()
