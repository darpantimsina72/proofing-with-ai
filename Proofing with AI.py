"""
Proofing with AI — a self-contained app.

    python "Proofing with AI.py"

It opens in your browser. Everything it needs is in this folder; it imports
nothing from any script outside it.

WHY A BROWSER AND NOT A DESKTOP WINDOW
--------------------------------------
Tk re-shapes the text around the caret. Put the caret in a Telugu word and
the glyphs around it are redrawn — measured at 519 pixels changing at full
contrast even with the caret on a correct character boundary. No font and no
caret setting changes it; it is how the Tk text widget is built. A browser
shapes the whole line with HarfBuzz and paints the caret on top, so the text
is never disturbed: measured zero re-layout at every caret position across a
word, mid-cluster included.

WHAT GOES IN THIS FOLDER
------------------------
    Proofing with AI.py        this launcher
    server.py                  the local web server and the API
    review_core.py             contracts, parsing, matching, session state
    gemini_client.py           the three Gemini auth paths
    index.html                 the user interface
    Detection_Prompt.txt       what to flag
    Get_Suggestions_Prompt.txt how to rewrite it
    one key file               openaiapi.txt (the default), geminiapi.txt or
                               vertex_key.json

REQUIREMENTS
------------
Python 3.9+ and nothing else, if you use openaiapi.txt (the gateway).
The API and JSON modes additionally need:  pip install google-genai
"""

import os
import signal
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LOG_PATH = os.path.join(HERE, "logs", "app.log")


def show_startup_error(text):
    """A message box with `text` and where the full log is — the only way
    a failure can reach anyone when the app runs without a window."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Proofing with AI could not start",
                             text.strip()[-1500:] + f"\n\n(Full log: {LOG_PATH})")
        root.destroy()
    except Exception:
        pass


# pythonw (Proofing with AI.bat on Windows) gives a program no stdout at
# all. Set up the log before anything else can fail, so a broken import
# shows in a message box rather than nowhere.
NO_WINDOW = sys.stdout is None
if NO_WINDOW:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    sys.stdout = sys.stderr = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
    print(f"\n----- {time.strftime('%Y-%m-%dT%H:%M:%S')} started without a window")

    def _crash(kind, exc, tb):
        import traceback
        text = "".join(traceback.format_exception(kind, exc, tb))
        print(text)
        show_startup_error(text)
    sys.excepthook = _crash

import gemini_client                                            # noqa: E402
import server                                                   # noqa: E402

# The gateway's base url (Open AI Api mode, openaiapi.txt). Change it here.
# May be written with or without a trailing /v1.
BASE_URL = "https://offeringschat.isha.in/"
gemini_client.OPENROUTER_BASE_URL = BASE_URL
gemini_client.OPENROUTER_URL = gemini_client._openrouter_endpoint(BASE_URL)

# The prompts live in Prompts/<Language>/ (see Prompts/README.md); the
# template folder is what every language is made from, so it is the one
# that has to be here.
NEEDED = ("index.html", "server.py", "review_core.py", "gemini_client.py",
          "sync_helper.py", "tts.py", "_voices_literal.py", "house_style.py",
          os.path.join("Prompts", "_template", "Detection_Prompt.txt"),
          os.path.join("Prompts", "_template", "Get_Suggestions_Prompt.txt"),
          os.path.join("Prompts", "_template",
                       "Detection_and_Suggestions_Prompt.txt"),
          os.path.join("Prompts", "_template",
                       "Custom_Text_Translation_Prompt.txt"))


def main():
    print("=" * 62)
    print(" Proofing with AI")
    print("=" * 62)

    missing = [f for f in NEEDED if not os.path.exists(os.path.join(HERE, f))]
    if missing:
        print("\nThese files are missing from this folder:")
        for m in missing:
            print(f"   {m}")
        print(f"\nFolder: {HERE}")
        return 1

    modes = gemini_client.available_modes()
    if not modes:
        # no key yet (a first start, or a copy of the project): the app opens anyway, and the keys are typed into
        # the ACCESS KEYS panel under Gemini access
        print("\nNo Gemini key yet - the app opens anyway: type your keys in the ACCESS KEYS panel (under Gemini access).")
        print("(openaiapi.txt / the gateway needs no extra Python package; the other two need:  pip install google-genai)")

    # A mode can be forced on the command line:  python "Proofing with AI.py" JSON
    wanted = sys.argv[1].upper() if len(sys.argv) > 1 else None
    if wanted and modes and wanted not in modes:
        print(f"\n'{wanted}' has no key here. Available: {', '.join(modes)}")
        return 1
    # Open AI Api (the gateway) is what the app prefers when its key file is
    # there; otherwise the first mode that has a key.
    mode = wanted or (gemini_client.DEFAULT_MODE
                      if (gemini_client.DEFAULT_MODE in modes or not modes) else modes[0])

    srv = server.ProofingServer(mode)
    url = srv.start()

    print(f"\n   folder : {HERE}")
    print(f"   language: {srv.language}  (prompts in Prompts/{srv.language})")
    print(f"   gemini  : {mode}  ({gemini_client.KEY_FILES[mode]})")
    if mode == "OPENROUTER":
        print(f"   gateway : {gemini_client.OPENROUTER_URL}")
    if len(modes) > 1:
        others = [m for m in modes if m != mode]
        print(f"            (also available: {', '.join(others)} — pass one "
              f"as an argument to switch)")
    print(f"   url     : {url}")

    keep_running_when_window_closes(srv)
    srv.open_browser()
    print("\nOpened in your browser.")
    print("If it did not open, paste the url above into one.")
    print("\nLeave this window open while you work.  Ctrl-C to stop.")
    try:
        while True:
            time.sleep(1)
            # Its window was closed: carry on while the page is open, and
            # stop once no tab has reached it for a while.
            if WINDOW_CLOSED and time.time() - srv.last_seen > IDLE_QUIT:
                break
    except KeyboardInterrupt:
        print("\nStopping…")
    srv.stop()
    return 0


# After its window is closed, the app keeps saving for as long as the page
# is open, then stops on its own once no tab has reached it for this long.
IDLE_QUIT = 15 * 60
WINDOW_CLOSED = False


def keep_running_when_window_closes(srv):
    """Closing the window the app was started from (a Terminal window, or
    VS Code's terminal panel) sends it SIGHUP, which would stop it at once
    — and with it every save from the page still open in the browser. So
    the hang-up is caught instead: what the app prints goes nowhere from
    then on (there is no window left to print to), and it keeps serving the
    page. Ctrl-C still stops it. Windows has no SIGHUP; there the page's
    red "app has stopped" bar and its Save my work button are the guard."""
    if not hasattr(signal, "SIGHUP"):
        return

    def on_hangup(signum, frame):
        global WINDOW_CLOSED
        WINDOW_CLOSED = True
        srv.last_seen = time.time()
        devnull = open(os.devnull, "w")
        try:
            os.dup2(devnull.fileno(), 1)
            os.dup2(devnull.fileno(), 2)
        except OSError:
            pass
        sys.stdout = sys.stderr = devnull

    signal.signal(signal.SIGHUP, on_hangup)


def run_without_window():
    """Started without a window (see NO_WINDOW): nothing printed can be
    seen and there is nothing to Ctrl-C. The app stops on its own once no
    tab has reached it for IDLE_QUIT, as after a closed window, and a
    failed start shows the end of the log in a message box."""
    global WINDOW_CLOSED
    WINDOW_CLOSED = True
    rc = main()
    if rc:
        sys.stdout.flush()
        with open(LOG_PATH, "r", encoding="utf-8") as fh:
            show_startup_error(fh.read())
    return rc


if __name__ == "__main__":
    sys.exit(run_without_window() if NO_WINDOW else main())
