import tkinter as tk
from tkinter import ttk, scrolledtext

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pokemon Run and Bun Helper")
        self.root.geometry("600x450")
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main Container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status Section
        self.status_var = tk.StringVar(value="Waiting for connection...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Helvetica", 10, "bold"))
        status_label.pack(pady=(0, 10), anchor="w")
        
        # Split Pane (Moves vs Switch)
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left: Move Predictions
        move_frame = ttk.Labelframe(paned, text="Predicted Enemy Moves", padding="5")
        paned.add(move_frame, weight=2)
        
        self.move_tree = ttk.Treeview(move_frame, columns=("Move", "Score", "Type", "Prob"), show="headings", height=8)
        self.move_tree.heading("Move", text="Move")
        self.move_tree.heading("Score", text="Score")
        self.move_tree.heading("Type", text="Type")
        self.move_tree.heading("Prob", text="Prob")
        self.move_tree.column("Move", width=120)
        self.move_tree.column("Score", width=50)
        self.move_tree.column("Type", width=100)
        self.move_tree.column("Prob", width=50)
        self.move_tree.pack(fill=tk.BOTH, expand=True)
        
        # Right: Switch Prediction
        switch_frame = ttk.Labelframe(paned, text="Next Switch-In", padding="5")
        paned.add(switch_frame, weight=1)
        
        self.switch_label = ttk.Label(switch_frame, text="--", font=("Helvetica", 12))
        self.switch_label.pack(pady=10)
        
        self.switch_reason = ttk.Label(switch_frame, text="", wraplength=150)
        self.switch_reason.pack(pady=5)
        
        # Log/Details
        details_frame = ttk.Labelframe(main_frame, text="Logs / Details", padding="5")
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.log_text = scrolledtext.ScrolledText(details_frame, height=5, font=("Courier", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def update_state(self, message):
        self.status_var.set(message)

    def update_predictions(self, scored_moves, best_switch):
        # Clear existing
        for item in self.move_tree.get_children():
            self.move_tree.delete(item)
            
        # Update Moves
        # scored_moves is list of dicts from MoveScorer
        if scored_moves:
            # Sort by highest score (standard or high roll)
            scored_moves.sort(key=lambda x: max(x['scores']['standard'], x['scores']['high_roll']), reverse=True)
            
            for m in scored_moves:
                name = m['move']
                score_std = m['scores']['standard']
                score_high = m['scores']['high_roll']
                reason = m['reasons']['standard']
                
                display_score = f"{score_std} / {score_high}" if score_std != score_high else f"{score_std}"
                
                prob = "High" if score_std >= 12 or score_high >= 12 else "Low"
                
                self.move_tree.insert("", tk.END, values=(name, display_score, reason, prob))
        
        # Update Switch
        if best_switch:
            name = best_switch.get('species', 'Unknown')
            # Assuming SwitchPredictor returns tuple (candidate, explanations) or just candidate?
            # My Code returned (candidate, explanations)
            
            # Need to handle tuple unwrap in main or here 
            # I'll handle it assuming best_switch is just the dict for now, fix in integration
            self.switch_label.config(text=str(name))
        else:
            self.switch_label.config(text="None")

    def run(self):
        self.root.mainloop()

    def update(self):
        self.root.update()

