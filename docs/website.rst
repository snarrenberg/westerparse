WesterParse Web Site
====================

.. figure:: images/WesterParseWebFlow.png
   :width: 400
   :alt: WesterParse Web Flow Chart
   :align: center
   :figwidth: 400
   
   How WesterParse works behind the scenes on the web site.
   
   ..


Westegaardian Species Counterpoint Online
-----------------------------------------

URL: https://talus.artsci.wustl.edu/westerparse/

The web interface was created by Stephen Pentecost, Senior Digital 
Humanities Specialist at Washington University in St. Louis.

Initial Setup
-------------

The user decides the number of lines (1, 2, or 3), the key
signature, the time signature, and the number of measures. Once editing mode
is entered, the user may add or delete measures, but the other options cannot
be edited. The user may also enter an exercise name and their own name; these
will be added to the score as title and composer, respectively.

Composition
-----------

Upon pressing Create Score, the web enters the edit screen,
and the user can now commence with adding notes to the score.
To make corrections, press the Change Notes button.  To return to composing,
press Add Notes..

Syntax Parsing
--------------

After completing a composition, the user can have
WesterParse evaluate the syntax of each line.
The result is displayed beneath the music.
For example:

.. code-block:: shell

   PARSE REPORT
   Key inferred by program: C major
   The line is generable as a primary line but not as a bass line.
   
If WesterParse was unable to infer a single key for the composition, perhaps
because the line is not unambiguously in a single key,
the user has the option of selecting a key, thereby forcing WesterParse
to use that selection. 

The final line of the report states whether the line is generable as a
monotriadic line. If it is, WesterParse reports the types of line that are valid
interpretations. In the example above, the line could be interpreted as a
primary line (and, by implication, also as a generic line), but not as a bass
line. If the line was not generable in any fashion, WesterParse would identify
errors of composition, if possible. For example:

.. code-block:: shell

   Line Parsing Errors
   The following linear errors were found when attempting
   to interpret the line:
			
			The non-tonic-triad pitch D4 in measure 4 cannot be generated.

If the composition is a single line, the user may select a type of line
(primary, bass, or generic). When the Evaluate Line button is pressed,
WesterParse will look only to see whether the line can be evaluated using
the selected type.

If the composition consists of two parts, WesterParse will try to
parse the upper line as a primary line and the lower line as a bass line.
And if the composition has three parts, it will try to parse at least one of
the upper lines as a primary line and the lower line as a bass line.

If the Display Parse option is enabled, the user can have WesterParse prepare
up to three possible parses of the composition, which will be displayed on
the web page in the are below the composition.  WesterParse often considers
dozens of different interpretations for each line of composition, but then
sifts through them to select the most plausible interpretations.

Voice Leading
-------------

If the user has composed counterpoint in two or
three parts, the user can have WesterParse check the voice leading.
This, too, will generate a report.
Ideally, the user wants to see the following report:

.. code-block:: shell

   No voice-leading errors found.
   
In less than ideal circumstances, the user may encounter a report such as this:

.. code-block:: shell

   Voice Leading Report 

 	 The following voice-leading errors were found:
		
		 Forbidden parallel motion to octave going into bar 2.
	  
	  Forbidden parallel motion to fifth going into bar 4.
		 
		 Prohibited leap of a fourth in bars 2 to 3.

File Download
-------------

At any point, the user has the option of downloading
the composition in the form of a MusicXML file.  This file can then be opened
and edited in any music notation program (e.g., MuseScore, Finale, StaffPad).
