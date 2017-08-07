# -*- coding: utf-8 -*-

"""
This file is part of the Note Organizer add-on for Anki

Main Module, hooks add-on methods into Anki

Copyright: (c) Glutanimate 2017
License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

from __future__ import unicode_literals

import aqt
from aqt.qt import *
from aqt import mw
from aqt.browser import Browser
from aqt.editor import Editor

from anki.hooks import addHook, wrap

from .organizer import Organizer
from .rearranger import Rearranger
from .config import *
from .consts import *


###### Browser
   
def onBrowserRowChanged(self, current, previous):
    """Sync row position to Organizer"""
    if not self.organizer:
        return
    self.organizer.focusNid(self.card.nid)


def onBrowserNoteDeleted(self, _old):
    """Synchronize note deletion to Organizer"""
    if not self.organizer:
        return _old(self)
    nids = self.selectedNotes()
    if not nids:
        return
    ret = _old(self)
    self.organizer.deleteNids(nids)
    return ret

def onBrowserClose(self, evt):
    """Close with browser"""
    if self.organizer:
        self.organizer.close()


def onReorganize(self):
    """Invoke Organizer window"""
    if self.organizer:
        self.organizer.show()
        return
    self.organizer = Organizer(self)
    self.organizer.show()


def setupMenu(self):
    """Setup menu entries and hotkeys"""
    self.menuOrg = QMenu(_("&Organizer"))
    action = self.menuBar().insertMenu(
                self.mw.form.menuTools.menuAction(), self.menuOrg)
    menu = self.menuOrg
    menu.addSeparator()
    a = menu.addAction('Reorganize Notes...')
    a.setShortcut(QKeySequence(HOTKEY_ORGANIZER))
    a.triggered.connect(self.onReorganize)


###### Editor

def onSetNote(self, note, hide=True, focus=False):
    """Hide BACKUP_Field if configured"""
    if not self.note or BACKUP_FIELD not in self.note:
        return
    model = self.note.model()
    flds = self.mw.col.models.fieldNames(model)
    idx = flds.index(BACKUP_FIELD)
    self.web.eval("""
        // hide last fname, field, and snowflake (FrozenFields add-on)
            document.styleSheets[0].addRule(
                'tr:nth-child({0}) .fname, #f{1}, #i{1}', 'display: none;');
        """.format(idx*2+1, idx))


###### Reviewer

menu_entries = [
    {"label": "New Note - &before", "cmd": NEW_NOTE, "offset": 0},
    {"label": "&New Note - after", "cmd": NEW_NOTE, "offset": 1},
    {"label": "D&uplicate Note - before", "cmd": DUPE_NOTE, "offset": 0},
    {"label": "&Duplicate Note - after", "cmd": DUPE_NOTE, "offset": 1},
    {"label": "Duplicate Note (with s&cheduling) - before",
        "cmd": DUPE_NOTE_SCHED, "offset": 0},
    {"label": "Duplicate Note (with &scheduling) - after",
        "cmd": DUPE_NOTE_SCHED, "offset": 1},
]


def addNoteOrganizerActions(web, menu):
    """Add Note Organizer actions to Reviewer Context Menu"""
    if mw.state != "review": # only show menu in reviewer
        return

    menu.addSeparator()
    org_menu = menu.addMenu('&New note...')
    for entry in menu_entries:
        cmd = entry["cmd"]
        offset = entry["offset"] 
        action = org_menu.addAction(entry["label"])
        action.triggered.connect(
            lambda _, c=cmd, o=offset: onReviewerOrgMenu(c, o))


def onReviewerOrgMenu(command, offset):
    """Invoke Rearranger from Reviewer to create new notes"""
    card = mw.reviewer.card
    did = card.odid or card.did # account for dyn decks
    deck = mw.col.decks.nameOrNone(did)
    note = card.note()
    nid = note.id
    
    # rearrange in context of origin deck
    search = "deck:'{}'".format(deck)
    note_pool = mw.col.findNotes(search)
    note_pool.sort()
    try:
        idx = note_pool.index(nid)
    except ValueError: # nid not in deck
        return False
    
    # construct command string that imitates Organizer GUI output
    if command.startswith(NEW_NOTE):
        data = MODEL_SAME
    else:
        data = str(nid)
    composite = command + ": " + data
    note_pool.insert(idx + offset, composite)
    
    start = None
    moved = []

    rearranger = Rearranger(card=card)
    res = rearranger.processNids(note_pool, start, moved)

    # display result in browser
    if REVIEWER_OPEN_BROWSER:
        browser = aqt.dialogs.open("Browser", mw)
        browser.form.searchEdit.lineEdit().setText(search)
        browser.onSearch()
        rearranger.selectNotes(browser, res)


# Hooks, etc.:

addHook("browser.setupMenus", setupMenu)
Browser.onReorganize = onReorganize
Browser.organizer = None

Browser.onRowChanged = wrap(Browser.onRowChanged, onBrowserRowChanged, "after")
Browser.closeEvent = wrap(Browser.closeEvent, onBrowserClose, "before")
Browser.deleteNotes = wrap(Browser.deleteNotes, onBrowserNoteDeleted, "around")

if HIDE_BACKUP_FIELD:
    Editor.setNote = wrap(Editor.setNote, onSetNote, "after")

if REVIEWER_CONTEXT_MENU:
    addHook("AnkiWebView.contextMenuEvent", addNoteOrganizerActions)