"""
Pure financial calculation utilities for Indian real estate.
All monetary values are in INR.
"""

from tools.coerce import to_float, to_str


def calculate_emi(principal: float, annual_rate_pct: float, tenure_years: int) -> float:
    """Calculate monthly EMI using reducing-balance formula."""
    r = annual_rate_pct / (12 * 100)
    n = tenure_years * 12
    if r == 0:
        return principal / n
    emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return round(emi, 2)


def calculate_gross_rental_yield(annual_rent_inr: float, property_price_inr: float) -> float:
    """Gross rental yield as a percentage."""
    if property_price_inr == 0:
        return 0.0
    return round((annual_rent_inr / property_price_inr) * 100, 2)


def calculate_cap_rate(
    annual_rent_inr: float,
    annual_expenses_inr: float,
    property_price_inr: float,
) -> float:
    """Cap rate = NOI / property value."""
    noi = annual_rent_inr - annual_expenses_inr
    if property_price_inr == 0:
        return 0.0
    return round((noi / property_price_inr) * 100, 2)


def calculate_price_per_sqft(price_inr: float, area_sqft: float) -> float:
    if area_sqft == 0:
        return 0.0
    return round(price_inr / area_sqft, 2)


def estimate_stamp_duty_and_registration(price_inr: float, state: str = "Maharashtra") -> dict:
    """Rough stamp duty + registration estimates for common Indian states."""
    rates = {
        "Maharashtra": {"stamp_duty_pct": 5.0, "registration_pct": 1.0},
        "Karnataka": {"stamp_duty_pct": 5.6, "registration_pct": 1.0},
        "Delhi": {"stamp_duty_pct": 6.0, "registration_pct": 1.0},
        "Tamil Nadu": {"stamp_duty_pct": 7.0, "registration_pct": 1.0},
        "Telangana": {"stamp_duty_pct": 5.0, "registration_pct": 0.5},
    }
    r = rates.get(state, {"stamp_duty_pct": 5.0, "registration_pct": 1.0})
    stamp_duty = round(price_inr * r["stamp_duty_pct"] / 100, 2)
    registration = round(price_inr * r["registration_pct"] / 100, 2)
    return {
        "stamp_duty_inr": stamp_duty,
        "registration_inr": registration,
    }


def estimate_payback_years(
    property_price_inr: float, annual_rent_inr: float, annual_appreciation_pct: float = 5.0
) -> float:
    """Years to recover investment via rent + appreciation."""
    if annual_rent_inr + (property_price_inr * annual_appreciation_pct / 100) == 0:
        return float("inf")
    annual_return = annual_rent_inr + property_price_inr * annual_appreciation_pct / 100
    return round(property_price_inr / annual_return, 1)


def full_financial_profile(property: dict, home_loan_rate_pct: float = 8.75) -> dict:
    """
    Generate a complete financial profile for a property dict.
    Expected keys: price_inr, area_sqft, monthly_rent_inr (optional),
                   annual_expenses_inr (optional), state (optional)
    home_loan_rate_pct: live-fetched rate passed in by the analyst agent.
    """
    price = to_float(property.get("price_inr"), 0.0)
    area = to_float(property.get("area_sqft"), 0.0)
    monthly_rent = to_float(property.get("monthly_rent_inr"), 0.0)
    annual_rent = monthly_rent * 12
    annual_expenses = to_float(property.get("annual_expenses_inr"), annual_rent * 0.15)
    state = to_str(property.get("state"), "Maharashtra") or "Maharashtra"

    loan_amount = price * 0.80  # 80% LTV
    txn = estimate_stamp_duty_and_registration(price, state)
    return {
        "purchase_price_inr": price,
        "carpet_area_sqft": area if area else None,
        "price_per_sqft_inr": calculate_price_per_sqft(price, area),
        "expected_monthly_rent_inr": monthly_rent,
        "gross_rental_yield_pct": calculate_gross_rental_yield(annual_rent, price),
        "cap_rate_pct": calculate_cap_rate(annual_rent, annual_expenses, price),
        "emi_inr": calculate_emi(loan_amount, home_loan_rate_pct, 20),
        "home_loan_rate_pct": home_loan_rate_pct,
        "loan_tenure_years": 20,
        "loan_amount_inr": loan_amount,
        "stamp_duty_inr": txn["stamp_duty_inr"],
        "registration_inr": txn["registration_inr"],
        "payback_years": estimate_payback_years(price, annual_rent),
    }
