import numpy as np
import pandas as pd

mtns = pd.DataFrame([
    {'name': 'Mount Everest',
        'height (m)': 8848,
        'summited': 1953,
        'mountain range': 'Mahalangur Himalaya'},
    {'name': 'K2',
        'height (m)': 8611,
        'summited': 1954,
        'mountain range': 'Baltoro Karakoram'},
    {'name': 'Kangchenjunga',
        'height (m)': 8586,
        'summited': 1955,
        'mountain range': 'Kangchenjunga Himalaya'},
    {'name': 'Lhotse',
        'height (m)': 8516,
        'summited': 1956,
        'mountain range': 'Mahalangur Himalaya'},
])
mtns.set_index('name', inplace=True)
print (1)
print(mtns)
print(2)
print(mtns.loc[:, 'height (m)'])
print(4)
print(mtns.loc[:, 'height (m)'].values)
print(5)
print(mtns.loc[:, 'mountain range'])
print(6)
print(mtns.loc['K2', :])
print(7)
print(mtns.loc['K2', 'mountain range'])
print(8)
print(mtns.loc[:, 'height (m)': 'summited'])
print(9)
print(mtns.loc[:, ['height (m)', 'summited']])
print(10)
print(mtns.loc[mtns.loc[:, 'summited'] > 1954, :])
print(11)
print(mtns.iloc[0, :])
print(12)
print(mtns.iloc[:, 2])
print(13)
print(mtns.iloc[0, 2])
print(14)
print(mtns.iloc[[1, 3], :])
print(15)
print(mtns.iloc[:, 0:2])
print(16)
print(mtns.iloc[:, 0:2].loc['K2', :])
print(17)
print(mtns.iloc[:, 0].loc['K2', :])
print(18)
