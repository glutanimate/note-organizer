# -*- coding: utf-8 -*-

"""
This file is part of the Note Rearranger add-on for Anki

Main Module, hooks add-on methods into Anki

Copyright: Glutanimate 2017
License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

from aqt.qt import *

from aqt.browser import Browser
from anki.hooks import addHook

from .forms import rearranger


class NoteTable(QTableWidget):
    def __init__(self, dialog, browser):
        QTableWidget.__init__(self)

        self.dialog = dialog
        self.browser = browser
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)

        self.setSelectionMode(QAbstractItemView.ExtendedSelection) 
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDragDropMode(QAbstractItemView.InternalMove)

        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        hh = self.horizontalHeader()
        hh.setDefaultSectionSize(100)
        hh.setMinimumSectionSize(100)
        hh.setStretchLastSection(True)

    def dropEvent(self, event):
        if event.source() == self and (event.dropAction() == Qt.MoveAction 
                        or self.dragDropMode() == QAbstractItemView.InternalMove):
            success, row, col, topIndex = self.dropOn(event)
            if success:             
                selRows = self.getSelectedRowsFast()                        

                top = selRows[0]
                # print 'top is %d'%top
                dropRow = row
                if dropRow == -1:
                    dropRow = self.rowCount()
                # print 'dropRow is %d'%dropRow
                offset = dropRow - top
                # print 'offset is %d'%offset

                for i, row in enumerate(selRows):
                    r = row + offset
                    if r > self.rowCount() or r < 0:
                        r = 0
                    self.insertRow(r)
                    # print 'inserting row at %d'%r


                selRows = self.getSelectedRowsFast()
                # print 'selected rows: %s'%selRows

                top = selRows[0]
                # print 'top is %d'%top
                offset = dropRow - top                
                # print 'offset is %d'%offset
                for i, row in enumerate(selRows):
                    r = row + offset
                    if r > self.rowCount() or r < 0:
                        r = 0

                    for j in range(self.columnCount()):
                        # print 'source is (%d, %d)'%(row, j)
                        # print 'item text: %s'%self.item(row,j).text()
                        source = QTableWidgetItem(self.item(row, j))
                        # print 'dest is (%d, %d)'%(r,j)
                        self.setItem(r, j, source)

                # Why does this NOT need to be here?
                # for row in reversed(selRows):
                    # self.removeRow(row)

                event.accept()

        else:
            QTableView.dropEvent(event)                

    def getSelectedRowsFast(self):
        selRows = []
        for item in self.selectedItems():
            if item.row() not in selRows:
                selRows.append(item.row())
        return selRows

    def droppingOnItself(self, event, index):
        dropAction = event.dropAction()

        if self.dragDropMode() == QAbstractItemView.InternalMove:
            dropAction = Qt.MoveAction

        if event.source() == self and event.possibleActions() & Qt.MoveAction and dropAction == Qt.MoveAction:
            selectedIndexes = self.selectedIndexes()
            child = index
            while child.isValid() and child != self.rootIndex():
                if child in selectedIndexes:
                    return True
                child = child.parent()

        return False

    def dropOn(self, event):
        if event.isAccepted():
            return False, None, None, None

        index = QModelIndex()
        row = -1
        col = -1

        if self.viewport().rect().contains(event.pos()):
            index = self.indexAt(event.pos())
            if not index.isValid() or not self.visualRect(index).contains(event.pos()):
                index = self.rootIndex()

        if self.model().supportedDropActions() & event.dropAction():
            if index != self.rootIndex():
                dropIndicatorPosition = self.position(event.pos(), self.visualRect(index), index)

                if dropIndicatorPosition == QAbstractItemView.AboveItem:
                    row = index.row()
                    col = index.column()
                    # index = index.parent()
                elif dropIndicatorPosition == QAbstractItemView.BelowItem:
                    row = index.row() + 1
                    col = index.column()
                    # index = index.parent()
                else:
                    row = index.row()
                    col = index.column()

            if not self.droppingOnItself(event, index):
                # print 'row is %d'%row
                # print 'col is %d'%col
                return True, row, col, index

        return False, None, None, None

    def position(self, pos, rect, index):
        r = QAbstractItemView.OnViewport
        margin = 2
        if pos.y() - rect.top() < margin:
            r = QAbstractItemView.AboveItem
        elif rect.bottom() - pos.y() < margin:
            r = QAbstractItemView.BelowItem 
        elif rect.contains(pos, True):
            r = QAbstractItemView.OnItem

        if r == QAbstractItemView.OnItem and not (self.model().flags(index) & Qt.ItemIsDropEnabled):
            r = QAbstractItemView.AboveItem if pos.y() < rect.center().y() else QAbstractItemView.BelowItem

        return r


class RearrangerDialog(QDialog):
    """Main dialog"""
    def __init__(self, browser):
        super(RearrangerDialog, self).__init__(parent=browser)
        self.browser = browser
        # load qt-designer form:
        self.f = rearranger.Ui_Dialog()
        self.f.setupUi(self)
        self.table = NoteTable(self, browser)
        self.f.tableLayout.addWidget(self.table)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Note ID', 'Sort Field', 'Back'])
        self.f.buttonBox.accepted.connect(self.onAccept)
        self.f.buttonBox.rejected.connect(self.onReject)
        self.fillRows()

    def fillRows(self):
        cids = self.browser.selectedCards()
        self.table.setRowCount(len(cids))
        print cids
        for row, cid in enumerate(cids):
            c = self.browser.col.getCard(cid)
            n = c.note()
            nid = n.id
            txt = self.browser.model.formatQA(n.fields[self.browser.col.models.sortIdx(n.model())])
            data = [str(nid), txt, "null"]
            for col, val in enumerate(data):
                self.table.setItem(row,col,QTableWidgetItem(val))

    def onAccept(self):
        res = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                res.append(item.text())
            else:
                res.append(None)
        print res
        self.close()

    def onReject(self):
        self.close()
        

def onRearrange(self):
    dialog = RearrangerDialog(self)
    dialog.exec_()

def setupMenu(self):
    self.menRrng = QMenu(_("&Rearranger"))
    action = self.menuBar().insertMenu(
                self.mw.form.menuTools.menuAction(), self.menRrng)
    menu = self.menRrng
    menu.addSeparator()
    a = menu.addAction('Rearrange Notes...')
    a.setShortcut(QKeySequence("Ctrl+R"))
    a.triggered.connect(self.onRearrange)

addHook("browser.setupMenus", setupMenu)
Browser.onRearrange = onRearrange