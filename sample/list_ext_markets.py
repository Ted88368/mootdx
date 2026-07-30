from mootdx2.quotes import Quotes

client = Quotes.factory(market='ext')
print(client.markets())
