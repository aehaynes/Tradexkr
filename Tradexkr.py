import sys
import btceapi as ba
import time
import sqlite3
from coin_round import roundCoin as rc
from decimal import Decimal

def getBalances():
	info = t.getInfo()
	balances = {}
	for currency in ba.all_currencies:
		balance = getattr(info, "balance_" + currency)
		balances[currency] = balance
	return balances
def getBalance(currency):
	balances = getBalances()
	try:
		return balances[currency]
	except KeyError:
		print "Invalid currency code!"

pairs = ('ltc_btc', 'nmc_btc', 'nvc_btc', 'trc_btc', 'ppc_btc', 'ftc_btc')
def getBids():
	prices = []

	for c in pairs:
		depth = ba.getDepth(c)
		price = depth[1][0][0]
		print c[:3] + " bid: " + str(price)
		prices.append((c[:3], price))
	return prices
def getAsks():
	prices = []

	for c in pairs:
		depth = ba.getDepth(c)
		price = depth[0][0][0]
		print c[:3] + " ask: " + str(price)
		prices.append((c[:3], price))
	return prices

def getSpendableBalance():
	c.execute('SELECT * FROM base_balance')
	spendableBalance = c.fetchone()[1]
	return Decimal(spendableBalance)

def diversifyCrypto():
	print "Diversifying coins. Getting rates..."
	base_currency = 'btc'
	base_amount = getSpendableBalance()
	prices = getAsks()
	for_each_coin = rc(base_amount / len(pairs))
	print "%s BTC on each coin" % (for_each_coin)

	buys = []
	for price in prices:
		amount = rc(for_each_coin / price[1])
		fee = rc(amount * Decimal(0.002))
		amount = rc(amount - fee)
		print "Can buy %s %s with fee of %s" % (amount, price[0], fee)
		#symbol, price, amount
		buys.append((price[0], price[1], amount))

	for buy in buys:
		pair = str(buy[0],) + "_btc"
		symbol = unicode(buy[0])
		price = unicode(buy[1])
		amount = unicode(rc(buy[2] - (buy[2] * Decimal(0.002))))
		values = (buy[0],)
		c.execute('SELECT EXISTS(SELECT * FROM balances WHERE currency=?)', values)
		result = c.fetchone()
		if result[0]:
			values = (amount, price, symbol)
			c.execute('UPDATE balances SET amount=?, bought_price=? WHERE currency=?', values)
			sql.commit()
		else:
			values = (symbol, amount, price)
			c.execute('INSERT INTO balances (currency, amount, bought_price) VALUES (?, ?, ?)', values)
			sql.commit()
		#pair, type, price, amount
		trade = t.trade(pair, 'buy', buy[1], buy[2])

		print "bought %s %s at %s" % (amount, symbol, price)

	pending_orders = True
	print "awaiting completion on all trades... this can take a while"
	while pending_orders:
		try:
			orderlist = t.orderList(active=True)
		except Exception:
			pending_orders = False

	print "updating balance..."
	c.execute('SELECT * FROM base_balance WHERE rowid=1')
	result = c.fetchone()
	total, spendable = result
	total = total - spendable
	spendable = 0
	values = (total, spendable)
	c.execute('UPDATE base_balance SET total=?, spendable=? WHERE rowid=1', values)
	print "balances updated"


def verifyNotStupid(balance):
	if balance > 4:
		print "This program is very new, and shouldn't be trusted with too much BTC."
		print "How much do you want to use (less than 4)?"
		amount = Decimal(raw_input())
		if amount < 4:
			return amount
		else:
			print "You're stubborn"
			sys.exit(1)
	else:
		return balance
def firstRun():
	print "first run!"
	print "using btc as base"
	btcBalance = unicode(getBalance('btc'))
	print "Current BTC balance is %s" % (btcBalance)
	btcBalance = verifyNotStupid()
	print "Inserting %s BTC as spendable in DB" % (btcBalance)
	c.execute('SELECT EXISTS(SELECT * FROM base_balance)')
	result = c.fetchone()
	if not result[0]:
		c.execute('INSERT INTO base_balance (total, spendable) VALUES (?, ?)', (btcBalance, btcBalance))
	else:
		c.execute('UPDATE base_balance SET total=?, spendable=? WHERE rowid=1', (btcBalance, btcBalance))
	sql.commit()
	diversifyCrypto()
	status = ('has_run',)
	c.execute('INSERT INTO status (key) VALUES (?)', status)
	sql.commit()

def groove():
	while 1:
		run = True
		asks = getBids()
		spendable = getSpendableBalance()
		if run:
			for price in asks:
				values = (price[0],)
				c.execute('SELECT * FROM balances WHERE currency=?', values)
				result = c.fetchone()
				total_spent = result[1] * result[2]
				amount_if_sold = price[1] * Decimal(result[1])
				profit_requred = (total_spent * 0.018) + total_spent
				print "bought %s at %s" % (price[0], result[2])
				if amount_if_sold > profit_requred:
					print "You made a profit of %s on %s" % (rc(amount_if_sold - Decimal(profit_requred)), price[0])
					to_sell = rc(Decimal(result[1]) - Decimal(result[1] * 0.002))
					pair = price[0] + "_btc"
					#pair, type, price, amount
					trade = t.trade(pair, 'sell', price[1], to_sell)
					c.execute('UPDATE balances SET amount=0, bought_price=0 WHERE currency=?', values)
					sql.commit()
					total_btc_gained = price[1] * to_sell
					print "sold all %s for a total of %s BTC" % (result[0], total_btc_gained)
					spendable = total_btc_gained
					values = (unicode(total_btc_gained), unicode(spendable))
					c.execute('UPDATE base_balance SET total=?, spendable=? WHERE rowid=1', values)
					sql.commit()
				else:
					print "no profit"
				
				
			time.sleep(80)
		else:
			print "re-diverse"
			diversifyCrypto()
			groove()



if __name__ == "__main__":
	if len(sys.argv) < 1:
		print "Usage: Tradexkr.py <keyfile>"
		sys.exit(1)
	key = sys.argv[1]
	handler = ba.KeyHandler(key)
	t = ba.TradeAPI(key, handler)

	sql = sqlite3.connect('trades.db')

	c = sql.cursor()
	#handle the first run
	def initialize():
		try:
			c.execute('SELECT * from status WHERE key="has_run"')
			has_run = c.fetchone()
			if has_run:
				print "not first run"
				groove()
			else:
				firstRun()

		except sqlite3.OperationalError:
			c.execute('''CREATE TABLE status (key text)''')
			c.execute('''CREATE TABLE balances (currency text, amount real, bought_price real)''')
			c.execute('''CREATE TABLE base_balance (total real, spendable real)''')
			sql.commit()
			initialize()
	initialize()
