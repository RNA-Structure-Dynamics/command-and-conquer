from socket import *
from time import ctime
import time
import base64
import hashlib
import six
import threading,_thread
import json
import _thread
lock=_thread.allocate_lock()
#lock=threading.lock()
connectionlist = []
gameRooms=[{'status':'empty','players':[],'current_tick':0},{'status':'empty','players':[],'current_tick':0}]
def JoinRoom(player,roomID):
    global connectionlist,gameRooms
    room=gameRooms[roomID]
    if(room['status']=='full'):
        return False
    room['players'].append(player)
    player.room=roomID
    player.team='gdi'
    if(len(room['players'])==1):
        room['status']='waiting'
    elif(len(room['players'])==2):
        room['status']='full'
        if(room['players'][0].team=='gdi'):
            player.team='nod'
    return True
def LeaveRoom(player):
    global gameRooms
    room=gameRooms[player.room]
    room['current_tick']=0
    if(room['status']=='full'):
        room['status']='waiting'
    elif(room['status']=='waiting'):
         room['status']='empty'
    if(room['players'][0]==player):
         room['players'].pop(0)
    else:
         room['players'].pop(1)
    if(room['status']=='waiting'):
        room['players'][0].connection.send(send_data('{"type":"end_game"}'))
    print(player,'leave room',room)
def initGame(roomID):
    global gameRooms
    room=gameRooms[roomID]
    if(room['status']=='full'):
        room['players'][0].connection.send(send_data('{"type":"start_game"}'))
        room['players'][1].connection.send(send_data('{"type":"start_game"}'))
        return True
    return False
        
        
class WebSocketClient(threading.Thread):
    def __init__(self,conn,ip_address,ip_port):
        super(WebSocketClient,self).__init__(name=ip_address+':'+str(ip_port))
        self.ip_address=ip_address
        self.ip_port=ip_port
        self.connection=conn
        self.handshake_finished=False
        self.room=-1
        self.team=None
        self.latencyTrips=[]
        self.commands=[]
        self.lastTickConfirmed=-1
        self.tickLag=-1
    def player_quit(self,quit_string):
        print('client quit out:',quit_string);
        LeaveRoom(self)
        self.connection.close()
    def measureLatency(self):
        self.latencyTrips.append({'start':time.time()})
        self.connection.send(send_data('{"type":"latency_ping"}'))
    def finishMeasuringLatency(self,clientMessage):
        measurement=self.latencyTrips[len(self.latencyTrips)-1]
        measurement['end']=time.time()
        measurement['roundTrip']=measurement['end']-measurement['start']
        #if(len(self.latencyTrips)==3):
        #    self.tickLag=int(sum(self.latencyTrips)*0.3)+1;
            
        print('milliseconds:',measurement['roundTrip']*1000)
    def run(self):
        global connectionlist,gameRooms
        print('connection try from ', self.ip_address,self.ip_port)
        while True:
            try:
                data=self.connection.recv(BUFSIZ)
            except Exception as e:
                print(e)
                self.connection.close()
                break
            if not data:
                self.player_quit('no data')
                break
            if(self.handshake_finished):
                received_data=parse_data(data);
                #print(data,received_data)
                if not(received_data):
                    self.player_quit('normal')
                    break
                json_data=json.loads(received_data)
                if(json_data['type']=="latency_pong"):
                    self.finishMeasuringLatency(json_data)
                    if(len(self.latencyTrips)<3):
                        self.measureLatency()
                elif(json_data['type']=='command'):
                    if(json_data.get('uids')):
                        self.commands.append({'uids':json_data['uids'],'details':json_data['details']})
                    self.lastTickConfirmed=int(json_data['currentTick'])
                    #print(self.team,received_data)
                    
                #target=json_data['t']
                #handle different message type based on message.type
                #if not target:
                #    s='Hi,you send yourself :[%s] %s' %(ctime(),received_data)
                #    target=self.ip_address
                #else:
                #    json_data['time']=ctime()
                #    s=json.dumps(json_data)
                #for i in connectionlist:
                #    if(target==i.ip_address):#broadcasting delete this judging!
                #        i.connection.send(send_data(s))
                        
                #print(s)
                STOP_CHAT=(received_data.upper()=="QUIT")
                if STOP_CHAT:
                    self.connection.close()
                    break

            else:
                headers = parse_headers(data.decode('utf-8'))
                token = generate_token(headers['Sec-WebSocket-Key'])#byte
                self.connection.send(handshake_header+token+b'\r\n\r\n')
                self.handshake_finished=True
                if (self.room<0):
                    roomJoinMsg={'type':"joined_room"}
                    if not(JoinRoom(self,0)):
                        if not(JoinRoom(self,1)):
                            roomJoinMsg['roomID']=-1
                        roomJoinMsg['roomID']=1
                    roomJoinMsg['roomID']=0
                    roomJoinMsg['team']=self.team
                    #send roomJoinMessage
                    s=json.dumps(roomJoinMsg)
                    print('join_room_msg',s)
                    self.connection.send(send_data(s))
                    if(gameRooms[self.room]['status']=='full'):
                        initGame(self.room)
                    self.measureLatency()
                    continue

def CheckWebClientSocketStatus():
    global connectionlist,gameRooms
    lock.acquire()
    for i in range(len(connectionlist)):
        if not connectionlist[i].is_alive():
            print('delete a quited connection')
            quited_connection=connectionlist.pop(i)
            del quited_connection
            break;
    if(gameRooms[0]['status']=='full' and gameRooms[0]['players'][0].lastTickConfirmed>=gameRooms[0]['current_tick'] and \
       gameRooms[0]['players'][1].lastTickConfirmed>=gameRooms[0]['current_tick']):
        new_commands=[]
        new_commands.extend(gameRooms[0]['players'][0].commands)
        new_commands.extend(gameRooms[0]['players'][1].commands)
        json_str_to_send=json.dumps({'type':"game_tick",'tick':(gameRooms[0]['current_tick']+2),'commands':new_commands})
        gameRooms[0]['players'][0].connection.send(send_data(json_str_to_send))
        gameRooms[0]['players'][1].connection.send(send_data(json_str_to_send))
        gameRooms[0]['players'][0].commands=[]
        gameRooms[0]['players'][1].commands=[]
        gameRooms[0]['current_tick']+=1
    lock.release()
    check_t=threading.Timer(0.1,CheckWebClientSocketStatus)
    check_t.start()

def parse_headers(msg):
    headers = {}
    header, data = msg.split('\r\n\r\n', 1)
    for line in header.split('\r\n')[1:]:
        key, value = line.split(': ', 1)
        headers[key] = value
    headers['data'] = data
    return headers
def generate_token(msg):
    key = msg + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
    ser_key = hashlib.sha1(key.encode('utf-8')).digest()
    return base64.b64encode(ser_key)
def send_data(msg):#msg is unicode
    msg_len=len(msg)
    if(msg_len<=125):
        data_to_send=b'\x81'+six.int2byte(msg_len)+msg.encode('utf-8')
    else:
        data_to_send=b'\x81\x7e'
        data_len_higher=six.int2byte(int(msg_len/256))
        data_len_lower=six.int2byte(msg_len%256)
        data_to_send+=data_len_higher+data_len_lower+msg.encode('utf-8')
    
    return data_to_send

def parse_data(msg_byte):
    if(msg_byte[0]==0x88):
        return False
    v = msg_byte[1] & 0x7f
    if v == 0x7e:#126
        p = 4
    elif v == 0x7f:
        p = 10
    else:
        p = 2
    mask = msg_byte[p:p+4]
    data = msg_byte[p+4:]
    i=0
    Ls=[]
    while(i<len(data)):
        mask1=mask[i%4]
        Ls.append(chr(mask1^data[i]))
        i+=1
    return ''.join(Ls)#unicode returned
    
HOST=''
PORT=12345
BUFSIZ=1024
ADDR=(HOST, PORT)
handshake_header=b'\
HTTP/1.1 101 WebSocket Protocol Hybi-10\r\n\
Upgrade: WebSocket\r\n\
Connection: Upgrade\r\n\
Sec-WebSocket-Accept: '
is_connected=False
sock=socket(AF_INET, SOCK_STREAM)

sock.bind(ADDR)

sock.listen(5)
CheckWebClientSocketStatus()
while True:
    print('waiting for next connection...')
    is_connected=False
    tcpClientSock, addr=sock.accept()
    newSocket=WebSocketClient(tcpClientSock,addr[0],addr[1])
    newSocket.start()
    connectionlist.append(newSocket)
    print('total connectin now:',connectionlist)
#tcpClientSock.close()
sock.close()
