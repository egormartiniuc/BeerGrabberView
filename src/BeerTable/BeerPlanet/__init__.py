

import base64
import hashlib
import datetime
from collections import OrderedDict


from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QTableView
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QStandardItem
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtGui import QKeySequence
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QPainter
from PyQt5.QtGui import QPen
from PyQt5.QtGui import QBrush
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QMimeData
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QEvent
from PyQt5.QtCore import QModelIndex
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import QDate

from BeerGrabber.utils import CRC64
from BeerGrabber.utils import ReadWriteFile
from BeerGrabber.beerplanet import BeerPlanetGrabber

Version = [0, 0, 1]

class BeerItem(QStandardItem):
    def __init__(self, value, parent=None):
        super().__init__(parent)
        self.setData(value, Qt.DisplayRole)
        

class BeerModel(QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent or self

class PopupLable(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent or self
        self.setWindowFlags(Qt.Popup)
        self.setVisible(False)
    
    def mousePressEvent(self, event):
        self.setVisible(False)
        return QLabel.mousePressEvent(self, event)
    
class ImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent or self
        self.setMouseTracking(True)
    
    def mouseMoveEvent(self, event):
        return QLabel.mouseMoveEvent(self, event)
                    

class BeerTable(QTableView):
    def __init__(self, model, beergraber, parent=None):
        super().__init__(parent)
        self._parent = parent or self
        self._model = model
        self.setModel(self._model)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setMouseTracking(True)
        self.viewport().setAttribute(Qt.WA_Hover, True)
        self.setWindowTitle('BeerPlanet')
        
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.headerMenu)
        self.horizontalHeader().setSectionsMovable(True)
        
        self._index = None
        self._pos = self.cursor().pos()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.updateTimer)
        self._timer.start(1000)
        
        self._top_rowid = -1
        self._bottom_rowid = -1
        
        self._label = PopupLable(self)
        
        self._beergraber = beergraber
        self._beergraber.start()
        
        self.lastError = None
        self.beers = OrderedDict()
        self.beerImages = OrderedDict()
                                                    

        self.origFields = OrderedDict([(0, 'name'), 
            (1, 'type'), (2, 'Accessory:'), (3, 'Alcohol:'), (4, 'Awards:'), (5, 'Brewery:'), 
            (6, 'Color:'), (7, 'Country:'), (8, 'Hop:'), (9, 'IBU:'), 
            (10, 'Malt:'), (11, 'Plato:'), (12, 'Rating:'), (13, 'Recipes:'), 
            (14, 'Served:'), (15, 'Type:'), (16, 'Description'), (-1, 'Id')])
        self.tableFields = [-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
        self.loadBeers()
        
    def updateTimer(self):
        if (self.isActiveWindow() and
            self._pos == self.cursor().pos() and 
            (not self._label.isVisible())):
            index = self.indexAt(self._pos)
            if index.column() == 0:
                beerId = int(self.model().data(index, Qt.DisplayRole))
                for pos in self.beerImages.get(beerId, []):
                    if pos == 1:
                        pixmap = QPixmap()
                        pixmap.loadFromData(self.beerImages[beerId][pos])
                        self._label.setPixmap(pixmap)
                        self._label.move(self._pos)
                        self._label.setVisible(True)
                        break
        self._pos = self.cursor().pos()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self.resizeRowsToContents()
            self._top_rowid = self.indexAt(self.rect().topLeft()).row()
            self._bottom_rowid = self.indexAt(self.rect().bottomRight()).row()
        elif event.key() == Qt.Key_D and event.modifiers() & Qt.ControlModifier and self.currentIndex():
            rowId = self.currentIndex().row()
            r = [self.model().item(rowId, colId).text() for colId in [1,2,4,5,6,8,13,14]]
            cb = QApplication.clipboard()
            cb.clear(mode=cb.Clipboard )
            cb.setText(chr(9).join(r), mode=cb.Clipboard)
        elif (event.key() == Qt.Key_C or event.key() == Qt.Key_S) and event.modifiers() & Qt.ControlModifier and self.currentIndex():
            rowId = self.currentIndex().row()
            beerId = int(self.model().item(rowId, 0).text())
            if beerId in self.beerImages:
                IBU = str()
                if int(self.model().item(rowId, 14).text()) > 0:
                    IBU = bytes([73, 66, 85, 32, 123, 125]).decode().format(
                        self.model().item(rowId, 14).text())
                r = [self.model().item(rowId, 1).text(),
                     self.model().item(rowId, 2).text(),
                    chr(32).join([
                        bytes([65, 66, 86, 32, 123, 125, 32, 37]).decode().format(
                            self.model().item(rowId, 4).text()),
                        IBU,
                    ]),
                    chr(32).join([self.model().item(rowId, 7).text(), chr(40),
                        self.model().item(rowId, 5).text(), chr(41)]),
                ]
                pixmap = self._pixmap(open(self.beerImages[beerId][0], 
                    ReadWriteFile.READ_BINARY).read(), None)
                height = pixmap.size().height()
                width = pixmap.size().width()
                p = QPixmap(width, height + 12*len(r))
                height = p.size().height()
                width = p.size().width()
                with QPainter(p) as painter:
                    painter.drawPixmap(0, 12*len(r), pixmap)
                    brush = QBrush(QColor(0, 0, 0, 255))
                    painter.fillRect(0, 0, p.size().width()-2, 12*len(r), brush)
                    font = QFont()
                    font.setFamily(bytes([65, 114, 105, 97, 108]).decode())
                    font.setBold(True)
                    font.setPixelSize(10)
                    painter.setFont( font )
                    pen = QPen()
                    pen.setColor(QColor(255, 255, 0, 255))
                    painter.setPen(pen)
                    for i, info in enumerate(r, 1):
                        painter.drawText( QPoint(2, i*10), info )
                if event.key() == Qt.Key_C:
                    QApplication.clipboard().clear()
                    QApplication.clipboard().setPixmap(p)
                else:
                    fileName, _ = QFileDialog.getSaveFileName(self, 
                        bytes([83, 97, 118, 101, 32, 73, 109, 97, 103, 101]).decode(),
                        str(beerId), 
                        bytes([73, 109, 97, 103, 101, 32, 40, 42, 46, 106, 112, 103, 41]).decode())
                    print(fileName)
                    p.save(fileName, bytes([74, 80, 71]).decode())
        return QTableView.keyPressEvent(self, event)
            
    def Clear(self):
        self.model().clear()
        self.model().setColumnCount(len(self.tableFields))
        self.model().setHorizontalHeaderLabels([self.origFields[i] for i in self.tableFields])
    
    def toNumber(self, value):
        if isinstance(value, int):
            return float(value)
        if isinstance(value, float):
            return value
        for sign in ['%', 'P']:
            value = value.replace(sign, '').strip()
        if value.isdigit():
            return float(int(value))
        elif value.count(',') == 1 and value.replace(',', '').isdigit():
            return float(value.replace(',', '.'))
        elif value.count('.') == 1 and value.replace('.', '').isdigit():
            return float(value)
        return -1.
    
    def toInteger(self, value):
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if '%' in value:
            value = value.replace('%', '').strip()
        if value.isdigit():
            return int(value)
        elif value.count(',') == 1 and value.replace(',', '').isdigit():
            return int(float(value.replace(',', '.')))
        elif value.count('.') == 1 and value.replace('.', '').isdigit():
            return int(float(value))
        return -1
    
    def toDate(self, value):
        return QDate(datetime.datetime.strptime(value.replace(chr(32), str()), '%m/%d/%Y'))
    
    def _pixmap(self, dataBytes, h=200, w=150):
        pixmap = QPixmap()
        pixmap.loadFromData(dataBytes)
        if h is None or w is None:
            return pixmap
        height = pixmap.size().height()
        width = pixmap.size().width()
        if width == 0 or height == 0:
            return pixmap
        return pixmap.scaled(w, h,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation)
    
    def loadBeers(self):
        
        self.beers.clear()
        self.beerImages.clear()
        self.Clear()
        
        while self._beergraber.is_alive():
            self._beergraber.join(1)
        _, rows = self._beergraber.beerRows() 
        
        rowId = -1
        for row in rows:
            row[3] = self.toNumber(row[3])
            row[9] = self.toNumber(row[9])
            row[11] = self.toNumber(row[11])
            row[12] = self.toNumber(row[12])
            
            r_ = [row[i] for i in self.tableFields if i>-1]
            id_ = CRC64(str(r_))
            rowId += 1
            r_.insert(0, str(id_))
            self.model().appendRow(list(map(BeerItem, r_)))
            
            for index, image_path in enumerate(row[17]):
                if not image_path: continue
                image_path = os.path.basename(image_path)
                image_path = os.path.join(self._beergraber.imageExportPath, image_path)
                if os.path.exists(image_path):
                    b = open(image_path, ReadWriteFile.READ_BINARY).read()
                    if id_ not in self.beerImages:
                        self.beerImages[id_] = OrderedDict()
                    self.beerImages[id_][index] = image_path
                    if rowId < 10000:
                        label = ImageLabel()
                        label.setPixmap(self._pixmap(b))
                        index = self.model().index(rowId, 0)
                        self.setIndexWidget(index, label)
                    break
            
            if row[16]:
                widget = QTextEdit()
                widget.setText(row[16])
                index = self.model().index(rowId, self.tableFields.index(16))
                self.setIndexWidget(index, widget)
        print('Loaded:', rowId)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
    
    def showEvent(self, event):
        self._top_rowid = self.indexAt(self.rect().topLeft()).row()
        self._bottom_rowid = self.indexAt(self.rect().bottomRight()).row()
    
    def closeEvent(self, event):
        self.Clear()
    
    def mousePressEvent(self, event):
        self._pos = event.pos()
        if event.button() == Qt.RightButton:
            index = self.indexAt(self._pos)
            if index.column() == 0:
                beerId = int(self.model().data(index, Qt.DisplayRole))
                if beerId in self.beerImages:
                    for pos in self.beerImages[beerId]:
                        if pos == 0:
                            b = open(self.beerImages[beerId][pos], 
                                ReadWriteFile.READ_BINARY).read()
                            pixmap = QPixmap()
                            pixmap.loadFromData(b)
                            self._label.setPixmap(pixmap)
                            self._label.move(self._pos)
                            self._label.setVisible(True)
                            break
        return QTableView.mousePressEvent(self, event)
        
    def mouseMoveEvent(self, event):
        pos = event.pos()
        index = self.indexAt(pos)
        if self._index is None:
            self.enterIndex(index)
        elif self._index != index:
            self.leaveIndex(self._index)
            self.enterIndex(index)
        else:
            self.moveIndex(index)
        self._index = index
        self._pos = pos
        return QTableView.mouseMoveEvent(self, event)
    
    def image_mouseMoveEvent(self, event):
        pass
    
    def event(self, event):
        return QTableView.event(self, event)
    
    def enterIndex(self, index):
        self._label.setVisible(False)
    
    def leaveIndex(self, index):
        self._label.setVisible(False)
    
    def moveIndex(self, index):
        self._label.setVisible(False)
    
    def headerMenu(self, point):
        globalPos = self.mapToGlobal(point)
        column = self.horizontalHeader().visualIndexAt(point.x())
        
        names = ["Contains",
        "Starts With",
        "Equals...", 
        "Does not Equal...",
        "Greater Than",
        "Less Than",
        "Between",
        "Clear filter"]
        menu = QMenu()
        for name in names:
            menu.addAction(name)
        selectedItem = menu.exec_(globalPos)
        
        if selectedItem and selectedItem.text() == names[7]:
            self.filterClear()
        elif selectedItem:
            value, status = QInputDialog.getText(self, "Custom filter", "Value:")
            if status:
                if selectedItem.text() == names[0]:
                    self.filterColumnValueContains(column, value)
                elif selectedItem.text() == names[1]:
                    self.filterColumnValueStartsWith(column, value)
                elif selectedItem.text() == names[2]:
                    self.filterColumnValueEqual(column, value)
                elif selectedItem.text() == names[3]:
                    self.filterColumnValueEqualNo(column, value)
                elif selectedItem.text() == names[4]:
                    self.filterColumnValueGreaterThan(column, value)
                elif selectedItem.text() == names[5]:
                    self.filterColumnValueLessThan(column, value)
                elif selectedItem.text() == names[6]:
                    pass
    
    def isDigital(self, v):
        return v.isdigit() or ('.' in v and v.count('.') == 1)
    
    def toDigital(self, v):
        if v.isdigit():
            return int(v)
        elif '.' in v and v.count('.') == 1:
            return round(float(v), 6)
        return v
    
    def filterClear(self):
        for i in range(self.model().rowCount()):
            if self.isRowHidden(i):
                self.setRowHidden(i, False)
    
    def filterColumnValueContains(self, column, value):
        if value == str():
            self.filterClear()
        else:
            value = value.upper()
            for rowId in range(self.model().rowCount()):
                v = self.model().item(rowId, column).data(Qt.DisplayRole)
                if v is None:
                    self.setRowHidden(rowId, True)
                elif v.upper().__contains__(value):
                    self.setRowHidden(rowId, False)
                else:
                    self.setRowHidden(rowId, True)
    
    def filterColumnValueStartsWith(self, column, value):
        if value == str():
            self.filterClear()
        else:
            value = value.upper()
            for rowId in range(self.model().rowCount()):
                v = self.model().item(rowId, column).data(Qt.DisplayRole)
                if v is None:
                    self.setRowHidden(rowId, True)
                elif v.upper().startswith(value):
                    self.setRowHidden(rowId, False)
                else:
                    self.setRowHidden(rowId, True)
    
    def filterColumnValueEqual(self, column, value):
        if value == str():
            self.filterClear()
        elif self.isDigital(value):
            ivalue = self.toDigital(value)
            for rowId in range(self.model().rowCount()):
                v = self.model().item(rowId, column).data(Qt.DisplayRole)
                if v is None:
                    self.setRowHidden(rowId, True)
                elif isinstance(v, int):
                    if v == ivalue:
                        self.setRowHidden(rowId, False)
                    else:
                        self.setRowHidden(rowId, True)
                elif isinstance(v, float):
                    if round(v, 6) == ivalue:
                        self.setRowHidden(rowId, False)
                    else:
                        self.setRowHidden(rowId, True)
                else:
                    if v == value:
                        self.setRowHidden(rowId, False)
                    else:
                        self.setRowHidden(rowId, True)
        else:
            for rowId in range(self.model().rowCount()):
                v = self.model().item(rowId, column).data(Qt.DisplayRole)
                if v is None:
                    self.setRowHidden(rowId, True)
                    self.__frozenTableView.setRowHidden(rowId, True)
                elif v == value:
                    self.setRowHidden(rowId, False)
                    self.__frozenTableView.setRowHidden(rowId, False)
                else:
                    self.setRowHidden(rowId, True)
                    self.__frozenTableView.setRowHidden(rowId, True)
    
    def filterColumnValueEqualNo(self, column, value):
        if value == str():
            self.filterClear()
        elif self.isDigital(value):
            ivalue = self.toDigital(value)
            for rowId in range(self.model().rowCount()):
                v = self.model().item(rowId, column).data(Qt.DisplayRole)
                if v is None:
                    self.setRowHidden(rowId, True)
                elif isinstance(v, int):
                    if v != ivalue:
                        self.setRowHidden(rowId, False)
                    else:
                        self.setRowHidden(rowId, True)
                elif isinstance(v, float):
                    if round(v, 6) != ivalue:
                        self.setRowHidden(rowId, False)
                    else:
                        self.setRowHidden(rowId, True)
                else:
                    if v != value:
                        self.setRowHidden(rowId, False)
                    else:
                        self.setRowHidden(rowId, True)
        else:
            for rowId in range(self.model().rowCount()):
                v = self.model().item(rowId, column).data(Qt.DisplayRole)
                if v is None:
                    self.setRowHidden(rowId, True)
                elif v == value:
                    self.setRowHidden(rowId, True)
                else:
                    self.setRowHidden(rowId, False)
                    
    def filterColumnValueGreaterThan(self, column, value):
        if value == str():
            self.filterClear()
        elif self.isDigital(value):
            ivalue = self.toDigital(value)
            for rowId in range(self.model().rowCount()):
                v = self.model().item(rowId, column).data(Qt.DisplayRole)
                if v is None:
                    self.setRowHidden(rowId, True)
                elif (isinstance(v, int) or isinstance(v, float)):
                    if v > ivalue:
                        self.setRowHidden(rowId, False)
                    else:
                        self.setRowHidden(rowId, True)
                else:
                    if v > value:
                        self.setRowHidden(rowId, False)
                    else:
                        self.setRowHidden(rowId, True)
        else:
            for rowId in range(self.model().rowCount()):
                v = self.model().item(rowId, column).data(Qt.DisplayRole)
                if v is None:
                    self.setRowHidden(rowId, True)
                elif v > value:
                    self.setRowHidden(rowId, False)
                else:
                    self.setRowHidden(rowId, True)
    
    def filterColumnValueLessThan(self, column, value):
        if value == str():
            self.filterClear()
        elif self.isDigital(value):
            ivalue = self.toDigital(value)
            for rowId in range(self.model().rowCount()):
                v = self.model().item(rowId, column).data(Qt.DisplayRole)
                if v is None:
                    self.setRowHidden(rowId, True)
                    self.__frozenTableView.setRowHidden(rowId, True)
                elif (isinstance(v, int) or isinstance(v, float)):
                    if v < ivalue:
                        self.setRowHidden(rowId, False)
                    else:
                        self.setRowHidden(rowId, True)
                else:
                    if v < value:
                        self.setRowHidden(rowId, False)
                    else:
                        self.setRowHidden(rowId, True)
        else:
            for rowId in range(self.model().rowCount()):
                v = self.model().item(rowId, column).data(Qt.DisplayRole)
                if v is None:
                    self.setRowHidden(rowId, True)
                elif v < value:
                    self.setRowHidden(rowId, False)
                else:
                    self.setRowHidden(rowId, True)
    
        


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import os
    
    app = QApplication([])
    
    proxy = {}
    path = os.path.join('..', '..', 'BeerPlanet')
    
    wnd = BeerTable(BeerModel(), 
        BeerPlanetGrabber(path, proxy, update_all=False))
    wnd.showMaximized()
    app.exec()
    