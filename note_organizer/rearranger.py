# -*- coding: utf-8 -*-

"""
This file is part of the Note Organizer add-on for Anki

Note rearranger module

Copyright: (c) Glutanimate 2017
License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

from anki.errors import AnkiError

from aqt import mw
from aqt.utils import tooltip
from config import *

class Rearranger:
    """Performs the actual database reorganization"""

    def __init__(self, browser, moved):
        self.browser = browser
        self.moved = moved


    def rearrange(self, nids, start):
        """Adjust nid order"""
        modified = []
        # Full database sync required:
        try:
            mw.col.modSchema(check=True)
        except AnkiError:
            tooltip("Reorganization aborted.")
            return False
        # Create checkpoint
        mw.checkpoint("Reorganize notes")

        print("\n" * 4)

        last = 0
        for idx, nid in enumerate(nids):

            try:
                nxt = nids[idx+1]
            except IndexError:
                nxt = None

            try:
                nid = int(nid)
            except ValueError:
                vals = nid.split(": ")
                if not vals or len(vals) < 2: # should not happen
                    continue
                action = vals[0]
                if action == DEL_NOTE:
                    nid = int(vals[1])
                    self.removeNote()
                    continue
                elif action == NEW_NOTE:
                    ntype = "".join(vals[1:])
                    nid = self.addNote(last, ntype)

            if not nxt: # have to do this after processing new notes
                nxt = nid +1

            if not self.noteExists(nid): # note deleted
                continue

            # check if order as expected
            if last != 0 and last < nid < nxt:
                # above check won't work if we moved an entire block,
                # so we need to check against all remaining indices
                # (excluding the ones that we know have been moved)
                if not any(nid>i for i in nids[idx:] if i not in self.moved):
                    last = nid
                    continue

            if last != 0:
                new_nid = last + 1 # regular nids
            elif start and start != nid:
                new_nid = start # first nid, date changed
            else:
                last = nid # first nid, date unmodified
                continue
            
            if BACKUP_NIDS:
                self.backupOriginalNid(nid)
            new_nid = self.updateNidSafely(nid, new_nid)

            print("==================================")
            print("last", last)
            print("current", nid)
            print("next", nxt)
            print("->new", new_nid)

            if nid in self.moved:
                modified.append(new_nid)

            last = new_nid

        mw.reset()
        self.selectNotes(modified)
        tooltip("Reorganized {} notes.".format(len(modified)))


    def addNote(self, last, ntype):
        pass

    def removeNote(self, nid):
        self.col.remNotes([nid])


    def noteExists(self, nid):
        """Checks the database to see whether the nid is actually assigned"""
        return mw.col.db.scalar("""
select id from notes where id = ?""", nid)


    def updateNidSafely(self, nid, new_nid):
        """Update nid while ensuring that timestamp doesn't already exist"""
        while self.noteExists(new_nid):
            new_nid += 1

        # Update note row
        mw.col.db.execute(
            """update notes set id=? where id = ?""", new_nid, nid)

        # Update card rows
        mw.col.db.execute(
            """update cards set nid=? where nid = ?""", new_nid, nid)

        return new_nid


    def backupOriginalNid(self, nid):
        """Store original NID in a predefined field (if available)"""
        note = mw.col.getNote(int(nid))
        if BACKUP_FIELD in note and not note[BACKUP_FIELD]:
            note[BACKUP_FIELD] = str(nid)
        note.flush()


    def getDeck(self):
        pass


    def createNewNote(self):
        pass


    def selectNotes(self, nids):
        """Select browser entries by note id"""
        sm = self.browser.form.tableView.selectionModel()
        sm.clear()
        cids = []
        for nid in nids:
            cids += mw.col.db.list(
                "select id from cards where nid = ? order by ord", nid)
        self.browser.model.selectedCards = {cid: True for cid in cids}
        self.browser.model.restoreSelection()
