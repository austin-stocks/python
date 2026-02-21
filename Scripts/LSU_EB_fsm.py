import graphviz

# Create a directed graph object
# f = graphviz.Digraph('finite_state_machine', filename='fsm.gv')
output_filename =  r"C:\Sundeep\Akeana\LSU-Docs\State_Machines\ev_fsm"
f = graphviz.Digraph('finite_state_machine',filename=output_filename, format="svg")
f.attr(rankdir='TB', center='True',size='16,32',label='') # Set layout direction and size

# Define "doublecircle" shape for final states
f.attr('node', shape='ellipse',style='filled',fillcolor='lightblue',fontname='Arial',
       fontsize='10',fixedsize='True',fontstyle='bold',width='1.3')
f.node('IDLE')
f.node('CMD')
f.node('RESP')

# Define transitions (edges) with labels
# f.edge('IDLE' , 'IDLE' , label=' ')
f.edge('IDLE' , 'IDLE' , label='Wait for Evict Req')
f.edge('IDLE' , 'CMD'  , label='EV Buf written')

f.edge('CMD'  , 'CMD'  , label='Wait for EV Obuf \nWrite')
f.edge('CMD'  , 'RESP' , label='EV Obuf written\nBus Cmd Sent')

f.edge('RESP' , 'RESP'  , label='Wait for bresp')
f.edge('RESP' , 'IDLE'  , label='Resp rcvd')


f.render(view=True)
