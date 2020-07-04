# Name:         utilities.py
# Purpose:      Scripts shared among various modules
#
# Author:       Robert Snarrenberg
# Copyright:    (c) 2020 by Robert Snarrenberg
# License:      LGPL or BSD, see license.txt
#-------------------------------------------------------------------------------

import itertools

def pairwise(span):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(span)
    next(b, None)
    zipped = zip(a, b)
    return list(zipped)

def pairwiseFromLists(list1, list2):
    'return permutations from two lists'
    comb = [(i,j) for i in list1 for j in list2]
    result = []
    for c in comb:
        if c[0] < c[1]:
            result.append(c)
        else:
            result.append((c[1],c[0]))
    return result
