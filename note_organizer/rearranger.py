# -*- coding: utf-8 -*-

"""
This file is part of the Note Organizer add-on for Anki

Note rearranger module

Copyright: (c) Glutanimate 2017
License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

from aqt import mw


class Rearranger:

    def __init__(self, browser, modified):
        self.browser = browser
        self._modified = modified

    def rearrange(self, nids):
        mw.col.modSchema(check=True)
        mw.progress.start(label="Note Reorganizer: updating...", max = len(nids))
        mw.checkpoint("Reorganize notes")

        modified = []

        print "\n" * 4

        last = nids.pop(0)
        for idx, nid in enumerate(nids):
            
            # print "idx", idx
            try:
                nxt = nids[idx+1]
            except IndexError:
                nxt = nid+1

            if last < nid < nxt:
                if not any(nid>i for i in nids[idx:]): # block moved
                    last = nid
                    continue
        
            dest = last+1
            print "=================================="
            print "last", last
            print "nid", nid
            print "next", nxt

            # Ensure timestamp doesn't already exist
            while mw.col.db.scalar(
                    "select id from notes where id = ?", dest):
                dest += 1

            print "dest", dest

            # Update the note row
            mw.col.db.execute(
                """update notes set id=? where id = ?""", dest, nid)

            # Update the cards row(s)
            mw.col.db.execute(
                """update cards set nid=? where nid = ?""", dest, nid)

            last = dest
            if nid in self._modified:
                modified.append(dest)

        mw.progress.finish()

        mw.reset()
        
        #self.selectNotes(modified)

        return

    def selectNotes(self, nids):
        sm = self.browser.form.tableView.selectionModel()
        sm.clear()
        cids = []
        for nid in nids:
            cids += mw.col.db.list(
                "select id from cards where nid = ? order by ord", nid)
        self.browser.model.selectedCards = {cid: True for cid in cids}
        self.browser.model.restoreSelection()