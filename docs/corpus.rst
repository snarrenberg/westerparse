Viewing the WesterParse Corpus
==============================

To test for compliance with Westergaard's rules, I have assembled a small 
corpus of examples, including many from Westergaard's book (these are identified by
page number in the filename). There are over 60 single lines and over 50 examples of two-part 
counterpoint, some with errors and others without. 

Requires Tkinter, PIL, and MuseScore.

Using the Corpus Viewer
-----------------------

Locate the corpus viewer module in the examples folder 
and then run the program from the terminal.

.. code-block:: ..
   
   $ python3 viewer.py

This will open a GUI.

Select a corpus to view: either lines or counterpoint.

Select a file in the list. The music will automatically display in the bottom panel.

If the file is a single line, you may select what line type to evaluate. 
Choose 'any' to get all of the possible parses.

If the file is counterpoint, you may choose either to evaluate the counterpoint or 
display the the linear syntax (i.e., the parses of the lines). If you choose to display
the syntax, be patient, as it takes several seconds for MuseScore to generate the image
files that will be displayed onscreen. The viewer can display up to four parses. In most
cases, the number of preferred parses does not exceed this number. The viewer displays
a message indicating the total number of preferred parses.

Brief reports on parsing and voice leading are displayed above the music. 

