# ULTIMATE PRICE DECAY — Full table + CSV export + Year on chart + Clean boxes
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
print("\nULTIMATE Option Price Decay Calculator + CSV Export".center(90, "="))
print("Takes various inputs and generates the price of the option over time")

side = input("\nBUY or SELL? (buy/sell): ").strip().lower()
option_type = input("Call or Put? (c/p): ").strip().lower()
option_type = "call" if option_type.startswith('c') else "put"

S = float(input("Current stock price ($): "))
K = float(input("Strike price ($): "))
actual_price = float(input("Your traded price ($ per share): "))

expiry_input = input("Expiry date (YYYY-MM-DD) OR DTE number: ").strip()
if re.match(r'^\d{4}-\d{2}-\d{2}$', expiry_input):
    expiry = datetime.datetime.strptime(expiry_input, "%Y-%m-%d").date()
    days_to_expiry = (expiry - datetime.date.today()).days
else:
    days_to_expiry = int(expiry_input)
    expiry = datetime.date.today() + datetime.timedelta(days=days_to_expiry)

iv_input = input("Implied Volatility (e.g. 0.35) — press Enter for 35%: ").strip()
IV = 0.35 if iv_input == "" else float(iv_input)
print(f"Using IV = {IV:.1%}")

r = 0.03
if days_to_expiry <= 0:
    print("DTE must be > 0!")
    exit()

theo_today = black_scholes_price(S, K, days_to_expiry/365.0, r, IV, option_type)

# ========================
# SIMULATION
# ========================
dates = []
theo_prices = []
pnl_per_share = []

for days_left in range(days_to_expiry, -1, -1):
    current_date = datetime.date.today() + datetime.timedelta(days=(days_to_expiry - days_left))
    T = days_left / 365.0
    theo = black_scholes_price(S, K, T, r, IV, option_type)
    decayed = theo_today - theo
    pnl = decayed if side.startswith('s') else -decayed

    dates.append(current_date)
    theo_prices.append(theo)
    pnl_per_share.append(pnl)

# ========================
# MILESTONES
# ========================
x = np.arange(len(dates))
theo_arr = np.array(theo_prices)

milestones = []
for level in [0.50, 0.25, 0.10]:
    target = actual_price * level
    hits = np.where(theo_arr <= target)[0]
    if len(hits) > 0:
        idx = hits[0]
        price = theo_prices[idx]
        date_str = dates[idx].strftime('%b %d %Y')
        milestones.append((idx, level, price, date_str))
    else:
        milestones.append((None, level, None, "Never"))

# ========================
# FINAL SUMMARY
# ========================
total_pnl = pnl_per_share[-1] * 100

print("\n" + " FINAL RESULT ".center(100, "="))
print(f"Option            : {option_type.upper()} {K} {'SHORT' if side.startswith('s') else 'LONG'}")
print(f"Entry premium     : ${actual_price:.3f}")
print(f"Theoretical today : ${theo_today:.3f}")
print(f"Total P&L at expiry : ${total_pnl:8.2f} per contract")
for i, (idx, level, price, dstr) in enumerate(milestones):
    pct = int(level * 100)
    if price is not None:
        print(f"{pct}% remaining    : {dstr} → ${price:.3f}")
    else:
        print(f"{pct}% remaining    : Never reached")
print("="*100)

# ========================
# FULL TABLE + CSV EXPORT
# ========================
print("\n" + "Daily Price Decay".center(90, "-"))
print(f"{'Date':<15} {'DTE':>5} {'Theo Price':>12} {'P&L/Contract':>16} {'% of Entry':>12}")
print("-" * 90)

# Prepare data for CSV
csv_data = []
csv_data.append(["Date", "DTE", "Theo_Price", "PnL_per_Contract", "%_of_Entry"])

for i in range(len(dates)):
    dte = days_to_expiry - i
    pnl_contract = pnl_per_share[i] * 100
    pct = theo_prices[i] / actual_price * 100 if actual_price > 0 else 0
    date_str = dates[i].strftime('%Y-%m-%d')  # ISO format for CSV

    print(f"{dates[i].strftime('%b %d %Y'):<15} {dte:5d} ${theo_prices[i]:10.3f}   ${pnl_contract:12.2f}    {pct:7.1f}%")

    csv_data.append([date_str, dte, round(theo_prices[i], 4), round(pnl_contract, 2), round(pct, 1)])

print("-" * 90)

# Save to CSV
csv_filename = "price_decay.csv"
with open(csv_filename, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(csv_data)

print(f"Full table saved as: {csv_filename}")

# ========================
# FINAL CHART
# ========================
print("\nLaunching final chart...")
plt.figure(figsize=(18, 10))

plt.plot(x, theo_prices, color='#d62728', linewidth=4.5, label='Option Price Decay')
plt.axhline(actual_price, color='blue', linestyle='--', linewidth=2.8, label=f'Entry: ${actual_price:.3f}')
plt.axhline(0, color='black', linewidth=1.2, alpha=0.6)

box_colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
labels = ['50%', '25%', '10%']

for (idx, level, price, datestr), color, label in zip(milestones, box_colors, labels):
    if idx is not None:
        plt.axvline(idx, color='gray', linestyle='--', alpha=0.7, linewidth=1.8)
        text = f"${price:.3f}\n{datestr}\n{label}"
        plt.text(idx, price, text,
                 fontsize=14, ha='center', va='center', weight='bold', color='white',
                 bbox=dict(boxstyle="round,pad=0.7", facecolor=color, edgecolor='black', linewidth=2.5))

plt.title(f"{option_type.upper()} PRICE DECAY TO EXPIRY\n"
          f"Stock: ${S} | Strike: ${K} | DTE: {days_to_expiry} days | IV: {IV:.1%}",
          fontsize=22, pad=30)
plt.xlabel("Date", fontsize=15)
plt.ylabel("Option Price ($)", fontsize=15)
plt.grid(alpha=0.35)
plt.legend(fontsize=15)

step = max(1, len(dates)//16)
tick_positions = x[::step]
tick_labels = [dates[i].strftime('%b %d %Y') for i in range(0, len(dates), step)]
plt.xticks(tick_positions, tick_labels, rotation=45, ha='right', fontsize=11)

plt.tight_layout()
plt.show()

print(f"\nDone! CSV saved as '{csv_filename}' in your current folder.")
print("You now have the most powerful personal theta tool ever made.")