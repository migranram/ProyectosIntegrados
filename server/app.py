## @package AppServidor
# Codigo principal servidor Comunicacion con el resto de dispositivos.

from flask import Flask, render_template, session, request, \
    copy_current_request_context
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect

import json
import pandas as pd
from dataManagement import Account

## INICIALIZACION DEL SERVIDOR Y BASE DE DATOS++
df = pd.read_csv('plantilla.csv')
rows, cols = (12,2)
cuentas = [[0 for i in range(cols)] for j in range(rows)]
clients = [[0 for i in range(cols)] for j in range(rows)]
cocinaSID = -1

ids = [[0 for i in range(cols)] for j in range(rows)]
IDpedido = 0

async_mode = None
puerto = 5000 
ip = "192.168.1.106"
    
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)

##----------------------------------------------

## ENRUTADOS+++++++++++++++++++++++++++++++++++

# APP MESAS
@app.route('/')
def index():
    mesa = request.args.get('mesa')
    pos = request.args.get('pos')
    #print(str(mesa) + " " + str(pos))
    data = {'table':mesa,'pos':pos}
    return render_template('Comanda.html', async_mode=socketio.async_mode, data=data)

# APP COCINA
@app.route('/cocina/')
def cocinaindex():
    return render_template('Cocina.html', async_mode=socketio.async_mode, data={'table':-1,'pos':-1})

# DESPEDIDA
@app.route('/gracias/')
def gracias():
    return render_template('gracias.html', async_mode=socketio.async_mode)


##-----------------------------------------------

## EVENTOS++++++++++++++++++++++++++++++++++++++++



# CONEXION

@socketio.event
def conectado(data):
    global cocinaSID
    #print("%s connected" % (request.sid))
    
    if(data['mesa'] == -1 or data['pos'] == -1):
        print('Kitchen connected with SID: ' + request.sid)
        cocinaSID = request.sid
    else: # Usuario nuevo o ya existe cuenta para esa posicion?
        if(cuentas[data['mesa']][data['pos']] == 0 or cuentas[data['mesa']][data['pos']] == None):
            print('New user at table [' + str(data['mesa']) + '] position [' + str(data['pos']) + ']')
            cuentas[data['mesa']][data['pos']] = Account('cuenta',df,data['mesa'],data['pos'])
            clients[data['mesa']][data['pos']] = request.sid
        else:
            print('ERROR, USER ALREADY EXISTS')



# MESA ENVIA COMANDA

@socketio.event
def comanda(message):
    global IDpedido
    mesa = message['mesa']
    pos = message['pos']
    if(any(request.sid in sublist for sublist in clients)): #Comprobamos si el usuario está registrado
        for c in message['data']:
            cuentas[mesa][pos].addProduct([c['product']],[int(c['quantity'])],message['id'])

        print(cuentas[mesa][pos].getOrders())
        emit('update',
            {'estado': 'Recibido', 'id': message['id']})
        emit('nuevaComanda',
            {'data': message['data'], 'id': IDpedido, 'mesa': message['mesa'], 'pos':message['pos'], 'total': cuentas[mesa][pos].getBill()},room=cocinaSID)
        ids[mesa][pos] = IDpedido
        IDpedido = IDpedido + 1
    else:
        print('ERROR, USER NOT REGISTERED')


# COCINA ACTUALIZA ESTADO
@socketio.event
def cocinaUpdate(message):
    print(message)
    emit('update',
         {'estado': message['state'], 'id': message['id']},room=clients[message['mesa']][message['pos']])
    if message['state']=='Preparado':   #al pulsar el boton de preparado, le damos al robot la orden de servir mesa
        emit('servir_mesa',
        {'mesa':message['mesa'], 'pos':message['pos']},room=robotSID)


# TESTS

@socketio.event
def prueba(message):
    print(message)


#ROBOT

@socketio.event
def robot(message):
    global robotSID
    robotSID=request.sid  #Guardamos el id del robot

@socketio.event
def robot_state(estado):
    emit('robot_state',
            estado,room=cocinaSID)


# DESCONEXION

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected', request.sid)
    for x in range(len(clients)):
        for y in range(2):
            if(clients[x][y] == request.sid):
                emit('finCliente',{'id': ids[x][y]},room=cocinaSID)
                if(cuentas[x][y].getBill()!=0): #Si el cliente ha hecho un pedido, recogemos su mesa.
                    emit('recoger_mesa',
                    {'mesa':x, 'pos':y},room=robotSID)
                clients[x][y] = None
                cuentas[x][y] = None

## -------------------------------------------------------


## EJECUCION DEL SERVER ++++++++++++++++++++++++++++++++++
if __name__ == '__main__':
    print("Running on " + str(ip) + ": " + str(puerto))
    socketio.run(app,port=puerto,host=ip)

##---------------------------------------------------------    