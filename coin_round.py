from decimal import Decimal, ROUND_HALF_DOWN

places = 8
def roundCoin(num):
	x = num.quantize(Decimal('0.00000001'), rounding = ROUND_HALF_DOWN)
	return x