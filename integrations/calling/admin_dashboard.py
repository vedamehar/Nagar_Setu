"""
Admin Dashboard for Complaint Management
- View all complaints
- Search and filter complaints
- Update complaint status
- Export data
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict
from tabulate import tabulate

DB_FILE = "complaints.db"

# ============ DATABASE HELPERS ============

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def dict_from_row(row):
    """Convert sqlite3.Row to dictionary"""
    return dict(row) if row else None

# ============ DASHBOARD FUNCTIONS ============

def show_all_complaints():
    """Display all complaints in table format"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id,
                phone_number,
                status,
                created_at
            FROM complaints
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print("No complaints found.")
            return
        
        data = [
            [row['id'][:8] + '...', row['phone_number'], row['status'], row['created_at']]
            for row in rows
        ]
        
        headers = ["Complaint ID", "Phone Number", "Status", "Created At"]
        print("\n📋 ALL COMPLAINTS\n")
        print(tabulate(data, headers=headers, tablefmt="grid"))
        print(f"\nTotal Complaints: {len(rows)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def show_pending_complaints():
    """Display pending complaints"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id,
                phone_number,
                status,
                created_at
            FROM complaints
            WHERE status = 'Pending'
            ORDER BY created_at ASC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print("✅ No pending complaints.")
            return
        
        data = [
            [row['id'][:8] + '...', row['phone_number'], row['status'], row['created_at']]
            for row in rows
        ]
        
        headers = ["Complaint ID", "Phone Number", "Status", "Created At"]
        print("\n⏳ PENDING COMPLAINTS\n")
        print(tabulate(data, headers=headers, tablefmt="grid"))
        print(f"\nTotal Pending: {len(rows)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def get_complaint_details(complaint_id: str):
    """Get detailed information about a complaint"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,))
        complaint = cursor.fetchone()
        conn.close()
        
        if not complaint:
            print(f"❌ Complaint not found: {complaint_id}")
            return
        
        print("\n📝 COMPLAINT DETAILS\n")
        print(f"ID:                    {complaint['id']}")
        print(f"Phone Number:          {complaint['phone_number']}")
        print(f"Status:                {complaint['status']}")
        print(f"Created At:            {complaint['created_at']}")
        print(f"Updated At:            {complaint['updated_at']}")
        print(f"\n🎙️  COMPLAINT AUDIO")
        print(f"URL:                   {complaint['complaint_audio_url']}")
        print(f"Text:                  {complaint['complaint_text'] or '(Not transcribed)'}")
        print(f"Language:              {complaint['complaint_language']}")
        print(f"\n📍 LOCATION AUDIO")
        print(f"URL:                   {complaint['location_audio_url']}")
        print(f"Text:                  {complaint['location_text'] or '(Not transcribed)'}")
        print(f"Language:              {complaint['location_language']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def update_complaint_status(complaint_id: str, new_status: str):
    """Update complaint status"""
    try:
        valid_statuses = ["Pending", "In Progress", "Resolved", "Closed", "Rejected"]
        
        if new_status not in valid_statuses:
            print(f"❌ Invalid status. Valid options: {', '.join(valid_statuses)}")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE complaints
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, complaint_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Complaint status updated to: {new_status}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def get_statistics():
    """Display statistics about complaints"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total complaints
        cursor.execute("SELECT COUNT(*) as count FROM complaints")
        total = cursor.fetchone()['count']
        
        # By status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM complaints
            GROUP BY status
            ORDER BY count DESC
        """)
        by_status = cursor.fetchall()
        
        # By date (last 7 days)
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM complaints
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)
        by_date = cursor.fetchall()
        
        conn.close()
        
        print("\n📊 STATISTICS\n")
        print(f"Total Complaints:      {total}")
        
        print("\n📌 BY STATUS:")
        for row in by_status:
            print(f"  {row['status']:20s} {row['count']:3d}")
        
        print("\n📅 LAST 7 DAYS:")
        for row in by_date:
            print(f"  {row['date']:s}         {row['count']:3d}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def search_complaints(phone_number: Optional[str] = None, status: Optional[str] = None):
    """Search complaints by phone number or status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT id, phone_number, status, created_at FROM complaints WHERE 1=1"
        params = []
        
        if phone_number:
            query += " AND phone_number LIKE ?"
            params.append(f"%{phone_number}%")
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print("❌ No complaints found matching criteria.")
            return
        
        data = [
            [row['id'][:8] + '...', row['phone_number'], row['status'], row['created_at']]
            for row in rows
        ]
        
        headers = ["Complaint ID", "Phone Number", "Status", "Created At"]
        print("\n🔍 SEARCH RESULTS\n")
        print(tabulate(data, headers=headers, tablefmt="grid"))
        print(f"\nTotal Found: {len(rows)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def export_complaints_json(filename: str = "complaints.json"):
    """Export all complaints to JSON"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM complaints ORDER BY created_at DESC")
        complaints = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        with open(filename, 'w') as f:
            json.dump(complaints, f, indent=2)
        
        print(f"✅ Exported {len(complaints)} complaints to {filename}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def export_complaints_csv(filename: str = "complaints.csv"):
    """Export all complaints to CSV"""
    try:
        import csv
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM complaints ORDER BY created_at DESC")
        complaints = cursor.fetchall()
        
        if not complaints:
            print("❌ No complaints to export.")
            return
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write headers
            writer.writerow(complaints[0].keys())
            
            # Write data
            for row in complaints:
                writer.writerow(row)
        
        conn.close()
        print(f"✅ Exported {len(complaints)} complaints to {filename}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

# ============ INTERACTIVE MENU ============

def show_menu():
    """Display interactive menu"""
    menu = """
╔══════════════════════════════════════════════════════╗
║        📞 COMPLAINT MANAGEMENT DASHBOARD             ║
╚══════════════════════════════════════════════════════╝

1. 📋 View All Complaints
2. ⏳ View Pending Complaints
3. 📝 View Complaint Details
4. ✏️  Update Complaint Status
5. 🔍 Search Complaints
6. 📊 View Statistics
7. 📤 Export to JSON
8. 📊 Export to CSV
9. 🚪 Exit

Choose an option (1-9): """
    return input(menu).strip()

def interactive_dashboard():
    """Run interactive dashboard"""
    while True:
        choice = show_menu()
        
        if choice == "1":
            show_all_complaints()
        
        elif choice == "2":
            show_pending_complaints()
        
        elif choice == "3":
            complaint_id = input("Enter Complaint ID: ").strip()
            get_complaint_details(complaint_id)
        
        elif choice == "4":
            complaint_id = input("Enter Complaint ID: ").strip()
            new_status = input("Enter New Status (Pending/In Progress/Resolved/Closed/Rejected): ").strip()
            update_complaint_status(complaint_id, new_status)
        
        elif choice == "5":
            phone = input("Search by phone number (or leave blank): ").strip() or None
            status = input("Search by status (or leave blank): ").strip() or None
            search_complaints(phone, status)
        
        elif choice == "6":
            get_statistics()
        
        elif choice == "7":
            filename = input("Enter filename (default: complaints.json): ").strip() or "complaints.json"
            export_complaints_json(filename)
        
        elif choice == "8":
            filename = input("Enter filename (default: complaints.csv): ").strip() or "complaints.csv"
            export_complaints_csv(filename)
        
        elif choice == "9":
            print("\n👋 Goodbye!\n")
            break
        
        else:
            print("❌ Invalid option. Please try again.\n")
        
        input("\nPress Enter to continue...\n")

# ============ COMMAND LINE INTERFACE ============

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "all":
            show_all_complaints()
        elif command == "pending":
            show_pending_complaints()
        elif command == "details" and len(sys.argv) > 2:
            get_complaint_details(sys.argv[2])
        elif command == "stats":
            get_statistics()
        elif command == "export-json":
            export_complaints_json()
        elif command == "export-csv":
            export_complaints_csv()
        else:
            print("Usage:")
            print("  python admin_dashboard.py                 # Interactive mode")
            print("  python admin_dashboard.py all              # Show all complaints")
            print("  python admin_dashboard.py pending          # Show pending complaints")
            print("  python admin_dashboard.py details <id>     # Show complaint details")
            print("  python admin_dashboard.py stats            # Show statistics")
            print("  python admin_dashboard.py export-json      # Export to JSON")
            print("  python admin_dashboard.py export-csv       # Export to CSV")
    else:
        # Interactive mode
        interactive_dashboard()
