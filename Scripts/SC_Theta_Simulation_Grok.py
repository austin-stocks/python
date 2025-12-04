# ULTIMATE DYNAMIC SCENARIO SIMULATOR — WITH FULL MILESTONE PRINT-OUT
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
import datetime
import re
import csv

def black_scholes_price(S, K, T, r, sigma, option_type="call"):
    if T <= 0:
        return max(S - K, 0) if option_type == "call" else max(K - S, 0)
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    if option_type == "call":
        return S * norm.cdf(d1) - K * np.exp(-r*T) * norm.cdf(d2)
    else:
        return K * np.exp(-r*T) * norm.cdf(-d2) - S * norm.cdf(-d1)

# ========================
# INPUTS
# ========================
print("ULTIMATE DYNAMIC SCENARIO SIMULATOR + MILESTONE REPORT".center(100, "="))
side = input("\nBUY or SELL? (buy/sell): ").strip().lower()
option_type = input("Call or Put? (c/p): ").strip().lower()
option_type = "call" if option_type.startswith('c') else "put"

S0 = float(input("Current stock price ($): "))
K = float(input("Strike price ($): "))
actual_price = float(input("Your traded option price ($ per share): "))

expiry_input = input("Expiry date (YYYY-MM-DD) OR DTE number: ").strip()
if re.match(r'^\d{4}-\d{2}-\d{2}$', expiry_input):
    expiry = datetime.datetime.strptime(expiry_input, "%Y-%m-%d").date()
    days_to_expiry = (expiry - datetime.date.today()).days
else:
    days_to_expiry = int(expiry_input)

iv_input = input("Implied Volatility (e.g. 0.35) — press Enter for 35%: ").strip()
IV = 0.35 if iv_input == "" else float(iv_input)
print(f"Using IV = {IV:.1%}")

while True:
    try:
        n_scenarios = int(input("\nHow many price scenarios at expiry? (1-10): ").strip())
        if 1 <= n_scenarios <= 10: break
        else: print("Enter 1–10.")
    except: print("Invalid input.")

targets = []
scenario_names = []
print(f"\nEnter {n_scenarios} target stock prices at expiry:")
for i in range(n_scenarios):
    name = input(f"  Scenario {i+1} name: ").strip()
    while True:
        try:
            price = float(input(f"  → {name or 'Target'} price ($): "))
            break
        except: print("Enter a number.")
    targets.append(price)
    scenario_names.append(name if name else f"Scenario {i+1}")

base_colors = ['#d62728', '#1f77b4', '#2ca02c', '#ff7f0e', '#9467bd',
               '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
line_colors = base_colors[:n_scenarios]
box_colors = [c + 'dd' for c in base_colors[:n_scenarios]]

r = 0.03
if days_to_expiry <= 0:
    print("DTE must be > 0!")
    exit()

# ========================
# SIMULATION
# ========================
dates = [datetime.date.today() + datetime.timedelta(days=i) for i in range(days_to_expiry + 1)]
x = np.arange(len(dates))

all_spot_paths = []
all_option_paths = []
all_milestones = []  # Will store readable data for printing

for target, name in zip(targets, scenario_names):
    spot = []
    opt = []
    milestones = []

    for i in range(days_to_expiry + 1):
        frac = i / days_to_expiry if days_to_expiry > 0 else 0
        S_t = S0 + frac * (target - S0)
        T = (days_to_expiry - i) / 365.0
        theo = black_scholes_price(S_t, K, T, r, IV, option_type)
        spot.append(S_t)
        opt.append(theo)

    # Find 50%, 25%, 10%
    for level in [0.50, 0.25, 0.10]:
        target_val = actual_price * level
        hits = np.where(np.array(opt) <= target_val)[0]
        if len(hits) > 0:
            idx = hits[0]
            milestones.append({
                'idx': idx,
                'level': level,
                'price': opt[idx],
                'date': dates[idx].strftime('%b %d %Y'),
                'y_base': opt[idx]
            })
        else:
            milestones.append(None)

    all_spot_paths.append(spot)
    all_option_paths.append(opt)
    all_milestones.append(milestones)

# ========================
# PRINT MILESTONE SUMMARY
# ========================
print("\n" + " MILESTONE SUMMARY (50% / 25% / 10% remaining) ".center(100, "="))
print(f"{'Scenario':<12} {'50%':<20} {'25%':<20} {'10%':<20}")
print("-" * 100)
for i, name in enumerate(scenario_names):
    row = f"{name:<12}"
    for level in [0.50, 0.25, 0.10]:
        ms = next((m for m in all_milestones[i] if m and m['level'] == level), None)
        if ms:
            row += f"{ms['date']} (${ms['price']:.3f})     ".ljust(20)
        else:
            row += "Never reached        ".ljust(20)
    print(row)
print("=" * 100)

# ========================
# SMART BOX PLACEMENT
# ========================
boxes_to_plot = []
for scen_idx, ms_list in enumerate(all_milestones):
    for ms in ms_list:
        if ms:
            boxes_to_plot.append({**ms, 'scenario': scen_idx, 'name': scenario_names[scen_idx]})

boxes_to_plot.sort(key=lambda b: b['idx'])
placed = {}
for box in boxes_to_plot:
    key = box['idx']
    placed.setdefault(key, []).append(box)

for day_boxes in placed.values():
    n = len(day_boxes)
    for i, b in enumerate(day_boxes):
        b['y_offset'] = actual_price * 0.045 * (i - (n-1)/2)
        b['x_offset'] = 0.7 * (i - (n-1)/2)

# ========================
# CHART
# ========================
print("\nLaunching final chart...")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)

for i in range(n_scenarios):
    ax1.plot(x, all_option_paths[i], color=line_colors[i], linewidth=3.5,
             label=f'{scenario_names[i]} → ${targets[i]:.1f}')

ax1.axhline(actual_price, color='gray', linestyle='--', linewidth=2, label=f'Entry ${actual_price:.3f}')
ax1.set_ylabel("Option Price ($)", fontsize=12)
ax1.set_title(f"{n_scenarios}-SCENARIO SIMULATOR + MILESTONES\n"
              f"{option_type.upper()} {K} | {days_to_expiry} DTE | IV {IV:.1%}", fontsize=14, pad=15)
ax1.grid(alpha=0.3)
ax1.legend(loc='upper right', fontsize=9.5, framealpha=0.94)

# Boxes
for box in boxes_to_plot:
    x_pos = box['idx'] + box.get('x_offset', 0)
    y_pos = box['y_base'] + box.get('y_offset', 0)
    pct = int(box['level']*100)
    text = f"${box['price']:.3f}\n{box['date']}\n{pct}%\n{box['name']}"
    ax1.text(x_pos, y_pos, text, fontsize=9, ha='center', va='center', weight='bold', color='white',
             bbox=dict(boxstyle="round,pad=0.48", facecolor=box_colors[box['scenario']],
                       edgecolor='black', linewidth=1.3))

# Stock paths
for i in range(n_scenarios):
    ax2.plot(x, all_spot_paths[i], color=line_colors[i], linewidth=3)
ax2.axhline(K, color='red', linestyle='--', linewidth=2, alpha=0.8)
ax2.set_ylabel("Stock Price ($)", fontsize=11)
ax2.set_xlabel("Date", fontsize=12)
ax2.grid(alpha=0.3)

step = max(1, len(dates)//14)
ax2.set_xticks(x[::step])
ax2.set_xticklabels([dates[i].strftime('%b %d %Y') for i in range(0, len(dates), step)],
                    rotation=45, ha='right', fontsize=9.5)

plt.tight_layout()
plt.subplots_adjust(hspace=0.08)
plt.show()

print("\nYou now have:")
print("• Full printed milestone table")
print("• All boxes visible on chart")
print("• Dynamic number of scenarios")
print("• Crystal-clear insight")
print("\nThis is the ultimate theta weapon.")
print("Go collect.")