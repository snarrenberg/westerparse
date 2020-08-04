WesterParse
===========

WesterParse implements the theory of tonal music presented in chapters 4-6
of *An Introduction to Tonal Theory* (New York: Norton, 1975) by Peter
Westergaard.  This portion of Westergaard's text develops a theory of
species counterpoint for classically tonal music.  An innovative feature
of the approach is the set of rules that define the closed tonal line.  In
effect, the line-generating rules implement the prolongational model of
tonal syntax originally developed by Heinrich Schenker.  Westergaard was
also interested in how the notes in one line interact with the notes in
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