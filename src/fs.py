import os
import json
import base64
import hashlib
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class PyFS:
	"""A minimal container storing files inside a single file.

	File layout:
	  4 bytes: b'PYFS' magic
	  1 byte: version
	  4 bytes: header length (big-endian)
	  N bytes: header JSON (plaintext) with fields: username, salt (hex), version, iterations
	  12 bytes: nonce used for AES-GCM
	  remaining bytes: AES-GCM ciphertext (includes tag)

	Encryption uses AES-256-GCM with a key derived from the password via PBKDF2-HMAC-SHA256.
	This provides authenticated encryption suitable for protecting confidentiality and integrity.
	"""

	MAGIC = b'PYFS'
	VERSION = 1

	def __init__(self, path):
		self.path = path
		self.files = {}
		self.header = None

	@staticmethod
	def _derive_key(password: str, salt: bytes, iterations: int = 100000) -> bytes:
		return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations, dklen=32)

	def create(self, username: str, password: str):
		dirpath = os.path.dirname(self.path)
		if dirpath and not os.path.exists(dirpath):
			os.makedirs(dirpath, exist_ok=True)
		salt = secrets.token_bytes(16)
		header = {
			'username': username,
			'salt': salt.hex(),
			'version': self.VERSION,
			'iterations': 100000,
		}
		payload = json.dumps({}).encode('utf-8')
		key = self._derive_key(password, salt, header['iterations'])
		aesgcm = AESGCM(key)
		nonce = secrets.token_bytes(12)
		encrypted = aesgcm.encrypt(nonce, payload, None)
		with open(self.path, 'wb') as f:
			f.write(self.MAGIC)
			f.write(bytes([self.VERSION]))
			header_bytes = json.dumps(header).encode('utf-8')
			f.write(len(header_bytes).to_bytes(4, 'big'))
			f.write(header_bytes)
			f.write(nonce)
			f.write(encrypted)
		self.files = {}
		self.header = header

	def load(self, username: str, password: str):
		if not os.path.exists(self.path):
			raise FileNotFoundError(self.path)
		with open(self.path, 'rb') as f:
			magic = f.read(4)
			if magic != self.MAGIC:
				raise ValueError('Not a PyFS file')
			version_byte = f.read(1)
			if not version_byte:
				raise ValueError('Corrupted file')
			version = version_byte[0]
			header_len = int.from_bytes(f.read(4), 'big')
			header_bytes = f.read(header_len)
			header = json.loads(header_bytes.decode('utf-8'))
			salt = bytes.fromhex(header['salt'])
			iterations = header.get('iterations', 100000)
			if username != header.get('username'):
				raise PermissionError('Username does not match')
			rest = f.read()
			if not rest:
				payload = b'{}'
			else:
				if len(rest) < 12:
					raise ValueError('Corrupted file (missing nonce)')
				nonce = rest[:12]
				ciphertext = rest[12:]
				key = self._derive_key(password, salt, iterations)
				aesgcm = AESGCM(key)
				try:
					payload = aesgcm.decrypt(nonce, ciphertext, None)
				except Exception as e:
					raise PermissionError('Incorrect password or corrupted file') from e

		data = json.loads(payload.decode('utf-8')) if payload else {}
		files = {}
		for name, b64 in data.items():
			files[name] = base64.b64decode(b64.encode('utf-8'))
		self.files = files
		self.header = header

	def save(self, password: str):
		if self.header is None:
			raise RuntimeError('No header present; create or load first')
		salt = bytes.fromhex(self.header['salt'])
		iterations = self.header.get('iterations', 100000)
		key = self._derive_key(password, salt, iterations)
		aesgcm = AESGCM(key)
		data = {name: base64.b64encode(data_bytes).decode('utf-8') for name, data_bytes in self.files.items()}
		payload = json.dumps(data).encode('utf-8')
		nonce = secrets.token_bytes(12)
		encrypted = aesgcm.encrypt(nonce, payload, None)
		with open(self.path, 'wb') as f:
			f.write(self.MAGIC)
			f.write(bytes([self.VERSION]))
			header_bytes = json.dumps(self.header).encode('utf-8')
			f.write(len(header_bytes).to_bytes(4, 'big'))
			f.write(header_bytes)
			f.write(nonce)
			f.write(encrypted)

	def list_files(self):
		return list(self.files.keys())

	def add(self, name: str, data_bytes: bytes):
		self.files[name] = data_bytes

	def delete(self, name: str):
		if name in self.files:
			del self.files[name]
		else:
			raise KeyError(name)

	def get(self, name: str):
		return self.files.get(name)
