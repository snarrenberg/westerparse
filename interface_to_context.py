import sys
import context

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

    print('interface_to_linear_parser.py', 
            'evaluation_type', evaluation_type, 
            'display_type', display_type,
            'keystep', keystep, 
            'keymodifier', keymodifier, 
            'mode', mode, 
            'keynote', keynote, 
            '\n\t', 
            'source', source)

    if display_type == 'writeToServer':
        
        context.evaluateLines(source, 
                                show='writeToServer', 
                                keynote=keynote,
                                mode=mode)
                                
    elif evaluation_type == 'upper line':
        
        context.evaluateLines(source, 
                                show=None, 
                                partSelection= 0, 
                                partLineType='primary',
                                keynote=keynote,
                                mode=mode)
                            
    elif evaluation_type == 'bass line':

        context.evaluateLines(source, 
                                show=None, 
                                partSelection= 1, 
                                partLineType='bass',
                                keynote=keynote,
                                mode=mode)
                            
    elif evaluation_type == 'counterpoint':

        context.evaluateCounterpoint(source, 
                                report=True, 
                                keynote=keynote,
                                mode=mode)

    else:
        print('interface_to_context.py ERROR -- Invalid evaluation_type')
