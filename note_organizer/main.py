# -*- coding: utf-8 -*-

"""
This file is part of the Note Organizer add-on for Anki

Main Module, hooks add-on methods into Anki

Copyright: (c) Glutanimate 2017
License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

from aqt.qt import *
from aqt.browser import Browser

from anki.hooks import addHook, wrap

from .organizer import Organizer

HOTKEY_ORGANIZER = "Ctrl+R"
   
def onBrowserRowChanged(self, current, previous):
    """Sync row position to Organizer"""
    if not self.organizer:
        return
    nid = str(self.card.nid)
    self.organizer.focusNid(nid)


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


# Hooks, etc.:

addHook("browser.setupMenus", setupMenu)
Browser.onReorganize = onReorganize
Browser.organizer = None

Browser.onRowChanged = wrap(Browser.onRowChanged, onBrowserRowChanged, "after")
Browser.closeEvent = wrap(Browser.closeEvent, onBrowserClose, "before")
