#-------------------------------------------------------------------------------
# Name:         patch_parse_files.py
# Purpose:      
# Author:       Stephen Pentecost
#-------------------------------------------------------------------------------
import sys
from lxml import etree

input_file_name = sys.argv[1]

parser = etree.XMLParser(remove_blank_text=True)

tree = etree.parse(input_file_name, parser)

for p in tree.xpath('//creator|//part-name|//part-abbreviation'):
    p.text = ' '
    
for p in tree.xpath('//work-title'):
    p.text = ' '

for p in tree.xpath('//movement-title'):
    p.getparent().remove(p) 
    
tree.write(input_file_name, 
            xml_declaration='<?xml version="1.0" encoding="utf-8"?>',
            pretty_print=True)
        
