import json
import requests
from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from urllib.parse import quote
import os

app = Flask(__name__)

class VideoExtractor:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"
        self.key_hex = "6b69656d7469656e6d75613931316361"
        self.iv_hex = "313233343536373839306f6975797472"
        
    def get_video_id(self, title):
        """Get video ID from HLS worker"""
        try:
            encoded_title = quote(title)
            worker_url = f"https://hlsworker.watchoutofficial2006.workers.dev/?title={encoded_title}"
            
            response = requests.get(worker_url, headers={"User-Agent": self.user_agent})
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 200 and data.get('result', {}).get('files'):
                    return data['result']['files'][0]['file_code']
            return None
        except Exception as e:
            print(f"Error getting video ID: {e}")
            return None
    
    def extract_m3u8(self, video_id):
        """EXACT SAME EXTRACTOR"""
        try:
            domain = "https://watchout.rpmvid.com"
            headers = {
                "Referer": domain,
                "User-Agent": self.user_agent
            }

            api_url = f'{domain}/api/v1/video?id={video_id}'
            response = requests.get(api_url, headers=headers)
            
            if response.status_code != 200:
                return {'success': False, 'error': f'API failed: {response.status_code}'}
            
            encrypted_data = response.text

            # CRYPTO DECRYPTION
            key = bytes.fromhex(self.key_hex)
            iv = bytes.fromhex(self.iv_hex)
            ciphertext = bytes.fromhex(encrypted_data)

            cipher = AES.new(key, AES.MODE_CBC, iv)
            plaintext = cipher.decrypt(ciphertext)
            decrypted_data = unpad(plaintext, AES.block_size)

            stream_info = json.loads(decrypted_data)
            video_url = stream_info.get('source')

            return {
                'success': True,
                'm3u8_url': video_url,
                'headers': headers,
                'video_id': video_id
            }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

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
        'message': 'Video Extractor API - Working with Crypto',
        'endpoints': {
            '/api/get-stream?title=MOVIE_TITLE': 'Get stream by title',
            '/api/direct-extract?video_id=FILE_CODE': 'Get stream by file_code'
        },
        'example': '/api/get-stream?title=wednesday.s01e02'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
