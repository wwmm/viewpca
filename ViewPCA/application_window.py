# -*- coding: utf-8 -*-

import os

import numpy as np
from PySide2.QtCharts import QtCharts
from PySide2.QtCore import QFile, QObject, Qt
from PySide2.QtGui import QBrush, QColor, QPainter, QPen
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import (QFileDialog, QFrame, QGraphicsDropShadowEffect,
                               QGraphicsEllipseItem, QLabel, QPushButton,
                               QTabWidget)

from ViewPCA.table import Table


class ApplicationWindow(QObject):
    def __init__(self):
        QObject.__init__(self)

        self.module_path = os.path.dirname(__file__)

        self.mouse_pressed = False
        self.mouse_pressed_x = 0
        self.mouse_pressed_y = 0
        self.tables = []
        self.group_markers = []

        # loading widgets from designer file

        loader = QUiLoader()

        loader.registerCustomWidget(QtCharts.QChartView)

        self.window = loader.load(self.module_path + "/ui/application_window.ui")

        self.tab_widget = self.window.findChild(QTabWidget, "tab_widget")
        chart_frame = self.window.findChild(QFrame, "chart_frame")
        chart_cfg_frame = self.window.findChild(QFrame, "chart_cfg_frame")
        self.chart_view = self.window.findChild(QtCharts.QChartView, "chart_view")
        button_add_tab = self.window.findChild(QPushButton, "button_add_tab")
        button_reset_zoom = self.window.findChild(QPushButton, "button_reset_zoom")
        button_save_image = self.window.findChild(QPushButton, "button_save_image")
        self.label_mouse_coords = self.window.findChild(QLabel, "label_mouse_coords")

        # Creating QChart
        self.chart = QtCharts.QChart()
        self.chart.setAnimationOptions(QtCharts.QChart.AllAnimations)
        self.chart.setTheme(QtCharts.QChart.ChartThemeLight)
        self.chart.setAcceptHoverEvents(True)

        self.axis_x = QtCharts.QValueAxis()
        self.axis_x.setTitleText("PC1")
        self.axis_x.setRange(-10, 10)
        self.axis_x.setLabelFormat("%.1f")

        self.axis_y = QtCharts.QValueAxis()
        self.axis_y.setTitleText("PC2")
        self.axis_y.setRange(-10, 10)
        self.axis_y.setLabelFormat("%.1f")

        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)

        self.chart_view.setChart(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        # self.chart_view.setRubberBand(QtCharts.QChartView.RectangleRubberBand)

        # 1 tab by default

        self.add_tab()

        # custom stylesheet

        style_file = QFile(self.module_path + "/ui/custom.css")
        style_file.open(QFile.ReadOnly)

        self.window.setStyleSheet(style_file.readAll().data().decode("utf-8"))

        style_file.close()

        # effects

        self.tab_widget.setGraphicsEffect(self.card_shadow())
        chart_frame.setGraphicsEffect(self.card_shadow())
        chart_cfg_frame.setGraphicsEffect(self.card_shadow())
        button_add_tab.setGraphicsEffect(self.button_shadow())
        button_reset_zoom.setGraphicsEffect(self.button_shadow())
        button_save_image.setGraphicsEffect(self.button_shadow())

        # signal connection

        self.tab_widget.tabCloseRequested.connect(self.remove_tab)
        button_add_tab.clicked.connect(self.add_tab)
        button_reset_zoom.clicked.connect(self.reset_zoom)
        button_save_image.clicked.connect(self.save_image)

        # override signal slot

        self.chart_view.mousePressEvent = self.on_mouse_press
        self.chart_view.mouseReleaseEvent = self.on_mouse_release
        self.chart_view.mouseMoveEvent = self.on_mouse_move

        # show window

        self.window.show()

    def button_shadow(self):
        effect = QGraphicsDropShadowEffect(self.window)

        effect.setColor(QColor(0, 0, 0, 100))
        effect.setXOffset(1)
        effect.setYOffset(1)
        effect.setBlurRadius(5)

        return effect

    def card_shadow(self):
        effect = QGraphicsDropShadowEffect(self.window)

        effect.setColor(QColor(0, 0, 0, 100))
        effect.setXOffset(2)
        effect.setYOffset(2)
        effect.setBlurRadius(5)

        return effect

    def add_tab(self):
        table = Table(self.chart)

        # data series

        table.series.attachAxis(self.axis_x)
        table.series.attachAxis(self.axis_y)

        # table selection series

        table.series_selection.attachAxis(self.axis_x)
        table.series_selection.attachAxis(self.axis_y)

        # signals

        table.model.dataChanged.connect(self.update_scale)
        table.new_mouse_coords.connect(self.on_new_mouse_coords)

        # add table

        self.tables.append(table)

        table.series.setName("table " + str(len(self.tables)))

        self.tab_widget.addTab(table.main_widget, "table " + str(len(self.tables)))

    def remove_tab(self, index):
        widget = self.tab_widget.widget(index)

        self.tab_widget.removeTab(index)

        for t in self.tables:
            if t.main_widget == widget:
                self.chart.removeSeries(t.series)
                self.chart.removeSeries(t.series_selection)

                self.tables.remove(t)

                self.update_scale()

                break

    def update_scale(self):
        n_tables = len(self.tables)

        if n_tables > 0:
            Xmin, Xmax, Ymin, Ymax = self.tables[0].model.get_min_max_xy()

            if n_tables > 1:
                for n in range(n_tables):
                    xmin, xmax, ymin, ymax = self.tables[n].model.get_min_max_xy()

                    if xmin < Xmin:
                        Xmin = xmin

                    if xmax > Xmax:
                        Xmax = xmax

                    if ymin < Ymin:
                        Ymin = ymin

                    if ymax > Ymax:
                        Ymax = ymax

            fraction = 0.15
            self.axis_x.setRange(Xmin - fraction * np.fabs(Xmin), Xmax + fraction * np.fabs(Xmax))
            self.axis_y.setRange(Ymin - fraction * np.fabs(Ymin), Ymax + fraction * np.fabs(Ymax))

    def save_image(self):
        home = os.path.expanduser("~")

        path = QFileDialog.getSaveFileName(self.window, "Save Image",  home, "PNG (*.png)")[0]

        if path != "":
            if not path.endswith(".png"):
                path += ".png"

            pixmap = self.chart_view.grab()

            pixmap.save(path)

    def reset_zoom(self):
        self.remove_group_markers()
        self.chart.zoomReset()

    def on_new_mouse_coords(self, point):
        self.label_mouse_coords.setText("x = {0:.6f}, y = {1:.6f}".format(point.x(), point.y()))

    def on_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_pressed = True

            ellipsis = QGraphicsEllipseItem(self.chart)

            ellipsis.setZValue(12)
            ellipsis.setBrush(QBrush(QColor(244, 67, 54, 50)))
            ellipsis.setPen(QPen(Qt.transparent))

            self.group_markers.append(ellipsis)

            self.mouse_pressed_x, self.mouse_pressed_y = event.x(), event.y()
        elif event.button() == Qt.MouseButton.RightButton:
            x, y = event.x(), event.y()

            for marker in self.group_markers:
                if marker.rect().contains(x, y):
                    marker.hide()

                    self.group_markers.remove(marker)

    def on_mouse_release(self, event):
        self.mouse_pressed = False

    def on_mouse_move(self, event):
        if self.mouse_pressed:
            x, y = event.x(), event.y()

            width = x - self.mouse_pressed_x
            height = y - self.mouse_pressed_y

            self.group_markers[-1].setRect(self.mouse_pressed_x, self.mouse_pressed_y, width, height)

    def remove_group_markers(self):
        for marker in self.group_markers:
            marker.hide()

        self.group_markers.clear()
