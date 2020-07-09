.. WesterParse documentation master file

WesterParse
===========

WesterParse implements the theory of tonal music presented in chapters 4-6 of 
*An Introduction to Tonal Theory* (New York: Norton, 1975) by Peter Westergaard. 
This portion of Westergaard's text develops a theory of species counterpoint for 
classically tonal music. An innovative feature of the approach is the set of rules
that define the closed tonal line. In effect, the line-generating rules implement
Heinrich Schenker's concept of fundamental structure (*Ursatz*), together with a 
repertory of ways for elaborating that structure. Westergaard was also interested in
how the notes in one line interact with the notes in another, and he had many 
interesting insights into how listeners use the rules as they negotiate the interpretation
of two or more lines unfolding simultaneously. WesterParse already incorporates many
of the cognitive preferences identified by Westergaard. The plan is ultimately to include 
all of the preference rules as well as giving users the option of activating each rule.

There are two main components to WesterParse: a *parser* that evaluates the structure of 
musical lines used in species counterpoint, and a *checker* that evaluates the
voice leading of species counterpoint compositions. 

Westergaard's innovative contribution to the pedagogical discipline of species 
counterpoint was the formulation of a syntax for contrapuntal lines and an explication 
of the cognitive issues involved in how listeners parse the syntax of such lines. 
Hence the name of this program, **WesterParse**.

.. figure:: images/ITTfigures.png
   :width: 300
   :alt: Westergaard stick figures p. 9
   :align: center
   :figwidth: 400
   
   Blah, blah, blah: developing a shared metalanguage for the musical object language (Westergaard 1975, 9)
   
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


