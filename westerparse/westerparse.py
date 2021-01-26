# -----------------------------------------------------------------------------
# Name:        westerparse.py
# Purpose:     Evaluating Westergaardian species counterpoint
#
# Author:      Robert Snarrenberg
# Copyright:   (c) 2020 by Robert Snarrenberg
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

from music21 import *

from westerparse import context
from westerparse import parser
from westerparse import vlChecker
from westerparse import theoryAnalyzerWP

# -----------------------------------------------------------------------------
# LOGGER
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
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

selectPreferredParseSets = True
logParses = False

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

       `writeToServer` -- Reserved for use by the WesterParse web site
       to write parses to musicxml files, which are then displayed in
       the browser window.

       `writeToLocal` -- Can be used to write parses in musicxml to a
       user's local directory. [Eventually the user will be able select
       a directory by editing a configuration.py file.]  By default, the
       files are written to 'parses_from_context/'.  The name for each
       file consists of the prefix 'parser_output\_', a timestamp,
       and the suffix '.musicxml'.

       `writeToPng` -- Use the application MuseScore to produce png files.
       MuseScore first generates an xml file and then derives the png
       file.  These are named with the prefix 'parser_output\_',
       a timestamp, and the appropriate suffix.  Note that Musescore
       inserts '-1' before adding the '.png' suffix. The default
       directory for these files is 'tempimages/'.  [This, too, can be
       changed by editing the configuration.py file.]

       `showWestergaardParse` -- Not yet functional.  Can be used if
       the source consists of only one line. It will display the parse(s)
       of a line using Westergaard's layered form of representation.

    `partSelection` -- Designates a line of the composition to parse.

       *Options*

       `None` -- The default option. Selects all of the lines for parsing.

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
    context.clearLogfile('logfile.txt')
    if partLineType == 'any' or '':
        partLineType = None
    try:
        cxt = makeGlobalContext(source, **kwargs)
    except context.EvaluationException as fce:
        fce.show()
        return
    try:
        parseContext(cxt, show, partSelection, partLineType)
        if show is None or report is True:
            print(cxt.parseReport)
        return True
    except context.EvaluationException as fce:
        fce.show()
    if logParses:
        logInterpretations(cxt, partSelection)


def evaluateCounterpoint(source,
                         report=True,
                         sonorityCheck=False,
                         **kwargs):
    """
    Determine whether voice leading conforms to Westergaard's rules.
    """
    context.clearLogfile('logfile.txt')
    try:
        cxt = makeGlobalContext(source, **kwargs)
    except context.EvaluationException as fce:
        fce.show()
        return
    try:
        if len(cxt.parts) == 1:
            raise context.ContextError(
                  'Context Error: The composition is only a single line. '
                  'There is no voice-leading to check.')
    except context.ContextError as ce:
        ce.logerror()
    try:
        if len(cxt.parts) == 1:
            raise context.EvaluationException
    except context.EvaluationException as ee:
        ee.show()
    else:
        vlChecker.vlErrors = []
        vlChecker.checkCounterpoint(cxt, report=True)

# -----------------------------------------------------------------------------
# HELPER SCRIPTS
# -----------------------------------------------------------------------------


def makeScore(source):
    """
    Import a musicxml file and convert to music21 Stream.
    """
    s = converter.parse(source)
    return s


def makeGlobalContext(source, **kwargs):
    """
    Import a musicxml file and convert to music21 Stream.
    Then create a :py:class:`~context.GlobalContext`.
    """
    s = converter.parse(source)
    # create a global context object and prep for evaluation
    # if errors encountered, script will exit and report
    gxt = context.GlobalContext(s, **kwargs)
    return gxt


def makeLocalContext(cxt, cxtOn, cxtOff, cxtHarmony):
    """
    Create a local context given a start and stop offset
    in an enclosing Context.
    [Not functional.]
    """
    locSource = cxt.getElementsByOffset(cxtOn,
                                     cxtOff,
                                     includeEndBoundary=True,
                                     mustFinishInSpan=False,
                                     mustBeginInSpan=True,
                                     includeElementsThatEndAtStart=False,
                                     classList=None)
    locCxt = context.LocalContext(locSource)
    locCxt.source = locSource
    locCxt.harmony = cxtHarmony
    return locCxt


def displaySourceAsPng(source):
    """
    Use MuseScore to create a .png image of a musicxml source file.
    """
    cxt = converter.parse(source)
    timestamp = str(time.time())
    filename = 'tempimages/' + 'display_output_' + timestamp + '.xml'
    cxt.write('musicxml.png', fp=filename)


def parseContext(cxt,
                 show=None,
                 partSelection=None,
                 partLineType=None,
                 report=False):
    """
    Parse the lines in a score.

    Run the parser for each line of a context using :py:func:`parsePart`.
    Use a dictionary to collect error reports from the parser and
    to produce an error report.
    Create a separate report for successful parses.
    If the user has elected to display the results, select
    the preferred interpretations and display them.
    """
    # dictionary for collecting error reports
    # primary keys: part names
    # secondary keys: 'parser errors', 'primary', 'bass'
    cxt.errorsDict = {}
    for part in cxt.parts:
        cxt.errorsDict[part.name] = {}

    # validate part selection and line type selection
    try:
        partsForParsing = validatePartSelection(cxt, partSelection)
    except context.ContextError as ce:
        ce.logerror()
        raise context.EvaluationException
    try:
        lineTypeSelection = validateLineTypeSelection(cxt,
                                                      partSelection,
                                                      partLineType)
    except context.ContextError as ce:
        ce.logerror()
        raise context.EvaluationException

    # Run the parser and collect errors.
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

    # Determine whether all parts are generable.
    generableParts = 0
    generableContext = False
    if partSelection is None:
        for part in cxt.parts:
            if part.isPrimary or part.isBass or part.isGeneric:
                generableParts += 1
        if generableParts == len(cxt.parts):
            generableContext = True
    elif partSelection is not None:
        rules = [cxt.parts[partSelection].isPrimary,
                 cxt.parts[partSelection].isBass,
                 cxt.parts[partSelection].isGeneric]
        if any(rules):
            generableContext = True

    # Create the optional parse report for user
    # and a required error report if errors arise.
    def createParseReport():
        # Base string for reporting parse results.
        cxt.parseReport = 'PARSE REPORT'

        # Gather information on the key to report to the user.
        if cxt.keyFromUser:
            result = ('Key supplied by user: ' + cxt.key.nameString)
            cxt.parseReport = cxt.parseReport + '\n' + result
        else:
            result = ('Key inferred by program: ' + cxt.key.nameString)
            cxt.parseReport = cxt.parseReport + '\n' + result

        if generableContext is True:
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
                        result = ('The line is generable as a primary line.')
                    elif partLineType == 'bass' and part.isBass:
                        result = ('The line is generable as a bass line.')
                    elif partLineType == 'generic' and part.isGeneric:
                        result = ('The line is generable as a generic line.')
                    # ERRORS
                    else:
                        error = ('The line is not generable as the '
                                 'selected type: ' + partLineType)
                        error = (error + '\nThe following linear '
                                 'errors were found:')
                        if cxt.errorsDict[part.name][partLineType]:
                            for err in cxt.errorsDict[part.name][partLineType]:
                                error = error + '\n\t\t' + str(err)
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
                                  'primary line. \nThe lower line '
                                  'is generable as a bass line.')
                    else:
                        result = ('At least one upper line is generable '
                                  'as a primary line. \nThe lower line '
                                  'is generable as a bass line.')
                # ERRORS
                elif not upperPrimary and lowerBass:
                    if len(cxt.parts) == 2:
                        error = ('The upper line is not generable '
                                 'as a primary line. \nBut the lower '
                                 'line is generable as a bass line.')
                    else:
                        error = ('No upper line is generable as a '
                                 'primary line. \nBut the lower line '
                                 'is generable as a bass line.')
                    for gul in genericUpperLines:
                        if cxt.errorsDict[gul]:
                            error = (error + '\n\tThe following linear '
                                     'errors were found in ' + gul + ':')
                            for err in cxt.errorsDict[gul]['parser errors']:
                                error = error + '\n\t\t\t' + str(err)
                    raise context.ContextError(error)
                elif upperPrimary and not lowerBass:
                    if len(cxt.parts) == 2:
                        error = ('The upper line is generable as a '
                                 'primary line. \nBut the lower line '
                                 'is not generable as a bass line.')
                    else:
                        error = ('At least one upper line is generable '
                                 'as a primary line. \nBut the lower line '
                                 'is not generable as a bass line.')
                    bln = cxt.parts[-1].name
                    if cxt.errorsDict[bln]:
                        error = (error + '\n\tThe following linear '
                                 'errors were found in the bass line:')
                        for err in cxt.errorsDict[bln]['bass']:
                            error = error + '\n\t\t\t' + str(err)
                    raise context.ContextError(error)
                elif not upperPrimary and not lowerBass:
                    if len(cxt.parts) == 2:
                        error = ('The upper line is not generable as a '
                                 'primary line. \nNor is the lower line '
                                 'generable as a bass line.')
                    else:
                        error = ('No upper line is generable as '
                                 'a primary line. \nNor is the lower '
                                 'line generable as a bass line.')
                    for part in cxt.parts[:-1]:
                        if cxt.errorsDict[part.name]:
                            error = (error + '\n\tThe following linear '
                                     'errors were found in ' + part.name + ':')
                            for err in cxt.errorsDict[part.name]['primary']:
                                error = error + '\n\t\t\t' + str(err)
                    bln = cxt.parts[-1].name
                    if cxt.errorsDict[bln]:
                        error = (error + '\n\tThe following linear errors '
                                 'were found in the bass line:')
                        for err in cxt.errorsDict[bln]['bass']:
                            error = error + '\n\t\t\t' + str(err)
                    raise context.ContextError(error)
                # Update parse report if no errors found.
                cxt.parseReport = cxt.parseReport + '\n' + result

        elif generableContext is False:
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
                        error = error + '\n\t\t\t' + str(err)
                    if not cxt.errorsDict[part.name]['parser errors']:
                        error = error + '\n\t\t\tUnspecified error.'
                try:
                    cxt.errorsDict[part.name]['primary']
                except KeyError:
                    pass
                else:
                    for err in cxt.errorsDict[part.name]['primary']:
                        error = error + '\n\t\t\t' + str(err)
                try:
                    cxt.errorsDict[part.name]['bass']
                except KeyError:
                    pass
                else:
                    for err in cxt.errorsDict[part.name]['bass']:
                        error = error + '\n\t\t\t' + str(err)
                raise context.ContextError(error)
            else:
                for part in cxt.parts[:-1]:
                    if part.isPrimary:
                        error = (error + '\n\t' + part.name +
                                 ' is generable as a primary line.')
                    elif (not part.isPrimary and part.isGeneric):
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
                            error = error + '\n\t\t\t' + str(err)
                    try:
                        cxt.errorsDict[part.name]['primary']
                    except KeyError:
                        pass
                    else:
                        for err in cxt.errorsDict[part.name]['primary']:
                            error = error + '\n\t\t\t' + str(err)
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
                            error = error + '\n\t\t\t' + str(err)
                    try:
                        cxt.errorsDict[part.name]['bass']
                    except KeyError:
                        pass
                    else:
                        for err in cxt.errorsDict[part.name]['bass']:
                            error = error + '\n\t\t\t' + str(err)

            raise context.ContextError(error)

    try:
        createParseReport()
    except context.ContextError as ce:
        ce.logerror()
        raise context.EvaluationException
    else:
        pass

        if show is not None:
            # Preferences currently only work for two-part counterpoint.
            # Preference can be turned off by setting
            # selectPreferredParseSets to False
            if (1 < len(cxt.parts) < 3
               and partSelection is None
               and selectPreferredParseSets):
                selectedPreferredParseSets(cxt, show)
            else:
                showInterpretations(cxt, show, partSelection, partLineType)


def validatePartSelection(cxt, partSelection):
    if partSelection is not None:
        try:
            cxt.parts[partSelection]
        except IndexError:
            if len(cxt.parts) == 1:
                pts = ' part'
            else:
                pts = ' parts'
            raise context.ContextError(
                'Context Error: The composition has only '
                + str(len(cxt.parts)) + pts
                + ', so the part selection must fall in the range of 0-'
                + str(len(cxt.parts)-1)
                + '. Hence the selection of part '
                + str(partSelection) + ' is invalid.')
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
    if partLineType is not None:
        if len(cxt.parts) == 1 or partSelection is not None:
            return True
        else:
            pass
        raise context.ContextError(
            'Context Error: You have selected the following line type: '
            + f'{partLineType}. \nHowever, line type selection is only permitted '
            + 'when the source is a single line \nor there is a valid '
            + 'part selection.'
            )


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


def checkFinalStep(part, cxt):
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

    # TODO move buffer function to utilities.py ?
    def shiftBuffer(stack, buffer):
        nextnote = buffer[0]
        buffer.pop(0)
        stack.append(nextnote)
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
        shiftBuffer(stack, buffer)
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


def selectedPreferredParseSets(cxt, show):
    """
    Select sets of parses according to preference rules.

    After parsing the individual parts, select sets of parses
    based on Westergaard preference rules, trying to negotiate the best match
    between global structures in the parts. [This currently works
    only for two-part counterpoint.]
    """
    # TODO need to refine the preferences substantially
    if len(cxt.parts) > 1:
        # Select uppermost part that isPrimary as the primaryPart.
        # This is arbitrary.
        primPart = None
        for part in cxt.parts[:-1]:
            if part.isPrimary:
                primPart = part
                break
        # Select lowest part as the bassPart.
        bassPart = cxt.parts[-1]

#        primaryS3Finals = [i.S3Final for i
#                           in primPart.interpretations['primary']]
#        bassS3s = [i.S3Index for i in bassPart.interpretations['bass']]
        preferredGlobals = []
        domOffsetDiffList = []  # structural Dominant Offset Differences List
        lowestDifference = 1000
        for interpPrimary in primPart.interpretations['primary']:
            for interpBass in bassPart.interpretations['bass']:
                a = primPart.recurse().flat.notes[interpPrimary.S3Final].offset
                b = bassPart.recurse().flat.notes[interpBass.S3Index].offset
                domOffsetDiff = (a - b)
                if abs(domOffsetDiff) < lowestDifference:
                    lowestDifference = abs(domOffsetDiff)
                domOffsetDiffList.append((abs(domOffsetDiff), (interpPrimary,
                                                          interpBass)))
#                    if interpBass.S3Index == interpPrimary.S3Final:
#                        preferredGlobals.append((interpPrimary, interpBass))
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

                # implement preference rules for global coordination of linear structures
                # Check for span placement and consonance of primary upper line notes
                # bass line pitches have already been checked

                def getBassNote(upperNote, context):
                    analyzer = theoryAnalyzerWP.Analyzer()
                    analyzer.addAnalysisData(context.score)
                    verts = analyzer.getVerticalities(context.score)
                    bassNote = None
                    for vert in verts:
                        if upperNote in vert.objects:
                            bassNote = vert.objects[-1]
                    return bassNote

                SList = prse[0].arcBasic
                # set primary line type: 3line, 5line, 8line
                SLine = str(len(SList)) + 'line'
                # set number of required structural consonances
                if len(SList) == 3:
                    structConsReq = 3
                else:
                    structConsReq = 4
                # count the structural consonance
                structuralConsonances = 0
                for s in SList:
                    u = primPart.recurse().notes[s]
                    b = getBassNote(u, cxt)
                    if vlChecker.isConsonanceAboveBass(b, u):
                        structuralConsonances += 1
                # check harmonic placement of structural pitches
                harmonicCoordination = True
                # check placement of S1
                if offPredom is not None:
                    if not (offInitTon
                            <= primPart.recurse().notes[SList[0]].offset
                            < offPredom):
                        harmonicCoordination = False
                        break
                else:
                    if not (offInitTon
                            <= primPart.recurse().notes[
                                SList[0]].offset
                            < offDom):
                        harmonicCoordination = False
                        break
                # check placement of predominant
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
                        u = primPart.recurse().notes[psi]
                        b = getBassNote(u, cxt)
                        if ((offPredom
                             <= primPart.recurse().notes[psi].offset
                             < offDom)
                                and vlChecker.isConsonanceAboveBass(b, u)):
                            structuralPredominant = True
                            break
                if not structuralPredominant:
                    harmonicCoordination = False
                    break
                # check placement of dominant
                if offPredom is None:
                    u = primPart.recurse().notes[SList[-1]]
                    b = getBassNote(u, cxt)
                    if ((offDom
                         <= primPart.recurse().notes[SList[-1]].offset
                         < offClosTon)
                            and vlChecker.isConsonanceAboveBass(b, u)):
                        harmonicCoordination = False
                        break

                # add pair to removal list if coordination tests not passed
                if not (structuralConsonances >= structConsReq
                        and harmonicCoordination):
                    nonharmonicParses.append(prse)

        if cxt.harmonicSpecies:
            preferredGlobals = [prse for prse in allGlobals
                            if prse not in nonharmonicParses]


        for pair in preferredGlobals:
            primPart.Pinterps = [pair[0]]
            bassPart.Binterps = [pair[1]]
            showInterpretations(cxt, show)
    elif len(cxt.parts) == 1:
        showInterpretations(cxt, show)


def showInterpretations(cxt, show, partSelection=None, partLineType=None):
    """
    Build interpretations for the context, gathering information from
    the parses of each line.
    """

    def buildInterpretation(parse):
        # Clean out slurs that might have been left behind by a previous parse.
        slurs = cxt.parts[parse.partNum].recurse().getElementsByClass(spanner.Slur)
        for slur in slurs:
            cxt.parts[parse.partNum].remove(slur)
        # TODO Remove not only slurs but also parentheses and colors.

        # BUILD the interpretation
        # Arcs, rules, and parens are tied to note indexes in the line,
        # and these are then attached to notes in the source part.
        gatherArcs(cxt.parts[parse.partNum], parse.arcs, parse.arcBasic)
        assignRules(cxt.parts[parse.partNum], parse.ruleLabels)
        assignParentheses(cxt.parts[parse.partNum], parse.parentheses)

    def selectOutput(content, show):
        if show == 'show':
            content.show()
        elif show == 'writeToServer':
            timestamp = str(time.time())
            filename = ('/home/spenteco/1/snarrenberg/parses_from_context/'
                        + 'parser_output_' + timestamp + '.musicxml')
            content.write('musicxml', filename)
            print(filename)
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

    if partSelection is not None:
        part = cxt.parts[partSelection]
        if partLineType == 'primary' and part.isPrimary:
            for PI in part.Pinterps:
                buildInterpretation(PI)
                selectOutput(part, show)
        elif partLineType == 'bass' and part.isBass:
            for BI in part.Binterps:
                buildInterpretation(BI)
                selectOutput(part, show)
        elif partLineType == 'generic' and part.isGeneric:
            for GI in part.Ginterps:
                buildInterpretation(GI)
                selectOutput(part, show)

    elif len(cxt.parts) == 1 and partLineType is None:
        part = cxt.parts[0]
        if part.Pinterps:
            for PI in part.Pinterps:
                buildInterpretation(PI)
                selectOutput(part, show)
        if part.Binterps:
            for BI in part.Binterps:
                buildInterpretation(BI)
                selectOutput(part, show)
        if part.Ginterps:
            for GI in part.Ginterps:
                buildInterpretation(GI)
                selectOutput(part, show)

    elif len(cxt.parts) == 1 and partLineType:
        part = cxt.parts[0]
        if partLineType == 'primary' and part.Pinterps:
            for PI in part.Pinterps:
                buildInterpretation(PI)
                selectOutput(part, show)
        elif partLineType == 'bass' and part.Binterps:
            for BI in part.Binterps:
                buildInterpretation(BI)
                selectOutput(part, show)
        elif partLineType == 'generic' and part.Ginterps:
            for GI in part.Ginterps:
                buildInterpretation(GI)
                selectOutput(part, show)

    elif len(cxt.parts) == 2 and partSelection is None:
        upperPart = cxt.parts[0]
        lowerPart = cxt.parts[1]
        for PI in upperPart.Pinterps:
            buildInterpretation(PI)
            for BI in lowerPart.Binterps:
                buildInterpretation(BI)
                selectOutput(cxt.score, show)
                time.sleep(2)

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
            buildInterpretation(UI)
            for II in innerPartPreferredInterps:
                buildInterpretation(II)
                for BI in lowerPart.Binterps:
                    buildInterpretation(BI)
                    selectOutput(cxt.score, show)
                    time.sleep(2)

    elif len(cxt.parts) > 3:
        error = 'Not yet able to display counterpoint in four or more parts.'
        raise context.ContextError(error)
    return


def logInterpretations(cxt, partSelection):
    """
    Write log file for interpretations for the context,
    gathering information from the parses of each line.
    """
    pass
    logInfo = []
    partsForParsing = validatePartSelection(cxt, partSelection)
    for part in partsForParsing:
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
    print('\n'.join(logInfo))

# -----------------------------------------------------------------------------
# OPERATIONAL SCRIPTS FOR PARSING DISPLAY
# -----------------------------------------------------------------------------


def gatherArcs(source, arcs, arcBasic=None):
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
    if arcBasic is not None:
        pass
        # consider using spanner.Line() in place of spanner.Slur(), as follows:
        # problem: cannot adjust the horizontal length of this spanner
#        UrArc = spanner.Line(lineType='solid', startHeight=25, tick='down')
#        source.insert(0, UrArc)
#        for ind in arcBasic:
#            obj = source.recurse().notes[ind]
#            UrArc.addSpannedElements(obj)


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
