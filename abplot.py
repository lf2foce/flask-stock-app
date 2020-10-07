import pandas as pd
df = pd.read_csv('all_stocks.csv')

print(df.loc[ (df['Ticker'] == 'VNM') & (df['Date'] == '2020-10-07')].iloc[0]['Adj_Close'])



