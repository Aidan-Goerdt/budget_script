#!/usr/bin/env python3
"""
Budget Script v1
Author: ChatGPT (spec-driven build)

Run:
  python budget_script.py

This script:
- Loads Chase, Discover, and Vibrant CSV statements
- Normalizes categories and amounts
- Lets user manually resolve duplicate transactions (amount-based)
- Aggregates income & spending
- Computes monthly stats, averages, and budgets
- Persists cleaned data and configs to disk

NOTE: This is intentionally readable and explicit rather than clever.
"""

from decimal import Decimal, getcontext
from datetime import datetime
from collections import defaultdict
import csv
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox

# ------------------ GLOBAL CONFIG ------------------
getcontext().prec = 28
DATA_DIR = "budget_data"
RUNS_DIR = os.path.join(DATA_DIR, "runs")
CONFIG_FILES = {
    "category_map": os.path.join(DATA_DIR, "category_map.json"),
    "merchant_rules": os.path.join(DATA_DIR, "merchant_rules.json"),
    "overrides": os.path.join(DATA_DIR, "overrides.json"),
}

CHASE_CATEGORIES = {
    "Health & Wellness",
    "Food & Drink",
    "Gas",
    "Travel",
    "Shopping",
    "Groceries",
    "Professional Services",
    "Entertainment",
    "Bills & Utilities",
}

# ------------------ UTILS ------------------

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(RUNS_DIR, exist_ok=True)


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def parse_date(s):
    return datetime.strptime(s.strip(), "%m/%d/%Y").date()


def d(val):
    return Decimal(str(val)).quantize(Decimal("0.01"))


# ------------------ TRANSACTION MODEL ------------------

def make_txn(date, desc, amount, category, source):
    return {
        "date": date,
        "description": desc.strip(),
        "amount": amount,
        "category": category,
        "source": source,
        "ignore": False,
    }


# ------------------ LOADERS ------------------

def load_chase(path, merchant_rules):
    txns = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r["Type"] == "Payment":
                continue
            amt = d(r["Amount"])
            cat = r["Category"]
            desc = r["Description"]

            for key, forced_cat in merchant_rules.items():
                if key in desc.upper():
                    cat = forced_cat

            txns.append(make_txn(
                parse_date(r["Transaction Date"]),
                desc,
                amt,
                cat,
                "CHASE"
            ))
    return txns


def load_discover(path, category_map, merchant_rules):
    txns = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            cat_raw = r["Category"]
            if cat_raw == "Payments & Credits":
                continue

            amt = d(r["Amount"]) * Decimal("-1")
            desc = r["Description"]

            # Merchant override first
            cat = None
            for key, forced_cat in merchant_rules.items():
                if key in desc.upper():
                    cat = forced_cat
                    break

            if not cat:
                cat = category_map.get(cat_raw, "Uncategorized")

            txns.append(make_txn(
                parse_date(r["Transaction Date"]),
                desc,
                amt,
                cat,
                "DISCOVER"
            ))
    return txns


def load_vibrant(path):
    txns = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            amt = d(r["Amount"])
            desc = r["Description"]
            cat = "Income" if amt > 0 else "Bills & Utilities"
            txns.append(make_txn(
                parse_date(r["Transaction Date"]),
                desc,
                amt,
                cat,
                "VIBRANT"
            ))
    return txns


# ------------------ DUPLICATE RESOLUTION ------------------

def resolve_duplicates(txns_a, txns_b):
    resolved = []
    used_b = set()

    for i, ta in enumerate(txns_a):
        match_found = False
        for j, tb in enumerate(txns_b):
            if j in used_b:
                continue
            if ta["amount"] == tb["amount"]:
                choice = duplicate_popup(ta, tb)
                if choice == "A":
                    resolved.append(ta)
                else:
                    resolved.append(tb)
                    used_b.add(j)
                match_found = True
                break
        if not match_found:
            resolved.append(ta)

    for j, tb in enumerate(txns_b):
        if j not in used_b:
            resolved.append(tb)

    return resolved


def duplicate_popup(a, b):
    root = tk.Tk()
    root.title("Duplicate Transaction Detected")

    choice = tk.StringVar()

    def select(val):
        choice.set(val)
        root.destroy()

    tk.Label(root, text="Select which transaction to KEEP", font=("Arial", 12, "bold")).pack(pady=5)

    frame = tk.Frame(root)
    frame.pack(padx=10, pady=10)

    left = tk.Frame(frame)
    right = tk.Frame(frame)
    left.pack(side="left", padx=10)
    right.pack(side="right", padx=10)

    for lbl, txn in [("A", a), ("B", b)]:
        box = left if lbl == "A" else right
        tk.Label(box, text=f"{txn['source']}\n{txn['date']}\n{txn['description']}\n{txn['amount']}\n{txn['category']}").pack()

    tk.Button(root, text="KEEP LEFT", command=lambda: select("A")).pack(side="left", padx=20, pady=10)
    tk.Button(root, text="KEEP RIGHT", command=lambda: select("B")).pack(side="right", padx=20, pady=10)

    root.mainloop()
    return choice.get()


# ------------------ AGGREGATION ------------------

def group_by_month(txns):
    months = defaultdict(list)
    for t in txns:
        key = t["date"].strftime("%Y-%m")
        months[key].append(t)
    return months


def compute_totals(txns):
    income = sum(t["amount"] for t in txns if t["source"] == "VIBRANT" and t["amount"] > 0)
    spending = sum(t["amount"] for t in txns if t["amount"] < 0)
    return income, spending


# ------------------ MAIN ------------------

def main():
    ensure_dirs()

    category_map = load_json(CONFIG_FILES["category_map"], {
        "Merchandise": "Shopping",
        "Restaurants": "Food & Drink",
        "Supermarkets": "Groceries",
        "Medical Services": "Health & Wellness",
        "Gasoline": "Gas",
        "Education": "Professional Services",
        "Travel/Entertainment": "Travel",
        "Automotive": "Shopping",
        "Services": "Professional Services",
    })

    merchant_rules = load_json(CONFIG_FILES["merchant_rules"], {
        "WALMART": "Groceries",
        "YMCA": "Health & Wellness",
        "SLING": "Entertainment",
        "COLLEGE TRANSCRIPT": "Professional Services",
    })

    root = tk.Tk()
    root.withdraw()

    messagebox.showinfo("Upload", "Select CHASE CSV")
    chase_file = filedialog.askopenfilename()
    messagebox.showinfo("Upload", "Select DISCOVER CSV")
    discover_file = filedialog.askopenfilename()
    messagebox.showinfo("Upload", "Select VIBRANT CSV")
    vibrant_file = filedialog.askopenfilename()

    chase = load_chase(chase_file, merchant_rules)
    discover = load_discover(discover_file, category_map, merchant_rules)
    vibrant = load_vibrant(vibrant_file)

    step1 = resolve_duplicates(chase, vibrant)
    step2 = resolve_duplicates(discover, vibrant)
    all_txns = resolve_duplicates(step1, step2)

    months = group_by_month(all_txns)
    income, spending = compute_totals(all_txns)

    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M")
    run_dir = os.path.join(RUNS_DIR, run_id)
    os.makedirs(run_dir)

    save_json(os.path.join(run_dir, "transactions.json"), all_txns)
    save_json(os.path.join(run_dir, "monthly.json"), months)

    save_json(CONFIG_FILES["category_map"], category_map)
    save_json(CONFIG_FILES["merchant_rules"], merchant_rules)

    messagebox.showinfo(
        "Summary",
        f"TOTAL INCOME: {income}\nTOTAL SPENDING: {spending}\nNET: {income + spending}"
    )


if __name__ == "__main__":
    main()
