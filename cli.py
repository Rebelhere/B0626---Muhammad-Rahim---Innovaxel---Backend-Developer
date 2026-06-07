"""
Pretty CLI interface for the Event Registration System using Rich library.
"""
import sys
from datetime import date

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich import box

from event_manager import (
    create_event,
    register_user,
    cancel_registration,
    edit_event,
    get_events,
    get_event_by_id,
    get_registrations_for_event,
    EventManagerError,
)

console = Console()


def print_header():
    console.print(
        Panel(
            "[bold cyan]Event Registration System[/bold cyan]",
            box=box.DOUBLE,
            style="bright_white",
        )
    )


def print_menu():
    table = Table(box=box.ROUNDED, show_header=False, border_style="cyan")
    table.add_column("Key", style="bold yellow", justify="center")
    table.add_column("Action", style="white")
    table.add_row("1", "Create Event")
    table.add_row("2", "Register User for Event")
    table.add_row("3", "View Events")
    table.add_row("4", "View Registrations for an Event")
    table.add_row("5", "Edit Event")
    table.add_row("6", "Cancel Registration")
    table.add_row("7", "Exit")
    console.print(table)


def handle_create_event():
    console.print("\n[bold green]Create New Event[/bold green]")
    console.print("[dim]Enter event details (or 'back' to return)[/dim]\n")

    name = Prompt.ask("Event name")
    if name.lower() == "back":
        return

    total_seats = IntPrompt.ask("Total seats")
    event_date = Prompt.ask("Event date (YYYY-MM-DD)")

    try:
        event = create_event(name, total_seats, event_date)
        console.print(
            f"\n[bold green]Event created successfully![/bold green]\n"
            f"  [cyan]ID:[/cyan]    {event.id}\n"
            f"  [cyan]Name:[/cyan]  {event.name}\n"
            f"  [cyan]Seats:[/cyan] {event.total_seats}\n"
            f"  [cyan]Date:[/cyan]  {event.event_date}\n"
        )
    except EventManagerError as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]\n")


def handle_register_user():
    console.print("\n[bold green]Register User for Event[/bold green]")

    events = get_events(upcoming_only=False, sort_by_date=True)
    if not events:
        console.print("[yellow]No events available to register for.[/yellow]\n")
        return

    event_table = Table(box=box.SIMPLE_HEAVY, border_style="dim")
    event_table.add_column("Event ID", style="cyan", no_wrap=True)
    event_table.add_column("Name", style="white", min_width=16, max_width=28)
    event_table.add_column("Date", style="yellow", justify="center", min_width=12, no_wrap=True)
    event_table.add_column("Seats (Avail/Total)", style="green", justify="center", min_width=18, no_wrap=True)
    for e in events:
        avail = e["available_seats"]
        total = e["total_seats"]
        avail_style = "green" if avail > 0 else "red"
        event_table.add_row(
            e["id"][:8] + "...",
            e["name"],
            e["event_date"],
            f"[{avail_style}]{avail}/{total}[/{avail_style}]",
        )
    console.print(event_table)

    event_id = Prompt.ask("\nEvent ID (full ID)")
    user_name = Prompt.ask("User name")

    full_event_id = event_id
    if len(event_id) < 36:
        prefix = event_id.rstrip(".")
        for e in events:
            if e["id"].startswith(prefix):
                full_event_id = e["id"]
                break

    try:
        registration = register_user(user_name, full_event_id)
        console.print(
            f"\n[bold green]Registration successful![/bold green]\n"
            f"  [cyan]Registration ID:[/cyan] {registration.id}\n"
            f"  [cyan]User:[/cyan]           {registration.user_name}\n"
            f"  [cyan]Registered at:[/cyan]  {registration.registered_at}\n"
        )
    except EventManagerError as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]\n")


def handle_view_events():
    console.print("\n[bold green]View Events[/bold green]\n")

    filter_choice = Prompt.ask(
        "Filter", choices=["all", "upcoming"], default="upcoming"
    )
    upcoming_only = filter_choice == "upcoming"

    events = get_events(upcoming_only=upcoming_only, sort_by_date=True)

    if not events:
        label = "upcoming events" if upcoming_only else "events"
        console.print(f"[yellow]No {label} found.[/yellow]\n")
        return

    table = Table(
        title="Events" + (" (Upcoming Only)" if upcoming_only else ""),
        box=box.HEAVY_EDGE,
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("#", style="dim", justify="center", width=4, no_wrap=True)
    table.add_column("ID", style="bright_black", width=38, no_wrap=True)
    table.add_column("Name", style="white", min_width=18, max_width=30)
    table.add_column("Date", style="yellow", justify="center", min_width=12, no_wrap=True)
    table.add_column("Total Seats", justify="center", style="blue", min_width=11, no_wrap=True)
    table.add_column("Available", justify="center", style="green", min_width=9, no_wrap=True)
    table.add_column("Registered", justify="center", style="magenta", min_width=11, no_wrap=True)

    for i, e in enumerate(events, 1):
        avail = e["available_seats"]
        avail_style = "green" if avail > 0 else "bold red"
        table.add_row(
            str(i),
            e["id"],
            e["name"],
            e["event_date"],
            str(e["total_seats"]),
            f"[{avail_style}]{avail}[/{avail_style}]",
            str(e["total_registrations"]),
        )

    console.print(table)
    console.print()


def handle_view_registrations():
    console.print("\n[bold green]View Registrations for Event[/bold green]\n")

    events = get_events(upcoming_only=False, sort_by_date=True)
    if not events:
        console.print("[yellow]No events found.[/yellow]\n")
        return

    event_table = Table(box=box.SIMPLE_HEAVY, border_style="dim")
    event_table.add_column("Event ID", style="cyan", no_wrap=True)
    event_table.add_column("Name", style="white", min_width=16, max_width=28)
    event_table.add_column("Date", style="yellow", justify="center", min_width=12, no_wrap=True)
    for e in events:
        event_table.add_row(e["id"][:8] + "...", e["name"], e["event_date"])
    console.print(event_table)

    event_id = Prompt.ask("\nEvent ID")
    full_event_id = event_id
    if len(event_id) < 36:
        prefix = event_id.rstrip(".")
        for e in events:
            if e["id"].startswith(prefix):
                full_event_id = e["id"]
                break

    regs = get_registrations_for_event(full_event_id, active_only=True)
    event = get_event_by_id(full_event_id)

    if event is None:
        console.print("[red]Event not found.[/red]\n")
        return

    if not regs:
        console.print(
            f"[yellow]No active registrations for '{event['name']}'.[/yellow]\n"
        )
        return

    table = Table(
        title=f"Registrations: {event['name']}",
        box=box.HEAVY_EDGE,
        border_style="green",
    )
    table.add_column("#", style="dim", justify="center", width=4, no_wrap=True)
    table.add_column("User Name", style="white", min_width=18, max_width=30)
    table.add_column("Registered At", style="cyan", min_width=22, no_wrap=True)

    for i, r in enumerate(regs, 1):
        table.add_row(str(i), r["user_name"], r["registered_at"])

    console.print(table)
    console.print()


def handle_edit_event():
    console.print("\n[bold blue]Edit Event[/bold blue]")

    events = get_events(upcoming_only=False, sort_by_date=True)
    if not events:
        console.print("[yellow]No events found.[/yellow]\n")
        return

    event_table = Table(box=box.SIMPLE_HEAVY, border_style="dim")
    event_table.add_column("Event ID", style="cyan", no_wrap=True)
    event_table.add_column("Name", style="white", min_width=16, max_width=28)
    event_table.add_column("Date", style="yellow", justify="center", min_width=12, no_wrap=True)
    event_table.add_column("Total Seats", style="blue", justify="center", min_width=11, no_wrap=True)
    event_table.add_column("Available", style="green", justify="center", min_width=9, no_wrap=True)
    event_table.add_column("Registered", style="magenta", justify="center", min_width=11, no_wrap=True)
    for e in events:
        avail = e["available_seats"]
        avail_style = "green" if avail > 0 else "bold red"
        event_table.add_row(
            e["id"][:8] + "...",
            e["name"],
            e["event_date"],
            str(e["total_seats"]),
            f"[{avail_style}]{avail}[/{avail_style}]",
            str(e["total_registrations"]),
        )
    console.print(event_table)

    event_id = Prompt.ask("\nEvent ID (full ID)")
    full_event_id = event_id
    if len(event_id) < 36:
        prefix = event_id.rstrip(".")
        for e in events:
            if e["id"].startswith(prefix):
                full_event_id = e["id"]
                break

    # Verify event exists
    event = get_event_by_id(full_event_id)
    if event is None:
        console.print("[red]Event not found.[/red]\n")
        return

    console.print(f"\n[dim]Editing: [bold]{event['name']}[/bold][/dim]")
    console.print("[dim]Leave a field blank to keep its current value.[/dim]\n")

    # Show current values and ask for new ones
    new_name = Prompt.ask(f"  Name [{event['name']}]", default="")
    new_seats_str = Prompt.ask(f"  Total Seats [{event['total_seats']}]", default="")
    new_date = Prompt.ask(f"  Event Date [{event['event_date']}]", default="")

    # Only pass fields that were actually changed
    kwargs = {}
    if new_name.strip():
        kwargs["new_name"] = new_name.strip()
    if new_seats_str.strip():
        try:
            seats = int(new_seats_str.strip())
            kwargs["new_total_seats"] = seats
        except ValueError:
            console.print("[red]Invalid number for total seats.[/red]\n")
            return
    if new_date.strip():
        kwargs["new_event_date"] = new_date.strip()

    if not kwargs:
        console.print("[yellow]No changes made.[/yellow]\n")
        return

    try:
        updated = edit_event(full_event_id, **kwargs)
        console.print(
            f"\n[bold green]Event updated successfully![/bold green]\n"
            f"  [cyan]ID:[/cyan]    {updated.id}\n"
            f"  [cyan]Name:[/cyan]  {updated.name}\n"
            f"  [cyan]Seats:[/cyan] {updated.total_seats}\n"
            f"  [cyan]Date:[/cyan]  {updated.event_date}\n"
        )
    except EventManagerError as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]\n")


def handle_cancel_registration():
    console.print("\n[bold yellow]Cancel Registration[/bold yellow]\n")

    events = get_events(upcoming_only=False, sort_by_date=True)
    if not events:
        console.print("[yellow]No events found.[/yellow]\n")
        return

    event_table = Table(box=box.SIMPLE_HEAVY, border_style="dim")
    event_table.add_column("Event ID", style="cyan", no_wrap=True)
    event_table.add_column("Name", style="white", min_width=16, max_width=28)
    event_table.add_column("Date", style="yellow", justify="center", min_width=12, no_wrap=True)
    event_table.add_column("Registrations", style="magenta", justify="center", min_width=13, no_wrap=True)
    for e in events:
        event_table.add_row(
            e["id"][:8] + "...", e["name"], e["event_date"], str(e["total_registrations"])
        )
    console.print(event_table)

    event_id = Prompt.ask("\nEvent ID")
    user_name = Prompt.ask("User name")

    full_event_id = event_id
    if len(event_id) < 36:
        prefix = event_id.rstrip(".")
        for e in events:
            if e["id"].startswith(prefix):
                full_event_id = e["id"]
                break

    try:
        registration = cancel_registration(user_name, full_event_id)
        console.print(
            f"\n[bold yellow]Registration cancelled successfully![/bold yellow]\n"
            f"  [cyan]Registration ID:[/cyan] {registration.id}\n"
            f"  [cyan]User:[/cyan]           {registration.user_name}\n"
            f"  [cyan]Cancelled at:[/cyan]   {registration.cancelled_at}\n"
        )
    except EventManagerError as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]\n")


def main():
    print_header()

    while True:
        print_menu()
        choice = Prompt.ask(
            "\nSelect an option",
            choices=["1", "2", "3", "4", "5", "6", "7"],
            default="3",
        )

        if choice == "1":
            handle_create_event()
        elif choice == "2":
            handle_register_user()
        elif choice == "3":
            handle_view_events()
        elif choice == "4":
            handle_view_registrations()
        elif choice == "5":
            handle_edit_event()
        elif choice == "6":
            handle_cancel_registration()
        elif choice == "7":
            console.print("\n[bold cyan]Goodbye![/bold cyan]\n")
            sys.exit(0)


if __name__ == "__main__":
    main()
