#!/usr/bin/env python

"""A really simple IRC bot."""

import sys
import re
from twisted.internet import reactor, protocol
from twisted.words.protocols import irc

from smtplib import SMTP
from email.mime.text import MIMEText


orders = {}
needs_size = {
   'lbq': range(0,5)
}
menus = {
    'lbq': [
        # Two for One Tuesday Menu Pizzas.
        [ 'Margaret & Rita', 'Sliced tomato with fresh basil and even fresher buffalo mozzarella. V - $20' ],
        [ 'The Old Bean', 'Pork belly, pickled chilli, coriander, mozzarella and tomato. V - $24' ],
        [ 'I Am The Eggplant', 'Grilled eggplant, halloumi, salsa, cherry tomatos, mozzarella. - $23' ],
        [ 'Wheel of Pork', 'Bacon, prosciutto, pork belly, confit onions, BBQ sauce. - $24' ],
        [ '"Not When We\'re Busy"', 'Lamb, rosemary, confit onions, goats feta, garlic oil, cherry tomato, mozzarella. - $24.50' ],
        [ 'Gnome Garden', 'Roasted pumpkin, toasted seeds, goats feta, pickled red onion, tomato, mozzarella. - $22.50' ],

        # Mains
        [ 'Mussels', 'A dozen steamed green lip mussels with white wine cream, fresh salsa and Leeds St sourdough. - $19' ],
        [ 'Parrotdog Pilsner Battered Fish & Chips', 'Battered Fish & Chips with salad and grilled lemon. - $22.50' ],
        [ 'Ham & Smoked Swiss Cheese Toasted Sandwich', 'On Leeds St sourdough, with sauerkraut & mustard, served with fries or salad. - $14' ],
        [ 'Salt & Pepper Calamari Salad', 'Salt & Pepper Calamari with grilled baby vegetables, season leaves, avocado & citrus herb dressing - $16' ],
        [ 'LBQ Burger ', '200g beef patty, confit onions, parmesan crisp, free range bacon in a cafe de paris buttered milk bun - $20' ],
        [ 'Cheeseburger', 'Beef, aioli, relish, pickled red onion, smoked swiss cheese - $16' ],
        [ 'Mushroom and Bean Burger', 'Roasted garlic, salad greens, grilled eggplant and tomato relish on sourdough. V - $17' ],
        [ 'Fried Chicken Burger', 'Fried chicken, crispy free range bacon, pickled chilli, aioli, slaw. - $17' ],
        [ 'Parrotdog Pilsner Battered Fish Burger', 'Parrotdog Pilsner Battered Fish with slaw, tartare and salsa - $18' ],
        [ 'Lamb Burger', 'Seasoned lamb patty, mint salsa, rocket, hummus, raita and goats feta - $17.50' ],
    ],
    'lbqthurs' : [
        [ 'Summer Salad', 'Mixed leaf salad with artichoke hearts, cherry tomatoes, French beans and tapenade. GF, VG - $10'],
        [ 'Calamari Salad', ' Coriander, mustard and cumin seed coated pan-fried calamari, with house salad and citrus aioli. - $10'],
        [ 'Chish & Fips', 'Crispy beer battered fish with chunky chips, tartare sauce and lemon. DF - $10'],
        [ 'BBQ Beef Pizza', 'Braised beef in beery BBQ sauce with blue cheese. V. - $10'],
        [ 'Chicken Pizza', 'Citrus chicken with brie and plum sauce. - $10'],
        [ 'Mushroom Burger', 'Roasted portobello mushrooms, roasted red peppers, tomato, lettuce, red onion in seeded bun. V, VG on request - $10' ],
    ],
    'lbqxmas': [
        [ 'ENTREE: soup', 'Tomato and fresh herb soup with fresh bread' ],
        [ 'ENTREE: pesto chicken', 'Grilled pesto chicken with feta, cucumber and tomato' ],
        [ 'ENTREE: garlic prawns', 'Garlic prawns with chilli, aioli and house salad' ],
        [ 'MAIN: courgette and cumin fritters', 'Courgette and cumin fritters with tomato chilli relish and radish, watercress and citrus fruit salad' ],
        [ 'MAIN: chicken roulade', 'Herb chicken roulade with grilled summer vegetables and roast red pepper coulis' ],
        [ 'MAIN: fish of the day', 'Pan-fried fish of the day with grilled summer vegetables and balsamic reduction' ],
        [ 'MAIN: steak', 'Stack with mushroom peppercorn sauch, house salad and kumara chips' ],
        [ 'DESSERT: beery ice cream', 'Wooden Spoon Freezery\'s beery ice cream with chocolate sauce' ],
        [ 'DESSERT: cheesecake', 'Baked dark chocolate and stout cheesecake with whipped cream' ],
        [ 'DESSERT: trifle', 'Summer fruit trifle of Victoria spounge, vanilla custard and sherry' ],
    ],
    'arizona': [
        [ 'Arizona Beef Burger', '200 gram grilled beef patty with bacon, cheese, mesclun, tomato, gherkins, barbeque chipotle sauce and roasted garlic mayo in a bug, served with chunky fries. $19.50' ],
        [ 'Chicken Burger', 'Grilled chicken breast with mesclun, tomato, avacado and roasted garlic mayo in a bin, served with chunky fries. $20'],
    ],
}

emails = {
    'lbq': [
        'Little Beer Quarter <littlebeerquarter@xtra.co.nz>',
        'Hugh Davenport <hugh@davenport.net.nz>',
        'Haydn Newport <haydn@catalyst.net.nz>',
    ],
    'lbqxmas': [
        'Little Beer Quarter <littlebeerquarter@xtra.co.nz>',
        'Hugh Davenport <hugh@davenport.net.nz>',
        'Haydn Newport <haydn@catalyst.net.nz>',
    ],
    'arizona': [
        'Arizona <cu@arizona.co.nz>',
        'Hugh Davenport <hugh@davenport.net.nz>',
        'Haydn Newport <haydn@catalyst.net.nz>',
    ],
}

fromemail = 'Lunchbot (Haydn Newport) <haydn@catalyst.net.nz>'
toemail = None

menu = None

protocols = []

disabled_commands = []#'help', 'menu', 'info', 'order', 'cancel', 'list', 'open', 'close']
ignore_nick = []
admin_nick = [ 'aquaman',
               'aqualaptop',
               'heiko',
               'wi11',
               'haydn',
               'haydnn',
               'kaotien',
               'florent'
             ]
admin_commands = [ 'send',
                   'open',
                   'close',
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
        global orders, menu, disabled_commands, toemail, ignore_nick, admin_nick, admin_commands
        if username in ignore_nick:
            return
        parts = cmd.split(' ',2)
        op = parts[0]
        if op in disabled_commands:
            return
        if op in admin_commands and not username in admin_nick:
            self.msg(channel, 'sorry you are not an admin')
            return
        if op == 'help':
            self.msg(channel, '- !help: show this message.')
            self.msg(channel, '- !menu: show the menu.')
            self.msg(channel, '- !info <n>: show info for an item on the menu.')
            self.msg(channel, '- !order [<nick>] <n> [<size (S|L)>] <special instructions>: order your lunch. `no beetroot` etc can go in `special instructions`')
            self.msg(channel, '- !cancel: cancel your order')
            self.msg(channel, '- !list: list current lunch orders')
            self.msg(channel, '- !msg <message>: Show a message on all channels')
            self.msg(channel, '- !notordered: Show a list of users that have not ordered')
            if username in admin_nick:
              self.msg(channel, '- !open <menu>: open orders for today, clear state')
              self.msg(channel, '- !send: Send a mailing of the order to the restaurant')
              self.msg(channel, '- !close: close orders')
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

            if not special:
                if item in needs_size['lbq']:
                    special = 'Large please'
            elif special and item in needs_size['lbq']:
                if special.startswith(('s ','S ')) or special in ['s', 'S']:
                    special = 'Small, {0}'.format(special[2:])
                elif special.startswith(('L ','l ')) or special in ['l', 'L']:
                    special = 'Large, {0}'.format(special[2:])
                elif item in needs_size['lbq']:
                    special = 'Large, {0}'.format(special)
            if special and special.endswith(', '):
                special = special[:-2]

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
                return
            if parts[1] not in menus:
                self.msg(channel, '%s is not a known menu.' % (parts[1],))
            menu = menus[parts[1]]
            toemail = emails[parts[1]]
            orders = {}
            msgAll('orders are now open for %s!' % (parts[1],))

        if op == 'close':
            msgAll('orders are now closed.');
            orders = {}
            menu = None
            toemail = None

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

        if op == 'send':
            if not menu:
                self.msg(channel, 'orders are not open')
                return

            if len(orders) == 0:
                self.msg(channel, 'nothing has been ordered!')
                return

            global fromemail

            if len(parts) > 1:
                time = parts[1:]
            else:
                time = 'today 12:15pm'
            body = 'Hi, would we be able to make a booking for %s\n' % time
            body += '%d orders for today:' \
                % (sum(len(v) for _,v in orders.items()))
            by_type = pivot_to_values(flatten_values(orders))
            for o,n in sorted(by_type.items(), key=lambda x:len(x[1])):
                instr = o[1] and '(%s) ' % (o[1],) or ''
                body += '\n%dx %s %s[%s]' % \
                    (len(n), menu[o[0]][0], instr, ','.join(n))
            body += '\n\nThanks, can we please get a reply to confirm this order?\n\n'
            body += 'Cheers, Haydn\n021 032 8216';

            self.msg(channel, body)

            msg = MIMEText(body)
            msg['Subject'] = 'Order for %s' % time
            msg['From'] = fromemail
            msg['To'] = ', '.join(map(str, toemail))

            s = SMTP('localhost')
            s.sendmail(fromemail, toemail, msg.as_string())
            s.quit()

            msgAll('orders have been sent to %s.' % toemail)

        if op == 'isadmin':
            if len(parts) < 2:
                self.msg(channel, 'yes, you are an admin' if username in admin_nick else 'no, you are not an admin')
                return
            self.msg(channel, 'yes, %s is an admin' % (parts[1]) if parts[1] in admin_nick else 'no, %s is not an admin' % (parts[1]))

        if op == 'thank' or op == 'thanks':
            if len(parts) < 2:
                self.msg(channel, 'No problem %s' % (username) )
                return
            th_string = 'Th%s' % ( re.split('[^yaeiou]+', parts[1], maxsplit=1)[1] )
            self.msg(channel, 'Thanks %s! %s' % (parts[1], th_string))


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
    reactor.connectTCP('irc.freenode.org', 6667, BotFactory('##catalystlunch'))
    reactor.run()
