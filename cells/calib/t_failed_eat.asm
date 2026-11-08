; Calibration cell T: does an action that has no effect earn the +1 that resting does?   Written with AI help.
; Always eats UP.  In the Sandbox the lone cell has nothing above it (empty square or wall), so every eat does nothing.
; Rules: "Resting is the only income" -> energy should stay at the start value (10) all match, pop 1.
; If failed actions counted as rest, energy would climb to the cap (50).

	mov	al, ACT_EAT + DIR_UP
	ret
