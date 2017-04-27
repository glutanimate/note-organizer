# -*- coding: utf-8 -*-

"""
This file is part of the Note Organizer add-on for Anki

Organizer dialog

Copyright: (c) Glutanimate 2017
License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

from timeit import default_timer as timer

from anki.hooks import addHook, remHook

from aqt.qt import *

from aqt.utils import saveHeader, restoreHeader, saveGeom, \
    restoreGeom, askUser, tooltip

from .forms import organizer
from .notetable import NoteTable
from .rearranger import Rearranger
from .config import *


class Organizer(QDialog):
    """Main dialog"""
    def __init__(self, browser):
        super(Organizer, self).__init__(parent=browser)
        self.browser = browser
        self.mw = browser.mw
        self.f = organizer.Ui_Dialog()
        self.f.setupUi(self)
        self.table = NoteTable(self)
        self.hh = self.table.horizontalHeader()
        self.f.tableLayout.addWidget(self.table)
        self.oldnids = []
        self.clipboard = []
        self.setupUi()
        addHook("reset", self.onReset)


    def setupUi(self):
        print("=====Performance benchmark=====")
        start = timer()
        self.fillTable()
        end = timer()
        print("total", end - start)    
        self.setupDate()
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

        s = QShortcut(QKeySequence(_(HOTKEY_INSERT)), 
                self.table, activated=self.onInsertNote)
        s = QShortcut(QKeySequence(_(HOTKEY_DUPE)), 
                self.table, activated=self.onDuplicateNote)
        s = QShortcut(QKeySequence(_(HOTKEY_REMOVE)), 
                self.table, activated=self.onRemoveNotes)
        s = QShortcut(QKeySequence(_(HOTKEY_CUT)), 
                self.table, activated=self.onCutRow)
        s = QShortcut(QKeySequence(_(HOTKEY_PASTE)), 
                self.table, activated=self.onPasteRow)

        # Sets up context sub-menu and hotkeys for various note types
        self.models_menu = self.setupModels()

    def setupDate(self):
        """Set up datetime range"""
        qtime = QDateTime()
        qtime.setTime_t(0)
        self.f.date.setMinimumDateTime(qtime)
        self.f.date.setMaximumDateTime(QDateTime.currentDateTime())


    def setupModels(self):
        models = [mod['name'] for mod in self.mw.col.models.all()]
        models.sort()
        mm = QMenu("New note...")
        for idx, model in enumerate(models):
            label = model
            if idx < 10:
                modifier = "Ctrl"
            elif idx < 20:
                modifier = "Ctrl+Shift"
            elif idx < 30:
                modifier = "Ctrl+Alt+Shift"
            else:
                modifier = None
            if modifier:
                hotkey = u"{}+{}".format(modifier, str((idx+1) % 10))
                label = label + "\t" + hotkey
                sc = QShortcut(QKeySequence(hotkey), 
                    self.table, activated=lambda a=model: self.onInsertNote(a))
            a = mm.addAction(label)
            a.triggered.connect(lambda _, a=model: self.onInsertNote(a))
        return mm


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
        mcol = m.activeCols
        mcolcnt = len(m.activeCols)

        # either get selected cards or entire view
        sel = b.selectedCards()
        if sel and len(sel) > 1:
            # need to map nids to actually selected row indexes
            idxs = b.form.tableView.selectionModel().selectedRows()
        else:
            sel = m.cards
            idxs = None

        # eliminate duplicates, get data, and sort it by nid
        start = timer()
        for row, cid in enumerate(sel):
            if idxs:
                row = idxs[row].row()
            c = m.cardObjs.get(cid, None)
            if not c:
                c = m.col.getCard(cid)
                m.cardObjs[cid] = c
            nid = c.note().id
            if nid in nids:
                continue
            data_row = [str(nid)]
            for col in range(mcolcnt):
                index = m.index(row, col)
                data_row.append(m.data(index, Qt.DisplayRole))
            nids.append(nid)
            data.append(data_row)
        data.sort()
        self.oldnids = [i[0] for i in data]

        end = timer()
        print("getdata", end - start) 

        # set table data
        start = timer()
        coldict = dict(b.columns)
        headers = ["Note ID"] + [coldict[key] for key in mcol]
        row_count = len(data)
        t.setRowCount(row_count)
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)

        for row, columns in enumerate(data):
            for col, value in enumerate(columns):
                item = QTableWidgetItem(value)
                f = QFont()
                f.setFamily(b.mw.fontFamily)
                f.setPixelSize(b.mw.fontHeight)
                item.setFont(f)
                t.setItem(row,col,item)

        end = timer()
        print("setdata", end - start)

        self.setWindowTitle("Reorganize Notes ({} notes shown)".format(row_count))


    def onCellChanged(self, row, col):
        """Update datetime display when (0,0) changed"""
        if row == col == 0:
            self.updateDate()


    def updateDate(self):
        """Update datetime based on (0,0) value"""
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
        self.f.date.setDateTime(qtime)


    def getDate(self):
        """Get datetime"""
        qtime = self.f.date.dateTime()
        if not qtime.isValid():
            return None
        timestamp = qtime.toTime_t()
        return timestamp


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

        a = m.addAction("New note\t{}".format(HOTKEY_INSERT))
        a.triggered.connect(self.onInsertNote)

        a = m.addAction("Duplicate note\t{}".format(HOTKEY_DUPE))
        a.triggered.connect(self.onDuplicateNote)

        m.addMenu(self.models_menu)

        a = m.addAction("Remove\t{}".format(HOTKEY_REMOVE))
        a.triggered.connect(self.onRemoveNotes)

        m.exec_(gpos)


    def onInsertNote(self, model=None):
        """Insert marker for new note"""
        rows = self.table.getSelectedRows()
        if not rows:
            return
        row = rows[0] + 1
        self.table.insertRow(row)
        if not model:
            model = MODEL_SAME
        data = u"{}: {}".format(NEW_NOTE, model)
        item = QTableWidgetItem(data)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        item.setForeground(Qt.darkGreen)
        self.table.setItem(row, 0, item)


    def onDuplicateNote(self):
        """Insert marker for duplicated note"""
        rows = self.table.getSelectedRows()
        if not rows:
            return
        row = rows[0]
        new_row = row+1
        self.table.insertRow(new_row)
        for col in range(self.table.columnCount()):
            if col == 0:
                value = self.table.item(row, 0).text()
                nid = ''.join(i for i in value if i.isdigit())
                if value.startswith(DEL_NOTE) or not nid:
                    self.table.removeRow(new_row)
                    return
                data = u"{}: {}".format(DUPE_NOTE, nid)
                dupe = QTableWidgetItem(data)
                font = dupe.font()
                font.setBold(True)
                dupe.setFont(font)
                dupe.setForeground(Qt.darkBlue)
            else:
                dupe = QTableWidgetItem(self.table.item(row, col))
            self.table.setItem(new_row, col, dupe)


    def onRemoveNotes(self):
        """Remove empty row(s)"""
        rows = self.table.getSelectedRows()
        if not rows:
            return
        to_remove = []
        delmark = u"{}: ".format(DEL_NOTE)
        for row in rows:
            item = self.table.item(row, 0)
            if not item:
                continue
            value = item.text()
            # New notes:
            if value.startswith((NEW_NOTE, DUPE_NOTE)): # remove
                to_remove.append(row)
                continue
            # Existing notes:
            if value.startswith(delmark): # remove deletion mark
                new = value.replace(delmark, "")
                item.setText(u"{}".format(new))
                font = item.font()
                font.setBold(False)
                item.setFont(font)
                item.setForeground(QBrush())
            else: # apply deletion mark
                item.setText(u"{}: {}".format(DEL_NOTE, value))
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(Qt.darkRed)
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
                    value = dupe.text()
                    if value not in t.moved:
                        t.moved.append(value)
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
        if ": " in nid: # ignore action markers
            nid = nid.split(": ")[1]
        cids = self.mw.col.db.list(
                "select id from cards where nid = ? order by ord", nid)
        for cid in cids:
            if cid in self.browser.model.cards:
                self.browser.focusCid(cid)
                break


    def deleteNids(self, nids):
        """Find and delete row by note ID"""
        for nid in nids:
            nid = str(nid)
            cells = self.table.findItems(nid, Qt.MatchEndsWith)
            if cells:
                row = cells[0].row()
                self.table.removeRow(row)


    def focusNid(self, nid):
        """Find and select row by note ID"""
        nid = str(nid)
        cells = self.table.findItems(nid, Qt.MatchEndsWith)
        if cells:
            self.table.setCurrentItem(cells[0])


    def onReset(self):
        self.clipboard = []
        self.fillTable()
        self.updateDate()
        if self.browser.card:
            self.focusNid(str(self.browser.card.nid))


    def cleanup(self):
        remHook("reset", self.onReset)


    def reject(self):
        """Notify browser of close event"""
        self.cleanup()
        self.browser.organizer = None
        saveGeom(self, "organizer")
        saveHeader(self.hh, "organizer")
        super(Organizer, self).reject()


    def onAccept(self):
        """Ask for confirmation, then call rearranger"""
        newnids = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if not item: # should not happen
                continue
            newnids.append(item.text())

        if newnids == self.oldnids:
            self.close()
            tooltip("No changes performed")
            return False

        moved = []
        for i in self.table.moved:
            try:
                moved.append(int(i))
            except ValueError: # only add existing notes to moved
                pass

        nn = newnids
        to_delete = len([i for i in nn if i.startswith(DEL_NOTE)])
        to_add = len([i for i in nn if i.startswith((NEW_NOTE, DUPE_NOTE))])
        to_move = len(moved)

        if not ASK_CONFIRMATION:
            pass
        else:
            ret = askUser("Overview of <b>changes</b>:"
                "<ul style='margin-left: 0'>"
                "<li><b>Move</b> at least <b>{}</b> note(s)"
                "<br>(other notes might have to be moved alongside)</li>"
                "<li><b>Remove {}</b> note(s)</li>"
                "<li><b>Create {}</b> new note(s)</li></ul>"
                "Are you sure you want to <b>proceed</b>?".format(to_move, to_delete, to_add),
                parent=self, defaultno=True, title="Please confirm action")
            if not ret:
                return False
          
        start = self.getDate() # TODO: identify cases where only date modified

        self.close()

        rearranger = Rearranger(self.browser, moved)
        rearranger.rearrange(newnids, start)


    def onReject(self):
        self.close()
