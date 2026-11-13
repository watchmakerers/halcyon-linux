"""Calculator logic, after the Windows calculator of the Vista era. No Qt here.

Standard mode works left to right (2 + 3 * 4 = 20), like Windows; Scientific
mode respects precedence and parentheses (2 + 3 * 4 = 14). Decimal maths
keeps 0.1 + 0.2 exact. Hex/Oct/Bin work on 64-bit two's-complement integers.

Keys are strings: "0".."9", "A".."F", ".", "+", "-", "*", "/", "=", "%",
"sqrt", "recip", "neg", "clear" (C), "CE", "back", "MC", "MR", "MS", "M+", "(", ")",
"sin", "cos", "tan", "x^y", "x^2", "x^3", "n!", "ln", "log", "pi", "Exp",
"Mod", "And", "Or", "Xor", "Not", "Lsh".

    python3 -m halcyon_calc.engine --selftest
"""
import decimal
import math
import sys
from decimal import Decimal

CTX = decimal.Context(prec=34, rounding=decimal.ROUND_HALF_EVEN, Emin=-9999, Emax=9999)
SHOW = 32                                  # significant digits shown
BITS = 64
MASK = (1 << BITS) - 1
BASES = {"hex": 16, "dec": 10, "oct": 8, "bin": 2}
DIGITS = "0123456789ABCDEF"
# Scientific precedence (higher binds tighter); x^y is right-associative.
PREC = {"Or": 1, "Xor": 2, "And": 3, "Lsh": 4, "+": 5, "-": 5, "*": 6, "/": 6, "Mod": 6, "x^y": 7}
BINARY = set(PREC)


class CalcError(Exception):
    pass


def to_signed(n):
    n &= MASK
    return n - (1 << BITS) if n >> (BITS - 1) else n


def fmt_int(n, base):
    """Integers in a base; negative numbers show as two's complement outside decimal."""
    if base == 10:
        return str(n)
    n &= MASK
    if n == 0:
        return "0"
    out = ""
    while n:
        out = DIGITS[n % base] + out
        n //= base
    return out


def fmt_dec(x):
    """A Decimal for the display: up to 32 significant digits, no trailing zeros,
    scientific notation for very large or small numbers."""
    if x.is_nan() or x.is_infinite():
        raise CalcError("Invalid input")
    if x == 0:
        return "0"
    x = CTX.plus(x)
    q = x.quantize(Decimal(1).scaleb(x.adjusted() - SHOW + 1), context=CTX) if x.adjusted() < 9999 else x
    q = q.normalize(CTX)
    exp = q.adjusted()
    if -16 <= exp < SHOW:
        s = format(q, "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s
    mant = q.scaleb(-exp).normalize(CTX)
    m = format(mant, "f")
    if "." in m:
        m = m.rstrip("0").rstrip(".")
    return f"{m}e{'+' if exp > 0 else ''}{exp}"


def dec(v):
    if isinstance(v, Decimal):
        return v
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            raise CalcError("Invalid input")
        # floats carry ~15 good digits; past that is noise (acos(0.5) -> 60.00000000000001)
        return CTX.create_decimal(f"{v:.15g}")
    return CTX.create_decimal(v)


class Engine:
    def __init__(self):
        self.mode = "standard"             # or "scientific"
        self.base = "dec"
        self.angle = "deg"                 # deg, rad, grad
        self.inv = False
        self.hyp = False
        self.memory = Decimal(0)
        self.has_memory = False
        self.clear()

    # ------------------------------------------------------------- state ---
    def clear(self):
        self.entry = "0"                   # what's being typed (or the last result)
        self.typing = False                # True while digits are going into entry
        self.error = ""
        # standard mode: a running total and the pending operator
        self.acc = None
        self.pending = None
        self.last_op = None                # (op, right) for repeated =
        # scientific mode: operand and operator stacks
        self.values, self.ops = [], []
        self.just_closed = False

    @property
    def radix(self):
        return BASES[self.base] if self.mode == "scientific" else 10

    @property
    def integer_mode(self):
        return self.radix != 10

    @property
    def parens(self):
        return self.ops.count("(")

    def display(self):
        if self.error:
            return self.error
        return self.entry

    def value(self):
        """The number in the display."""
        if self.integer_mode:
            return to_signed(int(self.entry, self.radix)) if self.entry not in ("", "-") else 0
        s = self.entry
        if s.endswith("e") or s.endswith("e+") or s.endswith("e-"):
            s = s.rstrip("e+-")
        try:
            return CTX.create_decimal(s or "0")
        except decimal.InvalidOperation:
            raise CalcError("Invalid input")

    def show(self, v):
        """Put a result in the display."""
        if self.integer_mode:
            self.entry = fmt_int(to_signed(int(v)), self.radix)
        else:
            self.entry = fmt_dec(dec(v))
        self.typing = False

    # ------------------------------------------------------------- input ---
    def press(self, key):
        if self.error and key not in ("clear", "CE"):
            if key in DIGITS[:self.radix] or key in (".", "pi", "MR"):
                self.clear()
            else:
                return self.display()
        try:
            self._press(key)
        except CalcError as e:
            self.clear()
            self.error = str(e)
        except (decimal.InvalidOperation, decimal.Overflow, OverflowError, ValueError, ZeroDivisionError):
            self.clear()
            self.error = "Invalid input"
        return self.display()

    def _press(self, key):
        if key in DIGITS and DIGITS.index(key) < self.radix and len(key) == 1:
            self._digit(key)
        elif key == ".":
            if self.integer_mode:
                return
            if not self.typing:
                self.entry, self.typing = "0.", True
            elif "." not in self.entry and "e" not in self.entry:
                self.entry += "."
        elif key == "back":
            if self.typing:
                self.entry = self.entry[:-1]
                if self.entry in ("", "-", "-0"):
                    self.entry, self.typing = "0", False
        elif key == "clear":                      # "C" is also a hex digit, so Clear has its own name
            self.clear()
        elif key == "CE":
            self.entry, self.typing, self.error = "0", False, ""
        elif key == "neg":
            self._negate()
        elif key in ("MC", "MR", "MS", "M+"):
            self._memory(key)
        elif key == "Exp":
            if not self.integer_mode and "e" not in self.entry:
                self.entry += "e+"
                self.typing = True
        elif key == "pi":
            self.show(Decimal("3.141592653589793238462643383279503"))
        elif key in BINARY:
            self._binary(key)
        elif key == "=":
            self._equals()
        elif key == "%":
            self._percent()
        elif key == "(":
            if self.mode == "scientific":
                self.ops.append("(")
                self.entry, self.typing = "0", False
        elif key == ")":
            self._close()
        else:
            self._unary(key)

    def _digit(self, d):
        if not self.typing or self.just_closed:
            self.entry, self.typing, self.just_closed = d, True, False
            return
        if "e" in self.entry:
            exp = self.entry.split("e")[1].lstrip("+-")
            if len(exp) < 4:
                self.entry = self.entry[:-1] if self.entry.endswith(("e+0", "e-0")) else self.entry
                self.entry += d
            return
        if self.entry == "0":
            self.entry = d
        elif self.entry == "-0":
            self.entry = "-" + d
        else:
            limit = {16: 16, 8: 22, 2: 64}.get(self.radix, SHOW)
            if len(self.entry.replace("-", "").replace(".", "")) < limit:
                self.entry += d

    def _negate(self):
        if self.typing and not self.integer_mode:
            if "e" in self.entry:
                m, e = self.entry.split("e")
                self.entry = m + "e" + ("-" + e[1:] if e.startswith("+") else "+" + e[1:])
            else:
                self.entry = self.entry[1:] if self.entry.startswith("-") else "-" + self.entry
        else:
            self.show(-self.value())

    def _memory(self, key):
        if key == "MC":
            self.memory, self.has_memory = Decimal(0), False
        elif key == "MR":
            self.show(self.memory if not self.integer_mode else int(self.memory))
        elif key == "MS":
            self.memory, self.has_memory = dec(self.value()), True
            self.typing = False
        else:
            self.memory, self.has_memory = CTX.add(self.memory, dec(self.value())), True
            self.typing = False

    # -------------------------------------------------------- arithmetic ---
    def apply(self, op, a, b):
        if self.integer_mode:
            a, b = int(a), int(b)
            if op in ("/", "Mod") and b == 0:
                raise CalcError("Cannot divide by zero")
            r = {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b,
                 "/": lambda: abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1),   # truncates toward zero
                 "Mod": lambda: a - b * (abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1)),
                 "And": lambda: a & b, "Or": lambda: a | b, "Xor": lambda: a ^ b,
                 "Lsh": lambda: a << (b & 63) if b >= 0 else a >> (-b & 63),
                 "x^y": lambda: a ** b if b >= 0 else 0}[op]()
            return to_signed(r)
        a, b = dec(a), dec(b)
        if op == "+":
            return CTX.add(a, b)
        if op == "-":
            return CTX.subtract(a, b)
        if op == "*":
            return CTX.multiply(a, b)
        if op == "/":
            if b == 0:
                raise CalcError("Cannot divide by zero" if a != 0 else "Result is undefined")
            return CTX.divide(a, b)
        if op == "Mod":
            if b == 0:
                raise CalcError("Cannot divide by zero")
            return CTX.subtract(a, CTX.multiply(b, CTX.divide_int(a, b).copy_abs() *
                                                 (1 if (a < 0) == (b < 0) else -1)))
        if op == "x^y":
            if self.inv:                        # y-th root of x
                self.inv = False
                if b == 0:
                    raise CalcError("Invalid input")
                if a < 0 and b == b.to_integral_value() and int(b) % 2:
                    return dec(-(float(-a) ** (1 / float(b))))
                return dec(float(a) ** (1 / float(b)))
            if b == b.to_integral_value() and abs(b) <= 10000:
                return CTX.power(a, int(b))
            if a < 0:
                raise CalcError("Invalid input")
            return CTX.power(a, b)
        if op in ("And", "Or", "Xor", "Lsh"):
            ia, ib = int(a), int(b)
            return Decimal(self.apply_int(op, ia, ib))
        raise CalcError("Invalid input")

    @staticmethod
    def apply_int(op, a, b):
        return to_signed({"And": a & b, "Or": a | b, "Xor": a ^ b,
                          "Lsh": a << (b & 63) if b >= 0 else a >> (-b & 63)}[op])

    def _binary(self, op):
        if self.mode == "standard":
            if op not in ("+", "-", "*", "/"):
                return
            if self.pending and not self.typing:
                self.pending = op                 # pressed twice: the last one counts
                return
            v = self.value()
            if self.pending is not None:
                v = self.apply(self.pending, self.acc, v)
                self.show(v)
            self.acc, self.pending, self.typing = v, op, False
            self.last_op = None
            return
        # scientific: precedence with operator and value stacks
        if self.ops and self.ops[-1] in BINARY and not self.typing and not self.just_closed and \
                len(self.values) == len([o for o in self.ops if o in BINARY]):
            self.ops[-1] = op                     # replace an operator pressed twice
            return
        self.values.append(self.value())
        self._reduce(PREC[op], right_assoc=op == "x^y")
        self.ops.append(op)
        if self.values:
            self.show(self.values[-1])
        self.typing = self.just_closed = False

    def _reduce(self, prec=0, right_assoc=False):
        while self.ops and self.ops[-1] != "(":
            top = self.ops[-1]
            if PREC[top] > prec or (PREC[top] == prec and not right_assoc):
                self.ops.pop()
                b = self.values.pop()
                a = self.values.pop()
                self.values.append(self.apply(top, a, b))
            else:
                break

    def _close(self):
        if self.mode != "scientific" or "(" not in self.ops:
            return
        self.values.append(self.value())
        self._reduce(0)
        if self.ops and self.ops[-1] == "(":
            self.ops.pop()
        self.show(self.values.pop())
        self.just_closed = True

    def _equals(self):
        if self.mode == "standard":
            if self.pending is not None:
                right = self.value()               # "5 + =" uses the display: 10
                v = self.apply(self.pending, self.acc, right)
                self.last_op = (self.pending, right)
                self.acc, self.pending = None, None
                self.show(v)
            elif self.last_op:                     # repeated =
                op, right = self.last_op
                self.show(self.apply(op, self.value(), right))
            self.typing = False
            return
        if self.values or self.ops:
            self.values.append(self.value())
            while "(" in self.ops:                 # close what's still open
                self._reduce(0)
                self.ops.pop()
            self._reduce(0)
            v = self.values.pop()
            last = None
            # remember the final operation for repeated =
            self.values, self.ops = [], []
            self.last_op = last
            self.show(v)
        self.typing = self.just_closed = False

    def _percent(self):
        """Windows: the display becomes that percent of the number before the operator."""
        if self.integer_mode:
            return
        base = self.acc if self.mode == "standard" else (self.values[-1] if self.values else None)
        if base is None:
            self.show(Decimal(0))
            return
        self.show(CTX.divide(CTX.multiply(dec(base), self.value()), Decimal(100)))

    # ------------------------------------------------------------ functions ---
    def _angle_in(self, x):
        return {"deg": math.radians(x), "rad": x, "grad": x * math.pi / 200}[self.angle]

    def _angle_out(self, x):
        return {"deg": math.degrees(x), "rad": x, "grad": x * 200 / math.pi}[self.angle]

    def _unary(self, key):
        inv, hyp = self.inv, self.hyp
        self.inv = self.hyp = False                # like Windows, Inv and Hyp apply once
        if self.integer_mode:
            v = int(self.value())
            if key == "Not":
                self.show(to_signed(~v))
            elif key == "neg":
                self.show(-v)
            elif key == "x^2":
                self.show(to_signed(v * v))
            elif key == "x^3":
                self.show(to_signed(v * v * v))
            elif key == "n!":
                if v < 0 or v > 20:
                    raise CalcError("Invalid input")
                self.show(to_signed(math.factorial(v)))
            return
        x = self.value()
        f = float(x)
        if key == "sqrt" or (key == "x^2" and inv):
            if x < 0:
                raise CalcError("Invalid input")
            r = CTX.sqrt(x)
        elif key == "x^2":
            r = CTX.multiply(x, x)
        elif key == "x^3":
            r = dec(math.copysign(abs(f) ** (1 / 3), f)) if inv else CTX.power(x, 3)
            if inv and round(float(r)) ** 3 == f:
                r = Decimal(round(float(r)))       # exact cube roots stay exact
        elif key == "recip":
            if x == 0:
                raise CalcError("Cannot divide by zero")
            r = CTX.divide(Decimal(1), x)
        elif key in ("sin", "cos", "tan"):
            if hyp and inv:
                r = {"sin": math.asinh, "cos": math.acosh, "tan": math.atanh}[key](f)
            elif hyp:
                r = {"sin": math.sinh, "cos": math.cosh, "tan": math.tanh}[key](f)
            elif inv:
                r = self._angle_out({"sin": math.asin, "cos": math.acos, "tan": math.atan}[key](f))
            else:
                a = self._angle_in(f)
                # exact zeros at multiples of the right angle (sin 180 = 0, cos 90 = 0, tan 45 = 1)
                if key == "tan" and abs(math.cos(a)) < 1e-15:
                    raise CalcError("Invalid input")
                r = {"sin": math.sin, "cos": math.cos, "tan": math.tan}[key](a)
                r = round(r, 15)                   # sin(180) is 1.2e-16 in floats: call it 0
            r = dec(r)
        elif key == "ln":
            if inv:
                r = CTX.exp(x)
            else:
                if x <= 0:
                    raise CalcError("Invalid input")
                r = CTX.ln(x)
        elif key == "log":
            if inv:
                r = CTX.power(Decimal(10), x)
            else:
                if x <= 0:
                    raise CalcError("Invalid input")
                r = CTX.log10(x)
        elif key == "n!":
            if x < 0:
                raise CalcError("Invalid input")
            if x == x.to_integral_value() and x <= 3000:
                r = Decimal(math.factorial(int(x)))
            else:
                r = dec(math.gamma(f + 1))
        elif key == "Not":                         # bitwise on the whole-number part, like Windows in Dec
            r = Decimal(to_signed(~int(x)))
        else:
            raise CalcError("Invalid input")
        self.show(r)

    # -------------------------------------------------------------- modes ---
    def set_mode(self, mode):
        if mode != self.mode:
            v = self.value() if not self.error else 0
            self.mode = mode
            if mode == "standard":
                self.base = "dec"
            self.clear()
            self.show(v)

    def set_base(self, base):
        """Switching base converts the displayed number (to an integer outside decimal)."""
        v = self.value() if not self.error else 0
        self.base = base
        self.clear()
        if base == "dec":
            self.show(Decimal(int(v)) if isinstance(v, int) else v)
        else:
            self.show(to_signed(int(v)))

    def paste(self, text):
        """Type a pasted number (digits only; anything else is ignored)."""
        for ch in text.strip().upper():
            if ch in DIGITS[:self.radix] or (ch == "." and not self.integer_mode):
                self.press(ch)
            elif ch == "-" and self.entry in ("0", ""):
                pass
        return self.display()


# ---------------------------------------------------------------- selftest ---
def group(text, base="dec"):
    """Digit grouping for the display: 1,234,567.89 in decimal, 1111 0000 / FFFF FFFF otherwise."""
    if not text or not (text[0].isdigit() or text[0] == "-" or text[0] in DIGITS) or "e" in text.lower() and base == "dec":
        return text
    sign = "-" if text.startswith("-") else ""
    body = text.lstrip("-")
    if base == "dec":
        whole, dot, frac = body.partition(".")
        out = f"{int(whole):,}" if whole.isdigit() else whole
        return sign + out + dot + frac
    n = 4 if base in ("hex", "bin") else 3
    head = len(body) % n
    parts = ([body[:head]] if head else []) + [body[i:i + n] for i in range(head, len(body), n)]
    return sign + " ".join(parts)


def run(keys, mode="standard", base=None, angle=None):
    e = Engine()
    e.set_mode(mode)
    if base:
        e.set_base(base)
    if angle:
        e.angle = angle
    for k in keys.split():
        if k == "INV":
            e.inv = True
        elif k == "HYP":
            e.hyp = True
        else:
            e.press(k)
    return e.display()


def _selftest():
    cases = [
        ("1 2 + 7 =", "19"),
        ("2 + 3 * 4 =", "20"),                       # standard: left to right
        (". 1 + . 2 =", "0.3"),                      # decimal maths
        ("5 + 3 = = =", "14"),                       # repeated =
        ("5 + =", "10"),
        ("1 0 - 3 = =", "4"),
        ("2 * * 3 =", "6"),
        ("2 + - 3 =", "-1"),                         # last operator counts
        ("5 0 + 1 0 % =", "55"),                     # 10% of 50
        ("2 0 0 * 1 0 % =", "4000"),
        ("1 / 3 =", "0.3333333333333333333333333333333333"[:34]),
        ("1 / 0 =", "Cannot divide by zero"),
        ("0 / 0 =", "Result is undefined"),
        ("9 sqrt", "3"),
        ("4 neg sqrt", "Invalid input"),
        ("4 recip", "0.25"),
        ("7 neg", "-7"),
        ("1 2 3 back back", "1"),
        ("5 MS clear MR + 1 =", "6"),
        ("5 MS 3 M+ clear MR", "8"),
        ("9 9 9 9 9 9 9 9 9 * 9 9 9 9 9 9 9 9 9 =", "999999998000000001"),
        ("1 Exp 3 0 0 * 1 Exp 3 0 0 =", "1e+600"),
        ("1 + 2 CE 5 =", "6"),
        ("1 / 0 = 7", "7"),                          # a digit after an error starts over
    ]
    sci = [
        ("2 + 3 * 4 =", "14"),                       # precedence
        ("( 2 + 3 ) * 4 =", "20"),
        ("2 * ( 3 + 4 ) =", "14"),
        ("( ( 1 + 2 ) * ( 3 + 4 ) ) =", "21"),
        ("2 x^y 3 =", "8"),
        ("2 x^y 3 x^y 2 =", "512"),                  # right-associative
        ("2 x^y . 5 =", "1.4142135623730950488016887242097"),
        ("1 7 Mod 5 =", "2"),
        ("7 neg Mod 3 =", "-1"),                     # sign follows the dividend, like Windows
        ("( 2 + 3 =", "5"),                          # = closes open parentheses
        ("9 0 sin", "1"),
        ("1 8 0 sin", "0"),
        ("9 0 cos", "0"),
        ("4 5 tan", "1"),
        ("9 0 tan", "Invalid input"),
        ("1 INV sin", "90"),
        ("0 . 5 INV cos", "60"),
        ("1 INV tan", "45"),
        ("0 HYP sin", "0"),
        ("1 HYP cos", "1.54308063481524"),
        ("0 INV HYP tan", "0"),
        ("5 x^2", "25"),
        ("2 5 INV x^2", "5"),
        ("3 x^3", "27"),
        ("2 7 INV x^3", "3"),
        ("8 neg INV x^3", "-2"),
        ("2 7 INV x^y 3 =", "3"),                    # cube root via Inv x^y
        ("1 0 0 log", "2"),
        ("2 INV log", "100"),
        ("1 ln", "0"),
        ("1 INV ln", "2.7182818284590452353602874713527"),
        ("0 ln", "Invalid input"),
        ("5 n!", "120"),
        ("0 n!", "1"),
        ("2 0 n!", "2432902008176640000"),
        ("pi", "3.1415926535897932384626433832795"),
    ]
    for keys, want in cases:
        got = run(keys)
        assert got == want, f"standard {keys!r}: {got!r} != {want!r}"
    for keys, want in sci:
        got = run(keys, "scientific")
        assert got == want, f"scientific {keys!r}: {got!r} != {want!r}"
    assert run("1 0 0 sin", "scientific", angle="grad") == "1"
    assert run("pi / 2 = sin", "scientific", angle="rad") == "1"
    # Inv and Hyp apply once, then untick
    e = Engine()
    e.set_mode("scientific")
    e.inv = True
    e.press("1")
    e.press("sin")
    assert not e.inv and e.display() == "90"
    # number bases
    e = Engine()
    e.set_mode("scientific")
    for k in "2 5 5".split():
        e.press(k)
    e.set_base("hex")
    assert e.display() == "FF"
    e.set_base("bin")
    assert e.display() == "11111111"
    e.set_base("oct")
    assert e.display() == "377"
    e.set_base("dec")
    assert e.display() == "255"
    for keys, base, want in [("F F And 0 F =", "hex", "F"), ("A Or 5 =", "hex", "F"), ("F Xor A =", "hex", "5"),
                             ("0 Not", "hex", "FFFFFFFFFFFFFFFF"), ("0 Not", "dec", "-1"),
                             ("1 Lsh 4 =", "hex", "10"), ("1 1 1 Lsh 1 =", "bin", "1110"),
                             ("1 0 / 3 =", "hex", "5"), ("7 / 2 =", "oct", "3"), ("1 Mod 0 =", "hex", "Cannot divide by zero"),
                             ("F F + 1 =", "hex", "100"), ("1 neg", "hex", "FFFFFFFFFFFFFFFF")]:
        got = run(keys, "scientific", base=base)
        assert got == want, f"{base} {keys!r}: {got!r} != {want!r}"
    e = Engine()
    e.set_mode("scientific")
    e.set_base("bin")
    e.press("2")                                     # not a binary digit: ignored
    e.press(".")
    assert e.display() == "0"
    # decimal with fractions becomes an integer in hex
    e = Engine()
    e.set_mode("scientific")
    for k in "1 2 . 7".split():
        e.press(k)
    e.set_base("hex")
    assert e.display() == "C"
    e.press("C")                                     # in hex, C is a digit (a new entry after the switch)...
    e.press("C")
    assert e.display() == "CC"
    e.press("clear")                                 # ...and clear still clears
    assert e.display() == "0"
    # parentheses counter
    e = Engine()
    e.set_mode("scientific")
    for k in "( 2 + ( 3".split():
        e.press(k)
    assert e.parens == 2
    assert group("1234567.25") == "1,234,567.25" and group("-1000") == "-1,000" and group("12") == "12"
    assert group("FFFFFF", "hex") == "FF FFFF" and group("11110000", "bin") == "1111 0000"
    assert group("Cannot divide by zero") == "Cannot divide by zero" and group("1e+600") == "1e+600"
    # paste
    e = Engine()
    assert e.paste(" 3.25\n") == "3.25"
    print(f"calc selftest ok: {len(cases)} standard, {len(sci)} scientific, plus bases and modes")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
