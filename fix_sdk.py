from pathlib import Path
p=Path('main.py');s=p.read_text(encoding='utf-8');s=s.replace('from vercel.blob import BlobClient','from vercel.blob import sync as blob_sdk\n\nclass BlobClient:\n    put = staticmethod(blob_sdk.put_blob)\n    delete = staticmethod(blob_sdk.delete_blob)');a=s.index('def list_blobs(prefix):');b=s.index('\n\ndef bot_enabled',a);s=s[:a]+'def list_blobs(prefix):\n    return list(blob_sdk.query_blobs(prefix=prefix))\n'+s[b:];p.write_text(s,encoding='utf-8')
Path('requirements.txt').write_text('flask>=3.1,<4\ndiscord-webhook>=1.4,<2\nvercel==0.12.0\n',encoding='utf-8')
Path('.vercelignore').write_text('.test-deps\n__pycache__\nupdate_admin.py\nverify_admin.py\n',encoding='utf-8')
