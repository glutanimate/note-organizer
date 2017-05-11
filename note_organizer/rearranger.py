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

    def __init__(self, browser, moved):
        self.browser = browser
        self.mw = self.browser.mw
        self.moved = moved
        self.nid_map = {}


    def rearrange(self, nids, start):
        # Full database sync required:
        try:
            self.mw.col.modSchema(check=True)
        except AnkiError:
            tooltip("Reorganization aborted.")
            return False
        # Create checkpoint
        self.mw.checkpoint("Reorganize notes")

        modified, deleted, created = self.processNids(nids, start)

        self.mw.reset()
        self.selectNotes(modified + created)
        tooltip(u"Reorganization complete:<br>"
            u"≥<b>{}</b> note(s) <b>moved</b><br>"
            u"<b>{}</b> note(s) <b>deleted</b><br>"
            u"<b>{}</b> note(s) <b>created</b>".format(
                len(modified), len(deleted), len(created)),
            parent=self.browser)


    def processNids(self, nids, start):
        """Adjust nid order"""
        modified = []
        deleted = []
        created = []
        last = 0

        for idx, nid in enumerate(nids):
            try:
                nxt = int(nids[idx+1])
            except (IndexError, ValueError):
                nxt = None

            try: # regular nid
                nid = int(nid)
            except ValueError: # action
                vals = nid.split(": ")
                if not vals or len(vals) < 2: # should not happen
                    continue
                action = vals[0]
                if action == DEL_NOTE:
                    nid = int(vals[1])
                    self.removeNote(nid)
                    deleted.append(nid)
                    continue
                elif action in (NEW_NOTE, DUPE_NOTE):
                    dupe = action == DUPE_NOTE
                    if dupe:
                        ntype = MODEL_SAME
                        sample_nid = int(vals[1])
                    else:
                        ntype = "".join(vals[1:])
                        sample_nid = last or nxt
                    nid = self.addNote(ntype, sample_nid, dupe)
                    if not nid:
                        continue
                    created.append(nid)

            if not nxt: # have to do this after processing new notes
                nxt = nid + 1

            if not self.noteExists(nid): # note deleted
                continue


            print("------------------------------")
            print("last", last)
            print("current", nid)
            print("next", nxt)
            print("nextmoved", nxt in self.moved)
            print("expected", last < nid < nxt)
            # check if order as expected
            if nxt not in self.moved and last != 0 and last < nid < nxt:
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

            if nid in self.moved and nid not in created:
                modified.append(new_nid)

            # keep track of moved nids (e.g. for dupes)
            self.nid_map[nid] = new_nid
            last = new_nid

            print("new_nid", new_nid)

        return modified, deleted, created


    def addNote(self, ntype, sample_nid, dupe):
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
        if dupe:
            new_note.tags = sample.tags
            new_note.fields = sample.fields
        else:
            # need to fill all fields to avoid notes without cards
            new_note.fields = ["empty note"] * len(new_note.fields)

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
