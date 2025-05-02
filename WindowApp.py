from tkinter import *
from tkinter import messagebox, ttk
import sqlite3
from datetime import datetime
import platform
import os
import time
from threading import Thread

# Initialize database with proper error handling
def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Create fresh table with all required columns
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 task TEXT NOT NULL,
                 due_date TEXT,
                 notified INTEGER DEFAULT 0)''')
    
    # Verify and add any missing columns without causing errors
    c.execute("PRAGMA table_info(tasks)")
    existing_columns = [col[1] for col in c.fetchall()]
    
    if 'due_date' not in existing_columns:
        try:
            c.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
            
    if 'notified' not in existing_columns:
        try:
            c.execute("ALTER TABLE tasks ADD COLUMN notified INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
    
    conn.commit()
    conn.close()

# Notification system
def show_notification(title, message):
    system = platform.system()
    try:
        if system == "Windows":
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=10)
        elif system == "Darwin":  # macOS
            os.system(f'osascript -e \'display notification "{message}" with title "{title}"\'')
        else:  # Linux
            os.system(f'notify-send "{title}" "{message}"')
    except Exception as e:
        print(f"Notification failed: {e}")

# Background reminder checker
def check_reminders():
    while True:
        try:
            conn = sqlite3.connect('tasks.db')
            c = conn.cursor()
            today = datetime.now().strftime("%m/%d/%Y")
            
            c.execute('''SELECT task, due_date FROM tasks 
                         WHERE due_date <= ? AND notified = 0''', (today,))
            
            for task, due_date in c.fetchall():
                show_notification("Task Due!", f"'{task}' is due on {due_date}")
                c.execute('''UPDATE tasks SET notified = 1 
                             WHERE task = ? AND due_date = ?''', (task, due_date))
                conn.commit()
            
            conn.close()
        except sqlite3.Error as e:
            print(f"Database error in reminder thread: {e}")
        time.sleep(60)  # Check every minute

# Task management functions
def add_task():
    task = task_entry.get().strip()
    due_date = due_entry.get().strip()
    
    if not task:
        messagebox.showwarning("Warning", "Please enter a task description!")
        return
    
    try:
        # Validate date format
        if due_date:  # Only validate if date is provided
            datetime.strptime(due_date, "%m/%d/%Y")
    except ValueError:
        messagebox.showwarning("Warning", "Invalid date format! Use MM/DD/YYYY or leave blank")
        return
    
    try:
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        c.execute("INSERT INTO tasks (task, due_date) VALUES (?, ?)", 
                 (task, due_date if due_date else None))
        conn.commit()
        conn.close()
        
        update_task_list()
        task_entry.delete(0, END)
        due_entry.delete(0, END)
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to add task: {e}")

def update_task_list():
    task_list.delete(*task_list.get_children())
    
    try:
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        c.execute("SELECT task, due_date FROM tasks ORDER BY due_date ASC, task ASC")
        
        today = datetime.now()
        for task, due_date in c.fetchall():
            if due_date:
                try:
                    due_datetime = datetime.strptime(due_date, "%m/%d/%Y")
                    days_left = (due_datetime - today).days
                    
                    if days_left < 0:
                        tag = "overdue"
                    elif days_left == 0:
                        tag = "due_today"
                    elif days_left <= 3:
                        tag = "due_soon"
                    else:
                        tag = "normal"
                except ValueError:
                    tag = "error"
            else:
                tag = "no_date"
                
            task_list.insert("", "end", values=(task, due_date if due_date else "No date"), tags=(tag,))
        
        conn.close()
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to load tasks: {e}")

def delete_task():
    selected = task_list.selection()
    if not selected:
        messagebox.showwarning("Warning", "Please select a task to delete!")
        return
    
    try:
        task = task_list.item(selected[0])['values'][0]
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE task=?", (task,))
        conn.commit()
        conn.close()
        update_task_list()
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to delete task: {e}")

# GUI Setup
root = Tk()
root.geometry('850x650')
root.title('Advanced To-Do List')

# Styling
style = ttk.Style()
style.configure("TFrame", background="#f0f0f0")
style.configure("TLabel", background="#f0f0f0", font=('Helvetica', 10))
style.configure("TButton", font=('Helvetica', 10), padding=5)
style.configure("Treeview", font=('Helvetica', 11), rowheight=25)
style.configure("Treeview.Heading", font=('Helvetica', 12, 'bold'))

# Main container
main_frame = ttk.Frame(root, padding="10")
main_frame.pack(fill=BOTH, expand=True)

# Input Frame
input_frame = ttk.Frame(main_frame)
input_frame.pack(fill=X, pady=10)

ttk.Label(input_frame, text="Task:").grid(row=0, column=0, padx=5, sticky=W)
task_entry = ttk.Entry(input_frame, width=40)
task_entry.grid(row=0, column=1, padx=5)

ttk.Label(input_frame, text="Due Date (MM/DD/YYYY):").grid(row=0, column=2, padx=5, sticky=W)
due_entry = ttk.Entry(input_frame, width=15)
due_entry.grid(row=0, column=3, padx=5)

add_btn = ttk.Button(input_frame, text="Add Task", command=add_task)
add_btn.grid(row=0, column=4, padx=10)

# Task List Frame
list_frame = ttk.Frame(main_frame)
list_frame.pack(fill=BOTH, expand=True, pady=10)

# Treeview with scrollbars
tree_scroll = ttk.Scrollbar(list_frame)
tree_scroll.pack(side=RIGHT, fill=Y)

task_list = ttk.Treeview(
    list_frame,
    columns=("Task", "Due Date"),
    show="headings",
    selectmode="browse",
    yscrollcommand=tree_scroll.set
)
task_list.pack(fill=BOTH, expand=True)

tree_scroll.config(command=task_list.yview)

# Configure columns
task_list.heading("Task", text="Task", anchor=W)
task_list.heading("Due Date", text="Due Date", anchor=W)
task_list.column("Task", width=400, anchor=W)
task_list.column("Due Date", width=150, anchor=W)

# Color tags
task_list.tag_configure("overdue", background='#ffdddd')
task_list.tag_configure("due_today", background='#ffffcc')
task_list.tag_configure("due_soon", background='#e6f3ff')
task_list.tag_configure("normal", background='white')
task_list.tag_configure("error", background='#f0f0f0', foreground='red')
task_list.tag_configure("no_date", background='#f8f8f8')

# Button Frame
btn_frame = ttk.Frame(main_frame)
btn_frame.pack(fill=X, pady=10)

delete_btn = ttk.Button(btn_frame, text="Delete Selected", command=delete_task)
delete_btn.pack(side=LEFT, padx=5)

# Initialize and start
init_db()
update_task_list()

# Start reminder thread
reminder_thread = Thread(target=check_reminders, daemon=True)
reminder_thread.start()

# Run the application
root.mainloop()