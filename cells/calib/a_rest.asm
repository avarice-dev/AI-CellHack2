; Calibration cell A: does `ret` count as an instruction?   Written with AI help.
; Run in the Sandbox (paste this whole file; no org/bits/section/%include needed).
;
; Executes exactly: mov al,ACT_REST / ret
; Match page "average instructions per call" (and max):
;   2  -> every instruction counts, including ret          (our assumed convention)
;   1  -> ret is not counted
;   anything else -> the engine counts something else (entry/exit overhead?); send the number.
; Expected fault log: empty.

	mov	al, ACT_REST
	ret
