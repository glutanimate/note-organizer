# -*- coding: utf-8 -*-

"""
This file is part of the Note Organizer add-on for Anki

Temporary configuration file

Copyright: (c) Glutanimate 2017
License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

# TODO: consider implementing in options dialog

# HOTKEY ASSIGNMENTS

HOTKEY_ORGANIZER = "Ctrl+G"
HOTKEY_INSERT = "Ctrl+N"
HOTKEY_DUPE = "Ctrl+D"
HOTKEY_DUPE_SCHED = "Ctrl+Shift+D"
HOTKEY_REMOVE = "Del"
HOTKEY_CUT = "Ctrl+X"
HOTKEY_PASTE = "Ctrl+V"

# OPTIONS

# General

# Ask confirmation before performing actions
ASK_CONFIRMATION = True
# Display warning when invoking on more than x cards
CARD_COUNT_WARNING = 2000
# Default note type of created notes
DEFAULT_MODEL = "Basic"

# Reviewer context actions

REVIEWER_CONTEXT_MENU = True
REVIEWER_OPEN_BROWSER = True

# NID fields

# whether or not to backup original Note IDs:
BACKUP_NIDS = True 
# field to use for Note ID backups:
BACKUP_FIELD = "onid"
# whether or not to hide BACKUP_FIELD in editors:
HIDE_BACKUP_FIELD = True
# support for "Add Note ID" add-on,
# new nid will be written in NID_FIELD:
NID_FIELD = "Note ID"