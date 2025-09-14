text = "complex loops require careful design"
word_count = {}

for word in text.split():
    word = word.lower()
    for char in word:
        if char.isalpha():
            word_count[char] = word_count.get(char, 0) + 1

print(word_count)
