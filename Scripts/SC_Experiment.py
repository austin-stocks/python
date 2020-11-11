import pandas as pd
import matplotlib.pyplot as plt

dc = pd.DataFrame({'A' : [1, 2, 3, 4],'B' : [4, 3, 2, 1],'C' : [3, 4, 2, 2]})

dc1 = pd.Dateframe()

plt.plot(dc)
plt.legend(dc.columns)
dcsummary = pd.DataFrame([dc.mean(), dc.sum()],index=['Mean','Total'])

plt.table(cellText=dcsummary.values,colWidths = [0.25]*len(dc.columns),
          rowLabels=dcsummary.index,
          colLabels=dcsummary.columns,
          cellLoc = 'center', rowLoc = 'center',
          loc='top')
fig = plt.gcf()

plt.show()