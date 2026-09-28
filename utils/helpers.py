"""
Shared helpers - Python ports of the helpers used by the CI4 controllers.

Ports:
  * financial-year logic           (Taxinv::gentaxinv, Quote::genquote, ...)
  * next-invoice-number generation (CONCAT_WS('/', FY, LPAD(count+1,4,0)))
  * money formatting               (money_format helper)
  * Indian currency words          (number → words used on print views)
"""
from datetime import date


def financial_year(today: date | None = None) -> str:
    """'23-24' style financial-year string (April → March), as in controllers."""
    t = today or date.today()
    if t.month > 3:
        return f"{t.year % 100:02d}-{t.year % 100 + 1:02d}"
    return f"{t.year % 100 - 1:02d}-{t.year % 100:02d}"


def fy_start(today: date | None = None) -> date:
    """First day of the running financial year (1 April)."""
    t = today or date.today()
    year = t.year if t.month > 3 else t.year - 1
    return date(year, 4, 1)


def money(value, symbol: str = "₹ ") -> str:
    """Indian-grouped currency string: ₹ 12,34,567.00"""
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0
    neg = value < 0
    value = abs(value)
    whole = int(value)
    frac = int(round((value - whole) * 100))
    if frac == 100:
        whole += 1
        frac = 0
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return f"{'-' if neg else ''}{symbol}{s}.{frac:02d}"


def number_to_words(num: int) -> str:
    """Indian numbering (lakh/crore) words - used on printed invoices."""
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
            "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
            "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
            "Eighty", "Ninety"]

    def two(n: int) -> str:
        return ones[n] if n < 20 else (tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")).strip()

    def three(n: int) -> str:
        h, r = divmod(n, 100)
        return ((ones[h] + " Hundred" if h else "") + (" " + two(r) if r else "")).strip()

    num = int(num)
    if num == 0:
        return "Zero"
    crore, num = divmod(num, 10000000)
    lakh, num = divmod(num, 100000)
    thousand, rest = divmod(num, 1000)
    words = []
    if crore:
        words.append(two(crore) + " Crore")
    if lakh:
        words.append(two(lakh) + " Lakh")
    if thousand:
        words.append(two(thousand) + " Thousand")
    if rest:
        words.append(three(rest))
    return " ".join(words)
