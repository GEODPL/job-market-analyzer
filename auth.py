"""Λογαριασμοί χρηστών με username + κωδικό, αποθηκευμένοι στον πίνακα `app_users` του Supabase.

Οι κωδικοί δεν αποθηκεύονται ποτέ ως κείμενο: κρατάμε PBKDF2-HMAC-SHA256 hash με τυχαίο salt ανά χρήστη.
Η εφαρμογή μιλά στον πίνακα από τον server του Streamlit (τα secrets δεν φτάνουν ποτέ στον browser).
"""
import hashlib
import hmac
import re
import secrets

TABLE = "app_users"
ITERATIONS = 200_000
USERNAME_RE = re.compile(r"[a-z0-9_.-]{3,30}")
MIN_PASSWORD = 8
MAX_PASSWORD = 128


class AuthError(Exception):
    """Σφάλμα με μήνυμα που μπορεί να εμφανιστεί αυτούσιο στον χρήστη."""


def normalize_username(username: str) -> str:
    return (username or "").strip().lower()


def hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS).hex()


def _db_error(e: Exception) -> AuthError:
    low = str(e).lower()
    code = str(getattr(e, "code", "") or "")
    if code == "23505" or "duplicate" in low or "unique" in low:
        return AuthError("Αυτό το username χρησιμοποιείται ήδη. Διάλεξε άλλο.")
    if code in ("PGRST205", "42P01") or "does not exist" in low or "could not find the table" in low:
        return AuthError("Ο πίνακας app_users δεν υπάρχει ακόμα στο Supabase. Τρέξε το supabase_users.sql.")
    if code == "42501" or "row-level security" in low or "permission denied" in low:
        return AuthError("Το Supabase key δεν έχει δικαίωμα στον πίνακα app_users. Βάλε το service_role key στο SUPABASE_SERVICE_KEY.")
    return AuthError(f"Σφάλμα βάσης δεδομένων: {e}")


def _find(client, username: str):
    res = client.table(TABLE).select("username,password_hash,salt").eq("username", username).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def register_user(client, username: str, password: str) -> str:
    """Δημιουργεί λογαριασμό. Επιστρέφει το κανονικοποιημένο username ή σηκώνει AuthError."""
    username = normalize_username(username)
    if not USERNAME_RE.fullmatch(username):
        raise AuthError("Το username θέλει 3-30 χαρακτήρες: μικρά λατινικά γράμματα, αριθμούς, . _ -")
    if len(password or "") < MIN_PASSWORD:
        raise AuthError(f"Ο κωδικός πρέπει να έχει τουλάχιστον {MIN_PASSWORD} χαρακτήρες.")
    if len(password) > MAX_PASSWORD:
        raise AuthError(f"Ο κωδικός μπορεί να έχει έως {MAX_PASSWORD} χαρακτήρες.")

    try:
        if _find(client, username):
            raise AuthError("Αυτό το username χρησιμοποιείται ήδη. Διάλεξε άλλο.")
        salt = secrets.token_bytes(16)
        client.table(TABLE).insert({
            "username": username,
            "password_hash": hash_password(password, salt),
            "salt": salt.hex(),
        }).execute()
    except AuthError:
        raise
    except Exception as e:
        raise _db_error(e) from e
    return username


def verify_user(client, username: str, password: str):
    """Επιστρέφει το κανονικοποιημένο username αν τα στοιχεία είναι σωστά, αλλιώς None."""
    username = normalize_username(username)
    if not username or not password or len(password) > MAX_PASSWORD:
        return None
    try:
        row = _find(client, username)
    except Exception as e:
        raise _db_error(e) from e

    # Κάνουμε πάντα το hash (και όταν ο χρήστης δεν υπάρχει) ώστε ο χρόνος απόκρισης να μην δείχνει ποια usernames υπάρχουν.
    salt = bytes.fromhex(row["salt"]) if row else b"\x00" * 16
    candidate = hash_password(password, salt)
    expected = row["password_hash"] if row else "0" * len(candidate)
    ok = hmac.compare_digest(candidate, expected)
    return username if (row and ok) else None
