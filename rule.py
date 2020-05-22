class Rule():
    """ A rule that can be assigned as an attribute to a Note in a Lyne """
    validRuleScopes = ('global', 'local')
    def __init__(self, name=None, lineType=None, scope=None, level=None, index=None):
        self.name = name # S1, E1, B1
        self.lineType = lineType
        self.scope = scope # global, local??
        self.level = level
        self.index = index # creates an attribute for tracking the position of a rule in a Lyne 
#        self.type # transition, insertion (stepto, insert)
#        self.subtype # I, R, P, N, IN, IP ...

    def __repr__(self):
        return str(self.name)        

class StepTo(Rule):
    ''' the generic rule for generating transitions '''
    # has a direction of approach: ascending, descending
    # has a completion value: true, false
    # perhaps also has a completion object: 
    # has a name: STEPTO
    pass
    
class Insert(Rule):
    ''' the generic rule for generating framing insertions '''
    # has a name: INSERT
    pass        
    
class Insertion(Insert):
    ''' the specific rule for generating non-repetitive framing insertions '''
    # has a left parenthesis value: true, false
    # has a right parenthsis value: true, false
    # has a name: E3
    pass        

class Repetition(Insert):
    ''' the specific rule for generating repetitive framing insertions '''
    # has an initiation object
    # has a right paren value: true, false
    # has a name: E1
    pass        

class Passing(StepTo):
    ''' the generic rule for generating unidirectional transitions '''
    # has both an initiation and a completion object
    # has a direction, derivable from the agreement of approaches
    # has a name: E4
    pass
    
class Neighboring(StepTo):
    ''' the generic rule for generating bidirectional transitions '''
    # has both an initiation and a completion object
    # has a position: upper or lower, derivable from approach
    # has a name: E2
    pass

if __name__ == "__main__":
    # self_test code
    pass
