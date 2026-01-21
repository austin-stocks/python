import wavedrom

# Define your timing diagram using the WaveJSON format
waveform_json = """
{
  "signal": [
  
    {"name": "clk", "wave": "101010101010101010101010101010101010101010101", "period":1},
    {"name": "clk_other", "wave": "p..................", "period": 2},

   
   
    # uTLB miss request from IFU
    {"name": "mmu_itlb_miss_req", "wave": "0.1.0........"},
    
    # TLB Lookup S/M
    {"name": "tlb_lookup_sm", "wave": "2.....2.2.2.2.2.", 
                          data:["Idle", "4K", "2M", "1G", "Done","Idle"], },
                          
    # TLB Lookup, miss
    {"name": "tlb_read", "wave": "0...1.......0."},
    {"name": "tlb_miss", "wave": "0.....1...0.."},
    {"name": "tlb_hit",  "wave": "0.........1.0"},
    {"name": "mmu_itlb_miss_ret_pkt.vld",    "wave": "0...........1.0.."},
    {},
    {},
    {},




    # uTLB miss request from IFU
    {"name": "mmu_itlb_miss_req", "wave": "0.1.0........"},
    
    # TLB Lookup S/M
    {"name": "tlb_lookup_sm", "wave": "2.....2.2.2.2.2.", 
                          data:["Idle", "4K", "2M", "1G", "PWALK","Idle"], },
                          
    # TLB Lookup, miss
    {"name": "tlb_read", "wave": "0...1.......0."},
    {"name": "tlb_miss", "wave": "0.....1.....0"},
    {},
    # PWQ write, PW S/M
    {"name": "pwQ_wren", "wave": "0...........1.0"},
    {"name": "pw_sm", "wave": "2.................2.2.2...|.2.", 
                          data:["Idle", "Start", "L4", "L4_PEND","Done"], },

    # LSU LDQ Write, PW request to LSU, PTE back
    {"name": "pwldQ_wren",     "wave": "0...................1.0"},
    {"name": "mmu_ld_req_vld", "wave": "0.....................1.0"},
    {},


    # PTE write to TLB, pkt return to IFU
    {"name": "lsu_mmu_req_ret_vld", "wave": "0.........................1.0"},
    {"name": "mmu_leaf_pte",        "wave": "0.........................1.0"},
    {"name": "TLB Write",           "wave": "0...........................1.0"},
    {"name": "mmu_itlb_miss_ret_pkt.vld",        "wave": "0...........................1.0"},
    {},


    {},
    {},
    {"name": "data", "wave": "x.345x|=.x", "data": ["head", "body", "tailed", "data"]},
    {"name": "req", "wave": "0.1..0|1.0"},
    {"name": "ack", "wave": "1.....|01."}
  ],
  
  config: { hscale: 1 },
  head:{
   text:"MMU Timing Diagram",
   tock:9
 },
}
"""

# Render the waveform and save it as an SVG file
# The output will be saved in your project directory
output_filename = "demo_waveform.svg"
wavedrom.render(waveform_json).saveas(output_filename)

print(f"Waveform saved to {output_filename}")

# {"name": "clk", "wave": "P..................", "period": 2},
# {"name": "state_ifu", "wave": "3333x...", data: ["Idle", "4K", "2M", "1G"], },
