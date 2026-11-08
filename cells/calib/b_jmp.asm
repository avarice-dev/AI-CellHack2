; Calibration cell B: does a taken jump count as an instruction?   Written with AI help.
; Run in the Sandbox (paste this whole file; no org/bits/section/%include needed).
;
; Executes exactly: jmp skip / mov al,ACT_REST / ret   (the jmp is always taken)
; Read together with cell A's average (A = 2 under our convention):
;   3  (A = 2) -> taken jumps count                         (our assumed convention)
;   2  (A = 2) -> taken jumps are NOT counted (sim: run.py --order-no-taken-jumps applies)
;   B = A + 1 in general means the jmp counts; B = A means it does not.
; Expected fault log: empty.

	jmp	skip
skip:
	mov	al, ACT_REST
	ret
