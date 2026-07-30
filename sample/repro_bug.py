from mootdx.quotes import Quotes

def test_588000_price():
    q = Quotes()
    # Test the problematic symbol
    symbol = '588000'
    df = q.quotes(symbol=symbol)
    print(f"Symbol: {symbol}")
    print(df)

    # Test a known correct symbol (SH Fund)
    symbol_correct = '510050'
    df_correct = q.quotes(symbol=symbol_correct)
    print(f"\nSymbol: {symbol_correct}")
    print(df_correct)

if __name__ == "__main__":
    test_588000_price()
