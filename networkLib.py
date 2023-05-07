from pyrf24 import RF24, rf24
import pandas as pd
import time
import logging

logging.basicConfig(level=logging.DEBUG)

#Array of link addresses (5 bytes each)
LINK_ADDRESSES = [b'NodeA1', b'NodeA2', b'NodeB1', b'NodeB2', b'NodeC1', b'NodeC2']
OWN_ADDRESS = b'NodeA1' #TODO Change to each address of each team TR
LINK_ADDRESSES.remove(OWN_ADDRESS) 

#Filename TODO: Change for each team
FILENAME = 'transmittedFile.txt' 

#Packet size
PACKET_SIZE = 32

#End of transmission message
EOT = [226, 144, 151]
EOT_BYTES = bytes(EOT)

#Timeout
TIMEOUT_FILE = 10
TIMEOUT_TOKEN = 1
TIMEOUT_STATUS = 2
TIMEOUT_STATUS_REPLY = 2

#Global Table with the reachable transceivers
tb = pd.DataFrame(columns=['Address', 'Token', 'File'])

#Token Info, Each transceiver must know if it has had the token or not
token = 0

#File Info, Each TR must know if it has the file or not
file = 0

#These packets have no payload, header=packet
TOKEN_PACKET = b'\x0D'

#Headers for packets that need to be built each time they are sent (updated info)
HEADER_STATUS = b'\x0A'
HEADER_STATUS_PACKET_REPLY = b'\x0B'
HEADER_FILE_PACKET = b'\x0C'

def transmitter():
    """
    Initializes file and token value to 1
    Initializes radio
    Calls sendStatus()
    Calls sendFile()
    Calls sendToken()
    """
    
    global file, token
    
    file = 1
    token = 1

    radio = RF24()
    if not radio.begin(4,0): #TODO: Here the 1st pin cahnegs for each team
        raise OSError("nRF24L01 hardware isn't responding")
    radio.payload_size = 32
    radio.channel = 26 #6A 20
    radio.data_rate = rf24.RF24_250KBPS
    radio.set_pa_level(rf24.rf24_pa_dbm_e.RF24_PA_HIGH)
    radio.dynamic_payloads = True
    radio.set_auto_ack(True)
    radio.ack_payloads = False
    radio.set_retries(5, 15) 
    radio.listen = False

    sendStatus(radio)

    sendFile(radio,FILENAME)

    while not sendToken(radio):
        continue

    del radio

    receiver()
    
    

#this function has to be executed every time the TR is passed the token
def sendStatus(radio):
    """
    Sends Status Packet to every Link Addresses with TIMEOUT_STATUS
    If there is response the open rx pipe and listen for response with TIMEOUT_STATUS_REPLY
    Stores info in a Table together with the corresponding link address. 
        If link address already in table update values, otherwise add new row
    """
    global tb
    
    for address in LINK_ADDRESSES:
        radio.open_tx_pipe(address)
        response = False
        timed_out = False
        start_time = time.time()
        while not response and not timed_out:
            response = radio.write(HEADER_STATUS+OWN_ADDRESS)
            timed_out = (time.time() - start_time > TIMEOUT_STATUS)
        
        if response: 
            logging.debug("Obtained response from " + str(address))
            radio.open_rx_pipe(1, OWN_ADDRESS)
            radio.listen = True
            timed_out = False
            start_time = time.time()
            while not radio.available() and not timed_out:
                time.sleep(1/1000)
                timed_out = (time.time() - start_time > TIMEOUT_STATUS_REPLY)
               
            if radio.available():
                answer_packet = radio.read(radio.get_dynamic_payload_size())
                radio.listen = False
                radio.close_rx_pipe(1)
                if answer_packet[0].to_bytes(1, byteorder='big') == HEADER_STATUS_PACKET_REPLY:
                    file_status = answer_packet[1]
                    token_status = answer_packet[2]
                    new_row = {'Address':address, 'File': file_status, 'Token':token_status}
                    if (tb['Address'] == new_row['Address']).any():
                        tb.loc[tb['Address'] == new_row['Address']] = new_row
                    else:
                        tb.loc[len(tb)] = new_row
                        
    logging.debug('sendStatus() finished:')                
    logging.debug(tb)              
            


def sendFile(radio,filename):
    """
    Send File to transceivers that do not have it already. (Check table)
    If TR stops responding ACKs keep trying during Timeout (think best value).
    If a TR timeouts, eliminate from tb so token is not passed to it.
    """
    global tb
    file = readFile(filename)
    timed_out = False
    for index, row in tb.iterrows():
        if row['File'] == 0:
            radio.open_tx_pipe(row['Address'])
            packet_id = b'\x00'
            start_time = time.time()
            timed_out = False
            for i in range(0, len(file),PACKET_SIZE-2):
                message = HEADER_FILE_PACKET + packet_id + file[i:i+PACKET_SIZE-2]

                while (not radio.write(message) and not timed_out):
                    timed_out = (time.time() - start_time > TIMEOUT_FILE)

                if timed_out:
                    tb = tb.drop(index) 
                    break
                int_value = int.from_bytes(packet_id, byteorder='big')  # convert byte to integer
                if int_value == 255:
                    int_value = 0
                else:
                    int_value += 1  # increment integer
                packet_id = int_value.to_bytes(1, byteorder='big')  # convert integer back to byte
            
            if not timed_out:
                end_packet = HEADER_FILE_PACKET + packet_id + EOT_BYTES
                while (not radio.write(end_packet) and not timed_out):
                    timed_out = (time.time() - start_time > TIMEOUT_FILE)            
    
    logging.debug('sendFile()')
    logging.debug('timed_out:'+str(timed_out))

def readFile(fileName): #TODO Read file from usb, particular for each team
    """
    Read file from usb.
    Return the file in bytes
    """
    with open("transmittedFile.txt", 'rb') as transmittedFile:
        file_data = transmittedFile.read()
    return file_data

def sendToken(radio):
    """
    Send Token to TR and keep retrying (Timeout= 5-10 s)
    Look table col 'Token' for priority: First TR with value 0, then TR with value 1 in first position
    If Token is sent to a TR with 'token' = 0, 'token' value is updated to 1 and TR is sent to the last row
    If Token is sent to a TR with 'token' = 1, 'token' TR is sent to the last row
    Returns True if token is passed to another node, False otherwise.
    """
    global tb
    token_passed = False

    if 0 in tb['Token'].values:
        for index, row in tb.iterrows():
            if row['Token'] == 0:
                start_time = time.time()
                radio.open_tx_pipe(row['Address'])
                token_passed = False
                timed_out = False
                while (not token_passed and not timed_out):
                    token_passed = radio.write(TOKEN_PACKET)
                    timed_out = (time.time() - start_time > TIMEOUT_TOKEN)
                if token_passed:
                    tb.loc[index,'Token'] = 1
                    tb =tb.drop(index)
                    tb = pd.concat([tb,row]) #move row to the last position
                    break
        
    if not token_passed: 
        for index, row in tb.iterrows():
            if row['Token'] == 1:
                start_time = time.time()
                radio.open_tx_pipe(row['Address'])
                token_passed = False
                timed_out = False
                while (not token_passed and not timed_out):
                    token_passed = radio.write(TOKEN_PACKET)
                    timed_out = (time.time() - start_time > TIMEOUT_TOKEN)
                if token_passed:
                    tb =tb.drop(index)#move row to the last position
                    tb = pd.concat([tb,row])
                    break

    logging.debug('sendToken()')
    logging.debug('token_passed:'+str(token_passed))
    return token_passed



def receiver():
    """
    Loop until receives a message.
    Take first byte (Header) and identify the message type.
    Call the corresponding function.
    """
    radio = RF24()
    if not radio.begin(4,0): #TODO: Here the 1st pin changes for each team
        raise OSError("nRF24L01 hardware isn't responding")
    radio.payload_size = 32
    radio.channel = 26 #6A 20
    radio.data_rate = rf24.RF24_250KBPS

    radio.set_pa_level(rf24.rf24_pa_dbm_e.RF24_PA_HIGH)
    radio.dynamic_payloads = True
    radio.set_auto_ack(True)
    radio.ack_payloads = False

    radio.set_retries(5,15) 
    radio.open_rx_pipe(1, OWN_ADDRESS) 
    radio.listen = True

    while True:
        while not radio.available():
            time.sleep(1/1000)
            continue

        received_message = radio.read(radio.get_dynamic_payload_size())

        header = received_message[0].to_bytes(1, byteorder='big') 

        if header == HEADER_STATUS:
            receiveStatus(radio, received_message)
        elif header == HEADER_FILE_PACKET:
            receiveFile(radio, received_message)
        elif header == TOKEN_PACKET:
            receiveToken(radio)

def receiveStatus(radio, message):
    """
    Open Tx pipe with transmitter address
    Build packet using the token and file global variables.
    Send it back to transmitter (timeout=5-10s)
    """
    radio.listen = False
    tx_address = message[1:6]
    radio.open_tx_pipe(tx_address)
    
    file_info = file.to_bytes(1, byteorder = 'big')
    token_info = token.to_bytes(1, byteorder='big')
    info = HEADER_STATUS_PACKET_REPLY + file_info + token_info
    response = False
    timed_out = False
    start_time = time.time()
    while not response and not timed_out:
        response = radio.write(info)
        timed_out = (time.time() - start_time > TIMEOUT_STATUS)
    radio.listen = True
    logging.debug('receiveStatus()')
    logging.debug('timed_out:'+ str(timed_out))
    logging.debug('response:' + str(response))

def receiveFile(radio, first_message):
    """
    Loop to receive file until an end of transmission is received (or timeout)
    Save the file to USB
    """
    last_packet_id = b'\xFF'
    transmission_end = False
    message_list = [first_message[2:]]

    timed_out = False
    start_time = time.time()
    while not transmission_end and not timed_out:
        while not radio.available() and not timed_out:
            time.sleep(1/1000)
            timed_out = (time.time() - start_time > TIMEOUT_STATUS)
        if radio.available():
            received_message = radio.read(radio.get_dynamic_payload_size())
            header = received_message[0]
            if header.to_bytes(1, byteorder='big') == HEADER_FILE_PACKET:
                if last_packet_id != received_message[1]:
                    if received_message[2:] == EOT_BYTES:
                        transmission_end = True
                    else:
                        message_list.append(received_message[2:])
                    last_packet_id=received_message[1]
    
    if transmission_end:
        file_data = b''.join(message_list)
        file = 1
        saveFile(file_data)
        logging.debug('File data:')
        logging.debug(file_data)


def receiveToken(radio):
    """
    When token packet is received. 
    Update token variable
    Then start transmitting mode (send status,...)
    """
    #token = 1
    del radio
    logging.debug('Token received')
    transmitter()

def saveFile(file_data): #TODO Save file in usb, particular for each team
    """
    Gets file in bytes.
    Save file in usb.
    """
    with open('transmittedFile.txt','wb') as transmittedFile:
        transmittedFile.write(file_data)
