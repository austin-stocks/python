import wavedrom

# Define your timing diagram using the WaveJSON format
waveform_json = """
{
  "signal": [

    # ------------------------------------------------------------------
    # TLB Miss case
    # ------------------------------------------------------------------
    # Clocks
   {"name": "CLK", "wave": "P.............", "period": 1},
    # ------------------------------------------------------------------

    # Packet 
    {"name": "lsu_p.valid-d",                      "wave": "010."},
    {"name": "lsu_p.amo-d",                        "wave": "010."},
    {"name": "dc_rden-dc1",                        "wave": "0.10."},

    {"name": "cachehit-dc3",                       "wave": "0........"},

    {"name": "Bus Buffer Write-dc5",               "wave": "0.....10."},
    {"name": "AXI arvalid",                        "wave": "0......10."},
    {"name": "AXI rdata", "wave": "6.......|.26...", 
                          data:["X", "Data", "X"], },

    {"name": "GPR return Data-AMO Load Part", "wave": "6..........26..", 
                          data:["X", "Data", "X"], },
    {"name": "AMO Operation-fr2", "wave": "3..........23..", 
                          data:["X", "AMO-EXE", "X"], },
    {"name": "cache Write-fr3",                "wave": "0...........10."},
    {"name": "Cache Write Data-fr3", "wave": "3...........23.", 
                          data:["X", "Data", "X"], },

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
output_filename = r"C:\Sundeep\Akeana\LSU-Docs\Timing_Diagrams\AMO_CacheMiss.svg"
wavedrom.render(waveform_json).saveas(output_filename)

print(f"Waveform saved to {output_filename}")

# {"name": "clk", "wave": "P..................", "period": 2},
# {"name": "state_ifu", "wave": "3333x...", data: ["Idle", "4K", "2M", "1G"], },
