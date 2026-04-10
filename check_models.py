import google.generativeai as genai

# Thay API Key của bạn vào đây
genai.configure(api_key="AIzaSyCjdD6uKle7Nf65TYL73B0pXcPPMPHN10w")

for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)