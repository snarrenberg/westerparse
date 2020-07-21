User's Guide
============

Basic Instructions
------------------

Start python in your terminal program.

.. code-block:: shell
   
   $ python

Then import WesterParse and choose a source file:

>>> import westerparse
>>> source = 'PATH/my_music.musicxml'

To parse the lines in the source:

>>> westerparse.evaluateLines(source)

To check the voice leading:

>>> westerparse.evaluateCounterpoint(source)

Parser Options
--------------

When evaluating lines, there are several options that a user can select. These must be
entered as keyword arguments.

- :literal:`show`
- :literal:`report`
- :literal:`partSelection`
- :literal:`partLineType`
- :literal:`keynote` and :literal:`mode`

The options for :literal:`show` determine how the parsing results will be displayed in musical 
notation. The valid options are: :literal:`None`, :literal:`'show'`, :literal:`'writeToServer'`, 
:literal:`'writeToLocal'`, :literal:`writeToPng'`, and :literal:`'showWestergaardParse'`.

:literal:`None` is the default option. :literal:`None` will suppress notated 
output and generate a text report instead. 

:literal:`'show'` will send the output to the notation program that the user has configured for use
with music21. The parse is shown using a modified Schenkerian notation.

>>> westerparse.evaluateLines(source, show='show')

:literal:`'writeToServer'` is used by the web site to write parses to musicxml files, which are then 
displayed in the browser window. 

:literal:`'writeToLocal'` can be used to write parses to a local directory.  [The user can select 
a directory by editing the configuration.py file.] By default, the files are written to 
'parses_from_context/'.  The name for each file consists of the prefix 'parser_output\_', 
a timestamp, and the suffix '.musicxml'.

:literal:`'writeToPng'` uses the application MuseScore to produce png files, which can then 
be used as illustrations.  In the process, MuseScore first generates an xml file and 
from that derives the png file. These are named with the prefix 'parser_output\_',  
a timestamp, and the appropriate suffix.  Note that Musescore inserts '-1' before 
adding the '.png' suffix.  The default directory for these files is 'tempimages/'. 
[This, too, can be changed by editing the configuration.py file.]

:literal:`'showWestergaardParse'` can be used if the source consists of only one line. It will 
display the parse(s) of a line using Westergaard's layered form of representation. 
[This option is not yet functional.]
 
If one or more lines in the source cannot be parsed (i.e., if there are syntax errors), 
the program will automatically generate a text report. If the user also wants to see a 
report on successful parses, the :literal:`report` option can be set to :literal:`True`. The default is :literal:`False`.
However, if :literal:`show=None`, then a report will be generated automatically regardless
of the option set for the report.

With :literal:`partSelection`, a user can designate a line of the composition to parse. 
The default is :literal:`None`, which in effect selects all of the lines for parsing.
Following the conventions of music21, lines are numbered from top to bottom, starting with
0. Since parts are a list, Python conventions are followed. So to select the bass line, 
a user can set the option as follows:

>>> westerparse.evaluateLines(source, partSelection=-1)

The option :literal:`partLineType` can only be used if the composition is a single line or if
the user has used the partSelection option. The options are as follows: :literal:`None`, :literal:`'primary'`, 
:literal:`'bass'`, and :literal:`'generic'`.

The default option is :literal:`None`, which has different meanings depending on the source. 
If the source is a single line or the user has selected a part, the parser will 
try to evaluate the line as each of the three types. If the composition has two lines, the
parser will evaluate the upper line as a primary line and the lower line as a bass line. 
And if there are more than three parts, the parser will evaluate the upper lines as either
primary or generic (with the stipulation that at least one must be a primary line), and will
evaluate the lower line as a bass line.

>>> westerparse.evaluateLines(source, partSelection=0, partLineType='primary')

The program automatically attempts to infer the key of the composition using a custom
algorithm. There may be cases where a composition is ambiguous, in which case, the 
user may override the program's inference by specifying a keynote and mode. The program will
then validate the user's selection and, if valid, will attempt to parse the composition
in the given key. The options are:

:literal:`knote` must be a capital letter in the set A, B, ..., G followed by either a hyphen (-)
to represent a flat or a hash (#) to represent a sharp. This must be a string, 
enclosed in quotation marks.
:literal:`kmode` must be either :literal:`'major'` or :literal:`'minor'`. 

>>> westerparse.evaluateLines(source, knote='G-', kmode='major)

Voice-Leading Checker Options
-----------------------------

At present, there are no user-selectable options. In a future release, the user will have
the option of checking the counterpoint for compliance with Westergaard's preference
rules for sonority. 