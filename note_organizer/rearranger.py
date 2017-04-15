# -*- coding: utf-8 -*-

"""
This file is part of the Note Organizer add-on for Anki

Note rearranger module

Copyright: (c) Glutanimate 2017
License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

from aqt import mw

class Rearranger:

    def __init__(self, browser, moved):
        self.browser = browser
        self.moved = moved

    def rearrange(self, nids):
        """Adjust nid order"""
        modified = []
        # Full database sync required:
        mw.col.modSchema(check=True)
        # Create undo checkpoint
        mw.checkpoint("Reorganize notes")

        print "\n" * 4
        last = nids.pop(0)
        for idx, nid in enumerate(nids):
            
            # print "idx", idx
            try:
                nxt = nids[idx+1]
            except IndexError:
                nxt = nid+1

            # check if order as expected
            if last < nid < nxt:
                # above check won't work if we moved an entire block,
                # so we need to check against all remaining indices
                if not any(nid>i for i in nids[idx:]):
                    last = nid
                    continue
        
            new_nid = last + 1
            # Ensure timestamp doesn't already exist
            while mw.col.db.scalar(
                    "select id from notes where id = ?", new_nid):
                new_nid += 1

            print "=================================="
            print "last", last
            print "nid", nid
            print "next", nxt
            print "new_nid", new_nid

            # Update note row
            mw.col.db.execute(
                """update notes set id=? where id = ?""", new_nid, nid)

            # Update cards rows
            mw.col.db.execute(
                """update cards set nid=? where nid = ?""", new_nid, nid)

            last = new_nid

            if nid in self.moved:
                modified.append(new_nid)

        mw.reset()
        self.selectNotes(modified)


    def selectNotes(self, nids):
        sm = self.browser.form.tableView.selectionModel()
        sm.clear()
        cids = []
        for nid in nids:
            cids += mw.col.db.list(
                "select id from cards where nid = ? order by ord", nid)
        self.browser.model.selectedCards = {cid: True for cid in cids}
        self.browser.model.restoreSelection()