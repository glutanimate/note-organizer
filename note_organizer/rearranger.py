# -*- coding: utf-8 -*-

"""
This file is part of the Note Organizer add-on for Anki

Note rearranger module

Copyright: (c) Glutanimate 2017
License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

from anki.errors import AnkiError

from aqt.utils import tooltip
from anki.utils import intTime
from config import *
from consts import *

class Rearranger:
    """Performs the actual database reorganization"""

    def __init__(self, browser):
        self.browser = browser
        self.mw = self.browser.mw
        self.nid_map = {}


    def processNids(self, nids, start, moved):
        """Main function"""
        # Full database sync required:
        try:
            self.mw.col.modSchema(check=True)
        except AnkiError:
            tooltip("Reorganization aborted.")
            return False
        # Create checkpoint
        self.mw.checkpoint("Reorganize notes")

        nids, deleted, created = self.processActions(nids)
        modified = self.rearrange(nids, start, moved, created)

        self.mw.col.reset()
        self.mw.reset()
        self.selectNotes(moved + created)
        tooltip(u"Reorganization complete:<br>"
            u"<b>{}</b> note(s) <b>moved</b><br>"
            u"<b>{}</b> note(s) <b>deleted</b><br>"
            u"<b>{}</b> note(s) <b>created</b><br>"
            u"<b>{}</b> note(s) <b>updated alongside</b><br>".format(
                len(moved), len(deleted), len(created), 
                len(modified)-len(moved)),
            parent=self.browser)


    def findSample(self, nids):
        """Find valid nid in nids list"""
        sample = None
        for nid in nids:
            try:
                sample = int(nid)
                if self.noteExists(sample):
                    break
            except ValueError:
                continue
        return sample


    def processActions(self, nids):
        """Parse and execute actions in nid list (e.g. note creation)"""
        """Also converts nids to ints"""
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
            elif action.startswith((NEW_NOTE, DUPE_NOTE)):
                sched = False
                ntype = None
                if action.startswith(DUPE_NOTE):
                    sample = int(data[0])
                    sched = action == DUPE_NOTE_SCHED
                else:
                    ntype = "".join(data)
                    sample = last or nxt or self.findSample(nids)
                if not sample or not self.noteExists(sample):
                    continue
                nid = self.addNote(sample, ntype=ntype, sched=sched)
                if not nid:
                    continue
                created.append(int(nid))
                processed.append(int(nid))

            last = nid

        return processed, deleted, created


    def rearrange(self, nids, start, moved, created):
        """Adjust nid order"""
        modified = []
        alterated = moved + created
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
                if nid in alterated and nxt in alterated:
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
            
            
            new_nid = self.updateNidSafely(nid, new_nid)

            if nid not in created:
                modified.append(new_nid)
                idnote = False
            else:
                idnote = True

            self.setNidFields(new_nid, nid, idnote=idnote)

            # keep track of moved nids (e.g. for dupes)
            self.nid_map[nid] = new_nid
            
            print("new_nid", new_nid)
            last = new_nid

        return modified


    def addNote(self, sample_nid, ntype=None, sched=False):
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
        new_note.tags = sample.tags
        if not ntype: # dupe
            fields = sample.fields
        else:
            # need to fill all fields to avoid notes without cards
            fields = ["."] * len(new_note.fields)
        new_note.fields = fields
        if BACKUP_FIELD in new_note: # skip onid field
            new_note[BACKUP_FIELD] = ""
        
        # Refresh note and add to database
        new_note.flush()
        self.mw.col.addNote(new_note)

        # Copy over scheduling from old cards
        if sched:
            scards = sample.cards()
            ncards = new_note.cards()
            for orig, copy in zip(scards, ncards):
                self.copyCardScheduling(orig, copy)

        return new_note.id


    def copyCardScheduling(self, o, c):
        """Copy scheduling data over from original card"""
        self.mw.col.db.execute(
            "update cards set type=?, queue=?, due=?, ivl=?, "
            "factor=?, reps=?, lapses=?, left=? where id = ?",
            o.type, o.queue, o.due, o.ivl,
            o.factor, o.reps, o.lapses, o.left, c.id)

    
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

        # Leave some room for future changes when possible
        for i in xrange(20):
            new_nid += 1
            if self.noteExists(new_nid):
                new_nid -= 1
                break

        # Update note row
        self.mw.col.db.execute(
            """update notes set id=? where id = ?""", new_nid, nid)

        # Update card rows
        self.mw.col.db.execute(
            """update cards set nid=? where nid = ?""", new_nid, nid)

        return new_nid


    def setNidFields(self, nid, onid, idnote=False):
        """Store original NID in a predefined field (if available)"""
        note = self.mw.col.getNote(nid)
        if BACKUP_FIELD in note and not note[BACKUP_FIELD]:
            note[BACKUP_FIELD] = str(onid)
        if idnote and NID_FIELD in note: # add nid to note id field
            note["Note ID"] = str(nid)
        note.flush()


    def selectNotes(self, nids):
        """Select browser entries by note id"""
        self.browser.form.tableView.selectionModel().clear()
        cids = []
        for nid in nids:
            nid = self.nid_map.get(nid, nid)
            cids += self.mw.col.db.list(
                "select id from cards where nid = ? order by ord", nid)
        self.browser.model.selectedCards = {cid: True for cid in cids}
        self.browser.model.restoreSelection()
