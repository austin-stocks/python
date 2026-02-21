import wavedrom

# Define your timing diagram using the WaveJSON format
waveform_json = """
{
  "signal": [

    # ------------------------------------------------------------------
    # Evict because of snoop request on AXI
    # ------------------------------------------------------------------
    # Clocks
   {"name": "CLK", "wave": "P....................", "period": 1},
    # ------------------------------------------------------------------

    # Packet 
    {"name": "axi_acvalid",                 "wave": "010."},
    {"name": "axi_acsnoop", "wave": "626..", 
                          data:["X", "SNP", "X"], },

    {"name": "snpreq-sn0",                  "wave": "0.10................."},
    {"name": "snpreq-sn1",                  "wave": "0..10................"},
    {"name": "snpreq-sn3",                  "wave": "0...10..............."},
    {"name": "evreq-ev0",                   "wave": "0....10.............."},
    {"name": "evreq-ev1",                   "wave": "0.....10............."},
    {"name": "evreq-ev2",                   "wave": "0......10............"},
    {"name": "dc-read",                     "wave": "0......10............"},
    {"name": "evreq-ev3",                   "wave": "0.......10..........."},
    {"name": "Cache-EVData-ev3",            "wave": "6.......26...........", data:["X", "Data", "X"], },
    {"name": "Cache-EVData-ev4",            "wave": "6........26..........", data:["X", "Data", "X"], },
    {"name": "EB-State Machine",            "wave": "8.........88.......8.", data:["IDLE", "CMD", "RESP","IDLE"], },
    {"name": "EVData-in-evbuf",             "wave": "6.........26.........", data:["X", "Data", "X"], },
    {"name": "EVData-in-evobuf",            "wave": "6..........26........", data:["X", "Data", "X"], },
    {"name": "lsu_axi_awvalid",             "wave": "0..........10........"},
    {"name": "lsu_axi_wdata",               "wave": "3..........23........", data:["X", "Data", "X"], },
    {"name": "lsu_axi_bvalid",              "wave": "0................10.."},

    {},
    {}
    # ------------------------------------------------------------------

  ],
}
"""

# Render the waveform and save it as an SVG file
# The output will be saved in your project directory
output_dir = "\\..\\..\\..\\..\\..\\Akeana"
# output_filename = output_dir + "\\" + "demo_waveform.svg"
output_filename = r"C:\Sundeep\Akeana\LSU-Docs\Timing_Diagrams\Evict_dueto_Snoop.svg"
wavedrom.render(waveform_json).saveas(output_filename)

print(f"Waveform saved to {output_filename}")

# {"name": "clk", "wave": "P..................", "period": 2},
# {"name": "state_ifu", "wave": "3333x...", data: ["Idle", "4K", "2M", "1G"], },
