"""
Pure financial calculation utilities for Indian real estate.
All monetary values are in INR.
"""


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
        "total_transaction_cost_inr": round(stamp_duty + registration, 2),
    }


def estimate_payback_years(
    property_price_inr: float, annual_rent_inr: float, annual_appreciation_pct: float = 5.0
) -> float:
    """Years to recover investment via rent + appreciation."""
    if annual_rent_inr + (property_price_inr * annual_appreciation_pct / 100) == 0:
        return float("inf")
    annual_return = annual_rent_inr + property_price_inr * annual_appreciation_pct / 100
    return round(property_price_inr / annual_return, 1)


def full_financial_profile(property: dict) -> dict:
    """
    Generate a complete financial profile for a property dict.
    Expected keys: price_inr, area_sqft, monthly_rent_inr (optional),
                   annual_expenses_inr (optional), state (optional)
    """
    price = property.get("price_inr", 0)
    area = property.get("area_sqft", 0)
    monthly_rent = property.get("monthly_rent_inr", 0)
    annual_rent = monthly_rent * 12
    annual_expenses = property.get("annual_expenses_inr", annual_rent * 0.15)  # 15% default
    state = property.get("state", "Maharashtra")

    loan_amount = price * 0.80  # 80% LTV
    return {
        "price_inr": price,
        "price_per_sqft": calculate_price_per_sqft(price, area),
        "emi_8pct_20yr": calculate_emi(loan_amount, 8.5, 20),
        "gross_rental_yield_pct": calculate_gross_rental_yield(annual_rent, price),
        "cap_rate_pct": calculate_cap_rate(annual_rent, annual_expenses, price),
        "payback_years": estimate_payback_years(price, annual_rent),
        "transaction_costs": estimate_stamp_duty_and_registration(price, state),
        "total_investment_inr": price + estimate_stamp_duty_and_registration(price, state)["total_transaction_cost_inr"],
    }
