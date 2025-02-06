import base64

with open("favico.ico", "rb") as img_file:
    b64_icon = base64.b64encode(img_file.read()).decode("utf-8")
print(b64_icon) 