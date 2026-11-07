;
; walker
;
; splits when it is fat, otherwise randomly decides between moving or resting.
;

	; do we have enough energy to split? if not, just wander

	cmp		rsi, 6
	jb		wander

	; if so, choose a random direction and split
	mov		cl, BYTE [rdi + VIEW_RAND]
	and		cl, ACT_DIR_MASK
	; al = ACT_SPLIT + dir
	mov		al, ACT_SPLIT
	add		al, cl
	ret

wander:

	; 50/50 chance of resting or moving in a random direction
	mov		cl, BYTE [rdi + VIEW_RAND]
	test	cl, 0x80
	jz		rest
	; al = ACT_MOVE + dir
	and		cl, ACT_DIR_MASK
	mov		al, ACT_MOVE
	add		al, cl
	ret

rest:
	mov		al, ACT_REST
	ret