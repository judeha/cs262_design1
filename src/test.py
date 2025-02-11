text = "hello\snfgkdsk`\nthis is my $ content| split here"
encoded = bytes(text, "utf-8")
decoded = encoded.decode("utf-8")
lst = decoded.split("|")
print(lst)