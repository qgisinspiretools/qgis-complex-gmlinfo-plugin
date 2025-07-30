from qgis.PyQt.QtGui import QIcon, QColor

from qgis.core import *
from qgis.gui import *

class SelectTool(QgsMapTool):
    def __init__(self, iface, callback):
        QgsMapTool.__init__(self, iface.mapCanvas())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.callback = callback
        self.rubberBand = QgsRubberBand(self.canvas)
        self.rubberBand.setColor(QColor(255, 0, 0, 255))
        self.rubberBand.setFillColor(QColor(255, 0, 0, 0))
        self.rubberBand.setWidth(1)
        self.isEmittingPoint = False

    def canvasPressEvent(self, e):
        self.startPoint = self.toMapCoordinates(e.pos())
        self.endPoint = self.startPoint
        self.isEmittingPoint = True
        self.showRect(self.startPoint, self.endPoint)

    def canvasMoveEvent(self, e):
        if not self.isEmittingPoint:
            return

        self.endPoint = self.toMapCoordinates(e.pos())
        self.showRect(self.startPoint, self.endPoint)

    def canvasReleaseEvent(self, e):
        self.isEmittingPoint = False
        print("[INFO] StartPoint: " + str(self.startPoint.x()) + ", " + str(self.startPoint.y()))
        print("[INFO] EndPoint: " + str(self.endPoint.x()) + ", " + str(self.endPoint.y()))
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        self.getFeaturesInRect(self.startPoint, self.endPoint)

    def showRect(self, startPoint, endPoint):
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        if startPoint.x() == endPoint.x() or startPoint.y() == endPoint.y():
            return

        point1 = QgsPointXY(startPoint.x(), startPoint.y())
        point2 = QgsPointXY(startPoint.x(), endPoint.y())
        point3 = QgsPointXY(endPoint.x(), endPoint.y())
        point4 = QgsPointXY(endPoint.x(), startPoint.y())

        self.rubberBand.addPoint(point1, False)
        self.rubberBand.addPoint(point2, False)
        self.rubberBand.addPoint(point3, False)
        self.rubberBand.addPoint(point4, True)  # true to update canvas
        self.rubberBand.show()

    def getFeaturesInRect(self, startPoint, endPoint):
        rect = QgsRectangle(self.startPoint, self.endPoint)
        layer = self.iface.activeLayer()

        layer.selectByRect(rect)
        self.callback()

    def deactivate(self):
        QgsMapTool.deactivate(self)
        self.deactivated.emit()