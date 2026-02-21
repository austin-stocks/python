import graphviz

# Create a directed graph object
# f = graphviz.Digraph('finite_state_machine', filename='fsm.gv')
output_filename =  r"C:\Sundeep\Akeana\MMU-Docs\Timing Diagrams\sfence_fsm"
f = graphviz.Digraph('finite_state_machine',filename=output_filename, format="svg")
f.attr(rankdir='TB', center='True',size='16,32',label='SFENCE SM') # Set layout direction and size

# Define "doublecircle" shape for final states
f.attr('node', shape='ellipse',style='filled',fillcolor='lightblue',fontname='Arial',
       fontsize='10',fixedsize='True',fontstyle='bold',width='1.3')
f.node('MMU_SFENCE_IDLE')
f.node('MMU_SFENCE_SCAN_TLB')
f.node('MMU_SFENCE_LOOKUP_4K')
f.node('MMU_SFENCE_LOOKUP_2M')
f.node('MMU_SFENCE_LOOKUP_1G')
f.node('MMU_SFENCE_LOOKUP_512G')
f.node('MMU_SFENCE_LOOKUP_256T')
f.node('MMU_SFENCE_DONE')

# Define transitions (edges) with labels
f.edge('MMU_SFENCE_IDLE' , 'MMU_SFENCE_DONE' , label='Full TLB request\nInvalidate all entries')
f.edge('MMU_SFENCE_IDLE' , 'MMU_SFENCE_SCAN_TLB' ,  label='ID Based Request',labelangle='75',labeldistance='5')
f.edge('MMU_SFENCE_IDLE' , 'MMU_SFENCE_LOOKUP_4K' , label='\n\n\nAddress Based Request')

f.edge('MMU_SFENCE_SCAN_TLB' , 'MMU_SFENCE_SCAN_TLB' , label='Scan Each Entry and\ninvalidate match')
f.edge('MMU_SFENCE_SCAN_TLB' , 'MMU_SFENCE_DONE' , label='Scan Complete')

f.edge('MMU_SFENCE_LOOKUP_4K' , 'MMU_SFENCE_LOOKUP_2M' , label='Invalidate Match')

f.edge('MMU_SFENCE_LOOKUP_2M' , 'MMU_SFENCE_LOOKUP_1G' , label='Invalidate Match')

f.edge('MMU_SFENCE_LOOKUP_1G' , 'MMU_SFENCE_LOOKUP_512G' , label='Invalidate Match\nsv48 or sv57')
f.edge('MMU_SFENCE_LOOKUP_1G' , 'MMU_SFENCE_DONE' , label='Invalidate Match\nsv39')

f.edge('MMU_SFENCE_LOOKUP_512G' , 'MMU_SFENCE_LOOKUP_256T' , label='Invalidate Match\nsv57')
f.edge('MMU_SFENCE_LOOKUP_512G' , 'MMU_SFENCE_DONE' , label='Invalidate Match\nsv48')

f.edge('MMU_SFENCE_LOOKUP_256T' , 'MMU_SFENCE_DONE' , label='Invalidate Match')

f.edge('MMU_SFENCE_DONE' , 'MMU_SFENCE_IDLE' , label='Return to idle')


f.render(view=True)
