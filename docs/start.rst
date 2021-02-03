Getting Started
===============

First Questions
---------------

What music theory do I need to know? -- Users who are familiar with
traditional species counterpoint may only need to consult Westergaard's rules:

* :doc:`The Westergaard Rules <speciesrules>` 

If you are new to species counterpoint, you may find the following guide of use:
    
* :download:`Species Counterpoint in the Tradition of Fux, Schenker, and
  Westergaard <SpeciesText.pdf>` 

What software do I need to install to run the project on my own system?

* Python 3
* `the music21 toolkit <http://web.mit.edu/music21/>`_
* WesterParse
* a music notation program like MuseScore

I just want to play around with it. Is there a website I can use instead of 
installing all this stuff?

Yes:

* Westegaardian Species Counterpoint Online: 
      
  * https://ada.artsci.wustl.edu/westerparse/
      
If you want to know how the program interprets Westergaard's own examples of
counterpoint, you can use the WesterParse Corpus Viewer, which includes over
one hundred examples of lines and counterpoint, mainly drawn from
Westergaard's textbook.

* :doc:`Viewing the WesterParse Corpus <corpus>`

Where can I find more information about using the program?
 
* :doc:`User's Guide to WesterParse <userguide>`


An Example
----------

Using WesterParse directly is three-step process:

   #. Compose an exercise in music notation software or on the project website.
   
   #. Save the exercise in MusicXML format.
   
   #. Run the line parser or voice-leading checker.
   
In the case of the parser, you have the option of seeing 
the results displayed in musical notation. Otherwise you will see a text report.

Let's say you have notated Fux's well-known Dorian cantus firmus using your
favorite notation software:

.. image:: images/FuxDorian.png
   :width: 600
   :alt: Fux Dorian cF

You can then ask WesterParse to parse the line. (The code below shows how
to load the copy of Fux's melody that is included with WesterParse)

.. code-block:: python

   >>> from westerparse import *
   >>> source = '../docs/samplefiles/FuxDorian.musicxml'
   >>> evaluateLines(source, 
   ...               show='show', 
   ...               partLineType='primary', 
   ...               report=True)

The program infers the key of D minor and attempts to parse the line as
a primary upper line. There are two possible interpretations (actually,
there are a few more, but the program exercises some preferential judgment
and weeds out the less plausible interpretations). 

If the keyword :literal:`show` had been set to None, 
the result would have taken the form of a simple text report:

.. code-block:: python

   PARSE REPORT
   Key inferred by program: D minor
   The line is generable as a primary line.

But since the keyword :literal:`show` was set to 'show', the program will
display the interpretations in a notation program.

.. image:: images/FuxDorianP1.png
   :width: 600
   :alt: Fux Dorian cF, as PL1

.. image:: images/FuxDorianP2.png
   :width: 600
   :alt: Fux Dorian cF, as PL2


The annotations indicate the syntactic function of each note by referring
to the rule of construction that generates that particular note under this 
particular interpretation of the line.
(The rule labels are provided in :doc:`The Westergaard Rules <speciesrules>`.)
The slurs bind notes together into syntactic units, such as passing and
neighboring motions.  Notes shown in blue belong to the basic structure
of the line.


Installation Instructions
-------------------------

Python 3 can be obtained from: http://www.python.org.

Install ``music21``.

.. code-block:: shell

   $ pip install music21
   
And then configure ``music21`` to use a musicxml viewer like MuseScore. 
See the instructions on the
`music21 website <http://web.mit.edu/music21/doc/installing/index.html>`_.

Download the latest WesterParse release from
`GitHub <https://github.com/snarrenberg/westerparse/releases>`_,
place it in a directory of your choice, and unzip it.  For example:

To install directly from GitHub:

.. code-block:: shell

   $ git+git://github.com/snarrenberg/westerparse.git

Navigate to the main :literal:`westerparse` package directory
and start :literal:`python`.

.. code-block:: shell

   $ python
   
Then begin using :literal:`westerparse`:

>>> from westerparse import westerparse
>>> source = 'docs/samplefiles/FuxDorian.musicxml'
>>> westerparse.evaluateLines(source, 
...                           show='show',
...                           partLineType='primary',
...                           report=True)

   Your MusicXML viewer (Finale, NotePad, MuseScore) should open and display
   two parses of the line, and a parse report should print in your
   terminal window.
            
How to Get Support
------------------

If you are having issues, please contact me at: snarrenberg@wustl.edu

License
-------

The project is licensed under the BSD license.