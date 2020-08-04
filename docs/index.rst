.. WesterParse documentation master file

WesterParse
===========

Peter Westergaard significantly improved the pedagogical discipline of
species counterpoint by formulating a syntax for contrapuntal
lines and explicating the cognitive issues involved in how listeners
parse the syntax of such lines.  Hence the name of this program,
**WesterParse**.

WesterParse implements the theory of tonal music presented in chapters 4-6
of Westergaard's textbook, *An Introduction to Tonal Theory*
(New York: Norton, 1975).  This portion of Westergaard's text develops
a theory of species counterpoint for classically tonal music.  An innovative
feature of the approach is the set of rules that define the closed tonal
line.  In effect, these line-generating rules implement the prolongational
model of tonal syntax originally developed by Heinrich Schenker.  Westergaard
was also interested in how the notes in one line interact with the notes in
another, and he had many interesting insights into how listeners use the
rules as they negotiate the interpretation of two or more lines unfolding
simultaneously.  WesterParse already incorporates many of the cognitive
preferences identified by Westergaard.  The plan is ultimately to include
all of the preference rules as well as giving users the option of
activating each rule.

There are two main components to WesterParse: a *parser* that evaluates
the structure of musical lines used in species counterpoint, and
a *checker* that evaluates the voice leading of species counterpoint
compositions.

One task of music theory is to model the procedural knowledge of
stylistically competent listeners.  In his textbook, Westergaard focused
on developing a shared metalanguage for discussing classically tonal music.
(See the figure below.)  WesterParse provides many additional refinements
to this metalanguage, such as the articulation of syntactic memory
units (in the form of lists for tracking open heads and transitions) and
various methods for retrospectively reinterpreting syntactic structure to
cope with novel events.



.. figure:: images/ITTfigures.png
   :width: 300
   :alt: Westergaard stick figures p. 9
   :align: center
   :figwidth: 400
   
   Blah, blah, blah: developing a shared metalanguage for the musical
   object language (Westergaard 1975, 9)
   
   ..


.. toctree::
   :maxdepth: 2

   start
   speciesrules
   userguide
   website
   corpus
   modulesdoc
   license
      

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


