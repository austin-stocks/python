import wavedrom

# Define your timing diagram using the WaveJSON format
waveform_json = """
{
  "signal": [

    # ------------------------------------------------------------------
    # TLB Miss case
    # ------------------------------------------------------------------
    # Clocks
   {"name": "CLK", "wave": "P...........", "period": 1},
    # ------------------------------------------------------------------

    # Packet 
    {"name": "lsu_p.valid-d",                     "wave": "010."},
    {"name": "lsu_p.store-d",                     "wave": "010."},
    {"name": "dc_rden-dc1",                       "wave": "0.10."},

    {"name": "dc_rddata-dc2", "wave": "6..26..", 
                          data:["X", "Data", "X"], },
    {"name": "tag_hit-dc2",                     "wave": "0..10...."},
    {"name": "cachehit-dc3",                    "wave": "0...10..."},
    {"name": "St Buf Write-dc3",                "wave": "0...10..."},

    {"name": "St Buf Drain-dc6",                "wave": "0......10."},
    {"name": "St Buf Rd data", "wave": "3......23.", 
                          data:["X", "Data", "X"], },
    {"name": "cache Write",                "wave": "0......10."},

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
output_filename = r"C:\Sundeep\Akeana\LSU-Docs\Timing_Diagrams\Storehit_CacheWrite.svg"
wavedrom.render(waveform_json).saveas(output_filename)

print(f"Waveform saved to {output_filename}")

# {"name": "clk", "wave": "P..................", "period": 2},
# {"name": "state_ifu", "wave": "3333x...", data: ["Idle", "4K", "2M", "1G"], },
