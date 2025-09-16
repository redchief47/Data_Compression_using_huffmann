from flask import Flask, request, send_file, render_template_string
import os, heapq, json
from collections import defaultdict
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import PyPDF2

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
COMPRESSED_FOLDER = 'compressed'
DECOMPRESSED_FOLDER = 'decompressed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COMPRESSED_FOLDER, exist_ok=True)
os.makedirs(DECOMPRESSED_FOLDER, exist_ok=True)

class Node:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq

def build_huffman_tree(text):
    freq = defaultdict(int)
    for ch in text:
        freq[ch] += 1
    heap = [Node(char, f) for char, f in freq.items()]
    heapq.heapify(heap)
    while len(heap) > 1:
        n1 = heapq.heappop(heap)
        n2 = heapq.heappop(heap)
        merged = Node(None, n1.freq + n2.freq)
        merged.left = n1
        merged.right = n2
        heapq.heappush(heap, merged)
    return heap[0]

def build_codes(root, code='', codes={}):
    if not root:
        return
    if root.char:
        codes[root.char] = code
    build_codes(root.left, code + '0', codes)
    build_codes(root.right, code + '1', codes)
    return codes

def compress_text(text):
    root = build_huffman_tree(text)
    codes = build_codes(root)
    encoded = ''.join(codes[ch] for ch in text)
    return encoded, codes

def decompress_text(encoded, codes):
    rev_codes = {v: k for k, v in codes.items()}
    current = ''
    decoded = ''
    for bit in encoded:
        current += bit
        if current in rev_codes:
            decoded += rev_codes[current]
            current = ''
    return decoded

def extract_text(file_path):
    if file_path.endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    elif file_path.endswith('.pdf'):
        reader = PyPDF2.PdfReader(file_path)
        return ''.join(page.extract_text() for page in reader.pages if page.extract_text())
    elif file_path.endswith(('.png', '.jpg', '.jpeg')):
        img = Image.open(file_path)
        return pytesseract.image_to_string(img)
    return ''

@app.route('/compress', methods=['POST'])
def compress():
    file = request.files['file']
    compression_ratio = int(request.form.get('compressionRatio'))
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    text = extract_text(filepath)
    if not text:
        return 'No text found in file', 400

    encoded, codes = compress_text(text)
    output_path = os.path.join(COMPRESSED_FOLDER, filename + '.huff')
    with open(output_path, 'w') as f:
        json.dump({'codes': codes, 'encoded': encoded}, f)

    return send_file(output_path, as_attachment=True)

@app.route('/decompress', methods=['POST'])
def decompress():
    file = request.files['file']
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    with open(filepath, 'r') as f:
        data = json.load(f)
        codes = data['codes']
        encoded = data['encoded']

    decoded = decompress_text(encoded, codes)
    output_path = os.path.join(DECOMPRESSED_FOLDER, filename + '.txt')
    with open(output_path, 'w') as f:
        f.write(decoded)

    return send_file(output_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)