# -----------------------------------------------------------------------------
# Name:         rule.py
# Purpose:      Object for storing the syntactic role of a note
#
# Author:       Robert Snarrenberg
# Copyright:    (c) 2021 by Robert Snarrenberg
# License:      BSD, see license.txt
# -----------------------------------------------------------------------------
"""
Rule
====

The Rule class stores information about a note's syntactic function."""

# -----------------------------------------------------------------------------
# MAIN CLASS
# -----------------------------------------------------------------------------


class Rule():
    """A rule that can be assigned as an attribute to a Note in a Line. A rule
    has a name (e.g., 'S2') and a level. For display purposes, rule
    names are appended to notes as lyrics."""
    validRuleScopes = ('global', 'local')

    def __init__(self, name=None, lineType=None,
                 scope=None, level=None, index=None):
        self.name = name  # S1, E1, B1
        self.lineType = lineType
        self.scope = scope  # global, local??
        self.level = level
        # creates an attribute for tracking the position of a rule in a line
        self.index = index
#        self.type # transition, insertion (stepto, insert)
#        self.subtype # I, R, P, N, IN, IP ...

    def __repr__(self):
        return str(self.name)

# -----------------------------------------------------------------------------


if __name__ == "__main__":
    # self_test code
    pass
# -----------------------------------------------------------------------------
# eof
