import base64

# Read the logo file and convert to base64
with open('static/img/Loan Aid.png', 'rb') as image_file:
    encoded_string = base64.b64encode(image_file.read()).decode()

# Create the data URL
data_url = f"data:image/png;base64,{encoded_string}"

# Print the first 100 characters to verify
print("Base64 encoded logo (first 100 chars):")
print(data_url[:100] + "...")
print("\nFull data URL length:", len(data_url))
print("Logo successfully converted to base64!")
