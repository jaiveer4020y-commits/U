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
        # AES Keys for CBC Decryption
        self.key_hex = "6b69656d7469656e6d75613931316361"
        self.iv_hex = "313233343536373839306f6975797472"
        
    def get_video_id(self, title):
        """Searches the worker API for a file ID based on the title"""
        try:
            encoded_title = quote(title)
            worker_url = f"https://netout.pages.dev/api/rpm?search={encoded_title}"
            
            print(f"[*] Searching for: {title}")
            response = requests.get(worker_url, headers={"User-Agent": self.user_agent}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Accessing the first item in the 'data' list from your JSON structure
                if data.get('data') and len(data['data']) > 0:
                    video_id = data['data'][0]['id']
                    print(f"[*] Found Video ID: {video_id}")
                    return video_id
                else:
                    print(f"[!] No results found in the 'data' list for: {title}")
            else:
                print(f"[!] Search API returned status: {response.status_code}")
            return None
        except Exception as e:
            print(f"[!] Error in get_video_id: {e}")
            return None
    
    def extract_m3u8(self, video_id):
        """Fetches encrypted stream data and decrypts it using AES-128-CBC"""
        try:
            domain = "https://watchout.rpmvid.com"
            headers = {
                "Referer": f"{domain}/",
                "User-Agent": self.user_agent
            }

            api_url = f'{domain}/api/v1/video?id={video_id}'
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return {'success': False, 'error': f'API failed: {response.status_code}'}
            
            # Remove any wrapping quotes from the raw response text
            encrypted_data = response.text.strip().strip('"')

            # Prepare Decryption
            key = bytes.fromhex(self.key_hex)
            iv = bytes.fromhex(self.iv_hex)
            ciphertext = bytes.fromhex(encrypted_data)

            cipher = AES.new(key, AES.MODE_CBC, iv)
            plaintext = cipher.decrypt(ciphertext)
            
            # Unpad PKCS7 data
            decrypted_data = unpad(plaintext, AES.block_size)
            stream_info = json.loads(decrypted_data)

            return {
                'success': True,
                'm3u8_url': stream_info.get('source'),
                'title': stream_info.get('title'),
                'id': video_id,
                'headers_required': {
                    "Referer": domain,
                    "User-Agent": self.user_agent
                }
            }
                
        except Exception as e:
            print(f"[!] Extraction Error: {e}")
            return {'success': False, 'error': str(e)}

# Initialize Extractor
extractor = VideoExtractor()

@app.route('/api/get-stream', methods=['GET'])
def get_stream():
    title = request.args.get('title')
    if not title:
        return jsonify({'success': False, 'error': 'Title parameter required'})
    
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
        'status': 'Online',
        'message': 'Video Extractor API',
        'endpoints': {
            '/api/get-stream?title=TITLE_HERE': 'Search and get stream',
            '/api/direct-extract?video_id=ID_HERE': 'Direct extraction'
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
