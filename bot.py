#!/usr/bin/env python

"""A really simple IRC bot."""

import sys
from twisted.internet import reactor, protocol
from twisted.words.protocols import irc


protocols = []

admin_nick = [ 'aquaman',
               'heytrav',
               'curry-overlord',
             ]
admin_commands = [ 'curry',
                 ]

def maybe_int(x):
    try: return int(x)
    except: return -1   # bs

class Bot(irc.IRCClient):
    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)

    _sentQueue = []
    users = {}

    def signedOn(self):
        self.join(self.factory.channel)
        self.channel = self.factory.channel
        protocols.append(self)
        self.lineRate = 0.0
        print "Signed on as %s." % self.nickname

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        protocols.remove(self)

    def joined(self, channel):
        print "Joined %s." % channel

    def act(self, user, channel, cmd):
        username = user.split('!',1)[0]
        if channel == self.nickname:
            channel = username
        global admin_nick, admin_commands
        parts = cmd.split(' ',2)
        op = parts[0]
        if op in admin_commands and not username in admin_nick:
            self.msg(channel, 'sorry you are not an admin')
            return
        if op == 'help':
            self.msg(channel, '!help: show this message.')
            self.msg(channel, '!curry [<message>]: notify CURRY. defaults to \'CURRY\'')

        if op == 'curry':
            message = len(parts) > 1 and ' '.join(parts[1:]) or "CURRY";
            msgAll('<%s> %s' % (username, message))

    def privmsg(self, user, channel, msg):
        print 'channel: `%s` user: `%s` msg: `%s`' % (user, channel, msg)
        if msg.startswith('!'):
            self.act( user, channel, msg[1:] )
        elif msg.startswith('currybot: '):
            self.act( user, channel, msg[10:] )

    def irc_NOTICE(self, prefix, params):
        if params[1] == '*** Message to %s throttled due to flooding' % (self.factory.channel):
            self.lineRate += 0.1
            self._queue.insert(0, self._sentQueue.pop())
            if not self._queueEmptying:
                self._sendLine()
            print "Flooding detected, lineRate now at %0.1f seconds" % self.lineRate

    def _reallySendLine(self, line):
        if line.startswith('PRIVMSG '):
            self._sentQueue.append(line)
            if len(self._sentQueue) > 20:   # This value is arbitary that "feels like a sensible limit"
                self._sentQueue.pop()
        return irc.IRCClient._reallySendLine(self, line)

    def lineReceived(self, line):
        #print line
        irc.IRCClient.lineReceived(self, line)

def flatten_values(xs):
    for k,x in xs.items():
        for x_ in x: yield (k,x_)

def pivot_to_values(xs):
    result = {}
    for k,v in xs:
        if v not in result: result[v] = [k]
        else: result[v].append(k)
    return result

def msgAll(msg):
    for protocol in protocols:
        protocol.msg(protocol.channel, msg)

class BotFactory(protocol.ClientFactory):
    protocol = Bot

    def __init__(self, channel, nickname='currybot'):
        self.channel = channel
        self.nickname = nickname

    def clientConnectionLost(self, connector, reason):
        print "Connection lost. Reason: %s" % reason
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "Connection failed. Reason: %s" % reason

if __name__ == "__main__":
    reactor.connectTCP('irc.wgtn.cat-it.co.nz', 6667, BotFactory('#catalyst'))
    reactor.connectTCP('irc.freenode.org', 6667, BotFactory('#catalystlunch'))
    reactor.run()
