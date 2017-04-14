# -*- coding: utf-8 -*-

"""
This file is part of the Note Organizer add-on for Anki

Main Module, hooks add-on methods into Anki

Copyright: (c) Glutanimate 2017
License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

from aqt.qt import *

from aqt.browser import Browser
from aqt.utils import saveHeader, restoreHeader

from anki.hooks import addHook, wrap

from .forms import organizer
from .notetable import NoteTable

HOTKEY_INSERT = "Ctrl+N"
HOTKEY_CUT = "Ctrl+x"
HOTKEY_PASTE = "Ctrl+v"

class Organizer(QDialog):
    """Main dialog"""
    def __init__(self, browser):
        super(Organizer, self).__init__(parent=browser)
        self.browser = browser
        self.mw = browser.mw

        self.context = None

        self.f = organizer.Ui_Dialog()
        self.f.setupUi(self)
        self.table = NoteTable(self)
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
        cutCut = QShortcut(QKeySequence(_(HOTKEY_CUT)), 
                self.table, activated=self.onCutRow)
        pasteCut = QShortcut(QKeySequence(_(HOTKEY_PASTE)), 
                self.table, activated=self.onPasteRow)

    def setupHeaders(self):
        """Restore and setup headers"""
        hh = self.table.horizontalHeader()
        restoreHeader(hh, "organizer")
        hh.setHighlightSections(False)
        hh.setMinimumSectionSize(50)
        hh.setDefaultSectionSize(100)
        hh.setResizeMode(QHeaderView.Interactive)
        hh.setStretchLastSection(True)
        hh.resizeSection(hh.logicalIndex(0), 120)
        hh.resizeSection(hh.logicalIndex(1), 240)
        hh.setMovable(True)
        hh.setClickable(False)
        vh = self.table.verticalHeader()
        vh.setClickable(False)
        vh.setResizeMode(QHeaderView.Fixed)

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
        a = m.addAction("Insert Note\t{}".format(HOTKEY_INSERT))
        a.triggered.connect(self.onInsertNote)
        a = m.addAction("Cut\t{}".format(HOTKEY_CUT))
        a.triggered.connect(self.onCutRow)
        if self.context:
            a = m.addAction("Paste\t{}".format(HOTKEY_PASTE))
            a.triggered.connect(self.onPasteRow)
        m.exec_(gpos)

    def onInsertNote(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return False
        row = sel[-1].row()
        col = self.getNidColumn()
        self.table.insertRow(row)
        self.table.setItem(row,0,QTableWidgetItem("Empty new note"))
        print "insert"

    def onCutRow(self):
        self.context = [1]
        print "cut"

    def onPasteRow(self):
        if not self.context:
            return
        print "pasted"
        self.context = None

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

    def getNidColumn(self):
        """Find Note ID column"""
        col = 0
        cols = self.table.columnCount()
        for idx in range(cols):
            header = self.table.horizontalHeaderItem(idx).text()
            if header == "Note ID":
                col = idx
                break
        return col

    def reject(self):
        """Notify browser of close event"""
        self.browser._organizer = None
        super(Organizer, self).reject()

    def onAccept(self):
        saveHeader(self.table.horizontalHeader(), "organizer")
        
        res = []
        col = self.getNidColumn()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, col)
            if item:
                res.append(item.text())
            else:
                res.append(None)
        print res
        # TODO: Confirmation dialog? ("Full sync necessary")
        # TODO: Restoration point
        self.close()


    def onReject(self):
        self.close()

        
def onBrowserRowChanged(self, current, previous):
    """Sync row position to Rearranger"""
    if not self._organizer:
        return
    nid = str(self.card.nid)
    self._organizer.focusNid(nid)

def onBrowserClose(self, evt):
    """Close with browser"""
    if self._organizer:
        self._organizer.close()

def onRearrange(self):
    """Invoke Rearranger window"""
    if self._organizer:
        self._organizer.show()
        return
    self._organizer = Organizer(self)
    self._organizer.show()


def setupMenu(self):
    """Setup menu entries and hotkeys"""
    self.menRrng = QMenu(_("&Organizer"))
    action = self.menuBar().insertMenu(
                self.mw.form.menuTools.menuAction(), self.menRrng)
    menu = self.menRrng
    menu.addSeparator()
    a = menu.addAction('Reorganize Notes...')
    a.setShortcut(QKeySequence("Ctrl+R"))
    a.triggered.connect(self.onRearrange)


# Hooks, etc.:

Browser._organizer = None
addHook("browser.setupMenus", setupMenu)
Browser.onRearrange = onRearrange
Browser.onRowChanged = wrap(Browser.onRowChanged, onBrowserRowChanged, "after")
Browser.closeEvent = wrap(Browser.closeEvent, onBrowserClose, "before")