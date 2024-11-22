import requests
import json as JSON

def altiriaSms(destinations, message, senderId, debug):
    if debug:
        print('Enter altiriaSms: '+destinations+', message: '+message+', senderId: '+senderId)
        if debug:
            #Se fija la URL base de los recursos REST
            baseUrl = 'https://www.altiria.net:8443/apirest/ws'
            #Se construye el mensaje JSON
            #YY y ZZ se corresponden con los valores de identificación del usuario en el sistema.
            #Descomentar para utilizar la autentificación mediante apikey
            credentials = {'apiKey': '', 'apiSecret': ''}
            destination = destinations.split(",")
            messageData = {
                'msg': message
                #No es posible utilizar el remitente en América pero sí en España y Europa
                #Descomentar la línea si se cuenta con un remitente autorizado por Altiria
                #,'senderId': senderId
            }
            jsonData = {'credentials': credentials, 'destination': destination, 'message': messageData}

            #Se fija el tipo de contenido de la peticion POST
            contentType = {'Content-Type':'application/json;charset=UTF-8'}

            #Se añade el JSON al cuerpo de la petición
            #Se fija el tiempo máximo de espera para conectar con el servidor (5 segundos)
            #Se fija el tiempo máximo de espera de la respuesta del servidor (60 segundos)
            #timeout(timeout_connect, timeout_read)
            #Se envía la petición y se recupera la respuesta
            r = requests.post(baseUrl+'/sendSms', data=JSON.dumps(jsonData), headers=contentType, timeout=60)
            print("REQUEST BODY" +JSON.dumps(jsonData))
            if debug:
                #Error en la respuesta del servidor
                if str(r.status_code) != '200':
                    print ('ERROR GENERAL: '+str(r.status_code))
                    print (r.text)
                else:
                    #Se procesa la respuesta capturada
                    print ('Código de estado HTTP: '+str(r.status_code))
                    jsonParsed = JSON.loads(r.text)
                    status = str(jsonParsed['status'])
                    print ('Código de estado Altiria: '+status)
                    if status != '000':
                        print ('Error: '+r.text)
            return r.text

