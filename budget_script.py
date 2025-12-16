#!/usr/bin/env python3
"""
Budget Tracking Script
Analyzes Chase, Discover, and Vibrant bank statements
"""

import csv
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from collections import defaultdict
import calendar

class BudgetTracker:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Budget Tracker")
        self.root.geometry("800x600")
        
        # Data storage
        self.transactions = []
        self.chase_file = None
        self.discover_file = None
        self.vibrant_file = None
        
        # Config directory
        self.config_dir = Path("budget_data")
        self.config_dir.mkdir(exist_ok=True)
        
        # Load persistent data
        self.category_map = self.load_json("category_map.json", {})
        self.merchant_rules = self.load_json("merchant_rules.json", {})
        
        # Chase standard categories
        self.standard_categories = [
            "Health & Wellness",
            "Food & Drink",
            "Gas",
            "Travel",
            "Shopping",
            "Groceries",
            "Professional Services",
            "Gifts and Donations",
            "Personal",
            "Entertainment",
            "Bills & Utilities"
        ]
        
        # Discover to Chase category mapping
        self.discover_to_chase = {
            "Merchandise": "Shopping",
            "Restaurants": "Food & Drink",
            "Supermarkets": "Groceries",
            "Medical Services": "Health & Wellness",
            "Gasoline": "Gas",
            "Education": "Professional Services",
            "Travel/ Entertainment": "Travel",
            "Automotive": "Shopping",
            "Services": "Professional Services"
        }
        
        self.setup_ui()
    
    def load_json(self, filename, default):
        """Load JSON config file"""
        filepath = self.config_dir / filename
        if filepath.exists():
            with open(filepath, 'r') as f:
                return json.load(f)
        return default
    
    def save_json(self, filename, data):
        """Save JSON config file"""
        filepath = self.config_dir / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def setup_ui(self):
        """Setup the main UI"""
        # Title
        title_label = tk.Label(self.root, text="Budget Tracker", font=("Arial", 20, "bold"))
        title_label.pack(pady=20)
        
        # Instructions
        instructions = tk.Label(
            self.root,
            text="Upload your YTD statements (CSV format)",
            font=("Arial", 12)
        )
        instructions.pack(pady=10)
        
        # File upload buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        self.chase_btn = tk.Button(
            button_frame,
            text="Upload Chase Statement",
            command=self.upload_chase,
            width=25,
            height=2
        )
        self.chase_btn.grid(row=0, column=0, padx=10, pady=10)
        
        self.discover_btn = tk.Button(
            button_frame,
            text="Upload Discover Statement",
            command=self.upload_discover,
            width=25,
            height=2
        )
        self.discover_btn.grid(row=1, column=0, padx=10, pady=10)
        
        self.vibrant_btn = tk.Button(
            button_frame,
            text="Upload Vibrant Statement",
            command=self.upload_vibrant,
            width=25,
            height=2
        )
        self.vibrant_btn.grid(row=2, column=0, padx=10, pady=10)
        
        # Status labels
        self.status_frame = tk.Frame(self.root)
        self.status_frame.pack(pady=10)
        
        self.chase_status = tk.Label(self.status_frame, text="Chase: Not uploaded", fg="red")
        self.chase_status.pack()
        
        self.discover_status = tk.Label(self.status_frame, text="Discover: Not uploaded", fg="red")
        self.discover_status.pack()
        
        self.vibrant_status = tk.Label(self.status_frame, text="Vibrant: Not uploaded", fg="red")
        self.vibrant_status.pack()
        
        # Process button
        self.process_btn = tk.Button(
            self.root,
            text="Process Budget",
            command=self.process_budget,
            width=25,
            height=2,
            bg="green",
            fg="white",
            font=("Arial", 12, "bold"),
            state=tk.DISABLED
        )
        self.process_btn.pack(pady=30)
        
    def upload_chase(self):
        """Upload Chase CSV"""
        filename = filedialog.askopenfilename(
            title="Select Chase Statement",
            filetypes=[("CSV files", "*.csv")]
        )
        if filename:
            self.chase_file = filename
            self.chase_status.config(text=f"Chase: {Path(filename).name}", fg="green")
            self.check_ready()
    
    def upload_discover(self):
        """Upload Discover CSV"""
        filename = filedialog.askopenfilename(
            title="Select Discover Statement",
            filetypes=[("CSV files", "*.csv")]
        )
        if filename:
            self.discover_file = filename
            self.discover_status.config(text=f"Discover: {Path(filename).name}", fg="green")
            self.check_ready()
    
    def upload_vibrant(self):
        """Upload Vibrant CSV"""
        filename = filedialog.askopenfilename(
            title="Select Vibrant Statement",
            filetypes=[("CSV files", "*.csv")]
        )
        if filename:
            self.vibrant_file = filename
            self.vibrant_status.config(text=f"Vibrant: {Path(filename).name}", fg="green")
            self.check_ready()
    
    def check_ready(self):
        """Check if all files are uploaded"""
        if self.chase_file and self.discover_file and self.vibrant_file:
            self.process_btn.config(state=tk.NORMAL)
    
    def parse_date(self, date_str):
        """Parse MM/DD/YYYY date"""
        try:
            return datetime.strptime(date_str.strip(), "%m/%d/%Y")
        except:
            return None
    
    def parse_amount(self, amount_str):
        """Parse currency amount to Decimal"""
        try:
            # Remove $ and commas
            clean = amount_str.replace("$", "").replace(",", "").strip()
            return Decimal(clean)
        except:
            return Decimal("0")
    
    def read_chase(self):
        """Read Chase CSV file"""
        transactions = []
        with open(self.chase_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip empty rows
                if not row.get('Transaction Date'):
                    continue
                
                # Skip Payment types
                if row.get('Type', '').strip().upper() == 'PAYMENT':
                    continue
                
                date = self.parse_date(row['Transaction Date'])
                if not date:
                    continue
                
                description = row['Description'].strip()
                category = row['Category'].strip()
                amount = self.parse_amount(row['Amount'])
                
                # Apply keyword-based category overrides
                if "YMCA OF GREATER RICHMOND" in description.upper():
                    category = "Health & Wellness"
                elif "SLING.COM" in description.upper():
                    category = "Entertainment"
                elif "COLLEGE TRANSCRIPT" in description.upper():
                    category = "Professional Services"
                
                transactions.append({
                    'source': 'Chase',
                    'date': date,
                    'description': description,
                    'category': category,
                    'amount': amount,
                    'original_row': row
                })
        
        return transactions
    
    def read_discover(self):
        """Read Discover CSV file"""
        transactions = []
        with open(self.discover_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip empty rows
                if not row.get('Trans. Date'):
                    continue
                
                category = row.get('Category', '').strip()
                
                # Skip Payments and Credits
                if category.upper() in ['PAYMENTS AND CREDITS', 'PAYMENTS', 'CREDITS']:
                    continue
                
                date = self.parse_date(row['Trans. Date'])
                if not date:
                    continue
                
                description = row['Description'].strip()
                amount = self.parse_amount(row['Amount'])
                
                # FLIP SIGN for Discover (their positive is spending)
                amount = -amount
                
                # Convert category to Chase standard
                chase_category = self.discover_to_chase.get(category, category)
                
                # Walmart override
                if "WALMART" in description.upper():
                    chase_category = "Groceries"
                
                # Check if we need to map this category
                if chase_category not in self.standard_categories:
                    chase_category = self.prompt_category_mapping(category, chase_category)
                
                transactions.append({
                    'source': 'Discover',
                    'date': date,
                    'description': description,
                    'category': chase_category,
                    'amount': amount,
                    'original_row': row
                })
        
        return transactions
    
    def read_vibrant(self):
        """Read Vibrant CSV file"""
        transactions = []
        with open(self.vibrant_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip empty rows
                if not row.get('Effective Date'):
                    continue
                
                date = self.parse_date(row['Effective Date'])
                if not date:
                    continue
                
                description = row['Description'].strip()
                amount = self.parse_amount(row['Amount'])
                
                # Determine category based on amount sign and description
                if amount > 0:
                    # Positive = Income
                    category = "Income"
                else:
                    # Negative = Spending from bank
                    # Try to categorize based on description
                    category = "Bills & Utilities"  # Default for bank spending
                
                transactions.append({
                    'source': 'Vibrant',
                    'date': date,
                    'description': description,
                    'category': category,
                    'amount': amount,
                    'original_row': row
                })
        
        return transactions
    
    def prompt_category_mapping(self, original_category, current_mapping):
        """Prompt user to map unknown category"""
        # Check if we've already mapped this
        if original_category in self.category_map:
            return self.category_map[original_category]
        
        # Create mapping dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Map Category")
        dialog.geometry("400x300")
        dialog.grab_set()
        
        tk.Label(
            dialog,
            text=f"Unknown category: {original_category}",
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        tk.Label(
            dialog,
            text="Map to:",
            font=("Arial", 10)
        ).pack(pady=5)
        
        selected = tk.StringVar(value=current_mapping)
        
        for cat in self.standard_categories:
            tk.Radiobutton(
                dialog,
                text=cat,
                variable=selected,
                value=cat
            ).pack(anchor=tk.W, padx=20)
        
        result = [None]
        
        def save_mapping():
            result[0] = selected.get()
            self.category_map[original_category] = result[0]
            self.save_json("category_map.json", self.category_map)
            dialog.destroy()
        
        tk.Button(
            dialog,
            text="Save Mapping",
            command=save_mapping,
            bg="green",
            fg="white"
        ).pack(pady=20)
        
        dialog.wait_window()
        return result[0] or current_mapping
    
    def find_duplicates(self, transactions):
        """Find potential duplicate transactions by amount"""
        amount_groups = defaultdict(list)
        
        for i, trans in enumerate(transactions):
            # Use absolute value for matching
            abs_amount = abs(trans['amount'])
            amount_groups[abs_amount].append((i, trans))
        
        # Find groups with multiple transactions
        duplicate_groups = []
        for amount, trans_list in amount_groups.items():
            if len(trans_list) > 1:
                duplicate_groups.append(trans_list)
        
        return duplicate_groups
    
    def resolve_duplicates(self, duplicate_groups):
        """Show UI to resolve duplicates"""
        indices_to_remove = set()
        
        total_groups = len(duplicate_groups)
        
        for group_num, group in enumerate(duplicate_groups, 1):
            # Create dialog
            dialog = tk.Toplevel(self.root)
            dialog.title(f"Resolve Duplicates ({group_num}/{total_groups})")
            dialog.geometry("700x400")
            dialog.grab_set()
            
            tk.Label(
                dialog,
                text=f"Potential duplicates found (Group {group_num} of {total_groups})",
                font=("Arial", 12, "bold")
            ).pack(pady=10)
            
            tk.Label(
                dialog,
                text="Check transactions that are DUPLICATES (they will be removed):",
                font=("Arial", 10)
            ).pack(pady=5)
            
            # Create frame for transactions
            trans_frame = tk.Frame(dialog)
            trans_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            checkboxes = []
            
            for idx, (orig_idx, trans) in enumerate(group):
                frame = tk.LabelFrame(trans_frame, text=f"{trans['source']}", padx=10, pady=5)
                frame.pack(fill=tk.X, pady=5)
                
                var = tk.BooleanVar(value=False)
                cb = tk.Checkbutton(frame, variable=var)
                cb.pack(side=tk.LEFT)
                
                info_text = f"Date: {trans['date'].strftime('%m/%d/%Y')} | Amount: ${trans['amount']:.2f} | {trans['description'][:50]}"
                tk.Label(frame, text=info_text, anchor=tk.W).pack(side=tk.LEFT, padx=10)
                
                checkboxes.append((var, orig_idx))
            
            def save_selections():
                for var, orig_idx in checkboxes:
                    if var.get():
                        indices_to_remove.add(orig_idx)
                dialog.destroy()
            
            tk.Button(
                dialog,
                text="Confirm",
                command=save_selections,
                bg="green",
                fg="white",
                width=20,
                height=2
            ).pack(pady=10)
            
            dialog.wait_window()
        
        return indices_to_remove
    
    def process_budget(self):
        """Main processing function"""
        try:
            # Read all files
            self.root.config(cursor="watch")
            self.root.update()
            
            chase_trans = self.read_chase()
            discover_trans = self.read_discover()
            vibrant_trans = self.read_vibrant()
            
            # Combine all transactions
            all_transactions = chase_trans + discover_trans + vibrant_trans
            
            # Find and resolve duplicates
            duplicate_groups = self.find_duplicates(all_transactions)
            
            if duplicate_groups:
                indices_to_remove = self.resolve_duplicates(duplicate_groups)
                # Remove duplicates
                all_transactions = [
                    trans for i, trans in enumerate(all_transactions)
                    if i not in indices_to_remove
                ]
            
            self.transactions = sorted(all_transactions, key=lambda x: x['date'])
            
            # Create run folder
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            run_dir = self.config_dir / "runs" / timestamp
            run_dir.mkdir(parents=True, exist_ok=True)
            
            # Save cleaned transactions
            self.save_transactions(run_dir)
            
            # Analyze and display results
            self.show_results(run_dir)
            
            self.root.config(cursor="")
            
        except Exception as e:
            self.root.config(cursor="")
            messagebox.showerror("Error", f"Error processing budget: {str(e)}")
    
    def save_transactions(self, run_dir):
        """Save cleaned transactions to CSV"""
        filepath = run_dir / "transactions.csv"
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Source', 'Description', 'Category', 'Amount'])
            for trans in self.transactions:
                writer.writerow([
                    trans['date'].strftime('%m/%d/%Y'),
                    trans['source'],
                    trans['description'],
                    trans['category'],
                    f"{trans['amount']:.2f}"
                ])
    
    def calculate_monthly_data(self):
        """Calculate monthly breakdowns"""
        monthly_data = defaultdict(lambda: {
            'income': Decimal('0'),
            'spending': defaultdict(lambda: Decimal('0')),
            'total_spending': Decimal('0')
        })
        
        for trans in self.transactions:
            month_key = trans['date'].strftime('%Y-%m')
            
            if trans['category'] == 'Income' or trans['amount'] > 0:
                monthly_data[month_key]['income'] += trans['amount']
            else:
                category = trans['category']
                amount = abs(trans['amount'])
                monthly_data[month_key]['spending'][category] += amount
                monthly_data[month_key]['total_spending'] += amount
        
        return monthly_data
    
    def show_results(self, run_dir):
        """Display results in new window"""
        results_window = tk.Toplevel(self.root)
        results_window.title("Budget Analysis")
        results_window.geometry("1000x700")
        
        # Create notebook for tabs
        notebook = ttk.Notebook(results_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Calculate data
        monthly_data = self.calculate_monthly_data()
        
        # Summary tab
        self.create_summary_tab(notebook, monthly_data, run_dir)
        
        # Monthly tabs
        for month_key in sorted(monthly_data.keys()):
            self.create_month_tab(notebook, month_key, monthly_data[month_key])
        
        # Current month budget tracking tab
        current_month = datetime.now().strftime('%Y-%m')
        if current_month in monthly_data:
            self.create_budget_tracking_tab(notebook, current_month, monthly_data, run_dir)
    
    def create_summary_tab(self, notebook, monthly_data, run_dir):
        """Create summary tab"""
        tab = tk.Frame(notebook)
        notebook.add(tab, text="Summary")
        
        # Create scrollable frame
        canvas = tk.Canvas(tab)
        scrollbar = tk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Calculate totals
        total_income = Decimal('0')
        total_spending = Decimal('0')
        category_totals = defaultdict(lambda: Decimal('0'))
        
        for month_key, data in monthly_data.items():
            total_income += data['income']
            total_spending += data['total_spending']
            for cat, amount in data['spending'].items():
                category_totals[cat] += amount
        
        total_leftover = total_income - total_spending
        
        # Display totals
        tk.Label(
            scrollable_frame,
            text="OVERALL SUMMARY",
            font=("Arial", 16, "bold")
        ).pack(pady=10)
        
        tk.Label(
            scrollable_frame,
            text=f"Total Income: ${total_income:,.2f}",
            font=("Arial", 12),
            fg="green"
        ).pack()
        
        tk.Label(
            scrollable_frame,
            text=f"Total Spending: ${total_spending:,.2f}",
            font=("Arial", 12),
            fg="red"
        ).pack()
        
        leftover_color = "green" if total_leftover >= 0 else "red"
        tk.Label(
            scrollable_frame,
            text=f"Total Leftover: ${total_leftover:,.2f}",
            font=("Arial", 12, "bold"),
            fg=leftover_color
        ).pack(pady=10)
        
        # Calculate averages (excluding current month)
        current_month = datetime.now().strftime('%Y-%m')
        past_months = [k for k in monthly_data.keys() if k != current_month]
        
        if past_months:
            avg_income = sum(monthly_data[m]['income'] for m in past_months) / len(past_months)
            avg_spending = sum(monthly_data[m]['total_spending'] for m in past_months) / len(past_months)
            
            tk.Label(
                scrollable_frame,
                text=f"\nAVERAGE MONTHLY (Past {len(past_months)} months)",
                font=("Arial", 14, "bold")
            ).pack(pady=10)
            
            tk.Label(
                scrollable_frame,
                text=f"Avg Monthly Income: ${avg_income:,.2f}",
                font=("Arial", 11)
            ).pack()
            
            tk.Label(
                scrollable_frame,
                text=f"Avg Monthly Spending: ${avg_spending:,.2f}",
                font=("Arial", 11)
            ).pack()
            
            # Category breakdown
            tk.Label(
                scrollable_frame,
                text="\nSPENDING BY CATEGORY",
                font=("Arial", 14, "bold")
            ).pack(pady=10)
            
            for category in sorted(category_totals.keys()):
                amount = category_totals[category]
                tk.Label(
                    scrollable_frame,
                    text=f"{category}: ${amount:,.2f}",
                    font=("Arial", 10)
                ).pack()
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_month_tab(self, notebook, month_key, month_data):
        """Create tab for individual month"""
        tab = tk.Frame(notebook)
        notebook.add(tab, text=month_key)
        
        # Create scrollable frame
        canvas = tk.Canvas(tab)
        scrollbar = tk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Month summary
        tk.Label(
            scrollable_frame,
            text=f"Month: {month_key}",
            font=("Arial", 16, "bold")
        ).pack(pady=10)
        
        tk.Label(
            scrollable_frame,
            text=f"Income: ${month_data['income']:,.2f}",
            font=("Arial", 12),
            fg="green"
        ).pack()
        
        tk.Label(
            scrollable_frame,
            text=f"Spending: ${month_data['total_spending']:,.2f}",
            font=("Arial", 12),
            fg="red"
        ).pack()
        
        leftover = month_data['income'] - month_data['total_spending']
        leftover_color = "green" if leftover >= 0 else "red"
        
        tk.Label(
            scrollable_frame,
            text=f"Leftover: ${leftover:,.2f}",
            font=("Arial", 12, "bold"),
            fg=leftover_color
        ).pack(pady=10)
        
        # Category breakdown
        tk.Label(
            scrollable_frame,
            text="SPENDING BY CATEGORY",
            font=("Arial", 14, "bold")
        ).pack(pady=10)
        
        for category in sorted(month_data['spending'].keys()):
            amount = month_data['spending'][category]
            tk.Label(
                scrollable_frame,
                text=f"{category}: ${amount:,.2f}",
                font=("Arial", 10)
            ).pack()
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_budget_tracking_tab(self, notebook, current_month, monthly_data, run_dir):
        """Create budget tracking tab for current month"""
        tab = tk.Frame(notebook)
        notebook.add(tab, text="Current Month Budget")
        
        # Create scrollable frame
        canvas = tk.Canvas(tab)
        scrollbar = tk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        tk.Label(
            scrollable_frame,
            text=f"CURRENT MONTH BUDGET TRACKING",
            font=("Arial", 16, "bold")
        ).pack(pady=10)
        
        tk.Label(
            scrollable_frame,
            text=f"Month: {current_month}",
            font=("Arial", 12)
        ).pack()
        
        # Calculate average budgets from past months
        past_months = [k for k in monthly_data.keys() if k != current_month]
        
        if not past_months:
            tk.Label(
                scrollable_frame,
                text="No historical data to create budget",
                font=("Arial", 12),
                fg="orange"
            ).pack(pady=20)
        else:
            # Calculate average income
            avg_income = sum(monthly_data[m]['income'] for m in past_months) / len(past_months)
            
            # Calculate average spending per category
            category_budgets = defaultdict(lambda: Decimal('0'))
            for month in past_months:
                for cat, amount in monthly_data[month]['spending'].items():
                    category_budgets[cat] += amount
            
            for cat in category_budgets:
                category_budgets[cat] /= len(past_months)
            
            # Get current month actual spending
            current_spending = monthly_data[current_month]['spending']
            
            tk.Label(
                scrollable_frame,
                text=f"Average Monthly Income: ${avg_income:,.2f}",
                font=("Arial", 11),
                fg="green"
            ).pack(pady=5)
            
            tk.Label(
                scrollable_frame,
                text="\nBUDGET vs ACTUAL BY CATEGORY",
                font=("Arial", 14, "bold")
            ).pack(pady=10)
            
            # Show each category
            all_categories = set(category_budgets.keys()) | set(current_spending.keys())
            
            for category in sorted(all_categories):
                budget = category_budgets.get(category, Decimal('0'))
                actual = current_spending.get(category, Decimal('0'))
                remaining = budget - actual
                
                frame = tk.Frame(scrollable_frame, relief=tk.RIDGE, borderwidth=2)
                frame.pack(fill=tk.X, padx=20, pady=5)
                
                tk.Label(
                    frame,
                    text=category,
                    font=("Arial", 11, "bold")
                ).pack(anchor=tk.W, padx=10, pady=2)
                
                tk.Label(
                    frame,
                    text=f"Budget: ${budget:,.2f} | Spent: ${actual:,.2f}",
                    font=("Arial", 10)
                ).pack(anchor=tk.W, padx=10)
                
                remaining_color = "green" if remaining >= 0 else "red"
                tk.Label(
                    frame,
                    text=f"Remaining: ${remaining:,.2f}",
                    font=("Arial", 10, "bold"),
                    fg=remaining_color
                ).pack(anchor=tk.W, padx=10, pady=2)
            
            # Save budget data
            budget_data = {
                'month': current_month,
                'avg_income': float(avg_income),
                'category_budgets': {k: float(v) for k, v in category_budgets.items()},
                'actual_spending': {k: float(v) for k, v in current_spending.items()}
            }
            
            with open(run_dir / "budget_tracking.json", 'w') as f:
                json.dump(budget_data, f, indent=2)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()
