"""
Core business logic for the Event Registration System.
"""
import re
from collections import defaultdict
from datetime import datetime, date
from typing import Optional

from models import Event, Registration
from storage import atomic_update, read_data


class EventManagerError(Exception):
    pass


def _validate_date(date_str: str) -> date:
    raw = date_str.strip()

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        raise EventManagerError(
            f"Invalid date format: '{raw}'. Expected YYYY-MM-DD (e.g. 2027-03-15)."
        )

    parts = raw.split("-")
    year  = int(parts[0])
    month = int(parts[1])
    day   = int(parts[2])

    if month < 1 or month > 12:
        raise EventManagerError(
            f"Invalid month: {month}. Month must be between 01 and 12."
        )

    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    if is_leap:
        days_in_month[2] = 29

    max_day = days_in_month[month]

    if day < 1:
        raise EventManagerError(f"Invalid day: {day}. Day must be at least 01.")

    if day > max_day:
        month_name = datetime(2000, month, 1).strftime("%B")
        if month == 2:
            leap_info = " (leap year)" if is_leap else " (not a leap year)"
            raise EventManagerError(
                f"Invalid day: {day} for {month_name} {year}{leap_info}. "
                f"{month_name} {year} has {max_day} days."
            )
        raise EventManagerError(
            f"Invalid day: {day} for {month_name}. "
            f"{month_name} has {max_day} days."
        )

    try:
        return date(year, month, day)
    except ValueError:
        raise EventManagerError(
            f"Invalid date: {raw}. Please check year, month, and day values."
        )


def _build_indexes(data: dict) -> dict:
    # Index events by ID and by name
    event_by_id: dict = {}
    event_names: dict = {}
    for e in data["events"]:
        event_by_id[e["id"]] = e
        event_names[e["name"].lower()] = e["id"]

    # Single pass through registrations to build all registration indexes
    reg_count_by_event: dict = defaultdict(int)
    active_reg_lookup: set = set()
    regs_by_event: dict = defaultdict(list)

    for r in data["registrations"]:
        eid = r["event_id"]
        regs_by_event[eid].append(r)
        if not r["cancelled"]:
            reg_count_by_event[eid] += 1
            active_reg_lookup.add((eid, r["user_name"].lower()))

    return {
        "event_by_id": event_by_id,
        "event_names": event_names,
        "reg_count_by_event": reg_count_by_event,
        "active_reg_lookup": active_reg_lookup,
        "regs_by_event": regs_by_event,
    }

def create_event(name: str, total_seats: int, event_date: str) -> Event:
    """
    Create a new event with validation.
    """
    name = name.strip()
    if not name:
        raise EventManagerError("Event name cannot be empty.")

    if total_seats <= 0:
        raise EventManagerError("Total seats must be greater than 0.")

    event_dt = _validate_date(event_date)

    today = date.today()
    if event_dt <= today:
        raise EventManagerError(f"Event date must be in the future. Today is {today}.")

    def _create(data: dict) -> Event:
        # O(1) name lookup via hash set instead of O(n) scan
        idx = _build_indexes(data)
        if name.lower() in idx["event_names"]:
            raise EventManagerError(f"An event with name '{name}' already exists.")

        event = Event(name=name, total_seats=total_seats, event_date=event_date.strip())
        data["events"].append(event.to_dict())
        return event

    return atomic_update(_create)

def register_user(user_name: str, event_id: str) -> Registration:
    user_name = user_name.strip()
    event_id = event_id.strip()

    if not user_name:
        raise EventManagerError("User name cannot be empty.")
    if not event_id:
        raise EventManagerError("Event ID is required.")

    def _register(data: dict) -> Registration:
        idx = _build_indexes(data)

        event = idx["event_by_id"].get(event_id)
        if event is None:
            raise EventManagerError(f"Event with ID '{event_id}' not found.")

        # O(1) seat count (was O(r) scan)
        active_count = idx["reg_count_by_event"].get(event_id, 0)
        if active_count >= event["total_seats"]:
            raise EventManagerError(
                f"Event '{event['name']}' is full. No seats available."
            )

        if (event_id, user_name.lower()) in idx["active_reg_lookup"]:
            raise EventManagerError(
                f"User '{user_name}' is already registered for event '{event['name']}'."
            )

        registration = Registration(user_name=user_name, event_id=event_id)
        data["registrations"].append(registration.to_dict())
        return registration

    return atomic_update(_register)

def cancel_registration(user_name: str, event_id: str) -> Registration:
    user_name = user_name.strip()
    event_id = event_id.strip()

    if not user_name:
        raise EventManagerError("User name cannot be empty.")
    if not event_id:
        raise EventManagerError("Event ID is required.")

    def _cancel(data: dict) -> Registration:
        idx = _build_indexes(data)

        # Only iterate registrations for this specific event, not all registrations
        user_lower = user_name.lower()
        for r in idx["regs_by_event"].get(event_id, []):
            if r["event_id"] == event_id and r["user_name"].lower() == user_lower and not r["cancelled"]:
                r["cancelled"] = True
                r["cancelled_at"] = datetime.now().isoformat()
                return Registration.from_dict(r)

        raise EventManagerError(
            f"No active registration found for '{user_name}' on event '{event_id}'."
        )

    return atomic_update(_cancel)

def get_events(upcoming_only: bool = False, sort_by_date: bool = True) -> list:
    data = read_data()
    idx = _build_indexes(data)

    today_str = date.today().isoformat()  
    events = []

    for e in data["events"]:
        if upcoming_only and e["event_date"] < today_str:
            continue

        active_count = idx["reg_count_by_event"].get(e["id"], 0)

        events.append({
            "id": e["id"],
            "name": e["name"],
            "total_seats": e["total_seats"],
            "event_date": e["event_date"],
            "available_seats": e["total_seats"] - active_count,
            "total_registrations": active_count,
            "created_at": e.get("created_at", ""),
        })

    if sort_by_date:
        events.sort(key=lambda x: x["event_date"])

    return events


def edit_event(event_id: str, new_name: str = None, new_total_seats: int = None, new_event_date: str = None) -> Event:
    event_id = event_id.strip()
    if not event_id:
        raise EventManagerError("Event ID is required.")

    if new_name is None and new_total_seats is None and new_event_date is None:
        raise EventManagerError("At least one field (name, total_seats, or event_date) must be provided.")

    def _edit(data: dict) -> Event:
        idx = _build_indexes(data)

        event = idx["event_by_id"].get(event_id)
        if event is None:
            raise EventManagerError(f"Event with ID '{event_id}' not found.")

        active_count = idx["reg_count_by_event"].get(event_id, 0)

        if new_name is not None:
            stripped = new_name.strip()
            if not stripped:
                raise EventManagerError("Event name cannot be empty.")
            name_lower = stripped.lower()
            for eid, ev in idx["event_by_id"].items():
                if eid != event_id and ev["name"].lower() == name_lower:
                    raise EventManagerError(f"An event with name '{stripped}' already exists.")
            event["name"] = stripped

        if new_total_seats is not None:
            if new_total_seats <= 0:
                raise EventManagerError("Total seats must be greater than 0.")
            if new_total_seats < active_count:
                raise EventManagerError(
                    f"Cannot reduce seats to {new_total_seats}. "
                    f"There are already {active_count} active registrations."
                )
            event["total_seats"] = new_total_seats

        if new_event_date is not None:
            new_dt = _validate_date(new_event_date)
            today = date.today()
            if new_dt <= today:
                raise EventManagerError(f"Event date must be in the future. Today is {today}.")
            event["event_date"] = new_event_date.strip()

        return Event.from_dict(event)

    return atomic_update(_edit)


def get_event_by_id(event_id: str) -> Optional[dict]:
    data = read_data()
    idx = _build_indexes(data)
    return idx["event_by_id"].get(event_id)

def get_registrations_for_event(event_id: str, active_only: bool = True) -> list:
    data = read_data()
    idx = _build_indexes(data)

    regs = idx["regs_by_event"].get(event_id, [])
    if active_only:
        return [r for r in regs if not r["cancelled"]]
    return list(regs)
