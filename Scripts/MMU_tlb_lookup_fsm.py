import graphviz

# Create a directed graph object
# f = graphviz.Digraph('finite_state_machine', filename='fsm.gv')
output_filename =  r"C:\Sundeep\Akeana\MMU-Docs\Timing Diagrams\TLB_Lookup"
f = graphviz.Digraph('finite_state_machine',filename=output_filename, format="svg")
f.attr(rankdir='PR', size='8,8',label='TLB Lookup SM') # Set layout direction and size

# Define "doublecircle" shape for final states
f.attr('node', shape='ellipse',style='filled',fillcolor='lightblue',fontname='Arial',
       fontsize='10',fixedsize='True',fontstyle='bold',width='1.3')
f.node('MMU_IDLE')
f.node('MMU_LOOKUP_4K')
f.node('MMU_LOOKUP_2M')
f.node('MMU_LOOKUP_1G')
f.node('MMU_LOOKUP_512G')
f.node('MMU_LOOKUP_256T')
f.node('MMU_PAGEWALK')
f.node('MMU_DONE')

# Define transitions (edges) with labels
f.edge('MMU_IDLE', 'MMU_LOOKUP_4K'        ,label='TLB Req')

f.edge('MMU_LOOKUP_4K', 'MMU_LOOKUP_2M'   ,label='TLB Miss')
f.edge('MMU_LOOKUP_4K', 'MMU_DONE'        ,label='TLB Hit')

f.edge('MMU_LOOKUP_2M','MMU_LOOKUP_1G'    ,label='TLB Miss')
f.edge('MMU_LOOKUP_2M','MMU_DONE'         ,label='TLB Hit')

f.edge('MMU_LOOKUP_1G','MMU_LOOKUP_512G'  ,label='TLB Miss and\nsv48 or sv57')
f.edge('MMU_LOOKUP_1G','MMU_PAGEWALK'     ,label='TLB Miss and\nsv39')
f.edge('MMU_LOOKUP_1G','MMU_DONE'         ,label='TLB Hit')

f.edge('MMU_LOOKUP_512G','MMU_LOOKUP_256T',label='TLB Miss and\nsv57')
f.edge('MMU_LOOKUP_512G','MMU_PAGEWALK'   ,label='TLB Miss and \nsv48')
f.edge('MMU_LOOKUP_512G','MMU_DONE'       ,label='TLB Hit')

f.edge('MMU_LOOKUP_256T','MMU_PAGEWALK'   ,label='TLB Miss')
f.edge('MMU_LOOKUP_256T','MMU_DONE'       ,label='TLB Hit')

f.edge('MMU_PAGEWALK','MMU_DONE'          ,label='Start PW and \nHandover to PW SM')

f.edge('MMU_DONE','MMU_IDLE'              ,label='Return to IDLE')

# f.edge('LR_0', 'LR_1', label='SS(S)')
# f.edge('LR_1', 'LR_3', label='S($end)')
# f.edge('LR_2', 'LR_6', label='SS(b)')
# f.edge('LR_2', 'LR_5', label='SS(a)')
# f.edge('LR_2', 'LR_4', label='S(A)')
# f.edge('LR_5', 'LR_7', label='S(b)')
# f.edge('LR_5', 'LR_5', label='S(a)') # Example of a self-loop
# f.edge('LR_6', 'LR_6', label='S(b)')
# f.edge('LR_6', 'LR_5', label='S(a)')
# f.edge('LR_7', 'LR_8', label='S(b)')
# f.edge('LR_7', 'LR_5', label='S(a)')
# f.edge('LR_8', 'LR_6', label='S(b)')
# f.edge('LR_8', 'LR_5', label='S(a)')

# Render the graph to a file (e.g., fsm.gv.png) and open it
f.render(view=True)
