# -*- coding: utf-8 -*-

"""
This file is part of the Note Organizer add-on for Anki

Note table widget

Copyright: (c) Glutanimate 2017
License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

from aqt.qt import *

class NoteTable(QTableWidget):
    """Custom QTableWidget with drag-and-drop support"""
    # adapted from http://stackoverflow.com/a/26311179
    def __init__(self, dialog):
        QTableWidget.__init__(self)

        self.dialog = dialog
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)

        self.setSelectionMode(QAbstractItemView.ExtendedSelection) 
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDragDropMode(QAbstractItemView.InternalMove)

        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.moved = []


    def dropEvent(self, event):
        if event.source() == self and (event.dropAction() == Qt.MoveAction 
                        or self.dragDropMode() == QAbstractItemView.InternalMove):
            success, row, col, topIndex = self.dropOn(event)
            if success:             
                selRows = self.getSelectedRows()                        

                top = selRows[0]
                dropRow = row
                if dropRow == -1:
                    dropRow = self.rowCount()
                offset = dropRow - top

                for i, row in enumerate(selRows):
                    r = row + offset
                    if r > self.rowCount() or r < 0:
                        r = 0
                    self.insertRow(r)

                selRows = self.getSelectedRows()

                top = selRows[0]
                offset = dropRow - top                
                for i, row in enumerate(selRows):
                    r = row + offset
                    if r > self.rowCount() or r < 0:
                        r = 0

                    for col in range(self.columnCount()):
                        dupe = QTableWidgetItem(self.item(row, col))
                        font = dupe.font()
                        font.setBold(True)
                        dupe.setFont(font)
                        self.setItem(r, col, dupe)
                        if col == 0:
                            value = dupe.text()
                            if value not in self.moved:
                                self.moved.append(value)

                event.accept()

        else:
            QTableView.dropEvent(event)                


    def getSelectedRows(self):
        sel = self.selectionModel().selectedRows()
        if not sel:
            return None
        return [i.row() for i in sel]


    def droppingOnItself(self, event, index):
        dropAction = event.dropAction()

        if self.dragDropMode() == QAbstractItemView.InternalMove:
            dropAction = Qt.MoveAction

        if (event.source() == self and 
                event.possibleActions() & Qt.MoveAction 
                and dropAction == Qt.MoveAction):
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
                elif dropIndicatorPosition == QAbstractItemView.BelowItem:
                    row = index.row() + 1
                    col = index.column()
                else:
                    row = index.row()
                    col = index.column()

            if not self.droppingOnItself(event, index):
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