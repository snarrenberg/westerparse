Getting Started
===============

First Questions
---------------

What music theory do I need to know? -- Users who are familiar with traditional species 
counterpoint may only need to consult Westergaard's rules:

   * :doc:`The Westergaard Rules <speciesrules>` 

If you are new to species counterpoint, you may find the following guide of use:
    
   * :download:`Species Counterpoint in the Tradition of Fux, Schenker, and Westergaard <SpeciesText.pdf>` 

What software do I need to install to run the project on my own system?

   * Python 3
   * `the music21 toolkit <http://web.mit.edu/music21/>`_
   * WesterParse
   * a music notation program like MuseScore

I just want to play around with it. Is there a website I can use instead of 
installing all this stuff? Yes.

   * Westegaardian Species Counterpoint Online: 
      
      * https://talus.artsci.wustl.edu/line_tester/
      * https://talus.artsci.wustl.edu/counterpoint_tester/

Where can I find more information about using the program?
 
   * :doc:`User's Guide to WesterParse <userguide>`


An Example
----------

Compose an exercise in music notation software or on the project website.
Save the exercise in MusicXML format.
Run the line parser or voice-leading checker.
In the case of the parser, you have the option of seeing 
the results displayed in musical notation. Otherwise you will see a text report.

Let's say you notate Fux's well-known Dorian cantus firmus using your favorite
notation software:

.. image:: images/FuxDorian.png
   :width: 600
   :alt: Fux Dorian cF

You can then ask WesterParse to parse the line:

.. code-block:: python

   >>> from westerparse import *
   >>> source = '../docs/samplefiles/FuxDorian.musicxml'
   >>> evaluateLines(source, 
   ...               show='show', 
   ...               partLineType='primary', 
   ...               report=True)

The program infers the key of D minor and attempts to parse the line as a primary
upper line. There are two possible interpretations (actually, there are a few more,
but the program exercises some preferential judgment and weeds out the less plausible
interpretations). 

The result could take the form of a text report:

.. code-block:: python

   PARSE REPORT
   Key inferred by program: D minor
   The line is generable as a primary line.

But since the keyword show was set to 'show', the program will display the 
interpretations in a notation program.

.. image:: images/FuxDorianP1.png
   :width: 600
   :alt: Fux Dorian cF, as PL1

.. image:: images/FuxDorianP2.png
   :width: 600
   :alt: Fux Dorian cF, as PL2
  

Installation Instructions
-------------------------

Python 3 can be obtained from: http://www.python.org.


1. Install ``music21``.

.. code-block:: shell

   $ pip install music21
   
   And then configure ``music21`` to use a musicxml viewer like MuseScore. 
   See the instructions on the `music21 website <http://web.mit.edu/music21/doc/installing/index.html>`_.

2. Download the latest WesterParse release from `GitHub <https://github.com/snarrenberg/westerparse/releases>`_. 
   and unzip it. For example:

.. code-block:: shell

   $ tar -xvf westerparse-1.0.3-alpha.tar.gz

3. Navigate to the ``src`` folder.

.. code-block:: shell

   $ cd westerparse-1.0.3-alpha/src/
   
4. Start python.

.. code-block:: shell

   $ python
   
5. Then begin using westerparse:

>>> from westerparse import *
>>> source = '../docs/samplefiles/FuxDorian.musicxml'
>>> evaluateLines(source, show='show', partLineType='primary', report=True)

            
How to Get Support
------------------

If you are having issues, please contact me at: snarrenberg@wustl.edu

License
-------

The project is licensed under the BSD license.