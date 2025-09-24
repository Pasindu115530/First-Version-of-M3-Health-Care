"""
Notification utilities with fast Windows toast support and cross-platform fallback.
"""
import sys
import platform

_win_toaster = None
_plyer = None

def _ensure_backends():
    global _win_toaster, _plyer
    if platform.system() == 'Windows' and _win_toaster is None:
        try:
            from win10toast import ToastNotifier  # type: ignore
            _win_toaster = ToastNotifier()
        except Exception:
            _win_toaster = None
    if _plyer is None:
        try:
            from plyer import notification as plyer_notification  # type: ignore
            _plyer = plyer_notification
        except Exception:
            _plyer = None

def fast_notify(title: str, message: str, duration: int = 5, app_id: str = "Safe Warner"):
    """Send a desktop notification quickly. Returns True if delivered, else False."""
    _ensure_backends()
    # Prefer Windows toast for speed/reliability in packaged .exe
    if platform.system() == 'Windows' and _win_toaster is not None:
        try:
            _win_toaster.show_toast(title, message, duration=duration, threaded=True)
            return True
        except Exception:
            pass
    # Fallback to plyer if available
    if _plyer is not None:
        try:
            _plyer.notify(title=title, message=message, timeout=duration, app_name=app_id)
            return True
        except Exception:
            pass
    return False


