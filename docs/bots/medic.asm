;
; medic
;
; when rich, feeds the friend above it, otherwise splits when fat, otherwise rests.
;

	; are we rich? if so, feed our neighbors, otherwise just rest or grow.
	cmp		rsi, 15
	jb		grow

	; is there a friend above me?
	lea		r8, [rdi + VIEW_CELLS]
	mov		al, BYTE [r8 + VIEW_UP]
	cmp		al, CELL_FRIEND
	jne		grow

	; feed cell above me
	mov		al, ACT_FEED
	add		al, DIR_UP
	ret

grow:

	; do we have enough energy to grow?
	cmp		rsi, 6
	jb		rest

	; get random direction
	mov		cl, BYTE [rdi + VIEW_RAND]
	and		cl, ACT_DIR_MASK
	; al = ACT_SPLIT + dir
	mov		al, ACT_SPLIT
	add		al, cl
	ret

rest:
	mov		al, ACT_REST
	ret