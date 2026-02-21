import graphviz

# Create a directed graph object
# f = graphviz.Digraph('finite_state_machine', filename='fsm.gv')
output_filename =  r"C:\Sundeep\Akeana\MMU-Docs\Timing Diagrams\MMU_NESTED_PW"
f = graphviz.Digraph('MMU_PW_FSM',filename=output_filename, format="jpeg")
# f.attr(rankdir='TB', size='16,16',label='MMU PW SM') # Set layout direction and size
f.attr(rankdir='TB', width='8',lenght='11',label='MMU NESTED PW SM') # Set layout direction and size

# Define "doublecircle" shape for final states
f.attr('node', shape='ellipse',style='filled',fillcolor='lightblue',fontname='Arial',
       fontsize='10',fixedsize='True',fontstyle='bold',width='1.3')
f.node('MMU_NESTED_PW_IDLE')
f.node('MMU_NESTED_PW_L3')
f.node('MMU_NESTED_PW_L3_PEND')
f.node('MMU_NESTED_PW_L2')
f.node('MMU_NESTED_PW_L2_PEND')
f.node('MMU_NESTED_PW_L1')
f.node('MMU_NESTED_PW_L1_PEND')
f.node('MMU_NESTED_PW_L0')
f.node('MMU_NESTED_PW_L0_PEND')
f.node('MMU_NESTED_PW_AD_START')
f.node('MMU_NESTED_PW_AD_WAIT')
f.node('MMU_NESTED_PW_DONE')

f.edge('MMU_NESTED_PW_IDLE','MMU_NESTED_PW_L3', label='Start Nested')

f.edge('MMU_NESTED_PW_L3','MMU_NESTED_PW_L3_PEND', label='PW Load Request')
f.edge('MMU_NESTED_PW_L3_PEND','MMU_NESTED_PW_AD_START', label='A or D Update')
f.edge('MMU_NESTED_PW_L3_PEND','MMU_NESTED_PW_DONE', label='Fault or Error')
f.edge('MMU_NESTED_PW_L3_PEND','MMU_NESTED_PW_L2', label='Ld Return Completed; goto next level')

f.edge('MMU_NESTED_PW_L2','MMU_NESTED_PW_L2_PEND', label='PW Load Request')
f.edge('MMU_NESTED_PW_L2_PEND','MMU_NESTED_PW_AD_START', label='A or D Update')
f.edge('MMU_NESTED_PW_L2_PEND','MMU_NESTED_PW_DONE', label='Fault or Error')
f.edge('MMU_NESTED_PW_L2_PEND','MMU_NESTED_PW_L1', label='Ld Return Completed; goto next level')

f.edge('MMU_NESTED_PW_L1','MMU_NESTED_PW_L1_PEND', label='PW Load Request')
f.edge('MMU_NESTED_PW_L1_PEND','MMU_NESTED_PW_AD_START', label='A or D Update')
f.edge('MMU_NESTED_PW_L1_PEND','MMU_NESTED_PW_DONE', label='Fault or Error')
f.edge('MMU_NESTED_PW_L1_PEND','MMU_NESTED_PW_L0', label='Ld Return Completed; goto next level')

f.edge('MMU_NESTED_PW_L0','MMU_NESTED_PW_L0_PEND', label='PW Load Request')
f.edge('MMU_NESTED_PW_L0_PEND','MMU_NESTED_PW_AD_START', label='A or D Update')
f.edge('MMU_NESTED_PW_L0_PEND','MMU_NESTED_PW_DONE', label='Fault, Error or PW Completed')

f.edge('MMU_NESTED_PW_AD_START','MMU_NESTED_PW_AD_WAIT', label='A/D Update Request')
f.edge('MMU_NESTED_PW_AD_WAIT','MMU_NESTED_PW_AD_WAIT', label='Wait for Request Completion')
f.edge('MMU_NESTED_PW_AD_WAIT','MMU_NESTED_PW_IDLE', label='ReStart PW on successful completion')
f.edge('MMU_NESTED_PW_AD_WAIT','MMU_NESTED_PW_DONE', label='Fault or Error')

f.edge('MMU_NESTED_PW_DONE','MMU_NESTED_PW_IDLE', label='Return to idle')


f.render(view=True)

