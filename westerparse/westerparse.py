# -----------------------------------------------------------------------------
# Name:        westerparse.py
# Purpose:     Evaluating Westergaardian species counterpoint
#
# Author:      Robert Snarrenberg
# Copyright:   (c) 2025 by Robert Snarrenberg
# License:     BSD, see license.txt
# -----------------------------------------------------------------------------
"""
WesterParse
===========

This is the main program module.

WesterParse allows a user to test a species counterpoint exercise
for conformity with the rules of line construction and voice leading
laid out in Peter Westergaard's book, *An Introduction to Tonal Theory*
(New York, 1975).

WesterParse imports a musicxml file, converts it to a music21 stream,
determines a key (unless specified by the user), and then evaluates
the linear syntax or the counterpoint.

The main scripts are:

>>> evaluateLines(source)
>>> evaluateCounterpoint(source)

For more information on how to use these scripts, see
:doc:`User's Guide to WesterParse <userguide>`.
"""

import logging
import time
import unittest
import os
import json

from music21 import *

from westerparse import context
from westerparse import parser
from westerparse import vlChecker
from westerparse import utilities

# -----------------------------------------------------------------------------
# LOGGER
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)
logger.propagate = False
# logging handlers
f_handler = logging.FileHandler('westerparse.txt', mode='w')
f_handler.setLevel(logging.DEBUG)
# logging formatters
f_formatter = logging.Formatter('%(message)s')
f_handler.setFormatter(f_formatter)
# add handlers to logger
logger.addHandler(f_handler)

# -----------------------------------------------------------------------------
# OPERATIONAL VARIABLES
# -----------------------------------------------------------------------------

usePreferredParseSets = True

# -----------------------------------------------------------------------------
# EXCEPTION HANDLERS
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# MAIN SCRIPTS
# -----------------------------------------------------------------------------

def evaluateLines(source,
                  show=None,
                  partSelection=None,
                  partLineType=None,
                  report=False,
                  **kwargs):
    """
    Determine whether lines are generable using Westergaard's rules.

    Keyword arguments:

    `show` -- Determines how the output is handled.

       *Options*

       None -- Default option. A text report is generated in lieu of a
       display in musical notation.

       `show` -- Parses will be displayed using the music notation application
       that the user has configured for music21.

       'html' -- A HTML report is generated.

       `writeToServer` -- Reserved for use by the WesterParse website
       to write parses to musicxml files, which are then displayed in
       the browser window.

       `writeToLocal` -- Can be used to write parses in musicxml to a
       user's local directory. [Eventually the user will be able to select
       a directory by editing a configuration.py file.]  By default, the
       files are written to 'parses_from_context/'.  The name for each
       file consists of the prefix 'parser_output', a timestamp,
       and the suffix '.musicxml'.

       `writeToPng` -- Use the application MuseScore to produce png files.
       MuseScore first generates an xml file and then derives the png
       file.  These are named with the prefix 'parser_output',
       a timestamp, and the appropriate suffix.  Note that Musescore
       inserts '-1' before adding the '.png' suffix. The default
       directory for these files is 'tempimages/'.  [This, too, can be
       changed by editing the configuration.py file.]

       `showWestergaardParse` -- Not yet functional.  Can be used if
       the source consists of only one line. It will display the parse(s)
       of a line using Westergaard's layered form of representation.

       `parsedata` -- Can be used to create a json data file for each viable
       parse of the selected parts. The data file consists of several lines of
       metadata, a data table for notes, and a data table for the arcs.

    `partSelection` -- Designates a line of the composition to parse.

       *Options*

       `None` -- The default option. Selects all the lines for parsing.

       0, 1, 2, ..., -1 -- Following the conventions of music21, lines are
       numbered from top to bottom, starting with 0.

    `partLineType` -- Only for use in evaluating a single line.  None is
    the default. User may select among 'primary', 'bass', or 'generic'.

    `report` -- True or False. Use True to see a text report.  Note: If
    one or more lines in the source cannot be parsed (i.e., if there are
    syntax errors) or the `show` option is set to None, the program will
    automatically generate a text report.

    Other keywords: `keynote` and `mode` -- The user can use these to
    force the parser to interpret the input in a particular key.

    For harmonically progressive species, the user can specify when
    the predominant and dominant spans begin, using the keywords
    `startDominant` and, if needed, `startPredominant`, with values
     given as measure numbers.
    """
    logger.debug(f'Evaluating lines in {source}.')
    # Make the global context.
    if partLineType == 'any' or '':
        partLineType = None
    try:
        cxt = makeGlobalContext(source, partSelection, **kwargs)
    except context.EvaluationException as fce:
        # suppress error reporting when generating parse data files
        if show == 'html':
            fn = os.path.basename(source)
            desc = f'{fn}\n{fce.desc}'
            return utilities.create_html_report(desc)
            # return utilities.create_html_report(fce.desc)
        elif show == 'parsedata':
            pass
        else:
            fce.report()
        return

    # Parse the global context.
    try:
        parseContext(cxt, show, partSelection, partLineType)
        logger.debug(f'\n{cxt.parseReport}')
        if show is None or report is True:
            pass
            # print(cxt.parseReport)
        elif show == 'Boolean':
            return True
        elif show == 'html':
            return utilities.create_html_report(cxt.parseReport)
        return True
    except context.EvaluationException as fce:
        # suppress error reporting when generating parse data files
        if show == 'html':
            return utilities.create_html_report(fce.desc)
        elif show == 'parsedata':
            pass
        else:
            fce.report()
            print(fce.desc)


def evaluateCounterpoint(source,
                         report=True,
                         sonorityCheck=False,
                         **kwargs):
    """
    Determine whether voice leading conforms to Westergaard's rules.

    If report is set to True, the program will produce a text report.
    If report is set to 'html', the program will produce a HTML report.
    """
    logger.debug(f'Evaluating voice leading in {source}.')
    # Make the global context.
    try:
        cxt = makeGlobalContext(source, partSelection=None, **kwargs)
    except context.EvaluationException as fce:
        if report == 'html':
            return utilities.create_html_report(fce.desc)
        else:
            print(fce.desc)
        return
    # Validate the context as contrapuntal.
    try:
        if len(cxt.parts) == 1:
            raise context.ContextError(
                  'The composition is only a single line. '
                  'There is no voice-leading to check.')
    except context.ContextError as ce:
        ce.logerror()
        if report == 'html':
            fn = os.path.basename(source)
            rpt = f'{fn}\n{ce.report}'
            return utilities.create_html_report(rpt)
    # If context is contrapuntal, evaluate the voice leading.
    else:
        result = vlChecker.checkCounterpoint(cxt, report)
        if report == 'html':
            return utilities.create_html_report(result)
        if not report:
            if vlChecker.vlErrors:
                return False
            else:
                return True

# -----------------------------------------------------------------------------
# MAIN AUXILIARY SCRIPT
# -----------------------------------------------------------------------------


def makeGlobalContext(source, partSelection, **kwargs):
    """
    Import a musicxml file and convert to music21 Stream.
    Then create a :py:class:`~context.GlobalContext`.
    """
    s = converter.parse(source)
    # create a global context object and prep for evaluation
    # if errors encountered, script will exit and report
    gxt = context.GlobalContext(s, partSelection, filename=source, **kwargs)
    return gxt

# -----------------------------------------------------------------------------
# PARSING SCRIPTS
# -----------------------------------------------------------------------------


def parseContext(cxt,
                 show=None,
                 partSelection=None,
                 partLineType=None,
                 report=False):
    """
    Run the parser for each line of a context using :py:func:`parsePart`.
    Collect error reports from the parser and
    to produce an error report.
    Create a separate report for successful parses.
    If the user has elected to display the results, select
    the preferred interpretations and display them.

    #. Create a dictionary of error reports for each part that is parsed.

    #. If the user has selected a part for evaluation, determine
       whether the selection is valid.

    #. If the user has selected a type of line, determine whether
       the selection is valid.

    #. Run the parser for the selected parts and collect errors, if any.
       For primary lines, check for compliance with rule G2.

    #. Determine the generability of the selected parts.

    #. If show is 'parsedata' and the parts are all generable, export the
       data for each parse as a json file.

    #. Create a parse report (text) to display to the user.

    #. Gather the sets of parses for the selected part(s).
       If the module variable 'usePreferredParseSets' is set to True,
       use Westergaard's counterpoint preferences for
       2- and 3-part counterpoint.

    #. [If show is 'parsedata' and the parts are all generable,
       export counterpoint data as a json file. (Not yet implemented.)]

    #. Based on the value of the 'show' variable, output
       the interpreted part(s).
    """

    # (1) Access the context's dictionary of dictionaries for collecting error reports.
    #   primary keys: part names
    #   secondary keys: 'parser errors', 'primary', 'bass'
    # cxt.errorsDict = {}
    for part in cxt.parts:
        cxt.errorsDict[part.name] = {}

    # (2) Validate part selection.
    try:
        partsForParsing = validatePartSelection(cxt, partSelection)
    except context.ContextError as ce:
        ce.logerror()
        raise context.EvaluationException(ce.desc)

    # (3) Validate line type selection.
    try:
        validateLineTypeSelection(cxt, partSelection, partLineType)
    except context.ContextError as ce:
        ce.logerror()
        raise context.EvaluationException(ce.desc)

    # (4) Run the parser, collect errors, and log parses.
    for part in partsForParsing:
        # Set the part's lineType if given by the user.
        if partLineType:
            part.lineType = partLineType
        else:
            part.lineType = None
        # Parse the selected part.
        parsePart(part, cxt)
        # Collect errors.
        if part.errors:
            cxt.errorsDict[part.name]['parser errors'] = part.errors
        else:
            cxt.errorsDict[part.name]['parser errors'] = []
        if part.typeErrorsDict:
            for key, value in part.typeErrorsDict.items():
                cxt.errorsDict[part.name][key] = value
        # Check the final step in potential primary lines
        if part.isPrimary:
            checkFinalStep(part, cxt)
        # Log the parse.
        parseLog = writeParseDataLog(part)
        logger.debug(f'{parseLog}')

    # (5) Determine the generability of the selected parts.
    generability = getGenerability(cxt, partSelection)
    logger.debug(f'\nGenerabilty: {generability}')

    # (6) Create parse data files, if called.
    if show == 'parsedata' and generability:
        writeParseDataFiles(cxt)

    # (7) Create parse report.
    try:
        createParseReport(cxt, generability, partsForParsing, partSelection,
                          partLineType)
    except context.ContextError as ce:
        # ce.logerror()
        raise context.EvaluationException(ce.desc)

    # (8) Gather the interpretations of the selected part(s)
    #       in the specified manner.
    # If usePreferredParseSets is True, use Westergaard's counterpoint
    #       preferences for 2- and 3-part counterpoint
    parseSets = gatherParseSets(cxt, partSelection, partLineType)

    # TODO (9) add export of counterpoint data file
    # (9) Create counterpoint data files, if called.
    if show == 'parsedata' and generability:
        writeCounterpointDataFiles(cxt, parseSets)

    # (10) Output the parses in the desired manner.
    showParses(cxt, show, parseSets)


def validatePartSelection(cxt, partSelection):
    """
    Determine whether the selected part number is actually present in
    the score, and if so, select that part; if not, report the selection
    error to the user. If no part is selected by the user, all parts
    of the score will be parsed.
    """
    partsSelected = None
    if partSelection is not None:
        try:
            cxt.parts[partSelection]
        except IndexError:
            if len(cxt.parts) == 1:
                pts = ' part'
            else:
                pts = ' parts'
            fn = os.path.basename(cxt.filename)
            error = (f'{fn}\nCONTEXT ERROR\n'
                + 'The composition has only '
                + str(len(cxt.parts)) + pts
                + ', so the part selection must fall in the range of 0-'
                + str(len(cxt.parts)-1)
                + '.\nHence the selection of part '
                + str(partSelection) + ' is invalid.')
            raise context.ContextError(error)
        else:
            if partSelection >= 0:
                partsSelected = cxt.parts[partSelection:partSelection+1]
            else:
                partsSelected = cxt.parts[partSelection::partSelection-1]
    elif len(cxt.parts) == 1:
        partsSelected = cxt.parts[0:1]
    elif partSelection is None:
        partsSelected = cxt.parts
    return partsSelected


def validateLineTypeSelection(cxt, partSelection, partLineType):
    """
    If the user has selected a line type, they must also have selected a
    single part for evaluation. If both selections were not made,
    report the error to the user.
    """
    if partLineType is not None:
        if len(cxt.parts) == 1 or partSelection is not None:
            return True
        else:
            pass
        fn = os.path.basename(cxt.filename)
        error = (f'{fn}\nCONTEXT ERROR\n'
                 + 'You have selected the following line type: '
                 + f'{partLineType}. '
                 + '\nHowever, line type selection is only permitted '
                 + 'when the source is a single line\nor there is a valid '
                 + 'part selection.')
        raise context.ContextError(error)


def parsePart(part, cxt):
    """
    Parse a given part.
    Create a (:py:class:`~parser.Parser`) for the part and
    collect the results.  Determine whether the line is generable as a primary,
    bass, or generic line.  Compile a list of ways the line can be generated
    for each line type, if at all. Collect a list of parsing errors.
    """
    # Run the parser.
    partParser = parser.Parser(part, cxt)
    # Sort out the interpretations of the part.
    part.parses = partParser.parses
    part.isPrimary = partParser.isPrimary
    part.isGeneric = partParser.isGeneric
    part.isBass = partParser.isBass
    part.Pinterps = partParser.Pinterps
    part.Ginterps = partParser.Ginterps
    part.Binterps = partParser.Binterps
    part.interpretations = partParser.interpretations
    # Gather errors, if any.
    part.errors = partParser.errors
    part.typeErrorsDict = partParser.typeErrorsDict
    logger.debug(f'\nValid parses of part {part.partNum}: {part.interpretations}')


def checkFinalStep(part, cxt):
    """
    Check primary lines for compliance with rule G2, which requires that at
    least one note in the penultimate measure has a clear step connection
    to the final note in the line. If no such connection is found, record
    the error.
    """
    # TODO this works when a line is otherwise parsable as a primary line,
    #   but perhaps it should also be called when a line is being evaluated
    #   as a primary line, regardless of whether it is otherwise generable

    # TODO rethink how the rule works in third species:
    #   e.g., 7-6-5 | 8, the local passing does not interfere with the
    #   7-8 connection
    # Assume there is no acceptable final step connection until proven true.
    finalStepConnection = False
    # Get the last note of the primary upper line.
    ultimaNote = part.recurse().notes[-1]
    # Collect the notes in the penultimate bar of the upper line.
    penultBar = part.getElementsByClass(stream.Measure)[-2].notes
    buffer = []
    stack = []

    # Fill buffer with notes of penultimate bar in reverse.
    for n in reversed(penultBar):
        buffer.append(n)
    blen = len(buffer)
    # Start looking for a viable step connection.
    while blen > 0:
        if vlChecker.isDiatonicStep(ultimaNote, buffer[0]):
            # Check penultimate note.
            if len(stack) == 0:
                finalStepConnection = True
                break
            # Check other notes, if needed.
            elif len(stack) > 0:
                for s in stack:
                    if vlChecker.isDiatonicStep(s, buffer[0]):
                        finalStepConnection = False
                        break
                    else:
                        finalStepConnection = True
        utilities.shiftBuffer(stack, buffer)
        blen = len(buffer)
    # Write an error in the context error dictionary for this part
    # and set isPrimary to False
    if not finalStepConnection:  # ultimaNote.csd.value % 7 == 0
        error = (
            'No final step connection in the primary upper line.')
        cxt.errorsDict[part.name]['parser errors'].append(error)
#        part.errors.append(error)
#        parserErrors = cxt.errorsDict[part.name]['parser errors']
#        parserErrors.append(error)
#        cxt.errorsDict[part.name]['parser errors'] = parserErrors
        part.isPrimary = False
    else:
        pass


def writeParseDataLog(part):
    """
    Write line parse to a log file.  Used for debugging.
    """
    pass
    logInfo = []
    parseHeader = ('Parse of part ' + str(part.partNum) + ':')
    logInfo.append(parseHeader)
    if part.parses:
        for prse in part.parses:
            parseData = ('Label: ' + prse.label
                         + '\n\tArcs:  ' + str(prse.arcs)
                         + '\n\tRules:\t'
                         + ''.join(['{:4d}'.format(lbl[0])
                                    for lbl in prse.ruleLabels])
                         + '\n\t      \t'
                         + ''.join(['{:>4}'.format(lbl[1])
                                    for lbl in prse.ruleLabels])
                         + '\n\t      \t'
                         + ''.join(['{:4d}'.format(lbl[2])
                                    for lbl in prse.ruleLabels])
                         )
            logInfo.append(parseData)
    logData = '\n'.join(logInfo)
    return logData


def getGenerability(cxt, partSelection):
    """
    Determine whether all parts are generable.
    """
    generableParts = 0
    generability = False
    if partSelection is None:
        for part in cxt.parts:
            if part.isPrimary or part.isBass or part.isGeneric:
                generableParts += 1
        if generableParts == len(cxt.parts):
            generability = True
    elif partSelection is not None:
        rules = [cxt.parts[partSelection].isPrimary,
                 cxt.parts[partSelection].isBass,
                 cxt.parts[partSelection].isGeneric]
        if any(rules):
            generability = True
    return generability


def writeParseDataFiles(cxt):
    """Using the output of :py:func:`extractParseDataFromPart`,
    write json data files for each successfully parsed line, ignoring
    generic parses."""
    # TODO limit to selected part
    for part in cxt.parts:
        Pinterps = part.interpretations.get('primary', None)
        Ginterps = part.interpretations.get('generic', None)
        Binterps = part.interpretations.get('bass', None)
        if Pinterps:
            for parse in Pinterps:
                extractParseDataFromPart(cxt, part, parse)
        # if Ginterps:
        #     for parse in Ginterps:
        #         extractParseData(part, parse)
        if Binterps:
            for parse in Binterps:
                extractParseDataFromPart(cxt, part, parse)


def extractParseDataFromPart(cxt, part, parse):
    """Prepare a json data file for a particular parse.
    Each file contains three sets of data:

    #. Metadata: file name, part number, line type, parse label, species

    #. A data table for notes: index, rule, generative level, offset,
       scale degree, left paren, right paren.

    #. A data table for arcs: list of note indexes,
       category (basic, secondary), type (passing, neighboring, repetition,
       arpeggiation), direction, position in hierarchy, list of scale degrees.

     """
    file_name = os.path.splitext(os.path.basename(cxt.filename))[0]
    # create a name for the parsed data file
    fn = 'parse_data/' + file_name + '_' + str(
        part.partNum) + '_' + parse.label + '_data.json'
    # assemble metadata
    parse_data = {}
    parse_data['file_name'] = file_name
    parse_data['part_number'] = part.partNum
    parse_data['line_type'] = parse.lineType
    parse_data['species'] = parse.species
    parse_data['parse_label'] = parse.label
    # assemble notes_array dictionary
    notes_array = []
    # start with the note labels in each part, consisting of a
    # tuple: (index, rule, level)
    # TODO address problem with indexing notes in fourth species
    for lab in parse.ruleLabels:
        note_array = {}
        note_array['index'] = lab[0]
        # offset property is causing problems, perhaps because of json
        # data restrictions (no fractions allowed),
        # so I've converted the fractions to approx floats
        if not isinstance(part.flatten().notes[lab[0]].offset, float):
            num = part.flatten().notes[lab[0]].offset.numerator
            den = part.flatten().notes[lab[0]].offset.denominator
            val = round(num / den, 2)
            note_array['offset'] = val
        else:
            note_array['offset'] = part.flatten().notes[lab[0]].offset
        note_array['csd_value'] = part.flatten().notes[lab[0]].csd.value
        note_array['rule_label'] = lab[1]
        note_array['gen_level'] = lab[2]
        # add dependency data
        # note_array['lefthead'] = part.flatten().notes[lab[0]].dependency.lefthead
        # note_array['righthead'] = part.flatten().notes[lab[0]].dependency.righthead
        # note_array['dependents'] = part.flatten().notes[lab[0]].dependency.dependents
        # detemine parentheses for each inserted note
        left_paren = False
        right_paren = False
        if lab[1] in ['E3', 'L3']:
            left_paren = True
            right_paren = True
            for arc in parse.arcs:
                if arc[-1] == lab[0]:
                    left_paren = False
                if arc[0] == lab[0]:
                    right_paren = False
        # detemine parentheses for each repetition, based on its lefthead
        elif lab[1] in ['E1', 'L1']:
            left_paren = False
            right_paren = False
            for arc in parse.arcs:
                # lookup start of arc to see if it has a left paren
                if (arc[-1] == lab[0] and part.flatten().notes[
                        arc[0]].csd.value == part.flatten().notes[
                        lab[0]].csd.value):
                    lefthead = arc[0]
                    lefttuplelist = [lb for lb in parse.ruleLabels if lb[0] == lefthead]
                    if lefttuplelist[0][1] in ['E3', 'L3']:
                        right_paren = True
                    # now check to see if an arc from the lefthead extends
                    # beyond the repetition
                    for a in parse.arcs:
                        if a[0] == lefthead and a[-1] > lab[0]:
                            right_paren = False
                # set to false if there's an arc that starts from the rep
                elif arc[0] == lab[0]:
                    right_paren = False
        note_array['left_paren'] = left_paren
        note_array['right_paren'] = right_paren
        # add note array to list
        notes_array.append(note_array)
    # add notes list to data
    parse_data['notes_array'] = notes_array
    # assemble arcs_array dictionary
    arcs_array = []
    for key, arc in parse.arcDict.items():
        arc_array = {}
        arc_array['arc'] = arc.arc
        arc_array['arc_category'] = arc.category
        arc_array['arc_type'] = arc.type
        arc_array['arc_subtype'] = arc.subtype
        arc_array['arc_content'] = arc.content
        arc_array['arc_level'] = arc.level
        arcs_array.append(arc_array)
    # add arcs list to data
    parse_data['arcs_array'] = arcs_array
    # write data to json text file
    with open(fn, 'w') as json_file:
        json.dump(parse_data, json_file, indent=4)


def createParseReport(cxt, generability, partsForParsing, partSelection,
                      partLineType):
    """
    Create an optional parse report to be diplayed to the user
    and a required error report if errors arise.
    """
    # Base string for reporting parse results.
    fn = os.path.basename(cxt.filename)
    cxt.parseReport = f'{fn}\nPARSE REPORT'

    # Gather information on the key to report to the user.
    if cxt.keyFromUser:
        result = ('Key supplied by user: ' + cxt.key.nameString)
        cxt.parseReport = cxt.parseReport + '\n' + result
    else:
        result = ('Key inferred by program: ' + cxt.key.nameString)
        cxt.parseReport = cxt.parseReport + '\n' + result

    if generability:
        if partSelection is not None or len(cxt.parts) == 1:
            if partSelection is not None:
                part = cxt.parts[partSelection]
            else:
                part = cxt.parts[0]
            if partLineType is None:
                if part.isPrimary and part.isBass:
                    result = ('The line is generable as both '
                              'a primary line and a bass line.')
                elif not part.isPrimary and part.isBass:
                    result = ('The line is generable as a bass '
                              'line but not as a primary line.')
                elif part.isPrimary and not part.isBass:
                    result = ('The line is generable as a primary '
                              'line but not as a bass line.')
                if (not part.isPrimary and not part.isBass
                        and part.isGeneric):
                    result = ('The line is generable only '
                              'as a generic line.')
            elif partLineType is not None:
                if partLineType == 'primary' and part.isPrimary:
                    result = 'The line is generable as a primary line.'
                elif partLineType == 'bass' and part.isBass:
                    result = 'The line is generable as a bass line.'
                elif partLineType == 'generic' and part.isGeneric:
                    result = 'The line is generable as a generic line.'
                # ERRORS
                else:
                    error = ('The line is not generable as the '
                             'selected type: ' + partLineType)
                    error = (error + '\nThe following linear '
                             'errors were found:')
                    if cxt.errorsDict[part.name][partLineType]:
                        for err in cxt.errorsDict[part.name][partLineType]:
                            error = error + '\n\t\t' + str(err)
                    error = f'{fn}\nPARSE REPORT\n' + error
                    raise context.ContextError(error)
            # Update parse report if no errors found.
            cxt.parseReport = cxt.parseReport + '\n' + result

        elif partSelection is None and len(cxt.parts) > 1:
            upperPrimary = False
            genericUpperLines = []
            lowerBass = False
            for part in cxt.parts[0:-1]:
                if part.isPrimary:
                    upperPrimary = True
                else:
                    genericUpperLines.append(part.name)
            if cxt.parts[-1].isBass:
                lowerBass = True
            if upperPrimary and lowerBass:
                if len(cxt.parts) == 2:
                    result = ('The upper line is generable as a '
                              'primary line.\nThe lower line '
                              'is generable as a bass line.')
                else:
                    result = ('At least one upper line is generable '
                              'as a primary line.\nThe lower line '
                              'is generable as a bass line.')
            # ERRORS
            elif not upperPrimary and lowerBass:
                if len(cxt.parts) == 2:
                    error = ('The upper line is not generable '
                             'as a primary line.\nBut the lower '
                             'line is generable as a bass line.')
                else:
                    error = ('No upper line is generable as a '
                             'primary line.\nBut the lower line '
                             'is generable as a bass line.')
                for gul in genericUpperLines:
                    if cxt.errorsDict[gul]:
                        error = (error + '\n\tThe following linear '
                                 'errors were found in ' + gul + ':')
                        for err in cxt.errorsDict[gul]['parser errors']:
                            error = error + '\n\t\t\t' + str(err)
                error = f'{fn}\nPARSE REPORT\n' + error
                raise context.ContextError(error)
            elif upperPrimary and not lowerBass:
                if len(cxt.parts) == 2:
                    error = ('The upper line is generable as a '
                             'primary line.\nBut the lower line '
                             'is not generable as a bass line.')
                else:
                    error = ('At least one upper line is generable '
                             'as a primary line.\nBut the lower line '
                             'is not generable as a bass line.')
                bln = cxt.parts[-1].name
                if cxt.errorsDict[bln]:
                    error = (error + '\n\tThe following linear '
                             'errors were found in the bass line:')
                    for err in cxt.errorsDict[bln].get('bass', []):
                        error = error + '\n\t\t\t' + str(err)
                error = f'{fn}\nPARSE REPORT\n' + error
                raise context.ContextError(error)
            elif not upperPrimary and not lowerBass:
                if len(cxt.parts) == 2:
                    error = ('The upper line is not generable as a '
                             'primary line.\nNor is the lower line '
                             'generable as a bass line.')
                else:
                    error = ('No upper line is generable as '
                             'a primary line.\nNor is the lower '
                             'line generable as a bass line.')
                for part in cxt.parts[:-1]:
                    if cxt.errorsDict[part.name].get('primary'):
                        error = (error + '\n\tThe following linear '
                                 'errors were found in ' + part.name + ':')
                        for err in cxt.errorsDict[part.name]['primary']:
                            error = error + '\n\t\t' + str(err)
                bln = cxt.parts[-1].name
                if cxt.errorsDict[bln].get('bass'):
                    error = (error + '\n\tThe following linear errors '
                             'were found in the bass line:')
                    for err in cxt.errorsDict[bln]['bass']:
                        error = error + '\n\t\t' + str(err)
                error = f'{fn}\nPARSE REPORT\n' + error
                raise context.ContextError(error)
            # Update parse report if no errors found.
            cxt.parseReport = cxt.parseReport + '\n' + result

    elif not generability:
        # Get header and key information from parse report.
        error = cxt.parseReport + '\n' + 'Line Parsing Errors'
        if len(partsForParsing) == 1:
            part = partsForParsing[0]
            error = (error + '\n\tThe following linear errors were '
                     'found when attempting to interpret the line:')
            try:
                cxt.errorsDict[part.name]['parser errors']
            except KeyError:
                pass
            else:
                for err in cxt.errorsDict[part.name]['parser errors']:
                    error = error + '\n\t\t' + str(err)
                # 2025-04-18 turn off unspecified error msg
                # if not cxt.errorsDict[part.name]['parser errors']:
                #     error = error + '\n\t\tUnspecified error.'
            try:
                cxt.errorsDict[part.name]['primary']
            except KeyError:
                pass
            else:
                for err in cxt.errorsDict[part.name]['primary']:
                    error = error + '\n\t\t' + str(err)
            try:
                cxt.errorsDict[part.name]['bass']
            except KeyError:
                pass
            else:
                for err in cxt.errorsDict[part.name]['bass']:
                    error = error + '\n\t\t' + str(err)
            raise context.ContextError(error)
        else:
            for part in cxt.parts[:-1]:
                if part.isPrimary:
                    error = (error + '\n\t' + part.name +
                             ' is generable as a primary line.')
                elif not part.isPrimary and part.isGeneric:
                    error = (error + '\n\t' + part.name +
                             ' is generable as a generic line.')
                else:
                    error = (error + '\n\t' + part.name +
                             ' is not generable. '
                             'The following errors were found:')
                try:
                    cxt.errorsDict[part.name]['parser errors']
                except KeyError:
                    pass
                else:
                    for err in cxt.errorsDict[part.name]['parser errors']:
                        error = error + '\n\t\t' + str(err)
                try:
                    cxt.errorsDict[part.name]['primary']
                except KeyError:
                    pass
                else:
                    for err in cxt.errorsDict[part.name]['primary']:
                        error = error + '\n\t\t' + str(err)
            for part in cxt.parts[-1:]:
                if part.isBass:
                    error = (error + '\n\t' + part.name +
                             ' is generable as a bass line.')
                else:
                    error = (error + '\n\t' + part.name +
                             ' is not generable. '
                             'The following errors were found:')
                try:
                    cxt.errorsDict[part.name]['parser errors']
                except KeyError:
                    pass
                else:
                    for err in cxt.errorsDict[part.name]['parser errors']:
                        error = error + '\n\t\t' + str(err)
                try:
                    cxt.errorsDict[part.name]['bass']
                except KeyError:
                    pass
                else:
                    for err in cxt.errorsDict[part.name]['bass']:
                        error = error + '\n\t\t' + str(err)

        raise context.ContextError(error)


def gatherParseSets(cxt, partSelection=None, partLineType=None):
    """
    After parsing the individual lines, collect all the possible combinations
    of parses. If the module variable `usePreferredParseSets`
    is set to True, use Westergaard’s counterpoint preferences
    for 2- and 3-part counterpoint.
    """
    parseSets = []
    # (1a) If one part is selected.
    if partSelection is not None:
        part = cxt.parts[partSelection]
        if partLineType == 'primary' and part.isPrimary:
            for parse in part.Pinterps:
                parseSets.append((parse,))
        elif partLineType == 'bass' and part.isBass:
            for parse in part.Binterps:
                parseSets.append((parse,))
        elif partLineType == 'generic' and part.isGeneric:
            for parse in part.Ginterps:
                parseSets.append((parse,))
    # (1b) if there is only 1 part and no type is specified.
    elif len(cxt.parts) == 1 and partLineType is None:
        part = cxt.parts[0]
        if part.Pinterps:
            for parse in part.Pinterps:
                parseSets.append((parse,))
        if part.Binterps:
            for parse in part.Binterps:
                parseSets.append((parse,))
        if part.Ginterps:
            for parse in part.Ginterps:
                parseSets.append((parse,))
    # (1c) if there is only 1 part and type is specified.
    elif len(cxt.parts) == 1 and partLineType:
        part = cxt.parts[0]
        if partLineType == 'primary' and part.Pinterps:
            for parse in part.Pinterps:
                parseSets.append((parse,))
        if partLineType == 'bass' and part.Binterps:
            for parse in part.Binterps:
                parseSets.append((parse,))
        if partLineType == 'generic' and part.Ginterps:
            for parse in part.Ginterps:
                parseSets.append((parse,))
    # (2a) If there are 2 parts and no preferences are specified, show
    # all combinations of primary and bass parses. Ignore generic parses.
    elif len(cxt.parts) == 2 and partSelection is None:
        upperPart = cxt.parts[0]
        lowerPart = cxt.parts[1]
        for PI in upperPart.Pinterps:
            for BI in lowerPart.Binterps:
                parseSets.append((PI, BI))
    # (2b) If there are 3 parts and no preferences are specified, show
    # all combinations of primary and bass parses. Ignore generic parses if
    # primary parses are available for an upper or inner line.
    elif len(cxt.parts) == 3 and partSelection is None:
        upperPart = cxt.parts[0]
        innerPart = cxt.parts[1]
        lowerPart = cxt.parts[2]
        if upperPart.isPrimary:
            upperPartPreferredInterps = upperPart.Pinterps
        else:
            upperPartPreferredInterps = upperPart.Ginterps
        if innerPart.isPrimary:
            innerPartPreferredInterps = innerPart.Pinterps
        else:
            innerPartPreferredInterps = innerPart.Ginterps
        for UI in upperPartPreferredInterps:
            for II in innerPartPreferredInterps:
                for BI in lowerPart.Binterps:
                    parseSets.append((UI, II, BI))
    parsesString = ("\n".join([f"\t{x}" for x in parseSets]) )
    logger.debug(f'\nAll parse sets:\n {parsesString}')
    # (3) select only preferred parses in 2- or 3-part counterpoint
    if len(cxt.parts) == 2 and partSelection is None and usePreferredParseSets:
        preferredParseSets = selectPreferredParseSets(cxt, 0)
        parseSets = preferredParseSets
    elif len(cxt.parts) == 3 and partSelection is None and usePreferredParseSets:
        upperPart = cxt.parts[0]
        innerPart = cxt.parts[1]
        preferredParseSets = []
        if upperPart.isPrimary:
            upperPrefs = selectPreferredParseSets(cxt, 0)
            # collect all of the possible P and G parses for the inner part
            innerPrefs = []
            if innerPart.isPrimary:
                innerPrefs += [p for p in innerPart.Pinterps]
            innerPrefs += [p for p in innerPart.Ginterps]
            # now make all the combinations
            for prefPair in upperPrefs:
                for II in innerPrefs:
                    preferredParseSets.append((prefPair[0], II, prefPair[1]))
        if innerPart.isPrimary:
            innerPrefs = selectPreferredParseSets(cxt, 1)
            # collect all of the possible P and G parses for the upper part
            upperPrefs = []
            if upperPart.isPrimary:
                upperPrefs += [p for p in upperPart.Pinterps]
            upperPrefs += [p for p in upperPart.Ginterps]
            # now make all the combinations
            for prefPair in innerPrefs:
                for PI in upperPrefs:
                    preferredParseSets.append((PI, prefPair[0], prefPair[1]))
            parseSets = preferredParseSets
    parsesString = ("\n".join([f"\t{x}" for x in parseSets]) )
    logger.debug(f'\nPreferred sets:\n {parsesString}')
    # (4) show 4-part counterpoint???
    if len(cxt.parts) > 3:
        error = 'Not yet able to display counterpoint in four or more parts.'
        raise context.ContextError(error)
    else:
        return parseSets


def selectPreferredParseSets(cxt, primaryPartNum):
    """
    Negotiate the best match between the global structure of a given
    upper line and the global structure of the bass line.
    [This currently works only for two- and three-part counterpoint.]
    """
    # TODO need to refine the preferences substantially

    primPart = cxt.parts[primaryPartNum]
    bassPart = cxt.parts[-1]
    preferredGlobals = []

    # Look for coordination of penultimate structural components.
    domOffsetDiffList = []  # structural Dominant Offset Differences List
    lowestDifference = 1000
    for interpPrimary in primPart.interpretations['primary']:
        for interpBass in bassPart.interpretations['bass']:
            # 2023-06-19 removed recurse() before flatten()
            a = primPart.flatten().notes[interpPrimary.S3Final].offset
            b = bassPart.flatten().notes[interpBass.S3Index].offset
            domOffsetDiff = (a - b)
            if abs(domOffsetDiff) < lowestDifference:
                lowestDifference = abs(domOffsetDiff)
            domOffsetDiffList.append((abs(domOffsetDiff),
                                      (interpPrimary, interpBass)))
    for pair in domOffsetDiffList:
        if abs(pair[0]) == abs(lowestDifference):
            preferredGlobals.append(pair[1])

    nonharmonicParses = []
    # TODO evaluate all pairings, not just the preferred ones
    #   create a list of all pairings???
    allGlobals = []
    for interpPrimary in primPart.interpretations['primary']:
        for interpBass in bassPart.interpretations['bass']:
            allGlobals.append((interpPrimary, interpBass))

    if allGlobals and cxt.harmonicSpecies:
        for prse in allGlobals:
            offInitTon = cxt.harmonicSpanDict['offsetInitialTonic']
            offPredom = cxt.harmonicSpanDict['offsetPredominant']
            offDom = cxt.harmonicSpanDict['offsetDominant']
            offClosTon = cxt.harmonicSpanDict['offsetClosingTonic']

            # implement preference rules for global coordination of
            #   linear structures
            # Check for span placement and consonance of
            #   primary upper line notes
            #   bass line pitches have already been checked

            SList = prse[0].arcBasic
            # Set primary line type: 3line, 5line, 8line.
            SLine = str(len(SList)) + 'line'
            # Set number of required structural consonances.
            if len(SList) == 3:
                structConsReq = 3
            else:
                structConsReq = 4
            # Count the structural consonances.
            structuralConsonances = 0
            for s in SList:
                u = primPart.flatten().notes[s]
                b = cxt.parts[
                                 -1].flatten().notes.getElementsByOffset(
                                 u.offset, mustBeginInSpan=False)[0]
                if vlChecker.isConsonanceAboveBass(b, u):
                    structuralConsonances += 1
            # Check harmonic coordination of structural pitches.
            # Assume it true until proven otherwise.
            # If false, add to list of nonharmonic parses
            harmonicCoordination = True
            # Check placement of S1.
            if offPredom is not None:
                if not (offInitTon
                        <= primPart.flatten().notes[SList[0]].offset
                        < offPredom):
                    harmonicCoordination = False
            else:
                if not (offInitTon
                        <= primPart.flatten().notes[
                            SList[0]].offset
                        < offDom):
                    harmonicCoordination = False
            # Check placement of predominant.
            predomSIndexList = []
            structuralPredominant = False
            if SLine == '3line':
                predomSIndexList = [SList[-2]]
            elif SLine == '5line':
                predomSIndexList = [SList[-4], SList[-2]]
            elif SLine == '8line':
                predomSIndexList = [SList[-6], SList[-4], SList[-2]]
            if offPredom is not None:
                for psi in predomSIndexList:
                    u = primPart.flatten().notes[psi]
                    b = cxt.parts[
                        -1].flatten().notes.getElementsByOffset(
                        u.offset, mustBeginInSpan=False)[0]
                    if ((offPredom
                         <= primPart.flatten().notes[psi].offset
                         < offDom)
                            and vlChecker.isConsonanceAboveBass(b, u)):
                        structuralPredominant = True
            if not structuralPredominant:
                harmonicCoordination = False
            # Check placement of dominant.
            if offPredom is None:
                u = primPart.flatten().notes[SList[-1]]
                b = cxt.parts[
                                 -1].flatten().notes.getElementsByOffset(
                                 u.offset, mustBeginInSpan=False)[0]
                if ((offDom
                     <= primPart.flatten().notes[SList[-1]].offset
                     < offClosTon)
                        and vlChecker.isConsonanceAboveBass(b, u)):
                    harmonicCoordination = False

            # Add pair to removal list if coordination tests not passed.
            if not (structuralConsonances >= structConsReq
                    and harmonicCoordination):
                nonharmonicParses.append(prse)

    if cxt.harmonicSpecies:
        preferredGlobals = [prse for prse in allGlobals
                            if prse not in nonharmonicParses]

    return preferredGlobals


def writeCounterpointDataFiles(cxt, parseSets):
    label_count = 0
    for parseSet in parseSets:
        if label_count < 10:
            label = '0' + str(label_count)
        else:
            label = str(label_count)
        # extractCounterpointDataFromParseSets(cxt, parseSet, label)
        pass


def extractCounterpointDataFromParseSets(cxt, parseSet, label):
    """Prepare a json data file for a particular set of parses.
    Each file contains n sets of data:

    #. Metadata: file name, species

    #. A data table for intervals.

    #. n data tables for arcs: list of note indexes,
       category (basic, secondary), type (passing, neighboring, repetition,
       arpeggiation), direction, position in hierarchy, list of scale degrees.

     """
    file_name = os.path.splitext(os.path.basename(cxt.filename))[0]
    # create a name for the parsed data file
    fn = 'counterpoint_data/' + file_name + '_' + label + '_data.json'
    pass


def showParses(cxt, show, parseSets):
    """Show the interpretations. For each set of line parses,
    build the representation of each component line
    and then select the appropriate mode of representation (show)."""
    def buildInterpretation(parse):
        # Clean out slurs that might have been left behind by a previous parse.
        slurs = cxt.parts[parse.partNum].recurse().getElementsByClass(
            spanner.Slur)
        for slur in slurs:
            cxt.parts[parse.partNum].remove(slur)
        # TODO Remove not only slurs but also parentheses and colors.

        # BUILD the interpretation
        # Arcs, rules, and parens are tied to note indexes in the line,
        # and these are then attached to notes in the source part.
        assignSlurs(cxt.parts[parse.partNum], parse.arcs, parse.arcBasic)
        assignRules(cxt.parts[parse.partNum], parse.ruleLabels)
        assignParentheses(cxt.parts[parse.partNum], parse.parentheses)

    def selectOutput(content, show):
        # content is a stream (part or score)
        if show == 'show':
            content.show()
        elif show == 'writeToServer':
            timestamp = str(time.time())
            filename = ('/home/spenteco/1/snarrenberg/parses_from_context/'
                        + 'parser_output_' + timestamp + '.musicxml')
            content.write('musicxml', filename)
            pass
            # print(filename)
        elif show == 'writeToCorpusServer':
            timestamp = str(time.time())
            filename = ('./media/tmp/'
                        + 'parser_output_' + timestamp + '.musicxml')
            content.write('musicxml', filename)
        elif show == 'writeToLocal':
            timestamp = str(time.time())
            filename = ('parses_from_context/'
                        + 'parser_output_' + timestamp + '.musicxml')
            content.write('musicxml', filename)
        elif show == 'writeToPng':
            timestamp = str(time.time())
            filename = ('tempimages/'
                        + 'parser_output_' + timestamp + '.xml')
            content.write('musicxml.png', fp=filename)
        elif show == 'showWestergaardParse':
            pass
            # TODO Activate function for displaying layered representations of
            # a parsed line, perhaps for one line only.
            # use parser.displayWestergaardParse

    for parseTuple in parseSets:
        # (1) Build the interpretation of each part.
        for parseLabel in parseTuple:
            buildInterpretation(parseLabel)
        # (2) Show the interpreted content.
        # if just one part present or selected, show just that part
        if len(parseTuple) == 1:
            selectedPart = parseTuple[0].partNum
            content = cxt.parts[selectedPart]
        # else show all parts:
        elif len(parseTuple) in [2, 3]:
            content = cxt.score

        selectOutput(content, show)

# -----------------------------------------------------------------------------
# OPERATIONAL SCRIPTS FOR PARSING DISPLAY
# -----------------------------------------------------------------------------


def assignSlurs(source, arcs, arcBasic=None):
    """
    Given a fully parsed line (an interpretation), sort through the arcs and
    create a music21 spanner (tie/slur) to represent each arc.
    """
    # Source is a Part in the input Score.
    # Sort through the arcs and create a spanner(tie/slur) for each.
    tempArcs = []
    # Skip duplicate arcs and the basic arc, if given.
    for elem in arcs:
        if elem not in tempArcs and elem != arcBasic:
            tempArcs.append(elem)
    arcs = tempArcs
    # Build arcs.
    for arc in arcs:
        arcBuild(source, arc)
    # TODO Set up separate function for the basic arc.
    # Currently using color to indicate notes in the basic arc.


def arcBuild(source, arc):
    """
    Translate an arc into a notated slur.
    """
    # Source is a Part in the input Score.
    if len(arc) == 2:
        slurStyle = 'dashed'
    else:
        slurStyle = 'solid'
    thisSlur = spanner.Slur()
    thisSlur.lineType = slurStyle
    thisSlur.placement = 'above'
    source.insert(0, thisSlur)
    for ind in arc:
        obj = source.recurse().notes[ind]
        thisSlur.addSpannedElements(obj)


def assignRules(source, rules):
    """
    Given a fully parsed line (an interpretation), add a lyric to each
    note to show the syntactic rule that generates the note.
    Also assigns a color to notes generated by a rule of basic structure.
    """
    # Source is a Part in the input Score.
    ruleLabels = rules
    for index, elem in enumerate(source.recurse().notes):
        for rule in ruleLabels:
            if index == rule[0]:
                elem.lyric = rule[1]
                if elem.lyric is not None and elem.lyric[0] == 'S':
                    elem.style.color = 'red'
                else:
                    elem.style.color = 'black'
            else:
                pass


def assignParentheses(source, parentheses):
    """
    Add parentheses around notes generated as insertions. [This aspect
    of syntax representation cannot be fully implemented at this time,
    because musicxml only allows parentheses to be assigned in pairs,
    whereas syntax coding requires
    the ability to assign left and right parentheses separately.]
    """
    # Source is a Part in the input Score.
    parentheses = parentheses
    for index, elem in enumerate(source.recurse().notes):
        for parens in parentheses:
            if index == parens[0]:
                elem.noteheadParenthesis = parens[1]
            else:
                pass

# -----------------------------------------------------------------------------
# TESTS
# -----------------------------------------------------------------------------


class Test(unittest.TestCase):

    def runTest(self):
        pass

    def test_evaluateLines(self):
        source = '../examples/corpus/WP100.musicxml'
        self.assertTrue(evaluateLines(source))

# -----------------------------------------------------------------------------


if __name__ == "__main__":
    unittest.main()

# -----------------------------------------------------------------------------
# eof
