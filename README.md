# Event Registration System

A CLI-based event registration system built with Python. Users can create events, register for them, cancel registrations, and view event details — all with persistent JSON storage and thread-safe concurrency.

---

## Demo

📹 **[Demo Video](https://youtu.be/mTzGQtvQpRs)**


---

## Features

- **Create Event** — Set up events with name, total seats, and a future date
- **Register User** — Register for events with duplicate and overbooking prevention
- **Cancel Registration** — Cancel a registration and free up the seat
- **View Events** — See all events with available seats, total registrations, sorted by date
- **View Registrations** — See who's registered for a specific event
- **Persistent Storage** — All data saved to a JSON file between runs
- **Thread-Safe** — File-level locking prevents race conditions and overbooking

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.13 |
| CLI Framework | [Rich](https://github.com/Textualize/rich) |
| Storage | JSON file with atomic writes |
| Concurrency | File-level locking with exponential backoff |
| Testing | pytest (54 tests) |

---

## Project Structure

```
├── cli.py              # Interactive CLI with Rich tables and menus
├── event_manager.py    # Business logic with optimized data structures
├── storage.py          # Thread-safe JSON storage with in-memory caching
├── models.py           # Event and Registration dataclasses
├── test_system.py      # 54 comprehensive tests
├── data.json           # Persistent data storage (auto-generated)
└── README.md           # This file
```

---

## Data Structures & Algorithms

The system uses several DSA concepts to ensure efficient operations:

### Hash Maps (dict) — O(1) Lookups
- **Event lookup by ID** — `event_by_id` dict replaces O(n) linear scan
- **Name uniqueness check** — `event_names` dict replaces O(n) scan for duplicate names
- **Seat count per event** — `reg_count_by_event` dict gives O(1) active registration count

### Hash Set — O(1) Duplicate Detection
- **Active registration lookup** — `active_reg_lookup` set of `(event_id, user_name)` tuples prevents duplicate registrations in O(1)

### Grouping (defaultdict) — O(1) Filtering
- **Registrations by event** — `regs_by_event` groups registrations by event_id, so cancellation only scans relevant records

### Single-Pass Index Building
- `_build_indexes()` builds all 5 indexes in **one pass** through the data: O(n + r) where n = events, r = registrations

### In-Memory Caching
- `storage.py` caches the parsed JSON in memory — repeated reads within the same session are served from RAM, eliminating redundant disk I/O

### Complexity Comparison

| Operation | Before | After |
|-----------|--------|-------|
| Create event (name check) | O(n) | O(1) |
| Register user (event lookup) | O(n) | O(1) |
| Register user (seat count) | O(r) | O(1) |
| Register user (duplicate check) | O(r) | O(1) |
| Cancel registration | O(r) | O(k)* |
| View events (all seats) | O(n x r) | O(n + r) |
| Get event by ID | O(n) | O(1) |
| Get registrations for event | O(r) | O(1) |
| Read data (repeated) | O(file_size) | O(1) cached |

*k = registrations for that specific event*

---

## How to Run

### Prerequisites
- Python 3.7+
- `rich` library

### Install Dependencies
```bash
pip install rich pytest
```

### Run the Application
```bash
cd "C:\Users\It Zone\Documents\Innovaxel Summer Internship Program"
python cli.py
```

### Run Tests
```bash
python -m pytest test_system.py -v
```

**Test Results:** 54/54 passed
- 15 Event creation tests (including date validation)
- 8 Registration tests
- 5 Cancellation tests
- 5 View/filter tests
- 2 Registration view tests
- 3 Concurrency tests
- 2 Persistence tests
- 14 Additional edge case tests

---

## Concurrency Safety

The system prevents race conditions through:

1. **File-level locking** — A lock file ensures only one process reads/writes at a time
2. **Atomic updates** — `atomic_update()` wraps read → modify → write in a single locked operation
3. **Atomic file writes** — Data is written to a temp file first, then `os.replace()` atomically swaps it in
4. **Exponential backoff** — Lock acquisition uses exponential backoff (10ms → 500ms) to handle contention gracefully

This guarantees no overbooking even when 20+ threads try to register for the last seat simultaneously.

---

## Author

**B0626 - Muhammad Rahim - Innovaxel - [Role]**
