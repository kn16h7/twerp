# PPylint: disable-msg=W0613,W0612,W0212,W0511,R0912,C0322,W0704
# W0511 = XXX (my own todo's)

"""

cli.py
======

Desc: Command-line module

Author: Rob Cakebread <cakebread a t gmail.com>

License : BSD

"""

__docformat__ = 'restructuredtext'


import cmd
import sys
import optparse
import logging
from urllib import quote_plus

from clint.textui import colored

from twerp.__init__ import __version__ as VERSION
from twerp.twiliolib import RestClient


#For tab-completion when in interactive mode
URLS = ['http://twimlets.com/holdmusic?Bucket=com.twilio.music.rock&',
        'http://twimlets.com/holdmusic?Bucket=com.twilio.music.soft-rock&',
        'http://twimlets.com/holdmusic?Bucket=com.twilio.music.ambient&',
        'http://twimlets.com/holdmusic?Bucket=com.twilio.music.classical&',
        'http://twimlets.com/holdmusic?Bucket=com.twilio.music.electronica&',
        'http://twimlets.com/holdmusic?Bucket=com.twilio.music.guitars&',
        'http://twimlets.com/holdmusic?Bucket=com.twilio.music.newage&',
        ]


class Interactive(cmd.Cmd):
    """Cmmand processor"""
    def __init__(self, client, sid=None):
        cmd.Cmd.__init__(self)
        self.sid = sid
        self.logger = logging.getLogger("twerp")
        self.client = client

    def emptyline(self):
        return

    def postloop(self):
        '''Print a blank line after program exits interactive mode'''
        print '\n'

    def cmdloop(self, sid=''):
        intro = "Type 'help' for twerp commands"
        self.sid = sid
        if self.sid is not None:
            self.prompt = "twerp (%s) >> " % self.sid[0:7]
        else:
            self.prompt = "twerp (...) >> "
        try:
            return cmd.Cmd.cmdloop(self, sid)
        except KeyboardInterrupt:
            sys.exit(0)

    def do_info(self, sid=None):
        '''
        Display info for current SID
        '''
        if not sid:
            sid = self.sid
        if sid:
            self.client.sid_call(sid)
        else:
            self.logger.error("Need an SID")

    def do_hangup(self, arg=None):
        '''
        Hangs up call associated with current SID shown in prompt.
        '''
        self.client.hangup(self.sid)
        self.prompt = "twerp (...) >> "

    def do_nuke(self, arg=None):
        '''
        Hangs up all voice calls in progress for the entire account
        CAUTION: Read the above carefully.
        '''
        self.client.hangup_all_calls()
        self.prompt = "twerp (...) >> "

    def do_list(self, args=None):
        '''
        List all calls in progress for your account
        '''
        self.client.list_calls()

    def do_sid(self, sid):
        '''
        Change SID for interactive session. New SID shows in prompt.
        '''
        if sid:
            self.sid = sid
            self.prompt = colored.red("twerp (%s...) >> " % self.sid[0:7])
        else:
            print >> sys.stderr, "You must specify the SID to use."

    def do_forward(self, number):
        '''
        Forward call to another phone number. e.g.
        forward +13235551212
        '''
        if number:
            url = '''http://twimlets.com/forward?PhoneNumber='''
            text = quote_plus(number)
            url = '%s%s' % (url, number)
            print url
            call = self.client.call_url(self.sid, url)
            #print >> sys.stderr, call.status

    def do_url(self, url):
        '''
        Redirect call using TwiML at URL e.g.
        url http://twimlets.com/some.twml
        '''
        if url:
            call = self.client.call_url(self.sid, url)
            #print >> sys.stderr, call.status
        else:
            print >> sys.stderr, "You need to specify a valid TWML URL e.g. "
            print >> sys.stderr, \
                "http://twimlets.com/holdmusic?Bucket=com.twilio.music.ambient"

    def complete_url(self, text, line, begidx, endix):
        if not text:
            completions = URLS[:]
        else:
            completions = [f
                            for f in URLS
                            if f.startswith(text)
                            ]
        return completions

    def do_EOF(self, line):
        '''Exit twerp's interactive mode'''
        return True


class Twerp(object):

    """
    Main class for twerp optparse CLI
    """

    def __init__(self):
        self.options = None
        self.logger = logging.getLogger("twerp")
        self.client = RestClient()

    def set_log_level(self):
        """
        Set log level according to command-line options

        @returns: logger object
        """

        if self.options.debug:
            self.logger.setLevel(logging.DEBUG)
        elif self.options.verbose:
            self.logger.setLevel(logging.INFO)
        self.logger.addHandler(logging.StreamHandler())
        return self.logger

    def run(self):
        """
        Perform actions based on CLI options

        @returns: status code
        """
        opt_parser = setup_opt_parser()
        (self.options, remaining_args) = opt_parser.parse_args()
        self.logger = self.set_log_level()

        if self.options.numbers:
            return self.client.list_numbers(self.options.verbose)
        elif self.options.dial:
            if not self.options.url and not self.options.say:
                self.logger.error("You must specify a --url with TwiML")
                self.logger.error("""e.g. This URL will say 'hello tworld'
                http://twimlets.com/message?Message%5B0%5D=Hello%20Tworld& """)
                return 1
            numbers = self.options.dial.split(",")
            sid = self.client.call_numbers(numbers, self.options.verbose,
                    self.options.callerid, self.options.url,
                    self.options.say)
            if self.options.interactive:
                Interactive(self.client).cmdloop(sid)
                return
        elif self.options.purchase:
            return self.client.purchase_number(self.options.purchase)
        elif self.options.contains and self.options.areacode:
            return self.client.numbers_contain_areacode(self.options.areacode, self.options.contains)
        elif self.options.contains:
            return self.client.numbers_contain(self.options.contains)
        elif self.options.areacode:
            return self.client.search_numbers(self.options.areacode)
        elif self.options.applications:
            return self.client.list_applications()
        elif self.options.participants:
            return self.client.list_conference_participants()
        elif self.options.conferences:
            return self.client.list_conferences()
        elif self.options.listsms:
            return self.client.list_sms()
        elif self.options.twerp_version:
            return self.twerp_version()
        elif self.options.sid:
            return self.client.get_sms_sid(self.options.sid)
        elif self.options.sms_recipients:
            numbers = self.options.sms_recipients.split(",")
            return self.client.send_sms(numbers, self.options.sms_message,
                    self.options.verbose)
        elif self.options.notifications:
            return self.client.notifications(self.options.verbose)
        elif self.options.interactive:
            Interactive(self.client).cmdloop('')
            return
        else:
            opt_parser.print_help()
        return 2

    def twerp_version(self):
        """
        Show twerp's version

        @returns: None
        """
        print("twerp version %s" % VERSION)


def setup_opt_parser():
    """
    Setup the optparser

    @returns: opt_parser.OptionParser

    """
    #pylint: disable-msg=C0301
    #line too long

    usage = "usage: %prog [options]"
    opt_parser = optparse.OptionParser(usage=usage)

    opt_parser.add_option("-V", "--version", action="store_true",
            dest="twerp_version", default=False,
            help="Show twerp version and exit.")
    opt_parser.add_option("-v", "--verbose", action='store_true',
            dest="verbose", default=False, help="Show more output stuff.")

    opt_parser.add_option("--debug", action='store_true',
            dest="debug", default=False, help="Show debugging information.")

    opt_parser.add_option("-q", "--quiet", action='store_true',
            dest="quiet", default=False, help="Show less output.")

    group_common = optparse.OptionGroup(opt_parser,
            "Common options",
            "These options can be used for both SMS and voice calls.")

    group_common.add_option("-c", "--callerid", action='store',
            dest="callerid", default=None,
            help="Phone number you are calling from or texting from.")

    group_sms = optparse.OptionGroup(opt_parser,
            "SMS options",
            "Send and reveive SMS text messages.")
    group_sms.add_option("-m", "--message", action='store',
            metavar="<TXT MSG>",
            dest="sms_message", default=False, help="Send SMS text message")

    group_sms.add_option("-s", "--sms", action='store',
            dest="sms_recipients", default=False,
            metavar="+12135551212,+14155551212",
            help="Send SMS text message to list of numbers.")

    group_sms.add_option("-l", "--list-sms", action='store_true',
            dest="listsms", default=False, help="Show incoming SMS messages.")

    group_call = optparse.OptionGroup(opt_parser,
            "Voice call options",
            "Place phone calls, execute TWIML.")
    group_call.add_option("-d", "--dial", action='store',
            metavar="+12135551212,+14155551212",
            help="List of numbers to dial, comma-separated.",
            dest="dial", default=False)

    group_call.add_option("-i", "--interactive", action='store_true',
            help="Go into interactive command-line mode after dialing.",
            dest="interactive", default=False)

    group_call.add_option("-y", "--say", action='store',
            metavar="Say something.",
            dest="say", default=False,
            help="Use with --dial to say something.")

    group_call.add_option("-u", "--url", action='store',
            metavar="URL of TWIML",
            dest="url", default=False,
            help="URL of TWIML to pass call with --call")

    group_call.add_option("-C", "--conferences", action='store_true',
            dest="conferences", default=False,
            help="Show conferences in-progress.")

    group_call.add_option("-b", "--buy", action='store',
            dest="purchase", default=False,
            metavar="+12135551212",
            help="Buy a specific phone number listed with -x")

    group_call.add_option("-a", "--area-code", action='store',
            dest="areacode", default=False,
            metavar="AREA CODE",
            help="Search for phone number to purchase by area code. Use -b to purchase from these results.")

    group_call.add_option("-x", "--contains", action='store',
            dest="contains", default=False,
            help="Search for phone number to purchase by numbers or letters it contains.")

    group_call.add_option("-P", "--conference-participants", action='store_true',
            dest="participants", default=False,
            help="Show participants for all conferences in-progress.")

    group_reports = optparse.OptionGroup(opt_parser,
            "Reporting options",
            "List your Twilio phone numbers and information about each.")

    group_reports.add_option("-F", "--notifications", action='store_true',
            dest="notifications", default=False, help="Show notifications " +
            "from Twilio API (error messages and warnings).")

    group_reports.add_option("-N", "--numbers", action='store_true',
            dest="numbers", default=False, help="Show all my Twilio phone " +
            "numbers. Use -Nv for detailed info on each number.")

    group_reports.add_option("-S", "--SID", action='store',
            dest="sid", default=False, help="Show log for given SID")

    group_applications = optparse.OptionGroup(opt_parser,
            "Applications",
            "Twilio Application information.")

    group_applications.add_option("-A", "--applications", action='store_true',
            dest="applications", default=False, help="Show all my Twilio Applications.")

    opt_parser.add_option_group(group_common)
    opt_parser.add_option_group(group_sms)
    opt_parser.add_option_group(group_call)
    opt_parser.add_option_group(group_reports)
    opt_parser.add_option_group(group_applications)
    return opt_parser


def main():
    """
    Let's do it.
    """
    my_twerp = Twerp()
    return my_twerp.run()

if __name__ == "__main__":
    sys.exit(main())
