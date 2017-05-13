# -*- coding: utf-8 -*-

"""
This file is part of the Note Organizer add-on for Anki

Note rearranger module

Copyright: (c) Glutanimate 2017
License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

from anki.errors import AnkiError

from aqt.utils import tooltip
from config import *

class Rearranger:
    """Performs the actual database reorganization"""

    def __init__(self, browser):
        self.browser = browser
        self.mw = self.browser.mw
        self.nid_map = {}


    def processNids(self, nids, start, moved):
        # Full database sync required:
        try:
            self.mw.col.modSchema(check=True)
        except AnkiError:
            tooltip("Reorganization aborted.")
            return False
        # Create checkpoint
        self.mw.checkpoint("Reorganize notes")

        nids, deleted, created = self.processActions(nids)
        moved += created
        modified = self.rearrange(nids, start, moved)

        self.mw.reset()
        self.selectNotes(modified + created)
        tooltip(u"Reorganization complete:<br>"
            u"≥<b>{}</b> note(s) <b>moved</b><br>"
            u"<b>{}</b> note(s) <b>deleted</b><br>"
            u"<b>{}</b> note(s) <b>created</b>".format(
                len(modified), len(deleted), len(created)),
            parent=self.browser)


    def processActions(self, nids):
        processed = []
        deleted = []
        created = []
        last = 0

        for idx, nid in enumerate(nids):
            try:
                processed.append(int(nid))
                continue
            except ValueError:
                vals = nid.split(": ")

            try:
                nxt = int(nids[idx+1])
            except (IndexError, ValueError):
                nxt = None

            action = vals[0]
            data = vals[1:]
            if action == DEL_NOTE:
                nnid = int(data[0])
                if not nnid or not self.noteExists(nnid):
                    continue
                self.removeNote(nnid)
                deleted.append(nnid)
                continue
            elif action in (NEW_NOTE, DUPE_NOTE):
                if action == DUPE_NOTE:
                    ntype = None
                    sample = int(data[0])
                else:
                    ntype = "".join(data)
                    sample = last or nxt or self.findSample(nids)
                if not sample or not self.noteExists(sample):
                    continue
                nid = self.addNote(sample, ntype)
                if not nid:
                    continue
                created.append(int(nid))
                processed.append(int(nid))

            last = nid

        return processed, deleted, created


    def findSample(self, nids):
        sample = None
        for nid in nids:
            try:
                sample = int(nid)
                break
            except ValueError:
                continue
        return sample


    def rearrange(self, nids, start, moved):
        """Adjust nid order"""
        modified = []
        last = 0

        for idx, nid in enumerate(nids):
            try:
                nxt = int(nids[idx+1])
            except (IndexError, ValueError):
                nxt = nid + 1

            if not self.noteExists(nid): # note deleted
                continue

            print("------------------------------")
            print("last", last)
            print("current", nid)
            print("next", nxt)
            print("nextmoved", nxt in moved)
            print("expected", last < nid < nxt)
            # check if order as expected
            if last != 0 and last < nid < nxt:
                if nid in moved and nxt in moved:
                    print("moved block")
                    pass
                else:
                    print("skipping")
                    last = nid
                    continue

            if last != 0:
                new_nid = last + 1 # regular nids
            elif start and start != (nid // 1000):
                new_nid = start * 1000 # first nid, date changed
            else:
                print("skipping first nid")
                last = nid # first nid, date unmodified
                continue

            print("modifying")
            
            if BACKUP_NIDS:
                self.backupOriginalNid(nid)
            
            new_nid = self.updateNidSafely(nid, new_nid)

            modified.append(new_nid)

            # keep track of moved nids (e.g. for dupes)
            self.nid_map[nid] = new_nid
            last = new_nid

            print("new_nid", new_nid)

        return modified


    def addNote(self, sample_nid, ntype=None):
        """Create new note based on sample nid"""
        sample_nid = self.nid_map.get(sample_nid, sample_nid)
        sample = self.mw.col.getNote(sample_nid)
        cids = self.mw.col.db.list(
                "select id from cards where nid = ? order by ord", sample_nid)
        try:
            sample_cid = cids[0]
        except IndexError:
            # invalid state: note has no cards
            return None
        # try to use visible card if available
        for cid in cids:
            if cid in self.browser.model.cards:
                sample_cid = cid
                break
        
        # gather model/deck information
        sample_card = self.mw.col.getCard(sample_cid)
        sample_did = sample_card.odid or sample_card.did # account for dyn decks
        sample_deck = self.mw.col.decks.get(sample_did)

        if not ntype or ntype == MODEL_SAME:
            model = sample.model()
        else:
            model = self.mw.col.models.byName(ntype)
        
        # Assign model to deck
        self.mw.col.decks.select(sample_did)
        sample_deck['mid'] = model['id']
        self.mw.col.decks.save(sample_deck)
        # Assign deck to model
        self.mw.col.models.setCurrent(model)
        model['did'] = sample_did
        self.mw.col.models.save(model)
        
        # Create new note
        new_note = self.mw.col.newNote()
        if not ntype: # dupe
            new_note.tags = sample.tags
            new_note.fields = sample.fields
        else:
            # need to fill all fields to avoid notes without cards
            new_note.fields = ["placeholder"] * len(new_note.fields)

        # Refresh note and add to database
        new_note.flush()
        self.mw.col.addNote(new_note)
        
        return new_note.id


    def removeNote(self, nid):
        self.mw.col.remNotes([nid])


    def noteExists(self, nid):
        """Checks the database to see whether the nid is actually assigned"""
        return self.mw.col.db.scalar(
            """select id from notes where id = ?""", nid)


    def updateNidSafely(self, nid, new_nid):
        """Update nid while ensuring that timestamp doesn't already exist"""
        while self.noteExists(new_nid):
            new_nid += 1

        # Update note row
        self.mw.col.db.execute(
            """update notes set id=? where id = ?""", new_nid, nid)

        # Update card rows
        self.mw.col.db.execute(
            """update cards set nid=? where nid = ?""", new_nid, nid)

        return new_nid


    def backupOriginalNid(self, nid):
        """Store original NID in a predefined field (if available)"""
        note = self.mw.col.getNote(nid)
        if BACKUP_FIELD in note and not note[BACKUP_FIELD]:
            note[BACKUP_FIELD] = str(nid)
        note.flush()


    def selectNotes(self, nids):
        """Select browser entries by note id"""
        sm = self.browser.form.tableView.selectionModel()
        sm.clear()
        cids = []
        for nid in nids:
            cids += self.mw.col.db.list(
                "select id from cards where nid = ? order by ord", nid)
        self.browser.model.selectedCards = {cid: True for cid in cids}
        self.browser.model.restoreSelection()
