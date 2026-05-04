import json
import requests
from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from urllib.parse import quote

app = Flask(__name__)

class VideoExtractor:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"
        # Hex keys for AES-128-CBC
        self.key_hex = "6b69656d7469656e6d75613931316361"
        self.iv_hex = "313233343536373839306f6975797472"
        
    def get_video_id(self, title):
        """Search for the video and return the first ID found"""
        try:
            encoded_title = quote(title)
            # FIXED: Removed 'curl' prefix and quote from URL string
            worker_url = f"https://netout.pages.dev/api/rpm?search={encoded_title}"
            
            response = requests.get(worker_url, headers={"User-Agent": self.user_agent})
            
            if response.status_code == 200:
                data = response.json()
                # FIXED: Logic to match your provided JSON structure (data is a list)
                if data.get('data') and len(data['data']) > 0:
                    return data['data'][0]['id']
            return None
        except Exception as e:
            print(f"Error getting video ID: {e}")
            return None
    
    def extract_m3u8(self, video_id):
        """Fetches and decrypts the stream URL"""
        try:
            domain = "https://watchout.rpmvid.com"
            headers = {
                "Referer": f"{domain}/",
                "User-Agent": self.user_agent
            }

            # FIXED: Changed variable 'id' to 'video_id' to match function argument
            api_url = f'{domain}/api/v1/video?id={video_id}'
            response = requests.get(api_url, headers=headers)
            
            if response.status_code != 200:
                return {'success': False, 'error': f'API failed: {response.status_code}'}
            
            # Assuming the API returns a raw hex string for decryption
            encrypted_data = response.text.strip().strip('"')

            # CRYPTO DECRYPTION
            key = bytes.fromhex(self.key_hex)
            iv = bytes.fromhex(self.iv_hex)
            ciphertext = bytes.fromhex(encrypted_data)

            cipher = AES.new(key, AES.MODE_CBC, iv)
            plaintext = cipher.decrypt(ciphertext)
            
            # PKCS7 Unpadding
            decrypted_data = unpad(plaintext, AES.block_size)
            stream_info = json.loads(decrypted_data)
            
            return {
                'success': True,
                'm3u8_url': stream_info.get('source'),
                'title': stream_info.get('title'),
                'id': video_id
            }
                
        except Exception as e:
            return {'success': False, 'error': f"Decryption/Extraction failed: {str(e)}"}

extractor = VideoExtractor()

@app.route('/api/get-stream', methods=['GET'])
def get_stream():
    title = request.args.get('title')
    if not title:
        return jsonify({'success': False, 'error': 'Title parameter required'})
    
    # FIXED: Method name was mismatched (get_id vs get_video_id)
    video_id = extractor.get_video_id(title)
    if not video_id:
        return jsonify({'success': False, 'error': 'No video found for this title'})
    
    result = extractor.extract_m3u8(video_id)
    return jsonify(result)

@app.route('/api/direct-extract', methods=['GET'])
def direct_extract():
    video_id = request.args.get('video_id')
    if not video_id:
        return jsonify({'success': False, 'error': 'Video ID parameter required'})
    
    result = extractor.extract_m3u8(video_id)
    return jsonify(result)

@app.route('/')
def home():
    return jsonify({
        'message': 'Video Extractor API - Active',
        'endpoints': {
            '/api/get-stream?title=name': 'Search and extract',
            '/api/direct-extract?video_id=id': 'Extract by ID'
        }
    })

if __name__ == '__main__':
    # Using port 5000 by default
    app.run(debug=True, port=5000)
