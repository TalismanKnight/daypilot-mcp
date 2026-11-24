"""Local-only DayPilot web client. Run from the project root."""
import asyncio, base64, json, sys, threading, webbrowser
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent
ALLOWED = {'get_day_overview','get_free_slots','get_priority_list','propose_plan','confirm','undo_last_change','speak_morning_briefing','set_profile','add_task','add_event','get_audit_log','plan_departure','prepare_ride','prepare_payment','confirm_payment_handoff','cancel_payment'}
URL = 'http://127.0.0.1:8765'
async def call(name, args):
    params = StdioServerParameters(command=sys.executable, args=['-m','daypilot.payment_server'], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, args)
            if result.isError:
                raise RuntimeError('MCP tool failed: ' + ' '.join(getattr(c,'text','') for c in result.content))
            data = getattr(result,'structuredContent',None)
            if not data:
                data = json.loads(next(c.text for c in result.content if c.type=='text'))
            if 'result' in data and isinstance(data['result'],dict): data = data['result']
            if name == 'speak_morning_briefing' and data.get('audio_path'):
                p = Path(data['audio_path']).resolve()
                if p.is_relative_to((ROOT/'out').resolve()) and p.suffix=='.mp3' and p.is_file():
                    data['audio'] = base64.b64encode(p.read_bytes()).decode()
                data.pop('audio_path',None)
            return data
class Handler(BaseHTTPRequestHandler):
    def send_data(self, status, data, mime):
        self.send_response(status); self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if self.path=='/': self.send_data(200,(ROOT/'daypilot_ui.html').read_bytes(),'text/html; charset=utf-8')
        else: self.send_error(404)
    def do_POST(self):
        if self.path!='/tool' or self.headers.get('Origin')!=URL or self.headers.get('Host')!='127.0.0.1:8765' or self.headers.get_content_type()!='application/json':
            self.send_error(403); return
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=16000: raise ValueError('Invalid request size')
            body=json.loads(self.rfile.read(n)); name=body['tool']; args=body.get('args',{})
            if name not in ALLOWED or not isinstance(args,dict): raise ValueError('Unsupported tool')
            data=asyncio.run(call(name,args)); self.send_data(200,json.dumps(data).encode(),'application/json')
        except Exception as e:
            self.send_data(400,json.dumps({'error':str(e)}).encode(),'application/json')
if __name__=='__main__':
    server=HTTPServer(('127.0.0.1',8765),Handler)
    print('DayPilot:',URL,flush=True)
    threading.Timer(0.7,lambda:webbrowser.open(URL)).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
