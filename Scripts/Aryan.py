
import  sys
from yahoo_historical import Fetcher
data = Fetcher("AAPL", [2016,12,25], [2017,1,1])
print(data.get)
print(data.get_historical())

sys.exit(1)

print("")
print("I am planning on learning python and stock investing this summer")

b = 10
a = b + 5
print("b : ", b)
print("a : ", a)

# Aryan learning if statements here
a = 769085
r=857
t=475
i=48576
y=a-t
print(y)
if(y>10000000):
  print(i/r)
else:
  print("hi")
# Done learning if statement - for now


# Learning for loops
for x in range(5):
  print ("Hello Aryan. Printing your name ", x+1 , " time")


for q in range(10000):
  print (q*q)