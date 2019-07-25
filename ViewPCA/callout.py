# -*- coding: utf-8 -*-

from PySide2.QtCore import QPoint, QPointF, QRect, QRectF, Qt, qAbs
from PySide2.QtGui import QColor, QFont, QFontMetrics, QPainterPath
from PySide2.QtWidgets import QGraphicsItem


class Callout(QGraphicsItem):
    """
        This class code was taken from \
        https://code.qt.io/cgit/qt/qtcharts.git/tree/examples/charts/callout/callout.cpp?h=5.13
    """

    def __init__(self, chart):
        QGraphicsItem.__init__(self, chart)

        self.chart = chart
        self.rect = QRectF()
        self.anchor = QPointF()
        self.text_rect = QRectF()
        self.text = ""
        self.font = QFont()

    def boundingRect(self):
        anchor = self.mapFromParent(self.chart.mapToPosition(self.anchor))

        rect = QRectF()

        rect.setLeft(min(self.rect.left(), anchor.x()))
        rect.setRight(max(self.rect.right(), anchor.x()))
        rect.setTop(min(self.rect.top(), anchor.y()))
        rect.setBottom(max(self.rect.bottom(), anchor.y()))

        return rect

    def paint(self, painter, option, widget):
        path = QPainterPath()

        path.addRoundedRect(self.rect, 5, 5)

        anchor = self.mapFromParent(self.chart.mapToPosition(self.anchor))

        if not self.rect.contains(anchor):
            point1 = QPointF()
            point2 = QPointF()

            # establish the position of the anchor point in relation to m_rect
            above = anchor.y() <= self.rect.top()
            aboveCenter = anchor.y() > self.rect.top() and anchor.y() <= self.rect.center().y()
            belowCenter = anchor.y() > self.rect.center().y() and anchor.y() <= self.rect.bottom()
            below = anchor.y() > self.rect.bottom()

            onLeft = anchor.x() <= self.rect.left()
            leftOfCenter = anchor.x() > self.rect.left() and anchor.x() <= self.rect.center().x()
            rightOfCenter = anchor.x() > self.rect.center().x() and anchor.x() <= self.rect.right()
            onRight = anchor.x() > self.rect.right()

            # get the nearest m_rect corner

            x = (onRight + rightOfCenter) * self.rect.width()
            y = (below + belowCenter) * self.rect.height()
            cornerCase = (above and onLeft) or (above and onRight) or (below and onLeft) or (below and onRight)
            vertical = qAbs(anchor.x() - x) > qAbs(anchor.y() - y)

            x1 = x + leftOfCenter * 10 - rightOfCenter * 20 + cornerCase * (not vertical) * (onLeft * 10 - onRight * 20)
            y1 = y + aboveCenter * 10 - belowCenter * 20 + cornerCase * vertical * (above * 10 - below * 20)

            x2 = x + leftOfCenter * 20 - rightOfCenter * 10 + cornerCase * (not vertical) * (onLeft * 20 - onRight * 10)
            y2 = y + aboveCenter * 20 - belowCenter * 10 + cornerCase * vertical * (above * 20 - below * 10)

            point1.setX(x1)
            point1.setY(y1)
            point2.setX(x2)
            point2.setY(y2)

            path.moveTo(point1)
            path.lineTo(anchor)
            path.lineTo(point2)

            path = path.simplified()

        painter.setBrush(QColor(255, 255, 255))
        painter.drawPath(path)
        painter.drawText(self.text_rect, self.text)

    def set_anchor(self, point):
        self.anchor = point

    def updateGeometry(self):
        self.prepareGeometryChange()

        self.setPos(self.chart.mapToPosition(self.anchor) + QPoint(10, -50))

    def set_text(self, text):
        self.text = text

        metrics = QFontMetrics(self.font)

        self.text_rect = metrics.boundingRect(QRect(0, 0, 150, 150), Qt.AlignLeft, self.text)

        self.text_rect.translate(5, 5)

        self.prepareGeometryChange()

        self.rect = QRectF(self.text_rect.adjusted(-5.0, -5.0, 5.0, 5.0))
