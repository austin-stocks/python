import graphviz

# Create a directed graph object
# f = graphviz.Digraph('finite_state_machine', filename='fsm.gv')
output_filename =  r"C:\Sundeep\Akeana\LSU-Docs\State_Machines\bb_fsm"
f = graphviz.Digraph('finite_state_machine',filename=output_filename, format="svg")
f.attr(rankdir='TB', center='True',size='16,32',label='Bus Buffer SM') # Set layout direction and size

# Define "doublecircle" shape for final states
f.attr('node', shape='ellipse',style='filled',fillcolor='lightblue',fontname='Arial',
       fontsize='10',fixedsize='True',fontstyle='bold',width='1.3')
f.node('IDLE')
f.node('WAIT')
f.node('CMD')
f.node('RESP')
f.node('DONE')

# Define transitions (edges) with labels
# f.edge('IDLE' , 'IDLE' , label=' ')
f.edge('IDLE' , 'WAIT' , label='Snoop Pend')
f.edge('IDLE' , 'CMD'  , label='No Snoop Pend')

f.edge('WAIT' , 'WAIT' , label='Snoop Pend')
f.edge('WAIT' , 'CMD'  , label='No Snoop Pend')

f.edge('CMD' , 'RESP'  , label='Sent Req')

f.edge('RESP' , 'RESP'  , label='Wait for Rsp')
f.edge('RESP' , 'IDLE'  , label='Rsp, no err and nc')
f.edge('RESP' , 'DONE'  , label=' ')

f.edge('DONE' , 'IDLE'  , label=' ')

f.render(view=True)
