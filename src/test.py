text = "hello\snfgkdsk`\nthis is my $ content| split here"
encoded = bytes(text, "utf-8")
decoded = encoded.decode("utf-8")
lst = decoded.split("|")
print(lst)

# # print the contents of a sqlite3 database
# import sqlite3

# conn = sqlite3.connect("messages.db")
# cursor = conn.cursor()
# cursor.execute("SELECT * FROM messages")
# rows = cursor.fetchall()
# for row in rows:
#     print(row)


emojis = ["🌺","🌸","👩🏼‍❤️‍💋‍👩🏽","👩🏼","💋","👳‍♂️","🏖","🖍"]
print(emojis[0])