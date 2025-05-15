# -----------------------------------------------------------------------------
# Name:         utilities.py
# Purpose:      Scripts shared among various modules
#
# Author:       Robert Snarrenberg
# Copyright:    (c) 2025 by Robert Snarrenberg
# License:      BSD, see license.txt
# -----------------------------------------------------------------------------

import itertools

# -----------------------------------------------------------------------------


def pairwise(span):
    """s -> (s0, s1), (s1, s2), (s2, s3), ..."""
    a, b = itertools.tee(span)
    next(b, None)
    zipped = zip(a, b)
    return list(zipped)


def pairwiseFromLists(list1, list2):
    """return permutations from two lists"""
    comb = [(i, j) for i in list1 for j in list2]
    result = []
    for c in comb:
        if c[0] < c[1]:
            result.append(c)
        else:
            result.append((c[1], c[0]))
    return result


def shiftBuffer(stack, buffer):
    nextnote = buffer[0]
    buffer.pop(0)
    stack.append(nextnote)


def shiftStack(stack, buffer):
    lastnote = stack[-1]
    stack.pop(-1)
    buffer.insert(0, lastnote)



def create_html_report(input):
    """
    Converts a report string to an HTML string,
    wrapping each line in the specified tag.

    Args:
        output: The string to convert.
        tag: The HTML tag to wrap each line in.

    Returns:
        An HTML string.
    """
    output = ''
    lines = input.splitlines()
    lines = [line.replace('\t', '&nbsp;&nbsp;') for line in lines]
    html_lines = [f"""<p>{line}</p>""" for line in lines]
    return """\n""".join(html_lines)


# -----------------------------------------------------------------------------


if __name__ == '__main__':
    # self_test code
    pass
# -----------------------------------------------------------------------------
# eof

    report = '\nError Report\n\tFirst line of report\n\t\tSecond line of report\n\t\t\tThird line of report'
    print(create_html_report(report))