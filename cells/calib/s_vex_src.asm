; Calibration cell S: does the site's VEX vpcmpeqb use its first SOURCE register (correct) or its destination?   Written with AI help.

;   pcmpeqb xmm0, xmm0          -> xmm0 = all ones;  xmm1 = xmm2 = 0
;   vpcmpeqb xmm2, xmm0, xmm1   -> correct: (ones == 0) = 0;   buggy (xmm2 == xmm1): (0 == 0) = all ones
; Both paths 7 insns.  Correct -> rest, no faults.  Buggy -> invalid action 0xFF (bad_action faults).
; RESULT 2026-11-08 (Sandbox 104136): bad_action every call -> the site uses the DESTINATION, like Unicorn.

	pcmpeqb	xmm0, xmm0
	vpcmpeqb xmm2, xmm0, xmm1
	pmovmskb eax, xmm2
	test	eax, eax
	jnz	bad
	mov	al, ACT_REST
	ret
bad:
	mov	al, 0xFF
	ret
