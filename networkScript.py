from networkLib import *
import logging

logging_dir= '/home/mtp/log/'
          
#logging.basicConfig(filename=logging_dir + 'NET.log',filemode='w', encoding='utf-8', level=logging.INFO,format='[%(asctime)s] %(message)s')

#logging.basicConfig( encoding='utf-8', level=logging.DEBUG,format='[%(asctime)s] %(message)s')

tx=True
if tx == True:
    transmitter()
else:
    receiver()
