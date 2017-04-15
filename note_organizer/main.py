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

   
def onBrowserRowChanged(self, current, previous):
    """Sync row position to Organizer"""
    if not self._organizer:
        return
    nid = str(self.card.nid)
    self._organizer.focusNid(nid)

def onBrowserClose(self, evt):
    """Close with browser"""
    if self._organizer:
        self._organizer.close()

def onReorganize(self):
    """Invoke Organizer window"""
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
    a.triggered.connect(self.onReorganize)


# Hooks, etc.:

Browser._organizer = None
addHook("browser.setupMenus", setupMenu)
Browser.onReorganize = onReorganize

Browser.onRowChanged = wrap(Browser.onRowChanged, onBrowserRowChanged, "after")
Browser.closeEvent = wrap(Browser.closeEvent, onBrowserClose, "before")