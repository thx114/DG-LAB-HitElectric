row_size = width * 4
for y in range(4):
    start = y * row_size
    for i in range(start, start + row_size, 4):
        data[i] = 255
        data[i+1] = 0
        data[i+2] = 255
for y in range(height - 4, height):
    start = y * row_size
    for i in range(start, start + row_size, 4):
        data[i] = 255
        data[i+1] = 0
        data[i+2] = 255


        