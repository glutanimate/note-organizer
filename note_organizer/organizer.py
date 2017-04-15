# -*- coding: utf-8 -*-

"""
This file is part of the Note Organizer add-on for Anki

Organizer dialog

Copyright: (c) Glutanimate 2017
License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

from aqt.qt import *

from aqt.utils import saveHeader, restoreHeader, saveGeom, \
    restoreGeom, askUser, tooltip

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
        # TODO: handle mw.reset events (especially note deletion)
        # TODO: save and restore window dimensions
        super(Organizer, self).__init__(parent=browser)
        self.browser = browser
        self.mw = browser.mw
        self.clipboard = []
        self.f = organizer.Ui_Dialog()
        self.f.setupUi(self)
        self.table = NoteTable(self)
        self.hh = self.table.horizontalHeader()
        self.f.tableLayout.addWidget(self.table)
        self.fillTable()
        self.updateDate()
        self.setupHeaders()
        restoreGeom(self, "organizer")
        self.setupEvents()
        self.table.setFocus()
        # focus currently selected card:
        if self.browser.card:
            self.focusNid(str(self.browser.card.nid))

    def setupEvents(self):
        """Connect event signals to slots"""
        self.table.selectionModel().selectionChanged.connect(self.onRowChanged)
        self.table.cellChanged.connect(self.onCellChanged)
        self.f.buttonBox.rejected.connect(self.onReject)
        self.f.buttonBox.accepted.connect(self.onAccept)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.onTableContext)

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
        self.hh.setMovable(True)
        self.hh.setClickable(False)
        self.hh.setHighlightSections(False)
        self.hh.setMinimumSectionSize(50)
        self.hh.setDefaultSectionSize(100)
        self.hh.setResizeMode(QHeaderView.Interactive)
        self.hh.setStretchLastSection(True)
        self.hh.resizeSection(self.hh.logicalIndex(0), 120)
        self.hh.resizeSection(self.hh.logicalIndex(1), 240)
        restoreHeader(self.hh, "organizer")
        vh = self.table.verticalHeader()
        vh.setClickable(False)
        vh.setResizeMode(QHeaderView.Fixed)
        vh.setDefaultSectionSize(24)
        vh_font = vh.font()
        vh_font.setPointSize(10)
        vh.setFont(vh_font)

    def fillTable(self):
        """Fill table rows with data"""
        b = self.browser
        m = b.model
        t = self.table

        data = []
        notes = []
        nids = []

        # either get selected cards or entire view
        sel = b.selectedCards()
        if sel and len(sel) > 1:
            # need to map nids to actually selected row indexes
            idxs = b.form.tableView.selectionModel().selectedRows()
        else:
            sel = m.cards
            idxs = None

        # sort and eliminate duplicates
        for row, cid in enumerate(sel):
            if idxs:
                row = idxs[row].row()
            c = b.col.getCard(cid)
            nid = c.note().id
            if nid not in nids:
                notes.append((nid, row))
                nids.append(nid)
        notes.sort()

        # get browser model data for rows
        for idx, (nid, row) in enumerate(notes):
            data.append([str(nid)])
            for col, val in enumerate(m.activeCols):
                index = m.index(row, col)
                data[idx].append(m.data(index, Qt.DisplayRole))

        coldict = {key: title for key, title in b.columns}
        headers = [coldict[key] for key in m.activeCols]

        # set table data
        row_count = len(data)
        t.setColumnCount(len(m.activeCols) + 1)
        t.setHorizontalHeaderLabels(["Note ID"] + headers)
        t.setRowCount(row_count)
        self.setWindowTitle("Reorganize Notes ({} notes shown)".format(row_count))

        for row, columns in enumerate(data):
            for col, value in enumerate(columns):
                item = QTableWidgetItem(value)
                f = QFont()
                f.setFamily(self.browser.mw.fontFamily)
                f.setPixelSize(self.browser.mw.fontHeight)
                item.setFont(f)
                t.setItem(row,col,item)


    def onCellChanged(self, row, col):
        if row == col == 0:
            self.updateDate()


    def updateDate(self):
        # TODO: set date bounds to (collection created, today)
        item = self.table.item(0, 0)
        if not item:
            return False
        try:
            nid = int(item.text())
        except ValueError:
            return False
        timestamp = nid / 1000
        qtime = QDateTime()
        qtime.setTime_t(timestamp)
        self.f.dateTimeEdit.setDateTime(qtime)


    def getDate(self):
        qtime = self.f.dateTimeEdit.dateTime()
        timestamp = qtime.toTime_t()
        return timestamp * 1000

    def focusNid(self, nid):
        """Find and select row by note ID"""
        cell = self.table.findItems(nid, Qt.MatchFixedString)
        if cell:
            self.table.setCurrentItem(cell[0])


    def onTableContext(self, pos):
        """Custom context menu for the table"""
        # need to map to viewport due to QAbstractScrollArea:
        gpos = self.table.viewport().mapToGlobal(pos)
        m = QMenu()
        
        a = m.addAction("Cut\t{}".format(HOTKEY_CUT))
        a.triggered.connect(self.onCutRow)
        if self.clipboard:
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


    def onInsertNote(self):
        """Insert empty row"""
        rows = self.table.getSelectedRows()
        if not rows:
            return
        row = rows[0]
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(EMPTY_NOTE))


    def onRemoveNotes(self):
        """Remove empty row(s)"""
        rows = self.table.getSelectedRows()
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
        """Store current selection in clipboard"""
        rows = self.table.getSelectedRows()
        if not rows:
            return
        self.clipboard = rows


    def onPasteRow(self):
        """Paste current selection"""
        # TODO: Needs some refactoring

        t = self.table
        cut = self.clipboard
        if not self.clipboard:
            return
        
        rows = self.table.getSelectedRows()
        if not rows:
            return
        
        new_row = rows[0]
        if new_row == cut[0] or new_row in range(cut[0], cut[-1]+1):
            # return if source and target identical
            # FIXME: support pasting back into the same range
            return False

        # Insert new row and copy data over
        offset = 0
        cols = t.columnCount()
        select = []
        for cut_row in cut[::-1]:
            t.insertRow(new_row)
            if new_row < cut_row:
                offset += 1
            adj_row = cut_row + offset
            # print("moving {} (actual: {}) to {}".format(
            #         cut_row+1, adj_row+1, new_row+1))
            for col in range(cols):
                dupe = QTableWidgetItem(t.item(adj_row, col))
                font = dupe.font()
                font.setBold(True)
                dupe.setFont(font)
                t.setItem(new_row, col, dupe)
                if col == 0:
                    t.modified.append(int(dupe.text()))
            t.clearSelection()

        # Remove old row
        for row in cut[::-1]:
            # print("removing {}".format(row+offset))
            t.removeRow(row+offset)

        # reselect moved rows
        selectionModel = t.selectionModel()
        if new_row > cut[0]:
            index1 = t.model().index(new_row-len(cut), 0)
            index2 = t.model().index(new_row-1, 2)
        else:
            index1 = t.model().index(new_row, 0)
            index2 = t.model().index(new_row+len(cut)-1, 0)
        itemSelection = QItemSelection(index1, index2)
        selectionModel.select(itemSelection, 
            QItemSelectionModel.Rows | QItemSelectionModel.Select)

        self.clipboard = None


    def onRowChanged(self, current, previous):
        """Sync row change to Browser"""
        mods = QApplication.keyboardModifiers()
        if mods & (Qt.ShiftModifier | Qt.ControlModifier):
            return # don't try to focus when multiple items are selected
        rows = self.table.getSelectedRows()
        if not rows:
            return
        item = self.table.item(rows[0], 0)
        if not item:
            return
        nid = item.text()
        cids = self.mw.col.db.list(
                "select id from cards where nid = ? order by ord", nid)
        for cid in cids:
            if cid in self.browser.model.cards:
                self.browser.focusCid(cid)
                break


    def reject(self):
        """Notify browser of close event"""
        self.browser.organizer = None
        saveGeom(self, "organizer")
        saveHeader(self.hh, "organizer")
        super(Organizer, self).reject()


    def onAccept(self):
        modified = self.table.modified
        if not modified:
            self.close()
            tooltip("No changes performed")
            return False

        ret = askUser("This will <b>modify</b> the note creation date of at least "
            "<b>{}</b> notes (a lot more if other notes need to be shuffled, too)."
            "<br><br>Are you sure you want to proceed?".format(len(modified)),
            parent=self, defaultno=True, title="Please confirm changes")
        if not ret:
            return False

        res = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if not item: # should not happen
                continue
            text = item.text()
            try:
                val = int(text)
            except ValueError:
                val = text
            res.append(val)
        
        start = self.getDate()

        self.close()

        rearranger = Rearranger(self.browser, modified)
        rearranger.rearrange(res, start)


    def onReject(self):
        self.close()
