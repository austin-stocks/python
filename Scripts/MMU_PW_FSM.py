import graphviz

# Create a directed graph object
# f = graphviz.Digraph('finite_state_machine', filename='fsm.gv')
f = graphviz.Digraph('MMU_PW_FSM',filename='MMU_PW_FSM', format="svg")
f.attr(rankdir='PR', size='8,16',label='MMU PW SM') # Set layout direction and size

# Define "doublecircle" shape for final states
f.attr('node', shape='ellipse',style='filled',fillcolor='lightblue',fontname='Arial',
       fontsize='10',fixedsize='True',fontstyle='bold',width='1.3')
f.node('MMU_PW_IDLE')
f.node('MMU_PW_START')
f.node('MMU_PW_L3_NESTED')
f.node('MMU_PW_L3')
f.node('MMU_PW_L3_PEND')
f.node('MMU_PW_L2_NESTED')
f.node('MMU_PW_L2')
f.node('MMU_PW_L2_PEND')
f.node('MMU_PW_L1_NESTED')
f.node('MMU_PW_L1')
f.node('MMU_PW_L1_PEND')
f.node('MMU_PW_L0_NESTED')
f.node('MMU_PW_L0')
f.node('MMU_PW_L0_PEND')
f.node('MMU_PW_FINAL_NESTED')
f.node('MMU_PW_AD_START')
f.node('MMU_PW_AD_WAIT')
f.node('MMU_PW_DONE')


f.edge('MMU_PW_IDLE','MMU_PW_START' , label='pwQ_ready')

f.edge('MMU_PW_START','MMU_PW_L3_NESTED',label='SV48 Hypervisor Enabled')
f.edge('MMU_PW_START','MMU_PW_L2_NESTED',label='SV39 Hypervisor Enabled')
f.edge('MMU_PW_START','MMU_PW_L3',label='SV48 Hypervisor Not Enabled')
f.edge('MMU_PW_START','MMU_PW_L2',label='SV39 Hypervisor Not Enabled')

f.edge('MMU_PW_L3_NESTED','MMU_PW_L3',label='Completed L3 nested Walk')
f.edge('MMU_PW_L3_NESTED','MMU_PW_DONE',label='Fault or Error')
f.edge('MMU_PW_L3','MMU_PW_L3_PEND',label='"PW Load Request')
f.edge('MMU_PW_L3_PEND','MMU_PW_L2_NESTED',label='Hypervisor Enabled')
f.edge('MMU_PW_L3_PEND','MMU_PW_L2',label='Hypervisor Not Enabled')
f.edge('MMU_PW_L3_PEND','MMU_PW_AD_START',label='A or D Update')
f.edge('MMU_PW_L3_PEND','MMU_PW_DONE',label='Fault or Error')

f.edge('MMU_PW_L2_NESTED','MMU_PW_L2',label='Completed L2 nested Walk')
f.edge('MMU_PW_L2_NESTED','MMU_PW_DONE',label='Fault or Error')
f.edge('MMU_PW_L2','MMU_PW_L2_PEND',label='PW Load Request')
f.edge('MMU_PW_L2_PEND','MMU_PW_L1_NESTED',label='Hypervisor Enabled')
f.edge('MMU_PW_L2_PEND','MMU_PW_L1',label='Hypervisor Not Enabled')
f.edge('MMU_PW_L2_PEND','MMU_PW_AD_START',label='A or D Update')
f.edge('MMU_PW_L2_PEND','MMU_PW_DONE',label='Fault or Error')

f.edge('MMU_PW_L1_NESTED','MMU_PW_L1',label='Completed L1 nested Walk')
f.edge('MMU_PW_L1_NESTED','MMU_PW_DONE',label='Fault or Error')
f.edge('MMU_PW_L1','MMU_PW_L1_PEND',label='PW Load Request')
f.edge('MMU_PW_L1_PEND','MMU_PW_L0_NESTED',label='Hypervisor Enabled')
f.edge('MMU_PW_L1_PEND','MMU_PW_L0',label='Hypervisor Not Enabled')
f.edge('MMU_PW_L1_PEND','MMU_PW_AD_START',label='A or D Update')
f.edge('MMU_PW_L1_PEND','MMU_PW_DONE',label='Fault or Error')

f.edge('MMU_PW_L0_NESTED','MMU_PW_L0',label='Completed L0 nested Walk')
f.edge('MMU_PW_L0_NESTED','MMU_PW_DONE',label='Fault or Error')
f.edge('MMU_PW_L0','MMU_PW_L0_PEND',label='PW Load Request')
f.edge('MMU_PW_L0_PEND','MMU_PW_FINAL_NESTED',label='Hypervisor Enabled')
f.edge('MMU_PW_L0_PEND','MMU_PW_AD_START',label='A or D Update')
f.edge('MMU_PW_L0_PEND','MMU_PW_DONE',label='Fault, Error or PW Completed')

f.edge('MMU_PW_FINAL_NESTED','MMU_PW_DONE',label='Completed Final nested Walk')

f.edge('MMU_PW_AD_START','MMU_PW_AD_WAIT',label='A/D Update Request')
f.edge('MMU_PW_AD_WAIT','MMU_PW_AD_WAIT',label='Wait for Request Completion')
f.edge('MMU_PW_AD_WAIT','MMU_PW_START',label='ReStart PW on successful completion')
f.edge('MMU_PW_AD_WAIT','MMU_PW_DONE',label='Fault or Error')

f.edge('MMU_PW_DONE','MMU_PW_IDLE',label='Return to idle')

f.render(view=True)

