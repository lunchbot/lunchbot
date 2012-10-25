#!/usr/bin/env python

"""A really simple IRC bot."""

import sys
from twisted.internet import reactor, protocol
from twisted.words.protocols import irc

orders = {}
menus = {
    'lbq': [
        [ 'Soup of the day', 'Soup of the day with fresh bread. $12' ],
        [ 'Creamy garlic mushrooms', 'Creamy garlic mushrooms with graid bread. $13 or with bacon $16' ],
        [ 'Chicken salad' , 'Grilled chicken salad with feta, olives, tomatoes, cucumber and rocket. $16' ],
        [ 'Tofu stir fry', 'Marinated tofu and green vegetable stir fry on savoury rice. $17' ],
        [ 'Chicken sandwich', 'Peri peri chicken sandwich on a wholemeal bap with roasted red pepper coulis, tomato, red onion, mesclun, shoestrings and aioli. $18' ],
        [ 'Fish & chips', 'Emerson\'s Pilsner battered fish and chips with housemade sauces and salad greens. $19' ],
        [ 'Beef burger', '220g beef patty, streaky bacon, onion rings, chilli jam and cheddar with shorestring fries and aioli. $20' ],
        [ 'Fish of the day', 'Pan fried fish of the day with grilled summer vegetables and lemon oil. $22' ],
        [ 'Steak', 'Steak with sauce du jour, hand-cut kumara chips and house salad. $26' ],
        [ 'Sour pizza' , 'slow roasted roma tomatoes, lemon oil, balsamic reduction and aged cheddar. $15' ],
        [ 'Sweet pizza' , 'house manuka smoked chicken, brie and orange honey sauce. $16' ],
        [ 'Spicy pizza' , 'Harrington\'s pepperoni, jalapenos, red capsicum and chilli oil. $15' ],
        [ 'Salty pizza' , 'capers, olives, halloumi and roasted red pepper coulis. $15' ],
        [ 'Bitter pizza' , 'black-peppered beef, smokey bbq sauce, spinach and blue cheese. $17' ],
        [ 'Fromage pizza' , 'tomato sauce, mozzarella, cheddar and parmesan with our cheese of the week. $15' ],
        [ 'Fungi pizza' , 'portobello, swiss brown mushrooms with forest mushroom sauce and shaved parmesan. $14' ],
        [ 'Ice cream' , 'Wooden Spoon Freezery\'s craft beer ice cream. $9' ],
        [ 'Cheese plate' , 'aged cheddar, brie and blue cheese with nuts, toasted bread and accompaniments. $16' ],
        [ 'Dessert of the week' , 'SURPRISE!!!' ],
    ]
}

menu = None

protocols = []

disabled_commands = []#'help', 'menu', 'info', 'order', 'cancel', 'list', 'open', 'close']

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
        global orders, menu, disabled_commands
        parts = cmd.split(' ',2)
        op = parts[0]
        if op in disabled_commands:
            return
        if op == 'help':
            self.msg(channel, '!help: show this message.')
            self.msg(channel, '!menu: show the menu.')
            self.msg(channel, '!info <n>: show info for an item on the menu.')
            self.msg(channel, '!order [<nick>] <n> <special instructions>: order your lunch. `no beetroot` etc can go in `special instructions`')
            self.msg(channel, '!cancel: cancel your order')
            self.msg(channel, '!list: list current lunch orders')
            self.msg(channel, '!open <menu>: open orders for today, clear state')
            self.msg(channel, '!close: close orders')
            self.msg(channel, '!msg <message>: Show a message on all channels')
            self.msg(channel, '!notordered: Show a list of users that have not ordered')

        if op == 'order':
            if not menu:
                self.msg(channel, 'orders are not open.')
                return

            if len(parts) < 2:
                self.msg(channel, 'i\'m confused about what you wanted.')
                return

            item = maybe_int(parts[1])
            if item == -1 and len(parts) > 2:
                parts = cmd.split(' ',3)
                username = parts.pop(1)
                item = maybe_int(parts[1])
            if item < 0 or item >= len(menu):
                self.msg(channel, 'that\'s not a thing.')
                return

            special = len(parts) > 2 and parts[2] or None

            if not username in orders:
                orders[username] = []

            orders[username].append((item,special))
            if special:
                msgAll('%s added a %s, with instructions: %s.' % \
                    (username, menu[item][0], special))
            else:
                msgAll('%s added a %s.' % (username, menu[item][0]))

        if op == 'menu':
            if not menu:
                self.msg(channel, 'orders are not open.')
                return

            self.msg(channel, 'menu:')
            for i,m in enumerate(menu):
                self.msg(channel, '%d) %s' % (i,m[0]))
            self.msg(channel, '-- end of menu --');

        if op == 'info':
            if not menu:
                self.msg(channel, 'orders are not open.')
                return

            if len(parts) < 2:
                self.msg(channel, 'i\'m confused about what you wanted info on.')

            item = maybe_int(parts[1])
            if item < 0 or item >= len(menu):
                self.msg(channel, 'that\s not a thing.')
                return

            self.msg(channel, '%d) %s - %s' % (item, menu[item][0], menu[item][1]))

        if op == 'cancel':
            if not menu:
                self.msg(channel, 'orders are not open.')
                return

            if len(parts) > 1:
                parts = cmd.split(' ',2)
                username = parts.pop(1)
            if username not in orders:
                self.msg(channel, 'you don\'t have anything ordered!')
            else:
                del orders[username]
                msgAll('%s cancelled their order.' % username)

        if op == 'list':
            if not menu:
                self.msg(channel, 'orders are not open.')
                return

            self.msg(channel, '%d orders for today:' \
                % sum(len(v) for _,v in orders.items()))
            by_type = pivot_to_values(flatten_values(orders))
            for o,n in sorted(by_type.items(), key=lambda x:len(x[1])):
                instr = o[1] and '(%s) ' % (o[1],) or ''
                self.msg(channel, '%dx %s %s[%s]' % \
                    (len(n), menu[o[0]][0], instr, ','.join(n)))
            self.msg(channel, '-- end of orders --');

        if op == 'open':
            if len(parts) < 2:
                self.msg(channel, 'you didn\'t specify a menu. valid menus are:');
                for mn in menus.keys():
                    self.msg(channel, '* %s' % (mn,))
            if parts[1] not in menus:
                self.msg(channel, '%s is not a known menu.' % (parts[1],))
            menu = menus[parts[1]]
            orders = {}
            msgAll('orders are now open for %s!' % (parts[1],))

        if op == 'close':
            msgAll('orders are now closed.');
            orders = {}
            menu = None

        if op == 'msg':
            if len(parts) < 2:
                self.msg(channel, 'you didn\'t specify what you want to message');
                return
            msgAll('<%s> %s' % (username, ' '.join(parts[1:])));

        if op == 'notordered':
            if not menu:
                self.msg(channel, 'orders are not open')
                return

            self.msg(channel, 'The following have not ordered anything: %s' % (', '.join(map(str, list(set(self.users[channel]) - set(orders.keys()))))))

    def privmsg(self, user, channel, msg):
        print 'channel: `%s` user: `%s` msg: `%s`' % (user, channel, msg)
        if msg.startswith('!'):
            self.act( user, channel, msg[1:] )
        elif msg.startswith('lunchbot: '):
            self.act( user, channel, msg[10:] )

    def irc_NOTICE(self, prefix, params):
        if params[1] == '*** Message to %s throttled due to flooding' % (self.factory.channel):
            self.lineRate += 0.1
            self._queue.insert(0, self._sentQueue.pop())
            if not self._queueEmptying:
                self._sendLine()
            print "Flooding detected, lineRate now at %0.1f seconds" % self.lineRate

    def irc_RPL_NAMREPLY(self, prefix, params):
        self.users[params[2]] = params[3].split(' ')
        self.users[params[2]].remove(self.nickname)

    def userJoined(self, user, channel):
        if user != self.nickname:
            self.users[channel].append(user)

    def userLeft(self, user, channel):
        self.users[channel].remove(user)

    def userKicked(self, user, channel, kicker, message):
        self.users[channel].remove(user)

    def userRenamed(self, olduser, newuser):
        # TODO: change orders as well
        for l in self.users:
            try:
                self.users[l].remove(olduser)
                self.users[l].append(newuser)
            except:
                pass

    def userQuit(self, user, reason):
        for l in self.users:
            try:
                l.remove(user)
            except:
                pass

    def _reallySendLine(self, line):
        if line.startswith('PRIVMSG '):
            self._sentQueue.append(line)
            if len(self._sentQueue) > 20:   # This value is arbitary that "feels like a sensible limit"
                self._sentQueue.pop()
        return irc.IRCClient._reallySendLine(self, line)

    def lineReceived(self, line):
        print line
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

    def __init__(self, channel, nickname='lunchbot'):
        self.channel = channel
        self.nickname = nickname

    def clientConnectionLost(self, connector, reason):
        print "Connection lost. Reason: %s" % reason
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "Connection failed. Reason: %s" % reason

if __name__ == "__main__":
    reactor.connectTCP('irc.wgtn.cat-it.co.nz', 6667, BotFactory('#lunch'))
    reactor.connectTCP('irc.freenode.org', 6667, BotFactory('#catalystlunch'))
    reactor.run()
