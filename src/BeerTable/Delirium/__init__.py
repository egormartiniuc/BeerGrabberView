

import base64
from collections import OrderedDict

from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QTableView
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtGui import QPen
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QBrush
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QPainter
from PyQt5.QtGui import QStandardItem
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QEvent
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import QModelIndex


from PyQt5.QtSql import QSqlDatabase
from PyQt5.QtSql import QSqlQuery
from PyQt5.QtSql import QSqlRecord

from BeerGrabber.utils import CRC64
from BeerGrabber.utils import ReadWriteFile


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
    def __init__(self, model, database, parent=None):
        super().__init__(parent)
        self._parent = parent or self
        self._model = model
        self.setModel(self._model)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setMouseTracking(True)
        self.viewport().setAttribute(Qt.WA_Hover, True)
        
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.headerMenu)
        
        self._index = None
        self._pos = self.cursor().pos()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.updateTimer)
        self._timer.start(1000)
        
        self._label = PopupLable(self)
        
        self._database = database
        self._db = QSqlDatabase('QSQLITE')
        self._db.setDatabaseName(self._database)
        self._q = None
        self.lastError = None
        self.beers = OrderedDict()
        self.beerImages = OrderedDict()
        self.tableFields = ['Image', 'name', 'alcohol', 'quantity', 
            'producer', 'country', 'overview']
        self.loadBeers()
    
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
            try:
                rowId = self.currentIndex().row()
                beerId = int(self.model().item(rowId, 0).text())
                if beerId in self.beerImages:
                    status = []
                    if self.model().item(rowId, 6).text() != bytes([110, 111, 32, 115, 99, 111, 114, 101]).decode():
                        status.append(self.model().item(rowId, 6).text())
                    if self.model().item(rowId, 8).text() != bytes([110, 111, 32, 115, 99, 111, 114, 101]).decode():
                        status.append(self.model().item(rowId, 8).text())
                    if self.model().item(rowId, 8).text() == self.model().item(rowId, 6).text():
                        if self.model().item(rowId, 6).text() != bytes([110, 111, 32, 115, 99, 111, 114, 101]).decode():
                            status = [self.model().item(rowId, 8).text()]
                    r = [self.model().item(rowId, 1).text(),
                         self.model().item(rowId, 2).text(),
                        chr(32).join([
                            bytes([65, 66, 86, 32, 123, 125, 32, 37]).decode().format(
                                self.model().item(rowId, 4).text()),
                        ]+status),
                        chr(32).join([
                            self.model().item(rowId, 13).text(), chr(40),
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
            except Exception as err:
                print(err)
        return QTableView.keyPressEvent(self, event)
    
    def updateTimer(self):
        if (self.isActiveWindow() and
            self._pos == self.cursor().pos() and 
            (not self._label.isVisible())):
            index = self.indexAt(self._pos)
            if index.column() == 0:
                i = int(self.model().data(index, Qt.DisplayRole))
                for pos in self.beerImages[i]:
                    if pos == 1:
                        pixmap = QPixmap()
                        pixmap.loadFromData(self.beerImages[i][pos])
                        self._label.setPixmap(pixmap)
                        self._label.move(self._pos)
                        self._label.setVisible(True)
                        break
        self._pos = self.cursor().pos()
        
    def Clear(self):
        self.model().clear()
        self.model().setColumnCount(len(self.tableFields))
        self.model().setHorizontalHeaderLabels(self.tableFields)
        
    def dbIter(self, sql):
        if self._q is not None:
            if self._q.exec(sql):
                has_next = self._q.next
                get_record = self._q.record
                qrange = range(0)
                if has_next():
                    record = get_record()
                    record_name = record.fieldName
                    record_value = record.value
                    qrange = range(record.count())
                    yield [record_name(i) for i in qrange]
                    yield [record_value(i) for i in qrange]
                    while has_next():
                        record = get_record()
                        record_value = record.value
                        yield [record_value(i) for i in qrange]
            else:
                self.lastError = self.__query.lastError().text()
    
    def normText(self, value):
        text = ''
        i = 0
        for c in value:
            i += 1
            if i > 90 and c == ' ':
                text += c + '\n'
                i = 0
            else:
                text += c
        return text
    
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
        self.Clear()
        if self._db.open():
            self._q = QSqlQuery(self._db)
            sqliter = self.dbIter('SELECT [id], [name], [source_page] FROM beers')
            _ = sqliter.__next__()
            for id_, name, page in sqliter:
                self.beers[id_] = [page, name]
                self.beerImages[id_] = OrderedDict()
            sqliter = self.dbIter('SELECT [id], [name], [alcohol], [quantity], [producer], [country], [overview] FROM beer_info')
            _ = sqliter.__next__()
            for id_, name, alcohol, quantity, producer, country, overview in sqliter:
                overview = self.normText(overview)
                self.beers[id_].extend([alcohol, quantity, producer, country, overview]) 
            sqliter = self.dbIter('SELECT [id], [name], [index], [image] FROM beer_images')
            _ = sqliter.__next__()
            for id_, _, index, image in sqliter:
                b = base64.b64decode(image.encode())
                self.beerImages[id_][index] = b
            for rowId, id_ in enumerate(self.beers):
                r = [id_] + self.beers[id_][1:]
                self.model().appendRow(list(map(BeerItem, r)))
                widget = QTextEdit()
                widget.setText(r[-1])
                index = self.model().index(rowId, 6)
                self.setIndexWidget(index, widget)
                if self.beerImages[id_]:
                    indexs = list(self.beerImages[id_])
                    b = self.beerImages[id_][indexs[0]]
                    pixmap = self._pixmap(b)
                    label = ImageLabel()
                    label.setPixmap(pixmap)
                    index = self.model().index(rowId, 0)
                    self.setIndexWidget(index, label)
            self._db.close()
            self.resizeColumnsToContents()
            self.resizeRowsToContents()
        self._q = None
    
    def closeEvent(self, event):
        self.Clear()
    
    def mousePressEvent(self, event):
        self._pos = event.pos()
        if event.button() == Qt.RightButton:
            index = self.indexAt(self._pos)
            if index.column() == 0:
                i = int(self.model().data(index, Qt.DisplayRole))
                for pos in self.beerImages[i]:
                    if pos == 1:
                        pixmap = QPixmap()
                        pixmap.loadFromData(self.beerImages[i][pos])
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
        
        if not selectedItem:
            return
        
        if selectedItem.text() == names[7]:
            self.filterClear()
        else:
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
            value = value.lower()
            for rowId in range(self.model().rowCount()):
                if self.isRowHidden(rowId):
                    continue
                v = self.model().item(rowId, column).data(Qt.DisplayRole).lower()
                if v is None:
                    self.setRowHidden(rowId, True)
                elif v.__contains__(value):
                    self.setRowHidden(rowId, False)
                else:
                    self.setRowHidden(rowId, True)
    
    def filterColumnValueStartsWith(self, column, value):
        if value == str():
            self.filterClear()
        else:
            for rowId in range(self.model().rowCount()):
                if self.isRowHidden(rowId):
                    continue
                v = self.model().item(rowId, column).data(Qt.DisplayRole)
                if v is None:
                    self.setRowHidden(rowId, True)
                elif v.startswith(value):
                    self.setRowHidden(rowId, False)
                else:
                    self.setRowHidden(rowId, True)
    
    def filterColumnValueEqual(self, column, value):
        if value == str():
            self.filterClear()
        elif self.isDigital(value):
            ivalue = self.toDigital(value)
            for rowId in range(self.model().rowCount()):
                if self.isRowHidden(rowId):
                    continue
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
                if self.isRowHidden(rowId):
                    continue
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
                if self.isRowHidden(rowId):
                    continue
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
                if self.isRowHidden(rowId):
                    continue
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
                if self.isRowHidden(rowId):
                    continue
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
                if self.isRowHidden(rowId):
                    continue
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
                if self.isRowHidden(rowId):
                    continue
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
                if self.isRowHidden(rowId):
                    continue
                v = self.model().item(rowId, column).data(Qt.DisplayRole)
                if v is None:
                    self.setRowHidden(rowId, True)
                elif v < value:
                    self.setRowHidden(rowId, False)
                else:
                    self.setRowHidden(rowId, True)
    
        


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication([])
    wnd = BeerTable(BeerModel(), '../../BeerDelirium/beerdata.db')
    wnd.showMaximized()
    app.exec()