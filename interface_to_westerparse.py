# -----------------------------------------------------------------------------
# Name:         interface_to_westerparse.py
# Purpose:      interface between WesterParse website and python code
# Author:       Stephen Pentecost
# -----------------------------------------------------------------------------
import sys
import westerparse
from multiprocessing import Process


if __name__ == "__main__":

    evaluation_type = sys.argv[1]
    keystep = sys.argv[2]
    keymodifier = sys.argv[3]
    mode = sys.argv[4]
    source = sys.argv[5]
    display_type = sys.argv[6]

    if display_type == 'None':
        display_type = None

    keynote = None
    if keystep > '' and keymodifier == 'flat':
        keynote = keystep + '-'
    elif keystep > '' and keymodifier == 'sharp':
        keynote = keystep + '#'
    elif keystep > '' and keymodifier == '':
        keynote = keystep

    if evaluation_type == 'any':
        evaluation_type = None

    print('interface_to_westerparse.py',
          'evaluation_type', evaluation_type,
          'display_type', display_type,
          'keystep', keystep,
          'keymodifier', keymodifier,
          'mode', mode,
          'keynote', keynote,
          '\n\t',
          'source', source)

    if display_type == 'writeToServer':

        if evaluation_type in ['primary', 'generic', 'bass', None]:

            context_process = Process(target=westerparse.evaluateLines,
                                      args=(source,),
                                      kwargs={'show': 'writeToServer',
                                              'partLineType': evaluation_type,
                                              'keynote': keynote,
                                              'mode': mode})

        else:

            context_process = Process(target=westerparse.evaluateLines,
                                      args=(source,),
                                      kwargs={'show': 'writeToServer',
                                              'keynote': keynote,
                                              'mode': mode})

    elif evaluation_type == 'primary':

        context_process = Process(target=westerparse.evaluateLines,
                                  args=(source,),
                                  kwargs={'show': None,
                                          'partSelection': 0,
                                          'partLineType': evaluation_type,
                                          'keynote': keynote,
                                          'mode': mode})

    elif evaluation_type == 'bass':

        context_process = Process(target=westerparse.evaluateLines,
                                  args=(source,),
                                  kwargs={'show': None,
                                          'partSelection': 0,
                                          'partLineType': evaluation_type,
                                          'keynote': keynote,
                                          'mode': mode})

    elif evaluation_type == 'generic':

        context_process = Process(target=westerparse.evaluateLines,
                                  args=(source,),
                                  kwargs={'show': None,
                                          'partSelection': 0,
                                          'partLineType': evaluation_type,
                                          'keynote': keynote,
                                          'mode': mode})

    elif evaluation_type is None:

        context_process = Process(target=westerparse.evaluateLines,
                                  args=(source,),
                                  kwargs={'show': None,
                                          'partSelection': 0,
                                          'partLineType': evaluation_type,
                                          'keynote': keynote,
                                          'mode': mode})

    elif evaluation_type == 'upper line':

        context_process = Process(target=westerparse.evaluateLines,
                                  args=(source,),
                                  kwargs={'show': None,
                                          'partSelection': 0,
                                          'partLineType': 'primary',
                                          'keynote': keynote,
                                          'mode': mode})

    elif evaluation_type == 'bass line':

        context_process = Process(target=westerparse.evaluateLines,
                                  args=(source,),
                                  kwargs={'show': None,
                                          'partSelection': -1,
                                          'partLineType': 'bass',
                                          'keynote': keynote,
                                          'mode': mode})

    elif evaluation_type == 'inner line':

        context_process = Process(target=westerparse.evaluateLines,
                                  args=(source,),
                                  kwargs={'show': None,
                                          'partSelection': 1,
                                          'partLineType': 'generic',
#                                          'partLineType': ['primary',
#                                                           'generic'],
                                          'keynote': keynote,
                                          'mode': mode})

    elif evaluation_type == 'counterpoint':

        context_process = Process(target=westerparse.evaluateCounterpoint,
                                  args=(source,),
                                  kwargs={'report': True,
                                          'keynote': keynote,
                                          'mode': mode})

    else:
        print('interface_to_context.py ERROR -- Invalid evaluation_type')

    context_process.start()
    context_process.join(timeout=60)
    context_process.terminate()
