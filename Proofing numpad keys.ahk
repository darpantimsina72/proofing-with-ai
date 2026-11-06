#Requires AutoHotkey v2.0
#SingleInstance Force

; Number pad 1-9 -> Ctrl+Shift+1-9, for the Book proofing tab of Proofing with AI:
;   1 = End                 2 = Page Down          3 = select the sentence's next word
;   4 = Home                5 = Page Up            6 = Right word (again = grow by a word)
;   7 = previous page       8 = next page          9 = whole sentence as Real Meaning
;   0 = stop playback (Play carries on from the same sentence). It sends the
;       Pause key, not Ctrl+Shift+0: Windows swallows the 0 of Ctrl+Shift+0
;       here, so the page never sees it.
;
; Only while the Proofing with AI browser window is in front, so the number
; pad types digits as usual everywhere else. Num Lock must be ON: with it off
; the keys are End / Page Down / ... and keep doing what they did before.
; While this runs, Numpad 0 no longer works as the page's second space bar.

#HotIf WinActive("Proofing with AI")
Numpad0::Send "{Pause}"
Numpad1::Send "^+1"
Numpad2::Send "^+2"
Numpad3::Send "^+3"
Numpad4::Send "^+4"
Numpad5::Send "^+5"
Numpad6::Send "^+6"
Numpad7::Send "^+7"
Numpad8::Send "^+8"
Numpad9::Send "^+9"
#HotIf
