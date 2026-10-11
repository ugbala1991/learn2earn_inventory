#!/usr/bin/env python3
"""
Learn2Earn Resource Lending System
Python 3 standard library only.

Run with:
    python learn2earn.py

The program saves its data to learn2earn_data.json in the same folder.
Choose menu option 8 to run the required demonstration from fresh starting data.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).with_name("learn2earn_data.json")

STARTING_RESOURCES = [
    {"id": "R001", "name": "Laptop", "category": "Electronics", "total": 10, "available": 10},
    {"id": "R002", "name": "Keyboard", "category": "Accessories", "total": 5, "available": 5},
    {"id": "R003", "name": "Headset", "category": "Accessories", "total": 3, "available": 3},
]
STARTING_FELLOWS = {"F001": "Ada", "F002": "John", "F003": "Grace"}


def fresh_state():
    """Return a new copy of the starting application data."""
    return {
        "resources": [item.copy() for item in STARTING_RESOURCES],
        "fellows": STARTING_FELLOWS.copy(),
        # Outstanding loans are keyed by (fellow ID, resource ID) in memory.
        "loans": [],
        "history": [],
    }


def safe_int(value):
    """Parse an integer without allowing invalid user data to crash the program."""
    try:
        text = str(value).strip()
        if not text:
            return None
        # Reject decimal-looking numbers such as 2.0 and other non-integers.
        if text.startswith("+"):
            text = text[1:]
        if not text or not text.isdigit():
            return None
        return int(text)
    except (TypeError, ValueError, OverflowError):
        return None


def resource_by_id(state, resource_id):
    return next((r for r in state["resources"] if r["id"].casefold() == resource_id.strip().casefold()), None)


def fellow_exists(state, fellow_id):
    return fellow_id.strip().upper() in state["fellows"]


def loan_record(state, fellow_id, resource_id):
    return next(
        (loan for loan in state["loans"]
         if loan["fellow_id"] == fellow_id.upper() and loan["resource_id"] == resource_id.upper()),
        None,
    )


def save_state(state):
    """Write JSON safely using a temporary file, so an interrupted write is less likely to corrupt data."""
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state, indent=2, ensure_ascii=False)
        fd, temp_name = tempfile.mkstemp(prefix="learn2earn_", suffix=".tmp", dir=str(DATA_FILE.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, DATA_FILE)
        finally:
            if os.path.exists(temp_name):
                os.remove(temp_name)
        return True
    except (OSError, TypeError, ValueError) as exc:
        print(f"Warning: data could not be saved ({exc}). Your current session can continue.")
        return False


def valid_loaded_state(data):
    """Validate the shape and core inventory/loan invariants of a JSON file."""
    if not isinstance(data, dict):
        return False
    if not all(key in data for key in ("resources", "fellows", "loans", "history")):
        return False
    if not isinstance(data["resources"], list) or not isinstance(data["fellows"], dict):
        return False
    if not isinstance(data["loans"], list) or not isinstance(data["history"], list):
        return False

    ids = set()
    for resource in data["resources"]:
        if not isinstance(resource, dict):
            return False
        if not all(k in resource for k in ("id", "name", "category", "total", "available")):
            return False
        if not all(isinstance(resource[k], str) and resource[k].strip() for k in ("id", "name", "category")):
            return False
        total, available = resource["total"], resource["available"]
        if type(total) is not int or type(available) is not int or total < 0 or not 0 <= available <= total:
            return False
        key = resource["id"].upper()
        if key in ids:
            return False
        ids.add(key)

    for fellow_id, name in data["fellows"].items():
        if not isinstance(fellow_id, str) or not isinstance(name, str):
            return False

    for loan in data["loans"]:
        if not isinstance(loan, dict) or not all(k in loan for k in ("fellow_id", "resource_id", "quantity")):
            return False
        if loan["fellow_id"] not in data["fellows"] or loan["resource_id"].upper() not in ids:
            return False
        if type(loan["quantity"]) is not int or loan["quantity"] <= 0:
            return False

    # Available units must agree with the outstanding loan records.
    for resource in data["resources"]:
        outstanding = sum(
            loan["quantity"] for loan in data["loans"]
            if loan["resource_id"].upper() == resource["id"].upper()
        )
        if resource["total"] - resource["available"] != outstanding:
            return False
    return True


def load_state():
    """Load JSON if valid; otherwise use the starter data and keep the program running."""
    if not DATA_FILE.exists():
        state = fresh_state()
        save_state(state)
        return state
    try:
        with DATA_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if valid_loaded_state(data):
            # Normalize IDs and keep a predictable shape.
            for fellow_id in data["fellows"]:
                data["fellows"][fellow_id] = data["fellows"][fellow_id].strip()
            return data
        print("Warning: the saved data is invalid or inconsistent. Starting with fresh data.")
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as exc:
        print(f"Warning: saved data could not be loaded ({exc}). Starting with fresh data.")
    state = fresh_state()
    save_state(state)
    return state


def add_resource(state, resource_id, name, category, total):
    resource_id = resource_id.strip().upper()
    name, category = name.strip(), category.strip()
    if not resource_id or not name or not category:
        return False, "Resource ID, name, and category cannot be blank."
    if resource_by_id(state, resource_id):
        return False, f"Resource ID {resource_id} already exists. IDs must be unique."
    if type(total) is not int or total <= 0:
        return False, "Total units must be a positive integer."
    state["resources"].append({
        "id": resource_id, "name": name, "category": category,
        "total": total, "available": total,
    })
    save_state(state)
    return True, f"Added {name} ({resource_id}) with {total} unit(s)."


def list_resources(state):
    if not state["resources"]:
        print("No resources are registered.")
        return
    print("\nRESOURCE INVENTORY")
    print("-" * 78)
    print(f"{'ID':<8} {'Name':<20} {'Category':<18} {'Total':>7} {'Available':>10} {'Borrowed':>9}")
    print("-" * 78)
    for r in state["resources"]:
        borrowed = r["total"] - r["available"]
        print(f"{r['id']:<8} {r['name'][:19]:<20} {r['category'][:17]:<18} {r['total']:>7} {r['available']:>10} {borrowed:>9}")
    print("-" * 78)


def borrow_resource(state, fellow_id, resource_id, quantity):
    fellow_id = fellow_id.strip().upper()
    resource_id = resource_id.strip().upper()
    if not fellow_id or not fellow_exists(state, fellow_id):
        return False, "Fellow ID not found. Check the ID and try again."
    resource = resource_by_id(state, resource_id)
    if resource is None:
        return False, "Resource ID not found. Check the ID and try again."
    if type(quantity) is not int or quantity <= 0:
        return False, "Quantity must be a positive integer."
    if quantity > resource["available"]:
        return False, f"Not enough stock. Only {resource['available']} unit(s) are available."
    # All validation is complete before changing state.
    record = loan_record(state, fellow_id, resource["id"])
    if record:
        record["quantity"] += quantity
    else:
        state["loans"].append({
            "fellow_id": fellow_id, "resource_id": resource["id"], "quantity": quantity
        })
    resource["available"] -= quantity
    state["history"].append({
        "action": "BORROW", "fellow_id": fellow_id, "resource_id": resource["id"],
        "quantity": quantity, "timestamp": datetime.now().isoformat(timespec="seconds"),
    })
    save_state(state)
    return True, f"{state['fellows'][fellow_id]} borrowed {quantity} unit(s) of {resource['name']}."


def return_resource(state, fellow_id, resource_id, quantity):
    fellow_id = fellow_id.strip().upper()
    resource_id = resource_id.strip().upper()
    if not fellow_id or not fellow_exists(state, fellow_id):
        return False, "Fellow ID not found. Check the ID and try again."
    resource = resource_by_id(state, resource_id)
    if resource is None:
        return False, "Resource ID not found. Check the ID and try again."
    if type(quantity) is not int or quantity <= 0:
        return False, "Quantity must be a positive integer."
    record = loan_record(state, fellow_id, resource["id"])
    currently_held = record["quantity"] if record else 0
    if quantity > currently_held:
        return False, f"Return rejected. This fellow currently has only {currently_held} unit(s) of this resource on loan."
    # All validation is complete before changing state.
    record["quantity"] -= quantity
    if record["quantity"] == 0:
        state["loans"].remove(record)
    resource["available"] += quantity
    state["history"].append({
        "action": "RETURN", "fellow_id": fellow_id, "resource_id": resource["id"],
        "quantity": quantity, "timestamp": datetime.now().isoformat(timespec="seconds"),
    })
    save_state(state)
    return True, f"{state['fellows'][fellow_id]} returned {quantity} unit(s) of {resource['name']}."


def search_by_name(state, term):
    term = term.strip().casefold()
    if not term:
        return []
    return [r for r in state["resources"] if term in r["name"].casefold()]


def filter_by_category(state, category):
    category = category.strip().casefold()
    if not category:
        return []
    return [r for r in state["resources"] if r["category"].casefold() == category]


def print_resource_results(results, empty_message="No matching resources found."):
    if not results:
        print(empty_message)
        return
    print(f"{'ID':<8} {'Name':<20} {'Category':<18} {'Total':>7} {'Available':>10} {'Borrowed':>9}")
    for r in results:
        print(f"{r['id']:<8} {r['name'][:19]:<20} {r['category'][:17]:<18} {r['total']:>7} {r['available']:>10} {r['total'] - r['available']:>9}")


def generate_report(state):
    total_units = sum(r["total"] for r in state["resources"])
    available_units = sum(r["available"] for r in state["resources"])
    borrowed_units = total_units - available_units
    low_stock = [r for r in state["resources"] if r["available"] < 3]
    borrowed_by_resource = {
        r["id"]: r["total"] - r["available"] for r in state["resources"]
    }
    highest = max(borrowed_by_resource.values(), default=0)
    leaders = [r for r in state["resources"] if borrowed_by_resource[r["id"]] == highest and highest > 0]

    print("\nLEARN2EARN INVENTORY REPORT")
    print("-" * 42)
    print(f"Total units:     {total_units}")
    print(f"Available units: {available_units}")
    print(f"Borrowed units:  {borrowed_units}")
    print("\nResources with fewer than 3 available units:")
    if low_stock:
        for r in low_stock:
            print(f"  - {r['name']} ({r['id']}): {r['available']} available")
    else:
        print("  None")
    print("\nResource(s) with the most units currently borrowed:")
    if leaders:
        for r in leaders:
            print(f"  - {r['name']} ({r['id']}): {borrowed_by_resource[r['id']]} borrowed")
    else:
        print("  No units are currently borrowed.")
    print("-" * 42)


def show_loans(state):
    if not state["loans"]:
        print("There are no outstanding loans.")
        return
    print("\nOUTSTANDING LOANS")
    for loan in state["loans"]:
        resource = resource_by_id(state, loan["resource_id"])
        name = resource["name"] if resource else loan["resource_id"]
        print(f"{loan['fellow_id']} ({state['fellows'].get(loan['fellow_id'], 'Unknown')}) — {name}: {loan['quantity']}")


def prompt_text(label):
    try:
        return input(label).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nInput cancelled.")
        return None


def prompt_positive_int(label):
    raw = prompt_text(label)
    if raw is None:
        return None
    number = safe_int(raw)
    if number is None or number <= 0:
        print("Invalid quantity. Enter a whole number greater than zero (for example, 2).")
        return None
    return number


def do_add_resource(state):
    resource_id = prompt_text("New resource ID: ")
    if resource_id is None:
        return
    name = prompt_text("Resource name: ")
    if name is None:
        return
    category = prompt_text("Category: ")
    if category is None:
        return
    total = prompt_positive_int("Total units: ")
    if total is None:
        return
    ok, message = add_resource(state, resource_id, name, category, total)
    print(message)


def do_borrow(state):
    fellow_id = prompt_text("Fellow ID (F001/F002/F003): ")
    if fellow_id is None:
        return
    resource_id = prompt_text("Resource ID (e.g. R001): ")
    if resource_id is None:
        return
    quantity = prompt_positive_int("Quantity to borrow: ")
    if quantity is None:
        return
    ok, message = borrow_resource(state, fellow_id, resource_id, quantity)
    print(message)


def do_return(state):
    fellow_id = prompt_text("Fellow ID: ")
    if fellow_id is None:
        return
    resource_id = prompt_text("Resource ID: ")
    if resource_id is None:
        return
    quantity = prompt_positive_int("Quantity to return: ")
    if quantity is None:
        return
    ok, message = return_resource(state, fellow_id, resource_id, quantity)
    print(message)


def run_demonstration():
    """Run the required scenario in order, resetting to the specified starting data first."""
    state = fresh_state()
    save_state(state)
    print("\n=== REQUIRED DEMONSTRATION (fresh starting data) ===")

    print("\n1. F001 borrows 2 laptops")
    print(borrow_resource(state, "F001", "R001", 2)[1])
    print(f"Laptop available units: {resource_by_id(state, 'R001')['available']} (expected 8)")

    print("\n2. F002 borrows 3 keyboards")
    print(borrow_resource(state, "F002", "R002", 3)[1])
    print(f"Keyboard available units: {resource_by_id(state, 'R002')['available']} (expected 2)")

    print("\n3. F001 returns 1 laptop")
    print(return_resource(state, "F001", "R001", 1)[1])
    print(f"Laptop available units: {resource_by_id(state, 'R001')['available']} (expected 9)")

    print("\n4. F003 requests 4 headsets (must be rejected)")
    before = resource_by_id(state, "R003")["available"]
    ok, message = borrow_resource(state, "F003", "R003", 4)
    print(f"{'UNEXPECTED SUCCESS' if ok else 'REJECTED'}: {message}")
    print(f"Headset available units: {resource_by_id(state, 'R003')['available']} (unchanged: {before})")

    print("\n5. F002 tries to return 4 keyboards (must be rejected)")
    before = resource_by_id(state, "R002")["available"]
    ok, message = return_resource(state, "F002", "R002", 4)
    print(f"{'UNEXPECTED SUCCESS' if ok else 'REJECTED'}: {message}")
    print(f"Keyboard available units: {resource_by_id(state, 'R002')['available']} (unchanged: {before})")

    print("\n6. Search for LAPtop (case-insensitive)")
    print_resource_results(search_by_name(state, "LAPtop"))

    print("\n7. Generate the report (expected totals: 18 total, 14 available, 4 borrowed)")
    generate_report(state)
    print(f"Data saved to: {DATA_FILE}")
    return state


def print_menu():
    print("""
========== LEARN2EARN ==========
1. List resources
2. Add resource
3. Borrow resource
4. Return resource
5. Search resources by name
6. Filter resources by category
7. Generate report
8. Run required demonstration (resets data first)
9. Show outstanding loans
0. Save and exit
===============================
""")


def main():
    state = load_state()
    print("Welcome to Learn2Earn Resource Lending.")
    print(f"Data file: {DATA_FILE}")
    while True:
        try:
            print_menu()
            choice = prompt_text("Choose an option (0-9): ")
            if choice is None:
                # A cancelled prompt should not crash the app; return to the menu.
                continue
            if choice == "0":
                save_state(state)
                print("Data saved. Thank you for using Learn2Earn Inventory! Goodbye!")
                break
            elif choice == "1":
                list_resources(state)
            elif choice == "2":
                do_add_resource(state)
            elif choice == "3":
                do_borrow(state)
            elif choice == "4":
                do_return(state)
            elif choice == "5":
                term = prompt_text("Enter all or part of a resource name: ")
                if term is not None:
                    print_resource_results(search_by_name(state, term))
            elif choice == "6":
                category = prompt_text("Enter category (e.g. Accessories): ")
                if category is not None:
                    print_resource_results(filter_by_category(state, category))
            elif choice == "7":
                generate_report(state)
            elif choice == "8":
                state = run_demonstration()
            elif choice == "9":
                show_loans(state)
            else:
                print("Invalid menu option. Please enter a number from 0 to 9.")
        except (EOFError, KeyboardInterrupt):
            print("\nExit requested. Saving data before closing.")
            save_state(state)
            break
        except Exception as exc:
            # Last-resort guard: report unexpected errors and keep the menu running.
            print(f"An unexpected problem occurred: {exc}")
            print("The program is still running. Please try that action again.")


if __name__ == "__main__":
    main()
