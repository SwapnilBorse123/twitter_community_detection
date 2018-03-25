from twitter import *
import oauth2 as oauth
import requests
import json
import sys
import networkx as nx
import time
import collections
import matplotlib.pyplot as plt
import community

# No of unique app registrations used for the program (KEEP this equal to number of unique tokens)
MAX_CLIENTS = 1
# No of users to consider per level of BFS
TOP_N_USERS = 5
# No of levels for the BFS to consider
NUM_OF_LEVELS = 3
# No of seconds in a window frame alloted by Twitter (15 minutes)
WINDOW_FRAME = 900
# Seed User
SEED_USER = 'Mr Xyz'
# Path for the input json file
TOKENS_FILE_PATH = "tokens.json"
# Token lists for four types of tokens
CK_LIST = [] # consumer key
CKS_LIST = [] # consumer secret
OT_LIST = [] # token
OTS_LIST = [] # token secret


##########################################################################
#	Driver function
##########################################################################
def main():
	setGlobals();
	G = makeGraph(SEED_USER)
	#with open('/home/imcoolswap/semester_second/SMDM/assignments/assignment_3/PranayBhabhera', 'wb') as fp:
	#	pickle.dump(G, fp)
	runCommunityDetection(G)
	#with open('/home/imcoolswap/semester_second/SMDM/assignments/assignment_3/PranayBhabhera', 'rb') as fp:
	#	G = pickle.load(fp)
	#runCommunityDetection(G)


##########################################################################
#	Function to set all the global variables used in the program (read from a file)
##########################################################################
def setGlobals():
	global CK_LIST, CKS_LIST, OT_LIST, OTS_LIST
	global MAX_CLIENTS, TOKENS_FILE_PATH
	data = json.load(open(TOKENS_FILE_PATH))
	CK_LIST = data['consumer_key'].split(",")
	CKS_LIST = data['consumer_secret'].split(",")
	OT_LIST = data['token'].split(",")
	OTS_LIST = data['token_secret'].split(",")
	MAX_CLIENTS = len(CK_LIST)

##########################################################################
#	Function to make communities and display in the form of a visual
##########################################################################
def runCommunityDetection(G):
	partition = community.best_partition(G)  # compute communities
	pos = nx.spring_layout(G)  # compute graph layout
	plt.figure(figsize=(10, 10))
	plt.axis('off')
	nx.draw_networkx_nodes(G, pos, node_size=100, cmap=plt.cm.RdYlBu, node_color=list(partition.values()))
	nx.draw_networkx_edges(G, pos, alpha=0.5)
	plt.show(G)


##########################################################################
#	Function to make the graph
##########################################################################
def makeGraph(userScreenName):
	global MAX_CLIENTS
	G = nx.Graph()
	count, clientCounter, clientIndex, currClientApiHits, cursor, RATE_LIMIT = 0, 0, 0, 0, -1, 14
	nodeCount = 1
	timeLag = WINDOW_FRAME / (RATE_LIMIT * MAX_CLIENTS) + 0.05
	bfsQ = [userScreenName]
	G.add_node(userScreenName)
	idTosNameDict = {} # dict to map id to screen name
	stopFlag = True
	while len(bfsQ) > 0 and stopFlag: # while the queue is not empty
		cursor = -1
		#print('Top element: ' + bfsQ[0])
		currUserScreenName = bfsQ[0]
		bfsQ = bfsQ[1:] # pop the first element
		client = getTwitterHandle(clientIndex)	
		while cursor != 0:
			if currClientApiHits == RATE_LIMIT:
				clientCounter = clientCounter + 1
				clientIndex = clientCounter % MAX_CLIENTS
				client = getTwitterHandle(clientIndex) # change to next client when it's API limit is reached
				currClientApiHits = 0
			print('***************** Current Client Index, API Hit No: ' + str(clientIndex) + ', ' + str(currClientApiHits) + ' *****************')
			if nodeCount < pow(TOP_N_USERS, NUM_OF_LEVELS) + 1: # do it till third level
				currClientApiHits = currClientApiHits + 1
				topFiveSnameList = getTopFive(client, currUserScreenName, idTosNameDict, cursor, timeLag)
				cursor = 0 # considering only first 5000 and not more
				print('INFO: Top ' + str(TOP_N_USERS) + ' for ' + currUserScreenName + ' : ' + str(topFiveSnameList))
				bfsQ = bfsQ + topFiveSnameList;
				print('INFO: bfsQ: ' + str(bfsQ))
				nodeCount = nodeCount + TOP_N_USERS
				print('INFO: Total nodes till now: ' + str(nodeCount))
				addEdges(G, topFiveSnameList, currUserScreenName)
			else:
				stopFlag = False
				break
	return G


##########################################################################
#	Function to add the edges in the graph
##########################################################################
def addEdges(G, topFiveSnameList, currUserScreenName):
	for i in topFiveSnameList:
		G.add_node(i)
		G.add_edge(currUserScreenName, i)
	print('INFO: Added ' + str(G.number_of_edges()) + ' edges till now!')


###############################################################################
#	Function to return the top five reciprocal friends with maximum followers
###############################################################################
def getTopFive(client, currUserScreenName, idTosNameDict, cursor, timeLag):
	print('INFO: Getting top five for :' + currUserScreenName)
	friendsIdList, followersIdList = [], []
	friendsSet, followersSet = set(), set()
	tempDict = collections.OrderedDict()
	friendIdListUrl = 'https://api.twitter.com/1.1/friends/ids.json?cursor='+ str(cursor) +'&screen_name='+ currUserScreenName +'&count=5000'
	followerIdListUrl = 'https://api.twitter.com/1.1/followers/ids.json?cursor='+ str(cursor) +'&screen_name='+ currUserScreenName +'&count=5000'
	listFrResponse = client.request(friendIdListUrl)
	listFoResponse = client.request(followerIdListUrl)
	parsed_json_fr = json.loads(listFrResponse[1].decode('utf-8'))
	parsed_json_fo = json.loads(listFoResponse[1].decode('utf-8'))
	try:
		friendsIdList = friendsIdList + parsed_json_fr['ids']
		followersIdList = followersIdList + parsed_json_fo['ids']
	except:
		print(parsed_json_fr)
		print(parsed_json_fo)
	time.sleep(timeLag)
	friendsSet.update(friendsIdList);
	followersSet.update(followersIdList);
	reciFrnsIdList = list(friendsSet & followersSet)[:100] # consider only first 100 reciprocal friends
	reciFrnsIdStr = ",".join(map(str,reciFrnsIdList))
	lookupUrl = 'https://api.twitter.com/1.1/users/lookup.json?user_id=' + reciFrnsIdStr
	parsed_json_usrData = json.loads(client.request(lookupUrl)[1].decode('utf-8'))
	for i in range(len(parsed_json_usrData)):
		try:
			if parsed_json_usrData[i]['protected'] != True: # skip protected users
				tempDict[parsed_json_usrData[i]['id']] = parsed_json_usrData[i]['followers_count']
		except:
			print(parsed_json_usrData)
	topFiveIdList = [i[0] for i in list(tempDict.items())[-TOP_N_USERS:]]
	topFiveSnameList = []
	for i in range(len(parsed_json_usrData)):
		try:
			if parsed_json_usrData[i]['id'] in topFiveIdList:
				idTosNameDict[parsed_json_usrData[i]['id']] = parsed_json_usrData[i]['screen_name']
				topFiveSnameList.append(parsed_json_usrData[i]['screen_name'])
		except:
			print(parsed_json_usrData)
	return topFiveSnameList



##########################################################################
#	Function to return an object of Twitter handle
##########################################################################
def getTwitterHandle(index):
	global CK_LIST, CKS_LIST, OT_LIST, OTS_LIST
	try:
		CONSUMER_KEY = CK_LIST[index]
		CONSUMER_SECRET = CKS_LIST[index]
		OAUTH_TOKEN = OT_LIST[index]
		OAUTH_TOKEN_SECRET = OTS_LIST[index]

		# creating client to authorize every http request
		consumer = oauth.Consumer(key = CONSUMER_KEY, secret = CONSUMER_SECRET)
		token = oauth.Token(key = OAUTH_TOKEN,secret = OAUTH_TOKEN_SECRET)
		client = oauth.Client(consumer, token)

		return client
	except:
		e = sys.exc_info()[0]
		print('ERROR: Exception caught: ' + str(e))
		return None


##########################################################################
#	Main function call
##########################################################################
if __name__ == "__main__":
	main()