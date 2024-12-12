from PySide2 import QtWidgets, QtCore, QtGui
 
class ShotLoadUI(QtWidgets.QWidget):
 
    def updateValue(self):
        pass
 
    def paintEvent(self, e):
        painter = QtGui.QPainter(self)
 
        # We can define brushes (draws filled areas) and pens (draws borders)
        yellow_brush = QtGui.QBrush()
        yellow_brush.setColor(QtGui.QColor('yellow'))
        yellow_brush.setStyle(QtCore.Qt.SolidPattern)
 
        black_brush = QtGui.QBrush()
        black_brush.setColor(QtGui.QColor('black'))
        black_brush.setStyle(QtCore.Qt.SolidPattern)
 
        black_pen = QtGui.QPen()
        black_pen.setColor(QtGui.QColor('black'))
        black_pen.setWidth(5)
 
        # Now we can set our brush and pen and start drawing
        painter.setPen(black_pen)
        painter.setBrush(yellow_brush)
        painter.drawEllipse(0, 0, 100, 100)
 
        painter.setBrush(QtCore.Qt.NoBrush)  # This removed the brush (fill)
        painter.drawArc(25, 55, 50, 15, 16*-15, 16*-165)
     
        painter.setBrush(black_brush)
        painter.drawChord(25, 35, 10, 10, 16*0, 16*180)
        painter.drawChord(65, 35, 10, 10, 16*0, 16*180)
 
    def makeUI(self):
        return self
 
    def sizeHint(self):
        return QtCore.QSize(self.size().width(), 100) 
