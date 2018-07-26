import copy
import logging
import regex as re
import spacy
from dateutil import tz, parser

logger = logging.getLogger('datefinder')


class DateFinder(object):
    """
    Locates dates in a text
    """

    DIGITS_MODIFIER_PATTERN = '\d+st|\d+th|\d+rd|first|second|third|fourth|fifth|sixth|seventh|eighth|nineth|tenth|next|last'
    DIGITS_PATTERN = '\d+'
    DAYS_PATTERN = 'monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thur|thurs|fri|sat|sun'
    MONTHS_PATTERN = 'january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec'
    # TIMEZONES_PATTERN = 'ACDT|ACST|ACT|ACWDT|ACWST|ADDT|ADMT|ADT|AEDT|AEST|AFT|AHDT|AHST|AKDT|AKST|AKTST|AKTT|ALMST|ALMT|AMST|AMT|ANAST|ANAT|ANT|APT|AQTST|AQTT|ARST|ART|ASHST|ASHT|AST|AWDT|AWST|AWT|AZOMT|AZOST|AZOT|AZST|AZT|BAKST|BAKT|BDST|BDT|BEAT|BEAUT|BIOT|BMT|BNT|BORT|BOST|BOT|BRST|BRT|BST|BTT|BURT|CANT|CAPT|CAST|CAT|CAWT|CCT|CDDT|CDT|CEDT|CEMT|CEST|CET|CGST|CGT|CHADT|CHAST|CHDT|CHOST|CHOT|CIST|CKHST|CKT|CLST|CLT|CMT|COST|COT|CPT|CST|CUT|CVST|CVT|CWT|CXT|ChST|DACT|DAVT|DDUT|DFT|DMT|DUSST|DUST|EASST|EAST|EAT|ECT|EDDT|EDT|EEDT|EEST|EET|EGST|EGT|EHDT|EMT|EPT|EST|ET|EWT|FET|FFMT|FJST|FJT|FKST|FKT|FMT|FNST|FNT|FORT|FRUST|FRUT|GALT|GAMT|GBGT|GEST|GET|GFT|GHST|GILT|GIT|GMT|GST|GYT|HAA|HAC|HADT|HAE|HAP|HAR|HAST|HAT|HAY|HDT|HKST|HKT|HLV|HMT|HNA|HNC|HNE|HNP|HNR|HNT|HNY|HOVST|HOVT|HST|ICT|IDDT|IDT|IHST|IMT|IOT|IRDT|IRKST|IRKT|IRST|ISST|IST|JAVT|JCST|JDT|JMT|JST|JWST|KART|KDT|KGST|KGT|KIZST|KIZT|KMT|KOST|KRAST|KRAT|KST|KUYST|KUYT|KWAT|LHDT|LHST|LINT|LKT|LMT|LMT|LMT|LMT|LRT|LST|MADMT|MADST|MADT|MAGST|MAGT|MALST|MALT|MART|MAWT|MDDT|MDST|MDT|MEST|MET|MHT|MIST|MIT|MMT|MOST|MOT|MPT|MSD|MSK|MSM|MST|MUST|MUT|MVT|MWT|MYT|NCST|NCT|NDDT|NDT|NEGT|NEST|NET|NFT|NMT|NOVST|NOVT|NPT|NRT|NST|NT|NUT|NWT|NZDT|NZMT|NZST|OMSST|OMST|ORAST|ORAT|PDDT|PDT|PEST|PET|PETST|PETT|PGT|PHOT|PHST|PHT|PKST|PKT|PLMT|PMDT|PMMT|PMST|PMT|PNT|PONT|PPMT|PPT|PST|PT|PWT|PYST|PYT|QMT|QYZST|QYZT|RET|RMT|ROTT|SAKST|SAKT|SAMT|SAST|SBT|SCT|SDMT|SDT|SET|SGT|SHEST|SHET|SJMT|SLT|SMT|SRET|SRT|SST|STAT|SVEST|SVET|SWAT|SYOT|TAHT|TASST|TAST|TBIST|TBIT|TBMT|TFT|THA|TJT|TKT|TLT|TMT|TOST|TOT|TRST|TRT|TSAT|TVT|ULAST|ULAT|URAST|URAT|UTC|UYHST|UYST|UYT|UZST|UZT|VET|VLAST|VLAT|VOLST|VOLT|VOST|VUST|VUT|WARST|WART|WAST|WAT|WDT|WEDT|WEMT|WEST|WET|WFT|WGST|WGT|WIB|WIT|WITA|WMT|WSDT|WSST|WST|WT|XJT|YAKST|YAKT|YAPT|YDDT|YDT|YEKST|YEKST|YEKT|YEKT|YERST|YERT|YPT|YST|YWT|zzz'
    ## explicit north american timezones that get replaced
    # NA_TIMEZONES_PATTERN = 'pacific|eastern|mountain|central'
    # ALL_TIMEZONES_PATTERN = TIMEZONES_PATTERN + '|' + NA_TIMEZONES_PATTERN
    DELIMITERS_PATTERN = '[/\:\-\,\s\_\+\@]+'
    TIME_PERIOD_PATTERN = 'a\.m\.|am|p\.m\.|pm'
    ## can be in date strings but not recognized by dateutils
    EXTRA_TOKENS_PATTERN = 'due|by|on|standard|daylight|savings|time|date|to|until|at|in'
    BEFORE_DATE_PATTERN = 'due|by|on|to|until|at|in|before|after|next|last|ago|since|from'
    
    ## TODO: Get english numbers?
    ## http://www.rexegg.com/regex-trick-numbers-in-english.html

    RELATIVE_PATTERN = 'before|after|next|last|ago|since|from'
    TIME_SHORTHAND_PATTERN = 'noon|midnight|today|yesterday'
    UNIT_PATTERN = 'second|minute|hour|day|week|month|year'

    ## Time pattern is used independently, so specified here.
    TIME_PATTERN = """
    (?P<time>
        ## Captures in format XX:YY(:ZZ) (PM) (EST)
        (
            (?P<hours>\d{{1,2}})
            \:
            (?P<minutes>\d{{1,2}})
            (\:(?<seconds>\d{{1,2}}))?
            ([\.\,](?<microseconds>\d{{1,6}}))?
            \s*
            (?P<time_periods>{time_periods})?
        )
        |
        ## Captures in format 11 AM (EST)
        ## Note with single digit capture requires time period
        (
            (?P<hours>\d{{1,2}})
            \s*
            (?P<time_periods>{time_periods})            
        )
    )
    """.format(
        time_periods=TIME_PERIOD_PATTERN        
    )

    DATES_PATTERN = """
    (
        (
            {time}
            |
            ## Grab any digits
            (?P<digits_modifier>{digits_modifier})
            |
            (?P<digits>{digits})
            |
            (?P<days>{days})
            |
            (?P<months>{months})
            |
            ## Delimiters, ie Tuesday[,] July 18 or 6[/]17[/]2008
            ## as well as whitespace
            (?P<delimiters>{delimiters})
            |
            ## These tokens could be in phrases that dateutil does not yet recognize
            ## Some are US Centric            
            (?P<before_date_tokens>{before_date_tokens})
        ## We need at least three items to match for minimal datetime parsing
        ## ie 10pm
        ){{3,}}
    )
    """
    ## (?P<extra_tokens>{extra_tokens})
            ## |
    #extra_tokens=EXTRA_TOKENS_PATTERN,
    DATES_PATTERN = DATES_PATTERN.format(
        time=TIME_PATTERN,
        digits=DIGITS_PATTERN,
        digits_modifier=DIGITS_MODIFIER_PATTERN,
        days=DAYS_PATTERN,
        months=MONTHS_PATTERN,
        delimiters=DELIMITERS_PATTERN,        
        before_date_tokens=BEFORE_DATE_PATTERN
    )

    DATE_REGEX = re.compile(DATES_PATTERN, re.IGNORECASE | re.MULTILINE | re.UNICODE | re.DOTALL | re.VERBOSE)

    TIME_REGEX = re.compile(TIME_PATTERN, re.IGNORECASE | re.MULTILINE | re.UNICODE | re.DOTALL | re.VERBOSE)

    ## These tokens can be in original text but dateutil
    ## won't handle them without modification
    REPLACEMENTS = {
        "standard": " ",
        "daylight": " ",
        "savings": " ",
        "time": " ",
        "date": " ",
        "by": " ",
        "due": " ",
        "on": " ",
        "to": " ",
        "in": " ",
        "the": " "
    }
    
    ## Characters that can be removed from ends of matched strings
    STRIP_CHARS = ' \n\t:-.,_'

    def __init__(self, base_date=None, use_spacy=False):
        self.base_date = base_date
        if use_spacy:
            self.nlp = spacy.load('en_core_web_sm')
        

    def find_dates(self, text, source=False, index=False, strict=False):
        """
            return dates information from sentence using regex approach
        """
        for date_string, indices, captures in self.extract_date_strings(text, strict=strict):

            as_dt = self.parse_date_string(date_string)
            if as_dt is None:
                ## Dateutil couldn't make heads or tails of it
                ## move on to next
                continue

            returnables = (as_dt,)
            if source:
                returnables = returnables + (date_string,)
            if index:
                returnables = returnables + (indices,)

            yield returnables


    def extract_date_strings(self, text, strict=True):
        """
        Scans text for possible datetime strings and extracts them 
        source: also return the original date string
        index: also return the indices of the date string in the text
        strict: Strict mode will only return dates sourced with day, month, and year
        """
        
        for match in self.DATE_REGEX.finditer(text):
            match_str = match.group(0)
            indices = match.span(0)

            ## Get individual group matches
            captures = match.capturesdict()
            time = captures.get('time')
            digits = captures.get('digits')
            digits_modifiers = captures.get('digits_modifiers')
            days = captures.get('days')
            months = captures.get('months')
            # timezones = captures.get('timezones')
            delimiters = captures.get('delimiters')
            time_periods = captures.get('time_periods')
            # extra_tokens = captures.get('extra_tokens')
            before_date_tokens = captures.get('before_date_tokens')

            if strict:
                complete = False
                ## in 2013, at 2014-01-1 ; using before_date_tokens
                if len(before_date_tokens) > 0:
                    # if we pick small length number, continue
                    if len(digits) == 1 and len(digits[0]) < 4:
                        continue
                    complete = True                    
                ## 12-05-2015
                if len(digits) == 3:
                    complete = True
                ## 19 February 2013 year 09:10
                elif (len(months) == 1) and (len(digits) == 2):
                    complete = True

                if not complete:
                    continue

            ## sanitize date string
            ## replace unhelpful whitespace characters with single whitespace
            match_str = re.sub('[\n\t\s\xa0]+', ' ', match_str)
            match_str = match_str.strip(self.STRIP_CHARS)

            ## Save sanitized source string
            yield match_str, indices, captures


    def _find_and_replace(self, date_string):
        """
            replaces substring from date_string which dateutils wont understand
        """
        # add timezones to replace
        cloned_replacements = copy.copy(self.REPLACEMENTS)  # don't mutate
        
        date_string = date_string.lower()
        for key, replacement in cloned_replacements.items():
            # we really want to match all permutations of the key surrounded by whitespace chars except one
            # for example: consider the key = 'to'
            # 1. match 'to '
            # 2. match ' to'
            # 3. match ' to '
            # but never match r'(\s|)to(\s|)' which would make 'october' > 'ocber'
            date_string = re.sub(r'(^|\s)' + key + '(\s|$)', replacement, date_string, flags=re.IGNORECASE)

        return date_string
    

    def parse_date_string(self, date_string):  
        """
            parses date_string using dateutils and returns datetime object
        """      
        # For well formatted string, we can already let dateutils parse them
        # otherwise self._find_and_replace method might corrupt them
        try:
            as_dt = parser.parse(date_string, default=self.base_date)
        except Exception as e:
            # replace tokens that are problematic for dateutil
            date_string = self._find_and_replace(date_string)

            ## One last sweep after removing
            date_string = date_string.strip(self.STRIP_CHARS)
            ## Match strings must be at least 3 characters long
            ## < 3 tends to be garbage
            if len(date_string) < 3:
                return None

            try:
                logger.debug('Parsing {0} with dateutil'.format(date_string))
                as_dt = parser.parse(date_string, default=self.base_date)
            except Exception as e1:
                logger.debug(e1)
                as_dt = None
            
        return as_dt
       

    def find_dates_with_spacy(self, text, source=False):
        """
            returns dates information from sentence using spacy approach
        """
        # get dates string
        dates_string = self.extract_date_strings_with_spacy(text)

        # parse dates string
        returnables = []
        for date_string in dates_string:
            as_dt = self.parse_date_string(date_string)

            if as_dt is None:
                continue

            returnable = (as_dt,)
            if source:
                returnable = returnable + (date_string,)
            returnables.append(returnable)

        return returnables


    def extract_date_strings_with_spacy(self, text):
        """
            extracts date strings using spacy's NER model,
            returns list of dates of text
        """
        dates = []
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ == 'DATE':
                dates.append(ent.text)
        return dates      


def find_dates(
    text,
    source=False,
    index=False,
    strict=False,
    base_date=None,
    use_spacy=False
    ):
    """
    Extract datetime strings from text
    :param text:
        A string that contains one or more natural language or literal
        datetime strings
    :type text: str|unicode
    :param source:
        Return the original string segment
    :type source: boolean
    :param index:
        Return the indices where the datetime string was located in text
    :type index: boolean
    :param strict:
        Only return datetimes with complete date information. For example:
        `July 2016` of `Monday` will not return datetimes.
        `May 16, 2015` will return datetimes.
    :type strict: boolean
    :param base_date:
        Set a default base datetime when parsing incomplete dates
    :type base_date: datetime
    :param use_spacy :
        flag to use spacy for extractint date expressions
    :return: Returns a generator that produces :mod:`datetime.datetime` objects,
        or a tuple with the source text and index, if requested
    """
    date_finder = DateFinder(base_date=base_date, use_spacy=use_spacy)
    if use_spacy:
        return date_finder.extract_date_with_spacy(text, source=source)    
    return date_finder.find_dates(text, source=source, index=index, strict=strict, use_spacy=use_spacy)