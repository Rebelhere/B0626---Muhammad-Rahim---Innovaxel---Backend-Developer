"""
Comprehensive test suite for the Event Registration System.
Tests all CRUD operations, validation, concurrency, and edge cases.

Run with: python -m pytest test_system.py -v
"""
import os
import json
import time
import tempfile
import threading
from datetime import date, timedelta
from unittest import TestCase, main as unittest_main

# Use a temp directory for test data
TEST_DIR = tempfile.mkdtemp()
TEST_DATA_FILE = os.path.join(TEST_DIR, "data.json")
TEST_LOCK_FILE = TEST_DATA_FILE + ".lock"

import storage
storage.DATA_FILE = TEST_DATA_FILE
storage.LOCK_FILE = TEST_LOCK_FILE
storage._file_lock = storage.FileLock(TEST_LOCK_FILE)
storage._cache = None
storage._cache_dirty = True

import event_manager


def cleanup():
    """Remove test data files and invalidate cache."""
    storage._cache = None
    storage._cache_dirty = True
    for f in [TEST_DATA_FILE, TEST_LOCK_FILE,
              TEST_DATA_FILE + ".tmp", TEST_DATA_FILE + ".lock"]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except OSError:
            pass


class TestCreateEvent(TestCase):
    def setUp(self):
        cleanup()

    def test_create_event_success(self):
        future = (date.today() + timedelta(days=30)).isoformat()
        event = event_manager.create_event("Tech Conference", 100, future)
        self.assertEqual(event.name, "Tech Conference")
        self.assertEqual(event.total_seats, 100)
        self.assertEqual(event.event_date, future)
        self.assertIsNotNone(event.id)

    def test_create_event_unique_name(self):
        future = (date.today() + timedelta(days=30)).isoformat()
        event_manager.create_event("Python Meetup", 50, future)
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.create_event("Python Meetup", 30, future)

    def test_create_event_case_insensitive_unique(self):
        future = (date.today() + timedelta(days=30)).isoformat()
        event_manager.create_event("Python Meetup", 50, future)
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.create_event("python meetup", 30, future)

    def test_create_event_empty_name(self):
        future = (date.today() + timedelta(days=30)).isoformat()
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.create_event("", 50, future)

    def test_create_event_whitespace_name(self):
        future = (date.today() + timedelta(days=30)).isoformat()
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.create_event("   ", 50, future)

    def test_create_event_zero_seats(self):
        future = (date.today() + timedelta(days=30)).isoformat()
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.create_event("Zero Event", 0, future)

    def test_create_event_negative_seats(self):
        future = (date.today() + timedelta(days=30)).isoformat()
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.create_event("Negative Event", -5, future)

    def test_create_event_past_date(self):
        past = (date.today() - timedelta(days=1)).isoformat()
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.create_event("Past Event", 50, past)

    def test_create_event_today_date(self):
        today = date.today().isoformat()
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.create_event("Today Event", 50, today)

    def test_create_event_invalid_date_format(self):
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.create_event("Bad Date", 50, "not-a-date")

    def test_create_event_invalid_month_50(self):
        with self.assertRaises(event_manager.EventManagerError) as ctx:
            event_manager.create_event("Bad Month", 10, "2026-50-10")
        self.assertIn("Invalid month", str(ctx.exception))

    def test_create_event_invalid_day_32(self):
        with self.assertRaises(event_manager.EventManagerError) as ctx:
            event_manager.create_event("Bad Day", 10, "2026-01-32")
        self.assertIn("Invalid day", str(ctx.exception))

    def test_create_event_feb_29_non_leap(self):
        with self.assertRaises(event_manager.EventManagerError) as ctx:
            event_manager.create_event("Leap Test", 10, "2025-02-29")
        self.assertIn("not a leap year", str(ctx.exception))

    def test_create_event_feb_29_leap_year(self):
        result = event_manager._validate_date("2028-02-29")
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 29)

    def test_create_multiple_unique_events(self):
        future1 = (date.today() + timedelta(days=30)).isoformat()
        future2 = (date.today() + timedelta(days=60)).isoformat()
        e1 = event_manager.create_event("Event A", 10, future1)
        e2 = event_manager.create_event("Event B", 20, future2)
        self.assertNotEqual(e1.id, e2.id)


class TestRegisterUser(TestCase):
    def setUp(self):
        cleanup()
        self.future = (date.today() + timedelta(days=30)).isoformat()
        self.event = event_manager.create_event("Test Event", 5, self.future)

    def test_register_success(self):
        reg = event_manager.register_user("Alice", self.event.id)
        self.assertEqual(reg.user_name, "Alice")
        self.assertEqual(reg.event_id, self.event.id)
        self.assertFalse(reg.cancelled)

    def test_register_nonexistent_event(self):
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.register_user("Bob", "fake-id-12345")

    def test_register_duplicate_user(self):
        event_manager.register_user("Charlie", self.event.id)
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.register_user("Charlie", self.event.id)

    def test_register_duplicate_case_insensitive(self):
        event_manager.register_user("Charlie", self.event.id)
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.register_user("charlie", self.event.id)

    def test_register_empty_user_name(self):
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.register_user("", self.event.id)

    def test_register_event_full(self):
        for i in range(5):
            event_manager.register_user(f"User{i}", self.event.id)
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.register_user("Overflow", self.event.id)

    def test_different_users_can_register(self):
        reg1 = event_manager.register_user("User1", self.event.id)
        reg2 = event_manager.register_user("User2", self.event.id)
        self.assertNotEqual(reg1.id, reg2.id)

    def test_register_after_cancel(self):
        event_manager.register_user("Dave", self.event.id)
        event_manager.cancel_registration("Dave", self.event.id)
        reg = event_manager.register_user("Dave", self.event.id)
        self.assertFalse(reg.cancelled)


class TestCancelRegistration(TestCase):
    def setUp(self):
        cleanup()
        self.future = (date.today() + timedelta(days=30)).isoformat()
        self.event = event_manager.create_event("Cancel Test", 5, self.future)

    def test_cancel_success(self):
        event_manager.register_user("Eve", self.event.id)
        result = event_manager.cancel_registration("Eve", self.event.id)
        self.assertTrue(result.cancelled)
        self.assertIsNotNone(result.cancelled_at)

    def test_cancel_nonexistent(self):
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.cancel_registration("Nobody", self.event.id)

    def test_cancel_already_cancelled(self):
        event_manager.register_user("Frank", self.event.id)
        event_manager.cancel_registration("Frank", self.event.id)
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.cancel_registration("Frank", self.event.id)

    def test_seat_freed_after_cancel(self):
        for i in range(5):
            event_manager.register_user(f"User{i}", self.event.id)
        with self.assertRaises(event_manager.EventManagerError):
            event_manager.register_user("Overflow", self.event.id)
        event_manager.cancel_registration("User0", self.event.id)
        reg = event_manager.register_user("NewUser", self.event.id)
        self.assertFalse(reg.cancelled)

    def test_cancel_case_insensitive(self):
        event_manager.register_user("Grace", self.event.id)
        result = event_manager.cancel_registration("grace", self.event.id)
        self.assertTrue(result.cancelled)


class TestViewEvents(TestCase):
    def setUp(self):
        cleanup()
        self.future = (date.today() + timedelta(days=30)).isoformat()
        self.past = (date.today() + timedelta(days=5)).isoformat()
        self.far_future = (date.today() + timedelta(days=60)).isoformat()
        self.event1 = event_manager.create_event("Alpha", 10, self.future)
        self.event2 = event_manager.create_event("Beta", 5, self.past)
        self.event3 = event_manager.create_event("Gamma", 20, self.far_future)

    def test_view_all_events(self):
        events = event_manager.get_events(upcoming_only=False, sort_by_date=True)
        self.assertEqual(len(events), 3)
        dates = [e["event_date"] for e in events]
        self.assertEqual(dates, sorted(dates))

    def test_view_upcoming_only(self):
        events = event_manager.get_events(upcoming_only=True, sort_by_date=True)
        today = date.today()
        for e in events:
            event_dt = date.fromisoformat(e["event_date"])
            self.assertGreaterEqual(event_dt, today)

    def test_available_seats_correct(self):
        event_manager.register_user("A", self.event1.id)
        event_manager.register_user("B", self.event1.id)
        events = event_manager.get_events(upcoming_only=False)
        e = next(ev for ev in events if ev["id"] == self.event1.id)
        self.assertEqual(e["available_seats"], 8)
        self.assertEqual(e["total_registrations"], 2)

    def test_available_seats_after_cancel(self):
        event_manager.register_user("C", self.event1.id)
        event_manager.cancel_registration("C", self.event1.id)
        events = event_manager.get_events(upcoming_only=False)
        e = next(ev for ev in events if ev["id"] == self.event1.id)
        self.assertEqual(e["available_seats"], 10)
        self.assertEqual(e["total_registrations"], 0)

    def test_empty_events_list(self):
        cleanup()
        events = event_manager.get_events(upcoming_only=False)
        self.assertEqual(events, [])


class TestViewRegistrations(TestCase):
    def setUp(self):
        cleanup()
        self.future = (date.today() + timedelta(days=30)).isoformat()
        self.event = event_manager.create_event("Reg View", 10, self.future)

    def test_active_only(self):
        event_manager.register_user("Active1", self.event.id)
        event_manager.register_user("Active2", self.event.id)
        event_manager.register_user("WillCancel", self.event.id)
        event_manager.cancel_registration("WillCancel", self.event.id)

        active = event_manager.get_registrations_for_event(self.event.id, active_only=True)
        names = [r["user_name"] for r in active]
        self.assertIn("Active1", names)
        self.assertIn("Active2", names)
        self.assertNotIn("WillCancel", names)
        self.assertEqual(len(active), 2)

    def test_all_registrations(self):
        event_manager.register_user("User1", self.event.id)
        event_manager.cancel_registration("User1", self.event.id)

        all_regs = event_manager.get_registrations_for_event(self.event.id, active_only=False)
        self.assertEqual(len(all_regs), 1)
        self.assertTrue(all_regs[0]["cancelled"])


class TestConcurrency(TestCase):
    def setUp(self):
        cleanup()
        self.future = (date.today() + timedelta(days=30)).isoformat()
        self.event = event_manager.create_event("Race Test", 10, self.future)

    def test_no_overbooking_concurrent(self):
        """20 threads try to register for 10 seats. Only 10 should succeed."""
        results = {"success": 0, "failed": 0}
        lock = threading.Lock()

        def attempt(user_name):
            try:
                event_manager.register_user(user_name, self.event.id)
                with lock:
                    results["success"] += 1
            except event_manager.EventManagerError:
                with lock:
                    results["failed"] += 1

        threads = [threading.Thread(target=attempt, args=(f"U{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(results["success"], 10)
        self.assertEqual(results["failed"], 10)

        events = event_manager.get_events(upcoming_only=False)
        e = next(ev for ev in events if ev["id"] == self.event.id)
        self.assertEqual(e["available_seats"], 0)
        self.assertEqual(e["total_registrations"], 10)

    def test_concurrent_duplicate_prevention(self):
        """Same user registered by 10 threads — only 1 should succeed."""
        results = {"success": 0, "failed": 0}
        lock = threading.Lock()

        def attempt():
            try:
                event_manager.register_user("SameUser", self.event.id)
                with lock:
                    results["success"] += 1
            except event_manager.EventManagerError:
                with lock:
                    results["failed"] += 1

        threads = [threading.Thread(target=attempt) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(results["success"], 1)
        self.assertEqual(results["failed"], 9)


class TestPersistence(TestCase):
    def setUp(self):
        cleanup()

    def test_data_persists(self):
        future = (date.today() + timedelta(days=30)).isoformat()
        event = event_manager.create_event("Persistent", 10, future)
        event_manager.register_user("Alice", event.id)

        with open(TEST_DATA_FILE, "r") as f:
            raw = json.load(f)
        self.assertEqual(len(raw["events"]), 1)
        self.assertEqual(len(raw["registrations"]), 1)

    def test_read_after_write(self):
        future = (date.today() + timedelta(days=30)).isoformat()
        event = event_manager.create_event("Read Test", 10, future)
        event_manager.register_user("Bob", event.id)

        events = event_manager.get_events(upcoming_only=False)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["name"], "Read Test")
        self.assertEqual(events[0]["total_registrations"], 1)


if __name__ == "__main__":
    unittest_main(verbosity=2)
