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

import time
import logging
import unittest

from music21 import *

import parser
import vlChecker
from context import *
from utilities import pairwise

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

selectPreferredParseSets = False
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
    """
    clearLogfile('logfile.txt')
    if partLineType == 'any' or '':
        partLineType = None
    try:
        cxt = makeGlobalContext(source, **kwargs)
    except EvaluationException as fce:
        fce.show()
        return
    try:
        parseContext(cxt, show, partSelection, partLineType)
        if show is None or report is True:
            print(cxt.parseReport)
        return True
    except EvaluationException as fce:
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
    clearLogfile('logfile.txt')
    try:
        cxt = makeGlobalContext(source, **kwargs)
    except EvaluationException as fce:
        fce.show()
        return
    try:
        if len(cxt.parts) == 1:
            raise ContextError(
                  'Context Error: The composition is only a single line. '
                  'There is no voice-leading to check.')
    except ContextError as ce:
        ce.logerror()
    try:
        if len(cxt.parts) == 1:
            raise EvaluationException
    except EvaluationException as ee:
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
    gxt = GlobalContext(s, **kwargs)
    return gxt


def makeLocalContext(cxt, cxtOn, cxtOff, cxtHarmony):
    """
    Create a local context given a start and stop offset
    in an enclosing Context.
    [Not functional.]
    """
    locCxt = cxt.getElementsByOffset(cxtOn,
                                     cxtOff,
                                     includeEndBoundary=True,
                                     mustFinishInSpan=False,
                                     mustBeginInSpan=True,
                                     includeElementsThatEndAtStart=False,
                                     classList=None)
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


def parseContext(context,
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
    context.errorsDict = {}
    for part in context.parts:
        context.errorsDict[part.name] = {}

    # validate part selection and line type selection
    try:
        partsForParsing = validatePartSelection(context, partSelection)
    except ContextError as ce:
        ce.logerror()
        raise EvaluationException
    try:
        lineTypeSelection = validateLineTypeSelection(context,
                                                      partSelection,
                                                      partLineType)
    except ContextError as ce:
        ce.logerror()
        raise EvaluationException

    # Run the parser and collect errors.
    for part in partsForParsing:
        # Set the part's lineType if given by the user.
        if partLineType:
            part.lineType = partLineType
        else:
            part.lineType = None
        # Parse the selected part.
        parsePart(part, context)
        # Collect errors.
        if part.errors:
            context.errorsDict[part.name]['parser errors'] = part.errors
        if part.typeErrorsDict:
            for key, value in part.typeErrorsDict.items():
                context.errorsDict[part.name][key] = value

    # Determine whether all parts are generable.
    generableParts = 0
    generableContext = False
    if partSelection is None:
        for part in context.parts:
            if part.isPrimary or part.isBass or part.isGeneric:
                generableParts += 1
        if generableParts == len(context.parts):
            generableContext = True
    elif partSelection is not None:
        rules = [context.parts[partSelection].isPrimary,
                 context.parts[partSelection].isBass,
                 context.parts[partSelection].isGeneric]
        if any(rules):
            generableContext = True

    # Create the optional parse report for user
    # and a required error report if errors arise.
    def createParseReport():
        # Base string for reporting parse results.
        context.parseReport = 'PARSE REPORT'

        # Gather information on the key to report to the user.
        if context.keyFromUser:
            result = ('Key supplied by user: ' + context.key.nameString)
            context.parseReport = context.parseReport + '\n' + result
        else:
            result = ('Key inferred by program: ' + context.key.nameString)
            context.parseReport = context.parseReport + '\n' + result

        if generableContext is True:
            if partSelection is not None or len(context.parts) == 1:
                if partSelection is not None:
                    part = context.parts[partSelection]
                else:
                    part = context.parts[0]
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
                        if context.errorsDict[part.name][partLineType]:
                            for err in context.errorsDict[part.name][partLineType]:
                                error = error + '\n\t\t' + str(err)
                        raise ContextError(error)
                # Update parse report if no errors found.
                context.parseReport = context.parseReport + '\n' + result

            elif partSelection is None and len(context.parts) > 1:
                upperPrimary = False
                genericUpperLines = []
                lowerBass = False
                for part in context.parts[0:-1]:
                    if part.isPrimary:
                        upperPrimary = True
                    else:
                        genericUpperLines.append(part.name)
                if context.parts[-1].isBass:
                    lowerBass = True
                if upperPrimary and lowerBass:
                    if len(context.parts) == 2:
                        result = ('The upper line is generable as a '
                                  'primary line. \nThe lower line '
                                  'is generable as a bass line.')
                    else:
                        result = ('At least one upper line is generable '
                                  'as a primary line. \nThe lower line '
                                  'is generable as a bass line.')
                # ERRORS
                elif not upperPrimary and lowerBass:
                    if len(context.parts) == 2:
                        error = ('\tThe upper line is not generable '
                                 'as a primary line. \nBut the lower '
                                 'line is generable as a bass line.')
                    else:
                        error = ('\tNo upper line is generable as a '
                                 'primary line. \nBut the lower line '
                                 'is generable as a bass line.')
                    for gul in genericUpperLines:
                        if context.errorsDict[gul]:
                            error = (error + '\n\tThe following linear '
                                     'errors were found in ' + gul + ':')
                            for err in context.errorsDict[gul]['primary']:
                                error = error + '\n\t\t\t' + str(err)
                    raise ContextError(error)
                elif upperPrimary and not lowerBass:
                    if len(context.parts) == 2:
                        error = ('\tThe upper line is generable as a '
                                 'primary line. \nBut the lower line '
                                 'is not generable as a bass line.')
                    else:
                        error = ('\tAt least one upper line is generable '
                                 'as a primary line. \nBut the lower line '
                                 'is not generable as a bass line.')
                    bln = context.parts[-1].name
                    if context.errorsDict[bln]:
                        error = (error + '\n\tThe following linear '
                                 'errors were found in the bass line:')
                        for err in context.errorsDict[bln]['bass']:
                            error = error + '\n\t\t\t' + str(err)
                    raise ContextError(error)
                elif not upperPrimary and not lowerBass:
                    if len(context.parts) == 2:
                        error = ('\tThe upper line is not generable as a '
                                 'primary line. \nNor is the lower line '
                                 'generable as a bass line.')
                    else:
                        error = ('\tNo upper line is generable as '
                                 'a primary line. \nNor is the lower '
                                 'line generable as a bass line.')
                    for part in context.parts[:-1]:
                        if context.errorsDict[part.name]:
                            error = (error + '\n\tThe following linear '
                                     'errors were found in ' + part.name + ':')
                            for err in context.errorsDict[part.name]['primary']:
                                error = error + '\n\t\t\t' + str(err)
                    bln = context.parts[-1].name
                    if context.errorsDict[bln]:
                        error = (error + '\n\tThe following linear errors '
                                 'were found in the bass line:')
                        for err in context.errorsDict[bln]['bass']:
                            error = error + '\n\t\t\t' + str(err)
                    raise ContextError(error)
                # Update parse report if no errors found.
                context.parseReport = context.parseReport + '\n' + result

        elif generableContext is False:
            # Get header and key information from parse report.
            error = context.parseReport + '\n' + 'Line Parsing Errors'
            if len(partsForParsing) == 1:
                part = partsForParsing[0]
                error = (error + '\n\tThe following linear errors were '
                         'found when attempting to interpret the line:')
                try:
                    context.errorsDict[part.name]['parser errors']
                except KeyError:
                    pass
                else:
                    for err in context.errorsDict[part.name]['parser errors']:
                        error = error + '\n\t\t\t' + str(err)
                    if not context.errorsDict[part.name]['parser errors']:
                        error = error + '\n\t\t\tUnspecified error.'
                try:
                    context.errorsDict[part.name]['primary']
                except KeyError:
                    pass
                else:
                    for err in context.errorsDict[part.name]['primary']:
                        error = error + '\n\t\t\t' + str(err)
                try:
                    context.errorsDict[part.name]['bass']
                except KeyError:
                    pass
                else:
                    for err in context.errorsDict[part.name]['bass']:
                        error = error + '\n\t\t\t' + str(err)
                raise ContextError(error)
            else:
                for part in context.parts[:-1]:
                    if context.errorsDict[part.name] == {} and part.isPrimary:
                        error = (error + '\n\t' + part.name +
                                 ' is generable as a primary line.')
                    elif (context.errorsDict[part.name] == {}
                          and not part.isPrimary and part.isGeneric):
                        error = (error + '\n\t' + part.name +
                                 ' is generable as a generic line.')
                    else:
                        error = (error + '\n\t' + part.name +
                                 ' is not generable. '
                                 'The following errors were found:')
                    try:
                        context.errorsDict[part.name]['parser errors']
                    except KeyError:
                        pass
                    else:
                        for err in context.errorsDict[part.name]['parser errors']:
                            error = error + '\n\t\t\t' + str(err)
                    try:
                        context.errorsDict[part.name]['primary']
                    except KeyError:
                        pass
                    else:
                        for err in context.errorsDict[part.name]['primary']:
                            error = error + '\n\t\t\t' + str(err)
                for part in context.parts[-1:]:
                    if context.errorsDict[part.name] == {} and part.isBass:
                        error = (error + '\n\t' + part.name +
                                 ' is generable as a bass line.')
                    else:
                        error = (error + '\n\t' + part.name +
                                 ' is not generable. '
                                 'The following errors were found:')
                    try:
                        context.errorsDict[part.name]['parser errors']
                    except KeyError:
                        pass
                    else:
                        for err in context.errorsDict[part.name]['parser errors']:
                            error = error + '\n\t\t\t' + str(err)
                    try:
                        context.errorsDict[part.name]['bass']
                    except KeyError:
                        pass
                    else:
                        for err in context.errorsDict[part.name]['bass']:
                            error = error + '\n\t\t\t' + str(err)

            raise ContextError(error)

    try:
        createParseReport()
    except ContextError as ce:
        ce.logerror()
        raise EvaluationException
    else:
        pass

        if show is not None:
            # Preferences currently only work for two-part counterpoint.
            # Preference can be turned off by setting
            # selectPreferredParseSets to False
            if (1 < len(context.parts) < 3
               and partSelection is None
               and selectPreferredParseSets):
                selectedPreferredParseSets(context, show)
            else:
                showInterpretations(context, show, partSelection, partLineType)


def validatePartSelection(context, partSelection):
    if partSelection is not None:
        try:
            context.parts[partSelection]
        except IndexError:
            if len(context.parts) == 1:
                pts = ' part'
            else:
                pts = ' parts'
            raise ContextError(
                'Context Error: The composition has only '
                + str(len(context.parts)) + pts
                + ', so the part selection must fall in the range of 0-'
                + str(len(context.parts)-1)
                + '. Hence the selection of part '
                + str(partSelection) + ' is invalid.')
        else:
            if partSelection >= 0:
                partsSelected = context.parts[partSelection:partSelection+1]
            else:
                partsSelected = context.parts[partSelection::partSelection-1]
    elif len(context.parts) == 1:
        partsSelected = context.parts[0:1]
    elif partSelection is None:
        partsSelected = context.parts
    return partsSelected


def validateLineTypeSelection(context, partSelection, partLineType):
    if partLineType is not None:
        if len(context.parts) == 1 or partSelection is not None:
            return
        else:
            pass
        raise ContextError(
            'Context Error: You have selected the following line type: '
            + f'{partLineType}. \nHowever, line type selection is only permitted '
            + 'when the source is a single line \nor there is a valid '
            + 'part selection.'
            )


def parsePart(part, context):
    """
    Parse a given part.

    Create a (:py:class:`~parser.Parser`) for the part and
    collect the results.  Determine whether the line is generable as a primary,
    bass, or generic line.  Compile a list of ways the line can be generated
    for each line type, if at all. Collect a list of parsing errors.
    """
    # Run the parser.
    partParser = parser.Parser(part, context)
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


def selectedPreferredParseSets(context, show):
    """
    Select sets of parses according to preference rules.

    After parsing the individual parts, select sets of parses
    based on Westergaard preference rules, trying to negotiate the best match
    between global structures in the parts. [This currently works
    only for two-part counterpoint.]
    """
    # TODO need to refine the preferences substantially
    if len(context.parts) > 1:
        # Select uppermost part that isPrimary as the primaryPart.
        # This is arbitrary.
        primPart = None
        for part in context.parts[:-1]:
            if part.isPrimary:
                primPart = part
                break
        # Select lowest part as the bassPart.
        bassPart = context.parts[-1]

        primaryS3Finals = [i.S3Final for i
                           in primPart.interpretations['primary']]
        bassS3s = [i.S3Index for i in bassPart.interpretations['bass']]
        preferredGlobals = []
        domOffsetDiffList = []  # structural Dominant Offset Differences List
        lowestDifference = 100
        for interpPrimary in primPart.interpretations['primary']:
            for interpBass in bassPart.interpretations['bass']:
                a = primPart.recurse().flat.notes[interpPrimary.S3Final].offset
                b = bassPart.recurse().flat.notes[interpBass.S3Index].offset
                domOffsetDiff = (a - b)
                if abs(domOffsetDiff) < lowestDifference:
                    lowestDifference = domOffsetDiff
                domOffsetDiffList.append((domOffsetDiff, (interpPrimary,
                                                          interpBass)))
#                    if interpBass.S3Index == interpPrimary.S3Final:
#                        preferredGlobals.append((interpPrimary, interpBass))
        for pair in domOffsetDiffList:
            if abs(pair[0]) == abs(lowestDifference):
                preferredGlobals.append(pair[1])
        for pair in preferredGlobals:
            primPart.Pinterps = [pair[0]]
            bassPart.Binterps = [pair[1]]
            showInterpretations(context, show)
    elif len(context.parts) == 1:
        showInterpretations(context, show)


def showInterpretations(context, show, partSelection=None, partLineType=None):
    """
    Build interpretations for the context, gathering information from
    the parses of each line.
    """

    def buildInterpretation(parse):
        # Clean out slurs that might have been left behind by a previous parse.
        slurs = context.parts[parse.partNum].recurse().getElementsByClass(spanner.Slur)
        for slur in slurs:
            context.parts[parse.partNum].remove(slur)
        # TODO Remove not only slurs but also parentheses and colors.

        # BUILD the interpretation
        # Arcs, rules, and parens are tied to note indexes in the line,
        # and these are then attached to notes in the source part.
        gatherArcs(context.parts[parse.partNum], parse.arcs, parse.arcBasic)
        assignRules(context.parts[parse.partNum], parse.ruleLabels)
        assignParentheses(context.parts[parse.partNum], parse.parentheses)

    def selectOutput(content, show):
        if show == 'show':
            content.show()
        elif show == 'writeToServer':
            timestamp = str(time.time())
            filename = ('/home/spenteco/1/snarrenberg/parses_from_context/'
                        + 'parser_output_' + timestamp + '.musicxml')
            content.write('musicxml', filename)
            print(filename)
        elif show == 'writeToLocal':
            timestamp = str(time.time())
            filename = ('parses_from_context/'
                        + 'parser_output_' + timestamp + '.musicxml')
            content.write('musicxml', filename)
            print(filename)
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
        part = context.parts[partSelection]
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

    elif len(context.parts) == 1 and partLineType is None:
        part = context.parts[0]
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

    elif len(context.parts) == 1 and partLineType:
        part = context.parts[0]
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

    elif len(context.parts) == 2 and partSelection is None:
        upperPart = context.parts[0]
        lowerPart = context.parts[1]
        for PI in upperPart.Pinterps:
            buildInterpretation(PI)
            for BI in lowerPart.Binterps:
                buildInterpretation(BI)
                selectOutput(context.score, show)
                time.sleep(2)

    elif len(context.parts) == 3 and partSelection is None:
        upperPart = context.parts[0]
        innerPart = context.parts[1]
        lowerPart = context.parts[2]
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
                    selectOutput(context.score, show)
                    time.sleep(2)

    elif len(context.parts) > 3:
        error = 'Not yet able to display counterpoint in four or more parts.'
        raise ContextError(error)
    return


def logInterpretations(context, partSelection):
    """
    Write log file for interpretations for the context,
    gathering information from the parses of each line.
    """
    pass
    logInfo = []
    partsForParsing = validatePartSelection(context, partSelection)
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


def gatherArcs(source, arcs, arcBasic):
    """
    Given a fully parsed line (an interpretation), sort through the arcs and
    create a music21 spanner (tie/slur) to represent each arc.
    """
    # Source is a Part in the input Score.
    # Sort through the arcs and create a spanner(tie/slur) for each.
    tempArcs = []
    # Skip duplicate arcs.
    for elem in arcs:
        if elem not in tempArcs:
            tempArcs.append(elem)
    arcs = tempArcs
    # Build arcs.
    for arc in arcs:
        arcBuild(source, arc)
    # TODO Set up separate function for the basic arc.
    if arcBasic is not None:
        pass
        # consider using spanner.Line() in place of spanner.Slur(), as follows:
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
    source.insert(0, thisSlur)
    for ind in arc:
        obj = source.recurse().notes[ind]
        thisSlur.addSpannedElements(obj)


def assignRules(source, rules):
    """
    Given a fully parsed line (an interpretation), add a lyric to each
    note to show the syntactic rule that generates the note.
    Also assigns the color
    blue to notes generated by a rule of basic structure.
    """
    # Source is a Part in the input Score.
    ruleLabels = rules
    for index, elem in enumerate(source.recurse().notes):
        for rule in ruleLabels:
            if index == rule[0]:
                elem.lyric = rule[1]
                if elem.lyric is not None and elem.lyric[0] == 'S':
                    elem.style.color = 'blue'
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
        #evaluateLines(source)


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()

# -----------------------------------------------------------------------------
# eof
