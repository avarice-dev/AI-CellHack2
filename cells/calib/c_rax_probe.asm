; Calibration cell C: is rax zero at entry?   Written with AI help.
; Run in the Sandbox (paste this whole file; no org/bits/section/%include needed).
;
; rax == 0 -> test / jnz (not taken) / mov al,ACT_REST / ret       = 4 instructions, rests
; rax != 0 -> test / jnz (taken) / mov al,0xFF / ret               = 4 instructions, returns 0xFF,
;             which is not a valid action: a bad_action fault in the match page's fault log.
; What to read:
;   fault log empty            -> rax was 0 at entry on every call (so `mov al,x` alone is safe and
;                                 the upper bytes of rax never matter; the docs already say only al is read)
;   bad_action lines in the log -> rax is NOT zeroed at entry; send a few lines (tick, position, rip).
;   average 4 -> taken jumps count (both paths are 4); an average between 3 and 4 with faults present
;                means taken jumps are not counted (the fault path is then 3).
; If every call faults the colony never acts and just sits at 10 energy: that itself is the answer.

	test	rax, rax
	jnz	bad
	mov	al, ACT_REST
	ret
bad:
	mov	al, 0xFF
	ret
