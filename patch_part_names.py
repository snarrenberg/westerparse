#-------------------------------------------------------------------------------
# Name:         patch_part_names.py
# Purpose:      
# Author:       Stephen Pentecost
#-------------------------------------------------------------------------------
import sys
from lxml import etree

if __name__ == "__main__":

    input_file_name = sys.argv[1]
    evaluation_type = sys.argv[2]
    output_file_name = sys.argv[3]

    parser = etree.XMLParser(remove_blank_text=True)

    tree = etree.parse(input_file_name, parser)

    for p in tree.xpath('//tied[@type="stop"]'):
        d = p.xpath('ancestor::note/duration')[0]
        d.addnext(etree.XML('<tie type="stop"/>'))

    for p in tree.xpath('//tied[@type="start"]'):
        d = p.xpath('ancestor::note/duration|ancestor::note/tie[@type="stop"]')[-1]
        d.addnext(etree.XML('<tie type="start"/>'))

    for p in tree.xpath('//score-part'):

        if p.get('id') == 'P0':

            for p_name in p.xpath('descendant::part-name'):
                p_name.text = 'Primary Upper Line'
    
            b = etree.Element('part-abbreviation')
            b.text = 'PL'
            b.tail = '\n'

            p.append(b)

        if p.get('id') == 'P1':

            for p_name in p.xpath('descendant::part-name'):
                p_name.text = 'Bass Line'
    
            b = etree.Element('part-abbreviation')
            b.text = 'BL'
            b.tail = '\n'

            p.append(b)

    for p in tree.xpath('//note/type'):
        if p.text == 'long':
            p.text = 'whole'
        elif p.text == 'breve':
            p.text = 'half'
        elif p.text == 'whole':
            p.text = 'quarter'

    for p in tree.xpath('//divisions'):
        p.text = '1'

    for p in tree.xpath('//note'):
        
        note_type = p.xpath('descendant::type')[0]
        duration = p.xpath('descendant::duration')[0]
        
        if note_type.text == 'whole':
            duration.text = '4'
        elif note_type.text == 'half':
            duration.text = '2'
        elif note_type.text == 'quarter':
            duration.text = '1'
            
        print(duration.text)

    tree.write(output_file_name, pretty_print=True)
        
