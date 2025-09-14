keys = [False, False, True, False, False, False, False]

K_s = 0
K_w = 1
K_d = 2
K_a = 3


# We printed the 0th value and the 4th value of the array "a"
a = [123, 1, 2, 3, 4]
print(a[0])
print(a[4])

print(K_s)
print()

# Goal: Print the 0th value of the array "keys"
print(keys[0])
print(keys[K_a])

# keys: [False, True, False, False, False]
# K_w = 1
# keys[K_w]     ->  True
if keys[K_w]:
    # move up
    pass
