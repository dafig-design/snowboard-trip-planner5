"""
Snowboard Trip Planner
Final Project - Drafter web application

Purpose: Help people pick a snowboarding resort that fits their region and
budget, then estimate what the whole trip will cost and save the estimates
so different plans can be compared.

NOTE: The resort numbers below are rough sample data for the project.
Update them with real prices, ratings and snowfall before you rely on them.
"""
from dataclasses import dataclass, field
from bakery import assert_equal
from drafter import *

# ---------------------------------------------------------------------------
# Global constants (allowed by the project requirements)
# ---------------------------------------------------------------------------
REGIONS = ["All", "Mid-Atlantic", "Northeast", "Rockies", "West"]
LODGING_OPTIONS = ["Hotel", "Cabin", "Hostel"]
RENTAL_PRICE_PER_DAY = 55.0   # snowboard + boots + helmet, per person
FOOD_PER_DAY = 40.0           # per person
NO_LIMIT = 9999.0             # used when the user leaves the budget blank


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class Resort:
    """Information about one resort (used for the constant RESORT_DATA)."""
    name: str
    location: str
    region: str
    difficulty_level: str      # "beginner", "intermediate", "expert"
    lift_ticket_price: float   # per person, per day
    rating: float              # average review score out of 5
    snowfall_inches: float     # average annual snowfall
    best_months: str           # when conditions are usually best


@dataclass
class CostEstimate:
    """One saved trip estimate."""
    label: str                 # e.g. "Wisp Resort - Cabin"
    amount_per_person: float   # total cost for one person for the whole trip
    days: int                  # how many days of riding
    category: str              # lodging type: "Hotel", "Cabin", "Hostel"
    group_size: int            # how many people are going
    notes: str                 # optional notes from the user


@dataclass
class State:
    """Everything the website needs to remember between pages."""
    selected_resort: str                  # name of the chosen resort
    lift_ticket_price: float              # ticket price of the chosen resort
    is_selected: bool                     # True once a resort is chosen
    estimates: list[CostEstimate] = field(default_factory=list)
    error: str = ""                       # message shown on the form
    region_filter: str = "All"            # region used on the resort list
    max_ticket: float = NO_LIMIT          # budget used on the resort list


# Sample resort data (constant): resort name -> Resort
RESORT_DATA = {
    "Wisp Resort": Resort("Wisp Resort", "McHenry, MD", "Mid-Atlantic",
                          "beginner", 95.0, 3.9, 100.0, "Jan - Feb"),
    "Blue Mountain": Resort("Blue Mountain", "Palmerton, PA", "Mid-Atlantic",
                            "intermediate", 85.0, 3.8, 85.0, "Jan - Feb"),
    "Snowshoe": Resort("Snowshoe", "Snowshoe, WV", "Mid-Atlantic",
                       "intermediate", 105.0, 4.1, 180.0, "Jan - Mar"),
    "Killington": Resort("Killington", "Killington, VT", "Northeast",
                         "intermediate", 150.0, 4.2, 250.0, "Jan - Mar"),
    "Stowe": Resort("Stowe", "Stowe, VT", "Northeast",
                    "expert", 160.0, 4.6, 314.0, "Jan - Mar"),
    "Breckenridge": Resort("Breckenridge", "Breckenridge, CO", "Rockies",
                           "intermediate", 190.0, 4.5, 300.0, "Jan - Mar"),
    "Vail": Resort("Vail", "Vail, CO", "Rockies",
                   "expert", 220.0, 4.7, 354.0, "Jan - Mar"),
    "Mammoth Mountain": Resort("Mammoth Mountain", "Mammoth Lakes, CA",
                               "West", "intermediate", 175.0, 4.4, 400.0,
                               "Feb - Apr"),
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def parse_positive_int(text: str) -> int:
    """Turn text into a whole number of at least 1, or return 0 if invalid."""
    cleaned = text.strip()
    if not cleaned.isdigit():
        return 0
    return int(cleaned)


def parse_budget(text: str) -> float:
    """Turn a budget string into a float, or NO_LIMIT if blank/invalid."""
    cleaned = text.strip().replace("$", "")
    if cleaned.replace(".", "", 1).isdigit():
        return float(cleaned)
    return NO_LIMIT


def format_money(amount: float) -> str:
    """Format a number as dollars, like $1,234.50."""
    # format(number, ",.2f") adds commas and keeps exactly 2 decimal places
    return "$" + format(amount, ",.2f")


def lodging_price_per_night(lodging: str) -> float:
    """Return the per-person nightly price for a lodging type."""
    if lodging == "Hotel":
        return 90.0
    elif lodging == "Cabin":
        return 70.0
    else:
        return 40.0


def cost_per_person(ticket_price: float, days: int, lodging: str,
                    needs_rentals: bool) -> float:
    """Total trip cost for one person (tickets, lodging, food, rentals)."""
    total = ticket_price * days
    total += lodging_price_per_night(lodging) * days
    total += FOOD_PER_DAY * days
    if needs_rentals:
        total += RENTAL_PRICE_PER_DAY * days
    return total


def total_cost(estimate: CostEstimate) -> float:
    """Total cost for the whole group for one saved estimate."""
    return estimate.amount_per_person * estimate.group_size


def matching_resorts(region: str, max_ticket: float) -> list[Resort]:
    """Return resorts in the region whose lift ticket fits the budget."""
    matches = []
    for resort in RESORT_DATA.values():
        in_region = region == "All" or resort.region == region
        if in_region and resort.lift_ticket_price <= max_ticket:
            matches.append(resort)
    return matches


def describe_resort(resort: Resort) -> str:
    """One-paragraph summary of a resort for the list page."""
    return (resort.name + " (" + resort.location + ") - " +
            resort.difficulty_level + ", lift ticket " +
            format_money(resort.lift_ticket_price) + "/day, rated " +
            str(resort.rating) + "/5, about " +
            str(round(resort.snowfall_inches)) + " in. of snow a year, " +
            "best months: " + resort.best_months + ".")


def describe_estimate(estimate: CostEstimate) -> str:
    """Summary text of one saved estimate."""
    text = (estimate.label + ": " + str(estimate.group_size) +
            " people for " + str(estimate.days) + " days = " +
            format_money(estimate.amount_per_person) + " per person, " +
            format_money(total_cost(estimate)) + " total.")
    if estimate.notes != "":
        text += " Notes: " + estimate.notes
    return text


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@route
def index(state: State) -> Page:
    """Home page: shows the current choice and the main links."""
    content = [Header("Snowboard Trip Planner", 1),
               "Find a resort that fits your budget and estimate what your "
               "trip will cost."]
    if state.is_selected:
        content.append("Current resort: " + state.selected_resort + " (" +
                       format_money(state.lift_ticket_price) +
                       "/day lift ticket)")
    else:
        content.append("You have not picked a resort yet.")
    content.append(LineBreak())
    content.append(Button("Choose a resort", choose_resort))
    content.append(Button("Estimate trip cost", estimate_form))
    content.append(Button("Saved estimates", saved_estimates))
    return Page(state, content)


@route
def choose_resort(state: State) -> Page:
    """Resort list page with a region and budget filter."""
    content = [Header("Choose a Resort", 1),
               "Region:",
               SelectBox("region", REGIONS, state.region_filter),
               "Max lift ticket price per day (leave blank for no limit):",
               TextBox("max_ticket", ""),
               Button("Apply filter", apply_filter),
               HorizontalRule()]
    resorts = matching_resorts(state.region_filter, state.max_ticket)
    if len(resorts) == 0:
        content.append("No resorts match that filter.")
    for resort in resorts:
        content.append(describe_resort(resort))
        content.append(Button("Select " + resort.name, select_resort,
                              [Argument("resort_name", resort.name)]))
        content.append(HorizontalRule())
    content.append(Button("Back to home", index))
    return Page(state, content)


@route
def apply_filter(state: State, region: str, max_ticket: str) -> Page:
    """Save the filter choices, then show the resort list again."""
    state.region_filter = region
    state.max_ticket = parse_budget(max_ticket)
    return choose_resort(state)


@route
def select_resort(state: State, resort_name: str) -> Page:
    """Remember which resort the user picked, then go to the cost form."""
    if resort_name in RESORT_DATA:
        state.selected_resort = resort_name
        state.lift_ticket_price = RESORT_DATA[resort_name].lift_ticket_price
        state.is_selected = True
        state.error = ""
    return estimate_form(state)


@route
def estimate_form(state: State) -> Page:
    """Form where the user describes their trip."""
    if not state.is_selected:
        return Page(state, [Header("Estimate Trip Cost", 1),
                            "Pick a resort first so we know the ticket price.",
                            Button("Choose a resort", choose_resort),
                            Button("Back to home", index)])
    content = [Header("Trip to " + state.selected_resort, 1)]
    if state.error != "":
        content.append("Error: " + state.error)
    content.extend(["How many people are going?",
                    TextBox("group_size", "2"),
                    "How many days of riding?",
                    TextBox("num_days", "3"),
                    "Lodging type:",
                    SelectBox("lodging", LODGING_OPTIONS, "Cabin"),
                    CheckBox("needs_rentals", False),
                    "Need rental gear?",
                    LineBreak(),
                    "Notes (optional):",
                    TextArea("notes", ""),
                    Button("Calculate and save", save_estimate),
                    Button("Back to home", index)])
    return Page(state, content)


@route
def save_estimate(state: State, group_size: str, num_days: str,
                  lodging: str, needs_rentals: bool, notes: str) -> Page:
    """Check the form, save a new CostEstimate, and show the result."""
    people = parse_positive_int(group_size)
    days = parse_positive_int(num_days)
    if people < 1 or days < 1:
        state.error = "Group size and days must be whole numbers of 1 or more."
        return estimate_form(state)
    state.error = ""
    per_person = cost_per_person(state.lift_ticket_price, days, lodging,
                                 needs_rentals)
    new_estimate = CostEstimate(state.selected_resort + " - " + lodging,
                                per_person, days, lodging, people,
                                notes.strip())
    state.estimates.append(new_estimate)
    return Page(state, [Header("Estimate Saved", 1),
                        describe_estimate(new_estimate),
                        Button("See all saved estimates", saved_estimates),
                        Button("Plan another trip", choose_resort),
                        Button("Back to home", index)])


@route
def saved_estimates(state: State) -> Page:
    """List every saved estimate, each with a delete button."""
    content = [Header("Saved Estimates", 1)]
    if len(state.estimates) == 0:
        content.append("No estimates yet.")
    for index_number, estimate in enumerate(state.estimates):
        content.append(describe_estimate(estimate))
        content.append(Button("Delete", delete_estimate,
                              [Argument("index", index_number)]))
        content.append(HorizontalRule())
    content.append(Button("Back to home", index))
    return Page(state, content)


@route
def delete_estimate(state: State, index: int) -> Page:
    """Remove one saved estimate, then show the list again."""
    if 0 <= index < len(state.estimates):
        state.estimates.pop(index)
    return saved_estimates(state)


# ---------------------------------------------------------------------------
# Unit tests (helpers and routes)
# ---------------------------------------------------------------------------
assert_equal(parse_positive_int("4"), 4)
assert_equal(parse_positive_int("abc"), 0)
assert_equal(parse_positive_int("-2"), 0)
assert_equal(parse_budget("$100"), 100.0)
assert_equal(parse_budget(""), NO_LIMIT)
assert_equal(format_money(1234.5), "$1,234.50")
assert_equal(lodging_price_per_night("Hotel"), 90.0)
assert_equal(lodging_price_per_night("Cabin"), 70.0)
assert_equal(lodging_price_per_night("Hostel"), 40.0)
# 2 days: tickets 200 + lodging 140 + food 80 = 420, rentals add 110
assert_equal(cost_per_person(100.0, 2, "Cabin", False), 420.0)
assert_equal(cost_per_person(100.0, 2, "Cabin", True), 530.0)
assert_equal(total_cost(CostEstimate("x", 100.0, 2, "Cabin", 3, "")), 300.0)
assert_equal(len(matching_resorts("All", NO_LIMIT)), len(RESORT_DATA))
assert_equal(len(matching_resorts("West", NO_LIMIT)), 1)
assert_equal(len(matching_resorts("All", 90.0)), 1)

test_state = State("", 0.0, False)
assert_equal(select_resort(test_state, "Wisp Resort").state.selected_resort,
             "Wisp Resort")
assert_equal(test_state.is_selected, True)
assert_equal(apply_filter(test_state, "West", "").state.region_filter, "West")
saved = save_estimate(test_state, "2", "3", "Cabin", True, "")
assert_equal(len(saved.state.estimates), 1)
bad = save_estimate(test_state, "zero", "3", "Cabin", True, "")
assert_equal(len(bad.state.estimates), 1)
assert_equal(delete_estimate(test_state, 0).state.estimates, [])
assert_equal(index(State("", 0.0, False)).state.is_selected, False)
assert_equal(choose_resort(State("", 0.0, False)).state.region_filter, "All")
assert_equal(estimate_form(State("", 0.0, False)).state.error, "")
assert_equal(saved_estimates(State("", 0.0, False)).state.estimates, [])

start_server(State("", 0.0, False))


