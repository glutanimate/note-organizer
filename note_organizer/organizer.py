# -*- coding: utf-8 -*-

"""
This file is part of the Note Organizer add-on for Anki

Organizer dialog

Copyright: (c) Glutanimate 2017
License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

from aqt.qt import *

from aqt.utils import saveHeader, restoreHeader

from .forms import organizer
from .notetable import NoteTable
from .rearranger import Rearranger

HOTKEY_INSERT = "Ctrl+N"
HOTKEY_REMOVE = "Del"
HOTKEY_CUT = "Ctrl+X"
HOTKEY_PASTE = "Ctrl+V"

#########

EMPTY_NOTE = "Empty note"

class Organizer(QDialog):
    """Main dialog"""
    def __init__(self, browser):
        super(Organizer, self).__init__(parent=browser)
        self.browser = browser
        self.mw = browser.mw

        self._context = None
        self._modified = []

        self.f = organizer.Ui_Dialog()
        self.f.setupUi(self)
        self.table = NoteTable(self)
        self.hh = self.table.horizontalHeader()
        self.f.tableLayout.addWidget(self.table)
        self.fillTable()
        self.setupHeaders()
        self.setupEvents()
        self.table.setFocus()


        # TODO: handle mw.reset events (especially note deletion)

    def setupEvents(self):
        self.table.cellClicked.connect(self.onCellClicked)
        self.f.buttonBox.rejected.connect(self.onReject)
        self.f.buttonBox.accepted.connect(self.onAccept)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.onRowContext)

        insCut = QShortcut(QKeySequence(_(HOTKEY_INSERT)), 
                self.table, activated=self.onInsertNote)
        delCut = QShortcut(QKeySequence(_(HOTKEY_REMOVE)), 
                self.table, activated=self.onRemoveNotes)
        cutCut = QShortcut(QKeySequence(_(HOTKEY_CUT)), 
                self.table, activated=self.onCutRow)
        pasteCut = QShortcut(QKeySequence(_(HOTKEY_PASTE)), 
                self.table, activated=self.onPasteRow)

    def setupHeaders(self):
        """Restore and setup headers"""
        restoreHeader(self.hh, "organizer")
        self.hh.setHighlightSections(False)
        self.hh.setMinimumSectionSize(50)
        self.hh.setDefaultSectionSize(100)
        self.hh.setResizeMode(QHeaderView.Interactive)
        self.hh.setStretchLastSection(True)
        self.hh.resizeSection(self.hh.logicalIndex(0), 120)
        self.hh.resizeSection(self.hh.logicalIndex(1), 240)
        self.hh.setMovable(True)
        self.hh.setClickable(False)
        vh = self.table.verticalHeader()
        vh.setClickable(False)
        vh.setResizeMode(QHeaderView.Fixed)
        vh.setDefaultSectionSize(24)
        vh_font = vh.font()
        vh_font.setPointSize(10)
        vh.setFont(vh_font)

    def fillTable(self):
        """Fill table rows with data"""
        model = self.browser.model
        t = self.table
        data = []
        notes = []
        nids = []

        # either get selected cards or entire view
        sel = self.browser.selectedCards()
        if not sel or len(sel) < 2:
            sel = model.cards

        # sort and eliminate duplicates
        for row, cid in enumerate(sel):
            c = self.browser.col.getCard(cid)
            nid = c.note().id
            if nid not in nids:
                notes.append((nid, row))
                nids.append(nid)
        notes.sort()

        # get browser model data for rows
        for idx, (nid, row) in enumerate(notes):
            data.append([str(nid)])
            for col, val in enumerate(model.activeCols):
                index = model.index(row, col)
                # We suppose data are strings
                data[idx].append(model.data(index, Qt.DisplayRole))

        coldict = {key: title for key, title in self.browser.columns}
        headers = [coldict[key] for key in model.activeCols]

        # set table data
        t.setColumnCount(len(model.activeCols) + 1)
        t.setHorizontalHeaderLabels(["Note ID"] + headers)
        t.setRowCount(len(data))
        for row, columns in enumerate(data):
            for col, value in enumerate(columns):
                t.setItem(row,col,QTableWidgetItem(value))


    def focusNid(self, nid):
        """Find and select row by note ID"""
        cell = self.table.findItems(nid, Qt.MatchFixedString)
        if cell:
            self.table.setCurrentItem(cell[0])


    def onRowContext(self, pos):
        """Custom context menu for the table"""
        # need to map to viewport due to QAbstractScrollArea
        gpos = self.table.viewport().mapToGlobal(pos)
        m = QMenu()
        
        a = m.addAction("Cut\t{}".format(HOTKEY_CUT))
        a.triggered.connect(self.onCutRow)
        if self._context:
            a = m.addAction("Paste\t{}".format(HOTKEY_PASTE))
            a.triggered.connect(self.onPasteRow)

        a = m.addAction("Insert empty note\t{}".format(HOTKEY_INSERT))
        a.triggered.connect(self.onInsertNote)
        
        sel = self.table.selectionModel().selectedRows()
        if sel:
            row = sel[-1].row()
            item = self.table.item(row, 0)
            if item and item.text() == EMPTY_NOTE:
                a = m.addAction("Remove empty note(s)\t{}".format(HOTKEY_REMOVE))
                a.triggered.connect(self.onRemoveNotes)

        m.exec_(gpos)

    def getSelectedRows(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        return [i.row() for i in sel]

    def onInsertNote(self):
        rows = self.getSelectedRows()
        if not rows:
            return
        row = rows[0]
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(EMPTY_NOTE))
        print "insert"


    def onRemoveNotes(self):
        rows = self.getSelectedRows()
        if not rows:
            return
        to_remove = []
        for row in rows:
            item = self.table.item(row, 0)
            if not item or not item.text() == EMPTY_NOTE:
                continue
            to_remove.append(row)
        for row in to_remove[::-1]: # in reverse to avoid updating idxs
            self.table.removeRow(row)


    def onCutRow(self):
        rows = self.getSelectedRows()
        if not rows:
            return
        self._context = rows


    def onPasteRow(self):
        # TODO: in dire need of refactoring

        t = self.table
        cut = self._context

        if not self._context:
            return
        rows = self.getSelectedRows()
        if not rows:
            return
        
        new_row = rows[0]
        if new_row == cut[0] or new_row in range(cut[0], cut[-1]+1):
            # FIXME: support pasting back into the same range
            return False

        offset = 0
        cols = t.columnCount()
        select = []

        for cut_row in cut[::-1]:
            t.insertRow(new_row)
            if new_row < cut_row:
                offset += 1
            adj_row = cut_row + offset
            # print "moving {} (actual: {}) to {}".format(
            #         cut_row+1, adj_row+1, new_row+1)
            for col in range(cols):
                dupe = QTableWidgetItem(t.item(adj_row, col))
                font = dupe.font()
                font.setBold(True)
                dupe.setFont(font)
                t.setItem(new_row, col, dupe)
                if col == 0:
                    self._modified.append(int(dupe.text()))
            t.clearSelection()


        for row in cut[::-1]:
            # print "removing {}".format(row+offset)
            t.removeRow(row+offset)

        selectionModel = t.selectionModel()
        if new_row > cut[0]:
            index1 = t.model().index(new_row-len(cut), 0)
            index2 = t.model().index(new_row-1, 2)
        else:
            index1 = t.model().index(new_row, 0)
            index2 = t.model().index(new_row+len(cut)-1, 0)
        itemSelection = QItemSelection(index1, index2)
        selectionModel.select(itemSelection, QItemSelectionModel.Rows | QItemSelectionModel.Select)

        self._context = None

    def onCellClicked(self, row, col):
        """Sync row change to Browser"""
        mods = QApplication.keyboardModifiers()
        if mods & (Qt.ShiftModifier | Qt.ControlModifier):
            return # nothing to focus when multiple items are selected
        item = self.table.item(row, 0)
        if not item:
            return
        nid = item.text()
        cids = self.mw.col.db.list(
                "select id from cards where nid = ? order by ord", nid)
        cid = None
        for c in cids:
            if c in self.browser.model.cards:
                cid = c
                break
        if cid:
            self.browser.focusCid(cid)

    def reject(self):
        """Notify browser of close event"""
        self.browser._organizer = None
        saveHeader(self.hh, "organizer")
        super(Organizer, self).reject()

    def onAccept(self):   
        res = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                res.append(int(item.text()))
            else:
                res.append(None)
        
        # TODO: Confirmation dialog? ("Full sync necessary")
        # TODO: Restoration point
        self.close()
        rearranger = Rearranger(self.browser, self._modified)
        rearranger.rearrange(res)


    def onReject(self):
        self.close()